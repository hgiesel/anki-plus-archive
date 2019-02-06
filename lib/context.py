import re
import os

# import the main window object (mw) from aqt
from aqt import mw
# import the "show info" tool from utils.py
from aqt.utils import showInfo
# import all of the Qt GUI library
from aqt.qt import *

from anki.hooks import addHook
from subprocess import Popen, PIPE
from shutil     import copyfile

from .util import *

# from pathlib import Path

home = os.path.expanduser('~')
config = mw.addonManager.getConfig(__name__)

addon_path = os.path.abspath(os.path.dirname(__file__))

icon_path = os.path.join(addon_path, "../icons")
icon_path_archive = os.path.join(icon_path, "archive.png")

def install_ark():
    install_path = os.path.join(home, '.local/bin', 'ark')

    if os.path.isdir(install_path) and not os.path.isfile(install_path):
        os.symlink(addon_path + '/../__init__.py', install_path)
        os.chmod(install_path, 0o755)

# cross out the currently selected text
def on_archive(editor):
    found_file = False

    try:
        quest_field_index = editor.note.keys().index(config['card_sets'][0]['quest_field'])
    except:
        showInfo('Note type does not have quest field: '+config['card_sets'][0]['quest_field'])
        return

    quest_content = editor.note.fields[quest_field_index]

    try:
        quest = re.search(config['card_sets'][0]['qid_regex'], quest_content).group(1) # only match inner group
    except:
        showInfo('Quest field "'+ config['card_sets'][0]['quest_field'] +'" does not contain quest tag specified by this regex: "'
                + config['card_sets'][0]['qid_regex'] + '"')
        return

    pageid_regex = re.compile(config['card_sets'][0]['pageid_regex'])

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

    if config['debug']:
        showInfo(str(
            '$SECTION    = ' + sextion    + '\n' +
            '$PAGE = ' + page + '\n' +
            '$QUEST    = ' + quest    + '\n'
            ))

    for root, _, files in os.walk(config['archive_root']):
        if os.path.basename(root) == section:
            for filename in files:
                if re.match(page, filename):

                    editor_command = config['editor_command']

                    lineno='1'
                    with open(root+'/'+filename, 'r+', encoding='utf-8') as handler:
                        for num, line in enumerate(handler, 1):
                            if re.match(re.sub('\([^?].*\)', quest, config['card_sets'][0]['qid_regex']), line):
                                lineno=str(num)

                    if config['debug']:
                        showInfo(str(
                            '$ROOT   = ' + root     + '\n' +
                            '$FILE   = ' + filename + '\n' +
                            '$LINENO = ' + lineno   + '\n'
                            ))

                    proc = Popen(
                    map(lambda x: re.sub('\$SECTION', section, x),
                     map(lambda x: re.sub('\$ROOT', root, x),
                      map(lambda x: re.sub('\$PAGE', page, x),
                       map(lambda x: re.sub('\$FILE', filename, x),
                        map(lambda x: re.sub('\$QUEST', quest, x),
                         map(lambda x: re.sub('\$LINENO', lineno, x),
                          editor_command)))))), env={})

                    found_file = True

    if not found_file:
        showInfo('Nothing was found')


def add_my_button(buttons, editor):
    editor._links['archive'] = on_archive
    buttons.insert(-1, editor._addButton(
        icon_path_archive, # "/full/path/to/icon.png",
        "archive",
        "Query archive"))
    return buttons

addHook("setupEditorButtons", add_my_button)
install_ark()
