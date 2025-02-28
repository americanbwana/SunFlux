#!/usr/bin/env python3
#
# BSD 3-Clause License
#
# Copyright (c) 2022-2023 Fred W6BSD
# All rights reserved.
#
#

import colorsys
import logging
import os
import sqlite3
import sys

from datetime import datetime, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

import adapters

from config import Config

plt.style.use(['classic', 'fast'])

NB_DAYS = 34

WWV_REQUEST = """
SELECT MAX(wwv.A), AVG(wwv.A), MIN(wwv.A), DATE(DATETIME(wwv.time, "unixepoch")) AS dt
FROM wwv
WHERE wwv.time > ?
GROUP BY dt
"""

WWV_CONDITIONS = "SELECT conditions FROM wwv ORDER BY time DESC LIMIT 1"

def color_complement(hue, saturation, value, alpha):
  rgb = colorsys.hsv_to_rgb(hue, saturation, value)
  c_rgb = [1.0 - c for c in rgb]
  c_hsv = colorsys.rgb_to_hsv(*c_rgb)
  return c_hsv + (alpha, )


def get_conditions(db_name):
  conn = sqlite3.connect(db_name, timeout=5,
                         detect_types=sqlite3.PARSE_DECLTYPES)
  with conn:
    curs = conn.cursor()
    result = curs.execute(WWV_CONDITIONS).fetchone()
  return result[0]

def get_wwv(db_name, days):
  data = []
  print(db_name)
  print(days)
  start_date = datetime.utcnow() - timedelta(days=days)
  print(start_date)
  conn = sqlite3.connect(db_name, timeout=5,
                         detect_types=sqlite3.PARSE_DECLTYPES)
  conn.set_trace_callback(print)
  with conn:
    curs = conn.cursor()
    results = curs.execute(WWV_REQUEST, (start_date,))
    for res in results:
      dte = datetime.strptime(res[-1], '%Y-%m-%d')
      data.append((dte, *res[:-1]))
  return data

def autolabel(ax, rects):
  """Attach a text label above each bar displaying its height"""
  for rect in rects:
    height = rect.get_height()
    color = rect.get_facecolor()
    ax.text(rect.get_x() + rect.get_width() / 2., 1, f'{int(height)}',
            color=color_complement(*color), fontsize="10", ha='center')

def graph(data, condition, filename):

  datetm = np.array([d[0] for d in data])
  amax = np.array([d[1] for d in data])
  amin = np.array([d[3] for d in data])
  aavg = np.array([d[2] for d in data])

  colors = ['lightgreen'] * len(aavg)
  for pos, val in enumerate(aavg):
    if 20 < val < 30:
      colors[pos] = 'darkorange'
    elif 30 < val < 50:
      colors[pos] = 'red'
    elif 50 < val < 100:
      colors[pos] = 'darkred'
    elif val >= 100:
      colors[pos] = 'darkmagenta'

  today = datetime.utcnow().strftime('%Y/%m/%d %H:%M UTC')
  fig = plt.figure(figsize=(12, 5))
  fig.suptitle('A-Index', fontsize=14, fontweight='bold')
  fig.text(0.01, 0.02, f'SunFluxBot By W6BSD {today}')
  fig.text(0.15, 0.8, "Forecast: " + condition, fontsize=12, zorder=4,
           bbox=dict(boxstyle='round', linewidth=1, facecolor='linen', alpha=1, pad=.8))

  axgc = plt.gca()
  axgc.tick_params(labelsize=10)
  bars = axgc.bar(datetm, aavg, linewidth=0.75, zorder=2, color=colors)
  axgc.plot(datetm, amax, marker='v', linewidth=0, color="steelblue")
  axgc.plot(datetm, amin, marker='^', linewidth=0, color="navy")
  autolabel(axgc, bars)

  axgc.axhline(y=20, linewidth=1.5, zorder=1, color='green')
  axgc.axhline(y=30, linewidth=1.5, zorder=1, color='darkorange')
  axgc.axhline(y=40, linewidth=1.5, zorder=1, color='red')
  axgc.axhline(y=50, linewidth=1.5, zorder=1, color='darkred')
  axgc.axhline(y=100, linewidth=1.5, zorder=1, color='darkmagenta')

  loc = mdates.DayLocator(interval=2)
  axgc.xaxis.set_major_formatter(mdates.DateFormatter('%a, %b %d UTC'))
  axgc.xaxis.set_major_locator(loc)
  axgc.xaxis.set_minor_locator(mdates.DayLocator())

  axgc.set_ylim(0, max(amax) * 1.15)
  axgc.set_ylabel('A-Index')
  axgc.grid(color="gray", linestyle="dotted", linewidth=.5)
  axgc.margins(.01)

  axgc.legend(['Max', 'Min'], loc='upper right', fontsize='10',
              facecolor='linen', borderaxespad=1)

  fig.autofmt_xdate(rotation=10, ha="center")
  plt.savefig(filename, transparent=False, dpi=100)
  plt.close()
  return filename

def main():
  _config = Config()
  config = _config.get('aindex')
  del _config

  adapters.install_adapters()
  logging.basicConfig(
    format='%(asctime)s %(name)s:%(lineno)3d - %(levelname)s - %(message)s', datefmt='%x %X',
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO'))
  )
  logger = logging.getLogger('aindex')

  try:
    name = sys.argv[1]
  except IndexError:
    name = '/tmp/aindex.png'

  # data = get_wwv(config['db_name'], 34)
  data = get_wwv(config['db_name'], config.get('nb_days', NB_DAYS))
  condition = get_conditions(config['db_name'])
  if data:
    graph(data, condition, name)
    logger.info('Graph "%s" saved', name)
  else:
    logger.warning('No data collected')


if __name__ == "__main__":
  sys.exit(main())
