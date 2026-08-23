# Akitafolio engineering roadmap

Этот файл — единый master plan для работ по результатам code review. Статусы
обновляются по мере выполнения; коммиты и переход к следующему эпику делаются
только после ревью владельца.

**Последнее обновление:** 2026-08-23. Epic 0 выполняется на
`72.56.120.66` (Timeweb Cloud). Cutover принят владельцем: новый service
запущен, прежний остановлен. Удаление старой установки отложено на rollback
window. Подробный порядок работ,
точки контроля и rollback описаны в [плане исполнения](EPIC_0_EXECUTION_PLAN.md).

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

**Статус:** blocked

- [ ] Выбрать единую production baseline Python (предложение: 3.11 или 3.12).
- [ ] Добавить `pyproject.toml`, dev-зависимости и воспроизводимый lock-файл.
- [ ] Подключить `pytest`, `pytest-asyncio`, coverage, Ruff и type checker.
- [ ] Переписать тесты так, чтобы они вызывали production-код, и исправить
  обнаружение тестов (`unittest discover` сейчас находит 0 тестов).
- [ ] Добавить CI: syntax, lint, types, unit/integration tests и coverage gate.

**Блокер:** в текущем окружении отсутствуют pytest, Ruff и mypy/pyright; установка
не выполняется без разрешения владельца.

## Epic 2 — P1 security и correctness

**Статус:** blocked by Epic 1

- [ ] Обновить уязвимые зависимости с compatibility tests: web3, aiohttp,
  requests, python-dotenv, hdwallet и click.
- [ ] Отключить или безопасно ограничить web3 CCIP Read для пользовательских
  контрактов; протестировать SSRF-сценарии.
- [ ] Исправить decimals и дедупликацию custom ERC20 tokens.
- [ ] Ввести per-user rate limits, квоты адресов/xpub/token и общий предел RPC
  concurrency; вынести синхронные Web3-вызовы из event loop.
- [ ] Перестать превращать ошибки upstream API в нулевые балансы и не записывать
  такие результаты в историю.
- [ ] Исправить фильтрацию секретов во всех логгерах и ограничить размер HTTP
  ответа/`Retry-After`.

**Блокер:** для полного SAST/SCA отсутствуют `bandit`, `semgrep`, `pip-audit` или
подключённый Codex Security plugin.

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
