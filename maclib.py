"""Operations on MAC addresses."""
import uuid
import random
import numbers


def get_mac():
  """Get your own device's MAC address using uuid.getnode().
  Returns a Mac object, or None on failure."""
  #TODO: uuid.getnode() arbitrarily chooses a MAC when the device has more than one. May have to use
  #      another method to make sure it's the MAC of the NIC in use. Probably have to create a
  #      dummy socket using a public IP.
  # uuid.getnode() returns the MAC as an integer.
  uuid_mac = Mac(uuid.getnode())
  # On failure, uuid.getnode() returns a random MAC, with the eight bit set:
  # https://docs.python.org/2/library/uuid.html#uuid.getnode
  # Check the eight bit to determine whether it failed.
  if uuid_mac.byte_ints[0] & 0b00000001:
    return None
  else:
    return uuid_mac


def get_random_mac():
  """Generate a valid, random MAC address."""
  # In the first byte, the two least-significant bits must be 10:
  # The 1 means it's a local MAC address (not globally assigned and unique).
  # The 0 means it's not a broadcast address.
  # https://superuser.com/questions/725467/set-mac-address-fails-rtnetlink-answers-cannot-assign-requested-address/725472#725472
  # 0-63 * 4 gives a number with 00 as the last binary digits.
  number = random.randint(0, 63) * 4
  # Add the following 5 bytes.
  for i in range(5):
    number *= random.randint(0, 255)
  return Mac(number)


def eui64_to_mac(eui64):
  """Convert an EUI-64 to a MAC address by removing the middle two bytes."""
  _bytes = eui64.split(':')
  return Mac(_bytes[:3] + _bytes[5:])


# Subclass tuple to make Mac immutable.
class Mac(tuple):
  """An object representing a MAC address.
  Initialize with one argument: a MAC address in one of 4 representations:
    1. a string of the colon-delimited hexadecimal bytes
    2. an iterable of the bytes as hex strings
    3. an iterable of the bytes as integers
    4. a single integer representing the 48-bit value of the address
  When a representation is requested that wasn't given initially, it is computed and cached.
  Mac objects are immutable."""

  # Need to override tuple's __new__().
  def __new__(cls, mac):
    return tuple.__new__(cls, ())

  def __init__(self, mac):
    self._string = None
    self._number = None
    self._bytes = None
    self._byte_ints = None
    if isinstance(mac, basestring):
      assert len(mac) == 17, 'Mac string must be 17 characters (6 colon-delimited hex bytes).'
      self._string = mac
    elif isinstance(mac, numbers.Integral):
      self._number = mac
    else:
      try:
        _bytes = tuple(mac)
      except TypeError:
        raise AssertionError('Mac object must be initialized with a string, integer, or iterable.')
      assert len(_bytes) == 6, 'Mac must consist of 6 bytes.'
      if isinstance(_bytes[0], basestring):
        self._bytes = _bytes
      elif isinstance(_bytes[0], numbers.Number):
        self._byte_ints = _bytes
      else:
        raise AssertionError('Mac bytes must be numbers or strings.')

  @property
  def string(self):
    """A string representing the MAC address as the standard colon-delimited hex bytes.
    If it doesn't exist, derive it from the bytes."""
    if self._string is None:
      self._string = ':'.join(self.bytes)
    return self._string

  @property
  def number(self):
    """An int representing the MAC address value as a number.
    If it doesn't exist, derive it from the bytes."""
    if self._number is None:
      hexadecimal = ''.join(self.bytes)
      self._number = int(hexadecimal, 16)
    return self._number

  @property
  def byte_ints(self):
    """A tuple representing the MAC address as a series of bytes (ints).
    If it doesn't exist, derive it from the bytes."""
    if self._byte_ints is None:
      self._byte_ints = tuple(int(o, 16) for o in self.bytes)
    return self._byte_ints

  @property
  def bytes(self):
    """An tuple representing the MAC address as a series of hex bytes (strings).
    If it doesn't exist, try deriving it from one of the other representations."""
    if self._bytes is None:
      if self._string is not None:
        self._bytes = tuple(self._string.split(':'))
      elif self._byte_ints is not None:
        self._bytes = tuple('{:02x}'.format(o) for o in self._byte_ints)
      elif self._number is not None:
        hexadecimal = '{:012x}'.format(self._number)
        self._bytes = tuple(hexadecimal[i:i+2] for i in range(0, 12, 2))
      else:
        raise AssertionError('Mac object is uninitialized.')
    return self._bytes

  def __str__(self):
    return self.string

  def __repr__(self):
    return "{}.{}('{}')".format(type(self).__module__, type(self).__name__, self.string)

  def __eq__(self, mac2):
    return self.string.upper() == mac2.string.upper()

  def __ne__(self, mac2):
    return self.string.upper() != mac2.string.upper()

  def to_eui64(self, is_mac48=False):
    """Convert the MAC address to an EUI-64 address.
    This expands the address to 64 bits by adding 'ff:fe' as the middle two bytes, by default.
    This is the procedure when the MAC address is considered an EUI-48 (as is done when creating an
    IPv6 address from a MAC address). If the MAC address should be considered a MAC-48 instead, so
    that 'ff:ff' is used as the middle bytes, set 'is_mac48' to True.
    N.B.: This is part 1 of how IPv6 generates addresses from MAC addresses. The second part is
    flipping the locally administered bit."""
    if is_mac48:
      middle = 'ff:ff'
    else:
      middle = 'ff:fe'
    return self.bytes[:3] + middle + self.bytes[3:]

  def is_broadcast(self):
    """Check whether the MAC address is the broadcast FF:FF:FF:FF:FF:FF address."""
    return self.string.upper() == 'FF:FF:FF:FF:FF:FF'

  def is_local(self):
    """Check whether the "locally administered" bit in a MAC address is set to 1."""
    return bool(self.byte_ints[0] & 0b00000010)

  def is_global(self):
    """Check whether the "locally administered" bit in a MAC address is set to 0.
    This means that the MAC address should be "globally unique"."""
    return not bool(self.byte_ints[0] & 0b00000010)

  def is_multicast(self):
    """Check whether the "multicast" bit in a MAC address is set to 1."""
    return bool(self.byte_ints[0] & 0b00000001)

  def is_unicast(self):
    """Check whether the "multicast" bit in a MAC address is set to 0.
    This means the MAC address is unicast."""
    return not bool(self.byte_ints[0] & 0b00000001)

  def is_normal(self):
    """Check whether the MAC address is the common type used by networking hardware.
    Returns false if it's a locally administered, multicast, or broadcast address."""
    # Is broadcast address?
    if self.is_broadcast():
      return False
    # Is locally administered bit set?
    if self.is_local():
      return False
    # Is multicast bit set?
    if self.is_multicast():
      return False
    return True

  def to_local(self):
    """Set the "locally administered" bit to 1 and return the result."""
    byte_ints = list(self.byte_ints)
    # OR the first byte with 00000010.
    byte_ints[0] = byte_ints[0] | 0b00000010
    return Mac(byte_ints)

  def to_global(self):
    """Set the "locally administered" bit to 0 and return the result."""
    byte_ints = list(self.byte_ints)
    # AND the first byte with 11111101.
    byte_ints[0] = byte_ints[0] & 0b11111101
    return Mac(byte_ints)

  def to_multicast(self):
    """Set the "multicast" bit to 1 and return the result."""
    byte_ints = list(self.byte_ints)
    # OR the first byte with 00000001.
    byte_ints[0] = byte_ints[0] | 0b00000001
    return Mac(byte_ints)

  def to_unicast(self):
    """Set the "multicast" bit to 0 and return the result."""
    byte_ints = list(self.byte_ints)
    # AND the first byte with 11111110.
    byte_ints[0] = byte_ints[0] & 0b11111110
    return Mac(byte_ints)
