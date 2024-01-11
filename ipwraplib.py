#!/usr/bin/env python
"""These functions are some simple wrappers for unix commands that query info
from the OS like wifi SSIDs, MAC addresses, DNS queries, etc."""
from __future__ import print_function
import os
import re
import sys
import errno
import socket
import inspect
import argparse
import subprocess
import distutils.spawn


def get_wifi_info():
  """Find out what the wifi interface name, SSID and MAC address are.
  Returns those three values as strings, respectively. If you are not connected
  to wifi or if an error occurs, returns three None's.
  It currently does this by parsing the output from the 'iwconfig' command.
  It determines the data from the first section with fields for "SSID"
  (or "ESSID") and "Access Point" (case-insensitive)."""
  ssid = None
  mac = None
  interface = None
  iwconfig_cmd = 'iwconfig'
  # Check if iwconfig command is available. If not, fall back to the common absolute path
  # /sbin/iwconfig. If this doesn't exist, subprocess will return an OSError anyway.
  # Note: distutils.spawn.find_executable() fails with an exception if there is no $PATH defined.
  # So we'll check first for that scenario. (I've actually seen this, for instance in the
  # environment NetworkManager sets up for scripts in /etc/NetworkManager/dispatcher.d/.
  if 'PATH' not in os.environ or not distutils.spawn.find_executable(iwconfig_cmd):
    iwconfig_cmd = '/sbin/iwconfig'
  # Call iwconfig.
  devnull = open(os.devnull, 'w')
  try:
    output = subprocess.check_output([iwconfig_cmd], encoding='utf8', stderr=devnull)
  except (OSError, subprocess.CalledProcessError):
    return (None, None, None)
  finally:
    devnull.close()
  # Parse ssid and mac from output.
  for line in output.splitlines():
    match = re.search(r'^(\S+)\s+\S', line)
    if match:
      interface = match.group(1)
    if not mac:
      match = re.search(r'^.*access point: ([a-fA-F0-9:]+)\s*$', line, re.I)
      if match:
        mac = match.group(1)
    if not ssid:
      match = re.search(r'^.*SSID:"(.*)"\s*$', line)
      if match:
        ssid = match.group(1)
    if ssid is not None and mac is not None:
      break
  return (interface, ssid, mac)


def get_default_route(to='8.8.8.8'):
  """Determine the default networking interface in use at the moment by using the
  'ip route get' command.
  This asks what the route is to a specific, external ip (the "to" argument).
  By default, this is Google's 8.8.8.8. This differentiates between multiple
  default routes if there are any.
  Returns the name of the interface, and the IP of the default route. Or, on
  error, returns (None, None)."""
  ip = None
  interface = None
  ip_cmd = 'ip'
  # Check if 'ip' command is available. If not, fall back to common absolute path.
  if 'PATH' not in os.environ or not distutils.spawn.find_executable(ip_cmd):
    ip_cmd = '/sbin/ip'
  # Call 'ip route get [ip]'.
  devnull = open(os.devnull, 'w')
  try:
    output = subprocess.check_output([ip_cmd, 'route', 'get', to], stderr=devnull)
  except (OSError, subprocess.CalledProcessError):
    return (None, None)
  finally:
    devnull.close()
  # Parse output.
  for line in output.splitlines():
    fields = line.rstrip('\r\n').split()
    if len(fields) < 7:
      continue
    # Expect a line like:
    #   8.8.8.8 via 192.168.1.1 dev wlp58s0  src 192.168.1.106
    #   192.168.2.100 dev wlx74da388d8aeb  src 192.168.2.103
    #   192.168.1.1 dev wlp58s0  src 192.168.1.106
    if fields[1] == 'via' and fields[3] == 'dev' and fields[5] == 'src':
      ip = fields[6]
      interface = fields[4]
    elif fields[1] == 'dev' and fields[3] == 'src':
      ip = fields[4]
      interface = fields[2]
    if ip is not None and interface is not None:
      if re.search(r'^[0-9\.]{7,15}$', ip):
        break
      else:
        ip = None
        interface = None
  return (interface, ip)


def dig_ip(domain):
  """Use 'dig' command to get the first IP returned in a DNS query for 'domain'.
  On error, or no result, returns None."""
  ip = None
  dig_cmd = 'dig'
  if 'PATH' not in os.environ or not distutils.spawn.find_executable(dig_cmd):
    dig_cmd = '/usr/bin/dig'
  devnull = open(os.devnull, 'w')
  try:
    output = subprocess.check_output([dig_cmd, '+short', '+time=1', '+tries=2', domain],
                                     stderr=devnull)
  except (OSError, subprocess.CalledProcessError):
    return None
  finally:
    devnull.close()
  for line in output.splitlines():
    ip = line.strip()
    return ip
  return None


def dns_query(domain):
  """Use the socket module to do a DNS query.
  Returns None on failure instead of raising an exception (like socket.gaierror)."""
  #TODO: Looks like getaddrinfo() is the preferred way?
  try:
    return socket.gethostbyname(domain)
  except socket.error:
    return None


def get_arp_table(proc_path='/proc/net/arp'):
  """Get ARP table data from the /proc/net/arp pseudo-file.
  Returns a dict mapping IP addresses to ARP table entries. Each entry is a dict
  mapping field names to values. Fields: ip (str), hwtype (int), flags (int), mac
  (str), mask (str), interface (str)."""
  table = {}
  header = True
  with open(proc_path) as arp_table:
    for line in arp_table:
      # Skip the header.
      if header:
        header = False
        continue
      # Assume the file is whitespace-delimited.
      fields = line.rstrip('\r\n').split()
      try:
        ip, hwtype, flags, mac, mask, interface = fields
      except ValueError:
        continue
      try:
        mac = mac.upper()
        hwtype = int(hwtype, 16)
        flags = int(flags, 16)
      except ValueError:
        continue
      table[ip] = {'ip':ip, 'hwtype':hwtype, 'flags':flags, 'mac':mac, 'mask':mask,
                   'interface':interface}
  return table


def get_mac_from_ip(ip):
  """Look up the MAC address of an IP on the LAN, using the /proc/net/arp pseudo-file.
  Returns None if the IP isn't found."""
  arp_table = get_arp_table()
  if ip in arp_table:
    return arp_table[ip]['mac']
  else:
    return None


def get_ip_socket(to='8.8.8.8'):
  """Get this machine's local IP address by creating a dummy socket to an external ip."""
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.connect(('8.8.8.8', 53))
  ip = sock.getsockname()[0]
  sock.close()
  return ip


def mask_ip(ip, prefix_len=None):
  """Take an ip and prefix and return the actual ip range it represents.
  Provide an ip address as a string and a prefix length (the part after the slash) as an int, or
  an ip address/prefix length as a single string in CIDR notation:
    upper, lower = mask_ip('104.39.72.0', 22)
  or
    upper, lower = mask_ip('104.39.72.0/22')
  Returns the lower and upper bounds of the ip range as strings.
  """
  if prefix_len is None:
    ip, prefix_len_str = ip.split('/')
    prefix_len = int(prefix_len_str)
  ip_bin = ip_to_bin(ip)
  ip_int = int(ip_bin, 2)
  mask_bin = '1' * prefix_len + '0' * (32-prefix_len)
  mask_int = int(mask_bin, 2)
  lower_bound_int = ip_int & mask_int
  # Get the "opposite" of the mask (e.g. 11111000 -> 00000111, if IP addresses were 8 bits).
  subnet_int = 0b11111111111111111111111111111111 ^ mask_int
  upper_bound_int = lower_bound_int + subnet_int
  lower_bound_str = int_to_ip(lower_bound_int)
  upper_bound_str = int_to_ip(upper_bound_int)
  return lower_bound_str, upper_bound_str


def ip_to_bin(ip_str):
  bin_str = ''
  for byte_int_str in ip_str.split('.'):
    byte_int = int(byte_int_str)
    byte_bin_str = bin(byte_int)[2:]
    byte_bin_str = pad_binary(byte_bin_str, 8)
    bin_str += byte_bin_str
  return bin_str


def int_to_ip(ip_int):
  ip_bin = bin(ip_int)[2:]
  ip_bin = pad_binary(ip_bin, 32)
  return bin_to_ip(ip_bin)


def bin_to_ip(ip_bin):
  ip_byte_strs = []
  for i in range(0, 32, 8):
    byte_bin_str = ip_bin[i:i+8]
    byte_int = int(byte_bin_str, 2)
    byte_int_str = str(byte_int)
    ip_byte_strs.append(byte_int_str)
  return '.'.join(ip_byte_strs)


def pad_binary(bin_str, length):
  return '0' * (length-len(bin_str)) + bin_str


##### Run functions on the command line. #####


DESCRIPTION = """Run library functions directly. Use at your own risk. If the function returns None,
no output will be printed. If the function returns a list, each item will be printed on its own
line. Otherwise, the raw output will be stringified and printed."""

def main(argv):

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('function', nargs='?',
    help='The name of the function to run. Use -l to see all valid functions.')
  parser.add_argument('-l', '--list', action='store_true',
    help='Print the complete list of functions and exit.')
  parser.add_argument('-d', '--docstring', action='store_true',
    help='Print the docstring of the function instead of calling it.')
  parser.add_argument('arg', nargs='*',
    help='Any arguments required for the function.')
  args = parser.parse_args(argv[1:])

  if args.list:
    for (name, obj) in globals().items():
      if hasattr(obj, '__call__') and name != 'main':
        print(signature(obj))
    return 0

  if not args.function:
    parser.print_help()
    fail('\nError: Must provide a function.')

  if args.function == 'main':
    fail('"main"? Nice try.')

  globals_dict = globals()
  if args.function in globals_dict:
    obj = globals_dict[args.function]
    if hasattr(obj, '__call__'):
      if args.docstring:
        print('def '+signature(obj)+':')
        if obj.__doc__:
          print('  """'+obj.__doc__+'"""')
        return 0
      output = obj(*args.arg)
      if isinstance(output, list):
        for item in output:
          print(item)
      elif output is not None:
        print(output)
    else:
      fail('Error: "'+args.function+'" not a function.')
  else:
    fail('Error: function "'+args.function+'"" not recognized.')


def signature(func):
  """Take a function and return the call signature as a string, formatted just
  like the "def" line (minus the "def " before and ":" after)."""
  argspec = inspect.getargspec(func)
  allargs = argspec.args
  lallargs = len(allargs)
  defaults = argspec.defaults
  if defaults is None:
    lkwargs = 0
  else:
    lkwargs = len(defaults)
  lposargs = lallargs - lkwargs
  signature = func.__name__+'('
  for (i, arg) in enumerate(allargs):
    signature += arg
    if i >= lposargs:
      default = defaults[i - lposargs]
      if isinstance(default, str):
        signature += "='"+default+"'"
      else:
        signature += '='+str(default)
    if i + 1 < lallargs:
      signature += ', '
  if argspec.varargs:
    signature += ', *'+argspec.varargs
  if argspec.keywords:
    signature += ', **'+argspec.keywords
  signature += ')'
  return signature


def fail(message):
  sys.stderr.write(message+'\n')
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception('Unrecoverable error')


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except IOError as ioe:
    if ioe.errno != errno.EPIPE:
      raise
