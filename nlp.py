#!/usr/bin/env python3
import argparse
import logging
import string
import sys
assert sys.version_info.major >= 3, 'Python 3 required'

DESCRIPTION = """Library for natural language processing."""


def make_argparser():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument('command', choices=('substring', 'similarity'),
    help='')
  parser.add_argument('-1', '--str1')
  parser.add_argument('-2', '--str2')
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
  tone_down_logger()

  if args.command == 'substring':
    substring = get_longest_word_substring(args.str1, args.str2)
    print(' '.join(substring))
  elif args.command == 'similarity':
    similarity = get_word_similarity(args.str1, args.str2)
    print(similarity)


def get_word_uniqueness(string_list):
  total_count = 0
  word_counts = {}
  for s in string_list:
    for word in get_words(s):
      total_count += 1
      try:
        word_counts[word] += 1
      except KeyError:
        word_counts[word] = 1
  uniqueness = {}
  for word, count in word_counts.items():
    uniqueness[word] = total_count/count
  return uniqueness


def score_words(words, uniqueness, weight_length=False):
  score = 0
  for word in words:
    score += uniqueness.get(word, 0)
  if weight_length:
    weight = 1 + (len(words)-1)/7.5
    return score * weight
  else:
    return score


def get_word_similarity(str1, str2, uniqueness=None):
  """Score the similarity of two strings by how many words they have in common.
  The score is the number of words they share over the total number of unique words in both strings.
  """
  words1 = set(get_words(str1))
  words2 = set(get_words(str2))
  overlap = words1 & words2
  all_words = words1 | words2
  assert all_words, (str1, str2)
  if uniqueness is None:
    return len(overlap)/len(all_words)
  # Weight by uniqueness of each word.
  overlap_score = score_words(overlap, uniqueness)
  all_words_score = score_words(all_words, uniqueness)
  return overlap_score/all_words_score


def get_words(input_str):
  words = []
  for word in input_str.lower().split():
    clean_word = word.strip(string.punctuation)
    if clean_word:
      words.append(clean_word)
  return words


def get_longest_word_substring(str1, str2, uniqueness=None):
  str2_index = {}
  # Build index of str2.
  words2 = get_words(str2)
  for i, word in enumerate(words2):
    try:
      str2_index[word].append(i)
    except KeyError:
      str2_index[word] = [i]
  # Find longest substring. Each substring is a list of indices into words2.
  substrings = []
  longest_substring = []
  words1 = get_words(str1)
  for i, word in enumerate(words1):
    # print('Word {:2d}: {!r}'.format(i, word))
    # Find all instances of this word in str2.
    if word in str2_index:
      new_substrings = []
      for i in str2_index[word]:
        hit = False
        # print('Found instance of {!r} in str2: {} ({!r})'.format(word, i, words2[i]))
        for substring in substrings:
          # print('Testing if {!r} continues {}'.format(word, [words2[x] for x in substring]))
          if i == substring[-1] + 1:
            # Match! The substring continues.
            # print('Match! ({} == {} + 1)'.format(i, substring[-1]))
            hit = True
            substring.append(i)
            new_substrings.append(substring)
          else:
            # Miss! End of this substring, unless another occurrence of the word continues it.
            # print('Miss!  ({} != {} + 1)'.format(i, substring[-1]))
            pass
        if not hit:
          # If this word didn't extend any other substring, start a new one.
          new_substrings.append([i])
          # print('Starting new substring: [{!r}]'.format(words2[i]))
      # Before throwing away the old list, check if it contained any record-breaking substrings.
      longest_substring = get_new_longest_substring(words2, substrings, longest_substring, uniqueness)
      substrings = new_substrings
    else:
      # Miss! End of all running substrings.
      # print('Miss! (not in str2)')
      # Check if we've found a new longest one, then delete the rest.
      longest_substring = get_new_longest_substring(words2, substrings, longest_substring, uniqueness)
      substrings = []
  longest_substring = get_new_longest_substring(words2, substrings, longest_substring, uniqueness)
  # print('Result:')
  # print([words2[x] for x in longest_substring])
  return [words2[x] for x in longest_substring]


def get_new_longest_substring(words, substrings, longest_substring, uniqueness=None):
  if uniqueness:
    substring_words = [words[i] for i in longest_substring]
    longest_substring_score = score_words(substring_words, uniqueness, weight_length=True)
  for substring in substrings:
    if uniqueness:
      substring_words = [words[i] for i in substring]
      substring_score = score_words(substring_words, uniqueness, weight_length=True)
      if substring_score > longest_substring_score:
        # print('Found new longest substring ({} > {}): {}'
        #       .format(substring_score, longest_substring_score, [words[i] for i in substring]))
        longest_substring_score = substring_score
        longest_substring = substring
    else:
      if len(substring) > len(longest_substring):
        # print('Found new longest substring: {}'.format([words[i] for i in substring]))
        longest_substring = substring
  return longest_substring


def tone_down_logger():
  """Change the logging level names from all-caps to capitalized lowercase.
  E.g. "WARNING" -> "Warning" (turn down the volume a bit in your log files)"""
  for level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
    level_name = logging.getLevelName(level)
    logging.addLevelName(level, level_name.capitalize())


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
