#!/usr/bin/env python
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import argparse
import subprocess
import collections
import ConfigParser

# _SCRIPT_DIR is the parent directory of _THIS_DIR, the directory this script is in. Since this will
# usually be included as a module in the "lib" submodule of a project, if we used this file's
# directory we'd get the commit of this submodule. Instead, cd to the directory above to get the
# commit of the main repo.
_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_SCRIPT_DIR = os.path.dirname(_THIS_DIR)
_DEFAULT_CONFIG_FILENAME = 'VERSION'


class Version(object):
  PRIMARY_KEYS = ('project', 'version_num', 'stage', 'commit')
  def __init__(self, **kwargs):
    for key in self.PRIMARY_KEYS:
      setattr(self, key, kwargs.get(key, None))
  @property
  def version(self):
    return str(self)
  def __str__(self):
    version = ''
    if self.version_num is None:
      return version
    else:
      version += self.version_num
    if self.stage is None:
      return version
    else:
      version += '-' + self.stage
    if self.commit is None:
      return version
    else:
      version += '+' + self.commit
    return version
  def __repr__(self):
    class_name = type(self).__name__
    kwarg_list = ['{}={}'.format(key, getattr(self, key)) for key in self.PRIMARY_KEYS]
    kwarg_str = ', '.join(kwarg_list)
    return class_name+'('+kwarg_str+')'


def get_version(config_path=None, repo_dir=None):
  """Get the full version string from a config file and/or commit hash.
  If a git commit can be obtained, it's the concatenation of version_num+commit.
  Otherwise it's just the version_num.
  If the version_num is not supplied, it tries to read it from disk using get_version_num()."""
  if config_path is None:
    config_path = os.path.join(_SCRIPT_DIR, _DEFAULT_CONFIG_FILENAME)
  config = _read_config(config_path)
  version = Version()
  if config is not None:
    version.project = config['project']
    version.version_num = config['version_num']
    version.stage = config['stage']
  commit = _get_git_commit(repo_dir)
  if commit is not None:
    version.commit = commit
  return version


def _get_git_commit(repo_dir=None):
  """Get the current git commit of this script."""
  # We have to cd to the repository directory because the --git-dir and --work-tree options don't
  # work on BSD. BUT: actually, it looks like on recent versions (FreeBSD 11.0) it might work.
  # Investigate.
  if repo_dir is None:
    repo_dir = _SCRIPT_DIR
  original_cwd = os.getcwd()
  try:
    if original_cwd != repo_dir:
      os.chdir(repo_dir)
    commit = _run_command(['git', 'log', '-n', '1', '--pretty=%h'], strip_newline=True)
  except OSError:
    return None
  finally:
    if original_cwd != os.getcwd():
      os.chdir(original_cwd)
  return commit


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


def _read_config(config_path):
  """
  Return None on failure."""
  KEYS = ('project', 'version_num', 'stage')
  data = collections.defaultdict(lambda: None)
  config = ConfigParser.RawConfigParser()
  try:
    result = config.read(config_path)
  except ConfigParser.Error:
    return None
  if not result:
    return None
  for key in KEYS:
    try:
      data[key] = config.get('version', key)
    except ConfigParser.Error:
      pass
  return data


def _make_argparser():
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config-path', default=os.path.join(_THIS_DIR, _DEFAULT_CONFIG_FILENAME))
  parser.add_argument('-r', '--repo-dir', default=_THIS_DIR)
  return parser


def _main(argv):
  parser = _make_argparser()
  args = parser.parse_args(argv[1:])
  version = get_version(config_path=args.config_path, repo_dir=args.repo_dir)
  print(version)


if __name__ == '__main__':
  sys.exit(_main(sys.argv))
