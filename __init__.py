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

# cross out the currently selected text
def on_archive(editor):
    found_file = False

    quest_index = editor.note.keys().index(config['quest_field'])
    quest_content = editor.note.fields[quest_index]
    quest = re.search(config['quest_regex'], quest_content).group(1) # only match inner group

    indices = [i for i, item in enumerate(editor.note.tags) if re.search('.*::.*', item)]
    if len(indices) >= 0:
        tag = editor.note.tags[indices[0]]

        topic = re.search("([^:]*)::[^:]*", tag).group(1)
        subtopic = re.search("::([^:]*)", tag).group(1)

        for root, _, files in os.walk(config['notes_path']):
            if os.path.basename(root) == topic:
                for file in files:
                    if re.match(subtopic, file):

                        editor_command = config['editor_command']

                        if config['debug']:
                            showInfo(str(
                                '$TOPIC' + topic + '\n' +
                                '$ROOT' + root + '\n' +
                                '$SUBTOPIC' ++ subtopic + '\n' +
                                '$FILE' + file + '\n' +
                                '$QUEST' + quest + '\n'
                                ))


                        proc = Popen(
                            [re.sub('\$TOPIC', topic, v) for v in
                             [re.sub('\$ROOT', root, v) for v in
                              [re.sub('\$SUBTOPIC', subtopic, v) for v in
                               [re.sub('\$FILE', file, v) for v in
                                [re.sub('\$QUEST', quest, v) for v in
                                 editor_command]]]]], env={})
                        found_file = True

    if not found_file:
        showInfo('Nothing was found')


def add_my_button(buttons, editor):
    editor._links['archive'] = on_archive
    buttons.insert(-1, editor._addButton(
        "iconname", # "/full/path/to/icon.png",
        "archive",
        "Open quest in archive"))
    return buttons

addHook("setupEditorButtons", add_my_button)
