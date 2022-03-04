#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause

from sys import argv, path, exit
from pathlib import Path

piclePath = Path(argv[0]).resolve().parent
if (piclePath / 'audioInterface').is_dir():
	path.insert(0, str(piclePath))
else:
	raise ImportError('Cannot find the audio interface gateware')

from audioInterface import cli
if __name__ == '__main__':
	exit(cli())
