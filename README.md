# Telegram-бот магазина косметики

MVP бота для магазина косметики на Python + aiogram 3.

## Возможности

- Добавление товаров администратором через `/addproduct` или `/admin`.
- Локальное хранение товаров в `data/products.json`.
- Генерация ссылки на товар вида `https://t.me/tgBOTmagadzamba_bot?start=PRODUCT_ID`.
- Открытие карточки товара по ссылке из Telegram-канала.
- Оформление заказа с вводом имени, телефона и адреса.
- Инлайн-кнопки для всех основных действий, включая `Назад` и `Отмена`.
- Заглушка оплаты: реальный платеж не создается, заказ не подтверждается, сообщение админу не отправляется.
- Опционально: исходящие запросы к Telegram API через HTTP/SOCKS-прокси (`aiohttp-socks`).

## Установка

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка

Скопируйте `.env.example` в `.env` и заполните:

```env
BOT_TOKEN=your_bot_token
ADMIN_ID=7600749840
BOT_USERNAME=tgBOTmagadzamba_bot

# Пример прокси в коротком формате host:port:user:pass (или полный URL socks5://...)
# TELEGRAM_PROXY=HOST:PORT:USER:PASSWORD
# Для SOCKS в коротком формате задайте TELEGRAM_PROXY_SCHEME=socks5
```

Реальные токены, логины и пароли прокси не храните в репозитории. Если они попали в чат — лучше перевыпустить и сменить.

## Запуск локально

```bash
python bot.py
```

При заданном `TELEGRAM_PROXY` бот создаёт сессию через `AiohttpSession(proxy=...)`; для работы прокси нужен пакет `aiohttp-socks` (уже в `requirements.txt`).

## Автозапуск (Linux, systemd)

Пример юнита лежит в [`deploy/tg-cosmetics-bot.service`](deploy/tg-cosmetics-bot.service). Отредактируйте пути `WorkingDirectory`, `EnvironmentFile`, `ExecStart`, пользователя `User`/`Group`, затем на сервере:

```bash
sudo cp deploy/tg-cosmetics-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tg-cosmetics-bot.service
sudo journalctl -u tg-cosmetics-bot -f
```

На Windows для автозапуска обычно используют «Планировщик заданий» или nssm, указав `python`/`pythonw` и каталог проекта.

## Админ-команды

- `/admin` — открыть админ-меню.
- `/addproduct` — начать добавление товара.

Админ-функции доступны только Telegram ID из `ADMIN_ID`.
