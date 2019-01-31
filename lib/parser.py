#!/usr/bin/env python3
import re
import argparse
import os
import sys
import json
import urllib.request


def setup_parser():
    config = None
    with open('/Users/hgiesel/Library/Application Support/Anki2/addons21/anki-context/config.json') as f:
        config = json.load(f)

    arkParser = argparse.ArgumentParser(description='Manage and query your notes!',
        prog='ark')

    arkParser.add_argument('-q', '--quiet', action='store_true',
        help='do not echo result or error')
    arkParser.add_argument('-d', '--debug', action='store_true',
        help='do not echo result or error')

    subparsers = arkParser.add_subparsers(dest='cmd',
        help='command to be used with the archive uri')
    subparsers_dict = {}

    subparsers_dict['paths'] = subparsers.add_parser('paths')
    subparsers_dict['paths'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
            default='default', help='decide how paths should be printed')
    subparsers_dict['paths'].add_argument('-d', '--delimiter',
            default='default', help='decide the delimiter for the output')
    subparsers_dict['paths'].add_argument('uri', nargs='?', default='',
        help='archive uri you want to query')

    subparsers_dict['stats'] = subparsers.add_parser('stats')
    subparsers_dict['stats'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
            default='default', help='decide how paths should be printed')
    subparsers_dict['stats'].add_argument('-d', '--delimiter',
            default='\t', help='decide the delimiter for the output')
    subparsers_dict['stats'].add_argument('uri', nargs='?', default='',
        help='archive uri you want to query')



    subparsers_dict['pagerefs'] = subparsers.add_parser('pagerefs')
    subparsers_dict['pagerefs'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
            default='default', help='decide how paths should be printed')
    subparsers_dict['pagerefs'].add_argument('-d', '--delimiter',
            default='default', help='decide the delimiter for the output')
    subparsers_dict['pagerefs'].add_argument('uri', nargs='?', default='',
        help='archive uri you want to query')

    subparsers_dict['headings'] = subparsers.add_parser('headings')
    subparsers_dict['headings'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
            default='default', help='decide how paths should be printed')
    subparsers_dict['headings'].add_argument('-d', '--delimiter',
            default='default', help='decide the delimiter for the output')
    subparsers_dict['headings'].add_argument('uri', nargs='?', default='',
        help='archive uri you want to query')

    subparsers_dict['verify'] = subparsers.add_parser('verify')
    subparsers_dict['verify'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
            default='default', help='decide how paths should be printed')
    subparsers_dict['verify'].add_argument('-d', '--delimiter',
            default='\t', help='decide the delimiter for the output')
    subparsers_dict['verify'].add_argument('uri', nargs='?', default='',
        help='archive uri you want to query')



    subparsers_dict['query'] = subparsers.add_parser('query')
    subparsers_dict['query'].add_argument('-v', '--validate', action='store_true',
            default=False, help='get a query you can use in Anki')
    subparsers_dict['query'].add_argument('uri', nargs='?', default='',
        help='additionally verify uri against archive')

    subparsers_dict['match'] = subparsers.add_parser('match')
    subparsers_dict['match'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
            default='default', help='decide how paths should be printed')
    subparsers_dict['match'].add_argument('uri', nargs='?', default='',
        help='match cards and see if any are missing or extra')

    subparsers_dict['add'] = subparsers.add_parser('add')
    subparsers_dict['add'].add_argument('uri', nargs='?', default='',
        help='add cards and see if any are missing or extra')
    subparsers_dict['add'].add_argument('content', nargs='?', type=argparse.FileType('r'),
            default=sys.stdin)

    subparsers_dict['browse'] = subparsers.add_parser('browse')
    subparsers_dict['browse'].add_argument('uri', nargs='?', default='',
        help='browse cards and see if any are missing or extra')



    subparsers_dict['decloze'] = subparsers.add_parser('decloze')
    subparsers_dict['decloze'].add_argument('uri', nargs='?', default='',
        help='match cards and see if any are missing or extra')
    subparsers_dict['decloze'].add_argument('infile', nargs='?', type=argparse.FileType('r'),
            default=sys.stdin)
    subparsers_dict['decloze'].add_argument('outfile', nargs='?', type=argparse.FileType('w'),
            default=sys.stdout)

    subparsers_dict['stdlib'] = subparsers.add_parser('stdlib')

    argv = arkParser.parse_args()

    return (argv, subparsers_dict[argv.cmd].error if argv.cmd else None)
