#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import argparse
import subprocess

# The parent directory of the directory this script is in. Since this will usually be included as a
# module in the "lib" submodule of a project, if we used this file's directory we'd get the commit
# of the submodule. Instead, cd to the directory above to get the commit of the main repo.
_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
_DEFAULT_VERSION_FILENAME = 'VERSION'


def get_git_commit(git_dir=None):
  """Get the current git commit of this script."""
  # We have to cd to the repository directory because the --git-dir and --work-tree options don't
  # work on BSD. BUT: actually, it looks like on recent versions (FreeBSD 11.0) it might work.
  # Investigate.
  if git_dir is None:
    git_dir = _SCRIPT_DIR
  original_cwd = os.getcwd()
  try:
    if original_cwd != git_dir:
      os.chdir(git_dir)
    commit = _run_command(['git', 'log', '-n', '1', '--pretty=%h'], strip_newline=True)
  except OSError:
    return None
  finally:
    if original_cwd != os.getcwd():
      os.chdir(original_cwd)
  return commit


def get_version_num(version_filepath):
  """Get the version number from a file on disk.
  Returns the first line from the file, stripped of newlines. Returns None on failure.
  Should be something like "1.0" or "0.2.1-alpha"."""
  if version_filepath:
    try:
      with open(version_filepath, 'rU') as version_file:
        return version_file.readline().rstrip('\r\n')
    except IOError:
      return None


def get_version(version_num=None, version_filepath=None):
  """Get the full version string.
  If a git commit can be obtained, it's the concatenation of version_num+commit.
  Otherwise it's just the version_num.
  If the version_num is not supplied, it tries to read it from disk using get_version_num()."""
  if version_filepath is None:
    version_filepath = os.path.join(_SCRIPT_DIR, _DEFAULT_VERSION_FILENAME)
  if version_num is None:
    version_num = get_version_num(version_filepath)
  if version_num:
    commit = get_git_commit()
    if commit:
      return '{}+{}'.format(version_num, commit)
    else:
      return str(version_num)
  elif commit:
    return commit
  else:
    return None


def _run_command(command, strip_newline=False):
  devnull = open(os.devnull, 'w')
  try:
    output = subprocess.check_output(command, stderr=devnull)
    exit_status = 0
  except subprocess.CalledProcessError as cpe:
    output = cpe.output
    exit_status = cpe.returncode
  except OSError:
    exit_status = None
  finally:
    devnull.close()
  if exit_status is None or exit_status != 0:
    return None
  elif strip_newline:
    return output.rstrip('\r\n')
  else:
    return output


def _make_argparser():
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--version-path')
  parser.add_argument('-g', '--git-dir')
  return parser


def _main(argv):
  parser = _make_argparser()
  args = parser.parse_args(argv[1:])
  print(get_version(version_filepath=args.version_path))
  print(get_git_commit(git_dir=args.git_dir))


if __name__ == '__main__':
  sys.exit(_main(sys.argv))
