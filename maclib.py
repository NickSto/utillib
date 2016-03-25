"""Operations on MAC addresses."""
import uuid
import random


def get_mac():
  """Get your own device's MAC address using uuid.getnode().
  Returns the MAC formatted in standard hex with colons."""
  #TODO: On failure, getnode() returns a random MAC. Check the "eight bit" to see if it's that:
  #      https://docs.python.org/2/library/uuid.html#uuid.getnode
  #TODO: getnode() also arbitrarily chooses a MAC when the device has more than one. May have to use
  #      another method to make sure it's the MAC of the NIC in use. Probably have to just create a
  #      dummy socket using a public IP.
  # uuid.getnode() returns the MAC as an integer.
  mac_hex = '{:012x}'.format(uuid.getnode())
  # Build mac from characters in mac_hex, inserting colons.
  octets = (mac_hex[i:i+2] for i in range(0, 12, 2))
  return ':'.join(octets)


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


def mac48_to_eui64(mac48):
  octets = mac48.split(':')
  if mac48.isupper():
    middle = 'FF:FE'
  else:
    middle = 'ff:fe'
  return octets[:3] + middle + octets[3:]


def eui48_to_eui64(eui48):
  """This is part 1 of how IPv6 generates addresses from MAC addresses. The second part is flipping
  the locally administered bit."""
  octets = eui48.split(':')
  if eui48.isupper():
    middle = 'FF:FF'
  else:
    middle = 'ff:ff'
  return octets[:3] + middle + octets[3:]


def eui64_to_mac48(eui64):
  octets = eui64.split(':')
  return octets[:3] + octets[5:]


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
  if mac_input.islower():
    return mac_global.lower()
  elif mac_input.isupper():
    return mac_global.upper()
  else:
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
