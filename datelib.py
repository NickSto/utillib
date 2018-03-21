#!/usr/bin/env python3
import sys
import datetime


class TimeUnit(object):
  def __init__(self, name=None, seconds=None, **kwargs):
    self.name = name
    self.seconds = seconds
    for kwarg, value in kwargs.items():
      setattr(self, kwarg, value)
  def __lt__(self, other):
    return self.seconds < other.seconds
  def __le__(self, other):
    return self.seconds <= other.seconds
  def __gt__(self, other):
    return self.seconds > other.seconds
  def __ge__(self, other):
    return self.seconds >= other.seconds
  def __repr__(self):
    return '<{} {}>'.format(self.name.upper(), type(self).__name__)
  def __str__(self):
    return self.name.upper()


SECOND = TimeUnit(
  name='second',
  abbrev='sec',
  symbol='s',
  format='%S',
  format_rounded='%Y-%m-%d %H:%M:%S',
  min_value=0,
  max_value=59,
  seconds=1,
)

MINUTE = TimeUnit(
  name='minute',
  abbrev='min',
  symbol='m',
  format='%M',
  format_rounded='%Y-%m-%d %H:%M',
  min_value=0,
  max_value=59,
  seconds=SECOND.seconds * 60,
)

HOUR = TimeUnit(
  name='hour',
  abbrev='hr',
  symbol='h',
  format='%H',
  format_rounded='%Y-%m-%d %H:00',
  min_value=0,
  max_value=23,
  seconds=MINUTE.seconds * 60,
)

DAY = TimeUnit(
  name='day',
  abbrev='day',
  symbol='d',
  format='%d',
  format_rounded='%Y-%m-%d',
  min_value=1,
  max_value=31,
  seconds=HOUR.seconds * 24,
)

WEEK = TimeUnit(
  name='week',
  abbrev='week',
  symbol='w',
  format='%d',
  format_rounded='%Y-%m-%d',
  min_value=0,
  max_value=4,
  seconds=DAY.seconds * 7,
)

MONTH = TimeUnit(
  name='month',
  abbrev='mo',
  symbol='M',
  format='%b',
  format_rounded='%b %Y',
  min_value=1,
  max_value=12,
  seconds=int(DAY.seconds * 30.5),
)

YEAR = TimeUnit(
  name='year',
  abbrev='yr',
  symbol='y',
  format='%Y',
  format_rounded='%Y',
  min_value=-sys.maxsize,
  max_value=sys.maxsize,
  seconds=int(DAY.seconds * 365.25),
)

TIME_UNITS = (SECOND, MINUTE, HOUR, DAY, WEEK, MONTH, YEAR)

UNIT_NAMES = {}
for _time_unit in TIME_UNITS:
  UNIT_NAMES[_time_unit.name] = _time_unit
  UNIT_NAMES[_time_unit.name+'s'] = _time_unit
  UNIT_NAMES[_time_unit.abbrev] = _time_unit

UNIT_SYMBOLS = {}
for _time_unit in TIME_UNITS:
  UNIT_SYMBOLS[_time_unit.symbol] = _time_unit

MONTH_LENGTHS = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}


def is_leap_year(year):
  """Returns True if `year` is a leap year, False if not."""
  return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def floor_datetime(dt, time_unit):
  """Round a datetime down to the nearest `time_unit`.
  `dt` must be a datetime.datetime and `time_unit` must be a TimeUnit."""
  dt_dict = {}
  for this_unit in TIME_UNITS:
    if this_unit == WEEK:
      continue
    unit_value = getattr(dt, this_unit.name)
    if time_unit == WEEK and this_unit == DAY:
      unit_value = unit_value - (unit_value % 7)
    elif this_unit.seconds < time_unit.seconds:
      unit_value = this_unit.min_value
    dt_dict[this_unit.name] = unit_value
  return datetime.datetime(**dt_dict)


def increase_datetime(dt, time_unit, amount):
  """Increase the datetime `dt` by `amount` `time_unit`s.
  `dt` must be a datetime.datetime and `time_unit` must be a TimeUnit."""
  # Currently this only increments by 1 at a time in order to avoid complicated math.
  #TODO: Complicated math.
  new_dt = dt
  for i in range(amount):
    new_dt = increment_datetime(new_dt, time_unit)
  return new_dt


def increment_datetime(dt, time_unit):
  """Increment `dt` by 1 `time_unit`s.
  `dt` must be a datetime.datetime and `time_unit` must be a TimeUnit."""
  dt_dict = {}
  carry = 0
  for this_unit in TIME_UNITS:
    if this_unit == WEEK:
      if time_unit == WEEK:
        unit_value = dt.day + 7
        this_unit = DAY
      else:
        continue
    else:
      unit_value = getattr(dt, this_unit.name)
      if this_unit == time_unit:
        unit_value += 1
      unit_value += carry
    # Figure out whether the unit overflowed and needs to be wrapped to zero, with a carry.
    if this_unit == DAY:
      if dt.month == 2:
        if is_leap_year(dt.year):
          max_value = 29
        else:
          max_value = 28
      else:
        max_value = MONTH_LENGTHS[dt.month]
    else:
      max_value = this_unit.max_value
    if unit_value > max_value:
      carry = 1
      unit_value = this_unit.min_value + unit_value - max_value - 1
    else:
      carry = 0
    dt_dict[this_unit.name] = unit_value
  return datetime.datetime(**dt_dict)
