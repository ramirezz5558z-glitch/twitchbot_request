import os
import threading
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from twitch_bot import TwitchBot  # Твой файл с ботом

app = Flask(__name__)
app.config['SECRET_KEY'] = 'osu_bot_secret_key'

# Настройка базы данных (путь /etc/data/ для Render Disk)
if os.path.exists('/etc/data'):
    db_path = '/etc/data/database.db'
else:
    db_path = 'database.db'

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Глобальная переменная для хранения экземпляра бота
twitch_bot_instance = None
bot_thread = None

# --- МОДЕЛЬ ДАННЫХ ---
class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(200))
    channel = db.Column(db.String(100))
    osu_client_id = db.Column(db.String(100))
    osu_client_secret = db.Column(db.String(100))
    osu_username = db.Column(db.String(100))

# Создание БД
with app.app_context():
    db.create_all()

# --- ЛОГИКА БОТА ---
def start_bot_thread(config_data):
    global twitch_bot_instance, bot_thread
    
    # Если бот уже запущен, нам нужно его остановить (в twitch_bot.py должен быть метод stop)
    if twitch_bot_instance:
        try:
            twitch_bot_instance.stop()
        except:
            pass

    # Создаем и запускаем бота
    twitch_bot_instance = TwitchBot(config_data, socketio)
    bot_thread = threading.Thread(target=twitch_bot_instance.run)
    bot_thread.daemon = True
    bot_thread.start()
    print(f"Бот запущен для канала: {config_data.channel}")

# --- МАРШРУТЫ (ROUTES) ---

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/settings')
def settings():
    config = Config.query.get(1)
    return render_template('settings.html', config=config)

@app.route('/obs')
def obs():
    return render_template('obs.html')

@app.route('/save_config', methods=['POST'])
def save_config():
    data = request.json
    config = Config.query.get(1)
    
    if not config:
        config = Config(id=1)
        db.session.add(config)
    
    config.token = data.get('token')
    config.channel = data.get('channel')
    config.osu_client_id = data.get('osu_client_id')
    config.osu_client_secret = data.get('osu_client_secret')
    config.osu_username = data.get('osu_username')
    
    db.session.commit()
    
    # Перезапускаем бота с новыми настройками
    start_bot_thread(config)
    
    return jsonify({"status": "success", "message": "Settings saved and bot restarted"})

    @app.route('/login/osu')
def login_osu():
    # Отправляем пользователя на osu! за разрешением
    osu_url = (
        f"https://osu.ppy.sh/oauth/authorize?client_id={OSU_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify"
    )
    return redirect(osu_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    # Обмениваем код на токен доступа
    data = {
        'client_id': OSU_CLIENT_ID,
        'client_secret': OSU_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }
    r = requests.post('https://osu.ppy.sh/oauth/token', data=data).json()
    
    # Получаем инфо о пользователе (его ник и ID)
    headers = {'Authorization': f"Bearer {r['access_token']}"}
    user_data = requests.get('https://osu.ppy.sh/api/v2/me', headers=headers).json()
    
    # Сохраняем в сессию, что он вошел
    session['user_id'] = user_data['id']
    session['username'] = user_data['username']
    
    return redirect('/') # Ведем в панель управления

# --- ОБРАБОТКА СОБЫТИЙ SOCKET.IO ---

@socketio.on('bot_action')
def handle_bot_action(data):
    # Отправка сообщения в чат через бота
    if twitch_bot_instance:
        twitch_bot_instance.send_message(data.get('message'))

@socketio.on('set_current_track')
def handle_set_track(data):
    # Пробрасываем данные из Dash в OBS
    emit('update_obs', data, broadcast=True)

@socketio.on('mark_obs_done')
def handle_obs_done():
    emit('signal_obs_done', broadcast=True)

@socketio.on('mark_obs_rejected')
def handle_obs_rejected():
    emit('signal_obs_rejected', broadcast=True)

# Автозапуск бота при старте сервера, если настройки уже есть
with app.app_context():
    existing_config = Config.query.get(1)
    if existing_config and existing_config.token and existing_config.channel:
        start_bot_thread(existing_config)

if __name__ == '__main__':
    # На локалке запускаем так, на Render будет через gunicorn
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
