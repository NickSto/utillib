import sys

class GeneratorList:
  """A class to allow using a generator like a (immutable) list.
  A.k.a. a lazily evaluated list."""
  def __init__(self, generator):
    self._generator = generator
    self._generator_done = False
    self._current_list = []
    self.type = type(self).__name__
  def __getattr__(self, name):
    if name in (
        'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'sort', 'reverse', '__setitem__',
        '__delitem__'
      ):
      raise RuntimeError(f'This {self.type} is not mutable.')
    else:
      raise AttributeError(f'{self.type} object has no attribute {name!r}')
  def __getitem__(self, index):
    """Get item at `index` or raise `IndexError` if `index` is out of bounds.
    `index` must be an integer. Slices are not currently supported.
    This is the heart of the GeneratorList. If the index is beyond the portion of the list that's
    been evaluated, the generator will be evaluated up to that point (or throw an IndexError if it
    ends before then). All items generated will be cached internally, so the generator is never
    reevaluated."""
    #TODO: Support slices.
    if isinstance(index, slice):
      raise NotImplementedError(f'Slices are not currently supported.')
    elif not isinstance(index, int):
      raise TypeError(f'Index must be an integer. Received {index!r} instead.')
    elif index < len(self._current_list):
      return self._current_list[index]
    elif self._generator_done:
      raise IndexError(
        f'Index {index} out of range for {self.type} of length {len(self._current_list)}'
      )
    else:
      for item in self._generator:
        self._current_list.append(item)
        if len(self._current_list) == index+1:
          return item
      self._generator_done = True
      raise IndexError(
        f'Index {index} out of range for {self.type} of length {len(self._current_list)}.'
      )
  def __len__(self):
    """Get the total length of the list. NOTE: This will cause the entire generator to be evaluated!"""
    for i, item in enumerate(self,1):
      pass
    return i
  def __contains__(self, query):
    """Check if the item `query` is contained in the list.
    The generator will be evaluated until the item is found, meaning the entire generator will be
    evaluated any time this returns False."""
    if query in self._current_list:
      return True
    elif self._generator_done:
      return False
    else:
      for value in self:
        if value == query:
          return True
      return False
  def __bool__(self):
    """Return True if there are any items in the list.
    This will evaluate the generator enough to get a single element at most."""
    if self._current_list:
      return True
    elif self._generator_done:
      return False
    else:
      try:
        self[0]
      except IndexError:
        return False
      else:
        return True
  def index(self, query, start=0, stop=sys.maxsize):
    for i, value in enumerate(self):
      if not start <= i < stop:
        continue
      if value == query:
        return i
    raise ValueError(f'{query!r} not found in this {self.type}')
  def count(self, query):
    return list(self).count(query)
  def copy(self):
    return list(self)
