from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import os

# ============ НАСТРОЙКА ============
app = Flask(__name__)
app.config['SECRET_KEY'] = 'svoi-secret-key-change-me-later'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///svoi.db'
).replace('postgres://', 'postgresql+psycopg://').replace('postgresql://', 'postgresql+psycopg://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# ============ МОДЕЛИ БАЗЫ ДАННЫХ ============
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(20), unique=True, nullable=False)
    users = db.relationship('User', backref='group', lazy=True)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    user = db.relationship('User', backref='messages')


# ============ ЗАГРУЗКА ПОЛЬЗОВАТЕЛЯ ============
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============ РОУТЫ ============
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.is_online = True
            db.session.commit()
            return redirect(url_for('chat'))
        else:
            flash('Неверный логин или пароль')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        invite_code = request.form.get('invite_code')

        if User.query.filter_by(username=username).first():
            flash('Такое имя уже занято')
            return redirect(url_for('register'))

        group = Group.query.filter_by(invite_code=invite_code).first()
        if not group:
            flash('Неверный код приглашения')
            return redirect(url_for('register'))

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            group_id=group.id
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('chat'))

    return render_template('login.html', register=True)


@app.route('/chat')
@login_required
def chat():
    messages = Message.query.filter_by(group_id=current_user.group_id).order_by(Message.timestamp).all()
    users = User.query.filter_by(group_id=current_user.group_id).all()
    return render_template('chat.html', messages=messages, users=users)


@app.route('/logout')
@login_required
def logout():
    current_user.is_online = False
    db.session.commit()
    logout_user()
    return redirect(url_for('login'))


# ============ СОКЕТЫ (РЕАЛТАЙМ ЧАТ) ============
@socketio.on('send_message')
def handle_message(data):
    if not current_user.is_authenticated:
        return

    msg = Message(
        text=data['text'],
        user_id=current_user.id,
        group_id=current_user.group_id
    )
    db.session.add(msg)
    db.session.commit()

    emit('new_message', {
        'username': current_user.username,
        'text': data['text'],
        'timestamp': msg.timestamp.strftime('%H:%M')
    }, broadcast=True)


# ============ ЗАПУСК ============
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not Group.query.first():
            test_group = Group(name='Тестовая группа', invite_code='SVOI2025')
            db.session.add(test_group)
            db.session.commit()
            print('✅ Создана тестовая группа. Код приглашения: SVOI2025')

    socketio.run(app, debug=True, host='0.0.0.0', port=5000)