# Деплой системы регистрации форума

## 1. Почта домена через Яндекс 360 (бесплатно)

### Регистрация
1. Идёшь на https://360.yandex.ru/business/
2. Нажимаешь "Подключить бесплатно"
3. Вводишь домен: `bigmoneychina.tech`
4. Яндекс покажет MX и TXT записи для добавления

### DNS записи (добавить на reg.ru)
```
Тип: MX  Имя: @  Значение: mx.yandex.net.  Приоритет: 10
Тип: TXT  Имя: @  Значение: v=spf1 redirect=_spf.yandex.ru
Тип: CNAME  Имя: mail  Значение: domain.mail.yandex.net.
```

### Создание почтового ящика
После подключения создай: `info@bigmoneychina.tech`

### SMTP для отправки писем из кода
```
Host: smtp.yandex.ru
Port: 465
SSL: YES
Login: info@bigmoneychina.tech
Password: пароль приложения (создать в настройках Яндекс ID)
```

⚠️ Используй "пароль приложения", не обычный пароль аккаунта!
   Яндекс ID → Безопасность → Пароли приложений → Создать пароль


## 2. Robokassa — регистрация

1. Идёшь на https://robokassa.com
2. Регистрируешься как ИП или ООО (физлицо не поддерживает фискализацию!)
3. В настройках магазина указываешь:
   - ResultURL: `https://bigmoneychina.tech/payment/result`
   - SuccessURL: `https://bigmoneychina.tech/payment/success`
   - FailURL: `https://bigmoneychina.tech/payment/fail`
   - Метод: POST
   - Алгоритм подписи: MD5
4. Подключаешь фискализацию (в разделе "Онлайн-кассы")
5. Копируешь: Login магазина, Пароль#1, Пароль#2


## 3. Деплой на сервер Timeweb (5.129.216.155)

### SSH подключение
```bash
ssh root@5.129.216.155
```

### Установка
```bash
git clone https://github.com/romahastr-cell/bigmoneychina-forum.git
cd bigmoneychina-forum/backend

# Создай .env из примера
cp .env.example .env
nano .env   # заполни все значения

# Запуск
docker compose up -d --build

# Первичная настройка форума в БД
docker exec forum-backend python setup_forum.py

# Установка Telegram webhook
docker exec forum-backend python set_webhook.py
```

### Проверка
```bash
curl https://bigmoneychina.tech/health
# Должно вернуть: {"status":"ok"}
```


## 4. Получить свой Telegram Chat ID

Напиши боту @userinfobot — он покажет твой chat_id.
Или напиши боту https://t.me/getmyid_bot

Запиши в .env:
```
TELEGRAM_ADMIN_CHAT_ID=ваш_chat_id
```


## 5. Добавить кнопку регистрации на сайт

В index.html замени все ссылки кнопок "Купить билет" на:
```html
href="https://bigmoneychina.tech/register"
```


## 6. Команды бота (для тебя как админа)

- `/stats` — статистика: сколько зарегистрировалось, оплатило
- `/list` — последние 10 участников
- `/mail` — создать email-рассылку для всех оплативших
- `/forums` — список форумов


## 7. Обновление ссылок МТС Линк перед каждым форумом

Напрямую в .env файле обновляй:
```
MTS_LINK_DAY1=https://mts-link.ru/новая_ссылка_день1
MTS_LINK_DAY2=https://mts-link.ru/новая_ссылка_день2
MTS_LINK_DAY3=https://mts-link.ru/новая_ссылка_день3
```
Потом: `docker compose restart forum-backend`


## 8. Автоматические напоминания (30 минут до эфира)

Добавь в crontab на сервере:
```bash
crontab -e

# День 1 - 21 апреля 10:30 МСК (07:30 UTC)
30 7 21 4 * docker exec forum-backend python send_reminder.py 1

# День 2 - 22 апреля 10:30 МСК
30 7 22 4 * docker exec forum-backend python send_reminder.py 2

# День 3 - 23 апреля 10:30 МСК
30 7 23 4 * docker exec forum-backend python send_reminder.py 3
```
