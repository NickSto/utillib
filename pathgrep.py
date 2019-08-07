#!/usr/bin/env python3
import argparse
import logging
import os
import pathlib
import sys
try:
  import yaml
except ImportError:
  yaml = None
assert sys.version_info.major >= 3, 'Python 3 required'

ESCAPE_CHARS = {'\\0':'\x00', '\\t':'\t', '\\n':'\n', '\\r':'\r'}
DESCRIPTION = """Filter files according to paths in them."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  input = parser.add_argument_group('Input')
  input.add_argument('infile', type=argparse.FileType('r'), default=sys.stdin, nargs='?',
    help='Input file. Default: stdin')
  input.add_argument('-f', '--fields', type=csv_int,
    help='Column(s) to match. Accepts a comma-delimited list. If multiple columns are given, the '
      'line will be printed if any of the values is judged to be included. '
      'Default: interpret the entire line as a single path.')
  input.add_argument('-d', '--delim',
    help="Field delimiter. You can use regular escape-character syntax for the following "
      "characters: '"+"', '".join(ESCAPE_CHARS.keys())+"'. Default: whitespace")
  filters = parser.add_argument_group('Filtering')
  filters.add_argument('-i', '--include', nargs=3, action='append',
    metavar=('[absolute|relative]', '[recursive|exact]', 'path'),
    help='Include lines matching this path. If inclusion rules are given, this uses a default-'
      'exclude model where only lines matching an include rule are output. If only exclude rules '
      'are given, it includes every line unless it matches an exclude rule. If both include and '
      "exclude rules are given, it's still default-exclude, but if the path matches both an "
      'include and exclude rule, exclusion takes precedence. '
      'If no rules are given, it will not include any line.')
  filters.add_argument('-x', '--exclude', nargs=3, action='append',
    metavar=('[absolute|relative]', '[recursive|exact]', 'path'),
    help='Exclude lines matching this path.')
  filters.add_argument('-e', '--ext', nargs=2, action='append', metavar=('[include|exclude]', 'ext'),
    help='Include or exclude lines with paths matching this extension.')
  filters.add_argument('-F', '--filters', metavar='filters.yaml', type=argparse.FileType('r'),
    help='Filter paths according to the criteria in this yaml file. See example for structure.')
  filters.add_argument('-I', '--include-file', metavar='include.yaml', type=argparse.FileType('r'),
    help='Add inclusion rules using a yaml file like the one for --filter, except starting one '
      'level lower (at the level of keys {}).'
      .format(', '.join([repr(key) for key in make_blank_criteria().keys()])))
  filters.add_argument('-X', '--exclude-file', metavar='exclude.yaml', type=argparse.FileType('r'),
    help='Same as --include-file, but for exclusions.')
  logs = parser.add_argument_group('Logging')
  logs.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  volume = logs.add_mutually_exclusive_group()
  volume.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  volume.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  volume.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  if args.filters:
    filters = parse_filters_file(args.filters)
  else:
    filters = make_blank_filters()
  if args.include_file:
    filters['included'], filters['has_included'] = parse_criteria_file(args.include_file)
  if args.exclude_file:
    filters['excluded'], filters['has_excluded'] = parse_criteria_file(args.exclude_file)

  parse_rules_args(filters, args.include, args.exclude, args.ext)

  delim = ESCAPE_CHARS.get(args.delim)
  for line in filter_input(args.infile, filters, args.fields, delim, 'raise'):
    print(line, end='')


def csv_int(csv_str):
  return [int(value_str) for value_str in csv_str.split('.')]


def parse_rules_args(filters, includes, excludes, exts):
  parse_rule_args(filters, includes, 'include')
  parse_rule_args(filters, excludes, 'exclude')
  parse_ext_rule(filters, exts)


def parse_rule_args(filters, args, rule_type):
  if args is None:
    return
  for path_type, recursivity, path_str in args:
    if path_type not in ('absolute', 'relative'):
      raise ValueError(f"1st argument to --{rule_type} must be 'absolute' or 'relative'. "
                       f'Saw {path_type!r} instead.')
    if recursivity not in ('recursive', 'exact'):
      raise ValueError(f"2nd argument to --{rule_type} must be 'recursive' or 'exact'. "
                       f'Saw {recursivity!r} instead.')
    filters[rule_type+'d'][path_type][recursivity].append(pathlib.Path(path_str))
    filters['has_{}d'.format(rule_type)] = True


def parse_ext_rule(filters, ext_args):
  if ext_args is None:
    return
  for rule_type, ext in ext_args:
    if rule_type not in ('include', 'exclude'):
      raise ValueError(f"1st argument to --ext must be 'include' or 'exclude'. "
                       f'Saw {rule_type!r} instead.')
    filters[rule_type+'d']['ext'].append(ext.lstrip('.'))


def filter_input(input, filters, fields, delim, error_handling):
  for line_num, line_raw in enumerate(input):
    paths = parse_line(line_raw, fields, delim, error_handling, line_num)
    if paths is None:
      continue
    for path in paths:
      if include_path(path, filters):
        yield line_raw
        break


def parse_line(line_raw, fields, delim, error_handling, line_num):
  if fields is None:
    line = line_raw.rstrip('\r\n')
    return (pathlib.Path(line),)
  else:
    field_values = split_line(line_raw, delim)
    try:
      return [pathlib.Path(field_values[field]) for field in fields]
    except IndexError:
      if error_handling != 'silent':
        logging.warning('Warning: Field out of range in line {}.'.format(line_num+1))
      if error_handling == 'raise':
        raise
      return None


def split_line(line_raw, delim):
  line = line_raw.rstrip('\r\n')
  if delim:
    return line.split(delim)
  else:
    return line.split()


def make_blank_filters():
  return {
    'excluded':make_blank_criteria(), 'has_excluded':False,
    'included':make_blank_criteria(), 'has_included':False,
  }


def make_blank_criteria():
  return {
    'absolute': {
      'recursive': [],
      'exact': [],
    },
    'relative': {
      'recursive': [],
      'exact': [],
    },
    'ext': [],
  }


def parse_filters_file(filters_file):
  assert yaml is not None, 'yaml module required to parse filters file.'
  filters = {}
  filters_data = yaml.safe_load(filters_file)
  excluded, has_excluded = parse_criteria(filters_data.get('excluded', {}))
  included, has_included = parse_criteria(filters_data.get('included', {}))
  return {
    'excluded':excluded, 'has_excluded':has_excluded,
    'included':included, 'has_included':has_included,
  }


def parse_criteria_file(criteria_file):
  assert yaml is not None, 'yaml module required to parse included/excluded files.'
  criteria_data = yaml.safe_load(criteria_file)
  root_keys = make_blank_criteria().keys()
  assert any([key in criteria_data for key in root_keys]), (
    'Included/excluded yaml file contains none of the recognized top-level keys. At least one of '
    "{} must be present. Saw instead: {}."
    .format(', '.join([repr(key) for key in root_keys]),
            ', '.join([repr(key) for key in criteria_data.keys()])))
  return parse_criteria(criteria_data)


def parse_criteria(criteria_data):
  criteria = make_blank_criteria()
  has_criteria = False
  # absolute
  absolute = criteria_data.get('absolute', {})
  #   recursive
  for path_str in absolute.get('recursive', ()):
    criteria['absolute']['recursive'].append(abs_str_to_path(path_str))
    has_criteria = True
  #   exact
  for path_str in absolute.get('exact', ()):
    criteria['absolute']['exact'].append(abs_str_to_path(path_str))
    has_criteria = True
  # relative
  relative = criteria_data.get('relative', {})
  #   recursive
  for path_str in relative.get('recursive', ()):
    criteria['relative']['recursive'].append(pathlib.Path(path_str))
    has_criteria = True
  #   exact
  for path_str in relative.get('exact', ()):
    criteria['relative']['exact'].append(pathlib.Path(path_str))
    has_criteria = True
  # ext
  for ext in criteria_data.get('ext', ()):
    criteria['ext'].append('.'+ext.lstrip('.'))
    has_criteria = True
  return criteria, has_criteria


def abs_str_to_path(path_str):
  if not (path_str.startswith('~') or path_str.startswith(os.sep)):
    raise ValueError("Absolute filter path does not start with '~' or '/': {!r}"
                     .format(path_str))
  return pathlib.Path(path_str).expanduser()


def include_path(path, filters, default=None):
  """Check which filters the path matches, and decide whether it should be included.
  If there are only exclude rules, this will be default to inclusion.
  Otherwise, this defaults to exclusion (if there are include rules, both include and exclude, or
  neither). Technically this returns `default` if there are no rules (defaults to `None`)."""
  if filters['has_excluded']:
    if path_matches_criteria(path, filters['excluded']):
      return False
    elif not filters['has_included']:
      return True
  if filters['has_included']:
    if path_matches_criteria(path, filters['included']):
      return True
    else:
      return False
  return default


def paths_match_criteria(paths, criteria):
  for path in paths:
    if path_matches_criteria(path, criteria):
      return True
  return False


def path_matches_criteria(path, criteria):
  # absolute
  #   exact
  for query_path in criteria['absolute']['exact']:
    if query_path == path:
      return True
  #   recursive
  for query_path in criteria['absolute']['recursive']:
    try:
      path.relative_to(query_path)
      return True
    except ValueError:
      pass
  # relative
  #   exact
  for query_path in criteria['relative']['exact']:
    if str(path).endswith(str(query_path)):
      return True
  #   recursive
  for query_path in criteria['relative']['recursive']:
    if is_subpath(path, query_path):
      return True
  #   ext
  for ext in criteria['ext']:
    if matches_extensions(path, ext):
      return True
  return False


def is_subpath(target_path, query_path):
  """Do  the query path elements occur anywhere inside the path?
  This algorithm allows for a query path that's multiple directory levels.
  Examples:
  is_subpath('/ab/cd/ef/gh', 'cd') == True
  is_subpath('/ab/cd/ef/gh', 'cd/ef') == True
  is_subpath('/ab/cd/ef/gh', 'd/ef') == False
  is_subpath('/ab/cd/ef/gh', 'ab') == True
  is_subpath('/ab/cd/ef/gh', 'gh') == True
  """
  query_str = str(query_path).lstrip(os.sep).rstrip(os.sep)
  target_str = str(target_path)
  try:
    i = target_str.index(query_str)
  except ValueError:
    return False
  starts_on_boundary = i == 0 or target_str[i-1] == os.sep
  ends_on_boundary = i+len(query_str) == len(target_str) or target_str[i+len(query_str)] == os.sep
  if starts_on_boundary and ends_on_boundary:
    return True
  else:
    return False


def matches_extensions(target_path, query_ext):
  """Does the filename extension match the query one?
  This will attempt to match the query against every possible extension length.
  I.e. for 'target.tar.gz', it tries both '.tar.gz' and '.gz'.
  This also means for 'Windows 3.1 Boot.iso', it tries both '.1 Boot.iso' and '.iso', but that's
  unlikely to give a false positive.
  The dot prefix on `query_ext` is optional."""
  if not query_ext.startswith('.'):
    query_ext = '.'+query_ext
  exts = target_path.suffixes
  for i in range(len(exts)):
    if query_ext == ''.join(exts[i:]):
      return True
  return False


def fail(message):
  logging.critical(message)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception('Unrecoverable error')


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
