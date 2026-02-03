Асинхронное приложение для обработки задач через очередь сообщений. Построен на FastAPI, PostgreSQL и RabbitMQ.

## Быстрый старт

```bash
docker compose up

```

API будет доступен на http://localhost:8000/docs (Swagger UI).


## Архитектура

### Почему RabbitMQ, а не Kafka?

Выбрал RabbitMQ по нескольким причинам:

- Обычная очередь задач
- Не нужны партиции, топики, consumer groups
- RabbitMQ легче разворачивать и мониторить для небольших нагрузок
- Гарантии `message.ack()`

Для текущей задачи (обработка задач с гарантией выполнения) RabbitMQ идеально подходит.


### 1. Transactional Outbox Pattern

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
Возникает потребность в отдельном сервисе (relay) который будет читать `outbox` таблицу и публиковать в RabbitMQ:

```python
while True:
    messages = select_from_outbox()
    for msg in messages:
        queue.publish(msg.task_id)
        delete_from_outbox(msg.id)
    sleep(1)
```

**Почему это надежно:**
- API не трогает RabbitMQ вообще — только БД (ACID транзакции)
- Если relay упадет — сообщения останутся в outbox, опубликуются позже
- Гарантия: любая задача в `tasks` попадет в очередь (eventually consistent)

### 2. Payload в БД, а не в очереди

на случай если он огромен


### 3. Идемпотентность обработки

Worker проверяет статус перед обработкой:
```python
task = get_task(task_id)
if task.status != PENDING:
    return  # Уже обработано или в процессе
```

Это защищает от:
- Дубликатов сообщений (RabbitMQ может доставить дважды при сбоях)
- Повторной обработки при restart'ах

### Микросервисная архитектура

### Миграции


## Масштабирование

### Горизонтальное масштабирование воркеров

Легко добавить новые инстансы: RabbitMQ автоматически распределит задачи между ними ( например через round-robin). Каждый worker обрабатывает задачи параллельно, но не больше одного воркера на задачу (идемпотентность).

### Вертикальное масштабирование

**Worker:**
- можно вводить multiprocessing

### Шардирование бд

### Дубликация сервисных уровней и API, добавление балансировщика


## Потенциальные точки отказа

**Проблема:** Если Publisher упадет, задачи накапливаются в outbox.
**Решение:** Дубликация или CDC

**Проблема:** Postgres не выдерживает нагрузок.
**Решение:** Outbox в Redis вместе с payload

**Проблема:** `durable=True` и `DeliveryMode.PERSISTENT` — каждое сообщение пишется на диск
**Решение:** Lazy queues в RabbitMQ (хранят в памяти, на диск при нехватке) или in-flight

**Проблема:** Нет rate limiting
**Решение:** Nginx


**Еще следует добавить:**
- TTL в RabbitMQ
- logger
- подключить метрики (Prometheus + Grafana)
- Юнит, интеграционные, сквозные тесты
- Версионирование

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

## Статусы задач

| Статус | Описание |
|--------|----------|
| `pending` | Создана, ждет в очереди |
| `processing` | Worker взял в работу |
| `completed` | Успешно выполнена |
| `failed` | Ошибка при выполнении |

