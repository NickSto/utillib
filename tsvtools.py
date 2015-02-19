#!/usr/bin/env python
from __future__ import division


def read_tsv(infile, labels=None):
  """Read a tsv, returning a list of rows, each represented by a dict mapping
  column labels to values. If no labels are given, the first line of the tsv is
  assumed to be a header with the column labels. Starting #'s are not removed
  from the header.
  Input argument is an opened file-like object (like a file or sys.stdin).
  Labels must be a list of label strings."""
  # If labels were given, build mapping between them and column numbers.
  columns = {}
  if labels:
    for (col, field) in enumerate(labels):
      columns[field] = col
    in_header = False
  else:
    in_header = True
  rows = []
  for line in infile:
    # Build columns dict, mapping column labels to column numbers.
    fields = line.rstrip('\r\n').split('\t')
    if in_header:
      for (col, field) in enumerate(fields):
        columns[field] = col
      in_header = False
      continue
    # Build a dict for a row, mapping column labels to values.
    row = {}
    for label in columns:
      try:
        row[label] = fields[columns[label]]
      except IndexError:
        row[label] = ''
    rows.append(row)
  return rows


def table2dictlist(rows, key_label, key_label2=None):
  """Take a table like that returned by read_tsv() and turn it into a dict mapping values in the
  "key_label" column to lists of rows with that value. If key_label2 is provided, that is used as
  an alternative key column to be used in the case where the first column is not present or empty
  (empty string). If both are missing, the row is skipped."""
  dictlist = {}
  for row in rows:
    # Try to get the value of the key column.
    # If the column is not present or empty, try the alternative key column (key_label2) if it's
    # given. If that doesn't work, silently skip the row.
    key = row.get(key_label)
    if key is None or key == '' and key_label2 is not None:
      key = row.get(key_label2)
      if key is None or key == '' and key_label2 is not None:
        continue
    rowlist = dictlist.get(key, [])
    rowlist.append(row)
    dictlist[key] = rowlist
  return dictlist


def join(table1, tableN, join_label):
  """Join two tables with a 1:N relationship on a field label "join_label".
  The tables must be in the format returned by read_tsv(). For one of the tables
  ("table1"), the join column must be uniquely identifying.
  The result will not contain information from any rows in either table that do
  not have a join value present in the other table."""
  result = []
  tableNdict = table2dictlist(tableN, join_label)
  for row1 in table1:
    try:
      join_value = row1[join_label]
    except KeyError:
      continue
    try:
      rowNlist = tableNdict[join_value]
    except KeyError:
      continue
    for rowN in rowNlist:
      #TODO: check if this modifies tableN
      rowN.update(row1)
      result.append(rowN)
  return result


def row_dicts2row_lists(row_dicts, header=None):
  """Transform a table from a list of row dicts to a list of row lists.
  The header must be a list of lists, one list for every header line, each line
  being a list of column labels."""
  row_lists = []
  for row_dict in row_dicts:
    if header:
      row_list = []
      for label in header[0]:
        row_list.append(row_dict[label])
      row_lists.append(row_list)
    else:
      row_lists.append(row_dict.values())
  return row_lists


def print_table(rows, header):
  header_str = '\n'.join(map(lambda x: '\t'.join(x), header))
  print header_str
  for row in rows:
    print '\t'.join(row)
