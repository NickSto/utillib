#!/usr/bin/env python3
from __future__ import print_function
import argparse
import base64
import binascii
import getpass
import logging
import sys
import cryptography.fernet
import cryptography.hazmat.backends
import cryptography.hazmat.primitives
import cryptography.hazmat.primitives.kdf.pbkdf2
assert sys.version_info.major >= 3, 'Python 3 required'

ENCODING = 'utf8'
DEFAULT_SALT = 'YMvE0GRTrO9_Ix5RAdhqZwAKyk-zYs37O1NDI93kXfI='
DEFAULT_ITERATIONS = 100000
DESCRIPTION = """Encrypt or decrypt data."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('command', choices=('encrypt', 'decrypt', 'key'),
    help='Which operation to perform. "key" will generate and print a valid key (or, if you '
         'give a --password, it will derive a key from it).')
  parser.add_argument('file', nargs='?',
    help='The file to encrypt or decrypt. "-" for stdin.')
  parser.add_argument('-k', '--key')
  parser.add_argument('-p', '--password')
  parser.add_argument('-t', '--text', action='store_true',
    help='Use a base64 encoding for the ciphertext.')
  parser.add_argument('-s', '--salt', default=DEFAULT_SALT,
    help='Give a different salt than the default for deriving the key from the password. Note that '
         'the default salt is hardcoded directly into this script and isn\'t a secret.')
  parser.add_argument('-i', '--iterations', type=int, default=DEFAULT_ITERATIONS,
    help='Number of pbkdf2 iterations for deriving the key from the password. Default: %(default)s')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  volume = parser.add_mutually_exclusive_group()
  volume.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
    default=logging.WARNING)
  volume.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
  volume.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  if args.command == 'key':
    if args.password:
      key = derive_key(args.password, args.salt, args.iterations)
    else:
      key = generate_key()
    print(key)
    return

  # Get the key.
  key = args.key
  password = args.password
  if not args.key and not args.password:
    password = getpass.getpass(prompt='Password: ')
  if password:
    key = derive_key(password, args.salt, args.iterations)

  # Check that the key is valid.
  try:
    cryptography.fernet.Fernet(key)
  except (binascii.Error, ValueError):
    # Maybe the user typed the key in the "Password" prompt?
    if password:
      try:
        cryptography.fernet.Fernet(password)
        key = password
      except (binascii.Error, ValueError):
        fail('Error: Invalid key.')
    else:
      fail('Error: Invalid key.')

  if args.command == 'encrypt':
    if args.file is None:
      fail('Error: Must provide a file to encrypt or "-" to read from stdin.')
    elif args.file == '-':
      plaintext = sys.stdin.read()
    else:
      with open(args.file) as infile:
        plaintext = infile.read()
    cipherthing = encrypt(plaintext, key, text=args.text)
    if args.text:
      print(cipherthing)
    else:
      sys.stdout.buffer.write(cipherthing)
  elif args.command == 'decrypt':
    if args.file is None:
      fail('Error: Must provide a file to dencrypt or "-" to read from stdin.')
    elif args.file == '-':
      infile = sys.stdin
    elif args.text:
      with open(args.file) as infile:
        cipherthing = infile.read()
    else:
      with open(args.file, 'rb') as infile:
        cipherthing = infile.read()
    plaintext = decrypt(cipherthing, key, text=args.text)
    print(plaintext, end='')


def generate_key():
  """Generate a random key.
  Returns it as a str."""
  key = cryptography.fernet.Fernet.generate_key()
  return str(key, ENCODING)


def derive_key(password, salt=DEFAULT_SALT, iterations=DEFAULT_ITERATIONS):
  """Derive a key from a password using pbkdf2.
  Give the password and salt as strings.
  Uses SHA-256 as the hash function.
  Returns the key as a base64-encoded str."""
  kdf = cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC(
    algorithm=cryptography.hazmat.primitives.hashes.SHA256(),
    length=32,
    salt=bytes(salt, ENCODING),
    iterations=iterations,
    backend=cryptography.hazmat.backends.default_backend()
  )
  key_bytes = kdf.derive(bytes(password, ENCODING))
  return base64.urlsafe_b64encode(key_bytes)


def encrypt(plaintext, key, text=False):
  """Encrypt a string with the given key.
  The key must be a base64 token of the type returned by generate_key() or derive_key().
  Returns the ciphertext as a bytes object.
  Raises a binascii.Error or ValueError on failure."""
  encryptor = cryptography.fernet.Fernet(key)
  plainbytes = bytes(plaintext, ENCODING)
  cipherbytes = encryptor.encrypt(plainbytes)
  if text:
    ciphertext = str(cipherbytes, ENCODING)
    return ciphertext
  else:
    return base64.urlsafe_b64decode(cipherbytes)


def decrypt(cipherthing, key, text=False):
  """Decrypt a ciphertext with the given key.
  The ciphertext must be a bytes object (like encrypt() returns).
  The key must be a base64 token of the type returned by generate_key() or derive_key().
  Returns the plaintext as a str.
  Raises a binascii.Error or ValueError on failure."""
  encryptor = cryptography.fernet.Fernet(key)
  if text:
    cipherbytes = bytes(cipherthing, ENCODING)
  else:
    cipherbytes = base64.urlsafe_b64encode(cipherthing)
  try:
    plainbytes = encryptor.decrypt(cipherbytes)
  except cryptography.fernet.InvalidToken:
    raise ValueError('Wrong key.')
  plaintext = str(plainbytes, ENCODING)
  return plaintext


def fail(message):
  logging.critical(message)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception('Unrecoverable error')


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
