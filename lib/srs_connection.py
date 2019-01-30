import urllib
import json
import re

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

        counts = None
        if not None in resp_json['result']:
            counts = [len(r) for r in resp_json['result']]

        outsiders = []
        if check_against is not None:
            resp_flattened = [item for sublist in resp_json['result'] for item in sublist]
            outsiders = self.anki_query_check_against(resp_flattened, check_against)

        return (counts, outsiders)

    def anki_delete(self):
        pass

    def anki_match(self):
        pass

