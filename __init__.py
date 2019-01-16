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

# a = aqt.editcurrent.EditCurrent(mw).editor.note.fields # arrray of field values
# a = aqt.editcurrent.EditCurrent(mw).editor.note.keys() # array of field names
# a = aqt.editcurrent.EditCurrent(mw).editor.note.values()
config = mw.addonManager.getConfig(__name__)

addon_path = os.path.dirname(__file__)

icon_path = os.path.join(addon_path, "icons")
icon_path_archive = os.path.join(icon_path, "archive.png")

# cross out the currently selected text
def on_archive(editor):
    found_file = False

    quest_index = editor.note.keys().index(config['quest_field'])
    quest_content = editor.note.fields[quest_index]
    quest = re.search(config['quest_regex'], quest_content).group(1) # only match inner group

    # first tag that is found that contains a sign of being hierarchical is taken to be topic
    indices = [i for i, item in enumerate(editor.note.tags) if re.search('::', item)]

    if len(indices) >= 0:
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
                            [re.sub('\$TOPIC', topic, v) for v in
                             [re.sub('\$ROOT', root, v) for v in
                              [re.sub('\$SUBTOPIC', subtopic, v) for v in
                               [re.sub('\$FILE', filename, v) for v in
                                [re.sub('\$QUEST', quest, v) for v in
                                 [re.sub('\$LINENO', lineno, v) for v in
                                  editor_command]]]]]], env={})
                        found_file = True

    if not found_file:
        showInfo('Nothing was found')


def add_my_button(buttons, editor):
    editor._links['archive'] = on_archive
    buttons.insert(-1, editor._addButton(
        icon_path_archive, # "/full/path/to/icon.png",
        "archive",
        "Open quest in archive"))
    return buttons

addHook("setupEditorButtons", add_my_button)
