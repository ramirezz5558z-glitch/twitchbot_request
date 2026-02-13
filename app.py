import eventlet
eventlet.monkey_patch()  # КРИТИЧНО: должно быть первой строкой

import os
import threading
import asyncio
from flask import Flask, render_template, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from twitch_bot import Bot  # Импортируем класс Bot из twitch_bot.py

app = Flask(__name__)
app.config['SECRET_KEY'] = 'osu_bot_secret_key_1337'

# Путь к базе данных
db_path = '/etc/data/database.db' if os.path.exists('/etc/data') else 'database.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Глобальные переменные
twitch_bot_instance = None

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(200))
    channel = db.Column(db.String(100))
    osu_client_id = db.Column(db.String(100))
    osu_client_secret = db.Column(db.String(100))
    osu_username = db.Column(db.String(100))

with app.app_context():
    db.create_all()

def bot_to_web_callback(user, map_info, raw_msg):
    """Вызывается ботом, когда в чате найдена ссылка"""
    socketio.emit('new_request', {
        'user': user,
        'map_name': map_info.get('map_name'),
        'bg_url': map_info.get('bg_url'),
        'details': map_info.get('text'),
        'stars': map_info.get('stars')
    })

def run_bot_worker(config_dict):
    """Функция для работы бота в отдельном потоке"""
    global twitch_bot_instance
    print(f"🚀 Запуск потока бота для канала: {config_dict['channel']}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        twitch_bot_instance = Bot(
            token=config_dict['token'],
            channel=config_dict['channel'],
            app_callback=bot_to_web_callback,
            osu_config=config_dict
        )
        twitch_bot_instance.run()
    except Exception as e:
        print(f"❌ Ошибка в потоке бота: {e}")

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/settings')
def settings():
    config = Config.query.get(1)
    return render_template('settings.html', config=config)

@app.route('/save_config', methods=['POST'])
def save_config():
    data = request.json
    config = Config.query.get(1) or Config(id=1)
    
    config.token = data.get('token')
    config.channel = data.get('channel')
    config.osu_client_id = data.get('osu_client_id')
    config.osu_client_secret = data.get('osu_client_secret')
    config.osu_username = data.get('osu_username')
    
    if not Config.query.get(1): db.session.add(config)
    db.session.commit()
    
    # Перезапуск бота
    c_dict = {
        'token': config.token, 'channel': config.channel,
        'osu_client_id': config.osu_client_id, 'osu_client_secret': config.osu_client_secret,
        'osu_username': config.osu_username
    }
    threading.Thread(target=run_bot_worker, args=(c_dict,), daemon=True).start()
    
    return jsonify({"status": "success"})

# Автозапуск при старте сервера
with app.app_context():
    conf = Config.query.get(1)
    if conf and conf.token and conf.channel:
        c_dict = {
            'token': conf.token, 'channel': conf.channel,
            'osu_client_id': conf.osu_client_id, 'osu_client_secret': conf.osu_client_secret,
            'osu_username': conf.osu_username
        }
        threading.Thread(target=run_bot_worker, args=(c_dict,), daemon=True).start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)