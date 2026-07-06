# Telegram infosec autoposting

Отдельный проект для автопостинга экспертных материалов по информационной безопасности в Telegram-канал.

## Что внутри

- `content-plan-infosec.md` — контент-план на 30 дней.
- `docs/autoposting-prompt.md` — промпт и правила генерации Telegram-постов.
- `.env.example` — шаблон переменных окружения для сервера.

## Настройка на сервере

```bash
git clone https://github.com/Salencore/telegram-infosec-autoposting.git
cd telegram-infosec-autoposting
cp .env.example .env
nano .env
```

Заполните `.env`:

```env
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=123456:...
TELEGRAM_CHANNEL_ID=@channel_username_or_numeric_id
```

Бот должен быть добавлен администратором в Telegram-канал и иметь право публиковать сообщения.

## Логика

Автопостер должен каждый день:

1. Читать `content-plan-infosec.md`.
2. Находить строку календаря по сегодняшней дате.
3. Генерировать пост по правилам из `docs/autoposting-prompt.md`.
4. Проверять JSON-ответ модели.
5. Сразу публиковать готовый пост в Telegram-канал.
