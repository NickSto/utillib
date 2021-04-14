"""Easy helpers for constructing HTML in Jupyter Notebooks."""
import logging


class Node:
  def equal_attrs(self, other):
    if type(self) != type(other):
      return False
    return True


class TextNode(Node):
  def __init__(self, content=''):
    self.content = content
  @property
  def textContent(self):
    return self.content
  def __str__(self):
    return self.content
  def __repr__(self):
    class_name = type(self).__name__
    if self.content:
      return f'{class_name}({self.content!r})'
    else:
      return f'{class_name}()'


class Elem(Node):
  def __init__(self, name, childNodes=[], style={}, id_=None, class_=None, text=None, **attrs):
    self.name = name
    self._attr_names = ['id', 'class_', 'style']
    self.style = style
    self.childNodes = childNodes
    self.id = id_
    self.classList = ClassList()
    if class_:
      self.class_ = class_
    for attr, value in attrs.items():
      setattr(self, attr, value)
    if text is not None:
      self.childNodes.append(TextNode(text))
  def __setattr__(self, name, value):
    if not name.startswith('_') and name not in ('name', 'childNodes', 'className', 'classList'):
      if name not in self._attr_names:
        self._attr_names.append(name)
    object.__setattr__(self, name, value)
  @property
  def attrs(self):
    return ReadOnlyDict({name:getattr(self,name) for name in self._attr_names})
  @property
  def class_(self):
    return str(self.classList)
  @class_.setter
  def class_(self, value):
    self.classList = ClassList(value)
  @property
  def className(self):
    return self.class_
  @className.setter
  def className(self, value):
    self.class_ = value
  @property
  def childNodes(self):
    return self._childNodes
  @childNodes.setter
  def childNodes(self, value):
    childNodes = []
    for child in value:
      if not isinstance(child, Node):
        raise TypeError(f'Child {child!r} is not a Node.')
      childNodes.append(child)
    self._childNodes = childNodes
  @property
  def children(self):
    return [child for child in self.childNodes if isinstance(child, Elem)]
  @property
  def style_str(self):
    style_strs = []
    for prop, value in self.style.items():
      style_strs.append(f'{prop}: {value}')
    return '; '.join(style_strs)
  @property
  def textContent(self):
    contents = []
    for child in self.childNodes:
      if isinstance(child, TextNode):
        contents.append(child.content)
    return ''.join(contents)
  def equal_attrs(self, other):
    """Are the two elements equal if the childNodes are ignored?"""
    if not super().equal_attrs(other):
      return False
    if self.name != other.name:
      return False
    if self.attrs != other.attrs:
      return False
    return True
  def _format_kwargs(self, dest):
    kwarg_strs = {}
    if self.id:
      if dest == 'repr':
        key = 'id_'
      elif dest == 'html':
        key = 'id'
      kwarg_strs[key] = self.id
    if self.class_:
      if dest == 'repr':
        key = 'class_'
      elif dest == 'html':
        key = 'class'
      kwarg_strs[key] = self.class_
    for name in self._attr_names:
      if name in ('id', 'class_', 'style', 'classList'):
        continue
      kwarg_strs[name] = getattr(self, name)
    if self.style:
      if dest == 'repr':
        style_str = self.style
      elif dest == 'html':
        style_str = self.style_str
      kwarg_strs['style'] = style_str
    return kwarg_strs
  def __repr__(self):
    class_name = type(self).__name__
    kwarg_strs = self._format_kwargs('repr')
    arg_strs = [repr(self.name)]
    arg_strs += [f'{key}={value!r}' for key, value in kwarg_strs.items()]
    if self.childNodes:
      child_strs = [repr(child) for child in self.childNodes]
      arg_strs.append(f'childNodes=[{", ".join(child_strs)}]')
    return f'{class_name}({", ".join(arg_strs)})'
  def __str__(self):
    kwarg_strs = self._format_kwargs('html')
    attr_strs = [f'{key}="{value}"' for key, value in kwarg_strs.items()]
    if attr_strs:
      attr_str = ' '+' '.join(attr_strs)
    else:
      attr_str = ''
    child_strs = [str(child) for child in self.childNodes]
    child_str = ''.join(child_strs)
    #TODO: Self-closing tags or ones with no end tag like <img>
    return f'<{self.name}{attr_str}>{child_str}</{self.name}>'


class ClassList(list):
  def __init__(self, *classes):
    for class_ in classes:
      if class_ not in self:
        self.append(class_)
  def add(self, value):
    if value not in self:
      self.append(value)
  def remove(self, value):
    if value in self:
      list.remove(self, value)
  def __str__(self):
    return ' '.join(self)


class ReadOnlyDict:
  def __init__(self, rw_dict):
    self._dict = {}
    for key, value in rw_dict.items():
      self._dict[key] = value
  def keys(self):
    return self._dict.keys()
  def values(self):
    return self._dict.values()
  def items(self):
    return self._dict.items()
  def __eq__(self, other):
    return self._dict == other._dict
  def __repr__(self):
    return repr(self._dict)


class Style(dict):
  def __init__(self, selector=None, selectors=None, styles={}, **kwargs):
    if selectors is not None:
      self.selectors = list(selectors)
    elif selector is not None:
      self.selectors = [selector]
    for prop, value in kwargs.items():
      self[prop] = value
    for prop. value in styles.items():
      self[prop] = value
  @property
  def selector(self):
    return self.selectors[0]
  @selector.setter
  def selector(self, value):
    self.selectors = [value]
  def scope(self, scope):
    new_selectors = []
    for selector in self.selectors:
      if selector.split()[0] == scope:
        logging.warning(f'Selector {selector!r} already begins with scope {scope!r}')
        new_selector = selector
      else:
        new_selector = scope+' '+selector
      new_selectors.append(new_selector)
    self.selectors = new_selectors
  def __repr__(self):
    class_name = type(self).__name__
    arg_strs = []
    if len(self.selectors) == 1:
      arg_strs.append(repr(self.selectors[0]))
    elif len(self.selectors) > 1:
      arg_strs.append(f'selectors={self.selectors!r}')
    if len(self) > 0:
      styles_str = dict.__repr__(self)
      arg_strs.append(f'styles={styles_str}')
    return f'{class_name}({", ".join(arg_strs)})'
  def __str__(self):
    selectors_str = ', '.join(self.selectors)
    prop_lines = [f'  {prop}: {value};' for prop, value in self.items()]
    return selectors_str+' {\n'+'\n'.join(prop_lines)+'\n}'


class StyleSheet(Elem, list):
  def __init__(self, *styles):
    self._initialized = False
    super().__init__('style')
    for style in styles:
      self.append(style)
    self._initialized = True
  def scope(self, scope):
    for style in self:
      style.scope(scope)
  @property
  def childNodes(self):
    contents = [str(style) for style in self]
    return [TextNode('\n'+'\n'.join(contents)+'\n')]
  @childNodes.setter
  def childNodes(self, value):
    if self._initialized:
      raise AttributeError(f"Can't set attribute childNodes.")
  def __repr__(self):
    class_name = type(self).__name__
    style_strs = [repr(style) for style in self]
    return f'{class_name}({", ".join(style_strs)})'


def compress_elems(elems):
  """Join together neighboring elements whose tags and attributes are the same.
  This is useful when you have runs of the same tag repeated which could be combined into a single
  element. For example:
    `<span>G</span><span>A</span><span>T</span><span class="star">T</span><span>A</span>`
  This would be compressed into an equivalent, but more efficient:
    `<span>GAT</span><span class="star">T</span><span>A</span>`
  Input and output are a `list` of `Node`s.
  CAUTION: This alters the input `Node`s."""
  new_elems = []
  last_elem = None
  for elem in elems:
    if elem.equal_attrs(last_elem):
      if isinstance(elem, TextNode):
        last_elem.content += elem.content
      elif isinstance(elem, Elem):
        last_elem.childNodes = compress_elems(last_elem.childNodes+elem.childNodes)
    else:
      new_elems.append(elem)
      last_elem = elem
  return new_elems
