import csv  # Убедись, что csv импортирован


@app.route('/import', methods=['POST'])
@login_required
def import_csv():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        return "Пожалуйста, выберите CSV файл", 400

    # Читаем файл
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)

    next(csv_input)  # Пропускаем строку-заголовок (City From, City To...)

    for row in csv_input:
        if len(row) >= 4:
            new_trip = Trip(
                city_from=row[0],
                city_to=row[1],
                budget_limit=int(row[2] or 0),
                days_count=int(row[3] or 1),
                user_id=current_user.id
            )
            db.session.add(new_trip)

    db.session.commit()
    return redirect(url_for('index'))


import os
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'travel-2026-final-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# --- МОДЕЛИ ДАННЫХ ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120))
    avatar = db.Column(db.String(200), default='default_avatar.png')
    bio = db.Column(db.Text)
    trips = db.relationship('Trip', backref='owner', lazy=True)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city_from = db.Column(db.String(100), nullable=False)
    city_to = db.Column(db.String(100), nullable=False)
    budget_limit = db.Column(db.Integer, default=0)
    days_count = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- ФУНКЦИЯ ПОГОДЫ ---
def get_weather(city):
    # В 2026 году используем API Яндекс.Погоды
    # API_KEY = "ВАШ_КЛЮЧ_ПОГОДЫ"
    try:
        # Здесь должна быть логика запроса requests.get(...)
        # Пока возвращаем демонстрационные данные
        return {"temp": "+22°C", "condition": "Солнечно"}
    except:
        return {"temp": "Н/Д", "condition": "нет данных"}


# --- РОУТЫ ---
@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/add_trip', methods=['POST'])
@login_required
def add_trip():
    new_trip = Trip(
        city_from=request.form.get('city_from'),
        city_to=request.form.get('city_to'),
        budget_limit=int(request.form.get('budget_limit') or 0),
        days_count=int(request.form.get('days_count') or 1),
        user_id=current_user.id
    )
    db.session.add(new_trip)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/trip/<int:trip_id>')
@login_required
def trip_details(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    # Расчет бюджета
    daily = trip.budget_limit // trip.days_count if trip.days_count > 0 else 0
    weather = get_weather(trip.city_to)

    # Рекомендации
    if daily < 3000:
        hotels, activities = "Хостелы или гостевые дома", "Бесплатные парки, прогулки, столовые"
    elif daily < 8000:
        hotels, activities = "Отели 3-4*, апартаменты", "Музеи, кафе, городские туры"
    else:
        hotels, activities = "Отели 5*, бутик-отели", "Рестораны, театры, частные гиды"

    return render_template('trip_view.html', trip=trip, daily=daily,
                           weather=weather, hotels=hotels, activities=activities)


@app.route('/api/my_trips')
@login_required
def api_trips():
    q = request.args.get('q', '').lower()
    trips = Trip.query.filter_by(user_id=current_user.id).filter(Trip.city_to.ilike(f"%{q}%")).all()
    return jsonify([{"id": t.id, "from": t.city_from, "to": t.city_to, "budget": t.budget_limit} for t in trips])


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

import requests  # Не забудь добавить в начало файла


# Функция для получения погоды
def get_yandex_weather(city_name):
    # В 2026 году для РФ это самый стабильный источник
    api_key = "ТВОЙ_КЛЮЧ_ПОГОДЫ"
    # Сначала узнаем координаты города (через Геокодер или упрощенно)
    # Для примера используем эндпоинт, который часто требует lat/lon
    # Здесь показана логика:
    try:
        # Это пример запроса, в реальности нужно передать lat/lon города
        # url = f"https://yandex.ru{lat}&lon={lon}"
        # headers = {'X-Yandex-API-Key': api_key}
        # res = requests.get(url, headers=headers).json()
        # return res['fact']['temp'], res['fact']['condition']
        return "+18°C", "Ясно"  # Заглушка, если ключа пока нет
    except:
        return "Н/Д", "нет данных"


@app.route('/trip/<int:trip_id>')
@login_required
def trip_details(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    daily = trip.budget_limit // trip.days_count if trip.days_count > 0 else 0

    # Получаем погоду для города назначения
    temp, cond = get_yandex_weather(trip.city_to)

    # Логика рекомендаций (как и была)
    if daily < 2500:
        hotels, activities = "Хостелы", "Бесплатные парки"
    elif daily < 7000:
        hotels, activities = "Отели 3*", "Музеи и кафе"
    else:
        hotels, activities = "Отели 5*", "Рестораны и театры"

    return render_template('trip_view.html',
                           trip=trip, daily=daily,
                           hotels=hotels, activities=activities,
                           temp=temp, cond=cond)


import os, io, csv
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'travel-2026-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# --- ОБНОВЛЕННАЯ МОДЕЛЬ ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120))
    avatar = db.Column(db.String(200), default='default_avatar.png')
    bio = db.Column(db.Text)
    trips = db.relationship('Trip', backref='owner', lazy=True)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city_from = db.Column(db.String(100), nullable=False)  # ОТКУДА
    city_to = db.Column(db.String(100), nullable=False)  # КУДА
    budget_limit = db.Column(db.Integer, default=0)
    days_count = db.Column(db.Integer, default=1)  # СРОК
    ticket_file = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- ОСНОВНЫЕ РОУТЫ ---
@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/add_trip', methods=['POST'])
@login_required
def add_trip():
    new_trip = Trip(
        city_from=request.form.get('city_from'),
        city_to=request.form.get('city_to'),
        budget_limit=int(request.form.get('budget_limit') or 0),
        days_count=int(request.form.get('days_count') or 1),
        user_id=current_user.id
    )
    db.session.add(new_trip)
    db.session.commit()
    return redirect(url_for('index'))


# СТРАНИЦА ПОДРОБНОСТЕЙ (НОВАЯ)
@app.route('/trip/<int:trip_id>')
@login_required
def trip_details(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    # Логика бюджета
    daily = trip.budget_limit // trip.days_count

    # Рекомендации по жилью и еде
    if daily < 2500:
        hotels = "Хостелы, придорожные мотели или аренда комнаты"
        activities = "Бесплатные парки, обзорные площадки, столовые"
    elif daily < 7000:
        hotels = "Отели 3*, апартаменты в центре"
        activities = "Городские музеи, кофейни, речные прогулки"
    else:
        hotels = "Отели 4-5*, SPA-комплексы"
        activities = "Театры, рестораны, индивидуальные экскурсии"

    return render_template('trip_view.html', trip=trip, daily=daily, hotels=hotels, activities=activities)


@app.route('/api/my_trips')
@login_required
def api_trips():
    q = request.args.get('q', '').lower()
    trips = Trip.query.filter_by(user_id=current_user.id).filter(Trip.city_to.ilike(f"%{q}%")).all()
    return jsonify(
        [{"id": t.id, "city_from": t.city_from, "city_to": t.city_to, "budget": t.budget_limit} for t in trips])


if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)
