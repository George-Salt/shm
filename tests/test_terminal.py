"""Exercise the actual TUI and plugin PTY with an inert fixture."""
import fcntl
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent


class TerminalTests(unittest.TestCase):
    def test_switch_and_pass_language_to_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / 'plugins' / 'demo'
            plugin.mkdir(parents=True)
            (plugin / 'plugin.conf').write_text('name.en=Demo\nname.ru=Пример\nentry=main.sh\n')
            (plugin / 'main.sh').write_text('printf "LANGUAGE_FROM_PLUGIN=%s\\n" "$SHM_LANG"\n')
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 26, 120, 0, 0))
            process = subprocess.Popen([sys.executable, str(ROOT / 'tui.py')], stdin=slave, stdout=slave, stderr=slave,
                                       env=dict(os.environ, SHM_HOME=directory, SHM_LANG='en', TERM='xterm-256color'))
            os.close(slave)

            data = b''

            def expect(text):
                nonlocal data
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if text.encode() in data:
                        data = data.split(text.encode(), 1)[1]
                        return
                    if select.select([master], [], [], 0.1)[0]:
                        data += os.read(master, 65536)
                self.fail('Terminal output did not contain: ' + text)

            try:
                expect('PLUGINS')
                os.write(master, b'l')
                expect('ПЛАГИНЫ')
                self.assertEqual((root / 'language').read_text(), 'ru\n')
                os.write(master, b'\r')
                expect('LANGUAGE_FROM_PLUGIN=ru')
                # Wait until the runner has displayed completion before returning.
                expect('Enter — вернуться')
                os.write(master, b'\r')
                expect('ПЛАГИНЫ')
                os.write(master, b'l')
                expect('PLUGINS')
                os.write(master, b'q')
                self.assertEqual(process.wait(timeout=3), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                os.close(master)


if __name__ == '__main__':
    unittest.main()
