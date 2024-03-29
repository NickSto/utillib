"""A wrapper for textwrap, to simplify its usage and add an important capability."""
# This should currently be compatible with Python 2.7 and 3.
import textwrap
try:
  import console
except ImportError:
  from . import console
__version__ = '0.10'

DEFAULT_WIDTH = 70

def wrap(text, width=None, width_mod=None, indent=0, lspace=0, **kwargs):
  """Take any input text and return output where no line is longer than "width".
  It preserves existing newlines, unlike textwrap. So it will simply look at
  each line, and if it's longer than "width" it will break it there. This
  means that any pre-wrapped text will look terrible if wrapped to a smaller
  with, so remember not to pre-wrap!
  width
    The maximum line length. If "width" is not given, it will try to determine
  the current terminal width using console.termwidth().
  lspace
    Number of spaces to prepend to each line. Counts toward the line width.
  indent
    Number of spaces to prepend to the first line (in addition to any lspace).
  Also counts toward line with.
  All other keyword arguments will be passed to textwrap.wrap(). N.B.: if
  "subsequent_indent" or "initial_indent" are given, then "lspace" and
  "indent" will be ignored."""
  wrapper = Wrapper(width=width, indent=indent, lspace=lspace, width_mod=width_mod, **kwargs)
  return wrapper.wrap(text)


def wrapper(width=None, width_mod=None, indent=0, lspace=0, **kwargs):
  """Return a function that performs wrapping with the same settings each time.
  Allows defining a shorthand for the full wrap function:
  wrap_short = simplewrapper.wrapper(width=70, indent=4)
  print wrap_short('Now you can just give this argument the text, and it will '
    +'wrap it to 70 characters with an indent of 4 each time.')"""
  return lambda text: wrap(text, width, width_mod, indent, lspace, **kwargs)


class Wrapper(object):
  """Same interface as the stand-alone wrap() function.
  Here, you give the parameters when creating the object, so then you only need
  to provide the text itself to the wrap() function. But you can also change
  certain attributes after creation."""

  def __init__(self, width=None, width_mod=None, indent=0, lspace=0, **kwargs):
    self._textwrapper = textwrap.TextWrapper(**kwargs)
    if width is None:
      self.width = console.termwidth(DEFAULT_WIDTH)
    if width_mod is not None:
      self.width += width_mod
    if not (kwargs.get('subsequent_indent') or kwargs.get('initial_indent')):
      self.lspace = lspace
      self.indent = indent

  def wrap(self, text, width=None, width_mod=None, indent=None, lspace=None):
    """Note: Attributes given here are temporary (only take effect for this
    invocation of wrap())."""
    # set temporary attributes
    if width is not None or width_mod is not None:
      width_old = self.width
    if width is not None:
      self.width = width
    if width_mod is not None:
      self.width += width_mod
    if lspace is not None:
      lspace_old = self.lspace
      self.lspace = lspace
    if indent is not None:
      indent_old = self.indent
      self.indent = indent
    # do wrapping
    wrapped = []
    for line in text.splitlines():
      wrapped_lines = self._textwrapper.wrap(line)
      if wrapped_lines:
        wrapped.extend(wrapped_lines)
      else:
        # textwrap returns an empty list when given an empty string.
        # But we don't want to remove empty lines.
        wrapped.append('')
    wrapped_str = '\n'.join(wrapped)
    # restore permanent attributes
    if width is not None or width_mod is not None:
      self.width = width_old
    if lspace is not None:
      self.lspace = lspace_old
    if indent is not None:
      self.indent = indent_old
    return wrapped_str

  # attributes are only an interface to the TextWrapper's attributes
  @property
  def width(self):
    return self._textwrapper.width
  @width.setter
  def width(self, width):
    if width <= 0:
      width = 1
    self._textwrapper.width = width

  @property
  def lspace(self):
    return len(self._textwrapper.subsequent_indent)
  @lspace.setter
  def lspace(self, lspace):
    if lspace < 0:
      lspace = 0
    # this order is important
    self._textwrapper.initial_indent = ' ' * (self.indent + lspace)
    self._textwrapper.subsequent_indent = ' ' * lspace

  @property
  def indent(self):
    return len(self._textwrapper.initial_indent) - len(self._textwrapper.subsequent_indent)
  @indent.setter
  def indent(self, indent):
    if indent + self.lspace < 0:
      indent = -self.lspace
    self._textwrapper.initial_indent = ' ' * (indent + self.lspace)

