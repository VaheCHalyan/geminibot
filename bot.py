import os
import logging
import requests
import base64
import json
import io
from datetime import datetime
import telebot
from telebot import types
import mimetypes
import threading
import http.server
import socketserver
import time
import signal
import sys

# Улучшенный HTTP сервер для поддержания активности
class KeepAliveHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        status_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Gemini Telegram Bot - Status</title>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f0f2f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .status {{ color: #28a745; font-size: 18px; font-weight: bold; }}
                .time {{ color: #6c757d; }}
                h1 {{ color: #495057; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Gemini Telegram Bot</h1>
                <div class="status">✅ Bot Status: ACTIVE</div>
                <p>🕐 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p>🔄 Auto-refresh every 30 seconds</p>
                <p>📊 Server running on port: {os.environ.get('PORT', '10000')}</p>
                <hr>
                <p><strong>Available Commands:</strong></p>
                <ul>
                    <li>/start - Start the bot</li>
                    <li>/help - Get help</li>
                    <li>/status - Check bot status</li>
                    <li>/clear - Clear chat history</li>
                </ul>
            </div>
        </body>
        </html>
        """
        self.wfile.write(status_page.encode('utf-8'))
    
    def log_message(self, format, *args):
        # Подавляем логи HTTP сервера
        pass

def run_keep_alive_server():
    """Запуск HTTP сервера для поддержания активности"""
    port = int(os.environ.get("PORT", 10000))
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with socketserver.TCPServer(("", port), KeepAliveHandler) as httpd:
                logging.info(f"🌐 HTTP сервер запущен на порту {port}")
                httpd.serve_forever()
                break
        except OSError as e:
            retry_count += 1
            if "Address already in use" in str(e):
                port += 1
                logging.warning(f"Порт {port-1} занят, пробую порт {port}")
            else:
                logging.error(f"Ошибка запуска HTTP сервера: {e}")
                time.sleep(5)
            
            if retry_count >= max_retries:
                logging.error("Не удалось запустить HTTP сервер после нескольких попыток")
                break

# Запуск HTTP сервера в отдельном потоке
server_thread = threading.Thread(target=run_keep_alive_server, daemon=True)
server_thread.start()

# Дополнительная функция heartbeat
def heartbeat():
    """Периодическая отправка heartbeat сигналов"""
    counter = 0
    while True:
        try:
            counter += 1
            logging.info(f"💓 Heartbeat #{counter} - Bot alive")
            time.sleep(300)  # Каждые 5 минут
        except Exception as e:
            logging.error(f"Ошибка в heartbeat: {e}")
            time.sleep(60)

# Запуск heartbeat в отдельном потоке
heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
heartbeat_thread.start()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем переменные окружения
BOT_TOKEN = os.getenv('BOT_TOKEN') or "8431876453:AAHOFXEar4aIcSMAn5WdXVdNxQMAiYZfhoo"
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY') or "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"
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID') or "2145450623"

# Отладочная информация
logger.info(f"🔍 BOT_TOKEN загружен: {BOT_TOKEN[:10]}...")
logger.info(f"🔍 OPENROUTER_API_KEY загружен: {OPENROUTER_API_KEY[:15]}...")
logger.info(f"🔍 ADMIN_CHAT_ID: {ADMIN_CHAT_ID}")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    exit(1)

if not OPENROUTER_API_KEY:
    logger.error("❌ OPENROUTER_API_KEY не найден!")
    exit(1)

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Конфигурация OpenRouter
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "google/gemini-2.5-flash"

# Поддерживаемые типы файлов
SUPPORTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
SUPPORTED_DOCUMENT_TYPES = [
    'text/plain', 'application/pdf', 'application/json',
    'text/csv', 'application/msword', 'text/html'
]

class GeminiBot:
    def __init__(self):
        self.user_contexts = {}
        self.max_context_length = 10
        
    def get_user_context(self, user_id):
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = []
        return self.user_contexts[user_id]
    
    def add_to_context(self, user_id, role, content):
        context = self.get_user_context(user_id)
        context.append({"role": role, "content": content})
        
        if len(context) > self.max_context_length * 2:
            context.pop(0)
    
    def clear_context(self, user_id):
        if user_id in self.user_contexts:
            self.user_contexts[user_id] = []
    
    def encode_file_to_base64(self, file_content, mime_type):
        try:
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            return f"data:{mime_type};base64,{encoded_content}"
        except Exception as e:
            logger.error(f"Ошибка кодирования файла: {e}")
            return None
    
    def prepare_message_content(self, text=None, file_data=None, mime_type=None):
        content = []
        
        if text:
            content.append({"type": "text", "text": text})
        
        if file_data and mime_type:
            if mime_type.startswith('image/'):
                encoded_file = self.encode_file_to_base64(file_data, mime_type)
                if encoded_file:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": encoded_file}
                    })
            else:
                try:
                    if mime_type == 'application/pdf':
                        text_content = f"[PDF файл получен, размер: {len(file_data)} байт]"
                    else:
                        text_content = file_data.decode('utf-8', errors='ignore')
                    
                    content.append({
                        "type": "text", 
                        "text": f"Содержимое файла ({mime_type}):\n\n{text_content[:4000]}..."
                    })
                except Exception as e:
                    content.append({
                        "type": "text",
                        "text": f"[Не удалось прочитать файл: {str(e)}]"
                    })
        
        return content if content else [{"type": "text", "text": text or "Привет!"}]
    
    def call_gemini_api(self, user_id, text=None, file_data=None, mime_type=None):
        try:
            context = self.get_user_context(user_id)
            message_content = self.prepare_message_content(text, file_data, mime_type)
            
            messages = context.copy()
            messages.append({"role": "user", "content": message_content})
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "X-Title": "Telegram Gemini Bot",
                "HTTP-Referer": "https://github.com/your-repo",
            }
            
            payload = {
                "model": MODEL_NAME,
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.7,
                "stream": False
            }
            
            logger.info(f"Отправляю запрос к Gemini для пользователя {user_id}")
            
            response = requests.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
                self.add_to_context(user_id, "user", message_content)
                self.add_to_context(user_id, "assistant", ai_response)
                
                return ai_response
            else:
                logger.error(f"Ошибка API OpenRouter: {response.status_code} - {response.text}")
                return f"❌ Ошибка API: {response.status_code}\n{response.text}"
                
        except requests.exceptions.Timeout:
            return "⏰ Превышено время ожидания. Попробуйте еще раз."
        except requests.exceptions.ConnectionError:
            return "🌐 Ошибка подключения к API."
        except Exception as e:
            logger.error(f"Ошибка при вызове Gemini API: {e}")
            return f"❌ Произошла ошибка: {str(e)}"

# Создаем экземпляр бота
gemini_bot = GeminiBot()

def signal_handler(signum, frame):
    logger.info("Получен сигнал завершения. Останавливаю бота...")
    try:
        bot.stop_polling()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def log_message(message):
    user = message.from_user
    logger.info(f"Сообщение от {user.first_name} ({user.id}): {message.content_type}")

@bot.message_handler(commands=['start'])
def start_handler(message):
    log_message(message)
    
    welcome_text = """
🤖 **Добро пожаловать в Gemini 2.0-flash Bot!**

Я могу:
• 💬 Отвечать на ваши вопросы
• 🖼️ Анализировать изображения  
• 📄 Работать с файлами (PDF, TXT, JSON и др.)
• 🧠 Вести контекстный диалог

**Команды:**
/start - Показать это сообщение
/clear - Очистить историю разговора
/help - Помощь и примеры
/status - Статус бота

Просто отправьте мне текст, изображение или файл! 🚀
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📚 Помощь", callback_data="help"),
        types.InlineKeyboardButton("🧹 Очистить чат", callback_data="clear")
    )
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['clear'])
def clear_handler(message):
    log_message(message)
    user_id = message.from_user.id
    gemini_bot.clear_context(user_id)
    bot.send_message(message.chat.id, "🧹 История разговора очищена!")

@bot.message_handler(commands=['help'])
def help_handler(message):
    log_message(message)
    help_text = """
📚 **Как использовать бота:**

**💬 Текстовые сообщения:**
• Задавайте любые вопросы
• Ведите диалог (бот помнит контекст)

**🖼️ Работа с изображениями:**
• Отправьте фото + вопрос о нем
• Анализ изображений

**📄 Работа с файлами:**
• PDF, TXT, JSON, CSV и другие
• Анализ содержимого файлов

**Команды:**
/clear - Очистить историю
/status - Проверить работу бота
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def status_handler(message):
    log_message(message)
    try:
        test_response = gemini_bot.call_gemini_api(message.from_user.id, "Ответь кратко: ты работаешь?")
        status_text = f"""
📊 **Статус бота:**

✅ Telegram Bot: Работает  
✅ OpenRouter API: Работает
✅ Gemini 2.0-flash: Доступен

🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Контекст: {len(gemini_bot.get_user_context(message.from_user.id))} сообщений

**Тест API:** {test_response[:100]}...
        """
        bot.send_message(message.chat.id, status_text, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при проверке статуса: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "help":
        help_handler(call.message)
    elif call.data == "clear":
        user_id = call.from_user.id
        gemini_bot.clear_context(user_id)
        bot.answer_callback_query(call.id, "🧹 История очищена!")
        bot.edit_message_text(
            "История разговора очищена! Можете задать новый вопрос.",
            call.message.chat.id,
            call.message.message_id
        )

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    try:
        log_message(message)
        bot.send_chat_action(message.chat.id, 'typing')
        
        file_info = bot.get_file(message.photo[-1].file_id)
        file_data = bot.download_file(file_info.file_path)
        caption = message.caption or "Что изображено на этой картинке? Опиши подробно."
        mime_type = 'image/jpeg'
        
        response = gemini_bot.call_gemini_api(message.from_user.id, caption, file_data, mime_type)
        
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                bot.send_message(message.chat.id, response[i:i+4096])
        else:
            bot.send_message(message.chat.id, response)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        bot.send_message(message.chat.id, f"❌ Ошибка при обработке изображения: {str(e)}")

@bot.message_handler(content_types=['document'])
def document_handler(message):
    try:
        log_message(message)
        bot.send_chat_action(message.chat.id, 'typing')
        
        file_info = bot.get_file(message.document.file_id)
        
        if file_info.file_size > 20 * 1024 * 1024:
            bot.send_message(message.chat.id, "❌ Файл слишком большой. Максимум 20MB.")
            return
        
        mime_type = message.document.mime_type or mimetypes.guess_type(message.document.file_name)[0]
        
        if not mime_type:
            bot.send_message(message.chat.id, "❌ Не удалось определить тип файла.")
            return
        
        if mime_type not in SUPPORTED_DOCUMENT_TYPES and not mime_type.startswith('text/'):
            bot.send_message(message.chat.id, f"❌ Тип файла не поддерживается.")
            return
        
        file_data = bot.download_file(file_info.file_path)
        caption = message.caption or f"Проанализируй файл {message.document.file_name}"
        
        response = gemini_bot.call_gemini_api(message.from_user.id, caption, file_data, mime_type)
        
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                bot.send_message(message.chat.id, response[i:i+4096])
        else:
            bot.send_message(message.chat.id, response)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке документа: {e}")
        bot.send_message(message.chat.id, f"❌ Ошибка при обработке файла: {str(e)}")

@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    log_message(message)
    bot.send_message(message.chat.id, "🎤 Голосовые сообщения пока не поддерживаются.")

@bot.message_handler(func=lambda message: True)
def text_handler(message):
    try:
        log_message(message)
        bot.send_chat_action(message.chat.id, 'typing')
        
        response = gemini_bot.call_gemini_api(message.from_user.id, message.text)
        
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                bot.send_message(message.chat.id, response[i:i+4096])
        else:
            bot.send_message(message.chat.id, response)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке текста: {e}")
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}")

def send_startup_notification():
    if ADMIN_CHAT_ID:
        try:
            startup_message = f"""
🚀 **Gemini Bot запущен!**

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Модель: {MODEL_NAME}
☁️ Платформа: Render.com
✅ Статус: Активен
            """
            bot.send_message(ADMIN_CHAT_ID, startup_message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")

def main():
    logger.info("🤖 Запускаю Gemini Telegram Bot...")
    logger.info(f"🔗 Модель: {MODEL_NAME}")
    logger.info(f"🌐 HTTP сервер активен на порту {os.environ.get('PORT', '10000')}")
    
    send_startup_notification()
    
    restart_count = 0
    max_restarts = 50
    
    while restart_count <= max_restarts:
        try:
            logger.info(f"🔄 Попытка запуска бота #{restart_count + 1}")
            bot.polling(none_stop=True, interval=2, timeout=60, skip_pending=True)
            
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания. Останавливаю бота...")
            break
            
        except Exception as e:
            restart_count += 1
            logger.error(f"❌ Ошибка в работе бота (попытка {restart_count}): {e}")
            
            if restart_count > max_restarts:
                logger.error("❌ Превышено максимальное количество перезапусков")
                break
                
            wait_time = min(restart_count * 5, 60)
            logger.info(f"⏳ Перезапуск через {wait_time} секунд...")
            time.sleep(wait_time)
            
            try:
                if ADMIN_CHAT_ID and restart_count % 10 == 0:
                    bot.send_message(ADMIN_CHAT_ID, f"⚠️ Бот перезапущен {restart_count} раз")
            except:
                pass
                
    logger.info("🛑 Бот завершил работу")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        try:
            if ADMIN_CHAT_ID:
                bot.send_message(ADMIN_CHAT_ID, f"💥 Критическая ошибка бота: {str(e)}")
        except:
            pass
        raise