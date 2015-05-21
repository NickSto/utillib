import os
__version__ = '0.1'

DEFAULT_WIDTH = 70
DEFAULT_HEIGHT = 24


def termheight(default=None):
  return termsize(default_height=default)[0]


def termwidth(default=None):
  return termsize(default_width=default)[1]


def termsize(default_height=None, default_width=None):
  """Methods for obtaining size, in order of fallback:
  termsize_ioctl(): Get directly via ioctl system call. Real-time,
                    spawns no child process, Unix-only.
  termsize_stty():  Get from "stty" command. Real-time, spawns child
                    process, requires "stty" command.
  termsize_env():   Get from $LINES, $COLUMNS. Does not update after
                    program start.
  defaults:         Defaults given by named arguments to termsize().
  DEFAULTs:         Module defaults (DEFAULT_WIDTH, DEFAULT_HEIGHT).
  """
  if default_height is None:
    default_height = DEFAULT_HEIGHT
  if default_width is None:
    default_width = DEFAULT_WIDTH
  for method in (termsize_ioctl, termsize_stty, termsize_env):
    (height, width) = method()
    if height is not None and width is not None:
      return height, width
  return (default_height, default_width)


# Adapted from:
# https://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python/566752#566752
def termsize_ioctl():
  import sys
  for fd in (sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()):
    (height, width) = _ioctl_fd(fd)
    if isinstance(height, int) and isinstance(width, int):
      return (height, width)
  try:
    fd = os.open(os.ctermid(), os.O_RDONLY)
    (height, width) = _ioctl_fd(fd)
    os.close(fd)
  except:
    return (None, None)
  if isinstance(height, int) and isinstance(width, int):
    return (height, width)
  return (None, None)


def _ioctl_fd(fd):
  import struct
  try:
    import fcntl
    import termios
  except ImportError:
    return (None, None)
  try:
    data = fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234')
    return struct.unpack('hh', data)
  except:
    return (None, None)


def termsize_stty():
  """Get current terminal height and width, using stty command.
  Returns a tuple of (height, width) int's, or (None, None) on error.
  Requires Python 2.7."""
  import subprocess
  devnull = open(os.devnull, 'wb')
  try:
    output = subprocess.check_output(['stty', 'size'], stderr=devnull)
  except (OSError, subprocess.CalledProcessError):
    return (None, None)
  finally:
    devnull.close()
  fields = output.split()
  try:
    return (int(fields[0]), int(fields[1]))
  except (ValueError, IndexError):
    return (None, None)


def termsize_env():
  height = os.environ.get('LINES')
  width = os.environ.get('COLUMNS')
  if width is not None:
    try:
      width = int(width)
    except ValueError:
      width = None
  if height is not None:
    try:
      height = int(height)
    except ValueError:
      height = None
  return (height, width)
