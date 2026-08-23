# Epic 0: план безопасного переноса production

**Статус:** done (P0.7 decommissioning deferred)
**Дата начала:** 2026-08-17
**Последнее изменение:** 2026-08-23 — владелец принял cutover и подтвердил
ручной Telegram smoke-test и смену root-пароля. Старый service stopped/disabled;
его удаление отложено на rollback window.
**ADR:** [ADR-0001](adr/0001-separate-production-vps.md)
**Старый VPS:** `194.87.83.103` — сайт и бот, не менять сайт
**Целевой VPS:** `72.56.120.66` — Timeweb Cloud; ранее использовался для Outline VPN

## Границы работ

- В scope: только Akitafolio, его systemd unit, данные и новые credentials.
- Вне scope: сайт, Caddy, Docker, `/opt/deploy-lab`, пользователь `deployer` и
  CI/CD на `194.87.83.103`.
- Не использовать `deploy.sh`, `/tmp`, Git или Docker-архивы для секретов и
  JSON-данных.
- Root SSH остаётся доступным по ключу и паролю — это принятое исключение из
  [ADR-0001](adr/0001-separate-production-vps.md).

## Текущее состояние

- Планирование Epic 0 завершено.
- P0.1 выполнен: на `72.56.120.66` обнаружены только Outline components
  (`shadowbox`, `watchtower`, `/opt/outline`), после подтверждённого inventory
  они удалены. Docker runtime, образы, данные и Docker apt-source удалены;
  Docker workloads отсутствуют. Zabbix сохранён как provider monitoring.
- P0.2 выполнен: создан отдельный passphrase-protected root key и
  `bot-operator` key; root key/password login проверены. UFW использует
  default deny incoming и rate-limited SSH, fail2ban sshd jail активен.
- P0.3 выполнен: Ubuntu обновлён, Python 3.12.3 и isolated venv установлены;
  service account `akitafolio`, root-owned EnvironmentFile и hardened
  `tg-balance-bot.service` готовы. Security exposure score: 2.4. Unit проходит
  `systemd-analyze verify`; service enabled и active.
- Локальная часть E0-T4 подготовлена и развернута: logging patch маскирует
  Telegram/Infura URLs, key-value credentials, wallet identifiers и exception
  text; 4 стандартных regression-теста проходят на Mac и target VPS.
- E0-T5 выполнена: после остановки старого service оба JSON перенесены напрямую;
  SHA-256 исходника и target совпадают, оба JSON валидны для service account.
  Содержимое не выводилось.
- Host fingerprint подтверждён через Timeweb Cloud console. Новый Telegram token
  проверен запросом `getMe` (HTTP 200); Ethereum, Polygon и BSC RPC отвечают
  HTTP 200 после включения BSC для текущего Project ID.
- На `194.87.83.103` service `tg-balance-bot` stopped и disabled. Сайт, Docker,
  Caddy и CI/CD не изменялись.
- Финальный acceptance-test подтверждён: новый service active/enabled, unit
  verification passed, systemd security score 2.4 (OK), `.env` и оба JSON имеют
  mode `0600`, а за последние 20 минут в journal не обнаружены Telegram/Infura
  credential patterns. Владелец подтвердил ручные `/start`, `/addresses` и
  `/portfolio`; BSC RPC возвращает HTTP 200.

## Последовательность и точки контроля

### P0.1 — read-only baseline целевого VPS (E0-T1)

**Цель:** подтвердить, что `72.56.120.66` подходит для отдельного бота и не
содержит неучтённой нагрузки.

1. Сверить ED25519 host-key fingerprint в provider console с тем, который видит
   SSH-клиент. Не удалять старую запись `known_hosts`, пока fingerprint не
   подтверждён независимым каналом.
2. Собрать без секретов: ОС, ядро, CPU/RAM/disk, uptime, открытые порты,
   активные systemd units, Docker/Compose workloads, пользователей,
   effective `sshd -T`, UFW и fail2ban status.
3. Инвентаризировать прежний Outline VPN: systemd units, Docker containers,
   volumes, firewall rules, пакеты и каталоги конфигурации. Не выводить access
   keys, certificates или содержимое конфигурации.
4. После отдельного подтверждения владельца остановить и удалить только
   идентифицированные Outline components, а затем повторить inventory и убедиться,
   что не затронуты другие workloads.
5. Проверить, что target не содержит сайта, Caddy, другого production-бота,
   чужих data volumes или служб, которым может навредить hardening.
6. Зафиксировать baseline в заметке выполнения Epic 0 без `.env`, ключей,
   `authorized_keys`, адресов и xpub.

**Стоп-условие:** обнаружена чужая/непонятная production-нагрузка, отсутствует
явное подтверждение удаления Outline, недостаточно ресурсов или host key не
подтверждён. В этом случае никаких изменений не делать.

**Критерий готовности:** Outline удалён только после подтверждения владельца,
baseline подтверждён, а владелец разрешает менять только целевой VPS.

### P0.2 — доступ и perimeter (E0-T2)

**Цель:** оставить управляемый root SSH и снизить риск password brute force.

1. Создать отдельный passphrase-protected root SSH key для этого VPS и добавить
   публичную часть через provider console. Проверить второй сеанс SSH до
   закрытия консоли.
2. Внести отдельный SSH drop-in после `sshd -t`:
   `PermitRootLogin yes`, `PasswordAuthentication yes`,
   `KbdInteractiveAuthentication no`, `PermitEmptyPasswords no`,
   ограниченное `MaxAuthTries` и `LoginGraceTime`.
3. Задать уникальный root-пароль через интерактивный `passwd root`; не передавать
   пароль как аргумент команды, в чат или history.
4. Настроить UFW: default deny incoming, разрешить SSH только из согласованных
   источников. Если IP владельца динамический, согласовать правило до включения,
   чтобы не потерять доступ.
5. Установить/включить fail2ban для SSH, настроить уведомляемый журнал и
   проверить, что один контролируемый неверный вход не блокирует основной ключ.
6. Создать отдельного `bot-operator` с отдельным key-only ключом. Не добавлять
   его в `sudo` или `docker`; если понадобятся действия, выдать sudoers rule
   только для конкретных `systemctl status/restart tg-balance-bot.service`.

**Стоп-условие:** SSH-конфигурация не проходит `sshd -t`, новый ключ не работает
или firewall блокирует проверенный административный доступ. Откатить только
последний drop-in/rule через открытую provider console.

**Критерий готовности:** root-вход ключом и паролем проверен, provider console
остаётся доступной, brute-force controls активны, неразрешённые входящие порты
закрыты.

### P0.3 — изолированный runtime (E0-T3)

**Цель:** подготовить non-root systemd runtime без Docker.

1. Установить обновления ОС и только нужные пакеты: Python выбранной baseline,
   `python3-venv`, Git, UFW и fail2ban. Зафиксировать фактические версии.
2. Создать системного пользователя `akitafolio` без shell login и каталоги:
   код — только для чтения service account, данные — writable только
   `akitafolio`, конфигурация — root-owned вне кода.
3. Подготовить unit `tg-balance-bot.service` с `User=akitafolio`,
   `EnvironmentFile=`, `UMask=0077`, restart policy, resource limits и
   systemd sandboxing (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`,
   `ProtectHome`, точечный `ReadWritePaths`).
4. Проверить unit через `systemd-analyze verify` и оценить его
   `systemd-analyze security` до запуска с production credentials.

**Стоп-условие:** sandboxing мешает Python, DNS, записи JSON или RPC. Ослаблять
только конкретную настройку после воспроизводимого теста, не переводить service
в root.

**Критерий готовности:** service может стартовать с тестовой конфигурацией,
писать только в data directory и не открывает входящие TCP/UDP-порты.

### P0.4 — исправление логирования и выпуск новых секретов (E0-T4)

**Цель:** не допустить повторной утечки Telegram token/Infura ID.

1. Подготовить локальный минимальный patch: HTTP-библиотеки не логируют URL на
   INFO, `SecretsFilter` применяется к root и дочерним logger'ам, маскирует
   значения в message и logging arguments.
2. Добавить regression tests, включая Telegram URL и Infura URL, и представить
   patch владельцу. Не переносить его на VPS и не выпускать новые secrets без
   отдельного code review.
3. После approval развернуть exact reviewed revision на target.
4. Выпустить новые Telegram token и Infura Project ID. Старые credentials не
   копировать и не использовать.
5. Поместить новые значения только в root-owned EnvironmentFile mode `0600` и
   проверить в journal redacted output, не публикуя сырые строки логов.

**Стоп-условие:** любая проверка показывает secret в stdout, journal, Git diff,
shell history или deployment artifact. Немедленно отозвать только что созданный
credential, очистить точку утечки и повторить выпуск.

**Критерий готовности:** тесты secret redaction проходят, новая конфигурация не
содержит старых credential, а `journalctl` не раскрывает URL или значения.

### P0.5 — консистентный перенос данных (E0-T5)

**Цель:** сохранить существующих пользователей и историю без утечки.

1. На старом VPS определить фактические пути `saved_addresses.json` и
   `portfolio_history.json`; проверить JSON синтаксис и доступное место на
   target, не печатая содержимое.
2. Остановить и disable старый `tg-balance-bot.service`; убедиться, что polling
   завершён и файлы больше не изменяются.
3. Создать локальную protected backup-копию, вычислить SHA-256 исходников и
   перенести каждый файл напрямую по проверенному SSH в data directory target.
4. На target установить владельца `akitafolio`, mode файлов `0600`, mode data
   directory `0700`; сверить SHA-256.
5. Хранить локальную backup-копию до окончания согласованного rollback window.

**Стоп-условие:** JSON невалиден, checksum не совпадает или на target недостаточно
места. Новый сервис не запускать; исходные файлы на старом VPS не изменять.

**Критерий готовности:** обе контрольные суммы совпадают; данные читаются service
account, но недоступны посторонним локальным пользователям.

### P0.6 — cutover и smoke tests (E0-T6, E0-T7)

**Цель:** запустить ровно один экземпляр бота и доказать работоспособность.

1. Зафиксировать revision, версии зависимостей и SHA-256 перенесённых данных в
   execution log без секретов.
2. Проверить старый сервис: `inactive` и `disabled`; затем запустить и enable
   новый service.
3. Проверить service status, процесс под `akitafolio`, отсутствие listen ports,
   permissions, systemd security score и отсутствие credentials в журнале.
4. Выполнить Telegram smoke tests с существующим тестовым пользователем:
   `/start`, `/addresses`, `/portfolio`, добавление и удаление тестовой записи
   с последующим откатом, запросы EVM/BTC/token/DeFi в пределах доступных API.
5. Выполнить negative tests: некорректный адрес, некорректный xpub, timeout
   внешнего API и повторный запрос. Проверить, что ошибка не превращается в
   нулевой snapshot и не раскрывает secrets.
6. Проверить SSH key и password, fail2ban/UFW, доступ `bot-operator`, backup и
   документированный rollback.

**Стоп-условие:** новый сервис логирует secret, повреждает данные, не отвечает
на базовые команды или появляется второй polling. Остановить новый service;
восстановить только проверенные данные и вернуться к rollback procedure.

**Критерий готовности:** все acceptance criteria Epic 0 из
[roadmap](ROADMAP.md) подтверждены, владелец принимает результат.

### P0.7 — окно отката и вывод старой установки (E0-T8)

**Цель:** удалить только устаревшую установку бота после стабильной эксплуатации.

1. Держать старый service stopped и disabled весь согласованный rollback window.
2. Проверять доступность, journal без secrets, использование API и целостность
данных нового VPS.
3. После явного approval владельца: revoke старые credentials, удалить только
`/opt/tg-balance-bot`, его unit, secrets и data на `194.87.83.103`.
4. Не менять Docker, Caddy, сайт, `/opt/deploy-lab`, `deployer` или его sudoers.
5. Обновить `ROADMAP.md`, ADR (если изменился итог) и deployment documentation;
провести полный regression/security test эпика.

**Стоп-условие:** нет явного approval владельца или rollback window не завершён.
Удаление не выполнять.

## Оставшиеся операционные решения

1. Согласовать длительность rollback window и отдельным approval разрешить удаление
   старой установки. До этого `/opt/tg-balance-bot` на shared VPS сохраняется,
   но service остаётся stopped и disabled.
2. До Epic 2 публичный запуск сохраняет остаточный риск отсутствия per-user
   quotas/rate limits; альтернативой является ограничение пользователей, которого
   текущая версия ещё не реализует.
