#!/usr/bin/env python3
"""Capture the actual SHM PTY screen as PNG (requires Pillow and pyte).

Run from a development environment: python tools/capture_screenshot.py
This does not execute plugins or modify the user's installed SHM.
"""
import fcntl
import os
from pathlib import Path
import pty
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time

import pyte
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
COLS, ROWS = 120, 26
FONT_PATH = os.environ.get('SHM_SCREENSHOT_FONT', '/usr/share/fonts/noto/NotoSansMono-Regular.ttf')
font = ImageFont.truetype(FONT_PATH, 19)
fallback_font = ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf', 19)
CELL_W, CELL_H = 12, 27
colors = {'default': '#dedee8', 'magenta': '#c69af5', 'brightmagenta': '#d6afff'}

for language in ('en', 'ru'):
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        shutil.copytree(ROOT / 'plugins', home / 'plugins')
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', ROWS, COLS, 0, 0))
        process = subprocess.Popen([sys.executable, str(ROOT / 'tui.py')], stdin=slave, stdout=slave, stderr=slave,
                                   env=dict(os.environ, SHM_HOME=str(home), SHM_LANG=language, TERM='xterm-256color'))
        os.close(slave)
        screen = pyte.Screen(COLS, ROWS)
        stream = pyte.Stream(screen)
        decoder = __import__('codecs').getincrementaldecoder('utf-8')()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    stream.feed(decoder.decode(os.read(master, 65536)))
                    if ('Ready' if language == 'en' else 'Готово') in '\n'.join(screen.display):
                        break
            else:
                raise RuntimeError('SHM did not draw its screen')
            image = Image.new('RGB', (COLS * CELL_W + 40, ROWS * CELL_H + 68), '#16161e')
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=14, outline='#343442', width=2)
            for x, color in zip((22, 44, 66), ('#f7768e', '#e0af68', '#9ece6a')):
                draw.ellipse((x, 17, x + 10, 27), fill=color)
            draw.text((95, 9), 'shm — ' + language.upper(), fill='#9292a8', font=font)
            for y in range(ROWS):
                for x in range(COLS):
                    cell = screen.buffer[y][x]
                    if not cell.data or cell.data == ' ':
                        continue
                    color = colors.get(cell.fg, '#dedee8')
                    if cell.fg == 'default' and not cell.bold:
                        color = '#aaaabb'
                    draw.text((20 + x * CELL_W, 48 + y * CELL_H), cell.data, fill=color, font=fallback_font if cell.data in ('❯', '↑', '↓') else font)
            target = ROOT / 'docs' / 'images' / ('shm-' + language + '.png')
            image.save(target)
            print(target)
        finally:
            os.write(master, b'q')
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            os.close(master)
