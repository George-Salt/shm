#!/usr/bin/env python3
import os
import re
import sys
import time
import tty
import termios
import select
import signal
import shutil
import subprocess
import unicodedata
import textwrap
import codecs
import pty
import fcntl
import struct
import collections
from pathlib import Path
from i18n import tr, get_language, set_language

ROOT = Path(os.environ.get('SHM_HOME', str(Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'shm')))
PLUGINS = ROOT / 'plugins'
RESET = '\x1b[0m'
ACCENT = '\x1b[1;35m'
MUTED = '\x1b[2m'
BOLD = '\x1b[1m'


def cell_width(s):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'FW' else 1 for c in s)


def clip(s, max_width):
    if max_width <= 0:
        return ''
    result = ''
    for c in str(s).replace('\n', ' ').replace('\r', ' '):
        if cell_width(result + c) > max_width:
            return result[:-1] + '…' if cell_width(result) == max_width and result else result + ('…' if cell_width(result) < max_width else '')
        result += c
    return result


def scan():
    result = []
    if not PLUGINS.is_dir():
        return result
    for folder in PLUGINS.iterdir():
        if folder.is_symlink() or not folder.is_dir() or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', folder.name):
            continue
        conf = folder / 'plugin.conf'
        if conf.is_symlink() or not conf.is_file():
            continue
        try:
            data = dict(line.split('=', 1) for line in conf.read_text(encoding='utf-8').splitlines() if '=' in line)
        except (OSError, UnicodeError):
            continue
        entry = data.get('entry', 'main.sh').strip()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.sh', entry) or '..' in entry:
            continue
        script = folder / entry
        if script.is_symlink() or not script.is_file():
            continue
        result.append({'id': folder.name, 'name': data.get('name.' + get_language(), data.get('name', folder.name)).strip(), 'description': data.get('description.' + get_language(), data.get('description', tr('Нет описания.'))).strip(), 'category': data.get('category.' + get_language(), data.get('category', tr('Другое'))).strip(), 'author': data.get('author', '—').strip(), 'script': script})
    return sorted(result, key=lambda x: (x['name'].casefold(), x['id']))


class UI:
    def __init__(self):
        self.items = scan()
        self.selected = self.items[0]['id'] if self.items else ''
        self.query = ''
        self.searching = False
        self.offset = 0
        self.message = tr('Готово') + ' · l: RU / EN'
        self.last_scan = time.monotonic()
        self.last_size = None
        self.dirty = True
        self.confirm = False
        self.clickmap = {}
        self.old_term = None
        self.input_buffer = ''
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.last_click = (0, None)

    def write(self, s):
        sys.stdout.write(s)
        sys.stdout.flush()

    def enter(self):
        self.old_term = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        self.write('\x1b[?1049h\x1b[?25l\x1b[?1000h\x1b[?1006h\x1b[0m')
        self.dirty = True

    def leave(self):
        self.write('\x1b[0m\x1b[?1006l\x1b[?1000l\x1b[?25h\x1b[?1049l')
        if self.old_term is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.old_term)
            self.old_term = None

    def size(self):
        x = shutil.get_terminal_size(fallback=(80, 24))
        return x.lines, x.columns

    def filtered(self):
        q = self.query.casefold().strip()
        return [p for p in self.items if q in ' '.join((p['name'], p['id'], p['description'], p['category'])).casefold()]

    def current(self):
        items = self.filtered()
        return next((p for p in items if p['id'] == self.selected), items[0] if items else None)

    def navigate(self, amount):
        items = self.filtered()
        if not items:
            return
        old = self.current()
        i = next((i for i, p in enumerate(items) if p['id'] == old['id']), 0)
        self.selected = items[max(0, min(len(items) - 1, i + amount))]['id']
        self.dirty = True

    def draw(self):
        h, w = self.size()
        self.clickmap = {}
        if w < 26 or h < 9:
            self.write('\x1b[H\x1b[2J' + ACCENT + '❯ SHM' + RESET + '\r\n' + tr('Увеличь терминал.') + '\r\n' + tr('q — выход'))
            return
        wide = w >= 76
        left = min(42, max(32, w // 3)) if wide else w
        canvas = [''] * h

        def line(y, x, value, style='', maximum=None):
            if y < 0 or y >= h or x >= w:
                return
            width = max(0, min(w - x, maximum if maximum is not None else w - x))
            value = clip(value, width)
            canvas[y] += f'\x1b[{x + 1}G{style}{value}{RESET}'

        line(0, 2, '❯ SHM  /  shell manager', ACCENT)
        if w > 54:
            status = f'{len(self.items)} {tr("плагинов")} · {get_language().upper()} [l]'
            line(0, w - len(status) - 2, status, MUTED)
        line(1, 2, '─' * (w - 4), MUTED)
        line(2, 2, tr('ПЛАГИНЫ'), BOLD)
        line(3, 2, '/ ' + (self.query if self.query else tr('Поиск')) + ('_' if self.searching else ''), MUTED, left - 4)
        items = self.filtered()
        curr = self.current()
        if curr:
            self.selected = curr['id']
        available = max(1, h - 8)
        pos = next((i for i, p in enumerate(items) if p['id'] == self.selected), 0)
        self.offset = max(0, min(self.offset, max(0, len(items) - available)))
        if pos < self.offset:
            self.offset = pos
        elif pos >= self.offset + available:
            self.offset = pos - available + 1
        for i in range(self.offset, min(len(items), self.offset + available)):
            item = items[i]
            y = 5 + i - self.offset
            focused = item['id'] == self.selected
            line(y, 2, ('❯ ' if focused else '  ') + item['name'], ACCENT if focused else '', left - 4)
            self.clickmap[y] = item['id']
        if not items:
            line(5, 3, tr('Плагины не найдены.'), MUTED, left - 5)
        if wide:
            for y in range(2, h - 2):
                line(y, left, '│', MUTED)
            x, width = left + 3, w - left - 5
            line(2, x, tr('ИНФОРМАЦИЯ'), BOLD, width)
            if curr:
                line(4, x, curr['name'], ACCENT, width)
                line(6, x, f'ID: {curr["id"]}', MUTED, width)
                line(7, x, f'{tr("Категория:")} {curr["category"]}', MUTED, width)
                line(8, x, f'{tr("Автор:")} {curr["author"]}', MUTED, width)
                if h > 15:
                    line(10, x, tr('ОПИСАНИЕ'), BOLD, width)
                    desc = curr['description']
                    words = desc.split()
                    parts = []
                    temp = ''
                    for word in words:
                        if temp and cell_width(temp + ' ' + word) > width:
                            parts.append(temp)
                            temp = word
                        else:
                            temp = (temp + ' ' + word).strip()
                    if temp:
                        parts.append(temp)
                    for y, para in enumerate(parts[:max(0, h - 15)], 12):
                        line(y, x, para, '', width)
        line(h - 3, 2, '─' * (w - 4), MUTED)
        line(h - 2, 2, tr('↑↓ выбор  Enter запуск  d удалить  / поиск  r обновить  l язык  q выход') if w >= 78 else tr('↑↓ выбор  Enter  d удалить  / поиск  r  q') if w >= 48 else tr('↑↓ Enter d / r q'), MUTED, w - 4)
        line(h - 1, 2, self.message, MUTED, w - 4)
        if self.confirm:
            line(max(2, h // 2 - 2), max(2, (w - 48) // 2), tr('Удалить выбранный плагин?'), ACCENT, min(48, w - 4))
            line(max(3, h // 2 - 1), max(2, (w - 48) // 2), tr('y — удалить     n / Esc — отмена'), BOLD, min(48, w - 4))
        output = '\x1b[0m\x1b[H\x1b[2J'
        for y, fragments in enumerate(canvas):
            if fragments:
                output += f'\x1b[{y + 1};1H' + fragments
        self.write(output + RESET)

    def delete(self):
        item = self.current()
        if not item:
            self.message = tr('Нет выбранного плагина.')
            return
        folder = PLUGINS / item['id']
        try:
            if folder.is_symlink() or not folder.is_dir() or folder.resolve().parent != PLUGINS.resolve():
                raise OSError(tr('Некорректный путь плагина'))
            shutil.rmtree(folder)
            self.items = scan()
            self.selected = self.items[0]['id'] if self.items else ''
            self.offset = 0
            self.message = f'{tr("Удалён:")} {item["name"]}'
        except OSError as e:
            self.message = f'{tr("Ошибка удаления:")} {e}'

    def run_plugin(self):
        item = self.current()
        if not item:
            return
        self.write('\x1b[?1000l\x1b[?1006l\x1b[?25l')
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
        master, slave = pty.openpty()
        slave_attrs = termios.tcgetattr(slave)
        slave_attrs[3] |= termios.ICANON | termios.ECHO | termios.ISIG
        slave_attrs[1] |= termios.OPOST | termios.ONLCR
        termios.tcsetattr(slave, termios.TCSANOW, slave_attrs)
        proc = None
        logs = collections.deque(maxlen=3500)
        logs.append(tr('Запуск плагина…'))
        current = ''
        partial_escape = ''
        pending_cr = False
        scroll = 0
        pending = ''
        status = None
        done = False
        last_size = (0, 0)
        dirty = True
        last_draw = 0.0
        output_decoder = codecs.getincrementaldecoder('utf-8')('replace')
        input_decoder = codecs.getincrementaldecoder('utf-8')('replace')
        input_buffer = ''

        def add_output(chunk):
            nonlocal current, partial_escape, pending_cr, scroll, dirty
            data = partial_escape + chunk
            partial_escape = ''
            i = 0
            while i < len(data):
                char = data[i]
                if pending_cr:
                    if char != '\n':
                        current = ''
                    pending_cr = False
                if char == '\x1b':
                    if i + 1 >= len(data):
                        partial_escape = data[i:]
                        break
                    if data[i + 1] == '[':
                        m = re.match(r'\x1b\[[0-?]*[ -/]*[@-~]', data[i:])
                        if m:
                            i += len(m.group())
                            continue
                        partial_escape = data[i:]
                        break
                    if data[i + 1] == ']':
                        m = re.search(r'\x07|\x1b\\', data[i + 2:])
                        if m:
                            i += 2 + m.end()
                            continue
                        partial_escape = data[i:]
                        break
                    i += 2
                    continue
                if char == '\n':
                    logs.append(current)
                    current = ''
                elif char == '\r':
                    pending_cr = True
                elif char in ('\b', '\x7f'):
                    current = current[:-1]
                elif char == '\t':
                    current += ' ' * (4 - len(current) % 4)
                elif char.isprintable():
                    current += char
                    if len(current) > 2500:
                        logs.append(current[:2500])
                        current = current[2500:]
                i += 1
            dirty = True

        def child_tty():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        def draw_runner():
            h, w = self.size()
            if h < 8 or w < 30:
                self.write('\x1b[0m\x1b[H\x1b[2J' + tr('Увеличь окно терминала.'))
                return
            bar = '─' * (w - 4)
            state = tr('ГОТОВО') if status == 0 else tr('ОШИБКА') if done else tr('ВЫПОЛНЯЕТСЯ')
            label = f'  ❯ SHM  /  {item["name"]}'
            output = ['\x1b[0m\x1b[H\x1b[2J', ACCENT, clip(label, w-2), RESET]
            output += [f'\x1b[2;3H{MUTED}{bar}{RESET}', f'\x1b[3;3H{BOLD}{tr("ВЫВОД ПЛАГИНА")}{RESET}', f'\x1b[3;{max(3,w-len(state)-2)}H{ACCENT}{state}{RESET}']
            visible = max(1, h-7)
            all_lines = list(logs) + ([current] if current else [])
            end = max(0, len(all_lines)-scroll)
            begin = max(0, end-visible)
            for row, content in enumerate(all_lines[begin:end], 5):
                output.append(f'\x1b[{row};3H{clip(content, w-4)}')
            output.append(f'\x1b[{h-2};3H{MUTED}{bar}{RESET}')
            footer = tr('Enter — вернуться   ↑↓/колесо — журнал   q — вернуться') if done else tr('Плагин принимает ввод   Ctrl+C — прервать   PgUp/PgDn — журнал')
            output.append(f'\x1b[{h-1};3H{MUTED}{clip(footer, w-4)}{RESET}')
            if scroll:
                output.append(f'\x1b[{h};3H{MUTED}{tr("Прокрутка:")} -{scroll} {tr("строк")}{RESET}')
            else:
                output.append(f'\x1b[{h};3H{MUTED}{clip(item["description"], w-4)}{RESET}')
            self.write(''.join(output))

        try:
            rows, cols = self.size()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
            proc = subprocess.Popen(['bash', str(item['script'])], stdin=slave, stdout=slave, stderr=slave,
                                    preexec_fn=child_tty, close_fds=True, bufsize=0,
                                    env=dict(os.environ, SHM_LANG=get_language()))
            os.close(slave)
            slave = -1
            while True:
                size = self.size()
                if size != last_size:
                    last_size = size
                    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', size[0], size[1], 0, 0))
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGWINCH)
                    dirty = True
                if dirty and time.monotonic() - last_draw >= 0.045:
                    draw_runner()
                    dirty = False
                    last_draw = time.monotonic()
                fds = [sys.stdin.fileno()]
                if not done:
                    fds.append(master)
                ready, _, _ = select.select(fds, [], [], 0.06)
                if master in ready:
                    try:
                        chunk = os.read(master, 8192)
                        if chunk:
                            add_output(output_decoder.decode(chunk))
                    except OSError:
                        pass
                if proc.poll() is not None and not done:
                    try:
                        while True:
                            r, _, _ = select.select([master], [], [], 0)
                            if not r:
                                break
                            chunk = os.read(master, 8192)
                            if not chunk:
                                break
                            add_output(output_decoder.decode(chunk))
                    except OSError:
                        pass
                    remaining = output_decoder.decode(b'', final=True)
                    if remaining:
                        add_output(remaining)
                    if current:
                        logs.append(current)
                        current = ''
                    status = proc.returncode
                    done = True
                    dirty = True
                if sys.stdin.fileno() in ready:
                    raw = os.read(sys.stdin.fileno(), 4096)
                    if not raw:
                        break
                    input_buffer += input_decoder.decode(raw)
                    if done:
                        if '\r' in input_buffer or '\n' in input_buffer or 'q' in input_buffer or '\x1b' in input_buffer:
                            break
                        if '\x1b[A' in input_buffer or '\x1b[5~' in input_buffer or '\x1b[<64' in input_buffer:
                            scroll = min(max(0, len(logs) - 1), scroll + 3)
                        if '\x1b[B' in input_buffer or '\x1b[6~' in input_buffer or '\x1b[<65' in input_buffer:
                            scroll = max(0, scroll - 3)
                    else:
                        if '\x1b[5~' in input_buffer:
                            scroll = min(max(0, len(logs) - 1), scroll + 5)
                            input_buffer = input_buffer.replace('\x1b[5~','')
                        if '\x1b[6~' in input_buffer:
                            scroll = max(0, scroll - 5)
                            input_buffer = input_buffer.replace('\x1b[6~','')
                        if input_buffer:
                            os.write(master, input_buffer.encode('utf-8'))
                    input_buffer = ''
                    dirty = True
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            if slave >= 0:
                os.close(slave)
            os.close(master)
            self.write('\x1b[0m\x1b[?1000h\x1b[?1006h\x1b[?25l')
            self.message = f'{item["name"]}: {tr("код")} {status if status is not None else tr("прерван")}'
            self.dirty = True

    def handle(self, key):
        if isinstance(key, tuple) and key[0] == 'mouse':
            _, btn, x, y, pressed = key
            if not pressed:
                return True
            if btn == 64:
                self.navigate(-3)
            elif btn == 65:
                self.navigate(3)
            elif btn == 0 and y in self.clickmap:
                ident = self.clickmap[y]
                now = time.monotonic()
                if ident == self.last_click[1] and now - self.last_click[0] < 0.4:
                    self.selected = ident
                    self.run_plugin()
                else:
                    self.selected = ident
                self.last_click = (now, ident)
            return True
        if self.confirm:
            if key in ('y', 'Y', 'д', 'Д'):
                self.delete()
            self.confirm = False
            return True
        if self.searching:
            if key in ('ENTER',):
                self.searching = False
            elif key == 'ESC':
                self.searching = False
                self.query = ''
            elif key == 'BACKSPACE':
                self.query = self.query[:-1]
            elif len(key) == 1 and key.isprintable():
                self.query += key
            items = self.filtered()
            self.selected = items[0]['id'] if items else ''
            self.offset = 0
            return True
        if key in ('q', 'Q', 'ESC', 'CTRL_C'):
            return False
        if key in ('DOWN', 'j'):
            self.navigate(1)
        elif key in ('UP', 'k'):
            self.navigate(-1)
        elif key == 'PAGEDOWN':
            self.navigate(max(1, self.size()[0] - 8))
        elif key == 'PAGEUP':
            self.navigate(-max(1, self.size()[0] - 8))
        elif key == 'HOME':
            self.navigate(-len(self.items))
        elif key == 'END':
            self.navigate(len(self.items))
        elif key == 'ENTER':
            self.run_plugin()
        elif key in ('d', 'D', 'DELETE'):
            self.confirm = True
        elif key == '/':
            self.searching = True
            self.query = ''
        elif key in ('l', 'L'):
            try:
                set_language('en' if get_language() == 'ru' else 'ru')
                self.items = scan()
                self.message = 'Language: English' if get_language() == 'en' else 'Язык: Русский'
            except OSError as exc:
                self.message = str(exc)
        elif key == 'r':
            self.items = scan()
            self.message = tr('Список обновлён.')
        return True

    def pop_event(self):
        b = self.input_buffer
        if not b:
            return None
        if b.startswith('\x1b[<'):
            m = re.match(r'\x1b\[<(\d+);(\d+);(\d+)([Mm])', b)
            if m:
                self.input_buffer = b[m.end():]
                return ('mouse', int(m[1]), int(m[2]) - 1, int(m[3]) - 1, m[4] == 'M')
            if len(b) < 24:
                return None
        sequences = {'\x1b[A':'UP', '\x1b[B':'DOWN', '\x1b[5~':'PAGEUP', '\x1b[6~':'PAGEDOWN', '\x1b[3~':'DELETE', '\x1b[H':'HOME', '\x1b[F':'END', '\x1bOH':'HOME', '\x1bOF':'END', '\x1b[C':'RIGHT', '\x1b[D':'LEFT'}
        for seq, name in sequences.items():
            if b.startswith(seq):
                self.input_buffer = b[len(seq):]
                return name
        if b.startswith('\x1b[') and len(b) < 9 and not re.search(r'[A-Za-z~]', b[2:]):
            return None
        if b.startswith('\x1b'):
            self.input_buffer = b[1:]
            return 'ESC'
        self.input_buffer = b[1:]
        if b[0] in ('\r', '\n'):
            return 'ENTER'
        if b[0] in ('\x7f', '\b'):
            return 'BACKSPACE'
        if b[0] == '\x03':
            return 'CTRL_C'
        return b[0]

    def loop(self):
        self.enter()
        try:
            running = True
            while running:
                size = self.size()
                if size != self.last_size:
                    self.last_size = size
                    self.dirty = True
                if time.monotonic() - self.last_scan > 3:
                    new = scan()
                    if new != self.items:
                        self.items = new
                        self.dirty = True
                    self.last_scan = time.monotonic()
                if self.dirty:
                    self.draw()
                    self.dirty = False
                readable, _, _ = select.select([sys.stdin.fileno()], [], [], 0.15)
                if readable:
                    self.input_buffer += self.decoder.decode(os.read(sys.stdin.fileno(), 4096))
                while True:
                    event = self.pop_event()
                    if event is None:
                        break
                    running = self.handle(event)
                    self.dirty = True
                    if not running:
                        break
        finally:
            self.leave()


if __name__ == '__main__':
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        sys.exit(tr('SHM нужен интерактивный терминал. Для списка: shm list'))
    UI().loop()
