#!/usr/bin/python3
import hashlib
import os
import pathlib
import sys
import zlib
from typing import Union

DEFAULT_CHUNK_SIZE = 1024**2


def main(argv):

  if len(argv) <= 2 or '-h' in argv[1][0:3]:
    script_name = os.path.basename(argv[0])
    print("""USAGE:
  $ """+script_name+""" hashtype filepath [chunksize]
Print the hash of a file. Only reads [chunksize] bytes into memory at a
time (default is """+str(DEFAULT_CHUNK_SIZE)+').')
    sys.exit(0)

  hashtype = argv[1]
  filename = argv[2]
  chunk_size = DEFAULT_CHUNK_SIZE
  if len(argv) >= 4:
    try:
      chunk_size = int(argv[3])
      print(f'Set chunk size to {chunk_size}')
    except ValueError:
      pass

  if hashtype == 'crc32' or hashtype == 'crc':
    print(crc32file(filename, chunk_size=chunk_size))
  else:
    print(hashfile(filename, hashtype, chunk_size=chunk_size))

  return 0


def crc32file(filename: Union[str, pathlib.Path], chunk_size: int=DEFAULT_CHUNK_SIZE) -> str:
  crc = crc32file_int(filename, chunk_size=chunk_size)
  if crc >= 0:
    return hex(crc)[2:]
  else:
    return '-'+hex(crc)[3:]


def crc32file_int(filename: Union[str, pathlib.Path], chunk_size: int=DEFAULT_CHUNK_SIZE) -> str:
  """Read a file and compute its CRC-32. Only reads chunk_size bytes into memory
  at a time."""
  crc = 0
  with open(filename, 'rb') as filehandle:
    chunk = filehandle.read(chunk_size)
    while chunk:
      crc = zlib.crc32(chunk, crc)
      if crc >= 0x80000000:  # 2**31
        # Correct for change made in 3.0:
        # Versions 2.6 to 2.7 returned a signed 32-bit integer.
        # Versions after 3.0 return an unsigned 32-bit integer.
        # https://stackoverflow.com/questions/30092226/how-to-calculate-crc32-with-python-to-match-online-results
        crc -= 0x100000000  # 2**32
      chunk = filehandle.read(chunk_size)
  return crc


def crc32str(data: str) -> str:
  crc = crc32data(data.encode('utf-8'))
  if crc >= 0:
    return hex(crc)[2:]
  else:
    return '-'+hex(crc)[3:]


def crc32data(data: bytes) -> int:
  return zlib.crc32(data)


def hashfile(
    filepath: Union[str, pathlib.Path], hash_name: str, chunk_size: int=DEFAULT_CHUNK_SIZE
  ) -> str:
  if hash_name not in hashlib.algorithms_available:
    raise ValueError(f'Hash algorithm {hash_name!r} not recognized.')
  hasher = hashlib.new(hash_name)
  digest = hashfile_with_hasher(filepath, hasher, chunk_size=chunk_size)
  return digest.hex()


def hashfile_with_hasher(
    filepath: Union[str, pathlib.Path], hasher: hashlib._hashlib.HASH,
    chunk_size: int=DEFAULT_CHUNK_SIZE
  ) -> bytes:
  with open(filepath, 'rb') as filehandle:
    chunk = filehandle.read(chunk_size)
    while chunk:
      hasher.update(chunk)
      chunk = filehandle.read(chunk_size)
  return hasher.digest()


def hashstr(data: str, hash_name: str) -> str:
  if hash_name not in hashlib.algorithms_available:
    raise ValueError(f'Hash algorithm {hash_name!r} not recognized.')
  hasher = hashlib.new(hash_name)
  digest = hashdata(data.encode('utf-8'), hasher)
  return digest.hex()


def hashdata(data: bytes, hasher: hashlib._hashlib.HASH) -> int:
  hasher.update(data)
  return hasher.digest()


if __name__ == "__main__":
  sys.exit(main(sys.argv))
