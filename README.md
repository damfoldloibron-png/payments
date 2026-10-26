# Сервис процессинга платежей

Микросервис, принимающий запросы на оплату, обрабатывает их через внешний платежный шлюз (эмуляция) и уведомляет обратно клиента через webhook. Пришедший платеж сохраняется в базе вместе с событием outbox в рамках одной транзакции - для сохранности. События из таблицы outbox читаются фоновой задачей - relay-процессом, и публикуются в RabbitMQ. Consumer подписывается на соответствующую очередь (привязанную к обменнику), получает событие, обрабатывает его (чтение БД, платеж, запись в БД, webhook) и подтверждает обработку. В случае ошибок сообщения отправляются в retry-очереди с заданным TTL, по истечении которого обратно направляются в основную очередь и повторяют попытку. Если попытки закончились, событие отправляется в DLQ.

## Запуск

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt # для миграции алембик и тестов
docker compose up -d --build --wait && alembic upgrade head
```

## Структура

```text
src/
  main.py            точка входа API
  app.py             создание приложения, startup/shutdown (БД, брокер, relay)
  routers.py         подключение маршрутов
  exc_handler.py     обработчики исключений
  middleware.py      логирование запросов
  config/            настройки и логирование
  database/          engine, фабрика сессий, Base
  payment_api/       модель платежей: router, schemas и т.п.
  outbox/            модель outbox: repository, relay-process
  external/
    broker/          брокер, топология (обменники, очереди)
    webhook/         HTTP-клиент webhook
  consumer/          точка входа consumer, handler, service
migrations/          миграции Alembic
docker-compose.yaml  postgres, rabbitmq, api, consumer
```

## Сценарии, надежность

Пришедшее событие сохраняется в таблице и в случае падения процесса, на рестарте relay вновь прочитает неотправленные события.

Rabbit хранит сообщения, пока их не подтвердит Consumer. Если при обработке события произошла ошибка:
- Платежа нет (событие сразу в DLQ)
- БД недоступна на чтении (Retry; если попытки закончились, событие в DLQ, платеж остается PENDING)
- Платеж вернулся с ошибкой (Retry, состояние еще не изменено; после последней попытки платеж получает статус FAILED, клиенту уходит webhook, событие в DLQ)
- Ошибка на записи в БД (Retry: платеж вновь отправляется с тем же ключом идемпотентности - считается, что платежный шлюз умеет обрабатывать это; если попытки закончились, событие в DLQ, платеж остается PENDING, при возврате события из DLQ он будет обработан вновь)
- Ошибка на webhook (Retry: читаем вновь БД, платеж обработан, отправляем webhook вновь, таким образом гарантия доставки минимум 1 раз; если попытки закончились, событие в DLQ, а результат платежа клиент получит через GET)

### Примеры

Создание платежа (`X-API-Key` - значение `API_KEY` из `.env`):

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: fOehNd+h1Q2g9yboVSh7Uwx/V299uJA3uZRssM493cA=" \
  -H "Idempotency-Key: order-" \
  -H "Content-Type: application/json" \
  -d '{"amount": "1500.50", "currency": "RUB", "description": "Оплата заказа 1", "metadata": {"order_id": "1"}, "webhook_url": "https://httpbin.org/post"}'
```

Ответ `202`:

```json
{"payment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "status": "PENDING", "created_at": "2026-10-08T10:15:02Z"}
```

Повтор с тем же `Idempotency-Key` вернет тот же платеж, новое событие не создается. Получение платежа (через 2-5 секунд статус `SUCCEEDED`):

```bash
curl http://localhost:8000/api/v1/payments/1cbad274-f268-421a-9e8b-8e3ad8ce9738 -H "X-API-Key: fOehNd+h1Q2g9yboVSh7Uwx/V299uJA3uZRssM493cA="
```

Брокер недоступен при приеме платежа (outbox):

```bash
docker compose stop rabbitmq
# POST /api/v1/payments -> 202, GET -> статус PENDING
docker compose start rabbitmq
```

Через несколько секунд relay публикует сохраненное событие, платеж становится `SUCCEEDED`, на webhook приходит запрос (при сбое между публикацией и отметкой событие может уйти повторно, поэтому webhook может прийти дважды).

БД недоступна при приеме платежа:

```bash
docker compose stop postgres
# POST /api/v1/payments -> 500, платеж не создан
docker compose start postgres
```

После запуска БД повтор запроса с тем же `Idempotency-Key` безопасен: платеж создается один раз.

БД недоступна во время обработки: сразу после `POST` остановить postgres и поднять его в течение ~15 секунд (попытки идут с паузами 5 и 10 секунд). Платеж становится `SUCCEEDED`, webhook приходит. Если БД поднята позже, сообщение попадает в `payments.dlq`, платеж остается `PENDING`.

Недоступный webhook: в запросе `"webhook_url": "http://localhost:1"`. Платеж `SUCCEEDED`, после трех попыток (паузы 5 и 10 секунд) сообщение в `payments.dlq`.


### Тесты

Интеграционные тесты работают против запущенного стека (`docker compose up`, миграции применены):

```bash
pytest -m integration
```

- `tests/integration/test_api.py` - авторизация, валидация, создание и получение платежа, идемпотентность.
- `tests/integration/test_load.py` - пачка платежей (`TEST_LOAD_COUNT`, по умолчанию 100): время, скорость и доля успеха.

Адрес API и webhook переопределяются `TEST_BASE_URL` и `TEST_WEBHOOK_URL`, тесты не очищают БД.
