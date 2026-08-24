# Epic 2 — security и correctness: план исполнения

**Статус:** done
**Дата:** 2026-08-24
**Границы:** P1 security/correctness. Не включает production deployment, удаление
старой установки и задачи Epic 3+.

## Исходные данные

- Epic 0 завершил изолированный production cutover, а Epic 1 добавил Python 3.12,
  `uv`, lockfile и базовый CI. Ветка Epic 1 отправлена в canonical GitHub remote.
- Toolchain добавлен: `pip-audit 2.10.1` и Bandit 1.9.4 — project-local через
  `uv`; Gitleaks 8.30.1 — локальный binary для directory scan. Semgrep и OSV
  Scanner не нужны для минимального гейта и не устанавливались.
- Владелец решил оставить текущие Telegram/Infura credentials. Это принятый
  residual risk после прежнего локального traceback; значения не записываются в
  репозиторий, документацию или логи.

## Критерии приёмки Epic 2

- Актуальный SCA и SAST отчёты не содержат неразрешённых high/critical findings;
  исключения имеют owner, обоснование и срок пересмотра.
- Уязвимые зависимости обновлены только после compatibility/regression tests и
  зафиксированы в `uv.lock`.
- Пользовательские контракты не могут инициировать произвольные сетевые запросы
  через CCIP Read; негативный SSRF test проходит.
- Дубли custom ERC20 не создают повторный баланс; значение `decimals` берётся из
  контракта или запрос отклоняется, а не молча предполагает 18.
- Ошибки RPC/API видны пользователю и в telemetry без секретов; они не сохраняют
  фальшивой нулевой snapshot.
- Команды не блокируют event loop и ограничены согласованными per-user квотами,
  конкурентностью и timeout-ами.
- Пройдены full test/lint/type/SAST/SCA/secret-scan прогоны; diff проверен
  владельцем перед единым commit Epic 2.

## Задачи

### E2-T0 — восстановить security baseline и включить проверяемый toolchain

1. Владелец оставляет текущие Telegram и Infura credentials, осознавая residual
   risk от предыдущего локального traceback. Ротация остаётся рекомендуемым
   follow-up при первом плановом обслуживании; значения не передаются в чат.
2. После явного разрешения добавить в отдельную `security` dependency group
   `pip-audit` и Bandit, закрепить lockfile и их запуск в CI. Предпочтительный
   минимальный набор — именно эти два пакета: они покрывают dependency audit и
   Python SAST без избыточной платформы.
3. Отдельно решить, нужен ли secret scanning: добавить Gitleaks **или** подключить
   уже управляемый организацией equivalent. Semgrep и Codex Security plugin —
   альтернативы/дополнение, но не обязательны для первого минимального гейта.
4. Сохранить baseline reports без секретов; подтверждённые false positive оформить
   узкими правилами, не blanket-ignore.

**Результат:** выполнено. Toolchain добавлен и запущен локально; `pip-audit` и
Bandit включены в CI. Gitleaks directory scan исключает только локальный ignored
`.env` через узкое path-правило и должен запускаться перед release/commit.

### E2-T1 — dependency remediation с compatibility tests

1. Снять SCA baseline по lockfile и сопоставить каждую advisory с фактическим
   использованием в приложении.
2. Для каждого пакета поднимать версию отдельным тестируемым шагом: сначала
   `python-dotenv`, `click`, `requests`/`aiohttp`, затем `hdwallet`, последним —
   `web3` с совместимыми `eth-*` пакетами. Не выполнять массовый `uv lock --upgrade`.
3. До и после каждого обновления запускать `uv run pip check`, unit tests,
   lint/type checks и targeted tests для затронутого integration boundary.
4. Для `web3` создать mocked provider/contract tests: native balance, ERC20
   `balanceOf`, ошибка RPC, отключённый CCIP Read. Реальный Infura не использовать
   в CI.

**Готово, когда:** advisory закрыта обновлением либо документированно доказана
неприменимость с датой пересмотра; lockfile воспроизводим и тесты зелёные.

### E2-T2 — устранить CCIP Read SSRF

1. Проверить API выбранной версии `web3` и явно отключить CCIP Read для всех
   клиентских запросов пользовательских адресов/контрактов, если feature не
   требуется продукту.
2. Добавить provider regression test: CCIP Read отключён на каждом Web3 client;
   пользовательские contract calls не включают его повторно. Отдельный
   `OffchainLookup` integration test с private/link-local URL требует локального
   test RPC и переносится в Epic 4 sandbox integration tests.
3. Если CCIP Read нужен продукту, вместо отключения спроектировать allowlist
   схем/хостов и отдельный bounded HTTP transport; это требует нового решения
   владельца и ADR до реализации.

### E2-T3 — корректность custom ERC20

1. В `/add_token` валидировать сеть и контракт, читать `decimals()` и `symbol()`
   через bounded Web3 boundary; не использовать default `18` как факт.
2. Нормализовать ключ дедупликации как `(chain, checksum_address)` и применить его
   как при добавлении, так и при загрузке ранее сохранённых записей.
3. Существующие дубликаты идемпотентно отбрасываются при чтении без изменения
   пользовательского JSON; отдельная persistent migration требует backup/rollback
   и переносится в Epic 3.
4. Добавить tests: 6/8/18 decimals, mixed-case адреса, дубликат после перезапуска,
   ошибка контракта и legacy запись.

### E2-T4 — защита от перегрузки и блокирования event loop

1. До реализации согласовать с владельцем численные policy: запросов на
   пользователя/минуту, максимум адресов, xpub и custom tokens, глобальная
   RPC-concurrency и response deadline. Это продуктовые лимиты; их нельзя
   выдумывать.
2. Реализовать один переиспользуемый limiter на command boundary, квоты хранения и
   bounded shared semaphore для RPC.
3. Вынести синхронные вызовы Web3 в `asyncio.to_thread` или перейти на
   проверенный async provider после dependency compatibility tests.
4. Проверить concurrency tests: один пользователь не монополизирует worker,
   второй получает предсказуемый результат; timeout/cancellation не оставляют
   зависших задач.

**Решение:** применены консервативные public-bot defaults: 6 дорогих запросов
в минуту на пользователя с burst 2 и single-flight, до 5 ETH-адресов, 10 BTC,
2 xpub, 10 custom tokens и 8 одновременных RPC. Все значения конфигурируются
через `AKITAFOLIO_*` settings.

### E2-T5 — не подменять upstream failures нулевыми данными

1. Разделить «нулевой подтверждённый баланс» и «баланс неизвестен из-за ошибки» в
   result model/service boundary.
2. Агрегатор сохраняет snapshot только когда входные данные достаточно полны;
   при частичной ошибке показывает понятный статус и не искажает 24h history.
3. Добавить regression tests для timeout, HTTP 429/5xx, invalid JSON и RPC error.

### E2-T6 — безопасные HTTP и логи

1. Провести вызов-за-вызовом audit всех loggers: не логировать URL query,
   authorization headers, body или exception text, если они могут содержать
   секрет; сохранить полезные redacted context fields.
2. В `HTTPClient` ограничить читаемый размер тела, обрабатывать oversized ответ
   как controlled error и ограничить `Retry-After` верхней границей.
3. Добавить tests на redaction, oversized body, malformed/negative/huge
   `Retry-After` и 429 retry.

### E2-T7 — приемка, ADR и commit

1. Запустить: locked sync, `pip check`, Ruff, mypy, pytest с coverage, SCA, Bandit,
   secret scan, actionlint и targeted security/concurrency tests.
2. Обновить `ROADMAP.md`, этот план и краткие development/security instructions.
3. Создать ADR только для выбранной policy CCIP Read и лимитов, если между
   альтернативами было реальное решение. Не создавать ADR ради факта работ.
4. Выполнено: ADR-0003 фиксирует выбранную policy CCIP Read/лимитов; итоговый
   diff, результаты и commit представлены владельцу. Переход к Epic 3 не входит
   в эту задачу.

## Порядок и границы ответственности

`E2-T0 → E2-T1 → E2-T2 → E2-T3 → E2-T4 → E2-T5 → E2-T6 → E2-T7`.

`E2-T3`, `E2-T5` и `E2-T6` могут готовиться параллельно после E2-T1, но их
acceptance объединяется в E2-T7. Production service не перезапускается, secrets
не печатаются и не коммитятся. Старый VPS и сайт на shared VPS не входят в scope.

## Принятое SCA-исключение

`PYSEC-2026-1325` (`ecdsa 0.19.2`, CVE-2024-23342) остаётся транзитивной
зависимостью `hdwallet 3.6.1`; для неё нет исправленной версии. Риск связан с
timing-атаками при создании/подписании private EC key. Бот принимает только
публичные xpub и не создаёт и не подписывает ключи, поэтому это не достигаемая
поверхность текущей функциональности. `pip-audit` игнорирует исключительно этот
ID в CI; исключение пересмотреть при каждом обновлении `hdwallet` либо не позднее
2026-09-24.

## Фактический результат

- E2-T0: добавлены `pip-audit 2.10.1`, Bandit 1.9.4, Gitleaks 8.30.1; первые
  два запускаются в CI, Gitleaks directory scan прошёл локально.
- E2-T1: обновлены `aiohttp 3.14.3`, `click 8.4.2`, `hdwallet 3.6.1`,
  `python-dotenv 1.2.3`, `requests 2.34.2`, `web3 7.16.0`, pytest и
  pytest-asyncio. Исправлена несовместимость hdwallet v3 constructor.
- E2-T2—E2-T6: CCIP Read выключен, custom ERC20 получает metadata из контракта
  и дедуплицируется, blocking RPC ограничены, HTTP body/Retry-After ограничены,
  incomplete portfolio не сохраняется как snapshot.
- E2-T7: `uv sync --locked --all-groups`, `pip check`, Ruff, mypy, pytest
  (18 passed, coverage 27.00%), `pip-audit` с одним документированным исключением,
  Bandit, Gitleaks, actionlint и pre-commit прошли. В `websockets` остаётся
  предупреждение deprecation, не failure.
