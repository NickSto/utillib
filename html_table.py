import collections.abc
from typing import Any, Union, Optional, Sequence, Mapping, Dict, List, Set, cast
try:
  from IPython.display import HTML
except ImportError:
  HTML = None

RawRow = List[Union['Cell',Dict[str,Any]]]
RawRows = Optional[Union[RawRow,List[RawRow]]]

DEFAULT_HEADER_STYLE = {'bold':True}
BORDER_STYLE = '1px solid black'


class Table:
  def __init__(self, body: RawRows=None, header: RawRows=None, header_len: int=None,
    header_style: Dict[str,Any]=None, align='left', font: str=None, size: str=None,
    css: Union[str,Sequence[str]]=None
  ):
    """This represents an HTML table.
    For the table body and header, give a list of lists, one per row of the table.
    You can also give a 1D list, if your body or header only has one row.
    Each cell can be either a raw value to be displayed as str(value), or a dict containing the
    value and metadata about how to display the cell:
    `value`:   The value to display.
    `width`:   The width of the cell (will be used as the colspan value).
    `height`:  The height of the cell (the rowspan value).
    `align`:   The text-align CSS style. Choose between 'left', 'center', and 'right'.
               If 'width' is not 1 and 'align' is not given, this will be set to 'center'.
    `font`:    The font family, as a CSS value.
    `size`:    The font size, as a CSS value.
    `borders`: Which sides of the cell to put a border on. The sides are named 'left', 'right',
               'top', and 'bottom'. Give a single `str`, or a `tuple`/`list` of sides.
               This will use a standard border style of `{}`.
    `css`:     Arbitrary CSS to insert in the `style` attribute. Give a `str` of raw CSS or a
               `tuple`/`list` of CSS statements.
    The kwargs to this function that appear in the list above will be applied to the entire table.
    `header_style` is a dict you can fill with the metadata listed above, and it will be applied to
    every cell in the header row(s). Default: {!r}. The metadata will not overwrite any existing
    values set in each cell. The same goes for the data in `css`: existing values will be kept,
    and keys that exist in `header_style`'s `css` that don't exist in the cell's `css` will be
    be applied to cell.
    `header_len` can be used to divide a single `body` into header and body sections. Give the
    number of rows of the `body` that should be removed and stored in the `header`.
    """.format(BORDER_STYLE, DEFAULT_HEADER_STYLE)
    if header_style is None:
      header_style = DEFAULT_HEADER_STYLE.copy()
    self.header_style = header_style
    if header is None and header_len is not None and body is not None:
      self.header = Rows(body[:header_len], header=True)
      self.body = Rows(body[header_len:])
    else:
      self.header = Rows(header, header=True)
      self.body = Rows(body)
    self.align = align
    self.font = font
    self.size = size
    self.css = css

  @property
  def css(self):
    return self._css

  @css.setter
  def css(self, value):
    self._css = parse_css(value)

  @property
  def rows(self):
    return self.header + self.body

  def __iter__(self):
    for row in self.rows:
      yield row

  def __getitem__(self, index: int):
    if index < len(self.header):
      return self.header[index]
    else:
      bindex = index - len(self.header)
      return self.body[bindex]

  def __str__(self):
    html_lines = []
    style_str = get_style_str(**vars(self))
    if style_str:
      html_lines.append(f'<table {style_str}>')
    else:
      html_lines.append('<table>')
    if self.header:
      style_str = get_style_str(**self.header_style)
      if style_str:
        html_lines.append(f'  <thead {style_str}>')
      else:
        html_lines.append('  <thead>')
      html_lines.append(str(self.header))
      html_lines.append('  </thead>')
    if self.body:
      html_lines.append('  <tbody>')
      html_lines.append(str(self.body))
      html_lines.append('  </tbody>')
    html_lines.append('</table>')
    return '\n'.join(html_lines)

  def render(self) -> HTML:
    return HTML(str(self))

  def add_border(self, dim: str, position: int, section: str=None, style=BORDER_STYLE) -> None:
    """Add a border to a table.
    `dim`: Which dimension of border ('rows' or 'cols')
    `position`: Where to add the border. Give a row or column number.
                It will add it to the right or bottom side of the 0-indexed row or column.
    `section`: Which section ('header' or 'body') to apply the border to. If given, the `position`
               will mean the position within the given section. If not, the `position` will be
               row/column of the entire table.
    `style`: The CSS value to use as the `border-top` or `border-left` value."""
    if dim.startswith('row') or dim.startswith('hor'):
      dim = 'rows'
    elif dim.startswith('col') or dim.startswith('vert'):
      dim = 'cols'
    if section == 'header':
      rows = self.header
    elif section == 'body':
      rows = self.body
    else:
      rows = self.rows
    # Add border styles.
    #TODO: Keep track of actual `r` vertical position, taking into account `height`s of the cells.
    #TODO: Store borders as Table metadata and only apply them in `__str__()`.
    for r, row in enumerate(rows):
      r_pos = r
      c_pos = 0
      for c, cell in enumerate(row):
        if dim == 'rows' and r_pos == position:
          if style == BORDER_STYLE:
            cell.borders.add('top')
          else:
            cell.css['border-top'] = style
        elif dim == 'cols' and c_pos == position:
          if style == BORDER_STYLE:
            cell.borders.add('left')
          else:
            cell.css['border-left'] = style
        if isinstance(cell, dict):
          c_pos += cell.get('width', 1) or 1
        else:
          c_pos += 1


class ListLike:

  def __init__(self, item_type):
    self._items = []
    self.item_type = item_type

  def _cast(self, item):
    if isinstance(item, self.item_type):
      return item
    else:
      return self.item_type(item)

  def __getitem__(self, index):
    return self._items[index]

  def __setitem__(self, index, item):
    self._items[index] = self._cast(item)

  def __len__(self):
    return len(self._items)

  def __add__(self, other):
    return self._items + other._items

  def __iter__(self):
    for item in self._items:
      yield item

  def append(self, item):
    self._items.append(self._cast(item))


class CellGroup(ListLike):

  def __repr__(self):
    class_name = type(self).__name__
    if self.header is None:
      header_str = ''
    else:
      header_str = f', header={self.header}'
    return f'{class_name}({self._items!r}{header_str})'


class Rows(CellGroup):

  def __init__(self, raw_rows: RawRows=None, header=False):
    super().__init__(Row)
    self._items: List[Row]
    self.header = header
    if not raw_rows:
      raw_rows = cast(RawRows, [])
    elif isinstance(raw_rows[0], str) or not isinstance(raw_rows[0], collections.abc.Iterable):
      # It's a single row.
      raw_row = cast(RawRow, raw_rows)
      raw_rows = [raw_row]
    for raw_row in raw_rows:
      self.append(raw_row)

  def __str__(self):
    html_lines = []
    for row in self:
      copy = row.copy()
      if copy.header is None:
        copy.header = self.header
      html_lines.append(str(copy))
    return '\n'.join(html_lines)


class Row(CellGroup):

  def __init__(self, raw_row: RawRow=None, header=None):
    super().__init__(Cell)
    self._items: List[Cell]
    self.header = header
    if not raw_row:
      raw_row = []
    for raw_cell in raw_row:
      self.append(raw_cell)

  def copy(self):
    return type(self)(self, header=self.header)

  def __str__(self):
    html_lines = []
    html_lines.append('    <tr>')
    for cell in self:
      if self.header != cell.header:
        final_cell = cell.copy()
        final_cell.header = self.header
      else:
        final_cell = cell
      html_lines.append('      '+str(final_cell))
    html_lines.append('    </tr>')
    return '\n'.join(html_lines)


class Cell:

  METADATA = {
    'header': {'default':False, 'type':bool},
    'width':  {'default':1, 'type':int},
    'height': {'default':1, 'type':int},
    'align':  {'default':'left', 'type':str},
    'font':   {'default':None, 'type':str},
    'size':   {'default':None, 'type':str},
    'bold':   {'default':False, 'type':bool},
    'borders':{'default':set(), 'type':set, 'raw_type':Union[str,Sequence[str],Set[str]]},
    'css':    {'default':{}, 'type':dict, 'raw_type':Union[str,Sequence[str],Mapping[str,Any]]},
  }

  def __init__(self, raw_cell: Any=None, value: Any=None, **kwargs):
    if isinstance(raw_cell, type(self)):
      type(self).copy(raw_cell, self)
      return
    self.init_attrs(**kwargs)
    if isinstance(raw_cell, collections.abc.Mapping):
      self.value = raw_cell.get('value')
      self.init_attrs(**raw_cell)
    elif raw_cell is None:
      self.value = value
    else:
      self.value = raw_cell

  @property
  def borders(self):
    return self._borders
  
  @borders.setter
  def borders(self, value):
    if isinstance(value, str):
      self._borders = set((value,))
    elif isinstance(value, collections.abc.Iterable):
      # A `set` is an iterable too.
      self._borders = set(value)
    elif value is None:
      self._borders = set()
    else:
      raise ValueError(f"'borders' must be a `str` or sequence of `str`s. Saw: {value!r}")

  @property
  def css(self):
    return self._css

  @css.setter
  def css(self, value):
    self._css = parse_css(value)

  def init_attrs(self, **kwargs):
    for attr, metadata in self.METADATA.items():
      if attr in kwargs:
        raw_value = kwargs[attr]
      else:
        raw_value = metadata['default']
      # Don't know if this cast really accomplishes anything, but why not.
      value = cast(metadata['type'], raw_value)
      setattr(self, attr, value)

  def apply(self, overwrite=True, **kwargs):
    """Set several properties at once."""
    for key, value in kwargs.items():
      if key == 'css':
        for ckey, cvalue in value.items():
          if overwrite or not self.css.get(ckey):
            self.css[ckey] = cvalue
      elif hasattr(self, key):
        if overwrite:
          setattr(self, key, value)
        elif getattr(self, key) is None:
          setattr(self, key, value)

  def copy(self, copy: 'Cell'=None):
    if copy is None:
      copy = type(self)()
    if hasattr(self.value, 'copy'):
      copy.value = self.value.copy()
    else:
      copy.value = self.value
    copy.init_attrs(**vars(self))
    return copy

  def __repr__(self):
    class_name = type(self).__name__
    kwarg_pairs = []
    if self.value is not None:
      kwarg_pairs.append(('value', repr(self.value)))
    for attr, metadata in self.METADATA.items():
      value = getattr(self, attr)
      if value != metadata['default']:
        kwarg_pairs.append((attr, repr(value)))
    kwarg_strs = [f'{attr}={value}' for attr, value in kwarg_pairs]
    kwarg_str = ', '.join(kwarg_strs)
    return f'{class_name}({kwarg_str})'

  def __str__(self):
    attributes = []
    if self.header:
      tag = 'th'
      attributes.append('scope="col"')
    else:
      tag = 'td'
    if self.width != 1:
      attributes.append(f'colspan={self.width}')
    if self.height != 1:
      attributes.append(f'rowspan={self.height}')
    style_str = get_style_str(**vars(self))
    if style_str:
      attributes.append(style_str)
    if attributes:
      attributes_html = ' '+' '.join(attributes)
    else:
      attributes_html = ''
    if self.value is None:
      value = ''
    else:
      value = self.value
    return f'<{tag}{attributes_html}>{value}</{tag}>'


def parse_css(value):
  css = {}
  if isinstance(value, str):
    for statement in value.split(';'):
      key, value = parse_css_statement(statement)
      css[key] = value
  elif isinstance(value, collections.abc.Mapping):
    css = dict(value)
  elif isinstance(value, collections.abc.Iterable):
    for statement in value:
      key, value = parse_css_statement(statement)
      css[key] = value
  elif value is not None:
    raise ValueError(f"'css' must be a `str`, sequence of `str`, or a mapping. Saw: {value!r}")
  return css


def parse_css_statement(statement):
  try:
    key, value = statement.split(':')
  except ValueError as error:
    error.args = (f'Invalid CSS statement: {statement!r}',)
    raise error
  return key.strip(), value.strip()


def get_style_str(
    font: str=None, size: str=None, align: str=None, bold: bool=None, borders: Set[str]=None,
    css: Mapping[str,Any]=None, **kwargs
  ) -> str:
  if css is None:
    css = {}
  else:
    css = dict(css)
  if font:
    css['font-family'] = font
  if size:
    css['font-size'] = size
  if align:
    css['text-align'] = align
  if bold:
    css['font-weight'] = 'bold'
  if borders:
    for border in borders:
      css[f'border-{border}'] = BORDER_STYLE
  if css:
    css_statements = [f'{key}: {value}' for key, value in css.items()]
    return 'style="{}"'.format('; '.join(css_statements))
  else:
    return ''
