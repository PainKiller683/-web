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

# Ключи получать тут: https://yandex.ru
MAPS_API_KEY = "c585582f-eef6-4946-aa74-544317085ccf"
RASP_API_KEY = "13bbc4a8-f7c8-418e-bd4c-40b72b78c48f"
WEATHER_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
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



def get_city_info(city_name):
    try:
        geo_url = f"https://yandex.ru{MAPS_API_KEY}&geocode={city_name}&format=json"
        geo_data = requests.get(geo_url).json()
        pos = geo_data['response']['GeoObjectCollection']['featureMember']['GeoObject']['Point']['pos']
        lon, lat = pos.split(' ')
        near_url = f"https://yandex.net{RASP_API_KEY}&lat={lat}&lng={lon}&format=json"
        near_data = requests.get(near_url).json()
        yandex_code = near_data.get('code')

        return {'lat': lat, 'lon': lon, 'code': yandex_code}
    except Exception as e:
        print(f"Ошибка гео-поиска {city_name}: {e}")
        return None


def get_weather(lat, lon):
    url = f"https://yandex.ru{lat}&lon={lon}&lang=ru_RU"
    headers = {'X-Yandex-API-Key': WEATHER_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return {
            "temp": f"{data['fact']['temp']}°C",
            "condition": data['fact']['condition']
        }
    except Exception as e:
        print(f"Ошибка погоды: {e}")
        return {"temp": "??", "condition": "нет данных"}


def get_routes(code_from, code_to):
    date_now = datetime.now().strftime('%Y-%m-%d')
    url = f"https://yandex.net{RASP_API_KEY}&from={code_from}&to={code_to}&lang=ru_RU&date={date_now}&limit=5"
    try:
        data = requests.get(url).json()
        return data.get('segments', [])
    except Exception as e:
        print(f"Ошибка расписаний: {e}")
        return []


@app.route('/')
@login_required
def index():
    return render_template('index.html')


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


@app.route('/add_trip', methods=['POST'])
@login_required
def add_trip():
    trip = Trip(city_from=request.form['city_from'],
                city_to=request.form['city_to'],
                budget_limit=int(request.form.get('budget_limit', 0)),
                days_count=int(request.form.get('days_count', 1)),
                user_id=current_user.id)
    db.session.add(trip)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/trip/<int:trip_id>')
@login_required
def trip_details(trip_id):
    trip = Trip.query.get_or_404(trip_id)

    # 1. Находим инфо по городам (координаты и коды)
    info_from = get_city_info(trip.city_from)
    info_to = get_city_info(trip.city_to)

    weather = {"temp": "??", "condition": "город не найден"}
    segments = []

    # 2. Если город назначения найден, запрашиваем погоду и рейсы
    if info_to:
        weather = get_weather(info_to['lat'], info_to['lon'])
        if info_from and info_from['code'] and info_to['code']:
            segments = get_routes(info_from['code'], info_to['code'])

    # 3. Расчет бюджета (старый код)
    daily = trip.budget_limit // trip.days_count if trip.days_count > 0 else 0
    if daily < 3000:
        hotels, acts = "Хостелы", "Бесплатные парки"
    elif daily < 8000:
        hotels, acts = "Отели 3*", "Музеи и кафе"
    else:
        hotels, acts = "Отели 5*", "Рестораны и гиды"

    return render_template('trip_view.html', trip=trip, daily=daily,
                           weather=weather, hotels=hotels, acts=acts,
                           segments=segments, maps_key=MAPS_API_KEY)


# --- ИМПОРТ / ЭКСПОРТ ---

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


@app.route('/api/my_trips')
@login_required
def api_trips():
    q = request.args.get('q', '').lower()
    trips = Trip.query.filter_by(user_id=current_user.id).filter(Trip.city_to.ilike(f"%{q}%")).all()
    return jsonify([{"id": t.id, "from": t.city_from, "to": t.city_to, "budget": t.budget_limit} for t in trips])


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
    app.run(debug=True)
