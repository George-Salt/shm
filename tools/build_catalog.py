#!/usr/bin/env python3
"""Regenerate the Bash translation table from translations.json."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
catalog = json.loads((root / 'translations.json').read_text(encoding='utf-8'))
path = root / 'i18n.sh'
source = path.read_text(encoding='utf-8')
start = source.index('declare -A SHM_EN=(')
end = source.index('\nshm_t()', start)

def quote(text):
    return "'" + text.replace("'", "'\\''") + "'"

table = 'declare -A SHM_EN=(\n' + ''.join(
    '  [' + quote(key) + ']=' + quote(value) + '\n' for key, value in catalog.items()
) + ')\n'
path.write_text(source[:start] + table + source[end:], encoding='utf-8')
