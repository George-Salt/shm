# Plugin authoring

[Русская версия](plugins.ru.md) · [README](../README.md)

## Layout

```text
hello/
├── plugin.conf
└── main.sh
```

The directory name is the plugin ID. It must start with an ASCII letter or digit and contain only ASCII letters, digits, underscores, or hyphens. Scanners skip symlinked plugin directories, configuration files, and entry scripts.

## Metadata

```ini
name=Hello
description=Print a greeting
author=Your name
category=Examples
entry=main.sh
```

The supported keys are `name`, `description`, `author`, `category`, and `entry`. Write literal `key=value` lines, without shell quotes or spaces around the key. Metadata is parsed as text, not sourced as shell code. Avoid duplicate keys. Missing `entry` defaults to `main.sh`; the remaining fields are display metadata.

The entry must be a filename ending in `.sh`, start with an ASCII letter or digit, and contain only letters, digits, underscores, hyphens, or periods. It cannot contain `..` or a directory separator.

## Minimal working example

```bash
mkdir -p hello
cat > hello/plugin.conf <<'CONF'
name=Hello
description=Print a greeting
author=Your name
category=Examples
entry=main.sh
CONF
cat > hello/main.sh <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
printf 'Hello, %s!\n' "${1:-world}"
SCRIPT
bash "${SHM_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/shm}/plugin-install.sh" ./hello
shm run hello Linux
```

The installer copies the entire plugin directory, validates configuration and entry files, and requests confirmation before replacing an existing plugin. Installation does not prove the script is safe. Do not include secrets or unnecessary files.

## Execution contract

SHM invokes the entry with Bash. CLI arguments are forwarded unchanged. Do not rely on the working directory being the plugin directory: derive resource paths from `${BASH_SOURCE[0]}`. Return zero on success and a nonzero exit status on failure. Check required external commands before use and confirm destructive actions explicitly.

The fullscreen runner provides a PTY, but its output view is not a general terminal emulator. Use line-oriented output and prompts; test programs requiring cursor positioning or their own fullscreen UI with `shm run <id>`.
