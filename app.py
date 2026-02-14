import eventlet
eventlet.monkey_patch()

# Теперь все остальное
import os
import threading
import asyncio
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO
from twitch_bot import Bot

app = Flask(__name__)
app.config['SECRET_KEY'] = 'osu_request_bot_key_99'

# База данных
db_path = '/etc/data/database.db' if os.path.exists('/etc/data') else 'database.db'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- МОДЕЛИ ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # Связь с настройками
    config = db.relationship('Config', backref='owner', uselist=False)

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    token = db.Column(db.String(200))
    channel = db.Column(db.String(100))
    osu_client_id = db.Column(db.String(100))
    osu_client_secret = db.Column(db.String(100))
    osu_username = db.Column(db.String(100))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- ЛОГИКА БОТА ---
active_bots = {} # Храним запущенных ботов по user_id

def bot_to_web_callback(user_id, chatter, map_info):
    socketio.emit('new_request', {
        'user': chatter,
        'map_name': map_info.get('map_name'),
        'bg_url': map_info.get('bg_url'),
        'details': map_info.get('text'),
        'stars': map_info.get('stars')
    }, room=str(user_id)) # Отправляем только владельцу

def run_bot_worker(user_id, config_dict):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = Bot(
        token=config_dict['token'],
        channel=config_dict['channel'],
        app_callback=lambda chatter, map_info, msg: bot_to_web_callback(user_id, chatter, map_info),
        osu_config=config_dict
    )
    active_bots[user_id] = bot
    bot.run()

# --- МАРШРУТЫ ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user:
            return "Пользователь уже существует"
        new_user = User(
            username=request.form.get('username'),
            password=generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        return "Неверные данные"
    return render_template('login.html')

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

@app.route('/settings')
@login_required
def settings():
    config = current_user.config or Config(user_id=current_user.id)
    return render_template('settings.html', config=config)

@app.route('/save_config', methods=['POST'])
@login_required
def save_config():
    data = request.json
    config = current_user.config
    if not config:
        config = Config(user_id=current_user.id)
        db.session.add(config)
    
    config.token = data.get('token')
    config.channel = data.get('channel')
    config.osu_client_id = data.get('osu_client_id')
    config.osu_client_secret = data.get('osu_client_secret')
    config.osu_username = data.get('osu_username')
    db.session.commit()
    
    # Запуск бота для конкретного юзера
    c_dict = {'token': config.token, 'channel': config.channel, 'osu_client_id': config.osu_client_id, 'osu_client_secret': config.osu_client_secret, 'osu_username': config.osu_username}
    threading.Thread(target=run_bot_worker, args=(current_user.id, c_dict), daemon=True).start()
    
    return jsonify({"status": "success"})

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)