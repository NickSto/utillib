#!/usr/bin/env python3
import argparse
import logging
import os
import pathlib
import sys
import yaml


def parse(lines, parse_yaml=True):
  content_lines = []
  yaml_lines = []
  state = None
  for line_raw in lines:
    line = line_raw.rstrip('\r\n')
    # Update the state for this line.
    if state is None:
      if line == '---':
        state = 'graymatter'
        continue
      elif line.strip():
        state = 'content'
      else:
        continue
    elif state == 'graymatter':
      if line == '---':
        state = 'content'
        continue 
    # Process the line according to the state.
    if state == 'graymatter':
      yaml_lines.append(line_raw)
    elif state == 'content':
      content_lines.append(line_raw)
  # Parse the yaml
  yaml_str = ''.join(yaml_lines)
  if parse_yaml:
    # Can raise a yaml.YAMLError
    metadata = yaml.safe_load(yaml_str)
  else:
    metadata = yaml_str
  return metadata, ''.join(content_lines)


def make_argparser():
  parser = argparse.ArgumentParser(add_help=False)
  options = parser.add_argument_group('Options')
  options.add_argument('inputs', type=pathlib.Path, nargs='+',
    help='Input Markdown file, or directory containing Markdown files.')
  options.add_argument('-m', '--meta', action='store_true',
    help='Just print the graymatter YAML.')
  options.add_argument('-c', '--content', action='store_true',
    help='Omit the graymatter and just print the content.')
  options.add_argument('-k', '--key',
    help='Just print the value of this key from the metadata.')
  options.add_argument('-v', '--value',
    help='Print files where the value of --key matches this. Only valid with --find and --key. '
      'The metadata value will be converted to a str before comparison.')
  options.add_argument('-t', '--trim', action='store_true',
    help='Trim whitespace one either side of the output.')
  options.add_argument('-V', '--validate', action='store_true',
    help='Only validate yaml syntax.')
  options.add_argument('-l', '--find', action='store_true',
    help='Just find files that match the given criteria (contain the --key, fail to --validate)')
  options.add_argument('-e', '--ext', default='md',
    help='Markdown file extension. For input paths which are directories, only examine files with'
      'this file extension (case-insensitive). Default: %(default)s')
  options.add_argument('-h', '--help', action='help',
    help='Print this argument help text and exit.')
  logs = parser.add_argument_group('Logging')
  logs.add_argument('-L', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  volume = logs.add_mutually_exclusive_group()
  volume.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  volume.add_argument('--verbose', dest='volume', action='store_const', const=logging.INFO)
  volume.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):
  parser = make_argparser()
  args = parser.parse_args(argv[1:])
  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  parse_yaml = args.key or args.validate

  md_files = expand_paths(args.inputs, args.ext)
  single_file = len(md_files) == 1
  if single_file:
    default_log = logging.warning
  else:
    default_log = logging.info
  for md_file in md_files:
    with md_file.open() as infile:
      try:
        metadata, content = parse(infile, parse_yaml=parse_yaml)
      except yaml.YAMLError as error:
        valid = False
        if single_file:
          raise
        elif args.validate and not args.find:
          print(md_file)
          print(f'{type(error).__name__}: {error}')
          continue
      else:
        valid = True
    if args.validate:
      if not valid:
        print(md_file)
      continue
    elif args.key:
      if metadata is None:
        default_log('No metadata found.')
        continue
      try:
        output = metadata[args.key]
      except KeyError:
        default_log(f'No key {args.key!r} found in the metadata.')
        continue
      if args.value is not None:
        if str(output) != args.value:
          continue
    elif args.meta:
      if metadata:
        output = metadata
      else:
        continue
    elif args.content:
      output = content
    else:
      fail('Must choose either --meta, --content, --validate, or --key.')
    if args.find:
      output = str(md_file)+'\n'
    output = format_output(output, args.trim)
    print(output, end='')


def expand_paths(input_paths, ext):
  output_paths = []
  for path in input_paths:
    if path.is_file():
      output_paths.append(path)
    elif path.is_dir():
      output_paths.extend(get_all_files(path, ext))
    elif path.exists():
      fail(f'Input path {path} is not a regular file or directory.')
    else:
      fail(f'Input path {path} not found.')
  return output_paths


def get_all_files(root_dir, ext=None):
  if ext:
    ext = '.'+ext
  for (dirpath_str, dirnames, filenames) in os.walk(root_dir):
    for name in filenames:
      path = pathlib.Path(dirpath_str,name)
      if not path.is_file():
        continue
      if ext is None or path.suffix == ext:
        yield path


def format_output(output, trim=False):
  if output is None:
    output = ''
  else:
    output = str(output).rstrip()+'\n'
  if trim:
    output = output.strip()
    if output:
      output += '\n'
  return output


def fail(message, print_msg=True):
  if print_msg:
    print(f'Error: {message}', file=sys.stderr)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception(message)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
