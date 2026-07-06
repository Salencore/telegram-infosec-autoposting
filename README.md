# Telegram infosec autoposting

Отдельный проект для бесплатного автопостинга экспертных материалов по информационной безопасности в Telegram-канал.

По умолчанию проект работает без платных API: он берет тему дня из `content-plan-infosec.md` и публикует готовый статический текст. OpenRouter, Gemini или OpenAI можно подключить, если понадобится ежедневная генерация новых вариантов.

## Что внутри

- `content-plan-infosec.md` — контент-план на 30 дней.
- `docs/autoposting-prompt.md` — промпт и правила генерации Telegram-постов.
- `autoposter/` — Python-скрипт, который генерирует и публикует посты.
- `posts/` — опциональная папка для ручных готовых постов. Если файла на дату нет, автопостер соберет пост сам из встроенных шаблонов.
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
TELEGRAM_BOT_TOKEN=123456:...
TELEGRAM_CHANNEL_ID=@channel_username_or_numeric_id
CONTENT_SOURCE=static
```

Бот должен быть добавлен администратором в Telegram-канал и иметь право публиковать сообщения.

`OPENAI_API_KEY`, `GEMINI_API_KEY` и `OPENROUTER_API_KEY` для статического режима не нужны.

## Ручная проверка

Посмотреть пост за конкретную дату без публикации:

```bash
docker compose run --rm infosec-autoposter python -m autoposter --once --dry-run --date 2026-07-06
```

Сразу опубликовать пост за конкретную дату:

```bash
docker compose run --rm infosec-autoposter python -m autoposter --once --date 2026-07-06
```

## Docker запуск

```bash
docker compose up -d --build
docker compose logs -f
```

Контейнер каждый день запускает публикацию в `AUTOPUBLISH_HOUR:AUTOPUBLISH_MINUTE` по `DEFAULT_TIMEZONE`.

## Логика

Автопостер должен каждый день:

1. Читать `content-plan-infosec.md`.
2. Находить строку календаря по сегодняшней дате.
3. Если есть файл `posts/YYYY-MM-DD.md`, публиковать его.
4. Если файла нет, собирать готовый пост из встроенных infosec-шаблонов.
5. Сразу публиковать готовый пост в Telegram-канал.

После публикации дата и ID сообщений сохраняются в `state/published.json`, чтобы не отправить тот же пост повторно.

## Режим OpenRouter

Если нужен режим генерации через OpenRouter:

```env
CONTENT_SOURCE=openrouter
OPENROUTER_API_KEY=ваш_openrouter_api_key
OPENROUTER_MODEL=google/gemini-2.5-flash
```

Можно выбрать другую модель из каталога OpenRouter. Для бесплатных моделей обычно используется суффикс `:free`, если модель доступна в free-варианте.

## Режим Gemini

Если нужен режим генерации через Gemini API:

```env
CONTENT_SOURCE=gemini
GEMINI_API_KEY=ваш_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash
```

Gemini API key можно получить в Google AI Studio.

## Режим OpenAI

Если позже нужен режим генерации через OpenAI API:

```env
CONTENT_SOURCE=openai
OPENAI_API_KEY=sk-...
```
