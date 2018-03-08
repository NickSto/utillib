#!/usr/bin/env python3
import argparse
import datetime
import http.client
import logging
import sys
import urllib.parse
import xml.etree.ElementTree

MAX_RESPONSE = 16384 # bytes
API_DOMAIN = 'api.pinboard.in'
GET_API_PATH = '/v1/posts/get?auth_token={token}&url={url}'
ADD_API_PATH = '/v1/posts/add?auth_token={token}&url={url}&description={title}&tags=tab+automated&replace=no'


def quote(string):
  return urllib.parse.quote_plus(string)


def make_request(domain, path):
  conex = http.client.HTTPSConnection(domain)
  #TODO: Both of these steps can throw exceptions. Deal with them.
  conex.request('GET', path)
  return conex.getresponse()


def check_response(response, request_type):
  if response.status == 429:
    # API rate limit reached.
    fail('Error: API rate limit reached (429 Too Many Requests).')
  response_body = response.read(MAX_RESPONSE)
  if request_type == 'get':
    return parse_get_response(response_body)
  elif request_type == 'add':
    return parse_add_response(response_body)


def parse_get_response(response_body):
  """Return True if url is already bookmarked, False if not."""
  try:
    root = xml.etree.ElementTree.fromstring(response_body)
  except xml.etree.ElementTree.ParseError:
    fail('Error 1: Parsing error in response from API:\n'+response_body)
  if root.tag == 'posts':
    if len(root) == 0:
      return False
    elif len(root) == 1:
      return True
    else:
      fail('Error: Too many hits when checking if tab is already bookmarked: {} hits'
           .format(len(root)))
  elif root.tag == 'result':
    if root.attrib.get('code') == 'something went wrong':
      fail('Error: Request failed when checking if tab is already bookmarked.')
    elif root.attrib.get('code') == 'done':
      fail('Error: "done" returned instead of result when checking if tab is already bookmarked.')
    elif 'code' in root.attrib:
      fail('Error: Received message "{}" when checking if tab is already bookmarked.'
           .format(root.attrib['code']))
    else:
      fail('Error 1: Unrecognized response from API:\n'+response_body)
  else:
    fail('Error 2: Unrecognized response from API:\n'+response_body)


def parse_add_response(response_body):
  try:
    root = xml.etree.ElementTree.fromstring(response_body)
  except xml.etree.ElementTree.ParseError:
    fail('Error 2: Parsing error in response from API:\n'+response_body)
  if root.tag == 'result':
    try:
      result = root.attrib['code']
    except KeyError:
      fail('Error 3: Unrecognized response from API:\n'+response_body)
    if result == 'done':
      return True
    elif result == 'something went wrong':
      return False
    else:
      fail('Error: Received message "{}" when adding bookmark.'.format(result))
  else:
    fail('Error 4: Unrecognized response from API:\n'+response_body)


########## Export file parsing ##########


def parse_archive_file(archive_path, format, tz_offset=None):
  if format == 'xml':
    tree = xml.etree.ElementTree.parse(archive_path)
    return parse_bookmarks_xml(tree.getroot(), tz_offset=tz_offset)
  else:
    raise ValueError('Invalid format "{}"'.format(format))


def parse_archive_str(archive_str, format, tz_offset=None):
  if format == 'xml':
    root = xml.etree.ElementTree.fromstring(archive_str)
    return parse_bookmarks_xml(root, tz_offset=tz_offset)
  else:
    raise ValueError('Invalid format "{}"'.format(format))


def parse_bookmarks_xml(root, tz_offset=None):
  if tz_offset is None:
    delta = datetime.datetime.now() - datetime.datetime.utcnow()
    tz_offset = round(delta.total_seconds())
  assert root.tag == 'posts', root.tag
  for post_element in root:
    assert post_element.tag == 'post', post_element.tag
    if post_element.attrib.get('extended') and post_element.attrib.get('description') == 'Twitter':
      post = Tweet()
      post.text = post_element.attrib.get('extended')
    else:
      post = Bookmark()
      post.title = post_element.attrib.get('description')
      if 'tag' in post_element.attrib:
        post.tags = post_element.attrib['tag'].strip().split()
    post.url = post_element.attrib.get('href')
    if 'time' in post_element.attrib and tz_offset is not None:
      timestamp_str = post_element.attrib['time']
      # Note: The bookmark timestamps are in UTC.
      # tz_offset has to be the difference (in seconds) between this machine's timezone and UTC.
      dt = datetime.datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')
      post.timestamp = int(dt.timestamp()) + tz_offset
    yield post


class Post(object):
  def __init__(self, type, url=None, timestamp=None):
    self.type = type
    self.url = url
    self.timestamp = timestamp

  def human_time(self):
    if self.timestamp:
      dt = datetime.datetime.fromtimestamp(self.timestamp)
      return dt.strftime('%Y-%m-%d %H:%M:%S')


class Tweet(Post):
  def __init__(self, url=None, timestamp=None, text=None):
    super().__init__('tweet', url=url, timestamp=timestamp)
    self.text = text


class Bookmark(Post):
  def __init__(self, url=None, timestamp=None, title=None, tags=[]):
    super().__init__('bookmark', url=url, timestamp=timestamp)
    self.title = title
    self.tags = tags


def make_argparser():
  parser = argparse.ArgumentParser()
  parser.add_argument('bookmarks',
    help='')
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])

  for post in parse_archive_file(args.bookmarks, 'xml'):
    print('{}: {}'.format(post.human_time(), post.url))
    if post.type == 'tweet':
      print(post.text)
    elif post.type == 'bookmark':
      print(post.title)
      if post.tags:
        print(', '.join(post.tags))


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
