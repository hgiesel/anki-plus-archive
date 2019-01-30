import enum
import os
import sys
import re
from re import compile

ARCHIVE_ROOT = os.environ['ARCHIVE_ROOT']

class Printer:
    @staticmethod
    def print_stats(vals, delimiter=None):
        '''pretty print values from ArkUri:stats '''
        if delimiter is None:
            delimiter = '\t'

        for val in vals:
                line = delimiter.join([
                        str(v) for v in list(val) ])

                print(line)

class Mode(enum.Enum):
    ''' modes for ArkUri.__analyze '''
    ANCESTOR = enum.auto()

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


    def __init__(self, uri=None, printer=None, hypothetical=False):
        ''' (self) -> ([ResultDict], mode: Mode, summary_name: String)
        * Analzyes uri and returns one of the following:

        ** 'abstract-algebra<@'           -> (multiple dirs                ,~doesn't affect mode)
        ** 'abstract-algebra<'            -> (multiple dirs                ,~doesn't affect mode)

        ** ''                             -> (multiple dirs                 ,ANCESTOR)

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
            self.ancestor_component = matches.group(1) or ''
            self.section_component  = matches.group(2) or ''
            self.page_component     = matches.group(3) or ''
            self.quest_component    = matches.group(4) or ''

            tempMode = Mode.ANCESTOR

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

            # print('ancestor: ' + self.ancestor_component)
            # print('section: ' + self.section_component)
            # print('page: '    + self.page_component)
            # print(self.quest_component)

        else:
            self.printer('query malformed: invalid archive uri')

        if not hypothetical:
            self.analysis = self.__analyze()

    def __analyze(self):
        summary_name = os.environ['ARCHIVE_ROOT']
        topics       = []

        self.failed = False

        '''
        processing of ancestor topic
        '''
        if self.ancestor_component:
            matched_ancestors = []
            ancestor_regex = re.compile('(.*/' + self.ancestor_component.replace('-','[^./]*-') + '[^./]*)/')

        readme_regex = re.compile('^README\..*')
        for root, dirs, files in os.walk(summary_name):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            files[:] = [f for f in files if not f.startswith('.')]

            if self.ancestor_component:
                match = ancestor_regex.search(root)
                if any([readme_regex.search(file) for file in files]) and root is not summary_name and match:
                    topics.append({
                        'dirName':   root,
                        'files': [{'fileName': file, 'lines': []} for file in files if not readme_regex.search(file)]})
                    matched_ancestors.append(match.group(1))
            else:
                if any([readme_regex.search(file) for file in files]) and root is not summary_name:
                    topics.append({
                        'dirName':   root,
                        'files': [{'fileName': file, 'lines':[]} for file in files if not readme_regex.search(file)]})

        if self.ancestor_component:
            unique_ancestors = set(matched_ancestors)

            if len(unique_ancestors) < 1:
                self.printer('no such ancestor topic exists')
                self.failed = True

            if len(unique_ancestors) > 1:
                self.printer('ancestor topic is ambiguous: ' +
                    ' '.join(map(lambda d: os.path.basename(d), unique_ancestors)))
                self.failed = True

            summary_name = unique_ancestors.pop()

        '''
        processing of section topic
        '''
        if self.section_component and not self.section_component == '@':
            section_regex = '/' + self.section_component.replace('-','[^./]*-') + '[^./]*$'
            topics = list(filter(lambda t: re.search(section_regex, t['dirName']), topics))

            if len(topics) < 1:
                self.printer('no such section topic exists: "'+self.section_component+'"')
                self.failed = True

            if len(topics) > 1:
                self.printer('section topic is ambiguous: '
                    + ' '.join(list(map(lambda t: os.path.basename(t['dirName']), topics))))
                self.failed = True

        '''
        processing of page topic
        '''

        if len(topics):
            first_dir = topics[0]
        else:
            self.printer('no sections found')
            self.failed = True
            return ({}, summary_name)

        if self.mode == Mode.PAGE_S or self.mode == Mode.QUEST_SA:
            page_regex = '^' + self.page_component[:-2].replace('-', '[^./]*-') + '[^./]*\..*$'
            first_dir['files'] = list(filter(
                lambda f: re.search(page_regex, f['fileName']), first_dir['files']))

        elif self.page_component and not self.page_component.endswith('@'):
            page_regex = '^' + self.page_component.replace('-', r'[^./]*-') + r'[^./]*\..*$'
            first_dir['files'] = list(filter(
                lambda f: re.search(page_regex, f['fileName']), first_dir['files']))

        if len(first_dir['files']) < 1:
            self.printer('no such page topic exists: "' + self.page_component + '"')
            self.failed = True

        # e.g. `gr-@` would hit `graphs-theory-1` and `groups-1`
        if self.page_component.endswith('-@') and len(first_dir['files']) > 1:
            page_series = set(map(lambda f: re.search('(.*)-.*', f['fileName']).group(1), first_dir['files']))
            if len(page_series) > 1:
                self.printer('page topic series is ambiguous: '
                    + ' '.join(list(map(lambda s: os.path.basename(s), page_series))))
                self.failed = True

        elif self.page_component and not self.page_component == '@' and len(first_dir['files']) > 1:
            self.printer('page topic is ambiguous: '
                + ' '.join(list(map(lambda f:
                    os.path.splitext(os.path.basename(f['fileName']))[0], first_dir['files']) )))
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

        '''
        constructing the result
        '''

        return (topics, summary_name)

    def paths(self):
        '''
        returns list of dirs, files, or files with linenos
        '''
        topics, summary_name = self.analysis
        result = []

        if self.mode in [Mode.QUEST_C, Mode.QUEST_B, Mode.QUEST_SA, Mode.QUEST_A, Mode.QUEST_I]:
            for d in topics:
                for f in d['files']:
                    for l in f['lines']:
                        result.append(( os.path.normpath(os.path.join(d['dirName'], f['fileName'])), l['lineno'] ))

        elif self.mode in [Mode.PAGE_B, Mode.PAGE_A, Mode.PAGE_S, Mode.PAGE_I]:
            for d in topics:
                for f in d['files']:
                    result.append(( os.path.normpath(os.path.join(topics[0]['dirName'], f['fileName'])), None ))

        elif self.mode in [Mode.SECTION_A, Mode.SECTION_I]:
            for d in topics:
                result.append(( os.path.normpath(d['dirName']), None ))

        elif self.mode in [Mode.ANCESTOR]:
            result.append(( os.path.normpath(summary_name), None ))

        else:
            self.printer('should-never-happen error')

        return result

    def stats(self, preanalyzed=None, fakeMode=None):
        ''' returns list of (identifer, qid, lineno) '''
        ''' returns list of (identifer, count of qtags, count of content lines) '''

        topics, summary_name = preanalyzed if preanalyzed is not None else self.analysis
        mode = fakeMode if fakeMode is not None else self.mode

        quest_id_regex = compile(r'^:(\d+)\a*:$')
        content_line_regex = compile(
                # block titles
                r'^(\.[^. ]+|'
                # ordered list
                r'\.+ .+|'
                # unordered list
                r'\*+ .+|'
                # any lines starting with anything except those
                r'[^\n\'":=/\-+< ]+)')

        other_regexes = [
                content_line_regex
                ]

        result = []

        if mode in [Mode.QUEST_I, Mode.QUEST_A, Mode.QUEST_SA, Mode.QUEST_B, Mode.QUEST_C]:
            for d in topics:
                for f in d['files']:
                    for l in f['lines']:

                        result.append((
                            os.path.normpath(os.path.join(d['dirName'], f['fileName'])),
                            l['quest'],
                            l['lineno'] ))

        elif mode in [Mode.PAGE_I, Mode.PAGE_S, Mode.PAGE_A, Mode.PAGE_B]:

            for d in topics:
                for f in d['files']:

                    qid_count = 0
                    other_counts = [0] * len(other_regexes)

                    with open(d['dirName']+'/'+f['fileName'], "r") as fx:
                        searchlines = fx.readlines()
                        for _, line in enumerate(searchlines):
                            if quest_id_regex.search(line):
                                qid_count += 1

                            for idx, re in enumerate(other_regexes):
                                if re.search(line):
                                    other_counts[idx] += 1

                        result.append((
                            os.path.normpath(os.path.join(d['dirName'], f['fileName'])),
                            qid_count) + tuple(other_counts))

        elif mode in [Mode.SECTION_I, Mode.SECTION_A]:

            for d in topics:
                all_stats = self.stats( ([d],''), Mode.PAGE_A )
                result.append((
                    os.path.normpath(d['dirName']),
                    str(sum(map(lambda l: int(l[1]), all_stats))),
                    str(sum(map(lambda l: int(l[2]), all_stats))) ))
                # TODO generalize to accepts any amount of stats

        elif mode in [Mode.ANCESTOR]:

            all_stats = self.stats( (topics,''), Mode.PAGE_A )
            result.append((
                os.path.normpath(summary_name),
                str(sum(map(lambda l: int(l[1]), all_stats))),
                str(sum(map(lambda l: int(l[2]), all_stats))) ))
            # TODO generalize to accepts any amount of stats

        else:
            self.printer('should-never-happen error')

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
            'headings': [{
                'info': '= Foobar',
                'lineno': [23]
            }]
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

    def verify(self):
        if not self.page_component:
            self.printer('needs page component')
        elif self.quest_component:
            self.printer('must not have quest component')
        else:
            return self._verify()

    def _verify(self):
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

        paths = [p[0] for p in self.paths()]

        duplicate_qids = []
        dangling_qid_references = []
        dangling_page_references = []

        qid_regex = re.compile('^:([0-9]+):(?: .*)?$')
        qid_ref_regex = re.compile('^:ext:([0-9]+):(?: .*)?$')
        page_ref_regex = re.compile('<<([^,]+)(?:,.*)?>>')

        result = []

        for f in paths:

            qids = []
            qid_refs = []
            page_refs = []

            dangling_qid_references = []
            dangling_page_references = []

            result.append({
                'fileName': f,
                'errors': [] })

            with open(f, "r") as fx:
                searchlines = fx.readlines()

                for lineno, line in enumerate(searchlines):

                    qid_match = qid_regex.search(line)
                    if qid_match:
                        qids.append((qid_match.group(1), lineno))

                    qid_ref_match = qid_ref_regex.search(line)
                    if qid_ref_match:
                        qid_refs.append((qid_ref_match.group(1), lineno))

                    page_ref_match = page_ref_regex.search(line)
                    if page_ref_match:
                        page_refs.append((page_ref_match.group(1), lineno))

                duplicate_qids = [qid[0] for qid in qids]
                unique_qids    = set(duplicate_qids)

                for qid in unique_qids:
                    duplicate_qids.remove(qid)

                for qid_ref in qid_refs:
                    if qid_ref[0] not in unique_qids:
                        dangling_qid_references.append(qid_ref)

                for page_ref in page_refs:
                    id = Identifier(uri=page_ref[0], printer=lambda _: ())
                    if id.failed:
                        dangling_page_references.append(page_ref)

                list(filter(lambda e: e['fileName'] == f, result))[0]['errors'] += [{
                        'type': 'duplicate_qid',
                        'info': dupe,
                        'lineno': [entry[1] + 1 for entry in qids if entry[0] == dupe]
                    } for dupe in set(duplicate_qids)] + [{
                        'type': 'dangling_qid_reference',
                        'info': dangling_qid_ref[0],
                        'lineno': [dangling_qid_ref[1] + 1]
                    } for dangling_qid_ref in dangling_qid_references] + [{
                        'type': 'dangling_page_reference',
                        'info': dangling_page_ref[0],
                        'lineno': [dangling_page_ref[1] + 1]
                    } for dangling_page_ref in dangling_page_references]

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
                    constructed_section, constructed_page = entry[0].split(':')
                else:
                    constructed_quest = entry[1]
                    constructed_section, constructed_page = self.section_component, entry[0]

                constructed_uri = constructed_section + ':' + constructed_page + '#' + constructed_quest
                queries.append(' '.join(ArkUri(constructed_uri).query()))

            remote_qcounts, outsiders = db.anki_query_count(queries, check_against=self.query())
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            result += [(t[0][0], t[0][1], t[1]) for t in tuple(zip(stats, remote_qcounts))]
            result += [o for o in outsiders]

        elif self.mode in [Mode.PAGE_I, Mode.PAGE_S, Mode.PAGE_A, Mode.PAGE_B]:

            queries = []
            for entry in stats:
                if self.mode == Mode.PAGE_B:
                    constructed_section, constructed_page = entry[0].split(':')
                else:
                    constructed_section, constructed_page = self.section_component, entry[0]

                constructed_uri = constructed_section + ':' + constructed_page
                queries.append(' '.join(ArkUri(constructed_uri).query()))

            remote_qcounts, _ = db.anki_query_count(queries)
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            for t in tuple(zip(stats, remote_qcounts)):
                result.append( (t[0][0], t[0][1], t[1]) )

        elif self.mode in [Mode.SECTION_I, Mode.SECTION_A]:

            queries = []
            for entry in stats:
                queries.append(' '.join(ArkUri(entry[0]).query()))

            remote_qcounts, _ = db.anki_query_count(queries)
            if remote_qcounts is None:
                self.printer('you probably need to select a profile')

            for t in tuple(zip(stats, remote_qcounts)):
                result.append( (t[0][0], t[0][1], t[1]) )

        elif self.mode in [Mode.ANCESTOR]:
            remote_qcount, _ = db.anki_query_count([' '.join(self.query())])
            if remote_qcount is None:
                self.printer('you probably need to select a profile')
            result.append( (stats[0][0], stats[0][1], remote_qcount[0]) )

        return result
