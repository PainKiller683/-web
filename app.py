import os, io, csv, requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'travel-2026-final-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#Ключи
MAPS_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"
GEO_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"
RASP_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"
WEATHER_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"

class Waypoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_name = db.Column(db.String(200))
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    avatar = db.Column(db.String(200), default='default_avatar.png')
    bio = db.Column(db.Text)
    trips = db.relationship('Trip', backref='owner', lazy=True)


class Trip(db.Model):
    waypoints = db.relationship('Waypoint', backref='trip', lazy=True)
    id = db.Column(db.Integer, primary_key=True)
    city_from = db.Column(db.String(100), nullable=False)
    city_to = db.Column(db.String(100), nullable=False)
    budget_limit = db.Column(db.Integer, default=0)
    days_count = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_station_code(lat, lon):
    """Находит код ближайшего транспортного узла по координатам"""
    url = "https://api.rasp.yandex-net.ru/v3.0/nearest_stations/"
    params = {
        "apikey": RASP_API_KEY,
        "lat": lat,
        "lng": lon,
        "distance": 50,  # Радиус поиска в км
        "format": "json",
        "lang": "ru_RU"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        # Возвращаем код станции (тип 'station') или города (тип 'settlement')
        if data.get('stations'):
            return data['stations'][0]['code']
        return None
    except Exception as e:
        print(f"Ошибка API Расписаний (nearest): {e}")
        return None


# def get_rasp_segments(code_from, code_to):
#     if not code_from or not code_to:
#         return []
#
#     url = "https://api.rasp.yandex-net.ru/v3.0/search/ "
#     params = {
#         "apikey": RASP_API_KEY,
#         "from": code_from,
#         "to": code_to,
#         "date": datetime.now().strftime('%Y-%m-%d'),
#         "format": "json"
#     }
#     try:
#         res = requests.get(url, params=params).json()
#         return res.get('segments', [])  # Список всех найденных рейсов
#     except:
#         return []


def get_city_info(city_name):
    # 1. Получаем координаты через Геокодер
    geo_url = "https://geocode-maps.yandex.ru/v1"
    params = {"apikey": GEO_API_KEY, "geocode": city_name, "format": "json"}
    try:
        r = requests.get(geo_url, params=params).json()
        geo_object = r['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']
        pos = geo_object['Point']['pos']
        lon, lat = pos.split(' ')

        # 2. Сразу ищем код станции Яндекса по этим координатам
        rasp_url = "https://api.rasp.yandex-net.ru/v3.0/nearest_stations/"
        r_rasp = requests.get(rasp_url, params={
            "apikey": RASP_API_KEY, "lat": lat, "lng": lon, "distance": 50, "format": "json"
        }).json()

        station_code = None
        if r_rasp.get('stations'):
            station_code = r_rasp['stations'][0]['code']  # Берем самую ближайшую

        return {"lat": float(lat), "lon": float(lon), "code": station_code}
    except Exception as e:
        print(f"Ошибка геокодирования города {city_name}: {e}")
        return None


def get_weather(lat, lon):
    url = "https://yandex.ru"
    headers = {'X-Yandex-API-Key': WEATHER_API_KEY}
    try:
        r = requests.get(url, headers=headers, params={'lat': lat, 'lon': lon, 'lang': 'ru_RU'}).json()
        return {
            "temp": f"{r['fact']['temp']}°",
            "condition": r['fact']['condition'],
            "icon": r['fact']['icon']
        }
    except:
        return {"temp": "??", "condition": "нет данных", "icon": "ovc"}


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/api/my_trips')
@login_required
def api_trips():
    q = request.args.get('q', '').lower()
    # Берем поездки только текущего пользователя
    trips = Trip.query.filter_by(user_id=current_user.id).all()

    # Фильтруем, если введен поиск
    if q:
        trips = [t for t in trips if q in t.city_to.lower() or q in t.city_from.lower()]

    return jsonify([{
        "id": t.id,
        "from": t.city_from,
        "to": t.city_to,
        "budget": t.budget_limit
    } for t in trips])


@app.route('/add_trip', methods=['POST'])
@login_required
def add_trip():
    new_trip = Trip(
        city_from=request.form['city_from'],
        city_to=request.form['city_to'],
        budget_limit=int(request.form.get('budget_limit', 0) or 0),
        days_count=int(request.form.get('days_count', 1) or 1),
        user_id=current_user.id
    )
    db.session.add(new_trip)
    db.session.commit()
    # Сразу перекидываем пользователя на страницу только что созданной поездки
    return redirect(url_for('trip_details', trip_id=new_trip.id))


@app.route('/get_route_data')
@login_required
def get_route_data():
    city_from = request.args.get('from')
    city_to = request.args.get('to')

    data_from = get_city_info(city_from)
    data_to = get_city_info(city_to)

    if data_from and data_to:
        return jsonify({
            "start": {"lat": data_from['lat'], "lon": data_from['lon']},
            "end": {"lat": data_to['lat'], "lon": data_to['lon']}
        })
    return jsonify({"error": "not found"}), 404

@app.route('/delete_trip/<int:trip_id>', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    db.session.delete(trip)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/trip/<int:trip_id>')
@login_required
def trip_details(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    info_from = get_city_info(trip.city_from)
    info_to = get_city_info(trip.city_to)

    # 1. Погода
    weather = {"temp": "??", "condition": "нет данных", "icon": "ovc"}
    if info_to:
        weather = get_weather(info_to['lat'], info_to['lon'])

    # 2. Рейсы Яндекс Расписаний
    segments = []
    if info_from and info_from.get('code') and info_to and info_to.get('code'):
        try:
            r_url = "https://api.rasp.yandex-net.ru/v3.0/schedule/"
            res = requests.get(r_url, params={
                "apikey": RASP_API_KEY,
                "from": info_from['code'],
                "to": info_to['code'],
                "date": datetime.now().strftime('%Y-%m-%d')
            }).json()
            segments = res.get('segments', [])
        except:
            segments = []

    # 3. Расчет бюджета (исправляем ошибку UndefinedError)
    daily = trip.budget_limit // trip.days_count if trip.days_count > 0 else 0
    hotels = "Хостелы" if daily < 3000 else "Отели 3*" if daily < 7000 else "Отели 5*"
    acts = "Прогулки" if daily < 3000 else "Музеи" if daily < 7000 else "Гиды"

    # Считаем траты (если у вас пока нет таблицы трат, ставим 0)
    spent = 0
    rem = trip.budget_limit - spent  # Остаток
    prog = (spent / trip.budget_limit * 100) if trip.budget_limit > 0 else 0  # Прогресс-бар

    return render_template('trip_detail.html',
                           trip=trip,
                           daily=daily,
                           weather=weather,
                           hotels=hotels,
                           acts=acts,
                           segments=segments,
                           maps_key=MAPS_API_KEY,
                           coords_to=info_to,
                           spent=spent,  # Передаем spent
                           rem=rem,  # Передаем rem (исправляет вашу ошибку)
                           prog=prog)  # Передаем prog


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_routes(code_from, code_to):
    """Получает список всех рейсов между двумя кодами станций"""
    if not code_from or not code_to:
        return []

    url = "https://api.rasp.yandex-net.ru/v3.0/search/"
    params = {
        "apikey": RASP_API_KEY,
        "from": code_from,
        "to": code_to,
        "date": datetime.now().strftime('%Y-%m-%d'),
        "format": "json",
        "lang": "ru_RU",
        "limit": 10  # Ограничим до 10 рейсов для экономии места
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        # Возвращаем список сегментов (рейсов)
        return data.get('segments', [])
    except Exception as e:
        print(f"Ошибка API Расписаний (search): {e}")
        return []


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hash_pw = generate_password_hash(request.form['password'])
        file = request.files.get('avatar')
        avatar_name = 'default_avatar.png'
        if file and file.filename != '':
            avatar_name = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], avatar_name))

        new_user = User(username=request.form['username'], password=hash_pw,
                        bio=request.form.get('bio'), avatar=avatar_name)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))



@app.route('/export')
@login_required
def export_csv():
    trips = Trip.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['From', 'To', 'Budget', 'Days'])
    for t in trips:
        writer.writerow([t.city_from, t.city_to, t.budget_limit, t.days_count])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
                     mimetype='text/csv', as_attachment=True, download_name='trips.csv')


@app.route('/import', methods=['POST'])
@login_required
def import_csv():
    file = request.files.get('file')
    if file:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        next(csv_input)
        for row in csv_input:
            if len(row) >= 4:
                db.session.add(Trip(city_from=row[0], city_to=row[1], budget_limit=int(row[2]),
                                    days_count=int(row[3]), user_id=current_user.id))
        db.session.commit()
    return redirect(url_for('index'))




if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
    app.run(debug=True)