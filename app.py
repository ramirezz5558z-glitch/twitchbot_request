from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import json
import os
import threading
import asyncio
from twitch_bot import Bot

app = Flask(__name__)
# Добавляем async_mode='eventlet' для стабильности на сервере
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Определяем базовую директорию, чтобы пути всегда были верными
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

twitch_bot = None
bot_thread = None

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def bot_callback(user, data):
    try:
        socketio.emit('new_request', {
            'user': user,
            'full_msg': data['full_msg'],
            'map_name': data['map_name'],
            'bg_url': data['bg_url']
        })
    except Exception as e:
        print(f"Ошибка отправки в браузер: {e}")

# --- ФУНКЦИЯ УПРАВЛЕНИЯ БОТОМ ---

def start_bot():
    global bot_thread
    # Если бот уже запущен, нам нужно его остановить (логика остановки должна быть в Bot)
    # Но для начала просто запускаем в потоке
    bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()

def run_bot_thread():
    print("--- [ПОТОК БОТА] Инициализация... ---")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    config = load_config()
    token = config.get('token', '')
    channel = config.get('channel', '')

    if not token or not channel:
        print("--- [ПОТОК БОТА] Жду настройки (токен или канал пуст)... ---")
        return

    if not token.startswith('oauth:'):
        token = f"oauth:{token}"

    global twitch_bot
    try:
        twitch_bot = Bot(
            token=token,
            channel=channel,
            app_callback=bot_callback,
            allowed_domains=["osu.ppy.sh"],
            osu_config=config
        )
        twitch_bot.loop = loop
        print(f"--- [ПОТОК БОТА] Вход на канал {channel}... ---")
        loop.run_until_complete(twitch_bot.start())
    except Exception as e:
        print(f"--- [ПОТОК БОТА] ОШИБКА: {e} ---")

# --- РОУТЫ ---

@app.route('/')
def dashboard():
    return render_template('dashboard.html', config=load_config())

@app.route('/save_config', methods=['POST'])
def save_config():
    data = request.json
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    # ПЕРЕЗАПУСК БОТА при сохранении (простейший вариант)
    print("--- Настройки обновлены, перезапуск бота... ---")
    start_bot() 
    
    return jsonify({"status": "success"})

# ... (остальные роуты оставляем как есть) ...

# --- ДЛЯ RENDER: Запуск потока при старте сервера ---
# Это сработает даже при запуске через Gunicorn
start_bot()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    print(f"--- [СЕРВЕР] Локальный запуск на порту {port} ---")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)
