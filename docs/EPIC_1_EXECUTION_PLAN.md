# Epic 1: воспроизводимая разработка и настоящие тесты

**Статус:** done
**Дата начала:** 2026-08-23
**Связанный roadmap:** [ROADMAP.md](ROADMAP.md)
**Границы:** не обновлять production-зависимости и не менять бизнес-логику без
отдельного решения в Epic 2 и Epic 4.

## Результат выполнения

- Владелец подтвердил Python 3.12 и `uv`; решение зафиксировано в
  [ADR-0002](adr/0002-python-312-and-uv.md).
- Добавлены `pyproject.toml`, `uv.lock`, отдельная dev dependency group и
  compatibility export `requirements.txt`. Direct runtime pins не менялись.
- `uv sync --all-groups`, `uv lock --check` и `uv run pip check` проходят на
  чистой project-local `.venv` с Python 3.12.8.
- Тесты перенесены в `tests/`: 9 pytest tests проходят; новая проверка вызывает
  production `TokenService` и formatter-функции, а не копии их реализации.
- Credentials исключены из Pydantic `Settings.__repr__`, чтобы ошибка теста не
  могла вывести Telegram/Infura значения в traceback.
- Ruff и pre-commit проходят; mypy initial scope (`akitafolio/models.py` и
  `tests`) проходит. Полный mypy run выявил 68 legacy errors за пределами
  scope; они сохранены как последующая техническая работа, без global ignore.
- Baseline coverage — 22.73%; введён минимальный gate 20%. Workflow GitHub
  Actions и actionlint проходят; `origin` переведён на canonical SSH URL.

## Собранный контекст

- Локальная среда: Python 3.12.8, `uv` 0.11.32 и Poetry 2.2.1 доступны.
- Production runtime: Python 3.12.3 на отдельном Timeweb VPS.
- В коде используется синтаксис не ниже Python 3.10 (`int | None`); текущая
  документация ошибочно обещает Python 3.8+.
- В репозитории нет `pyproject.toml`, lock-файла, CI workflow, pytest config или
  coverage config. Есть только `requirements.txt` с direct pins.
- Доступны два файла тестов. `test_logging_redaction.py` — 4 настоящих
  `unittest`-теста. `test_portfolio_message.py` содержит функции pytest-style,
  но одновременно дублирует production formatter и не вызывает `TokenService`;
  `unittest discover` поэтому не исполняет его.
- Отсутствуют: `pytest`, `pytest-asyncio`, `pytest-cov`, Ruff, mypy/pyright,
  coverage, pre-commit, Bandit и pip-audit. Их не устанавливать до решения
  владельца.
- Git remote принял push, но сообщил о новом canonical URL
  `https://github.com/f7one/akitafolio_portfolio_-tracker.git`; URL нужно
  перепроверить и заменить только после подтверждения владельца.

## Цели и критерии приёмки

1. Одна объявленная Python baseline совместима с local и production runtime.
2. Чистый checkout воспроизводимо устанавливает runtime и dev-зависимости через
   один выбранный инструмент и lock-файл.
3. Тестовый runner находит и запускает все тесты; тесты вызывают production-код,
   а не его копии.
4. Линтинг, типы, тесты и минимальное покрытие запускаются одинаково локально и
   в CI.
5. Epic завершается полным regression-прогоном; dependency security upgrades и
   бизнес-correctness остаются задачами следующих эпиков.

## План задач

### E1-T0 — подтвердить решения и подключить toolchain

**Предложение:** выбрать Python 3.12 (допустимый диапазон `>=3.12,<3.13`) и
`uv` как единственный менеджер зависимостей: обе production/local версии уже
совместимы, а `uv` установлен. Poetry не использовать параллельно.

Запросить отдельное разрешение на установку только dev-инструментов:

- `pytest`, `pytest-asyncio`, `pytest-cov`;
- `ruff`;
- `mypy` (или pyright — выбрать один; рекомендация: mypy);
- `pre-commit`.

`pip-audit`, Bandit и Semgrep не входят в bootstrap Epic 1: это отдельный
security scan Epic 2, для которого потребуется тот же явный доступ.

**Готово, когда:** владелец подтвердил baseline, package manager и разрешил
toolchain; версии зафиксированы в plan/ADR только после подтверждения.

### E1-T1 — создать проектный manifest и lock

1. Добавить `pyproject.toml` с project metadata, `requires-python`, runtime
   зависимостями из текущего `requirements.txt` и отдельной dev dependency group.
2. Добавить настройки pytest, Ruff, mypy и coverage в этом же файле; не плодить
   конфигурационные файлы без необходимости.
3. Сгенерировать `uv.lock`; оставить `requirements.txt` только как совместимый
   экспорт или удалить его после согласования единственного source of truth.
4. Проверить повторяемость: удалить временное venv, выполнить sync из lock и
   убедиться, что `pip check` проходит.

**Не делать:** обновление версий runtime-пакетов, подмена `web3`/`aiohttp` или
изменение production dependency strategy — это Epic 2 после compatibility tests.

### E1-T2 — заменить ложные тесты настоящими

1. Перенести тесты в `tests/` и привести к pytest discovery.
2. Заменить копии `format_portfolio_message` и `format_tokens_message` в
   `test_portfolio_message.py` вызовами реальных handler/formatter функций.
3. Покрыть `TokenService` через mocked HTTP/Web3 boundary: dust filtering,
   aggregation и ошибки upstream без реальных RPC calls.
4. Сохранить logging-redaction regression tests, адаптировав их к pytest без
   уменьшения сценариев.
5. Добавить async tests для handler/service boundary через `pytest-asyncio`.

**Готово, когда:** `pytest` обнаруживает все тесты, а искусственно внесённое
расхождение formatter-а с production-кодом делает тест красным.

### E1-T3 — качество и покрытие

1. Настроить Ruff lint/format для существующего стиля; сначала устранить только
   детерминированные нарушения без масштабного рефакторинга.
2. Настроить mypy только на package и постепенно расширять строгие правила;
   не скрывать реальные проблемы blanket `ignore_missing_imports`.
3. Ввести coverage по `akitafolio/` с начальным threshold, выбранным после
   baseline run. Не назначать произвольный процент до измерения.
4. Добавить pre-commit hooks для Ruff и fast tests; hooks не должны обращаться
   к Telegram/Infura или читать `.env`.

**Готово, когда:** все команды работают на чистой environment и дают
actionable diagnostics.

### E1-T4 — CI и repository hygiene

1. Добавить GitHub Actions workflow на Python 3.12: locked sync, Ruff, mypy,
   pytest с coverage и `pip check`.
2. Прогнать `actionlint` (уже установлен локально) и локально воспроизвести CI.
3. Проверить, что CI не получает secrets, не делает RPC calls и запускается на
   pull request/push.
4. После подтверждения владельца обновить `origin` на canonical GitHub URL и
   проверить fetch/push. До этого remote не менять.

### E1-T5 — документация и закрытие эпика

1. Синхронизировать README и DEVELOPMENT: Python 3.12, `bot.py`, `uv` workflow,
   test/lint/type/CI команды.
2. Добавить ADR о Python baseline и package-manager только после подтверждения
   решений E1-T0.
3. Выполнить полный test/lint/type/coverage/CI regression; обновить roadmap и
   этот план фактическими результатами.
4. Представить diff владельцу, затем создать отдельный commit Epic 1.

## Порядок выполнения и зависимости

`E1-T0 → E1-T1 → E1-T2 → E1-T3 → E1-T4 → E1-T5`.

Нельзя переходить к E1-T1, пока отсутствует разрешение на toolchain; нельзя
создавать ADR до выбора baseline/package manager; нельзя закрывать Epic без
полного test/lint/type/CI прогона.

## Зафиксированные последующие действия

1. Расширять mypy scope по модулям и исправлять 68 обнаруженных legacy errors,
   не добавляя blanket suppressions.
2. Повышать coverage выше initial 20% вместе с contract/integration tests.
3. Dependency security upgrades и полный SAST/SCA остаются в Epic 2.
