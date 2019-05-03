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

def on_command_replace(text, archive_root, section, page, qid):
    for dirname, _, bases in os.walk(archive_root):
        if os.path.basename(dirname) == section:
            for base in bases:
                if re.match(page, base):

                    return list(map(
                            lambda x: re.sub('\$ROOT', archive_root, x), map(
                                lambda x: re.sub('\$DIR', dirname, x), map(
                                    lambda x: re.sub('\$BASE', base, x), map(
                                        lambda x: re.sub('\$SECTION', section, x), map(
                                            lambda x: re.sub('\$PAGE', page, x), map(
                                                lambda x: re.sub('\$QID', qid, x), text)))))))

def on_command(editor, archive_root: str, card_sets, comm) -> None:
    ### get qid
    qid_field_name = card_sets[0]['qid_field']

    if qid_field_name:
        try:
            qid_field = editor.note.keys().index(qid_field_name)
        except:
            showInfo('Note type does not have quest field: ' + qid_field_name)
            return None

        qid_unclean = editor.note.fields[qid_field]
        qid_regex = re.compile("^:?([0-9]+):?")

        try:
            qid = re.search(qid_regex, qid_unclean).group(1) # only match inner group
        except:
            showInfo('Quest field %s does not contain quest tag specified by this regex: '
                    '"^:([0-9]+):(?: .*)?"' % (card_sets[0]['qid_field']))

            return None
    else:
        qid = str(editor.note.id)

    ### get section and page
    pageid_prefix = card_sets[0]['pageid_prefix']
    pageid_regex = re.compile((pageid_prefix + "::" if pageid_prefix else "") + "(?:.*::)?([^:]*)::([^:]*)$")

    # first tag that is found that contains a sign of being hierarchical is taken to be section
    indices = [i for i, item in enumerate(editor.note.tags) if pageid_regex.search(item)]

    if len(indices) == 0:
        showInfo('Tags do not contain section tag!')
        return None

    elif len(indices) != 1:
        showInfo('''
        Tags contain multiple viable pageids.
        Only one tag is allowed to be hierarchical!')
        '''.lstrip())
        return None

    tag = editor.note.tags[indices[0]]
    tag_matches = pageid_regex.search(tag)

    section = tag_matches.group(1)
    page = tag_matches.group(2)

    # showInfo("%s::%s#%s" % (section, page, qid))

    if comm['type'] == 'shell':
        result = on_command_replace(comm['arguments'], archive_root, section, page, qid)
        proc = Popen(result, env={})

    elif comm['type'] == 'clipboard':
        result = on_command_replace([comm['text']], archive_root, section, page, qid)[0]
        pyperclip.copy(result)

    else:
        showInfo('Invalid command type!')
        return


def main(config, icons):

    if len(config['commands']) > 6:
        showInfo('anki-plus-archive supports a maximum of 6 commands')
        return

    def on_command0(editor):
        nonlocal config
        on_command(editor, config['archive_root'], config['card_sets'], config['commands'][0])
    def on_command1(editor):
        nonlocal config
        on_command(editor, config['archive_root'], config['card_sets'], config['commands'][1])
    def on_command2(editor):
        nonlocal config
        on_command(editor, config['archive_root'], config['card_sets'], config['commands'][2])
    def on_command3(editor):
        nonlocal config
        on_command(editor, config['archive_root'], config['card_sets'], config['commands'][3])
    def on_command4(editor):
        nonlocal config
        on_command(editor, config['archive_root'], config['card_sets'], config['commands'][4])
    def on_command5(editor):
        nonlocal config
        on_command(editor, config['archive_root'], config['card_sets'], config['commands'][5])

    on_command_list = [
        on_command0,
        on_command1,
        on_command2,
        on_command3,
        on_command4,
        on_command5,
    ]

    def add_my_buttons(buttons, editor):
        nonlocal config
        nonlocal icons
        nonlocal on_command_list

        for i, command in enumerate(config['commands']):
            editor._links[command['title']] = on_command_list[i]
            buttons.insert(-1, editor._addButton(
                icons[i],
                command['title'],
                command['description'],
                ))

        return buttons

    addHook("setupEditorButtons", add_my_buttons)
