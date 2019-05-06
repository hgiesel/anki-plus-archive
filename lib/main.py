from lib.identifier import Mode, Identifier, Printer
from lib.util import decloze_util, stdlib_util
from lib.srs_connection import AnkiConnection
import pprint

def paths(config, argv, printer):
  addr = Identifier(config, argv.uri, printer=printer)
  result = getattr(addr, argv.cmd)()

  if argv.paths == 'rel':
    printed = [(Identifier.to_rel_path(path[0]), path[1]) for path in result]
  elif argv.paths == 'id':
    printed = [(Identifier.to_identifier(path[0]), path[1]) for path in result]
  elif argv.paths == 'shortid':
    printed = [(Identifier.to_identifier(path[0], omit_section=True), path[1]) for path in result]
  elif argv.paths == 'none':
    printed = []

  if argv.delimiter == 'default':
    printed = [(path[0] + ':' + str(path[2]) + ':',) if path[2] is not None else (path[0],) for path in result]

  Printer.print_stats(printed, delimiter=argv.delimiter)

def stats(config, argv, printer):
  addr = Identifier(config, argv.uri, printer=printer)

  result = getattr(addr, argv.cmd)()

  if argv.paths == 'default':
    argv.paths = 'id'

  if argv.paths == 'full':
    pass
  elif argv.paths == 'rel':
    result = [(Identifier.to_rel_path(e[0]),) + e[1:] for e in result]
  elif argv.paths == 'shortid':
    result = [(Identifier.to_identifier(e[0], omit_section=True),) + e[1:] for e in result]
  elif argv.paths == 'none':
    result = [e[1:] for e in result]
  elif argv.paths == 'id':
    result = [(Identifier.to_identifier(e[0]),) + e[1:] for e in result]

  Printer.print_stats(result, delimiter=argv.delimiter)

def headings(config, argv, printer):
  addr = Identifier(config, argv.uri, printer=printer)

  result = getattr(addr, argv.cmd)()
  lines = [(val['file_name'],heading[0],heading[1]) for val in result for heading in val['headings']]

  if argv.paths == 'default':
    argv.paths='id'


  if argv.paths == 'full':
    pass
  elif argv.paths == 'rel':
    lines = [(Identifier.to_rel_path(line[0]),) + line[1:] for line in lines]
  elif argv.paths == 'id':
    lines = [(Identifier.to_identifier(line[0]),) + line[1:] for line in lines]
  elif argv.paths == 'shortid':
    lines = [(Identifier.to_identifier(line[0], omit_section=True),) + line[1:] for line in lines]
  elif argv.paths == 'none':
    lines = [line[1:] for line in lines]

  Printer.print_stats(lines, argv.delimiter if not argv.delimiter == 'default' else '\t')

def pagerefs(config, argv, printer):
  addr = Identifier(config, '@:@', printer=printer)

  result = getattr(addr, argv.cmd)(argv.uri, expand_tocs=argv.tocs, further_refs=argv.further)
  lines = sorted([(val['file_name'],pageref[0],pageref[1]) for val in result for pageref in val['pagerefs']], key=lambda t: t[2])

  if argv.paths == 'default':
    argv.paths = 'id'

  if argv.paths == 'full':
    pass
  elif argv.paths == 'rel':
    lines = [(Identifier.to_rel_path(line[0]),) + line[1:] for line in lines]
  elif argv.paths == 'id':
    lines = [(Identifier.to_identifier(line[0]),) + line[1:] for line in lines]
  elif argv.paths == 'shortid':
    lines = [(Identifier.to_identifier(line[0], omit_section=True),) + line[1:] for line in lines]
  elif argv.paths == 'none':
    lines = [line[1:] for line in lines]

  Printer.print_stats(lines, argv.delimiter if not argv.delimiter == 'default' else '\t')

def revrefs(config, argv, printer):
  result = getattr(Identifier(config, '@:@', printer=printer), argv.cmd)(
      argv.uri, further_refs=argv.further, k=argv.k)
  pprint.pprint(result)

def query(config, argv, printer):
  addr = Identifier(config, argv.uri, printer=printer)
  result = getattr(addr, argv.cmd)(argv.validate)
  print(' '.join(result))

def verify(config, argv, printer):
  addr = Identifier(config, '@:@', printer=printer)

  result = getattr(addr, argv.cmd)(argv.uri)
  lines = [(entry['file_name'],error['type'],error['info'],error['lineno']) for entry in result for error in entry['errors']]

  if argv.paths == 'default':
    argv.paths = 'id'

  if argv.paths == 'full':
    pass
  elif argv.paths == 'rel':
    lines = [(Identifier.to_rel_path(entry['file_name']), error['type'],error['info'], error['lineno']) for entry in result for error in entry['errors']]
  elif argv.paths == 'id':
    lines = [(Identifier.to_identifier(entry['file_name']), error['type'],error['info'],error['lineno']) for entry in result for error in entry['errors']]
  elif argv.paths == 'shortid':
    lines = [(Identifier.to_identifier(entry['file_name'], omit_section=True), error['type'],error['info'],error['lineno']) for entry in result for error in entry['errors']]
  elif argv.paths == 'none':
    lines = [(error['type'],error['info'],error['lineno']) for entry in result for error in entry['errors']]

  Printer.print_stats(lines, delimiter=argv.delimiter)

def match(config, argv, printer):
  anki_connection = AnkiConnection(config, printer=printer)

  addr = Identifier(config, argv.uri, printer=printer)
  result, outsiders = getattr(addr, argv.cmd)(anki_connection)

  if argv.paths == 'default':
    argv.paths = 'id'

  if argv.paths == 'full':
    pass
  elif argv.paths == 'rel':
    result = list(map(lambda t: (Identifier.to_rel_path(t[0]), t[1], t[2]), result))
  elif argv.paths == 'id':
    result = list(map(lambda t: (Identifier.to_identifier(t[0]), t[1], t[2]), result))
  elif argv.paths == 'shortid':
    result = list(map(lambda t: (Identifier.to_identifier(t[0], omit_section=True), t[1], t[2]), result))
  elif argv.paths == 'none':
    result = list(map(lambda t: (t[1], t[2]), result))

  all_results = sorted(result + outsiders, key=lambda t: t[0])

  if argv.mismatches:
    if addr.quest_component:
      all_results = list(filter(lambda t: not t[2] == 1, all_results))
    else:
      all_results = list(filter(lambda t: not int(t[1]) == t[2], all_results))

  Printer.print_stats(all_results)

def add(config, argv, printer):
  anki_connection = AnkiConnection(config, printer=printer)

  ident = Identifier(config, argv.uri, printer=printer)
  if ident.mode == Mode.QUEST_I or ident.mode == Mode.PAGE_I:
    _, path, _, qid = ident.paths()[0]

    result = anki_connection.anki_add(path.replace(':', '::'), qid, argv.content.read())
    print(result['result'] if result['result'] else result['error'])

  else:
    printer('uri must designate a single quest or page')

def browse(config, argv, printer):
  anki_connection = AnkiConnection(config, printer=printer)

  addr = Identifier(config, argv.uri, printer=printer).query()
  result = anki_connection.anki_browse(addr)

  print(result['result'] if result['result'] else result['error'])

def decloze(config, argv, printer):
  text = argv.infile.read()
  text_declozed = decloze_util(text)
  print(text_declozed, file=argv.outfile)

def stdlib(config, argv, printer):
  stdlib_util()

FUNCTION_DICT = {
    'paths': paths,
    'stats': stats,
    'headings': headings,
    'query': query,
    'verify': verify,
    'add': add,
    'match': match,
    'browse': browse,
    'pagerefs': pagerefs,
    'revrefs': revrefs,
    'decloze': decloze,
    'stdlib': stdlib,
    }
