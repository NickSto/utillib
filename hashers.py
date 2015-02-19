#!/usr/bin/python
import os
import sys
import zlib
import hashlib

DEFAULT_CHUNK_SIZE = 1024**2


def main(argv):

  if len(argv) <= 2 or '-h' in argv[1][0:3]:
    script_name = os.path.basename(argv[0])
    print """USAGE:
  $ """+script_name+""" hashtype filepath [chunksize]
Print the hash of a file. Only reads [chunksize] bytes into memory at a
time (default is """+str(DEFAULT_CHUNK_SIZE)+""").
Available hashes are "crc32", and "md5"."""
    sys.exit(0)

  hashtype = argv[1]
  filename = argv[2]
  chunk_size = DEFAULT_CHUNK_SIZE
  if len(argv) >= 3:
    try:
      chunk_size = int(argv[2])
    except ValueError:
      pass

  if hashtype == 'crc32' or hashtype == 'crc':
    print crc32(filename, chunk_size=chunk_size)
  elif hashtype == 'md5':
    print hashfile(filename, hashlib.md5(), chunk_size=chunk_size)
  else:
    raise Exception('Hash type "'+hashtype+'" not recognized.')

  return 0


def crc32(filename, chunk_size=DEFAULT_CHUNK_SIZE):
  """Read a file and compute its CRC-32. Only reads chunk_size bytes into memory
  at a time."""
  crc = 0
  with open(filename, 'r') as filehandle:
    chunk = filehandle.read(chunk_size)
    while chunk != "":
      crc = zlib.crc32(chunk, crc)
      chunk = filehandle.read(chunk_size)
  if crc >= 0:
    return hex(crc)[2:]
  else:
    return '-'+hex(crc)[3:]


def hashfile(filepath, hasher, chunk_size=DEFAULT_CHUNK_SIZE):
  with open(filepath) as filehandle:
    chunk = filehandle.read(chunk_size)
    while len(chunk) > 0:
      hasher.update(chunk)
      chunk = filehandle.read(chunk_size)
  return hasher.hexdigest()


if __name__ == "__main__":
  sys.exit(main(sys.argv))
