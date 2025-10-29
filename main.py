
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Email
from werkzeug.security import generate_password_hash, check_password_hash
from replit import db
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or 'your-secret-key-here'

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

@app.route('/')
def index():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        if not password:
            flash('Пароль обязателен')
            return render_template('register.html', form=form)
        
        if db.get(f"user_{username}"):
            flash('Пользователь с таким именем уже существует')
            return render_template('register.html', form=form)
        
        db[f"user_{username}"] = {
            'password': generate_password_hash(password)
        }
        
        flash('Регистрация прошла успешно!')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        if not password:
            flash('Пароль обязателен')
            return render_template('login.html', form=form)
        
        user_data = db.get(f"user_{username}")
        if user_data and check_password_hash(user_data['password'], password):
            session['username'] = username
            # Устанавливаем статус "В работе" при входе
            db[f"user_status_{username}"] = {
                'status': 'В работе',
                'last_seen': datetime.now().isoformat()
            }
            flash('Вы успешно вошли в систему!')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    username = session.get('username')
    if username:
        # Устанавливаем статус "Не в сети" при выходе
        db[f"user_status_{username}"] = {
            'status': 'Не в сети',
            'last_seen': datetime.now().isoformat()
        }
    session.pop('username', None)
    flash('Вы вышли из системы')
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    tasks = db.get(f"tasks_{username}", [])
    return render_template('profile.html', username=username, tasks=tasks)

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    task_text = request.form.get('task')
    if task_text:
        username = session['username']
        tasks = db.get(f"tasks_{username}", [])
        
        new_task = {
            'id': len(tasks) + 1,
            'text': task_text,
            'completed': False
        }
        
        tasks.append(new_task)
        db[f"tasks_{username}"] = tasks
        flash('Задача успешно добавлена!')
    
    return redirect(url_for('profile'))

@app.route('/toggle_task/<int:task_id>')
def toggle_task(task_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    tasks = db.get(f"tasks_{username}", [])
    
    for task in tasks:
        if task['id'] == task_id:
            task['completed'] = not task['completed']
            break
    
    db[f"tasks_{username}"] = tasks
    return redirect(url_for('profile'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    tasks = db.get(f"tasks_{username}", [])
    
    tasks = [task for task in tasks if task['id'] != task_id]
    db[f"tasks_{username}"] = tasks
    flash('Задача удалена!')
    
    return redirect(url_for('profile'))

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    message_text = request.form.get('message')
    if message_text:
        username = session['username']
        messages = db.get('chat_messages', [])
        
        new_message = {
            'id': len(messages) + 1,
            'username': username,
            'message': message_text,
            'timestamp': __import__('datetime').datetime.now().strftime('%H:%M')
        }
        
        messages.append(new_message)
        # Keep only last 50 messages
        if len(messages) > 50:
            messages = messages[-50:]
        
        db['chat_messages'] = messages
    
    return redirect(url_for('index'))

@app.route('/get_messages')
def get_messages():
    if 'username' not in session:
        return {'messages': []}
    
    messages = db.get('chat_messages', [])
    # Convert ObservedDict objects to regular dictionaries for JSON serialization
    regular_messages = []
    for msg in messages:
        regular_messages.append({
            'id': msg.get('id', ''),
            'username': msg.get('username', ''),
            'message': msg.get('message', ''),
            'timestamp': msg.get('timestamp', '')
        })
    return {'messages': regular_messages}

@app.route('/update_status', methods=['POST'])
def update_status():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    username = session['username']
    data = request.get_json() or {}
    status = data.get('status')
    
    if not status:
        return jsonify({'success': False, 'error': 'Status required'}), 400
    
    db[f"user_status_{username}"] = {
        'status': status,
        'last_seen': datetime.now().isoformat()
    }
    
    return jsonify({'success': True, 'status': status})

@app.route('/get_active_users')
def get_active_users():
    if 'username' not in session:
        return jsonify({'users': []})
    
    active_users = []
    current_time = datetime.now()
    
    # Обновляем last_seen для текущего пользователя
    username = session['username']
    current_status = db.get(f"user_status_{username}", {'status': 'В работе', 'last_seen': current_time.isoformat()})
    db[f"user_status_{username}"] = {
        'status': current_status.get('status', 'В работе'),
        'last_seen': current_time.isoformat()
    }
    
    # Получаем всех пользователей
    all_keys = list(db.keys())
    for key in all_keys:
        if key.startswith('user_status_'):
            user = key[12:]  # убираем префикс 'user_status_'
            status_data = db.get(key, {})
            
            # Проверяем, был ли пользователь активен в последние 5 минут
            try:
                last_seen = datetime.fromisoformat(status_data.get('last_seen', ''))
                time_diff = current_time - last_seen
                
                # Считаем пользователя активным, если он был онлайн в последние 5 минут
                if time_diff < timedelta(minutes=5) and status_data.get('status') != 'Не в сети':
                    active_users.append({
                        'username': user,
                        'status': status_data.get('status', 'В работе')
                    })
            except:
                # Если не удалось распарсить дату, пропускаем
                pass
    
    return jsonify({'users': active_users})

@app.route('/sync_ducks', methods=['POST'])
def sync_ducks():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    username = session['username']
    data = request.get_json() or {}
    
    duck_count = data.get('duckCount', 0)
    duck_data = data.get('duckData', {})
    duck_comments = data.get('duckComments', {})
    
    # Сохраняем данные на сервере
    db[f'duckCount_{username}'] = duck_count
    db[f'duckData_{username}'] = duck_data
    db[f'duckComments_{username}'] = duck_comments
    
    return jsonify({'success': True, 'message': 'Утки синхронизированы'})

@app.route('/get_ducks')
def get_ducks():
    if 'username' not in session:
        return jsonify({'duckCount': 0, 'duckData': {}, 'duckComments': {}})
    
    username = session['username']
    
    duck_count = db.get(f'duckCount_{username}', 0)
    duck_data = db.get(f'duckData_{username}', {})
    duck_comments = db.get(f'duckComments_{username}', {})
    
    # Конвертируем ObservedDict в обычные словари
    regular_duck_data = {}
    for key, value in (duck_data.items() if duck_data else []):
        regular_duck_data[str(key)] = {
            'name': value.get('name', ''),
            'color': value.get('color', '#FFD700')
        }
    
    regular_duck_comments = {}
    for key, value in (duck_comments.items() if duck_comments else []):
        regular_duck_comments[str(key)] = str(value)
    
    return jsonify({
        'duckCount': duck_count,
        'duckData': regular_duck_data,
        'duckComments': regular_duck_comments
    })

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'admin':
            session['admin'] = True
            flash('Добро пожаловать в админ панель!')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Неверный логин или пароль администратора')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    
    # Получаем всех пользователей и их уток
    users_data = {}
    all_keys = list(db.keys())
    
    for key in all_keys:
        if key.startswith('user_'):
            username = key[5:]  # убираем префикс 'user_'
            duck_count_key = f'duckCount_{username}'
            duck_data_key = f'duckData_{username}'
            
            users_data[username] = {
                'duck_count': 0,
                'ducks': {}
            }
            
            # Получаем данные уток из localStorage (будем имитировать через db)
            if duck_count_key in db:
                users_data[username]['duck_count'] = db[duck_count_key]
            if duck_data_key in db:
                users_data[username]['ducks'] = db[duck_data_key]
    
    # Получаем сообщения чата
    chat_messages = db.get('chat_messages', [])
    
    return render_template('admin_dashboard.html', users_data=users_data, chat_messages=chat_messages)

@app.route('/admin/manage_user/<username>', methods=['POST'])
def admin_manage_user(username):
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    
    action = request.form.get('action')
    
    if action == 'add_duck':
        duck_name = request.form.get('duck_name', f'Админская утка')
        duck_color = request.form.get('duck_color', '#FFD700')
        
        # Получаем текущие данные уток пользователя
        duck_count_key = f'duckCount_{username}'
        duck_data_key = f'duckData_{username}'
        
        current_count = db.get(duck_count_key, 0)
        current_ducks = db.get(duck_data_key, {})
        
        # Добавляем новую утку
        new_count = current_count + 1
        current_ducks[str(new_count)] = {'name': duck_name, 'color': duck_color}
        
        # Сохраняем
        db[duck_count_key] = new_count
        db[duck_data_key] = current_ducks
        
        flash(f'Утка "{duck_name}" добавлена пользователю {username}')
    
    elif action == 'remove_duck':
        duck_id = request.form.get('duck_id')
        if duck_id:
            duck_count_key = f'duckCount_{username}'
            duck_data_key = f'duckData_{username}'
            duck_comments_key = f'duckComments_{username}'
            
            current_count = db.get(duck_count_key, 0)
            current_ducks = db.get(duck_data_key, {})
            current_comments = db.get(duck_comments_key, {})
            
            if duck_id in current_ducks:
                del current_ducks[duck_id]
                if duck_id in current_comments:
                    del current_comments[duck_id]
                
                # Перенумеровываем уток
                new_ducks = {}
                new_comments = {}
                new_count = 0
                
                for i, (old_id, duck_data) in enumerate(current_ducks.items(), 1):
                    new_id = str(i)
                    new_ducks[new_id] = duck_data
                    if old_id in current_comments:
                        new_comments[new_id] = current_comments[old_id]
                    new_count = i
                
                db[duck_count_key] = new_count
                db[duck_data_key] = new_ducks
                db[duck_comments_key] = new_comments
                
                flash(f'Утка удалена у пользователя {username}')
    
    elif action == 'clear_all_ducks':
        duck_count_key = f'duckCount_{username}'
        duck_data_key = f'duckData_{username}'
        duck_comments_key = f'duckComments_{username}'
        
        db[duck_count_key] = 0
        db[duck_data_key] = {}
        db[duck_comments_key] = {}
        
        flash(f'Все утки удалены у пользователя {username}')
    
    elif action == 'delete_user':
        # Удаляем пользователя и все его данные
        keys_to_delete = []
        for key in db.keys():
            if key.endswith(f'_{username}') or key == f'user_{username}':
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del db[key]
        
        flash(f'Пользователь {username} удален')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clear_chat', methods=['POST'])
def admin_clear_chat():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    
    db['chat_messages'] = []
    flash('Чат полностью очищен')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/start_workday', methods=['POST'])
def admin_start_workday():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    
    # Очищаем чат
    db['chat_messages'] = []
    
    # Добавляем системное сообщение о начале рабочего дня
    from datetime import datetime
    start_message = {
        'id': 1,
        'username': 'Система',
        'message': f'🌅 Начался новый рабочий день! Удачной работы всем! ({datetime.now().strftime("%d.%m.%Y")})',
        'timestamp': datetime.now().strftime('%H:%M')
    }
    
    db['chat_messages'] = [start_message]
    flash('Новый рабочий день начался! Чат очищен.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/mass_add_ducks', methods=['POST'])
def admin_mass_add_ducks():
    if not session.get('admin'):
        return redirect(url_for('admin_panel'))
    
    duck_name = request.form.get('duck_name', 'Подарок от администратора')
    duck_color = request.form.get('duck_color', '#FFD700')
    
    # Получаем всех пользователей
    all_keys = list(db.keys())
    users_count = 0
    
    for key in all_keys:
        if key.startswith('user_'):
            username = key[5:]
            duck_count_key = f'duckCount_{username}'
            duck_data_key = f'duckData_{username}'
            
            current_count = db.get(duck_count_key, 0)
            current_ducks = db.get(duck_data_key, {})
            
            # Добавляем новую утку
            new_count = current_count + 1
            current_ducks[str(new_count)] = {'name': duck_name, 'color': duck_color}
            
            # Сохраняем
            db[duck_count_key] = new_count
            db[duck_data_key] = current_ducks
            users_count += 1
    
    flash(f'Утка "{duck_name}" добавлена всем пользователям ({users_count} чел.)')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/get_data')
def admin_get_data():
    if not session.get('admin'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Получаем всех пользователей и их уток
    users_data = {}
    all_keys = list(db.keys())
    
    for key in all_keys:
        if key.startswith('user_') and not key.startswith('user_status_'):
            username = key[5:]  # убираем префикс 'user_'
            duck_count_key = f'duckCount_{username}'
            duck_data_key = f'duckData_{username}'
            
            duck_count = db.get(duck_count_key, 0)
            duck_data_raw = db.get(duck_data_key, {})
            
            # Конвертируем ObservedDict в обычные словари
            duck_data = {}
            for duck_id, duck_info in (duck_data_raw.items() if duck_data_raw else []):
                duck_data[str(duck_id)] = {
                    'name': duck_info.get('name', ''),
                    'color': duck_info.get('color', '#FFD700')
                }
            
            users_data[username] = {
                'duck_count': duck_count,
                'ducks': duck_data
            }
    
    # Получаем сообщения чата
    chat_messages_raw = db.get('chat_messages', [])
    chat_messages = []
    for msg in chat_messages_raw:
        chat_messages.append({
            'id': msg.get('id', ''),
            'username': msg.get('username', ''),
            'message': msg.get('message', ''),
            'timestamp': msg.get('timestamp', '')
        })
    
    # Получаем активных пользователей
    active_users_count = 0
    current_time = datetime.now()
    for key in all_keys:
        if key.startswith('user_status_'):
            status_data = db.get(key, {})
            try:
                last_seen = datetime.fromisoformat(status_data.get('last_seen', ''))
                time_diff = current_time - last_seen
                if time_diff < timedelta(minutes=5) and status_data.get('status') != 'Не в сети':
                    active_users_count += 1
            except:
                pass
    
    total_ducks = sum(user_data['duck_count'] for user_data in users_data.values())
    
    return jsonify({
        'users_data': users_data,
        'chat_messages': chat_messages,
        'stats': {
            'total_users': len(users_data),
            'total_ducks': total_ducks,
            'total_messages': len(chat_messages),
            'active_users': active_users_count
        }
    })

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Вы вышли из админ панели')
    return redirect(url_for('admin_panel'))

@app.route('/cat')
def cat_animation():
    return app.send_static_file('cat_animation.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
