#!/usr/bin/env python3
import collections.abc
import logging
import math
from typing import Any, Union, Optional, Callable, Sequence, Mapping, Generator, Iterable, Dict, List, Tuple, Set, cast
try:
  from IPython.display import HTML
except ImportError:
  HTML = None

RawRow = List[Union['Cell',Dict[str,Any]]]
RawRows = Optional[Union[RawRow,List[RawRow]]]
RawStyle = Union['Style',Dict[str,Any]]

DEFAULT_HEADER_STYLE = {'bold':True}
BORDER_STYLE = '1px solid black'


class Styled:

  def init_style(self, kwargs: Dict[str,Any]) -> Set[str]:
    unused = set()
    style_kwargs = {}
    for key, value in kwargs.items():
      if key in Style.METADATA:
        style_kwargs[key] = value
      else:
        unused.add(key)
    self.style = style_kwargs
    return unused

  def __getattr__(self, attr: str) -> Any:
    if attr in Style.METADATA:
      return getattr(self.style, attr)
    else:
      object.__getattribute__(self, attr)

  def __setattr__(self, attr: str, value: Any):
    if attr == 'style':
      if isinstance(value, Style):
        object.__setattr__(self, 'style', value)
      elif isinstance(value, collections.abc.Mapping):
        object.__setattr__(self, 'style', Style(**value))
      else:
        raise ValueError(f"'style' attribute can only be set to a Style object or a mapping.")
    elif attr in Style.METADATA:
      setattr(self.style, attr, value)
    else:
      object.__setattr__(self, attr, value)


class Table(Styled):
  def __init__(self, body: RawRows=None, header: RawRows=None, header_len: int=None,
    header_style: RawStyle=None, **kwargs: Mapping[str,Any]
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
    `css`:     Arbitrary CSS to insert in the `style` attribute. Give a `dict` mapping properties to
               values or an iterable of CSS statements (e.g. `padding: 1px`) or a `str` (a single
               CSS statement).
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
    if header is None and header_len is not None and body is not None:
      self.header = body[:header_len]
      self.body = body[header_len:]
    else:
      self.header = header
      self.body = body
    self.header.style = header_style
    self.init_style(kwargs)

  @property
  def header_style(self) -> 'Style':
    return self.header.style

  @header_style.setter
  def header_style(self, raw_style: RawStyle):
    self.header.style = raw_style

  @property
  def header(self) -> 'Rows':
    return self._header

  @header.setter
  def header(self, raw_header: RawRows) -> None:
    self._header = Rows(raw_header, header=True)

  @property
  def body(self) -> 'Rows':
    return self._body

  @body.setter
  def body(self, raw_body: RawRows) -> None:
    self._body = Rows(raw_body)

  @property
  def rows(self) -> 'Rows':
    return self.header + self.body

  @property
  def width(self) -> Optional[int]:
    #TODO: This is not always accurate, even with a table that appears to have equal width rows.
    #      In such a table, if a cell has a rowspan > 1, the following row will have a smaller
    #      total colspan, since the cell in the row above takes the place of one of its cells.
    try:
      row = self[0]
    except IndexError:
      return None
    width = 0
    for cell in row:
      width += cell.width
    return width

  @property
  def height(self):
    #TODO: I think this is not always accurate, if you have the wrong combination of rowspans.
    return len(self)

  def __len__(self) -> int:
    return len(self.header) + len(self.body)

  def __iter__(self) -> Generator['Row',None,None]:
    for row in self.rows:
      yield row

  def __getitem__(self, index: int) -> 'Row':
    if index < len(self.header):
      return self.header[index]
    else:
      bindex = index - len(self.header)
      return self.body[bindex]

  def __repr__(self) -> str:
    class_name = type(self).__name__
    arg_strs: List[str] = []
    if self.body:
      arg_strs.append(repr(self.body))
    if self.header:
      arg_strs.append(f'header={self.header!r}')
    for attr, metadata in Style.METADATA.items():
      value = getattr(self, attr)
      if value != metadata['default']:
        arg_strs.append(f'{attr}={value!r}')
    return f'{class_name}('+', '.join(arg_strs)+')'

  def to_text(self, delim='\t', row_delim='\n') -> str:
    sections = []
    for section in self.header, self.body:
      if section:
        sections.append(section.to_text(delim=delim, row_delim=row_delim))
    return row_delim.join(sections)

  def to_html(self, indents=0, indent='  ') -> str:
    html_lines = []
    attr_str = self.style.to_attr_str()
    html_lines.append(indent*indents+f'<table{attr_str}>')
    if self.header:
      html_lines.append(self.header.to_html(indents=(indents+1), indent=indent))
    if self.body:
      html_lines.append(self.body.to_html(indents=(indents+1), indent=indent))
    html_lines.append(indent*indents+'</table>')
    return '\n'.join(html_lines)

  def deep_apply(self, **kwargs: Mapping[str,Any]) -> None:
    """Apply styles directly to every Cell."""
    self.header.deep_apply(**kwargs)
    self.body.deep_apply(**kwargs)

  def extend(self, other, direction='down'):
    #TODO: Keep header rows looking like headers and body rows looking like bodies.
    if direction == 'down':
      self.body += other.rows
    elif direction == 'right':
      max_len = max(len(self), len(other))
      orig_width = self.width
      for i in range(max_len):
        try:
          row = self[i]
        except IndexError:
          row = Row([None] * orig_width)
          self.body.append(row)
        try:
          other_row = other[i]
        except IndexError:
          other_row = Row([None] * other.width)
        row.extend(other_row)

  def render(self) -> HTML:
    return HTML(self.to_html())

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
        c_pos += cell.width

  @classmethod
  def make_freq_table(
      cls,
      freqs: Mapping[Any,int],
      labels: Optional[Mapping]=None,
      headers: Optional[Mapping[int,Union[str,'Cell']]]=None,
      max_rows: Optional[int]=None,
      ranks: bool=True,
      splitter: Optional[Callable[[Any],Sequence]]=None,
      order: Sequence=()
    ) -> 'Table':
    """Create a Table from a dict mapping values to counts of how often each value occurs.
    This automatically sorts them by frequency, calculates the total and the percent of it each
    count represents, and formats everything for readability.
    `labels`: A dict mapping the raw keys in `freqs` to the display names which should be shown in
      the table.
    `headers`: Alternate text to show in the header row of the table. Give a dict mapping the
      column number to the string to display. The "rank"s column is 0, the "values" column is 1,
      and so on. This indexing is the same ("values" is still 1) if the ranks column is omitted.
    `max_rows`: Only show the top `max_rows` values.
    `ranks`: Whether to show the "ranks" column (True) or not (False).
    `splitter`: A function which will turn any of the values (`freqs` keys) into multiple columns.
      It should take a key from `freqs` and return a sequence of values, dicts, or Cells (the same
      format as a row you'd give to Table).
    `order`: A custom order to sort the rows by, instead of sorting them by frequency. Give a list
      of values matching the keys in the `freqs` argument, in the order they should be displayed.
      Not all keys in `freqs` must be given. Those omitted will be put after those included.
    """
    if len(freqs) < 1:
      raise ValueError('Frequency dict is empty!')
    if labels is None:
      labels = {}
    if headers is None:
      headers = {}
    all_items = sorted(freqs.items(), key=lambda item: (-item[1], item[0]))
    if order:
      keys = [item[0] for item in all_items]
      reordered_keys = partially_order(keys, order)
      all_items = [(key,freqs[key]) for key in reordered_keys]
    total = sum([row[1] for row in all_items])
    if max_rows is not None and len(all_items) > max_rows:
      items = all_items[:max_rows]
      trunc = True
    else:
      items = all_items
      trunc = False
    max_round_to = 0
    for value, count in items:
      max_round_to = max(max_round_to, get_round_to(100*count/total, 1))
    format_str = f'{{:0.{max_round_to}f}} %'
    rows = []
    labels_len = None
    for row_num, (value, count) in enumerate(items, 1):
      pct = 100*count/total
      if int(pct) == pct:
        pct_str = str(int(pct))
        align = 'left'
      else:
        pct_str = format_str.format(pct)
        align = 'right'
      if splitter is None:
        label_cells = [labels.get(value, value)]
        labels_len = 1
      else:
        label_cells = list(splitter(value))
        this_labels_len = len(label_cells)
        if labels_len is None:
          labels_len = this_labels_len
        elif this_labels_len != labels_len:
          raise ValueError(
            f'Splitter returned inconsistent number of columns ({labels_len} != {this_labels_len})'
          )
      row = label_cells + [{'value':f'{count:,}', 'align':'right'}, {'value':pct_str, 'align':align}]
      if ranks:
        row = [row_num] + row
      rows.append(row)
    if trunc:
      rows.append([{'value':'...', 'width':3, 'align':'center'}])
    summary = ['(Total)', {'value':f'{total:,}', 'align':'right'}, format_str.format(100)]
    if ranks:
      summary = [''] + summary
    rows.append(summary)
    # Determine the headers row.
    default_headers = {
      0:'', 1:{'value':'Value', 'width':labels_len},
      1+labels_len:{'value':'Count', 'align':'right'},
      2+labels_len:{'value':'Percent', 'align':'right'}
    }
    for i, header_cell in default_headers.items():
      if i not in headers:
        headers[i] = header_cell
    headers_row = []
    for i, header_cell in sorted(headers.items(), key=lambda item: item[0]):
      if i != 0 or ranks:
        headers_row.append(header_cell)
    return cls(rows, header=headers_row)


class ListLike:

  def __init__(self, item_type: type):
    self._items = []
    self.item_type = item_type

  def _cast(self, item):
    if isinstance(item, self.item_type):
      return item
    else:
      return self.item_type(item)

  def __getitem__(self, index: int):
    return self._items[index]

  def __setitem__(self, index: int, item):
    self._items[index] = self._cast(item)

  def __delitem__(self, index: int):
    del self._items[index]

  def __len__(self):
    return len(self._items)

  def __add__(self, other: 'ListLike') -> 'ListLike':
    if hasattr(self, 'copy') and hasattr(self.copy, '__call__'):
      copy = self.copy()
      copy._items += other._items
      return copy
    else:
      return type(self)(self._items + other._items)

  def __iter__(self):
    for item in self._items:
      yield item

  def append(self, item):
    self._items.append(self._cast(item))

  def insert(self, index: int, item):
    self._items.insert(index, self._cast(item))

  def extend(self, items):
    if type(items) == type(self):
      self._items.extend(items._items)
    elif type(items[0]) == self.item_type:
      self._items.extend([self._cast(item) for item in items])
    else:
      self_type = type(self).__name__
      raise ValueError(
        f'Argument to {self_type}.extend() must be either a {self_type} or a sequence of '
        f'{self.item_type.__name__}s.'
      )


class CellGroup(ListLike):

  def copy(self):
    return type(self)(self, header=self.header)

  def __repr__(self) -> str:
    class_name = type(self).__name__
    if self.header is None:
      header_str = ''
    else:
      header_str = f', header={self.header}'
    return f'{class_name}({self._items!r}{header_str})'


class Rows(CellGroup, Styled):

  def __init__(self, raw_rows: RawRows=None, header=False, **kwargs: Mapping[str,Any]):
    super().__init__(Row)
    self._items: List[Row]
    self.header = header
    self.init_style(kwargs)
    if not raw_rows:
      raw_rows = cast(RawRows, [])
    elif isinstance(raw_rows[0], str) or not isinstance(raw_rows[0], collections.abc.Iterable):
      # It's a single row.
      raw_row = cast(RawRow, raw_rows)
      raw_rows = [raw_row]
    for raw_row in raw_rows:
      self.append(raw_row)

  def __str__(self) -> str:
    return '['+', '.join([str(row) for row in self])+']'

  def to_text(self, delim='\t', row_delim='\n') -> str:
    return row_delim.join([row.to_text(delim=delim) for row in self])

  def to_html(self, indents=0, indent='  ') -> str:
    html_lines = []
    if self.header:
      tag = 'thead'
    else:
      tag = 'tbody'
    attr_str = self.style.to_attr_str()
    html_lines.append(indent*indents+f'<{tag}{attr_str}>')
    for row in self:
      copy = row.copy()
      if copy.header is None:
        copy.header = self.header
      html_lines.append(copy.to_html(indents=(indents+1), indent=indent))
    html_lines.append(indent*indents+f'</{tag}>')
    return '\n'.join(html_lines)

  def deep_apply(self, **kwargs: Mapping[str,Any]) -> None:
    """Apply styles directly to every Cell."""
    for row in self:
      row.deep_apply(**kwargs)


class Row(CellGroup, Styled):

  def __init__(self, raw_row: RawRow=None, header=None, **kwargs: Mapping[str,Any]):
    super().__init__(Cell)
    self._items: List[Cell]
    self.header = header
    self.init_style(kwargs)
    if not raw_row:
      raw_row = []
    for raw_cell in raw_row:
      self.append(raw_cell)

  def __str__(self) -> str:
    return '('+self.to_text(delim=', ')+')'

  def to_text(self, delim='\t') -> str:
    return delim.join([str(cell) for cell in self])

  def to_html(self, indents=0, indent='  ') -> str:
    html_lines = []
    attr_str = self.style.to_attr_str()
    html_lines.append(indent*indents+f'<tr{attr_str}>')
    for cell in self:
      if self.header != cell.header:
        final_cell = cell.copy()
        final_cell.header = self.header
      else:
        final_cell = cell
      html_lines.append(indent*(indents+1)+final_cell.to_html())
    html_lines.append(indent*indents+'</tr>')
    return '\n'.join(html_lines)

  def deep_apply(self, **kwargs: Mapping[str,Any]) -> None:
    """Apply styles directly to every Cell."""
    for cell in self:
      cell.apply(**kwargs)


class Cell(Styled):

  ATTR_DEFAULTS = {'width':1, 'height':1, 'header':None}

  def __init__(self, raw_cell: Any=None, value: Any=None, **kwargs):
    if isinstance(raw_cell, type(self)):
      type(self).copy(raw_cell, self)
      return
    unused = self.init_all(kwargs)
    if isinstance(raw_cell, collections.abc.Mapping):
      self.value = raw_cell.get('value')
      unused = self.init_all(raw_cell, ignore={'value'})
    elif raw_cell is None:
      self.value = value
    else:
      self.value = raw_cell
    if not kwargs.get('align') and is_number(self.value):
      self.style.align = 'right'

  def init_all(self, kwargs: Mapping[str,Any], ignore=None):
    unused_attrs = self.init_attrs(kwargs)
    unused_styles = self.init_style(kwargs)
    unused = unused_attrs & unused_styles
    if ignore is not None:
      unused = unused - ignore
    if unused:
      class_name = type(self).__name__
      unused_str = ', '.join([repr(attr) for attr in unused])
      raise AttributeError(f'{class_name!r} object has no attribute(s) {unused_str}')

  def init_attrs(self, kwargs: Mapping[str,Any]) -> Set[str]:
    unused = set(kwargs.keys())
    for attr, default in self.ATTR_DEFAULTS.items():
      if attr in kwargs:
        setattr(self, attr, kwargs[attr])
        unused.remove(attr)
      else:
        setattr(self, attr, default)
    return unused

  def apply(self, overwrite=True, **kwargs: Mapping[str,Any]):
    """Set several properties at once."""
    for key, value in kwargs.items():
      if key == 'css':
        for ckey, cvalue in value.items():
          if overwrite or not self.style.css.get(ckey):
            self.style.css[ckey] = cvalue
      elif hasattr(self.style, key):
        if overwrite:
          setattr(self.style, key, value)
        elif getattr(self.style, key) is None:
          setattr(self.style, key, value)

  def copy(self, copy: 'Cell'=None) -> 'Cell':
    if copy is None:
      copy = type(self)()
    if hasattr(self.value, 'copy'):
      copy.value = self.value.copy()
    else:
      copy.value = self.value
    copy.style = self.style.copy()
    copy.init_attrs(vars(self))
    return copy

  #TODO:
  # def __eq__(self, other) -> bool:

  def __repr__(self) -> str:
    class_name = type(self).__name__
    kwarg_strs = []
    if self.value is not None:
      kwarg_strs.append(f'value={self.value!r}')
    for attr, default in self.ATTR_DEFAULTS.items():
      value = getattr(self, attr)
      if value != default:
        kwarg_strs.append(f'{attr}={value!r}')
    for attr, metadata in Style.METADATA.items():
      value = getattr(self, attr)
      if value != metadata['default']:
        kwarg_strs.append(f'{attr}={value!r}')
    kwarg_str = ', '.join(kwarg_strs)
    return f'{class_name}({kwarg_str})'

  def __str__(self) -> str:
    if self.value is None:
      return ''
    else:
      return str(self.value)

  def to_html(self) -> str:
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
    style_str = str(self.style)
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


class Style:

  METADATA: Dict[str,Dict[str,Any]] = {
    'align':  {'default':'left', 'type':str, 'css':'text-align'},
    'font':   {'default':None, 'type':str, 'css':'font-family'},
    'size':   {'default':None, 'type':str, 'css':'font-size'},
    'bold':   {'default':None, 'type':bool},
    'borders':{'default':set(), 'type':set, 'raw_type':Union[str,Sequence[str],Set[str]]},
    'css':    {'default':{}, 'type':dict, 'raw_type':Union[str,Sequence[str],Mapping[str,Any]]},
  }

  def __init__(self, **kwargs: Mapping[str,Any]):
    super().__init__()
    for key, metadata in self.METADATA.items():
      if key in kwargs:
        setattr(self, key, kwargs[key])
        del kwargs[key]
      else:
        setattr(self, key, metadata['default'])
    invalid_attrs = [repr(key) for key in kwargs]
    if invalid_attrs:
      class_name = type(self).__name__
      raise AttributeError(f'Invalid attribute(s) for {class_name!r} object: '+', '.join(invalid_attrs))

  def __setattr__(self, attr: str, raw_value: Any):
    if attr not in self.METADATA:
      raise AttributeError(f'{type(self).__name__!r} object has no attribute {attr!r}.')
    if attr == 'css':
      value = Style.parse_css(raw_value)
    elif attr == 'borders':
      value = Style.parse_borders(raw_value)
    else:
      value = raw_value
    object.__setattr__(self, attr, value)

  def copy(self):
    return type(self)(**vars(self))

  @staticmethod
  def parse_borders(value: Union[str,Iterable,None]) -> Set[str]:
    borders = set()
    if isinstance(value, str):
      borders.add(value)
    elif isinstance(value, collections.abc.Iterable):
      # A `set` is an iterable too.
      borders = set(value)
    elif value is not None:
      raise ValueError(f"'borders' must be a `str` or sequence of `str`s. Saw: {value!r}")
    return borders

  @staticmethod
  def parse_css(value: Union[str,Mapping,Iterable,None]) -> Dict[str,Any]:
    css = {}
    if isinstance(value, str):
      for statement in value.split(';'):
        key, value = Style.parse_css_statement(statement)
        css[key] = value
    elif isinstance(value, collections.abc.Mapping):
      css = dict(value)
    elif isinstance(value, collections.abc.Iterable):
      for statement in value:
        key, value = Style.parse_css_statement(statement)
        css[key] = value
    elif value is not None:
      raise ValueError(f"'css' must be a `str`, sequence of `str`, or a mapping. Saw: {value!r}")
    return css

  @staticmethod
  def parse_css_statement(statement: str) -> Tuple[str,str]:
    try:
      key, value = statement.split(':')
    except ValueError as error:
      error.args = (f'Invalid CSS statement: {statement!r}',)
      raise error
    return key.strip(), value.strip()

  def __repr__(self) -> str:
    attr_strs = []
    for key, metadata in self.METADATA.items():
      value = getattr(self, key)
      if value != metadata['default']:
        attr_strs.append(f'{key}={value!r}')
    class_name = type(self).__name__
    return f'{class_name}({", ".join(attr_strs)})'

  def __str__(self) -> str:
    css = dict(self.css)
    for key, metadata in self.METADATA.items():
      if not hasattr(self, key) or key == 'css':
        continue
      value = getattr(self, key)
      if value is None:
        continue
      if 'css' in metadata:
        css_property = metadata['css']
        css[css_property] = value
      elif key == 'bold':
        if value is True:
          css['font-weight'] = 'bold'
        elif value is False:
          css['font-weight'] = 'normal'
      elif key == 'borders':
        for border in value:
          css[f'border-{border}'] = BORDER_STYLE
    if css:
      css_statements = [f'{key}: {value}' for key, value in css.items()]
      return 'style="{}"'.format('; '.join(css_statements))
    else:
      return ''

  def to_attr_str(self) -> str:
    style_str = str(self)
    if style_str:
      return ' '+style_str
    else:
      return ''


def rotate_table(old_rows):
  """Rotate a table 90° (rows become columns, columns become rows).
  Only works on tables where all cells' widths and heights are 1 and all rows are the same width."""
  new_rows = []
  width = len(old_rows[0])
  for col in range(width):
    new_row = []
    for old_row in old_rows:
      new_row.append(old_row[col])
    new_rows.append(new_row)
  return new_rows


def is_number(value: Any) -> bool:
  try:
    float(value)
  except (ValueError, TypeError):
    return False
  else:
    return True


def get_round_to(num, decimals):
    log = math.log10(num)
    if num < 1:
        return decimals - 1 - math.floor(log)
    else:
        return decimals


def partially_order(unordered, order):
  """Sort a list according to a given order.
  The given order doesn't have to be comprehensive. Any elements in the input list that aren't in
  the `order` list will be put at the end of the output list, in the same order as they appear in
  the input.
  NOTE: The elements must be hashable, and cannot appear repeatedly in the list. So this is ideal
  for sorting identifiers or dictionary keys."""
  ordered = []
  ordered_set = set()
  input_set = set(unordered)
  for element in order:
    if element in input_set:
      ordered.append(element)
      ordered_set.add(element)
  for element in unordered:
    if element not in ordered_set:
      ordered.append(element)
  return ordered


import argparse
import pathlib
import sys
import tempfile

DESCRIPTION = """Create formatted tables from text input."""

def make_argparser():
  parser = argparse.ArgumentParser(add_help=False, description=DESCRIPTION)
  options = parser.add_argument_group('Options')
  options.add_argument('-H', '--header', dest='headers', action='store_const', const=1, default=0,
    help='The first input row is a header.')
  options.add_argument('--headers', type=int,
    help='How many header rows there are in the input.')
  options.add_argument('-t', '--tabs', dest='delim', action='store_const', const='\t')
  options.add_argument('-s', '--table-style', dest='table_styles', action='append',
    help='Add this CSS property:value pair to the <table> style attribute. The string will be '
      'added verbatim to the list of CSS rules. Give multiple times to add multiple rules.')
  options.add_argument('-a', '--accumulate',
    help='Store input between invocations for later output (with --dump). Give a unique id to tell '
      'it which ongoing input to add this to.')
  options.add_argument('-d', '--dump',
    help='Output formatted table from input stored with --accumulate. Give the id of the '
      'accumulated input you want to print. Note: This will delete the accumulated input, so it '
      "can't be used more than once.")
  options.add_argument('-h', '--help', action='help',
    help='Print this argument help text and exit.')
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

  if args.dump:
    temp_dir = get_temp_dir()
    acc_path = temp_dir/f'acc.{args.dump}.txt'
    input_stream = acc_path.open()
  else:
    input_stream = sys.stdin

  if args.accumulate:
    if args.dump:
      fail('Cannot give both --accumulate and --dump.')
    temp_dir = get_temp_dir()
    acc_path = temp_dir/f'acc.{args.accumulate}.txt'
    with acc_path.open('a') as acc_file:
      for line in input_stream:
        acc_file.write(line)
    return

  header = []
  body = []
  for row_num, fields in enumerate(parse_input(input_stream, delim=args.delim), 1):
    cell_dicts = [{'value':value} for value in fields]
    if row_num <= args.headers:
      header.append(cell_dicts)
    else:
      body.append(cell_dicts)

  table = Table(body, header=header)
  table.css = args.table_styles

  print(table.to_html())

  if args.dump:
    input_stream.close()
    acc_path.unlink()


def parse_input(stream, delim=None):
  for line in stream:
    yield line.rstrip('\r\n').split(sep=delim)


def get_temp_dir():
  with tempfile.NamedTemporaryFile() as temp_file:
    temp_root = pathlib.Path(temp_file.name).parent
  temp_dir = temp_root/'html-table-acc'
  i = 1
  while not is_temp_dir_availabile(temp_dir):
    i += 1
    temp_dir = temp_root/f'html-table-acc{i}'
    if i >= 1000:
      fail(f'Could not find available temporary directory (like {temp_dir})')
  temp_dir.mkdir(mode=0o700, exist_ok=True)
  return temp_dir


def is_temp_dir_availabile(temp_dir):
  """Does it look like the directory is already in use by a different program?"""
  if not temp_dir.exists():
    return True
  if not temp_dir.is_dir():
    return False
  for child_path in temp_dir.iterdir():
    if not (child_path.name.startswith('acc.') and child_path.name.endswith('.txt')):
      return False
  return True


def fail(message):
  logging.critical(f'Error: {message}')
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception(message)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass