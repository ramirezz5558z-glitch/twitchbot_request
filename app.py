from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import json
import os
import threading
import asyncio
from twitch_bot import Bot

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

CONFIG_FILE = "config.json"
twitch_bot = None

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

# --- РОУТЫ ---

@app.route('/')
def dashboard():
    # Главная страница (с фоном)
    return render_template('dashboard.html', config=load_config())

@app.route('/obs')
def obs_widget():
    # Виджет для OBS
    return render_template('obs.html')

@app.route('/settings')
def settings():
    # Настройки (с фоном)
    return render_template('settings.html', config=load_config())

@app.route('/save_config', methods=['POST'])
def save_config():
    data = request.json
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return jsonify({"status": "success"})

# --- НОВОЕ: Обратная связь ---
@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    data = request.json
    msg = data.get('message', '')
    contact = data.get('contact', '')
    
    # Сохраняем отзыв в файл
    with open("feedback.txt", "a", encoding="utf-8") as f:
        f.write(f"--- FEEDBACK ---\nContact: {contact}\nMessage: {msg}\n\n")
        
    print(f"📩 ПОЛУЧЕН ОТЗЫВ: {msg}")
    return jsonify({"status": "success"})

# --- СОКЕТЫ ---

@socketio.on('set_current_track')
def handle_current_track(data):
    socketio.emit('update_obs', data)

@socketio.on('mark_obs_done')
def handle_obs_done():
    socketio.emit('signal_obs_done')

@socketio.on('mark_obs_rejected')
def handle_obs_rejected():
    socketio.emit('signal_obs_rejected')

@socketio.on('bot_action')
def handle_bot_action(json_data):
    global twitch_bot
    if twitch_bot and twitch_bot.loop:
        try:
            asyncio.run_coroutine_threadsafe(
                twitch_bot.send_chat_message(json_data.get('message')), 
                twitch_bot.loop
            )
        except Exception as e:
            print(f"Chat error: {e}")

# --- ЗАПУСК ---

def run_bot_thread():
    print("--- [ПОТОК БОТА] Инициализация... ---")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    config = load_config()
    token = config.get('token', '')
    if token and not token.startswith('oauth:'):
        token = f"oauth:{token}"

    if not token or not config.get('channel'):
        print("--- [ПОТОК БОТА] Жду настройки... ---")
        return

    global twitch_bot
    try:
        twitch_bot = Bot(
            token=token,
            channel=config['channel'],
            app_callback=bot_callback,
            allowed_domains=["osu.ppy.sh"],
            osu_config=config
        )
        twitch_bot.loop = loop
        print(f"--- [ПОТОК БОТА] Вход на канал {config['channel']}... ---")
        loop.run_until_complete(twitch_bot.start())
    except Exception as e:
        print(f"--- [ПОТОК БОТА] ОШИБКА: {e} ---")

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    threading.Thread(target=run_bot_thread, daemon=True).start()
    
    # Получаем порт от сервера (для Render), или используем 5050 для теста
    port = int(os.environ.get("PORT", 5050))
    
    print(f"--- [СЕРВЕР] Запуск на порту {port} ---")
    # host='0.0.0.0' обязателен для серверов!
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)
