# MAIN ENTRANCE FOR EVERYTHING RUN WITHIN ANKI ITSELF
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

from . import pyperclip

home = os.path.expanduser('~')
config = mw.addonManager.getConfig(__name__)

addon_path = os.path.abspath(os.path.dirname(__file__))

icon_path = os.path.join(addon_path, "../icons")

def install_ark():
  install_dir = os.path.join(home, '.local/bin')
  install_path = os.path.join(install_dir, 'ark')

  if os.path.isdir(install_dir) and not os.path.isfile(install_path):
    os.symlink(addon_path + '/../__init__.py', install_path)
    os.chmod(install_path, 0o755)


def on_archive(editor, comm):
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

              if comm['type'] == 'shell':
                shell_command = comm['arguments']

                proc = Popen(
                  map(lambda x: re.sub('\$SECTION', section, x),
                    map(lambda x: re.sub('\$ROOT', root, x),
                      map(lambda x: re.sub('\$PAGE', page, x),
                        map(lambda x: re.sub('\$FILE', filename, x),
                          map(lambda x: re.sub('\$QUEST', quest, x),
                            # map(lambda x: re.sub('\$LINENO', lineno, x),
                            shell_command))))), env={})

                found_file = True

              elif comm['type'] == 'clipboard':

                pyperclip.copy(re.sub('\$SECTION', section, re.sub('\$ROOT', root,
                  re.sub('\$PAGE', page,
                    re.sub('\$FILE', filename,
                      re.sub('\$QUEST', quest,
                        # re.sub('\$LINENO', lineno,
                        comm['text']))))))

                found_file = True


  if not found_file:
    showInfo('Nothing was found')

def on_archive0(editor):
  on_archive(editor, config['commands'][0])
def on_archive1(editor):
  on_archive(editor, config['commands'][1])
def on_archive2(editor):
  on_archive(editor, config['commands'][2])
def on_archive3(editor):
  on_archive(editor, config['commands'][3])
def on_archive4(editor):
  on_archive(editor, config['commands'][4])
def on_archive5(editor):
  on_archive(editor, config['commands'][5])

ON_ARCHIVE_COMMANDS = [
  on_archive0,
  on_archive1,
  on_archive2,
  on_archive3,
  on_archive4,
  on_archive5
  ]


def add_my_buttons(buttons, editor):
  for i, command in enumerate(config['commands']):
    editor._links['archive'] = ON_ARCHIVE_COMMANDS[i]
    buttons.insert(-1, editor._addButton(
      os.path.join(icon_path, "looks_" + str(i) + ".png"),
      "command " + str(i),
      "Command " + str(i) +" for archive"))

  return buttons

addHook("setupEditorButtons", add_my_buttons)
install_ark()
