import enum
import os
from re import compile
from copy import deepcopy
from itertools import groupby

class Printer:
    @staticmethod
    def print_stats(vals, delimiter=None):
        '''pretty print values from Identifier:stats '''
        if delimiter is None:
            delimiter = '\t'

        lines = '\n'.join([delimiter.join([str(v) for v in list(val)]) for val in vals])
        if lines:
            print(lines)

class Mode(enum.Enum):
    ''' modes for Identifier.__analyze '''
    ARCHIVE = enum.auto()

    SECTION_I = enum.auto()
    SECTION_A = enum.auto()

    PAGE_I = enum.auto()
    PAGE_S = enum.auto()
    PAGE_A = enum.auto()
    PAGE_B = enum.auto()

    QUEST_I  = enum.auto()
    QUEST_SA = enum.auto()
    QUEST_A  = enum.auto()
    QUEST_B  = enum.auto()
    QUEST_C  = enum.auto()

class Identifier:

    @staticmethod
    def to_rel_path(path, rel_path):
        '''
        can transform:
        abs_path -> rel path from archive root
        '''
        result = os.path.relpath(path, os.path.join(rel_path, '..'))
        return result

    @staticmethod
    def to_identifier(path, omit_section=None) -> str:
        '''
        can transform:
        abs_path -> section
        abs_path -> section:page
        abs_path -> :page
        '''

        result = ''

        if os.path.isdir(path):
            section = os.path.basename(path)
            result = section

        elif os.path.isfile(path):
            root, file_name = os.path.split(path)
            section = os.path.basename(root)
            page, _ = os.path.splitext(file_name)

            if omit_section:
                result = ':%s' % (page)
            else:
                result = '%s:%s' % (section, page)

        return result

    def __init__(self, config, uri=None, preanalysis=None, printer=None, hypothetical=False, tocfilter_options=None):
        ''' (self) -> ([ResultDict], mode: Mode, summary_name: String)
        * Analzyes uri and returns one of the following:

        ** 'abstract-algebra<@'           -> (multiple dirs                ,~doesn't affect mode)
        ** 'abstract-algebra<'            -> (multiple dirs                ,~doesn't affect mode)
        ** 'grapth-theory:R<'             -> (multiple dirs/files          ,~doesn't affect mode)

        ** ''                             -> (multiple dirs                 ,ARCHIVE)

        ** 'group-theory'                 -> (single dir+multiple files     ,SECTION_I)
        ** '@'                            -> (multiple dirs                 ,SECTION_A)

        ** 'group-theory:group-like-2'    -> (single dir,file               ,PAGE_I)
        ** 'group-theory:group-like-@'    -> (single dir+multiple files     ,PAGE_S)
        ** 'group-theory:@'               -> (single dir+multiple files     ,PAGE_A)
        ** '@:@'                          -> (multiple dirs,files,lines     ,PAGE_B)

        ** 'group-theory:group-like-2#5'  -> (single dir,file,lines         ,QUEST_I)
        ** 'group-theory:group-like-@#@'  -> (single dir,file+multiple lines,QUEST_SA)
        ** 'group-theory:group-like-2#@'  -> (single dir,file+multiple lines,QUEST_A)
        ** 'group-theory:@#@'             -> (single dir+multiple files     ,QUEST_B)
        ** '@:@#@'                        -> (multiple dirs,files,lines     ,QUEST_C)
        '''

        if uri is None:
            uri = ''

        if printer is None:
            self.printer = print
        else:
            self.printer = printer

        if config is None:
            self.printer('no config provided')
        else:
            self.config = config

        self.failed   = False
        self.qids_set = False

        # queries that don't need to check against the archive
        # e.g. for making match tests against Anki
        self.hypthetical = hypothetical

        if tocfilter_options is None:
            self.expand_tocs = False
            self.nonhierarchical_refs = False

        else:
            self.expand_tocs = tocfilter_options['expand_tocs']
            self.nonhierarchical_refs = tocfilter_options['nonhierarchical_refs']

        component_regex = compile(# optional filter component
                           r'^(?:([^#/]+)//)?'
                           # compulsory section component (but may be empty!)
                           r'([^#/:]*)'
                           # can't have quest identifier without page component!
                           r'(?:'
                           # can be one or two colons
                           r':?:'
                           # page component can't be empty
                           r'([^#/:]+)'
                           # quest identifer must be preceded with number sign
                           r'(?:#'
                           # quest identifer is numbers or @
                           r'(@|\d+)'
                           # closes both non capturing groups
                           r')?)?$')

        matches = component_regex.search(uri)

        if matches is not None:
            self.uri                = uri
            self.filter_component   = matches.group(1) or ''
            self.section_component  = matches.group(2) or ''
            self.page_component     = matches.group(3) or ''
            self.quest_component    = matches.group(4) or ''

            self.__decide_mode()
        else:

            # e.g. ark ../group-theory
            if os.path.isdir(uri):
                self.filter_component  = ''
                self.section_component = os.path.basename(os.path.abspath(uri))
                self.page_component    = ''
                self.quest_component   = ''

                self.uri               = self.section_component
                self.__decide_mode()

            # e.g. ark ./edq289gr.adoc
            elif os.path.isfile(uri):
                full_uri = os.path.abspath(uri)
                self.filter_component  = ''
                self.section_component = os.path.basename(os.path.dirname(full_uri))
                self.page_component    = os.path.splitext(os.path.basename(full_uri))[0]
                self.quest_component   = ''

                self.uri               = self.section_component+':'+self.page_component
                self.__decide_mode()

            else:
                self.printer('query malformed: invalid archive uri: ' + uri)
                self.failed = True

        if preanalysis:
            self.analysis = deepcopy(preanalysis)
            self.summary_name = ''
            self.qids_set = True

        elif not hypothetical:
            self.analysis, self.summary_name = self.__analyze()

        self.analysis = self.__postfilter(self.analysis)

    def __decide_mode(self):
            tempMode = Mode.ARCHIVE

            ''' section components '''

            if self.section_component == '@':
                tempMode = Mode.SECTION_A

            elif self.section_component:
                tempMode = Mode.SECTION_I

            ''' page components '''

            if self.page_component:

                # section defaults to cwd if page is specified
                if not self.section_component:
                    self.section_component = os.path.basename(os.getcwd())
                    tempMode = Mode.SECTION_I

                if self.page_component == '@':
                    if tempMode == Mode.SECTION_A:
                        tempMode = Mode.PAGE_B

                    else: # tempMode == Mode.SECTION_I:
                        tempMode = Mode.PAGE_A

                elif tempMode == Mode.SECTION_I:

                    if self.page_component.endswith('-@') and len(self.page_component) >= 3:
                        tempMode = Mode.PAGE_S

                    else:
                        tempMode = Mode.PAGE_I

            ''' quest components '''

            if self.quest_component:

                if self.quest_component == '@':
                    if tempMode == Mode.PAGE_B:
                        tempMode = Mode.QUEST_C

                    elif tempMode == Mode.PAGE_A:
                        tempMode = Mode.QUEST_B

                    elif tempMode == Mode.PAGE_S:
                        tempMode = Mode.QUEST_SA

                    elif tempMode == Mode.PAGE_I:
                        tempMode = Mode.QUEST_A

                elif tempMode == Mode.PAGE_I:
                    tempMode = Mode.QUEST_I

                elif self.quest_component:
                    self.printer('query malformed: cannot use quest identifers without definite page topic or @')

            self.mode = tempMode

    def __analyze(self):
        '''
        analyze filter component and fill
        topics accordingly
        '''

        summary_name = self.config['archive_root']
        topics       = []

        self.failed = False

        ''' processing of filter '''

        if not ':' in self.filter_component:
            if self.filter_component:
                matched_ancestors = []
                ancestor_regex = compile('(.*/' + self.filter_component.replace('-','[^./]*-') + '[^./]*)/?')

            first_dir = True
            toc_regex = compile('^%s.*' % self.config['archive_syntax']['tocs'])

            for root, dirs, files in os.walk(summary_name):
                files[:] = [f for f in files if not f.startswith('.')]

                content_pages, tocs = [], []
                for f in files:
                    (tocs if toc_regex.search(f) else content_pages).append(f)

                dirs[:] = [d for d in dirs if
                        not d.startswith('.') and (not tocs or first_dir)]

                if self.filter_component:
                    match = ancestor_regex.search(root)
                else:
                    match = True

                first_dir = False

                if tocs and root is not summary_name and match:
                    topics.append({
                        'dir_name':   root,
                        'files': [{
                            'file_name': f,
                            'lines': []
                            } for f in content_pages],
                        'tocs': [{
                            'file_name': t,
                            'lines': []
                            } for t in tocs]
                        })

                    if self.filter_component:
                        matched_ancestors.append(match.group(1))

            if self.filter_component:
                unique_ancestors = set(matched_ancestors)

                if len(unique_ancestors) < 1:
                    self.printer('no such ancestor topic exists')
                    self.failed = True

                if len(unique_ancestors) > 1:
                    self.printer('ancestor topic is ambiguous: ' +
                        ' '.join(map(lambda d: os.path.basename(d), unique_ancestors)))
                    self.failed = True

                summary_name = unique_ancestors.pop()

            self.qids_set = False
            return (topics, summary_name)

        else:
            result = []

            theid = Identifier(self.config, uri='@:@', printer=self.printer)
            pagerefs = theid.pagerefs(
                    self.filter_component,
                    # these come from tocfilter_options argument
                    expand_tocs=self.expand_tocs, nonhierarchical_refs=self.nonhierarchical_refs)
            summary_name = Identifier(self.config, uri=self.filter_component, printer=self.printer).paths()[0][0]

            files = map(lambda t: os.path.split(t), [i[2] for p in pagerefs for i in p['pagerefs']])
            files_grouped = groupby(files, lambda t: t[0])

            for key, item in files_grouped:
                files = (list(map(lambda t: { 'file_name': t[1], 'lines': [] }, item)))
                result.append({
                        'dir_name':   key,
                        'files': files,
                        'tocs': []
                        })

            return (result, summary_name)

    def __postfilter(self, topics):
        ''' returns filtered topic '''
        ''' processing of section topic '''

        if self.section_component and not self.section_component == '@':
            section_regex = compile('/' + self.section_component.replace('-','[^./]*-') + '[^./]*$')
            topics = list(filter(lambda t: section_regex.search(t['dir_name']), topics))

            if len(topics) < 1:
                self.printer('no such section topic exists: "'+self.uri+'"')
                self.failed = True

            if len(topics) > 1:
                self.printer('section topic is ambiguous: '
                    + ' '.join(list(map(lambda t: os.path.basename(t['dir_name']), topics))))
                self.failed = True

        ''' processing of page topic '''

        if len(topics):
            first_dir = topics[0]
        else:
            self.printer('no sections found')
            self.failed = True
            return {}

        if self.mode == Mode.PAGE_S or self.mode == Mode.QUEST_SA:
            page_regex = compile('^' + self.page_component[:-2].replace(r'-', r'[^./]*-') + r'[^./]*\..*$')

            first_dir['files'] = list(filter(
                lambda f: page_regex.search(f['file_name']), first_dir['files']))
            first_dir['tocs'] = list(filter(
                lambda f: page_regex.search(f['file_name']), first_dir['tocs']))

        elif self.page_component and not self.page_component.endswith('@'):
            page_regex = compile('^' + self.page_component.replace('-', r'[^./]*-') + r'[^-./]*\..*$')

            first_dir['files'] = list(filter(
                lambda f: page_regex.search(f['file_name']), first_dir['files']))
            first_dir['tocs'] = list(filter(
                lambda f: page_regex.search(f['file_name']), first_dir['tocs']))

        if len(first_dir['files'] + first_dir['tocs']) < 1:
            self.printer('no such page topic exists: "' + self.uri + '"')
            self.failed = True

        # e.g. `gr-@` would hit `graphs-theory-1` and `groups-1`
        if self.page_component.endswith('-@') and len(first_dir['files'] + first_dir['tocs']) > 1:
            page_series = set(map(lambda f: re.search('(.*)-.*', f['file_name']).group(1), first_dir['files']))
            if len(page_series) > 1:
                self.printer('page topic series is ambiguous: '
                    + ' '.join(list(map(lambda s: os.path.basename(s), page_series))))
                self.failed = True

        elif self.page_component and not self.page_component == '@' and len(first_dir['files'] + first_dir['tocs']) > 1:
            self.printer('page topic is ambiguous: '
                + ' '.join(list(map(lambda f:
                    os.path.splitext(os.path.basename(f['file_name']))[0], first_dir['files'] + first_dir['tocs']) )))
            self.failed = True

        '''
        processing of quest identifier
        '''

        if self.quest_component and not self.qids_set:
            quest_id_regex = compile(self.config['archive_syntax']['qids'])
            for d in topics:
                for f in d['files']:
                    with open(d['dir_name'] + '/' + f['file_name'], 'r') as stream:
                        searchlines = stream.readlines()
                        for idx, line in enumerate(searchlines):
                            quest_identifier = quest_id_regex.search(line)
                            if quest_identifier:
                                f['lines'].append({
                                    'lineno': idx + 1,
                                    'quest': quest_identifier.group(1)})
            self.qids_set = True

        if self.mode == Mode.QUEST_I:
            first_dir  = topics[0]
            first_file = topics[0]['files'][0]

            quest_comp_regex = compile(self.quest_component + '$')

            first_file['lines'] = list(filter(
                lambda l: quest_comp_regex.search(l['quest']), first_file['lines']))

            if len(first_file['lines']) < 1:
                self.printer('no such quest identifier exists in file: "' + self.quest_component + '"')
                self.failed = True

            elif len(first_file['lines']) > 1:
                self.printer('quest is ambiguous: "' + self.quest_component + '"')
                self.failed = True

        return topics



    def paths(self, pages=None, tocs=None):
        ''' resturns [(abs_file_name, ark_loc, lineno, qid)] '''

        filetypes = []
        if tocs is None or tocs:
            tocs = True
            filetypes.append('tocs')
        elif tocs:
            tocs = False

        if pages is None or pages:
            pages = True
            filetypes.append('files')
        elif pages:
            pages = False

        result = []

        if self.quest_component:
            result = [((
                os.path.normpath(os.path.join(d['dir_name'], f['file_name'])),
                os.path.basename(d['dir_name']) +':'+ os.path.splitext(f['file_name'])[0],
                l['lineno'], l['quest'] ))
                for d in self.analysis for ft in filetypes for f in d[ft] for l in f['lines']]

        elif self.page_component:
            result = [((
                os.path.normpath(os.path.join(d['dir_name'], f['file_name'])),
                os.path.basename(d['dir_name']) +':'+ os.path.splitext(f['file_name'])[0],
                None, None ))
                for d in self.analysis for ft in filetypes for f in d[ft]]

        elif self.section_component:
            result = [((
                os.path.normpath(d['dir_name']),
                os.path.basename(d['dir_name']),
                None, None ))
                for d in self.analysis]

        else:
            result.append(( os.path.normpath(self.summary_name), os.path.basename(self.summary_name)+'//', None, None ))

        return result

    def stats(self, preanalysis=None, fake_mode=None, tocs=None, pages=None):
        ''' returns [(identifer, qid, lineno)] for files '''
        ''' returns [(identifer, count of qtags, count of content lines)] for qids '''

        qid_regex = compile(self.config['archive_syntax']['qids'])
        content_line_regex = compile(
                # block titles
                r'^(\.[^. ]+|'
                # ordered list
                r'\.+ .+|'
                # unordered list
                r'\*+ .+|'
                # any lines starting with anything except those
                r'[^\n\'":=/\-+< ]+)')

        other_regexes = [compile(other_re) for other_re in self.config['archive_syntax']['stats']]

        paths = self.paths(tocs=tocs, pages=pages)
        result = []

        if self.quest_component:
            result = [ (entry[0], entry[3], entry[2] ) for entry in paths]

        elif self.page_component or fake_mode:
            for entry in paths:
                qid_count = 0
                other_counts = [0] * len(other_regexes)

                with open(entry[0]) as fx:
                    searchlines = fx.readlines()
                    for _, line in enumerate(searchlines):
                        if qid_regex.search(line):
                            qid_count += 1

                        for idx, re in enumerate(other_regexes):
                            if re.search(line):
                                other_counts[idx] += 1

                    result.append((
                        os.path.normpath(entry[0]),
                        qid_count) + tuple(other_counts))

        elif self.section_component:
            analyses = [(d[0], Identifier(self.config, uri=d[1]+':@', preanalysis=self.analysis).stats()) for d in paths]
            result = [( d,
                sum(map(lambda l: int(l[1]), a)),
                sum(map(lambda l: int(l[2]), a)) )
                for d, a in analyses ]
                # TODO generalize to accepts any amount of stats

        else:
            # all_stats = self.stats( (topics,''), Mode.PAGE_A )
            fake_stats = Identifier(self.config, uri='@:@', preanalysis=self.analysis).stats()
            result = [( self.summary_name,
                sum(map(lambda l: int(l[1]), fake_stats)),
                sum(map(lambda l: int(l[2]), fake_stats)) )]
            # TODO generalize to accepts any amount of stats


        return result

    def headings(self):
        if not self.page_component:
            self.printer('needs page component')
        elif self.quest_component:
            self.printer('must not have quest component')
        else:
            return self._headings()

    def _headings(self):
        '''
        returns list of headers defined in file
        [{
            'file_name': '/path/to/archive/group-like-2.adoc'
            'headings': [('= Foobar', [23])]
        }]
        '''

        result = []

        paths = [p[0] for p in self.paths()]
        heading_regex = compile(self.config['archive_syntax']['headings'])

        for f in paths:

            headings = []

            with open(f, "r") as fx:
                searchlines = fx.readlines()

                for lineno, line in enumerate(searchlines):

                    heading_match = heading_regex.search(line)
                    if heading_match:
                        headings.append((heading_match.group(1), lineno))

            result.append({
                'file_name': f,
                'headings': headings
                })


        return result

    def pagerefs(self, paths_searched, expand_tocs=None, nonhierarchical_refs=None, fixed_lineno=None):
        '''
        only works with pageids, not sectionids or qids
        returns list of pagerefs defined in file
        self: paths considered for completion
        -> if they are not contained within there: error?
        paths_searched: paths where you look for pagerefs

        [{
            'file_name': '/path/to/archive/group-like-2.adoc',
            'pagerefs': [('graph-theory:fcd2cda, [23])]
            }]
        }]
        or
        [{
            'graph-theory:fcd2ca': [('/path/to/archive/group-like-2.adoc', [23])]
            'group-theory:fc3434': [('/path/to/archive/group-like-2.adoc', [23])]
        }]
        '''

        if nonhierarchical_refs is None or not nonhierarchical_refs:
            nonhierarchical_refs = False
        else:
            nonhierarchical_refs = True

        if expand_tocs is None or not expand_tocs:
            expand_tocs = False
        else:
            expand_tocs = True

        paths_under_consideration = [p[0] for p in self.paths()]
        pageref_regex = compile(self.config['archive_syntax']['pagerefs'])
        toc_regex = compile('^%s.*' % self.config['archive_syntax']['tocs'])
        result = []

        id_with_paths_searched = Identifier(self.config, preanalysis=self.analysis, uri=paths_searched)

        if not id_with_paths_searched.page_component:
            self.printer('needs page component')
        elif id_with_paths_searched.quest_component:
            self.printer('must not have quest component')

        for f in [t[0] for t in id_with_paths_searched.paths()]:
            pagerefs = []

            with open(f, "r") as fx:
                searchlines = fx.readlines()

                for lineno, line in enumerate(searchlines):

                    pageref_match = pageref_regex.search(line)
                    if pageref_match:

                        pageref_matched = pageref_match.group(1)

                        # dealing with further pagerefs
                        if pageref_matched.startswith('!'):
                            if nonhierarchical_refs:
                                pageref_matched = pageref_matched[1:]
                            else:
                                continue

                        prov_id = (pageref_matched
                                if not pageref_matched.startswith(':')
                                else os.path.basename(os.path.dirname(f)) + pageref_matched)

                        prov_identifier = Identifier(self.config, uri=prov_id, preanalysis=self.analysis)

                        file_name, pageref, _, _ = prov_identifier.paths()[0]

                        if expand_tocs and toc_regex.search(os.path.basename(file_name)):
                            inter_result = self.pagerefs(file_name, expand_tocs=True, nonhierarchical_refs=nonhierarchical_refs, fixed_lineno=lineno)
                            result += inter_result
                            continue

                        pagerefs.append((pageref, lineno if not fixed_lineno else fixed_lineno, file_name))

            result.append({
                'file_name': f,
                'pagerefs': pagerefs
                })

        return result

    def pagerefs_keyby(self, paths_searched, expand_tocs=None, nonhierarchical_refs=None, fixed_lineno=None):
        '''
        returns list of pagerefs defined in file
        self: paths considered for completion
        -> if they are not contained within there: error?
        paths_searched: paths where you look for pagerefs

        [{
            'graph-theory:fcd2ca': [('/path/to/archive/group-like-2.adoc', [23])]
            'group-theory:fc3434': [('/path/to/archive/group-like-2.adoc', [23])]
        }]
        '''

        if nonhierarchical_refs is None or not nonhierarchical_refs:
            nonhierarchical_refs = False
        else:
            nonhierarchical_refs = True

        if expand_tocs is None or not expand_tocs:
            expand_tocs = False
        else:
            expand_tocs = True

        paths_under_consideration = [p[0] for p in self.paths()]
        pageref_regex = compile(self.config['archive_syntax']['pagerefs'])
        toc_regex = compile('^%s.*' % self.config['archive_syntax']['tocs'])

        result = {}

        id_with_paths_searched = Identifier(self.config, preanalysis=self.analysis, uri=paths_searched)

        if not id_with_paths_searched.page_component:
            self.printer('needs page component')
        elif id_with_paths_searched.quest_component:
            self.printer('must not have quest component')

        for f in [t[0] for t in id_with_paths_searched.paths()]:
            with open(f, "r") as fx:
                searchlines = fx.readlines()

                for lineno, line in enumerate(searchlines):

                    pageref_match = pageref_regex.search(line)
                    if pageref_match:

                        pageref_matched = pageref_match.group(1)

                        # dealing with further pagerefs
                        if pageref_matched.startswith('!'):
                            if nonhierarchical_refs:
                                pageref_matched = pageref_matched[1:]
                            else:
                                continue

                        prov_id = pageref_matched if not pageref_matched.startswith(':') else os.path.basename(os.path.dirname(f)) + pageref_matched
                        prov_identifier = Identifier(self.config, uri=prov_id, preanalysis=self.analysis)

                        try:
                            file_name, pageref, _, _ = prov_identifier.paths()[0]
                        except:
                            self.printer('file contains invalid pageref')

                        if expand_tocs and toc_regex.search(os.path.basename(file_name)):
                            inter_result = self.pagerefs_keyby(file_name, expand_tocs=True, nonhierarchical_refs=nonhierarchical_refs, fixed_lineno=lineno)
                            print('inter_result: ' + inter_result)
                            ## TODO
                            continue

                        try:
                            result[pageref].append( (f, lineno if not fixed_lineno else fixed_lineno, file_name) )
                        except:
                            result[pageref] = []
                            result[pageref].append( (f, lineno if not fixed_lineno else fixed_lineno, file_name) )

        return result

    def revrefs(self, paths_searched, prepagerefs=None, forbidden_pagerefs=None, nonhierarchical_refs=None, k=None):
        '''
        traces back all pagerefs to a specific file
        self: paths considered for completion
        -> if they are not contained within there: error?
        paths_searched: paths that you trace back

        acts differently for content pages and tocs:
        * content pages are only traced back one step
        * tocs are traced back until the end

        prepageref: when called recursively, these is the previously
          evaluated result from pagerefs

        result := [{
            'pageref': '/path/to/archive/group-like-2.adoc',
            'traceback': [
                [('/path/to/toc', 23, 'pat)],
                [('/path/to/file', 99)],
                [('/path/to/toc2', 9), ('/path/to/toc', 23)],
                [('/path/to/toc3', 69), ('/path/to/toc', 23)],
                [('/path/to/tocX', 423), ('/path/to/toc3', 69), ('/path/to/toc', 23)]
            }]
        }]
        '''

        result = []

        if nonhierarchical_refs is None or not nonhierarchical_refs:
            nonhierarchical_refs = False
        else:
            nonhierarchical_refs = True

        if (k is -1 or k is None) and nonhierarchical_refs:
            k = 1
        elif (k is -1 or k is None) and not nonhierarchical_refs:
            k = 20

        paths = Identifier(self.config, uri=paths_searched, preanalysis=self.analysis, printer=self.printer)

        if not paths.page_component:
            self.printer('needs page component')
        elif paths.quest_component:
            self.printer('must not have quest component')

        for file_name, qid, _, _ in paths.paths():

            if k >= 1:
                if not prepagerefs:
                    pagerefs = self.pagerefs_keyby(paths_searched='@:@', nonhierarchical_refs=nonhierarchical_refs)
                else:
                    pagerefs = prepagerefs

                if not forbidden_pagerefs:
                    forbidden_pagerefs = []

                try:
                    pre_result = [[pr] for pr in pagerefs[qid]]
                except:
                    pre_result = []

                for val in pre_result:
                    if val in forbidden_pagerefs:
                        self.printer('cycle detected starting at: "' + str(paths_searched) +'"\n' + str(forbidden_pagerefs))

                add_result = []

                toc_regex = compile('^%s.*' % self.config['archive_syntax']['tocs'])

                for elem in pre_result:
                    if toc_regex.search(os.path.basename(elem[0][0])):

                        new_id = Identifier(self.config, uri=elem[0][0], preanalysis=self.analysis, printer=self.printer)
                        next_lookup =  self.revrefs(new_id.paths()[0][1], prepagerefs=pagerefs,
                                forbidden_pagerefs=pre_result + forbidden_pagerefs, k=k-1)

                        add_result += [ i + elem for i in next_lookup[0]['traceback'] ]

                traceback = pre_result + add_result

            else:
                traceback = []

            result.append({
                    'pageref': file_name,
                    'traceback': traceback
                    })

        return result

    def verify(self, test_uri, nonhierarchical_refs=True):
        '''
        returns list of integrity errors of files
        [{
            'file_name': '/path/to/archive/group-like-2.adoc'
            'errors': [{
                'type': 'duplicate_qid',
                'info': '03',
                'lineno': [23,34]
            }]
        }]
        '''

        test_id = Identifier(self.config, uri=test_uri, preanalysis=self.analysis)

        if not test_id.page_component:
            self.printer('needs page component')
            return []
        elif test_id.quest_component:
            self.printer('must not have quest component')
            return []

        test_paths = test_id.paths()

        duplicate_qids = []
        dangling_qidrefs = []
        dangling_pagerefs = []

        qid_regex = compile(self.config['archive_syntax']['qids'])
        qidref_regex = compile(self.config['archive_syntax']['qidrefs'])
        pageref_regex = compile(self.config['archive_syntax']['pagerefs'])

        result = []

        for f in test_paths:

            qids = []
            qidrefs = []
            pagerefs = []

            dangling_qidrefs = []
            dangling_pagerefs = []

            result.append({
                'file_name': f[0],
                'errors': [] })

            with open(f[0], "r") as fx:
                searchlines = fx.readlines()

                for lineno, line in enumerate(searchlines):

                    qid_match = qid_regex.search(line)
                    if qid_match:
                        qids.append((qid_match.group(1), lineno))

                    qidref_match = qidref_regex.search(line)
                    if qidref_match:
                        qidrefs.append((qidref_match.group(1), lineno))

                    pageref_match = pageref_regex.search(line)
                    if pageref_match:

                        pageref_matched = pageref_match.group(1)
                        # dealing with further pagerefs
                        if pageref_matched.startswith('!'):
                            if nonhierarchical_refs:
                                pageref_matched = pageref_matched[1:]
                            else:
                                continue


                        pagerefs.append((pageref_matched
                            if not pageref_matched.startswith(':')
                            else os.path.basename(os.path.dirname(f[0])) + pageref_matched, lineno))

                duplicate_qids = [qid[0] for qid in qids]
                unique_qids    = set(duplicate_qids)

                for qid in unique_qids:
                    duplicate_qids.remove(qid)

                for qidref in qidrefs:
                    if qidref[0] not in unique_qids:
                        dangling_qidrefs.append(qidref)

                for pageref in pagerefs:
                    fake_id = Identifier(self.config, uri=pageref[0], preanalysis=self.analysis, printer=lambda t: t)
                    if fake_id.failed:
                        dangling_pagerefs.append(pageref)

                list(filter(lambda e: e['file_name'] == f[0], result))[0]['errors'] += [{
                        'type': 'duplicate_qid',
                        'info': dupe,
                        'lineno': [entry[1] + 1 for entry in qids if entry[0] == dupe]
                    } for dupe in set(duplicate_qids)] + [{
                        'type': 'dangling_qidref',
                        'info': dangling_qidref[0],
                        'lineno': [dangling_qidref[1] + 1]
                    } for dangling_qidref in dangling_qidrefs] + [{
                        'type': 'dangling_pageref',
                        'info': dangling_pageref[0],
                        'lineno': [dangling_pageref[1] + 1]
                    } for dangling_pageref in dangling_pagerefs]

        return result

    def match(self, db, type=None):
        stats = self.stats(tocs=False)
        result = []

        if self.quest_component:

            queries = []
            for entry in stats:
                constructed_uri = Identifier.to_identifier(entry[0]) + '#' + entry[1]
                queries.append(' '.join(Identifier(self.config, uri=constructed_uri, preanalysis=self.analysis).query()))

            remote_qcounts, outsiders = db.anki_query_count(queries, check_against=self.query())
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            result = [[(t[0][0], t[0][1], t[1])
                for t in tuple(zip(stats, remote_qcounts))], [o for o in outsiders]]

        elif self.page_component:
            queries = []

            for entry in stats:
                constructed_uri = (self.filter_component + '//' if self.filter_component else '') + Identifier.to_identifier(entry[0])
                queries.append(' '.join(Identifier(self.config, uri=constructed_uri, preanalysis=self.analysis).query()))

            remote_qcounts, _ = db.anki_query_count(queries)
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            result = [[( (t[0][0], t[0][1], t[1]) )
                for t in tuple(zip(stats, remote_qcounts))], []]

        elif self.section_component:

            queries = []
            for entry in stats:
                constructed_uri = (self.filter_component + '//' if self.filter_component else '') + Identifier.to_identifier(entry[0])
                queries.append(' '.join(Identifier(self.config, uri=constructed_uri, preanalysis=self.analysis).query()))

            remote_qcounts, _ = db.anki_query_count(queries)
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            result = [[( (t[0][0], t[0][1], t[1]) )
                for t in tuple(zip(stats, remote_qcounts))], []]

        else:
            the_query = ' '.join(self.query())
            remote_qcount, _ = db.anki_query_count([the_query])

            if remote_qcount is None:
                self.printer('you probably need to select a profile')

            result = [[( (stats[0][0], stats[0][1], remote_qcount[0]) )], []]


        return result

    def query(self, option=0):
        result = []

        # toc in filter_component
        if ':' in self.filter_component:
            prep_ac = []

            for d in self.analysis:
                for f in d['files']:
                    prep_ac.append(
                        '"tag:{0}::{1}"'.format(os.path.basename(d['dir_name']),
                                                os.path.splitext(f['file_name'])[0]))

            ac = '(' + ' or '.join(prep_ac) + ')'

        # ancestor section in filter_component
        elif self.filter_component:

            prep_ac = []
            for d in self.analysis:
                prep_ac.append('tag:{0}::*'.format(os.path.basename(d['dir_name'])))

            ac = '(' + ' or '.join(prep_ac) + ')'

        else:
            ac = None

        section_comp = self.section_component.replace('@', '').replace('-', '*-') + '*' if self.section_component else '*'
        page_comp = self.page_component.replace('@', '') .replace('-', '*-') + '*' if self.page_component else '*'
        qc = self.quest_component.replace('@', '*') if self.quest_component else '*'

        if ac:
            result.append(ac)

        pageid_prefix = self.config['card_config']['pageid_prefix'] + '::' if self.config['card_config']['pageid_prefix'] else ''
        pageid_suffix = '::' + self.config['card_config']['pageid_suffix'] if self.config['card_config']['pageid_suffix'] else ''

        result.append('"tag:%s%s::%s%s"' % (pageid_prefix, section_comp, page_comp, pageid_suffix))

        if self.config['card_config']['qid_field']:
            result.append('"%s:*%s"' % (self.config['card_config']['qid_field'], qc))
        else:
            result.append('"nid:%s"' % (qc))

        return result
