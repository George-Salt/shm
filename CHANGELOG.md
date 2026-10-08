# Changelog / История изменений

## 0.1.1 — 2026-10-08

- Add an explicit bilingual language selector before interactive installer prompts.
- Support `bash install.sh --lang en|ru` for scripted installation and save the selected language for the first application launch.
- Verify English installation under a Russian locale and Russian installation under an English locale through real PTYs.

Добавлен двуязычный выбор языка перед вопросами интерактивного установщика, параметр `--lang en|ru` и сохранение языка для первого запуска приложения. Проверяется установка на английском в русской локали и на русском в английской.

## 0.1.0 — 2026-10-08

- English and Russian localization for the TUI, CLI, installer, and bundled plugins.
- Persistent language selection with the `l` key, `shm lang`, and `SHM_LANG` overrides.
- Localized plugin metadata and `shm --version`.
- README badges, captured terminal screenshots, and installable release archives with checksums.
- Language resolution, live switching, and safe plugin localization checks.

Локализация интерфейса, CLI, установщика и встроенных плагинов; сохранение языка через `l` и `shm lang`, переменная SHM_LANG, двуязычные метаданные плагинов, версия приложения, бейджи и скриншоты README, архив релиза с контрольными суммами и проверки локализации.

## Initial repository preparation

- Initial public repository packaging for the existing SHM implementation.
- English and Russian documentation, plugin guides, and contribution/security policies.
- GitHub issue and pull request templates, MIT license, and automated smoke checks.

Первоначальное оформление существующей реализации для публичного репозитория: двуязычная документация, руководства по плагинам, правила участия и безопасности, шаблоны GitHub, лицензия MIT и автоматические проверки.
