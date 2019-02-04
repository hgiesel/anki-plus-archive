import enum
import os
import sys
import re
from re import compile
import copy

ARCHIVE_ROOT = os.environ['ARCHIVE_ROOT']

class Printer:
    @staticmethod
    def print_stats(vals, delimiter=None):
        '''pretty print values from Identifier:stats '''
        if delimiter is None:
            delimiter = '\t'

        lines = '\n'.join([ delimiter.join([ str(v) for v in list(val) ]) for val in vals ])
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
    def to_rel_path(path):
        '''
        can transform:
        abs_path -> rel path from archive root
        '''
        result = os.path.relpath(path, os.path.join(ARCHIVE_ROOT, '..'))
        return result

    @staticmethod
    def to_identifier(path, omit_section=None):
        '''
        can transform:
        abs_path -> section
        abs_path -> section:page
        abs_path -> :page
        '''

        if os.path.isdir(path):
            section = os.path.basename(path)
            result = section

        elif os.path.isfile(path):
            root, fileName = os.path.split(path)
            section = os.path.basename(root)
            page, _ = os.path.splitext(fileName)

            if omit_section:
                result = ':'+page
            else:
                result = section+':'+page

        return result


    def __init__(self, config, uri=None, preanalysis=None, printer=None, hypothetical=False):
        ''' (self) -> ([ResultDict], mode: Mode, summary_name: String)
        * Analzyes uri and returns one of the following:

        ** 'abstract-algebra<@'           -> (multiple dirs                ,~doesn't affect mode)
        ** 'abstract-algebra<'            -> (multiple dirs                ,~doesn't affect mode)

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

        self.failed = False

        component_regex = (# optional ancestor component
                           r'^(?:([^#/:]+)//)?'
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

        matches = re.search(component_regex, uri)

        # queries that don't need to check against the archive
        # e.g. for making match tests against Anki
        self.hypthetical = hypothetical

        if matches is not None:
            self.uri                = uri
            self.filter_component   = matches.group(1) or ''
            self.section_component  = matches.group(2) or ''
            self.page_component     = matches.group(3) or ''
            self.quest_component    = matches.group(4) or ''

            self.__decide_mode()

        else:
            self.printer('query malformed: invalid archive uri')
            self.failed = True

        if preanalysis:
            self.analysis = copy.deepcopy(preanalysis)
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
        summary_name = os.environ['ARCHIVE_ROOT']
        topics       = []

        self.failed = False

        '''
        processing of filter
        '''
        if self.filter_component:
            matched_ancestors = []
            ancestor_regex = re.compile('(.*/' + self.filter_component.replace('-','[^./]*-') + '[^-./]*)/?')

        first_dir = True
        toc_regex = re.compile('^README.*')

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
                    'dirName':   root,
                    'files': [{
                        'fileName': f,
                        'lines': []
                        } for f in content_pages],
                    'tocs': [{
                        'fileName': t,
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

        return (topics, summary_name)

    def __postfilter(self, topics):
        ''' returns filtered topic '''
        ''' processing of section topic '''

        if self.section_component and not self.section_component == '@':
            section_regex = re.compile('/' + self.section_component.replace('-','[^./]*-') + '[^./]*$')
            topics = list(filter(lambda t: section_regex.search(t['dirName']), topics))

            if len(topics) < 1:
                self.printer('no such section topic exists: "'+self.uri+'"')
                self.failed = True

            if len(topics) > 1:
                self.printer('section topic is ambiguous: '
                    + ' '.join(list(map(lambda t: os.path.basename(t['dirName']), topics))))
                self.failed = True

        ''' processing of page topic '''

        if len(topics):
            first_dir = topics[0]
        else:
            self.printer('no sections found')
            self.failed = True
            return {}

        if self.mode == Mode.PAGE_S or self.mode == Mode.QUEST_SA:
            page_regex = re.compile('^' + self.page_component[:-2].replace('-', '[^./]*-') + '[^-./]*\..*$')

            first_dir['files'] = list(filter(
                lambda f: page_regex.search(f['fileName']), first_dir['files']))
            first_dir['tocs'] = list(filter(
                lambda f: page_regex.search(f['fileName']), first_dir['tocs']))

        elif self.page_component and not self.page_component.endswith('@'):
            page_regex = re.compile('^' + self.page_component.replace('-', r'[^./]*-') + r'[^-./]*\..*$')
            first_dir['files'] = list(filter(
                lambda f: page_regex.search(f['fileName']), first_dir['files']))
            first_dir['tocs'] = list(filter(
                lambda f: page_regex.search(f['fileName']), first_dir['tocs']))

        if len(first_dir['files'] + first_dir['tocs']) < 1:
            self.printer('no such page topic exists: "' + self.uri + '"')
            self.failed = True

        # e.g. `gr-@` would hit `graphs-theory-1` and `groups-1`
        if self.page_component.endswith('-@') and len(first_dir['files'] + first_dir['tocs']) > 1:
            page_series = set(map(lambda f: re.search('(.*)-.*', f['fileName']).group(1), first_dir['files']))
            if len(page_series) > 1:
                self.printer('page topic series is ambiguous: '
                    + ' '.join(list(map(lambda s: os.path.basename(s), page_series))))
                self.failed = True

        elif self.page_component and not self.page_component == '@' and len(first_dir['files'] + first_dir['tocs']) > 1:
            self.printer('page topic is ambiguous: '
                + ' '.join(list(map(lambda f:
                    os.path.splitext(os.path.basename(f['fileName']))[0], first_dir['files'] + first_dir['tocs']) )))
            self.failed = True

        '''
        processing of quest identifier
        '''

        if self.quest_component:
            quest_id_regex = re.compile(r'^:(\d+)\a*:$')
            for d in topics:
                for f in d['files']:
                    with open(d['dirName']+'/'+f['fileName'], 'r') as stream:
                        searchlines = stream.readlines()
                        for idx, line in enumerate(searchlines):
                            quest_identifier = quest_id_regex.search(line)
                            if quest_identifier:
                                f['lines'].append({
                                    'lineno': idx,
                                    'quest': quest_identifier.group(1)})


        if self.mode == Mode.QUEST_I:
            first_dir  = topics[0]
            first_file = topics[0]['files'][0]

            # quest_id_regex = re.search(r'^:(%s)\a*:$', line)

            first_file['lines'] = list(filter(
                lambda l: l['quest'] == self.quest_component, first_file['lines']))

            if len(first_file['lines']) < 1:
                self.printer('no such quest identifier exists in file')
                self.failed = True

            elif len(first_file['lines']) > 1:
                self.printer('quest is ambiguous: '
                    + ' '.join(list(map(lambda f: os.path.basename(f['fileName']), first_file))))
                self.failed = True
                # should actually never happen

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
                os.path.normpath(os.path.join(d['dirName'], f['fileName'])),
                os.path.basename(d['dirName']) +':'+ os.path.splitext(f['fileName'])[0],
                l['lineno'], l['quest'] ))
                for d in self.analysis for ft in filetypes for f in d[ft] for l in f['lines']]

        elif self.page_component:
            result = [((
                os.path.normpath(os.path.join(d['dirName'], f['fileName'])),
                os.path.basename(d['dirName']) +':'+ os.path.splitext(f['fileName'])[0],
                None, None ))
                for d in self.analysis for ft in filetypes for f in d[ft]]

        elif self.section_component:
            result = [((
                os.path.normpath(d['dirName']),
                os.path.basename(d['dirName']),
                None, None ))
                for d in self.analysis]

        else:
            result.append(( os.path.normpath(self.summary_name), '', None, None ))

        return result

    def stats(self, preanalysis=None, fake_mode=None):
        ''' returns [(identifer, qid, lineno)] for files '''
        ''' returns [(identifer, count of qtags, count of content lines)] for qids '''

        filetypes = ['files', 'tocs']

        quest_id_regex = compile(r'^:([0-9]+):(?: \a*)?')
        content_line_regex = compile(
                # block titles
                r'^(\.[^. ]+|'
                # ordered list
                r'\.+ .+|'
                # unordered list
                r'\*+ .+|'
                # any lines starting with anything except those
                r'[^\n\'":=/\-+< ]+)')

        other_regexes = config['regexes']['stats']

        paths = self.paths()
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
                        if quest_id_regex.search(line):
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
                str(sum(map(lambda l: int(l[1]), a))),
                str(sum(map(lambda l: int(l[2]), a))) )
                for d, a in analyses ]
                # TODO generalize to accepts any amount of stats

        else:
            # all_stats = self.stats( (topics,''), Mode.PAGE_A )
            fake_stats = Identifier(self.config, uri='@:@', preanalysis=self.analysis).stats()
            result = [( self.summary_name,
                str(sum(map(lambda l: int(l[1]), fake_stats))),
                str(sum(map(lambda l: int(l[2]), fake_stats))) )]
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
            'fileName': '/path/to/archive/group-like-2.adoc'
            'headings': [('= Foobar', [23])]
        }]
        '''

        result = []

        paths = [p[0] for p in self.paths()]
        heading_regex = re.compile('^=(?: )?(.*)$')

        for f in paths:

            headings = []

            with open(f, "r") as fx:
                searchlines = fx.readlines()

                for lineno, line in enumerate(searchlines):

                    heading_match = heading_regex.search(line)
                    if heading_match:
                        headings.append((heading_match.group(1), lineno))

            result.append({
                'fileName': f,
                'headings': headings
                })


        return result

    def pagerefs(self):
        if not self.page_component:
            self.printer('needs page component')
        elif self.quest_component:
            self.printer('must not have quest component')
        else:
            return self._pagerefs()

    def _pagerefs(self, key_by=None):
        '''
        returns list of pagerefs defined in file
        [{
            'fileName': '/path/to/archive/group-like-2.adoc',
            'pagerefs': [('graph-theory:fcd2cda, [23])]
            }]
        }]
        '''

        '''
        or
        [{
            'graph-theory:fcd2ca': [('/path/to/archive/group-like-2.adoc', [23])
            'group-theory:fc3434': [('/path/to/archive/group-like-2.adoc', [23])
        }]
        '''

        paths = [p[0] for p in self.paths()]
        pageref_regex = re.compile('<<([^,]+)(?:,.*)?>>')

        if key_by:
            result = {}

            for f in paths:
                with open(f, "r") as fx:
                    searchlines = fx.readlines()

                    for lineno, line in enumerate(searchlines):

                        pageref_match = pageref_regex.search(line)
                        if pageref_match:

                            provisional_id = pageref_match.group(1)
                            fileName = Identifier(provisional_id
                                    if not provisional_id.startswith(':')
                                    else os.path.basename(os.path.dirname(f))+provisional_id).paths()[0][0]

                            dirName, baseName = os.path.split(fileName)
                            pageref = ':'.join([os.path.basename(dirName), os.path.splitext(baseName)[0]])

                            try:
                                result[pageref].append( (f, lineno) )
                            except:
                                result[pageref] = []
                                result[pageref].append( (f, lineno) )

        else:
            result = []

            for f in paths:
                pagerefs = []

                with open(f, "r") as fx:
                    searchlines = fx.readlines()

                    for lineno, line in enumerate(searchlines):

                        pageref_match = pageref_regex.search(line)
                        if pageref_match:

                            provisional_id = pageref_match.group(1)
                            fileName, _ = Identifier(provisional_id
                                    if not provisional_id.startswith(':')
                                    else os.path.basename(os.path.dirname(f))+provisional_id).paths()[0]

                            dirName, baseName = os.path.split(fileName)
                            pageref = ':'.join([os.path.basename(dirName), os.path.splitext(baseName)[0]])

                            pagerefs.append((pageref, lineno))

                result.append({
                    'fileName': f,
                    'pagerefs': pagerefs
                    })


        return result

    def revpagerefs(self):
        if not self.page_component:
            self.printer('needs page component')
        elif self.quest_component:
            self.printer('must not have quest component')
        else:
            return self._revpagerefs()

    def _revpagerefs(self, uri='', prepagerefs=None):
        '''
        traces back all pagerefs to a specific file
        [{
            'pageref': '/path/to/archive/group-like-2.adoc',
            'traceback': [
                [('/path/to/toc', 23)],
                [('/path/to/file', 99)],
                [('/path/to/toc2', 9), ('/path/to/toc', 23)],
                [('/path/to/toc3', 69), ('/path/to/toc', 23)],
                [('/path/to/tocX', 423), ('/path/to/toc3', 69), ('/path/to/toc', 23)]
            }]
        }]

        uri: the uri you want to trace back till
        acts differently for content pages and tocs:
        * content pages are only traced back one step
        * tocs are traced back until the end
        '''

        result = []

        file_name, _ = self.paths()[0]
        tag = Identifier.to_identifier(file_name)

        if not prepagerefs:
            pagerefs = Identifier('@:@')._pagerefs(key_by=True)
        else:
            pagerefs = prepagerefs

        try:
            pre_result= [[pr] for pr in pagerefs[tag]]
        except:
            pre_result = []

        add_result = []

        toc_regex = re.compile('^README.*')
        for elem in pre_result:
            if toc_regex.search(os.path.basename(elem[0][0])):

                new_id = Identifier((Identifier.to_identifier(elem[0][0])))
                # print('new id: '+ str(new_id.paths()))
                next_lookup =  new_id._revpagerefs(uri=uri, prepagerefs=pagerefs)
                # print('new lookup: ' + str(next_lookup))
                add_result += [ i + elem for i in next_lookup['traceback'] ]


        result = {
                'pageref': file_name,
                'traceback': pre_result + add_result
                }

        return result

    def verify(self, test_uri):
        '''
        returns list of integrity errors of files
        [{
            'fileName': '/path/to/archive/group-like-2.adoc'
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

        qid_regex = re.compile(self.config['regexes']['qids'])
        qidref_regex = re.compile(self.config['regexes']['qidrefs'])
        pageref_regex = re.compile(self.config['regexes']['pagerefs'])

        result = []

        for f in test_paths:

            qids = []
            qidrefs = []
            pagerefs = []

            dangling_qidrefs = []
            dangling_pagerefs = []

            result.append({
                'fileName': f[0],
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
                        pagerefs.append((pageref_match.group(1)
                            if not pageref_match.group(1).startswith(':')
                            else os.path.basename(os.path.dirname(f[0])) + pageref_match.group(1), lineno))

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

                list(filter(lambda e: e['fileName'] == f[0], result))[0]['errors'] += [{
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



    def query(self, validate=False, type='anki'):
        if validate:
            analyzee = self.__analyze()
        else:
            analyzee = None

        result = []
        result.append('card:1')


        pc = self.section_component.replace('@', '').replace('-', '*-') + '*' if self.section_component else '*'
        lc = self.page_component.replace('@', '').replace('-', '*-') + '*' if self.section_component else '*'
        qc = self.quest_component.replace('@', '*') if self.section_component else '*'

        result.append('tag:' + pc + '::' + lc)
        result.append('Quest:'+ '"*' + ':' + qc +':' +'*"')

        return result

    def match(self, db, type=None):

        stats = self.stats()
        result = []

        if self.mode in [Mode.QUEST_I, Mode.QUEST_SA, Mode.QUEST_A, Mode.QUEST_B, Mode.QUEST_C]:

            queries = []
            for entry in stats:
                if self.mode == Mode.QUEST_C:
                    constructed_quest = entry[1]
                    constructed_section, constructed_page = Identifier.to_identifier(entry[0]).split(':')
                else:
                    constructed_quest = entry[1]
                    constructed_section, constructed_page = self.section_component, entry[0]

                constructed_uri = constructed_section + ':' + constructed_page + '#' + constructed_quest
                queries.append(' '.join(Identifier(constructed_uri).query()))

            remote_qcounts, outsiders = db.anki_query_count(queries, check_against=self.query())
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            result += [(t[0][0], t[0][1], t[1]) for t in tuple(zip(stats, remote_qcounts))]
            result += [o for o in outsiders]

        elif self.mode in [Mode.PAGE_I, Mode.PAGE_S, Mode.PAGE_A, Mode.PAGE_B]:

            queries = []
            for entry in stats:
                if self.mode == Mode.PAGE_B:
                    constructed_section, constructed_page = Identifier.to_identifier(entry[0]).split(':')
                else:
                    constructed_section, constructed_page = self.section_component, entry[0]

                constructed_uri = constructed_section + ':' + constructed_page
                queries.append(' '.join(Identifier(constructed_uri).query()))

            remote_qcounts, _ = db.anki_query_count(queries)
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            for t in tuple(zip(stats, remote_qcounts)):
                result.append( (t[0][0], t[0][1], t[1]) )

        elif self.mode in [Mode.SECTION_I, Mode.SECTION_A]:

            queries = []
            for entry in stats:
                queries.append(' '.join(Identifier(Identifier.to_identifier(entry[0])).query()))

            remote_qcounts, _ = db.anki_query_count(queries)
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            for t in tuple(zip(stats, remote_qcounts)):
                result.append( (t[0][0], t[0][1], t[1]) )

        elif self.mode in [Mode.ARCHIVE]:
            remote_qcount, _ = db.anki_query_count([' '.join(self.query())])
            if remote_qcount is None:
                self.printer('you probably need to select a profile')
            result.append( (stats[0][0], stats[0][1], remote_qcount[0]) )

        return result
