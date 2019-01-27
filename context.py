import re
import os

from . import util

# import the main window object (mw) from aqt
from aqt import mw
# import the "show info" tool from utils.py
from aqt.utils import showInfo
# import all of the Qt GUI library
from aqt.qt import *

from anki.hooks import addHook
from subprocess import Popen, PIPE
from shutil     import copyfile

# from pathlib import Path

home = os.path.expanduser('~')
config = mw.addonManager.getConfig(__name__)

addon_path = os.path.abspath(os.path.dirname(__file__))

icon_path = os.path.join(addon_path, "icons")
icon_path_archive = os.path.join(icon_path, "archive.png")


def install_ark():
    showInfo(str(home))
    install_path = home + '/.local/bin'

    if os.path.isdir(install_path):
        os.symlink(addon_path + '/ark.py', install_path + '/ark')
        os.chmod(install_path + '/ark', 0o755)
    else:
        showInfo('Make sure the directory exists: ' + install_path)



# cross out the currently selected text
def on_archive(editor):
    found_file = False

    try:
        quest_field_index = editor.note.keys().index(config['quest_field'])
    except:
        showInfo('Note type does not have quest field: '+config['quest_field'])
        return

    quest_content = editor.note.fields[quest_field_index]

    try:
        quest = re.search(config['quest_regex'], quest_content).group(1) # only match inner group
    except:
        showInfo('Quest field does not contain quest tag specified by this regex: '+config['quest_regex'])
        return


    # first tag that is found that contains a sign of being hierarchical is taken to be topic
    indices = [i for i, item in enumerate(editor.note.tags) if re.search('::', item)]

    if len(indices) == 0:
        showInfo('Tags do not contain topic tag')
        return

    tag = editor.note.tags[indices[0]]
    tag_matches = re.search(config['topic_regex'], tag)
    topic = tag_matches.group(1)
    subtopic = tag_matches.group(2)

    if config['debug']:
        showInfo(str(
            '$TOPIC    = ' + topic    + '\n' +
            '$SUBTOPIC = ' + subtopic + '\n' +
            '$QUEST    = ' + quest    + '\n'
            ))

    for root, _, files in os.walk(config['notes_path']):
        if os.path.basename(root) == topic:
            for filename in files:
                if re.match(subtopic, filename):

                    editor_command = config['editor_command']

                    lineno='1'
                    with open(root+'/'+filename, 'r+', encoding='utf-8') as handler:
                        for num, line in enumerate(handler, 1):
                            if re.match(re.sub('\([^?].*\)', quest, config['quest_regex']), line):
                                lineno=str(num)

                    if config['debug']:
                        showInfo(str(
                            '$ROOT   = ' + root     + '\n' +
                            '$FILE   = ' + filename + '\n' +
                            '$LINENO = ' + lineno   + '\n'
                            ))

                    proc = Popen(
                    map(lambda x: re.sub('\$TOPIC', topic, x),
                     map(lambda x: re.sub('\$ROOT', root, x),
                      map(lambda x: re.sub('\$SUBTOPIC', subtopic, x),
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
