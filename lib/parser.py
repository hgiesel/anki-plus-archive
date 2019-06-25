#!/usr/bin/env python3
import re
import argparse
import os
import sys
import json
import urllib.request

def setup_config(base_path):
    if os.path.isfile(os.path.join(base_path, 'meta.json')):
        config_file_name = os.path.join(base_path, 'meta.json')
        with open(config_file_name, 'r') as f:
            return json.load(f)['config']

    else:
        config_file_name = os.path.join(base_path, 'config.json')
        with open(config_file_name, 'r') as f:
            return json.load(f)

def setup_parser(config):
    ark_parser = argparse.ArgumentParser(description='Manage and query your notes!',
                                         prog='ark')

    ark_parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='do not echo result or error')
    ark_parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='do not echo result or error')

    subparsers = ark_parser.add_subparsers(
        dest='cmd',
        help='command to be used with the archive uri')
    subparsers_dict = {}

    subparsers_dict['paths'] = subparsers.add_parser('paths')
    subparsers_dict['paths'].add_argument('uri', nargs='?', default='',
                                          help='archive uri you want to query')
    subparsers_dict['paths'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
      default='default', help='decide how paths should be printed')
    subparsers_dict['paths'].add_argument('-d', '--delimiter',
        default='default', help='decide the delimiter for the output')
    subparsers_dict['paths'].add_argument('-t', '--tocs', action='store_true',
        help='only display tocs in result')
    subparsers_dict['paths'].add_argument('-n', '--no-tocs', action='store_true',
        help='exclude tocs in result')
    subparsers_dict['paths'].add_argument('-e', '--expand-tocs', action='store_true',
        help='expand pagerefs that point to tocs')
    subparsers_dict['paths'].add_argument('-f', '--nonhierarchical-refs', action='store_true',
        help='follow furter pagerefs when using toc as filter component')

    subparsers_dict['stats'] = subparsers.add_parser('stats')
    subparsers_dict['stats'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
      default='default', help='decide how paths should be printed')
    subparsers_dict['stats'].add_argument('-d', '--delimiter',
      default='\t', help='decide the delimiter for the output')
    subparsers_dict['stats'].add_argument('uri', nargs='?', default='',
      help='archive uri you want to query')
    subparsers_dict['stats'].add_argument('-t', '--tocs', action='store_true',
      help='only display tocs in result')
    subparsers_dict['stats'].add_argument('-n', '--no-tocs', action='store_true',
      help='exclude tocs in result')
    subparsers_dict['stats'].add_argument('-e', '--expand-tocs', action='store_true',
      help='expand pagerefs that point to tocs')
    subparsers_dict['stats'].add_argument('-f', '--nonhierarchical-refs', action='store_true',
          help='follow furter pagerefs when using toc as filter component')

    subparsers_dict['headings'] = subparsers.add_parser('headings')
    subparsers_dict['headings'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
      default='default', help='decide how paths should be printed')
    subparsers_dict['headings'].add_argument('-d', '--delimiter',
      default='default', help='decide the delimiter for the output')
    subparsers_dict['headings'].add_argument('uri', nargs='?', default='',
      help='archive uri you want to query')
    subparsers_dict['headings'].add_argument('-o', '--only-top-level', action='store_true',
      help='display only the first heading in the file')
    subparsers_dict['headings'].add_argument('-t', '--tocs', action='store_true',
      help='display only tocs in result')
    subparsers_dict['headings'].add_argument('-n', '--no-tocs', action='store_true',
      help='exclude tocs in result')
    subparsers_dict['headings'].add_argument('-e', '--expand-tocs', action='store_true',
      help='expand pagerefs that point to tocs')
    subparsers_dict['headings'].add_argument('-f', '--nonhierarchical-refs', action='store_true',
          help='follow furter pagerefs when using toc as filter component')

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
    subparsers_dict['match'].add_argument('-m', '--mismatches',
      action='store_true', help='only display files or quests which don\'t match with SRS')
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


    subparsers_dict['pagerefs'] = subparsers.add_parser('pagerefs')
    subparsers_dict['pagerefs'].add_argument('-e', '--expand-tocs', action='store_true',
          help='expand pagerefs that point to tocs')
    subparsers_dict['pagerefs'].add_argument('-f', '--nonhierarchical-refs', action='store_true',
          help='include nonhierarchical pagerefs')
    subparsers_dict['pagerefs'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
          default='default', help='decide how paths should be printed')
    subparsers_dict['pagerefs'].add_argument('-d', '--delimiter',
          default='default', help='decide the delimiter for the output')
    subparsers_dict['pagerefs'].add_argument('uri', nargs='?', default='',
          help='archive uri you want to query')

    subparsers_dict['revrefs'] = subparsers.add_parser('revrefs')
    subparsers_dict['revrefs'].add_argument('-p', '--paths', choices=['default','none','full','rel','id','shortid'],
      default='default', help='decide how paths should be printed')
    subparsers_dict['revrefs'].add_argument('-d', '--delimiter',
      default='default', help='decide the delimiter for the output')
    subparsers_dict['revrefs'].add_argument('-f', '--nonhierarchical-refs', action='store_true',
          help='follow nonhierarchical pagerefs')
    subparsers_dict['revrefs'].add_argument('-k', type=int,
            default=-1, help='decide how deep pagerefs are traced, NOTE: may cause error in combination with nonhierarchical refs')
    subparsers_dict['revrefs'].add_argument('uri', nargs='?', default='',
      help='archive uri you want to query')

    subparsers_dict['decloze'] = subparsers.add_parser('decloze')
    subparsers_dict['decloze'].add_argument('uri', nargs='?', default='',
      help='match cards and see if any are missing or extra')
    subparsers_dict['decloze'].add_argument('infile', nargs='?', type=argparse.FileType('r'),
      default=sys.stdin)
    subparsers_dict['decloze'].add_argument('outfile', nargs='?', type=argparse.FileType('w'),
      default=sys.stdout)

    subparsers_dict['stdlib'] = subparsers.add_parser('stdlib')

    return ark_parser, subparsers_dict
