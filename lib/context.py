# MAIN ENTRANCE FOR EVERYTHING RUN WITHIN ANKI ITSELF
import re
import os
from subprocess import Popen

from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *
from anki.hooks import addHook

from .util import *

from . import pyperclip

def on_archive(editor, config, comm):
    found_file = False
    qid_field_name = config['card_sets'][0]['qid_field']

    try:
        qid_field = editor.note.keys().index(qid_field_name)
    except:
        showInfo('Note type does not have quest field: ' + qid_field_name)
    return

    if qid_field:
        qid = editor.note.fields[qid_field]
        qid_regex = re.compile("^:?([0-9]+):?")

    try:
        quest = re.search(qid_regex, qid).group(1) # only match inner group
    except:
        showInfo('Quest field "'+ config['card_sets'][0]['qid_field'] +'" does not contain quest tag specified by this regex: "'
                + "^:([0-9]+):(?: .*)?" + '"')
        return

    else:
        quest = str(editor.note.id)

    pageid_prefix = config['card_sets'][0]['pageid_prefix']
    pageid_regex = re.compile((pageid_prefix + "::" if pageid_prefix else "") + "(?:.*::)?([^:]*)::([^:]*)$")

    # first tag that is found that contains a sign of being hierarchical is taken to be section
    indices = [i for i, item in enumerate(editor.note.tags) if pageid_regex.search(item)]

    if len(indices) == 0:
        showInfo('Tags do not contain section tag')
    return

    if len(indices) > 1 :
        showInfo('Tags contain multiple viable pageids')
    return

    tag = editor.note.tags[indices[0]]
    tag_matches = pageid_regex.search(tag)
    section = tag_matches.group(1)
    page = tag_matches.group(2)

#     if config['debug']:
#         showInfo(str(
#             '$SECTION    = ' + section    + '\n' +
#             '$PAGE = ' + page + '\n' +
#             '$QUEST    = ' + quest    + '\n'
#             ))

    for root, _, files in os.walk(config['archive_root']):
        if os.path.basename(root) == section:
            for filename in files:
                if re.match(page, filename):
                    if comm['type'] == 'shell':
                        shell_command = comm['arguments']

            proc = Popen(
                    map(lambda x: re.sub(r'$SECTION', section, x),
                        map(lambda x: re.sub(r'$ROOT', root, x),
                            map(lambda x: re.sub(r'$PAGE', page, x),
                                map(lambda x: re.sub(r'$FILE', filename, x),
                                    map(lambda x: re.sub(r'$QUEST', quest, x),
                                        # map(lambda x: re.sub('\$LINENO', lineno, x),
                                        shell_command))))), env={})

            found_file = True

        elif comm['type'] == 'clipboard':

            pyperclip.copy(
                re.sub(r'$SECTION', section,
                    re.sub(r'$ROOT', root,
                        re.sub(r'$PAGE', page,
                            re.sub(r'$FILE', filename,
                                re.sub(r'$QUEST', quest,
                                    # re.sub('\$LINENO', lineno,
                                    comm['text']))))))

            found_file = True


    if not found_file:
        showInfo('Nothing was found')


def main(config, icons):

    def on_archive0(editor):
        nonlocal config
        on_archive(editor, config, config['commands'][0])
    def on_archive1(editor):
        nonlocal config
        on_archive(editor, config, config['commands'][1])
    def on_archive2(editor):
        nonlocal config
        on_archive(editor, config, config['commands'][2])
    def on_archive3(editor):
        nonlocal config
        on_archive(editor, config, config['commands'][3])
    def on_archive4(editor):
        nonlocal config
        on_archive(editor, config, config['commands'][4])
    def on_archive5(editor):
        nonlocal config
        on_archive(editor, config, config['commands'][5])

    on_archive_commands = [
        on_archive0,
        on_archive1,
        on_archive2,
        on_archive3,
        on_archive4,
        on_archive5,
    ]

    def add_my_buttons(buttons, editor):
        nonlocal config
        nonlocal icons
        nonlocal on_archive_commands

        for i, _command in enumerate(config['commands']):
            editor._links['archive'] = on_archive_commands[i]
            buttons.insert(-1, editor._addButton(
                icons[i],
                "command " + str(i),
                "Command " + str(i) +" for archive"
                ))

        return buttons

    addHook("setupEditorButtons", add_my_buttons)
