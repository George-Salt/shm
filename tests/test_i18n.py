"""Language selection, live switching, and catalog consistency checks."""
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'SHM_HOME': self.temp.name, 'LANG': 'en_US.UTF-8'}, clear=True)
        self.environment.start()
        import i18n
        self.i18n = importlib.reload(i18n)
        import tui
        self.tui = importlib.reload(tui)

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def test_precedence_and_fallback(self):
        self.assertEqual(self.i18n.get_language(), 'en')
        os.environ['LANG'] = 'ru_RU.UTF-8'
        self.assertEqual(self.i18n.get_language(), 'ru')
        os.environ['LC_MESSAGES'] = 'en_US.UTF-8'
        self.assertEqual(self.i18n.get_language(), 'en')
        os.environ['LC_ALL'] = 'ru_RU.UTF-8'
        self.assertEqual(self.i18n.get_language(), 'ru')
        Path(self.temp.name, 'language').write_text('en\n')
        self.assertEqual(self.i18n.get_language(), 'en')
        os.environ['SHM_LANG'] = 'ru'
        self.assertEqual(self.i18n.get_language(), 'ru')
        os.environ['SHM_LANG'] = 'unknown'
        self.assertEqual(self.i18n.get_language(), 'en')

    def test_live_switch_preserves_selection_and_translates_metadata(self):
        folder = Path(self.temp.name, 'plugins', 'demo')
        folder.mkdir(parents=True)
        (folder / 'plugin.conf').write_text('name=Fallback\nname.en=English\nname.ru=Русский\nentry=main.sh\n')
        (folder / 'main.sh').write_text('exit 0\n')
        ui = self.tui.UI()
        self.assertEqual(ui.current()['name'], 'English')
        ui.handle('l')
        self.assertEqual(ui.current()['name'], 'Русский')
        self.assertEqual(ui.selected, 'demo')
        self.assertEqual(Path(self.temp.name, 'language').read_text(), 'ru\n')
        ui.handle('l')
        self.assertEqual(ui.current()['name'], 'English')
        output = []
        ui.write = output.append
        ui.size = lambda: (26, 120)
        ui.draw()
        self.assertIn('PLUGINS', output[0])
        self.assertNotIn('ПЛАГИНЫ', output[0])

    def test_catalog_covers_python_literals_and_bash_messages(self):
        import ast
        import re
        root = Path(__file__).resolve().parent.parent
        catalog = json.loads((root / 'translations.json').read_text())
        for node in ast.walk(ast.parse((root / 'tui.py').read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr':
                self.assertIn(node.args[0].value, catalog)
        paths = [root / p for p in ('shm-cli', 'install.sh', 'plugin-install.sh')]
        paths += list((root / 'plugins').glob('*/main.sh'))
        for path in paths:
            for key in re.findall(r"shm_t '([^']*)'", path.read_text()):
                self.assertIn(key, catalog, str(path))


if __name__ == '__main__':
    unittest.main()
