"""Operations on MAC addresses."""
import uuid
import random


def get_mac():
  """Get your own device's MAC address using uuid.getnode().
  Returns the MAC formatted in standard hex with colons."""
  # uuid.getnode() returns the MAC as an integer.
  mac_hex = hex(uuid.getnode())
  # [2:] removes leading '0x'.
  mac_hex = mac_hex[2:]
  # Fill in leading 0's, if needed.
  mac_hex = ('0' * (13 - len(mac_hex))) + mac_hex
  # Remove trailing 'L'.
  mac_hex = mac_hex[:12]
  # Build mac from characters in mac_hex, inserting colons.
  mac = ''
  for (i, char) in enumerate(mac_hex):
    if i > 1 and i % 2 == 0:
      mac += ':'
    mac += char
  return mac


def get_random_mac():
  """Generate a valid, random MAC address."""
  # In the first byte, the two least-significant bits must be 10:
  # The 1 means it's a local MAC address (not globally assigned and unique).
  # The 0 means it's not a broadcast address.
  # https://superuser.com/questions/725467/set-mac-address-fails-rtnetlink-answers-cannot-assign-requested-address/725472#725472
  octet1_int = random.randint(0, 63)*4
  octets = ['{:02x}'.format(octet1_int)]
  for i in range(5):
    octet_int = random.randint(0, 255)
    octets.append('{:02x}'.format(octet_int))
  return ':'.join(octets)


def local_to_global_mac(mac_input):
  """Alter a MAC address by setting its "locally administered" bit to 0.
  If there are alphabetic characters in the MAC, the output will match their case."""
  octets = mac_input.split(':')
  octet1_int_input = int(octets[0], 16)
  # Check if the second bit is 1.
  if octet1_int_input & 2:
    # If so, flip it with an XOR.
    octet1_int_global = octet1_int_input ^ 2
  else:
    # Otherwise, it's a global MAC already. Return unchanged.
    return mac_input
  octet1_global = '{:02x}'.format(octet1_int_global)
  octets[0] = octet1_global
  mac_global = ':'.join(octets)
  # Follow capitalization of the input.
  for alpha in ('A', 'B', 'C', 'D', 'E', 'F'):
    if alpha in mac_input:
      return mac_global.upper()
  return mac_global


def is_mac_normal(mac):
  """Check whether the MAC address is the common type used by networking hardware.
  Returns false if it's a locally administered, multicast, or broadcast address."""
  # Is broadcast address?
  if is_mac_broadcast(mac):
    return False
  octets = mac.split(':')
  octet1_int = int(octets[0], 16)
  # Is multicast bit set?
  if octet1_int & 1:
    return False
  # Is locally administered bit set?
  if octet1_int & 2:
    return False
  return True

def is_mac_broadcast(mac):
  """Check whether the MAC address is the broadcast FF:FF:FF:FF:FF:FF address."""
  return mac.upper() == 'FF:FF:FF:FF:FF:FF'

def is_mac_local(mac):
  """Check whether the "locally administered" bit in a MAC address is set to 1."""
  return _test_mac_bit(mac, 2)

def is_mac_global(mac):
  """Check whether the "locally administered" bit in a MAC address is set to 0.
  This means that the MAC address should be "globally unique"."""
  return not _test_mac_bit(mac, 2)

def is_mac_multicast(mac):
  """Check whether the "multicast" bit in a MAC address is set to 1."""
  return _test_mac_bit(mac, 1)

def is_mac_unicast(mac):
  """Check whether the "multicast" bit in a MAC address is set to 0.
  This means the MAC address is unicast."""
  return not _test_mac_bit(mac, 1)

def _test_mac_bit(mac, bit):
  octets = mac.split(':')
  octet1_int = int(octets[0], 16)
  return bool(octet1_int & bit)
