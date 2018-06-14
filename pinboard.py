#!/usr/bin/env python3
import argparse
import datetime
import http.client
import logging
import socket
import sys
import time
import urllib.parse
import xml.etree.ElementTree
try:
  import requests
  import requests.exceptions
  from bs4 import BeautifulSoup
except ImportError:
  requests = None
  BeautifulSoup = None

# API documentation: https://pinboard.in/api
# Get the auth token from https://pinboard.in/settings/password

MAX_RESPONSE = 16384 # bytes
API_DOMAIN = 'api.pinboard.in'
GET_API_PATH = '/v1/posts/get?auth_token={token}&url={url}'
ADD_API_PATH = '/v1/posts/add?auth_token={token}&url={url}&description={title}&tags={tags}&replace=no'


def quote(string):
  return urllib.parse.quote_plus(string)


class ApiInterface(object):

  def __init__(self, auth_token):
    self.auth_token = auth_token

  def is_url_bookmarked(self, url):
    """Check if a url is already bookmarked."""
    request_path = GET_API_PATH.format(token=self.auth_token, url=quote(url))
    response = make_request(API_DOMAIN, request_path)
    return check_response(response, 'get')

  def bookmark_url(self, url, title, tags=None):
    """Bookmark a url. Returns True on success, False otherwise."""
    if tags is None:
      tags_str = 'automated'
    else:
      tags_str = make_tags_str(tags)
    request_path = ADD_API_PATH.format(token=self.auth_token, url=quote(url), title=quote(title),
                                       tags=tags_str)
    logging.debug('https://'+API_DOMAIN+request_path)
    response = make_request(API_DOMAIN, request_path)
    return check_response(response, 'add')


def make_tags_str(tags):
  tags_strs = []
  for tag in tags:
    if ' ' in tag:
      raise ValueError('Tags cannot contain spaces. Failed on {!r}.'.format(tag))
    tags_strs.append(quote(str(tag)))
  return '+'.join(tags_strs)


def make_request(domain, path):
  try:
    conex = http.client.HTTPSConnection(domain)
    conex.request('GET', path)
  except (http.client.HTTPException, socket.gaierror):
    return None
  return conex.getresponse()


def check_response(response, request_type):
  if response is None:
    fail('Failure making HTTP request to Pinboard API.')
  elif response.status == 429:
    # API rate limit reached.
    fail('API rate limit reached (429 Too Many Requests).')
  elif response.status == 401:
    fail('Received 401 Forbidden. Are you using the right API token?')
  response_body = str(response.read(MAX_RESPONSE), 'utf8')
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
      fail('Error 1: Unrecognized response from API:\n{}'+response_body)
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
  subparsers = parser.add_subparsers(dest='command', help='Subcommands')
  read = subparsers.add_parser('read', help='Read a bookmarks export XML.')
  read.add_argument('bookmarks',
    help='The bookmarks file.')
  bookmark = subparsers.add_parser('bookmark', help='Save a url as a bookmark.')
  bookmark.add_argument('urls', nargs='?',
    help='Provide a literal url as the argument, or a file containing urls (one per line). '
         'If not given, this will read a list of urls from stdin.')
  bookmark.add_argument('-a', '--auth-token', required=True,
    help='Your Pinboard API authentication token. Available from '
         'https://pinboard.in/settings/password')
  bookmark.add_argument('-t', '--tags', default='automated',
    help='The tags to save the bookmark(s) with. Use a comma-delimited list. Default: "%(default)s"')
  bookmark.add_argument('-d', '--skip-dead-links', action='store_true',
    help="Don't bookmark urls which return an error HTTP status.")
  bookmark.add_argument('-A', '--user-agent',
    default='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0',
    help='User agent to give when making requests to the urls. Default: "%(default)s"')
  parser.add_argument('-p', '--pause', type=float, default=1,
    help='A time to wait in-between requests to the Pinboard API. The documentation recommends 3 '
         'seconds: https://pinboard.in/api Default: %(default)s')
  bookmark.add_argument('-n', '--simulate', action='store_true',
    help='Only simulate the process, printing the tabs which will be archived but without actually '
         'doing it.')
  parser.add_argument('-l', '--log', type=argparse.FileType('w'), default=sys.stderr,
    help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
  volume = parser.add_mutually_exclusive_group()
  volume.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL)
  volume.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO,
    default=logging.INFO)
  volume.add_argument('-D', '--debug', dest='volume', action='store_const', const=logging.DEBUG)
  return parser


def main(argv):

  parser = make_argparser()
  args = parser.parse_args(argv[1:])
  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  if args.command == 'read':
    read_archive(args.bookmarks)
  elif args.command == 'bookmark':
    if requests is None or BeautifulSoup is None:
      fail('Error: "requests" and "beautifulsoup4" modules are required for saving bookmarks.')
    urls = read_urls(args.urls)
    tags = args.tags.split(',')
    save_bookmarks(urls, args.auth_token, tags=tags, simulate=args.simulate, pause=args.pause,
                   skip_dead_links=args.skip_dead_links, user_agent=args.user_agent)


def read_archive(path):
  for post in parse_archive_file(path, 'xml'):
    print('{}: {}'.format(post.human_time(), post.url))
    if post.type == 'tweet':
      print(post.text)
    elif post.type == 'bookmark':
      print(post.title)
      if post.tags:
        print(', '.join(post.tags))


def save_bookmarks(urls, auth_token, tags=('automated',), simulate=False, skip_dead_links=False,
                   user_agent=None, pause=1):
  if user_agent is None:
    headers = {}
  else:
    headers = {'User-Agent': user_agent}
  skipped = 0
  existing = 0
  bookmarked = 0
  api = ApiInterface(auth_token)
  for url in urls:
    time.sleep(pause)
    if not simulate and api.is_url_bookmarked(url):
      logging.warning('Already bookmarked: {}'.format(url))
      existing += 1
    else:
      instance_headers = get_headers(headers, url)
      try:
        response = requests.get(url, timeout=6, headers=instance_headers)
      except requests.exceptions.RequestException:
        logging.error('Error making request to {}'.format(url))
        logging.error('  Could not determine a title. Skipping bookmark..')
        skipped += 1
        continue
      except AttributeError as error:
        # Catching exception due to bug https://github.com/requests/requests/issues/3807
        if error.args[0] == "'NoneType' object has no attribute 'readline'":
          logging.error('Error making request to {}'.format(url))
          logging.error("  The server sent a response requests couldn't handle. Skipping bookmark..")
          skipped += 1
          continue
        else:
          raise
      if skip_dead_links and response.status_code >= 400:
        logging.error('Error: Dead link (status {}): {}'.format(response.status_code, url))
        logging.error('  Skipping bookmark..')
        skipped += 1
        continue
      title = get_title(response.text)
      if title:
        logging.info('Found title {!r}'.format(title))
      else:
        logging.warning('No title found for {}'.format(url))
        title = url
      if simulate:
        logging.info('Bookmarking simulated only for '+url)
        bookmarked += 1
      else:
        time.sleep(pause)
        success = api.bookmark_url(url, title, tags=tags)
        if success:
          logging.info('Successfully bookmarked {}'.format(url))
          bookmarked += 1
  if simulate:
    adverb = 'Simulatedly'
  else:
    adverb = 'Successfully'
  logging.warning('{} {} bookmarked\n{} Already bookmarked\n{} Skipped due to errors.'
                  .format(bookmarked, adverb, existing, skipped))


def get_headers(default_headers, url):
  """Modify headers for specific sites.
  Youtube actually sends a more easily parsable response to robots than to browsers. So remove any
  user agent spoofing we might've enabled and allow requests to reveal itself."""
  headers = default_headers
  domain = urllib.parse.urlparse(url).netloc
  fields = domain.split('.')
  domain_ending = '.'.join(fields[len(fields)-2:])
  if domain_ending == 'youtu.be' or (len(fields) >= 2 and fields[len(fields)-2] == 'youtube'):
    headers = default_headers.copy()
    del headers['User-Agent']
  return headers


def get_title(html):
  if html is None:
    return None
  soup = BeautifulSoup(html, 'html.parser')
  if soup.title:
    return soup.title.text.strip()
  else:
    return None


def read_urls(urls):
  if not urls:
    return (line.rstrip('\r\n') for line in sys.stdin)
  elif urls.startswith('http://') or urls.startswith('https://'):
    return [urls]
  else:
    with open(urls) as urls_file:
      return (line.rstrip('\r\n') for line in urls_file)


def fail(message):
  logging.critical(message)
  if __name__ == '__main__':
    sys.exit(1)
  else:
    raise Exception(message)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
