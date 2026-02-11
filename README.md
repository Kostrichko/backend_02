# Асинхронная система обработки задач

Backend-сервис на FastAPI для приема и асинхронной обработки задач через RabbitMQ.

---

## Задача

Реализовать сервис, который:
- принимает задачи через `POST /tasks` с полем `payload`
- сохраняет в PostgreSQL и отправляет в очередь
- фоновым воркером обрабатывает задачи (имитация через sleep)
- обновляет статус: `pending` → `processing` → `done` / `failed`
- запускается через `docker compose up`

---

## Быстрый старт

```bash
docker compose up
```

API: http://localhost:8000/docs
RabbitMQ UI: http://localhost:15672 (guest/guest)

> Миграции применяются автоматически при старте контейнеров.

---

## Архитектура

```
┌─────────┐      ┌─────────┐      ┌──────────┐      ┌──────────┐      ┌────────┐
│   API   │─────▶│ Service │─────▶│ Postgres │◀─────│ Publisher│─────▶│RabbitMQ│
│ FastAPI │      │  Layer  │      │  +Outbox │      │  (Relay) │      │        │
└─────────┘      └─────────┘      └──────────┘      └──────────┘      └────┬───┘
                                         ▲                                    │
                                         │                                    ▼
                                   ┌─────────┐                         ┌─────────┐
                                   │ Service │◀────────────────────────│ Worker  │
                                   │  Layer  │                         └─────────┘
                                   └─────────┘
```

| Компонент | Роль |
|-----------|------|
| **API** | HTTP-эндпоинты, валидация через Pydantic |
| **Service Layer** | Бизнес-логика, работа с БД через SQLAlchemy |
| **Publisher (relay)** | Читает outbox, публикует task_id в RabbitMQ, удаляет из outbox |
| **Worker** | Слушает RabbitMQ, обрабатывает задачи, обновляет статус |

---

## Почему RabbitMQ, а не Kafka

- Задача — простая очередь задач, не стриминг событий
- Не нужны партиции, топики, consumer groups
- Встроенный `message.ack()` — подтверждение обработки
- Проще в настройке и мониторинге для данного масштаба

---

## Ключевые решения

### Outbox pattern

API не пишет в RabbitMQ напрямую. Задача и outbox-запись создаются в одной транзакции:

```python
async with session.begin():
    task = Task(payload=payload)
    session.add(task)
    session.flush()

    outbox = Outbox(task_id=task.id)
    session.add(outbox)
```

Publisher (relay) периодически читает outbox и публикует в очередь. Если relay упадёт — сообщения останутся в outbox и будут доставлены при рестарте.

**Зачем:**
- API работает только с БД — ACID транзакции
- Гарантия доставки (eventually consistent)
- Payload не попадает в брокер — защита от больших данных

### SELECT FOR UPDATE

Worker использует пессимистичную блокировку при обработке:

```python
result = await session.execute(
    select(Task).where(Task.id == task_id).with_for_update()
)
```

**Зачем:**
- RabbitMQ может доставить сообщение дважды
- Несколько воркеров не обработают одну задачу
- Защита от TOCTOU (Time-of-Check-Time-of-Use)

### Атомарная публикация в relay

Relay публикует и удаляет сообщения по одному:

```python
for msg in messages:
    await queue.publish({"task_id": msg.task_id})
    await session.delete(msg)
    await session.commit()
```

При падении после 5-го из 10 сообщений — при рестарте будут отправлены только оставшиеся 5.

---

## Статусы задач

| Статус | Описание |
|--------|----------|
| `pending` | Создана, ожидает обработки |
| `processing` | Worker взял в работу |
| `done` | Успешно обработана |
| `failed` | Ошибка при обработке |

Удаление задачи возможно только в статусе `done` или `failed`.

---

## API

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/tasks` | Создать задачу. Возвращает `task_id` и `status` |
| `GET` | `/tasks` | Список задач с пагинацией (`skip`, `limit`) |
| `GET` | `/tasks/{id}` | Получить задачу по ID |
| `PATCH` | `/tasks/{id}` | Обновить `payload` или `result` |
| `DELETE` | `/tasks/{id}` | Удалить задачу (только `done`/`failed`) |

---

## Масштабирование

**Worker:** запустить N реплик — RabbitMQ распределит задачи автоматически (round-robin). `SELECT FOR UPDATE` гарантирует, что задача будет обработана ровно один раз.

**API:** несколько реплик за балансировщиком.

**Publisher:** активный + standby или несколько инстансов с координацией через блокировки.

**БД:** read-реплики для GET-запросов, шардирование по task_id при росте.

---

## Потенциальные точки отказа

| Проблема | Решение |
|----------|---------|
| Publisher упал — задачи копятся в outbox | Дубликация publisher или CDC |
| PostgreSQL не выдерживает нагрузку | Read-реплики, outbox в Redis |
| `durable=True` — медленная запись на диск | Lazy queues в RabbitMQ |
| Нет rate limiting | Nginx / API Gateway |

---

## Что добавить для продакшена

- Аутентификация и авторизация
- Rate limiting
- TTL для сообщений в RabbitMQ и Dead Letter Queue
- Метрики (Prometheus + Grafana)
- Структурированное логирование в ELK/Loki
- Интеграционные и E2E тесты
- Graceful shutdown (SIGTERM)
- API versioning (`/api/v1/tasks`)
- Connection pooling с настройкой `pool_size`, `max_overflow`

---

## Структура проекта

```
├── api/                # FastAPI приложение
│   └── routers/        # Эндпоинты
├── worker/             # Consumer — обработка задач
│   └── solver.py       # Бизнес-логика обработки
├── relay/              # Publisher — outbox → RabbitMQ
├── broker/             # Обёртка над aio-pika
├── service/            # Сервисный слой (вся работа с БД)
├── database/           # Engine, session, миграции
│   └── migration/      # Alembic
├── shared/             # Общий код
│   ├── models/         # SQLAlchemy ORM-модели
│   ├── schemas/        # Pydantic-схемы
│   └── config.py       # Настройки из переменных окружения
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Миграции

Используется Alembic. Миграции хранятся в `database/migration/versions/` и применяются автоматически при `docker compose up`.

Для создания новой миграции локально:

```bash
docker compose up postgres -d
alembic revision --autogenerate -m "description"
alembic upgrade head
```
