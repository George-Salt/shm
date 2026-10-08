"""Verify the installer's explicit selector independently of system locale."""
import fcntl
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent


class InstallerTests(unittest.TestCase):
    def test_interactive_language_selection(self):
        for locale, choice, language, question, success in (
            ('ru_RU.UTF-8', '1', 'en', 'Install the bundled plugins?', 'SHM installed:'),
            ('en_US.UTF-8', '2', 'ru', 'Установить плагины', 'SHM установлен:'),
        ):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                home = Path(directory) / 'home'
                home.mkdir()
                data = Path(directory) / 'data'
                env = dict(os.environ, HOME=str(home), SHM_HOME=str(data), LANG=locale)
                for key in ('SHM_LANG', 'LC_ALL', 'LC_MESSAGES'):
                    env.pop(key, None)
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 100, 0, 0))
                process = subprocess.Popen(['bash', str(ROOT / 'install.sh')], stdin=slave, stdout=slave, stderr=slave, env=env)
                os.close(slave)
                output = b''

                def expect(text):
                    nonlocal output
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        if text.encode() in output:
                            return
                        if select.select([master], [], [], 0.1)[0]:
                            try:
                                output += os.read(master, 65536)
                            except OSError:
                                break
                    self.fail('Installer output missing: ' + text + '\n' + output.decode(errors='replace'))

                try:
                    expect('Language / Язык [1/2, en/ru]:')
                    os.write(master, (choice + '\n').encode())
                    expect(question)
                    os.write(master, b'n\n')
                    expect(success)
                    self.assertEqual(process.wait(timeout=3), 0)
                    self.assertEqual((data / 'language').read_text(), language + '\n')
                    self.assertFalse((data / 'plugins' / 'cleanup').exists())
                    app_env = dict(env, LANG='ru_RU.UTF-8' if language == 'en' else 'en_US.UTF-8')
                    result = subprocess.run([str(home / '.local/bin/shm'), 'lang'], env=app_env, capture_output=True, text=True, check=True)
                    self.assertEqual(result.stdout.strip(), language)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)

    def test_explicit_flag_and_environment(self):
        for args, explicit in ((['--lang', 'en'], 'ru'), ([], 'en')):
            with self.subTest(args=args), tempfile.TemporaryDirectory() as directory:
                env = dict(os.environ, HOME=directory, SHM_HOME=directory + '/data', SHM_LANG=explicit)
                result = subprocess.run(['bash', str(ROOT / 'install.sh')] + args, env=env, input='', text=True, capture_output=True, check=True)
                self.assertIn('SHM installed:', result.stdout)
                self.assertNotIn('Select language', result.stdout)
                self.assertEqual(Path(directory, 'data/language').read_text(), 'en\n')

    def test_invalid_flag_does_not_install(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, HOME=directory, SHM_HOME=directory + '/data')
            result = subprocess.run(['bash', str(ROOT / 'install.sh'), '--lang', 'de'], env=env, input='', text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(Path(directory, 'data').exists())


if __name__ == '__main__':
    unittest.main()
