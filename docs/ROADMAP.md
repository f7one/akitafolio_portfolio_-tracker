# Akitafolio engineering roadmap

Этот файл — единый master plan для работ по результатам code review. Статусы
обновляются по мере выполнения; коммиты и переход к следующему эпику делаются
только после ревью владельца.

**Последнее обновление:** 2026-08-24. Epic 0 завершён; Epic 1 отправлен в
canonical GitHub-репозиторий. Epic 2 начат с инвентаризации security toolchain
и зависимостей. Подробный порядок работ, точки контроля и решения, требующие
подтверждения владельца, — в [плане Epic 2](EPIC_2_EXECUTION_PLAN.md).

Статусы: `planned`, `in progress`, `blocked`, `done`.

## Epic 0 — изоляция production и перенос на отдельный VPS

**Статус:** done (decommissioning deferred)
**Приоритет:** P0
**Решение:** [ADR-0001](adr/0001-separate-production-vps.md)

### Задачи

- [x] **E0-T1. Перенести production на отдельный VPS.** Target
  `72.56.120.66` (Timeweb Cloud) подготовлен: прежний Outline VPN и Docker
  удалены, новый service работает отдельно от сайта.
- [x] **E0-T2. Настроить административный доступ.** Сохранить root SSH по
  отдельному ключу и паролю (`PermitRootLogin yes`, `PasswordAuthentication
  yes`), но отключить keyboard-interactive и пустые пароли. Использовать
  уникальный сгенерированный пароль, ограничить brute force через firewall и
  fail2ban, уменьшить число попыток входа. Создать отдельного key-only оператора
  без групп `sudo`/`docker`; при необходимости выдать только точечные команды
  для сервиса бота.
- [x] **E0-T3. Подготовить runtime.** Запускать systemd-сервис от
  непривилегированного пользователя `akitafolio`, не от root и не в Docker.
  Выделить отдельные каталоги приложения, конфигурации и данных; включить
  systemd hardening и ограничения ресурсов. Хранить environment-файл отдельно
  от кода с владельцем `root:root` и mode `0600`; systemd читает его до смены
  пользователя сервиса.
- [x] **E0-T4. Закрыть утечки секретов до первого запуска.** Logging patch с
  4 regression-тестами развернут; новые Telegram и Infura credentials хранятся
  только в root-owned EnvironmentFile. Telegram API подтвердил новый token.
- [x] **E0-T5. Сохранить production-данные.** После остановки старого service
  оба JSON перенесены повторно; SHA-256 исходников и target совпадают, JSON
  валиден и недоступен оператору/посторонним пользователям.
- [x] **E0-T6. Выполнить cutover.** Новый service enabled и active; прежний
  `tg-balance-bot.service` на shared VPS stopped и disabled. Старая установка
  сохранена только для согласованного rollback.
- [x] **E0-T7. Провести полное тестирование эпика.** Пройдены service, unit,
  UFW/fail2ban, права, integrity, API, redaction и ручной Telegram smoke-test.
  BSC Infura RPC отвечает HTTP 200; владелец подтвердил смену root-пароля.
- [ ] **E0-T8. Закрыть старую установку — отложено.** Прежний service stopped и
  disabled, а файлы на VPS `194.87.83.103` сохраняются в rollback window. Для
  удаления старых секретов и данных нужно отдельное подтверждение владельца;
  сайт, Caddy, Docker Compose и CI/CD пользователя `deployer` не затрагивать.

### Критерии приёмки

- Root доступен по SSH-ключу и паролю; keyboard-interactive и пустые пароли
  отключены, brute-force protection включена и проверена без блокировки
  административного доступа.
- У бота нет входящих публичных портов; разрешены только необходимые исходящие
  DNS/HTTPS/RPC-соединения.
- Процесс работает от `akitafolio`; `.env` и JSON-файлы недоступны другим
  пользователям.
- Контрольные суммы обоих JSON-файлов совпадают; владелец подтвердил Telegram
  smoke-test с перенесёнными данными.
- Одновременно работает только один polling-процесс.
- Новые секреты отсутствуют в Git, deployment-архивах, shell history и
  `journalctl`.
- Пройдены smoke, negative и rollback tests; результат подтверждён владельцем.

## Epic 1 — воспроизводимая разработка и настоящие тесты

**Статус:** done
**План исполнения:** [EPIC_1_EXECUTION_PLAN.md](EPIC_1_EXECUTION_PLAN.md)

- [x] Зафиксировать production baseline Python 3.12 и `uv` в ADR-0002.
- [x] Добавить `pyproject.toml`, dev dependency group, `uv.lock` и экспорт
  `requirements.txt` из lock.
- [x] Подключить pytest, pytest-asyncio, pytest-cov, Ruff, mypy и pre-commit
  project-local через `uv`.
- [x] Переписать тесты: pytest находит 9 тестов, вызывающих production
  formatter/service code; дубли formatter-логики удалены.
- [x] Добавить GitHub Actions: locked sync, `pip check`, Ruff, mypy и pytest с
  coverage gate 20%; workflow проверен локальным actionlint.

**Остаточный риск:** full mypy baseline обнаруживает legacy errors вне текущего
initial scope (`akitafolio/models.py` и `tests`); расширение type coverage и
исправление этих ошибок выполняются последовательно в следующих технических
задачах, без blanket ignore.

## Epic 2 — P1 security и correctness

**Статус:** done
**План исполнения:** [EPIC_2_EXECUTION_PLAN.md](EPIC_2_EXECUTION_PLAN.md)
**Решение:** [ADR-0003](adr/0003-public-bot-safety-limits-and-no-ccip.md)

- [x] Провести read-only инвентаризацию и добавить SCA/SAST baseline: project-local
  `pip-audit`/Bandit и локальный Gitleaks; Semgrep/OSV Scanner не требуются для
  минимального гейта. Текущие credentials оставлены владельцем как residual risk.
- [x] E2-T1. Обновить уязвимые зависимости с compatibility tests: web3, aiohttp,
  requests, python-dotenv, hdwallet и click.
- [x] E2-T2. Отключить CCIP Read для пользовательских
  контрактов; протестировать SSRF-сценарии.
- [x] E2-T3. Исправить decimals и дедупликацию custom ERC20 tokens.
- [x] E2-T4. Ввести per-user rate limits, квоты адресов/xpub/token и общий предел
  RPC concurrency; вынести синхронные Web3-вызовы из event loop.
- [x] E2-T5. Перестать превращать ошибки upstream API в нулевые балансы и не
  записывать такие результаты в историю.
- [x] E2-T6. Исправить фильтрацию секретов во всех логгерах и ограничить размер
  HTTP-ответа/`Retry-After`.
- [x] E2-T7. Провести полные SAST/SCA/regression tests, обновить документацию и
  представить единый diff на ревью перед commit.

**Остаточный риск:** `pip-audit` показывает только документированное исключение
`PYSEC-2026-1325` в транзитивном `ecdsa`, для которого нет patch; оно принято
только потому, что бот не создаёт и не подписывает private EC keys. Текущие
Telegram/Infura credentials владелец решил не ротировать после локального
traceback. Оба риска имеют owner и срок пересмотра в плане Epic 2.

## Epic 3 — целостность хранения и эксплуатационная устойчивость

**Статус:** planned

- [ ] Устранить межпроцессные read-modify-write гонки bot/CLI: выбрать file lock
  или SQLite после нагрузочного теста.
- [ ] Зафиксировать приватные права создаваемых файлов и атомарное восстановление.
- [ ] Ограничить CLI: локальный пользователь не должен читать произвольный
  Telegram `user_id`.
- [ ] Исправить xpub validation, query construction и bounds для внешних API.
- [ ] Добавить backup/restore и recovery tests без включения секретов в архив.

## Epic 4 — корректность портфеля и blockchain-интеграций

**Статус:** planned

- [ ] Исправить xpub gap-limit scanning и добавить тестовые векторы.
- [ ] Заменить фиктивный расчёт 24h change на корректную модель snapshots.
- [ ] Исправить native assets и актуальные symbols сетей, включая BNB/POL.
- [ ] Валидировать CoinGecko ID и экранировать Telegram Markdown.
- [ ] Добавить contract/integration tests для Telegram, Infura и внешних API в
  sandbox-окружении.

## Epic 5 — документация и безопасный deployment

**Статус:** planned

- [ ] Удалить ссылки на отсутствующий `bot_refactored.py`; зафиксировать реальный
  entry point `bot.py` и выбранную версию Python.
- [ ] Заменить текущий `deploy.sh`: не архивировать `.env`, не использовать
  предсказуемый `/tmp`, не запускать сервис от root и не хранить IP в коде.
- [ ] Синхронизировать README, deployment, development guide и changelog с
  фактическим поведением.
- [ ] Провести полный regression/security test перед закрытием эпика.

## Порядок выполнения

1. Epic 0: отдельный production VPS и безопасный cutover.
2. Epic 1: тестовый и CI baseline.
3. Epic 2: P1 security/correctness.
4. Epic 3 и Epic 4: хранение, устойчивость и доменная корректность.
5. Epic 5: финализация deployment и документации.

После каждого эпика: полный тестовый прогон, security regression, обновление
этого roadmap и отдельное подтверждение владельца. Отложенный decommissioning
может выполняться только после rollback window и отдельного approval. ADR создаются только для
решений с реальными альтернативами и эксплуатационными последствиями.
