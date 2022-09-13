#!/usr/bin/env python3
import argparse
import logging
import os
import pathlib
import sys
import yaml

# Looks like https://pypi.org/project/frontmatter/ can already do this?
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
    help='Just print the graymatter YAML. Or, when used with --find, match files which have '
      'graymatter metadata.')
  options.add_argument('-c', '--content', action='store_true',
    help='Omit the graymatter and just print the content.')
  options.add_argument('-k', '--key',
    help='Just print the value of this key from the metadata.')
  options.add_argument('-v', '--value',
    help='Print files where the value of --key matches this. Only valid with --find and --key. '
      'The metadata value will be converted to a str before comparison.')
  options.add_argument('-E', '--ignore-empty', action='store_true',
    help='When using --find --key (with no --value), ignore files which contain the --key but '
      "with no value (the value is None or ''). For example: `title: ` or `date: ''`.")
  options.add_argument('-t', '--trim', action='store_true',
    help='Trim whitespace one either side of the output.')
  options.add_argument('-V', '--validate', action='store_true',
    help='Only validate yaml syntax. Will print any errors found while parsing the file(s). '
      'When used with --find, this will print all files that validated.')
  options.add_argument('-f', '--find', action='store_true',
    help='Just find files that match the given criteria: contain the --key, --validates)')
  options.add_argument('-n', '--not', dest='find_matches', action='store_false', default=True,
    help="When using --find, print files that *don't* match the criteria. Like grep's -v flag.")
  options.add_argument('-l', '--list-filename', action='store_true',
    help='When extracting data (e.g. not using --find or --validate), prepend with the filename, '
      'like the default grep -R output. Except this will separate the filename from the data with '
      'reliable tab character instead of a colon.')
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

  # Compile the list of files to examine.
  md_files = expand_paths(args.inputs, args.ext)
  single_file = len(md_files) == 1
  # If we're just examining a single file, the default verbosity should be INFO.
  if single_file and args.volume == logging.WARNING:
    logging.getLogger().setLevel(logging.INFO)

  # Process each file.
  for md_path in md_files:
    # Parse contents.
    metadata, content, error = parse_contents(md_path, parse_yaml=parse_yaml)
    if error:
      error: Exception
      if single_file:
        raise error
      elif args.validate and not args.find:
        # We're validating multiple files. Print the file and error.
        # If --find was given with --validate, we just want a list of files, not the full errors.
        print(md_path)
        print(f'  {type(error).__name__}: {error}')
        continue
    # Use the contents.
    if args.find:
      # If we're just --find-ing and listing matching files, check if this matches, print if it
      # does, then move on to the next file.
      is_match = file_matches(
        metadata, args.key, args.value, args.meta, args.validate, error,
        ignore_empty=args.ignore_empty
      )
      if (args.find_matches and is_match) or (not args.find_matches and not is_match):
        print(md_path)
      continue
    elif args.key or args.meta or args.content:
      # Get the requested output and print it.
      try:
        data = get_output(content, metadata, args.key, args.meta, args.content)
      except NoData:
        continue
      output = format_output(data, args.trim)
      if args.list_filename:
        if output == '':
          output = '\n'
        output = f'{md_path}\t{output}'
      print(output, end='')
    elif not args.validate:
      fail('Must provide at least one of --find, --validate, --key, --meta, or --content.')


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


def parse_contents(md_path, parse_yaml=True):
  with md_path.open() as md_file:
    try:
      metadata, content = parse(md_file, parse_yaml=parse_yaml)
    except (yaml.YAMLError, UnicodeDecodeError) as error:
      return None, None, error
    else:
      return metadata, content, None


def file_matches(metadata, key, value, find_metadata, validate, error, ignore_empty=False):
  if validate:
    if error:
      return False
    else:
      return True
  if metadata is None or metadata == '':
    logging.info('No metadata found.')
    if key or value or find_metadata:
      return False
    else:
      return None
  elif find_metadata:
    return True
  if key:
    try:
      actual_value = metadata[key]
    except KeyError:
      return False
    if value is not None:
      if value == str(actual_value):
        return True
      else:
        return False
    elif ignore_empty:
      if actual_value == '' or actual_value is None:
        return False
      else:
        return True
    else:
      return True


def get_output(content, metadata, key, get_metadata, get_content):
  """Get the specified data from the file.
  If the data is not present (e.g. the requested key is not in the metadata), this will raise a
  NoData exception. This is necessary because we want `None` (and every other data type) to be a
  valid return value."""
  if key:
    if metadata is None:
      logging.info('No metadata found.')
      raise NoData('No metadata.')
    try:
      return metadata[key]
    except KeyError:
      logging.info(f'No key {key!r} found in the metadata.')
      raise NoData('Requested key not present.')
  elif get_metadata:
    if metadata:
      return metadata
    else:
      logging.info('No metadata found.')
      raise NoData('No metadata.')
  elif get_content:
    return content
  else:
    raise RuntimeError(
      'Illegal argument combination. '
      'Must provide at least one of `key`, `get_metadata`, or `get_content`.'
    )


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


class NoData(RuntimeError):
  """The requested data was not found."""
  pass


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
