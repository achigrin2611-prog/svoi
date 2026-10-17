import eventlet
eventlet.monkey_patch(socket=True, select=True, time=True, thread=True, os=True)

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import string

# ============ НАСТРОЙКА ============
app = Flask(__name__)
app.config['SECRET_KEY'] = 'svoi-secret-key-change-me-later'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///svoi.db'
).replace('postgres://', 'postgresql+psycopg://').replace('postgresql://', 'postgresql+psycopg://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# ============ ГЕНЕРАЦИЯ КОДА ============
def generate_invite_code():
    while True:
        code = 'SVOI-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if not Group.query.filter_by(invite_code=code).first():
            return code


# ============ МОДЕЛИ ============
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    memberships = db.relationship('Membership', backref='user', cascade='all, delete-orphan')


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(20), unique=True, nullable=False)
    memberships = db.relationship('Membership', backref='group', cascade='all, delete-orphan')


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    __table_args__ = (db.UniqueConstraint('user_id', 'group_id', name='unique_membership'),)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_edited = db.Column(db.Boolean, default=False)
    reply_to_id = db.Column(db.Integer, nullable=True)
    reply_to_text = db.Column(db.Text, nullable=True)
    reply_to_user = db.Column(db.String(50), nullable=True)
    user = db.relationship('User', backref='messages')
    reactions = db.relationship('Reaction', backref='message', cascade='all, delete-orphan')


class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emoji = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    user = db.relationship('User', backref='reactions')


# ============ ЗАГРУЗКА ПОЛЬЗОВАТЕЛЯ ============
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============ РОУТЫ ============
@app.route('/')
@login_required
def index():
    memberships = Membership.query.filter_by(user_id=current_user.id).all()
    groups = []
    for m in memberships:
        group = Group.query.get(m.group_id)
        if group:
            last_msg = Message.query.filter_by(group_id=group.id).order_by(Message.timestamp.desc()).first()
            groups.append({
                'group': group,
                'last_message': last_msg.text[:50] if last_msg else 'Нет сообщений',
                'last_time': last_msg.timestamp.strftime('%H:%M') if last_msg else ''
            })
    return render_template('groups.html', groups=groups)


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
            return redirect(url_for('index'))
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
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        membership = Membership(user_id=user.id, group_id=group.id)
        db.session.add(membership)
        db.session.commit()

        login_user(user)
        return redirect(url_for('index'))

    return render_template('login.html', register=True)


@app.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        group_name = request.form.get('group_name', '').strip()

        if not group_name:
            flash('Введи название')
            return redirect(url_for('create_group'))

        invite_code = generate_invite_code()
        new_group = Group(name=group_name, invite_code=invite_code)
        db.session.add(new_group)
        db.session.commit()

        membership = Membership(user_id=current_user.id, group_id=new_group.id)
        db.session.add(membership)
        db.session.commit()

        return redirect(url_for('chat', group_id=new_group.id))

    return render_template('create_group.html')


@app.route('/register_new', methods=['GET', 'POST'])
def register_new():
    if request.method == 'POST':
        group_name = request.form.get('group_name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not group_name or not username or not password:
            flash('Заполни все поля')
            return redirect(url_for('register_new'))

        if User.query.filter_by(username=username).first():
            flash('Такое имя уже занято')
            return redirect(url_for('register_new'))

        invite_code = generate_invite_code()
        new_group = Group(name=group_name, invite_code=invite_code)
        db.session.add(new_group)
        db.session.commit()

        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        membership = Membership(user_id=user.id, group_id=new_group.id)
        db.session.add(membership)
        db.session.commit()

        login_user(user)
        return redirect(url_for('chat', group_id=new_group.id))

    return render_template('register_new.html')


@app.route('/join', methods=['GET', 'POST'])
@login_required
def join_group():
    if request.method == 'POST':
        invite_code = request.form.get('invite_code', '').strip()

        group = Group.query.filter_by(invite_code=invite_code).first()
        if not group:
            flash('Неверный код')
            return redirect(url_for('join_group'))

        existing = Membership.query.filter_by(user_id=current_user.id, group_id=group.id).first()
        if existing:
            return redirect(url_for('chat', group_id=group.id))

        membership = Membership(user_id=current_user.id, group_id=group.id)
        db.session.add(membership)
        db.session.commit()

        return redirect(url_for('chat', group_id=group.id))

    return render_template('join.html')


@app.route('/chat/<int:group_id>')
@login_required
def chat(group_id):
    membership = Membership.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not membership:
        abort(403)

    group = Group.query.get_or_404(group_id)
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.timestamp).all()

    memberships = Membership.query.filter_by(group_id=group_id).all()
    users = [User.query.get(m.user_id) for m in memberships]

    reactions_data = {}
    for msg in messages:
        reactions = Reaction.query.filter_by(message_id=msg.id).all()
        counts = {}
        for r in reactions:
            counts[r.emoji] = counts.get(r.emoji, 0) + 1
        reactions_data[msg.id] = counts

    return render_template(
        'chat.html',
        group=group,
        messages=messages,
        users=users,
        reactions_data=reactions_data
    )


@app.route('/logout')
@login_required
def logout():
    current_user.is_online = False
    db.session.commit()
    logout_user()
    return redirect(url_for('login'))


# ============ СОКЕТЫ ============
@socketio.on('join')
def on_join(data):
    group_id = data['group_id']
    membership = Membership.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not membership:
        return
    room = f'group_{group_id}'
    join_room(room)


@socketio.on('send_message')
def handle_message(data):
    if not current_user.is_authenticated:
        return

    group_id = data['group_id']
    membership = Membership.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not membership:
        return

    reply_to_id = data.get('reply_to_id')
    reply_to_text = None
    reply_to_user = None

    if reply_to_id:
        original = Message.query.get(reply_to_id)
        if original and original.group_id == group_id:
            reply_to_text = original.text[:100]
            reply_to_user = original.user.username

    msg = Message(
        text=data['text'],
        user_id=current_user.id,
        group_id=group_id,
        reply_to_id=reply_to_id,
        reply_to_text=reply_to_text,
        reply_to_user=reply_to_user
    )
    db.session.add(msg)
    db.session.commit()

    room = f'group_{group_id}'
    emit('new_message', {
        'id': msg.id,
        'username': current_user.username,
        'text': data['text'],
        'timestamp': msg.timestamp.strftime('%H:%M'),
        'user_id': current_user.id,
        'reply_to_id': reply_to_id,
        'reply_to_text': reply_to_text,
        'reply_to_user': reply_to_user
    }, to=room)


@socketio.on('toggle_reaction')
def handle_reaction(data):
    if not current_user.is_authenticated:
        return

    message_id = data['message_id']
    emoji = data['emoji']

    msg = Message.query.get(message_id)
    if not msg:
        return

    membership = Membership.query.filter_by(user_id=current_user.id, group_id=msg.group_id).first()
    if not membership:
        return

    existing = Reaction.query.filter_by(
        user_id=current_user.id,
        message_id=message_id,
        emoji=emoji
    ).first()

    if existing:
        db.session.delete(existing)
        action = 'removed'
    else:
        new_reaction = Reaction(emoji=emoji, user_id=current_user.id, message_id=message_id)
        db.session.add(new_reaction)
        action = 'added'

    db.session.commit()

    reactions = Reaction.query.filter_by(message_id=message_id).all()
    counts = {}
    for r in reactions:
        counts[r.emoji] = counts.get(r.emoji, 0) + 1

    room = f'group_{msg.group_id}'
    emit('reaction_updated', {
        'message_id': message_id,
        'counts': counts,
        'action': action,
        'user_id': current_user.id,
        'emoji': emoji
    }, to=room)


@socketio.on('delete_message')
def handle_delete(data):
    if not current_user.is_authenticated:
        return

    message_id = data['message_id']
    msg = Message.query.get(message_id)
    if not msg or msg.user_id != current_user.id:
        return

    group_id = msg.group_id
    db.session.delete(msg)
    db.session.commit()

    room = f'group_{group_id}'
    emit('message_deleted', {'message_id': message_id}, to=room)


@socketio.on('edit_message')
def handle_edit(data):
    if not current_user.is_authenticated:
        return

    message_id = data['message_id']
    new_text = data['text'].strip()
    if not new_text:
        return

    msg = Message.query.get(message_id)
    if not msg or msg.user_id != current_user.id:
        return

    msg.text = new_text
    msg.is_edited = True
    db.session.commit()

    room = f'group_{msg.group_id}'
    emit('message_edited', {'message_id': message_id, 'text': new_text}, to=room)


# ============ ИНИЦИАЛИЗАЦИЯ БД ============
def init_db():
    with app.app_context():
        db.create_all()
        if not Group.query.first():
            test_group = Group(name='Тестовая группа', invite_code='SVOI2025')
            db.session.add(test_group)
            db.session.commit()
            print('✅ Создана тестовая группа: SVOI2025')


# ============ ЗАПУСК ============
if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)