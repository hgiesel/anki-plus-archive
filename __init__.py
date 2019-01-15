# import the main window object (mw) from aqt
from aqt import mw
# import the "show info" tool from utils.py
from aqt.utils import showInfo
# import all of the Qt GUI library
from aqt.qt import *

from anki.hooks import addHook
from subprocess import Popen, PIPE

NOTES_PATH = '/Users/hgiesel/Developer/notes/README.adoc'
# a = aqt.editcurrent.EditCurrent(mw).editor.note.fields # arrray of field values
# a = aqt.editcurrent.EditCurrent(mw).editor.note.keys() # array of field names
# a = aqt.editcurrent.EditCurrent(mw).editor.note.values()


# cross out the currently selected text
def onStrike(editor):
    editor.web.eval("wrap('<del>', '</del>');")
    quest_index = editor.note.keys().index("Front")
    quest_content = editor.note.fields[quest_index]
    m = re.search(':(\d*).*?:', foo).group(1) # only match inner group
    showInfo(str(m))
    showInfo(str('hello world'))
    proc = Popen(['/usr/local/bin/mvim', NOTES_PATH], env={})

def addMyButton(buttons, editor):
    editor._links['strike'] = onStrike
    return buttons + [editor._addButton(
        "iconname", # "/full/path/to/icon.png",
        "Open in archive", # link name
        "tooltip")]

addHook("setupEditorButtons", addMyButton)


def test_function():
    # get the number of cards in the current collection, which is stored in
    # the main window
    card_count = mw.col.cardCount()
    # show a message box
    showInfo("Card count: %d" % card_count)

# create a new menu item, "test"
ACTION = QAction("test", mw)
# set it to call testFunction when it's clicked
ACTION.triggered.connect(test_function)
# and add it to the tools menu
mw.form.menuTools.addAction(ACTION)
