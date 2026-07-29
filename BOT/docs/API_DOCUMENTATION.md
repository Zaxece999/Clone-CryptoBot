# Crypto Pay API Documentation

## Обзор

Crypto Pay API позволяет интегрировать функции CryptoBot в ваши приложения. API предоставляет возможности для создания инвойсов, чеков, выполнения переводов и получения информации о балансе.

## Базовая информация

- **Base URL**: `https://pay.crypt.bot/api`
- **Протокол**: HTTPS
- **Формат данных**: JSON
- **Кодировка**: UTF-8

## Аутентификация

Все запросы к API должны содержать заголовок аутентификации:

```
Crypto-Pay-API-Token: YOUR_API_TOKEN
```

API токен можно получить в боте через команду `/api`.

## Структура ответа

Все ответы API имеют следующую структуру:

```json
{
  "ok": true,
  "result": {
    // данные ответа
  }
}
```

В случае ошибки:

```json
{
  "ok": false,
  "error": {
    "code": "ERROR_CODE",
    "name": "ErrorName",
    "message": "Описание ошибки"
  }
}
```

## Методы API

### getMe

Получить информацию о текущем приложении.

**Запрос:**
```
GET /getMe
```

**Ответ:**
```json
{
  "ok": true,
  "result": {
    "app_id": 1,
    "name": "My Application",
    "payment_processing_bot_username": "CryptoBot"
  }
}
```

### getBalance

Получить баланс кошелька.

**Запрос:**
```
GET /getBalance
```

**Ответ:**
```json
{
  "ok": true,
  "result": [
    {
      "currency_code": "USDT",
      "available": "100.50",
      "onhold": "0.00"
    },
    {
      "currency_code": "BTC",
      "available": "0.001",
      "onhold": "0.000"
    }
  ]
}
```

### getExchangeRates

Получить курсы обмена валют.

**Запрос:**
```
GET /getExchangeRates
```

**Ответ:**
```json
{
  "ok": true,
  "result": [
    {
      "is_crypto": true,
      "is_fiat": false,
      "source": "BTC",
      "target": "USD",
      "rate": "45000.00"
    }
  ]
}
```

### getCurrencies

Получить список поддерживаемых валют.

**Запрос:**
```
GET /getCurrencies
```

**Ответ:**
```json
{
  "ok": true,
  "result": [
    {
      "is_blockchain": true,
      "is_stablecoin": false,
      "is_fiat": false,
      "name": "Bitcoin",
      "code": "BTC",
      "url": "https://bitcoin.org",
      "decimals": 8
    }
  ]
}
```

### createInvoice

Создать инвойс для оплаты.

**Запрос:**
```
POST /createInvoice
Content-Type: application/json

{
  "asset": "USDT",
  "amount": "10.50",
  "description": "Payment for service",
  "hidden_message": "Thank you!",
  "paid_btn_name": "callback",
  "paid_btn_url": "https://example.com/success",
  "payload": "user_123",
  "allow_comments": true,
  "allow_anonymous": false,
  "expires_in": 3600
}
```

**Параметры:**
- `asset` (string, обязательный) - код валюты
- `amount` (string, обязательный) - сумма
- `description` (string, необязательный) - описание платежа
- `hidden_message` (string, необязательный) - скрытое сообщение
- `paid_btn_name` (string, необязательный) - название кнопки после оплаты
- `paid_btn_url` (string, необязательный) - URL кнопки после оплаты
- `payload` (string, необязательный) - дополнительные данные
- `allow_comments` (boolean, необязательный) - разрешить комментарии
- `allow_anonymous` (boolean, необязательный) - разрешить анонимную оплату
- `expires_in` (integer, необязательный) - время жизни в секундах

**Ответ:**
```json
{
  "ok": true,
  "result": {
    "invoice_id": 123,
    "status": "active",
    "hash": "abc123",
    "asset": "USDT",
    "amount": "10.50",
    "pay_url": "https://t.me/CryptoBot?start=invoice_abc123",
    "bot_invoice_url": "https://t.me/CryptoBot?start=invoice_abc123",
    "created_at": "2023-01-01T12:00:00Z",
    "allow_comments": true,
    "allow_anonymous": false,
    "description": "Payment for service"
  }
}
```

### getInvoices

Получить список инвойсов.

**Запрос:**
```
GET /getInvoices?asset=USDT&invoice_ids=123,124&status=paid&offset=0&count=100
```

**Параметры:**
- `asset` (string, необязательный) - фильтр по валюте
- `invoice_ids` (string, необязательный) - список ID инвойсов через запятую
- `status` (string, необязательный) - фильтр по статусу
- `offset` (integer, необязательный) - смещение для пагинации
- `count` (integer, необязательный) - количество записей (макс. 1000)

**Ответ:**
```json
{
  "ok": true,
  "result": {
    "items": [
      {
        "invoice_id": 123,
        "status": "paid",
        "hash": "abc123",
        "asset": "USDT",
        "amount": "10.50",
        "pay_url": "https://t.me/CryptoBot?start=invoice_abc123",
        "created_at": "2023-01-01T12:00:00Z",
        "paid_at": "2023-01-01T12:05:00Z"
      }
    ],
    "count": 1
  }
}
```

### createCheck

Создать чек для отправки средств.

**Запрос:**
```
POST /createCheck
Content-Type: application/json

{
  "asset": "USDT",
  "amount": "5.00",
  "pin_to_user_id": 123456789,
  "pin_to_username": "username"
}
```

**Параметры:**
- `asset` (string, обязательный) - код валюты
- `amount` (string, обязательный) - сумма
- `pin_to_user_id` (integer, необязательный) - привязать к пользователю по ID
- `pin_to_username` (string, необязательный) - привязать к пользователю по username

**Ответ:**
```json
{
  "ok": true,
  "result": {
    "check_id": 456,
    "hash": "def456",
    "asset": "USDT",
    "amount": "5.00",
    "bot_check_url": "https://t.me/CryptoBot?start=check_def456",
    "status": "active",
    "created_at": "2023-01-01T12:00:00Z",
    "activates_count": 0
  }
}
```

### getChecks

Получить список чеков.

**Запрос:**
```
GET /getChecks?asset=USDT&check_ids=456,457&status=active&offset=0&count=100
```

**Параметры аналогичны getInvoices**

### deleteCheck

Удалить чек.

**Запрос:**
```
DELETE /deleteCheck
Content-Type: application/json

{
  "check_id": 456
}
```

**Ответ:**
```json
{
  "ok": true,
  "result": true
}
```

### transfer

Перевести средства другому пользователю.

**Запрос:**
```
POST /transfer
Content-Type: application/json

{
  "user_id": 123456789,
  "asset": "USDT",
  "amount": "1.00",
  "spend_id": "unique_spend_id",
  "comment": "Transfer comment",
  "disable_send_notification": false
}
```

**Параметры:**
- `user_id` (integer, обязательный) - Telegram ID получателя
- `asset` (string, обязательный) - код валюты
- `amount` (string, обязательный) - сумма
- `spend_id` (string, обязательный) - уникальный ID операции
- `comment` (string, необязательный) - комментарий к переводу
- `disable_send_notification` (boolean, необязательный) - отключить уведомление

**Ответ:**
```json
{
  "ok": true,
  "result": {
    "transfer_id": 789,
    "user_id": 123456789,
    "asset": "USDT",
    "amount": "1.00",
    "status": "completed",
    "completed_at": "2023-01-01T12:00:00Z",
    "comment": "Transfer comment"
  }
}
```

## Webhook уведомления

Для получения уведомлений о событиях настройте webhook URL в настройках приложения.

### Структура webhook

```json
{
  "update_id": 1,
  "update_type": "invoice_paid",
  "request_date": "2023-01-01T12:00:00Z",
  "payload": {
    "invoice_id": 123,
    "status": "paid",
    "hash": "abc123",
    "asset": "USDT",
    "amount": "10.50",
    "paid_at": "2023-01-01T12:05:00Z",
    "paid_anonymously": false,
    "comment": "Payment comment"
  }
}
```

### Типы событий

- `invoice_paid` - инвойс оплачен
- `check_activated` - чек активирован

### Верификация webhook

Для верификации webhook используйте заголовок `crypto-pay-api-signature`:

```python
import hmac
import hashlib

def verify_webhook(body, signature, secret):
    expected = hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

## Коды ошибок

| Код | Название | Описание |
|-----|----------|----------|
| `UNAUTHORIZED` | Unauthorized | Неверный API токен |
| `FORBIDDEN` | Forbidden | Недостаточно прав |
| `NOT_FOUND` | NotFound | Ресурс не найден |
| `VALIDATION_ERROR` | ValidationError | Ошибка валидации данных |
| `INSUFFICIENT_FUNDS` | InsufficientFunds | Недостаточно средств |
| `RATE_LIMIT_EXCEEDED` | RateLimitExceeded | Превышен лимит запросов |
| `INTERNAL_ERROR` | InternalError | Внутренняя ошибка сервера |

## Лимиты

- Максимум 1000 запросов в минуту на API ключ
- Максимум 10000 запросов в час на API ключ
- Максимум 100000 запросов в день на API ключ
- Максимум 1000 записей в одном запросе списка

## Примеры кода

### Python

```python
import requests
import json

class CryptoPayAPI:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {
            "Crypto-Pay-API-Token": api_token,
            "Content-Type": "application/json"
        }
    
    def get_me(self):
        response = requests.get(f"{self.base_url}/getMe", headers=self.headers)
        return response.json()
    
    def create_invoice(self, asset, amount, **kwargs):
        data = {"asset": asset, "amount": amount, **kwargs}
        response = requests.post(
            f"{self.base_url}/createInvoice",
            json=data,
            headers=self.headers
        )
        return response.json()
    
    def create_check(self, asset, amount, **kwargs):
        data = {"asset": asset, "amount": amount, **kwargs}
        response = requests.post(
            f"{self.base_url}/createCheck",
            json=data,
            headers=self.headers
        )
        return response.json()

# Использование
api = CryptoPayAPI("your_api_token_here")
invoice = api.create_invoice("USDT", "10.00", description="Test payment")
print(invoice)
```

### JavaScript

```javascript
class CryptoPayAPI {
    constructor(apiToken) {
        this.apiToken = apiToken;
        this.baseUrl = "https://pay.crypt.bot/api";
        this.headers = {
            "Crypto-Pay-API-Token": apiToken,
            "Content-Type": "application/json"
        };
    }
    
    async getMe() {
        const response = await fetch(`${this.baseUrl}/getMe`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async createInvoice(asset, amount, options = {}) {
        const data = { asset, amount, ...options };
        const response = await fetch(`${this.baseUrl}/createInvoice`, {
            method: "POST",
            headers: this.headers,
            body: JSON.stringify(data)
        });
        return response.json();
    }
}

// Использование
const api = new CryptoPayAPI("your_api_token_here");
api.createInvoice("USDT", "10.00", { description: "Test payment" })
    .then(invoice => console.log(invoice));
```

### cURL

```bash
# Получить информацию о приложении
curl -X GET "https://pay.crypt.bot/api/getMe" \
  -H "Crypto-Pay-API-Token: your_api_token_here"

# Создать инвойс
curl -X POST "https://pay.crypt.bot/api/createInvoice" \
  -H "Crypto-Pay-API-Token: your_api_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "asset": "USDT",
    "amount": "10.00",
    "description": "Test payment"
  }'
```

## Поддержка

Если у вас есть вопросы по использованию API, обратитесь в поддержку через бота или создайте issue в репозитории проекта.