# Асинхронная система обработки задач

Высоконагруженное приложение для надежной обработки задач через очередь сообщений.  
Построено на **FastAPI**, **PostgreSQL** и **RabbitMQ**.

---

## Быстрый старт

```bash
docker compose up
```

API будет доступен на http://localhost:8000/docs

> Миграции выполняются автоматически при старте контейнеров

---

## Архитектура

### Почему RabbitMQ, а не Kafka?

Выбрал RabbitMQ по нескольким причинам:

- Обычная очередь задач
- Не нужны партиции, топики, consumer groups
- RabbitMQ легче разворачивать и мониторить для небольших нагрузок
- Гарантии `message.ack()`

Для текущей задачи (обработка задач с гарантией выполнения) RabbitMQ подходит.


### Outbox

Хотим, чтобы задача атомарно сохранялась в бд и отправлялась брокеру. для этого используем доп. таблицу Outbox:

```python
# Атомарная транзакция
async with session.begin():
    task = Task(payload=payload)
    session.add(task)
    session.flush()  # Получили ID
    
    outbox = Outbox(task_id=task.id)  # Записали в outbox
    session.add(outbox)
    # Commit обеих записей в одной транзакции
```

**Publisher (relay)** периодически читает `outbox` и публикует в RabbitMQ:

```python
while True:
    messages = select_from_outbox()
    for msg in messages:
        queue.publish(msg.task_id)
        delete_from_outbox(msg.id)
    sleep(1)
```

**Преимущества:**

- API работает только с БД (ACID транзакции)
- При падении relay сообщения остаются в outbox
- Гарантия: любая задача попадет в очередь (eventually consistent)
- Payload не попадает в брокер (защита от огромных данных)

---


### Идемпотентность обработки

Worker проверяет статус перед обработкой:

```python
task = get_task(task_id)
if task.status != PENDING:
    return  # Уже обработано или в процессе
```

**Защита от:**
- Дубликатов сообщений (RabbitMQ может доставить дважды)
- Повторной обработки при рестартах

---

### Компоненты системы

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

**Компоненты:**

- **API** (FastAPI) — принимает HTTP-запросы, валидирует схемы
- **Service Layer** — бизнес-логика, работа с БД через ORM (создание Task + Outbox атомарно)
- **Publisher** (relay) — читает Outbox, публикует task_id в RabbitMQ, очищает Outbox
- **Worker** — слушает RabbitMQ, обрабатывает задачи через Service Layer, обновляет статус

Каждый сервис можно масштабировать независимо:
- API: несколько реплик за load balancer
- Publisher: активный + standby или несколько с lock-based coordination
- Worker: N реплик — RabbitMQ распределит нагрузку


### Миграции

Используется **Alembic** с поддержкой async SQLAlchemy.

## Масштабирование

### Горизонтальное масштабирование воркеров

Легко добавить новые инстансы: RabbitMQ автоматически распределит задачи между ними ( например через round-robin). Каждый worker обрабатывает задачи параллельно, но не больше одного воркера на задачу (идемпотентность).

### Вертикальное масштабирование

**Worker:**
- можно вводить multiprocessing

### Шардирование бд

### Реплики сервисных уровней и API, добавление балансировщика


## Потенциальные точки отказа

<table>
<tr>
<td><strong>Проблема</strong></td>
<td><strong>Решение</strong></td>
</tr>
<tr>
<td> Publisher упал → задачи накапливаются в outbox</td>
<td> Дубликация или CDC (Change Data Capture)</td>
</tr>
<tr>
<td>Postgres не выдерживает нагрузку</td>
<td> Outbox в Redis + payload там же</td>
</tr>
<tr>
<td> <code>durable=True</code> → медленная запись на диск</td>
<td> Lazy queues (память → диск при нехватке)</td>
</tr>
<tr>
<td> Отсутствует rate limiting</td>
<td> Nginx</td>
</tr>
</table>

**Что еще нужно добавить:**

- TTL для сообщений в RabbitMQ
- Структурированное логирование (ELK/Loki)
- Метрики (Prometheus + Grafana)
- Интеграционные и E2E тесты
- API Versioning

---

## Структура проекта

```
├── api/              # FastAPI приложение
│   └── routers/      # Эндпоинты
├── worker/           # Обработчик задач
│   └── solver.py     # Бизнес-логика
├── relay/            # Publisher (Outbox → RabbitMQ)
├── service/          # Бизнес-логика
├── database/         # БД setup
│   └── migration/    # Alembic миграции
├── shared/           # Общий код
│   ├── models/       # ORM модели
│   └── schemas/      # Pydantic схемы
└── docker-compose.yml
```

---

## Статусы задач

| Статус | Описание |
|--------|----------|
| `pending` | Создана, ждет в очереди |
| `processing` | Worker взял в работу |
| `done` | Успешно выполнена |
| `failed` | Ошибка при выполнении |

## Сложности при разработке

### 1. Docker Compose зависимости и healthchecks
Несколько раз сталкивался с тем, что воркеры стартовали раньше RabbitMQ и падали с `ConnectionRefusedError`. Пришлось изучать healthchecks, `depends_on` с `condition`, разбираться почему `service_started` недостаточно и нужен `service_healthy`.

### 2. Автоматизация миграций
Хотел, чтобы `docker compose up` запускал все автоматически, включая миграции. Проблема: старые файлы миграций могли конфликтовать с новой схемой. Решение с очисткой `alembic_version` пришло не сразу — сначала пытался удалять файлы вручную.
