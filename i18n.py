"""Language selection and translations for SHM (no external dependencies)."""
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get('SHM_HOME', str(Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'shm')))
CATALOG = json.loads((Path(__file__).parent / 'translations.json').read_text(encoding='utf-8'))


def get_language():
    explicit = os.environ.get('SHM_LANG')
    if explicit:
        return explicit if explicit in ('ru', 'en') else 'en'
    try:
        saved = (ROOT / 'language').read_text(encoding='utf-8').strip()
        if saved in ('ru', 'en'):
            return saved
    except OSError:
        pass
    locale = os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG', 'en')
    return 'ru' if locale.lower().startswith('ru') else 'en'


def set_language(language):
    if language not in ('ru', 'en'):
        raise ValueError('Language must be ru or en')
    ROOT.mkdir(parents=True, exist_ok=True)
    temporary = ROOT / 'language.tmp'
    temporary.write_text(language + '\n', encoding='utf-8')
    temporary.replace(ROOT / 'language')
    os.environ['SHM_LANG'] = language


def tr(text):
    return CATALOG.get(text, text) if get_language() == 'en' else text
