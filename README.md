# 🤖 Gemini 2.5-flash Telegram Bot

Telegram бот с интеграцией Gemini 2.5-flash через OpenRouter API.

## Возможности:
- 💬 Контекстные диалоги с ИИ
- 🖼️ Анализ изображений
- 📄 Работа с файлами (PDF, TXT, JSON)
- 🧠 Память разговора

## Деплой на Railway:

1. Форкните репозиторий
2. Подключите к Railway.app
3. Добавьте переменные окружения:
   - `BOT_TOKEN` - токен от @BotFather
   - `OPENROUTER_API_KEY` - ключ от OpenRouter
   - `ADMIN_CHAT_ID` - ваш chat_id (опционально)

## Получение токенов:

### Telegram Bot Token:
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

### OpenRouter API Key:
1. Регистрируйтесь на https://openrouter.ai
2. Перейдите в Keys
3. Создайте новый ключ
4. Скопируйте ключ

## Команды бота:
- `/start` - Запуск и приветствие
- `/help` - Помощь
- `/clear` - Очистка истории
- `/status` - Статус бота

## Поддерживаемые файлы:
- **Изображения:** JPG, PNG, GIF, WebP
- **Документы:** TXT, PDF, JSON, CSV, HTML

Автор: Created with Claude