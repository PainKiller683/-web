import os, io, csv, requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'travel-2026-final-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- API НАСТРОЙКИ ---
YANDEX_WEATHER_API_KEY = "demo_yandex_weather_api_key_ca6d09349ba0"  # <-- ВСТАВИТЬ КЛЮЧ


# --- МОДЕЛИ ДАННЫХ ---
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


# --- ФУНКЦИЯ ПОГОДЫ ---
def get_weather(city):
    def get_weather(city):
        api_key = "demo_yandex_weather_api_key_ca6d09349ba0"
        # Пример реального запроса к API Яндекса (нужны координаты lat/lon)
        url = f"https://yandex.ru"
        headers = {'X-Yandex-API-Key': api_key}

        try:
            response = requests.get(url, headers=headers)
            print(f"DEBUG WEATHER STATUS: {response.status_code}")  # Должно быть 200
            print(f"DEBUG JSON: {response.json()}")  # Посмотри структуру ответа

            data = response.json()
            return {
                "temp": f"{data['fact']['temp']}°C",
                "condition": data['fact']['condition']
            }
        except Exception as e:
            print(f"ERROR: {e}")
            return {"temp": "Ошибка", "condition": "нет связи"}


# --- РОУТЫ ---
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
    logout_user();
    return redirect(url_for('login'))


@app.route('/add_trip', methods=['POST'])
@login_required
def add_trip():
    trip = Trip(city_from=request.form['city_from'], city_to=request.form['city_to'],
                budget_limit=int(request.form.get('budget_limit', 0)),
                days_count=int(request.form.get('days_count', 1)), user_id=current_user.id)
    db.session.add(trip);
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/trip/<int:trip_id>')
@login_required
def trip_details(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    daily = trip.budget_limit // trip.days_count if trip.days_count > 0 else 0
    weather = get_weather(trip.city_to)

    if daily < 3000:
        hotels, acts = "Хостелы", "Бесплатные парки"
    elif daily < 8000:
        hotels, acts = "Отели 3*", "Музеи и кафе"
    else:
        hotels, acts = "Отели 5*", "Рестораны и гиды"

    return render_template('trip_view.html', trip=trip, daily=daily,
                           weather=weather, hotels=hotels, acts=acts)


@app.route('/export')
@login_required
def export_csv():
    trips = Trip.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['From', 'To', 'Budget', 'Days'])
    for t in trips: writer.writerow([t.city_from, t.city_to, t.budget_limit, t.days_count])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True,
                     download_name='trips.csv')


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
                db.session.add(Trip(city_from=row[0], city_to=row[1], budget_limit=int(row[2]), days_count=int(row[3]),
                                    user_id=current_user.id))
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
