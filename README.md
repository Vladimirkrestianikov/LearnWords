# LearnWords

Telegram-бот для изучения английских слов. Подбирает слова под ваш уровень и темы,
показывает карточки с примерами, проверяет ответы с помощью OpenAI и напоминает
повторять слова по алгоритму интервального повторения SM-2.

Стек: Python 3.12+, aiogram 3, OpenAI API, SQLAlchemy 2 (async) + SQLite, APScheduler.

## Возможности

- **Изучение слов** — карточки со словом, переводом, примером и синонимами под уровень A1–C2 и выбранные темы.
- **Тесты 7 видов** — перевод EN→RU и RU→EN, выбор варианта, пропущенное слово, своё предложение, перевод предложения, значение в контексте. Ответы проверяет ИИ: учитывает синонимы и опечатки, объясняет ошибки.
- **Повторение SM-2** — слова возвращаются через растущие интервалы (10 минут, 1 день, 3 дня, неделя и т.д.); сложные слова повторяются чаще.
- **Словари** — свои коллекции слов, избранное, тест по словарю, экспорт в TXT и CSV.
- **Импорт** — загрузка слов из текста, TXT, DOCX, PDF, CSV, XLSX с предпросмотром перед сохранением.
- **Прогресс и достижения** — точность ответов, серии дней, опыт (XP), уровни.
- **Админ-панель** — пользователи, общая статистика, общие словари, выбор модели OpenAI, рассылка.

## Быстрый старт

### 1. Что понадобится

- Python 3.12 или новее (`python3 --version`)
- Токен Telegram-бота — создайте бота у [@BotFather](https://t.me/BotFather) командой `/newbot`
- Ключ OpenAI API — [platform.openai.com/api-keys](https://platform.openai.com/api-keys) (на аккаунте должен быть баланс)
- Свой Telegram ID для доступа к админ-панели — узнать можно у [@userinfobot](https://t.me/userinfobot)

### 2. Установка

```bash
git clone https://github.com/<ваш-логин>/LearnWords.git
cd LearnWords
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Настройка

```bash
cp .env.example .env
```

Откройте `.env` и впишите свои значения:

| Переменная | Что это |
|---|---|
| `BOT_TOKEN` | Токен от @BotFather |
| `OPENAI_API_KEY` | Ключ OpenAI |
| `OPENAI_MODEL` | Модель, по умолчанию `gpt-4o-mini` |
| `ADMIN_IDS` | Telegram ID администраторов через запятую |
| `DATABASE_URL` | Путь к базе, по умолчанию `sqlite+aiosqlite:///data/learnwords.db` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `MAX_UPLOAD_SIZE_MB` | Максимальный размер файла для импорта |
| `RATE_LIMIT_SECONDS` | Минимальная пауза между сообщениями пользователя |

Файл `.env` содержит секреты и не попадает в git (он в `.gitignore`). Никогда не вписывайте реальные ключи в `.env.example`.

### 4. Запуск

```bash
python -m learnwords.bot
```

База данных создаётся автоматически при первом запуске в папке `data/`. Когда в консоли появится строка
`LearnWords is fully initialized and ready.`, откройте бота в Telegram и отправьте `/start`.

Остановить бота — `Ctrl+C`.

## Как пользоваться

Главное меню внизу экрана:

- **Изучать слова** — урок из нескольких карточек. На первой карточке есть подсказка по кнопкам: «Знаю», «Сложное», ☆ (избранное), «Тест», «Далее →». После последней карточки начинается короткий тест.
- **Повторение** — слова, которым подошёл срок повторения, и отдельно сложные слова.
- **Словари**, **Импорт**, **Прогресс**, **Достижения**, **Настройки** (уровень, темы, цель на день, язык объяснений), **Помощь**.

Во время теста ответ пишется обычным сообщением в чат, либо выбирается кнопкой, если вопрос с вариантами.
Отменить любое действие — `/cancel`.

## Структура проекта

```
learnwords/
├── bot.py            точка входа
├── config/           настройки из .env
├── database/         модели, репозитории, миграции Alembic
├── handlers/         обработчики: старт, обучение, словари, импорт, настройки, админка
├── keyboards/        клавиатуры
├── middlewares/      авторизация, сессия БД, антиспам
├── services/         логика: OpenAI, обучение, повторение, импорт, статистика
├── scheduler/        напоминания о повторении
├── schemas/          схемы ответов OpenAI
├── states/           состояния диалогов (FSM)
└── utils/            парсер файлов, SM-2, логгер
tests/                тесты pytest
data/                 база SQLite (не в git)
logs/                 логи (не в git)
```

## Тесты

```bash
python -m pytest
```

## Запуск на сервере

Бот работает через long polling, поэтому ему не нужен домен или открытые порты — подойдёт любой VPS.
Самый простой способ держать его запущенным постоянно — сервис systemd. Пример `/etc/systemd/system/learnwords.service`:

```ini
[Unit]
Description=LearnWords Telegram bot
After=network-online.target

[Service]
WorkingDirectory=/home/<user>/LearnWords
ExecStart=/home/<user>/LearnWords/.venv/bin/python -m learnwords.bot
Restart=always
User=<user>

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now learnwords
journalctl -u learnwords -f      # смотреть логи
```

Одновременно должен работать только один экземпляр бота с одним токеном — иначе Telegram вернёт ошибку `Conflict`.

## Резервная копия

Все данные лежат в `data/learnwords.db`. Копию можно сделать так (бот при этом может работать):

```bash
sqlite3 data/learnwords.db ".backup 'data/backup_$(date +%Y%m%d).db'"
```
