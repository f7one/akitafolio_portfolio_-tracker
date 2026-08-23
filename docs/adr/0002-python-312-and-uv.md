# ADR-0002: Python 3.12 и uv для разработки

- **Статус:** accepted
- **Дата:** 2026-08-23
- **Владелец решения:** project owner

## Контекст

Код использует синтаксис Python 3.10+, тогда как прежняя документация обещала
Python 3.8+. Production VPS работает на Python 3.12.3, локальная среда — на
Python 3.12.8. В репозитории не было project manifest, lock-файла или единого
способа установить runtime и dev-зависимости. Локально доступны и `uv`, и Poetry.

## Решение

1. Зафиксировать поддержку Python в диапазоне `>=3.12,<3.13`.
2. Использовать `uv` как единственный package manager для development и CI.
3. Хранить runtime и dev dependency groups в `pyproject.toml`, а полную
   разрешённую граф-зависимостей — в `uv.lock`.
4. `requirements.txt` экспортируется из lock как compatibility artifact для
   legacy/pip workflows; source of truth — `pyproject.toml` и `uv.lock`.

## Последствия

- Local и production runtime используют одну Python baseline.
- Чистый checkout воспроизводимо собирается командой `uv sync --all-groups`.
- Обновление пакетов требует изменения manifest/lock и проверки CI.
- Версии direct runtime-зависимостей не обновляются этим ADR; их security и
  compatibility work остаётся Epic 2.

## Рассмотренные альтернативы

### Сохранить Python 3.8+

Отклонено: это противоречит используемому синтаксису и текущему production runtime.

### Использовать Poetry

Работоспособный вариант, но `uv` уже установлен, быстрее создаёт locked environment
и позволяет не поддерживать два package-manager workflow. Отклонено.
