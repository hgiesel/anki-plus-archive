#!/usr/bin/env python3
import re
import enum
import argparse
import os
import sys
import json
import urllib.request

content_lines = (# block titles
        r'^(\.[^. ]+|'
        # ordered list
        r'\.+ .+|'
        # unordered list
        r'\*+ .+|'
        # any lines starting with anything except those
        r'[^\n\'":=/\-+< ]+)'
        )

def ark():
    print(
'''
ark() {
  local entry
arr="$(quiet=errors arkutil paths "$1")"
exitstatus=$?
   [[ ! $exitstatus == '0' ]] && return $exitstatus
read -a entry <<< "${arr[@]}"

if [[ -d ${entry} ]]; then
  cd "$entry"

  elif [[ -f ${entry} ]]; then
    $EDITOR "${entry}"

  elif [[ ${entry} =~ ^(.*):(.*): ]]; then
    $EDITOR "${BASH_REMATCH[1]}" +${BASH_REMATCH[2]} -c 'normal! zz'
  fi
}

alias hasq="awk '{ if(\$2 != 0) { print \$0 } }'"
alias noq="awk '{ if(\$2 == 0) { print \$0 } }'"

alias nomatch="awk '{ if(\$2 != \$3 ) { print \$0 } }'"
alias miss="awk '{ if(\$3 != 1) { print \$0 } }'"
''')

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

class ArkPrinter:
    @staticmethod
    def print_stats(vals):
        '''pretty print values from ArkUri:stats '''
        for val in vals:
            print('\t'.join([str(v) for v in list(val)]))

    @staticmethod
    def print_paths(vals):
        '''prints values from ArkUri:paths '''
        for val in vals:
            file_name, lineno = val
            if lineno is not None:
                print('{0}:{1}:'.format(file_name, lineno))
            else:
                print(file_name)

class ArkUri:
    def __init__(self, uri='', hypothetical=False):
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

                if self.page_component == '@':
                    if tempMode == Mode.SECTION_A:
                        tempMode = Mode.PAGE_B

                    elif tempMode == Mode.SECTION_I:
                        tempMode = Mode.PAGE_A

                    else:
                        theparser.error('query malformed: cannot use page topics without definite section topic or @')

                elif tempMode == Mode.SECTION_I and self.page_component.endswith('-@') and len(self.page_component) >= 3:
                    tempMode = Mode.PAGE_S

                elif tempMode == Mode.SECTION_I:
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
                    theparser.error('query malformed: cannot use quest identifers without definite page topic or @')

            self.mode = tempMode

        else:
            theparser.error('query malformed: invalid archive uri')

        if ARGV.debug:
            print('ancestor: {}\nsection: {}\npage: {}\nmode: {}'.format(
                   self.ancestor_component,
                   self.section_component,
                   self.page_component,
                   self.mode))

    def __analyze(self):

        summary_name = os.environ['ARCHIVE_ROOT']
        topics      = []

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
                theparser.error('no such ancestor topic exists')

            if len(unique_ancestors) > 1:
                theparser.error('ancestor topic is ambiguous: ' +
                    ' '.join(map(lambda d: os.path.basename(d), unique_ancestors)))

            summary_name = unique_ancestors.pop()

        '''
        processing of section topic
        '''
        if self.section_component and not self.section_component == '@':
            section_regex = '/' + self.section_component.replace('-','[^./]*-') + '[^./]*$'
            topics = list(filter(lambda t: re.search(section_regex, t['dirName']), topics))

            if len(topics) < 1:
                theparser.error('no such section topic exists')

            if len(topics) > 1:
                theparser.error('section topic is ambiguous: '
                    + ' '.join(list(map(lambda t: os.path.basename(t['dirName']), topics))))

        '''
        processing of page topic
        '''

        first_dir = topics[0]


        if self.mode == Mode.PAGE_S or self.mode == Mode.QUEST_SA:
            page_regex = '^' + self.page_component[:-2].replace('-', '[^./]*-') + '[^./]*\..*$'
            first_dir['files'] = list(filter(
                lambda f: re.search(page_regex, f['fileName']), first_dir['files']))

        elif self.page_component and not self.page_component.endswith('@'):
            page_regex = '^' + self.page_component.replace('-', r'[^./]*-') + r'[^./]*\..*$'
            first_dir['files'] = list(filter(
                lambda f: re.search(page_regex, f['fileName']), first_dir['files']))

        if len(first_dir['files']) < 1:
            theparser.error('no such page topic exists')

        # e.g. `gr-@` would hit `graphs-theory-1` and `groups-1`
        if self.page_component.endswith('-@') and len(first_dir['files']) > 1:
            page_series = set(map(lambda f: re.search('(.*)-.*', f['fileName']).group(1), first_dir['files']))
            if len(page_series) > 1:
                theparser.error('page topic series is ambiguous: '
                    + ' '.join(list(map(lambda s: os.path.basename(s), page_series))))

        elif self.page_component and not self.page_component == '@' and len(first_dir['files']) > 1:
            theparser.error('page topic is ambiguous: '
                + ' '.join(list(map(lambda f:
                    os.path.splitext(os.path.basename(f['fileName']))[0], first_dir['files']) )))

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
                theparser.error('no such quest identifier exists in file')

            elif len(first_file['lines']) > 1:
                theparser.error('quest is ambiguous: '
                    + ' '.join(list(map(lambda f: os.path.basename(f['fileName']), first_file))))
                # should actually never happen

        '''
        constructing the result
        '''

        return (topics, summary_name)

    def paths(self):
        '''
        returns list of dirs, files, or files with linenos
        '''
        topics, summary_name = self.__analyze()
        result = []

        if self.mode in [Mode.QUEST_C, Mode.QUEST_B, Mode.QUEST_SA, Mode.QUEST_A, Mode.QUEST_I]:
            for d in topics:
                for f in d['files']:
                    for l in f['lines']:
                        result.append( (d['dirName'] + '/' + f['fileName'], l['lineno']) )

        elif self.mode in [Mode.PAGE_B, Mode.PAGE_A, Mode.PAGE_S, Mode.PAGE_I]:
            for d in topics:
                for f in d['files']:
                    result.append( (topics[0]['dirName']+'/'+f['fileName'], None) )

        elif self.mode in [Mode.SECTION_A, Mode.SECTION_I]:
            for d in topics:
                result.append( (d['dirName'],None) )

        elif self.mode in [Mode.ANCESTOR]:
            result.append( (summary_name,None) )

        else:
            theparser.error('should-never-happen error')

        return result

    def stats(self, preanalyzed=None, fakeMode=None):
        '''
        returns list of (identifer, count of content lines, count of qtags)
        '''
        topics, summary_name = preanalyzed if preanalyzed is not None else self.__analyze()
        mode = fakeMode if fakeMode is not None else self.mode

        result = []

        if mode in [Mode.QUEST_I, Mode.QUEST_A, Mode.QUEST_SA, Mode.QUEST_B, Mode.QUEST_C]:
            for d in topics:
                for f in d['files']:
                    for l in f['lines']:

                        display_name = ''
                        if len(topics) == 1:
                            display_name = os.path.splitext(f['fileName'])[0]
                        else:
                            display_name = os.path.basename(d['dirName']) + ':' + os.path.splitext(f['fileName'])[0]

                        result.append( (display_name,
                            l['quest'],
                            l['lineno']) )

        elif mode in [Mode.PAGE_I, Mode.PAGE_S, Mode.PAGE_A, Mode.PAGE_B]:


            content_line_regex = re.compile(content_lines)
            quest_id_regex = re.compile(r'^:(\d+)\a*:$')

            for d in topics:
                for f in d['files']:

                    quest_count = 0
                    content_line_count = 0

                    display_name = ''
                    if len(topics) == 1:
                        display_name = os.path.splitext(f['fileName'])[0]
                    else:
                        display_name = os.path.basename(d['dirName']) + ':' + os.path.splitext(f['fileName'])[0]

                    with open(d['dirName']+'/'+f['fileName'], "r") as fx:
                        searchlines = fx.readlines()
                        for _, line in enumerate(searchlines):
                            if quest_id_regex.search(line):
                                quest_count += 1
                            elif content_line_regex.search(line):
                                content_line_count += 1

                        result.append( (display_name,
                            quest_count,
                            content_line_count) )

        elif mode in [Mode.SECTION_I, Mode.SECTION_A]:

            for d in topics:
                all_stats = self.stats( ([d],''), Mode.PAGE_A )
                result.append((os.path.basename(d['dirName']),
                    str(sum(map(lambda l: int(l[1]), all_stats))),
                    str(sum(map(lambda l: int(l[2]), all_stats)))))

        elif mode in [Mode.ANCESTOR]:

            all_stats = self.stats( (topics,''), Mode.PAGE_A )
            result.append((os.path.basename(summary_name),
                str(sum(map(lambda l: int(l[1]), all_stats))),
                str(sum(map(lambda l: int(l[2]), all_stats)))))

        else:
            theparser.error('should-never-happen error')

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

            # print('### outsider ' + str(outsiders))

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

            for t in tuple(zip(stats, remote_qcounts)):
                result.append( (t[0][0], t[0][1], t[1]) )

        elif self.mode in [Mode.SECTION_I, Mode.SECTION_A]:

            queries = []
            for entry in stats:
                queries.append(' '.join(ArkUri(entry[0]).query()))

            remote_qcounts, _ = db.anki_query_count(queries)

            for t in tuple(zip(stats, remote_qcounts)):
                result.append( (t[0][0], t[0][1], t[1]) )

        elif self.mode in [Mode.ANCESTOR]:
            remote_qcount, _ = db.anki_query_count([' '.join(self.query())])
            result.append( (stats[0][0], stats[0][1], remote_qcount[0]) )

        return result

class AnkiConnection:
    def __init__(self, port=8765, deck_name=None, quest_field_name=None, quest_id_regex=None):
        '''setup connection to anki'''
        self.req = urllib.request.Request('http://localhost:' + str(port))
        self.req.add_header('Content-Type', 'application/json; charset=utf-8')

        self.quest_field_name = quest_field_name
        self.quest_id_regex = quest_id_regex
        self.deck_name = deck_name

    def anki_add(self, json):
        pass

    def anki_query_check_against(self, resps, check_against):

        check_against_query = ' '.join(check_against) + ' deck:{0}*'.format(self.deck_name)

        check_against_req = json.dumps({
            'action': 'findNotes',
            'version': 6,
            'params': {
                'query': check_against_query
                }
            }).encode('utf-8')


        check_against_resp = urllib.request.urlopen(self.req, check_against_req)
        check_against_json = json.loads(check_against_resp.read().decode('utf-8'))

        check_against_filtered = [entry for entry in check_against_json['result'] if not entry in resps]

        if len(check_against_filtered):
            outsider_info_query = json.dumps({
                "action": "notesInfo",
                "version": 6,
                "params": {
                    "notes": check_against_filtered
                    }
                }).encode('utf-8')

            outsider_info_resp = urllib.request.urlopen(self.req, outsider_info_query)
            outsider_info_json = json.loads(outsider_info_resp.read().decode('utf-8'))

            tags = [list(filter(lambda tag: re.match('.*::.*', tag), entry['tags']))
                for entry in outsider_info_json['result']]

            displayed_tags = [ ':'.join(re.match('(.*)::(.*)', ts[0]).groups())
                if len(ts) == 1 else '???:???' for ts in tags]

            quest_fields = [entry['fields'][self.quest_field_name]['value']
                for entry in outsider_info_json['result']]

            quest_ids = [re.sub('(?:<[^>]*>)*?' + self.quest_id_regex + '.*', r'\g<1>', entry)
                for entry in quest_fields]

            zipped_ids = list(zip(displayed_tags, quest_ids))
            zipped_ids_unique = set(zipped_ids)

            result =  [i + (-zipped_ids.count(i),) for i in zipped_ids_unique]

            return result

        else:
            return []


    def anki_query_count(self, query_list, check_against=None):

        query = json.dumps({
            'action': 'multi',
            'version': 6,
            'params': {
                'actions': [{
                    'action': 'findNotes',
                    'params': { 'query': q + ' deck:{}*'.format(self.deck_name) }
                    } for q in query_list]
                }
            }).encode('utf-8')

        resp = urllib.request.urlopen(self.req, query)
        resp_json = json.loads(resp.read().decode('utf-8'))

        counts = [len(r) for r in resp_json['result']]

        if check_against is not None:
            resp_flattened = [item for sublist in resp_json['result'] for item in sublist]

            outsiders = self.anki_query_check_against(resp_flattened, check_against)

            return (counts, outsiders)

        else:
            return (counts, [])

    def anki_delete(self):
        pass

    def anki_match(self):
        pass

if __name__ == '__main__':

    config = None
    with open('/Users/hgiesel/Library/Application Support/Anki2/addons21/anki-contextualize/config.json') as f:
        config = json.load(f)

    arkParser = argparse.ArgumentParser(description='Manage and query your notes!',
        prog='arkutil')

    arkParser.add_argument('-q', '--quiet', action='store_true',
        help='do not echo result or error')
    arkParser.add_argument('-d', '--debug', action='store_true',
        help='do not echo result or error')

    subparsers = arkParser.add_subparsers(dest='cmd',
        help='command to be used with the archive uri')
    subparsers_dict = {}

    subparsers_dict['paths'] = subparsers.add_parser('paths')
    subparsers_dict['paths'].add_argument('uri', nargs='?', default='',
        help='archive uri you want to query')

    subparsers_dict['stats'] = subparsers.add_parser('stats')
    subparsers_dict['stats'].add_argument('uri', nargs='?', default='',
        help='archive uri you want to query')

    subparsers_dict['query'] = subparsers.add_parser('query')
    subparsers_dict['query'].add_argument('-v', '--validate', action='store_true',
            default=False, help='get a query you can use in Anki')
    subparsers_dict['query'].add_argument('uri', nargs='?', default='',
        help='additionally verify uri against archive')

    subparsers_dict['match'] = subparsers.add_parser('match')
    subparsers_dict['match'].add_argument('uri', nargs='?', default='',
        help='match cards and see if any are missing or extra')

    subparsers_dict['ark'] = subparsers.add_parser('ark')

    ARGV = arkParser.parse_args()

    if ARGV.cmd is not None:
        theparser = subparsers_dict[ARGV.cmd]

        result = None

        if ARGV.cmd == 'paths':
            result = getattr(ArkUri(ARGV.uri), ARGV.cmd)()
            ArkPrinter.print_paths(result)

        elif ARGV.cmd == 'stats':
            result = getattr(ArkUri(ARGV.uri), ARGV.cmd)()
            ArkPrinter.print_stats(result)

        elif ARGV.cmd == 'query':
            result = getattr(ArkUri(ARGV.uri), ARGV.cmd)(ARGV.validate)
            print(' '.join(result))

        elif ARGV.cmd == 'match':
            anki_connection = AnkiConnection(
                    deck_name='misc::head',
                    quest_field_name='Quest',
                    quest_id_regex=r':([0-9]+)\a*:'
                    )

            result = getattr(ArkUri(ARGV.uri), ARGV.cmd)(anki_connection)

            ArkPrinter.print_stats(result)

        elif ARGV.cmd == 'ark':
            ark()

        else:
            getattr(ArkUri(ARGV.uri), ARGV.cmd)()
