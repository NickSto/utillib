#!/usr/bin/env python3
import argparse
import datetime
import sys
import xml.etree.ElementTree


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


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
