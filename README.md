# SHM — Shell Script Manager

[Русская документация](README.ru.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

SHM is a lightweight terminal application for organizing, inspecting, running, and removing local Bash script plugins on Linux. It provides a fullscreen Python interface and a command-line interface. The application and bundled plugins currently display messages in Russian; documentation is available in English and Russian.

## Features

- Searchable plugin list with keyboard and mouse navigation.
- Plugin metadata, configurable script entry points, and argument forwarding through the CLI.
- Embedded execution view with a pseudo-terminal (PTY) for output and interactive prompts.
- Confirmation before plugin removal or replacement.
- User-local installation and configurable data directory.
- Standard-library-only Python implementation; no pip dependencies.

## Requirements

Linux, Bash 4.4 or newer, Python 3.8 or newer, and standard GNU utilities. The fullscreen interface requires an interactive terminal with ANSI escape sequence support and a UTF-8 locale. Git is needed only to clone the repository. Individual plugins may require additional tools.

## Installation

```bash
git clone https://github.com/George-Salt/shm.git
cd shm
bash install.sh
```

The launcher is installed to `~/.local/bin/shm`. Add this directory to your shell's PATH if necessary:

```bash
# Bash or Zsh: add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Fish
fish_add_path ~/.local/bin
```

Start a new shell, then run `shm`. The installer asks whether to install bundled plugins. Non-interactive installation skips them. Re-running the installer updates application files and leaves installed plugins in place, apart from a legacy migration that removes the old `alice` plugin when it matches the installer’s signature.

## Usage

```bash
shm                         # Open the fullscreen interface
shm list                    # List installed plugins
shm info cleanup            # Inspect metadata
shm run cleanup             # Run a plugin
shm run my-plugin arg1 arg2  # Forward arguments to its script
shm remove my-plugin        # Remove after confirmation
shm help                    # Show command help
```

`shm run` returns the plugin's exit status. Use the CLI for non-interactive terminals and scripts.

| Control | Action |
| --- | --- |
| Up / Down or k / j | Select a plugin |
| Page Up / Page Down, Home / End | Navigate the list |
| Enter | Run the selected plugin |
| / | Search; Enter applies, Esc cancels |
| d or Delete | Request removal with confirmation |
| r | Reload plugins |
| q or Esc | Exit |
| Mouse | Click to select, double-click to run, wheel to scroll |

The execution view forwards input to the running plugin. After completion, Enter, q, or Esc returns to the list. Programs requiring their own fullscreen terminal interface should be run through `shm run <id>`.

## Plugins

Plugins live in `<SHM_HOME>/plugins/<id>/`. Each directory contains `plugin.conf` and a Bash entry script (default: `main.sh`). Install a local plugin with:

```bash
bash "${SHM_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/shm}/plugin-install.sh" ./plugins/cleanup
```

See the [plugin authoring guide](docs/plugins.md) for the format and a minimal example. Plugins execute with your user's permissions and are not sandboxed. Review a script before installing or running it.

### Bundled plugins

| ID | Purpose | Dependencies |
| --- | --- | --- |
| cleanup | Clean package caches, user caches, trash, and old journal entries on Arch Linux and derivatives | GNU utilities; `sudo`, `paccache` from pacman-contrib; optional `gio` and `journalctl` |
| bluetooth-speaker | Pair/connect a Bluetooth device, select an audio output, and set volume to 30% | BlueZ `bluetoothctl`, PipeWire/WirePlumber `wpctl`; optional `pactl` for A2DP selection |

Cleanup requests confirmation before deleting data; package cache and journal operations use sudo. Bluetooth discovery lists known devices as well as discovered devices; users choose the intended audio device. Hardware and service configuration affect results.

## Configuration and appearance

| Variable | Meaning |
| --- | --- |
| SHM_HOME | Override application and plugin data location |
| XDG_DATA_HOME | Data base directory when SHM_HOME is unset; defaults to ~/.local/share |
| NO_COLOR | A nonempty value disables CLI color formatting |

Use the same environment settings during installation and execution. The launcher always installs to `~/.local/bin`. The default data location is `~/.local/share/shm`.

The interface uses the terminal's ANSI palette (ANSI 5 for accent) and default background. It does not change the terminal palette using OSC commands and does not use curses. NO_COLOR currently applies to the Bash CLI, not the fullscreen interface.

## Updating and uninstalling

Update the checkout with `git pull --ff-only`, then run `bash install.sh` again. Bundled plugin updates require opting in and confirming replacement.

To uninstall, remove `~/.local/bin/shm` and the SHM data directory. The data directory also contains installed plugins and their files: back up anything needed first. For custom installations, use the actual SHM_HOME location.

## Development

Run `bash tests/smoke.sh` for syntax checks and isolated installation/CLI checks. GitHub Actions runs the same checks on pushes and pull requests with Python 3.8 and 3.12. Interactive UI, audio hardware, and destructive cleanup actions require manual testing and are not exercised by CI.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CHANGELOG.md](CHANGELOG.md). SHM is distributed under the [MIT license](LICENSE).
