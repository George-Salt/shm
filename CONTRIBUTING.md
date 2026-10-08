# Contributing / Участие в разработке

## English

Open an issue for bugs or proposed changes. Include your Linux distribution, Bash/Python versions, terminal, reproduction steps, and expected/actual behavior. Remove private data from logs.

For a contribution, fork the repository, create a focused branch, make the change, and run `bash tests/smoke.sh`. Manually verify affected terminal behavior; hardware plugins need testing on the relevant hardware. Update both README translations and both plugin guides when behavior changes. Submit a pull request describing the problem, implementation, and validation. Keep scripts user-local where possible and preserve explicit confirmation for destructive operations. Be respectful and constructive in discussions.

## Русский

Для сообщения об ошибке или предложения создайте issue. Укажите дистрибутив Linux, версии Bash/Python, терминал, шаги воспроизведения, ожидаемый и фактический результат. Удалите приватные сведения из журналов.

Для изменения создайте fork и отдельную ветку, внесите правки и выполните `bash tests/smoke.sh`. Проверьте затронутое поведение терминала вручную; аппаратным плагинам нужна проверка на соответствующем оборудовании. При изменении поведения обновите обе версии README и руководства по плагинам. В pull request опишите проблему, решение и проверки. По возможности используйте каталоги пользователя и сохраняйте явное подтверждение удаления данных. Общайтесь уважительно и конструктивно.
