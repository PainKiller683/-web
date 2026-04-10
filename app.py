import os
import io
import csv
import requests
from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, send_file, make_response, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Импорт локальных модулей
from forms import RegistrationForm, TripForm, ExpenseForm
from utils import save_avatar, check_file_extension

app = Flask(__name__)

# Конфигурация приложения
app.config.update(
    SECRET_KEY='travel-dash-2026-very-secure-key',
    SQLALCHEMY_DATABASE_URI='sqlite:///travel_v5.db',
    UPLOAD_FOLDER='static/uploads',
    AVATAR_FOLDER='static/avatars',
    MAX_CONTENT_LENGTH=10 * 1024 * 1024  # Лимит загрузки 10 МБ
)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# --- МОДЕЛИ ДАННЫХ (ORM) ---

class User(UserMixin, db.Model):
    """Таблица пользователей с метаданными профиля."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    avatar = db.Column(db.String(200), default='default_avatar.png')  # Имя файла аватара
    bio = db.Column(db.Text)  # Краткая биография
    trips = db.relationship('Trip', backref='owner', lazy=True)


class Trip(db.Model):
    """Таблица основных данных о поездке."""
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    budget_limit = db.Column(db.Float, default=0.0)
    ticket_file = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Связи с расходами и точками маршрута
    expenses = db.relationship('Expense', backref='trip', cascade="all, delete-orphan", lazy=True)
    waypoints = db.relationship('Waypoint', backref='trip', cascade="all, delete-orphan", lazy=True)


class Expense(db.Model):
    """Таблица учета финансовых операций по поездке."""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    description = db.Column(db.String(200))
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)


class Waypoint(db.Model):
    """Таблица для хранения точек маршрута на карте."""
    id = db.Column(db.Integer, primary_key=True)
    place_name = db.Column(db.String(150), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    """Функция загрузки пользователя для Flask-Login."""
    return User.query.get(int(user_id))


# --- ОСНОВНЫЕ ОБРАБОТЧИКИ (ROUTES) ---

@app.route('/')
@login_required
def index():
    """Главная страница со списком всех поездок пользователя."""
    form = TripForm()
    user_trips = Trip.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', trips=user_trips, form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        bio = request.form.get('bio')
        file = request.files.get('avatar')

        # Хэшируем пароль
        hash_pw = generate_password_hash(password)

        # Обработка аватара
        avatar_filename = 'default_avatar.png'
        if file and file.filename != '':
            avatar_filename = "av_" + secure_filename(username + "_" + file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename))

        new_user = User(
            username=username,
            password=hash_pw,
            bio=bio,
            avatar=avatar_filename
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Авторизация пользователя."""
    if request.method == 'POST':
        login_val = request.form.get('username')
        pass_val = request.form.get('password')

        user = User.query.filter_by(username=login_val).first()
        if user and check_password_hash(user.password, pass_val):
            login_user(user)
            return redirect(url_for('index'))

        flash('Неверное имя пользователя или пароль. Попробуйте еще раз.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Завершение текущей сессии пользователя."""
    logout_user()
    return redirect(url_for('login'))


@app.route('/trip/create', methods=['POST'])
@login_required
def create_trip():
    """Добавление новой поездки в базу данных."""
    form = TripForm()
    if form.validate_on_submit():
        ticket_data = form.ticket.data
        filename = secure_filename(ticket_data.filename) if ticket_data else None

        if filename:
            ticket_data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_trip = Trip(
            city=form.city.data,
            budget_limit=form.budget.data,
            ticket_file=filename,
            user_id=current_user.id
        )

        db.session.add(new_trip)
        db.session.commit()
        flash('Новый план поездки успешно создан!', 'success')

    return redirect(url_for('index'))


@app.route('/trip/view/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def trip_detail(trip_id):
    """Детальный просмотр поездки: маршрут и финансы."""
    target_trip = Trip.query.get_or_404(trip_id)

    if target_trip.user_id != current_user.id:
        return "403 Доступ запрещен", 403

    expense_form = ExpenseForm()
    if expense_form.validate_on_submit():
        new_expense = Expense(
            amount=expense_form.amount.data,
            category=expense_form.category.data,
            description=expense_form.description.data,
            trip_id=target_trip.id
        )
        db.session.add(new_expense)
        db.session.commit()
        flash('Новый расход успешно добавлен в смету.', 'info')
        return redirect(url_for('trip_detail', trip_id=target_trip.id))

    # Расчет финансовой статистики
    current_spent = sum(e.amount for e in target_trip.expenses)
    percent_used = (current_spent / target_trip.budget_limit * 100) if target_trip.budget_limit > 0 else 0

    return render_template(
        'trip_detail.html',
        trip=target_trip,
        form=expense_form,
        spent=current_spent,
        progress=min(percent_used, 100)
    )


# --- API И ЭКСПОРТ (CSV) ---

@app.route('/api/v1/search')
@login_required
def search_api():
    """REST API для поиска поездок на лету."""
    query_text = request.args.get('q', '').lower()
    filtered = Trip.query.filter_by(user_id=current_user.id).filter(Trip.city.ilike(f"%{query_text}%")).all()

    return jsonify([{
        "id": trip.id,
        "city": trip.city,
        "total_expenses": sum(e.amount for e in trip.expenses),
        "limit": trip.budget_limit
    } for trip in filtered])


@app.route('/add_trip', methods=['POST'])
@login_required
def add_trip():
    city = request.form.get('city')
    budget = request.form.get('budget_limit', 0)  # Получаем бюджет
    file = request.files.get('ticket')

    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Записываем все 4 колонки: city, budget_limit, ticket_file, user_id
    new_trip = Trip(city=city, budget_limit=budget, ticket_file=filename, user_id=current_user.id)
    db.session.add(new_trip)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/export/data')
@login_required
def export_csv():
    """Генерация CSV отчета по всем поездкам пользователя."""
    buffer = io.StringIO()
    csv_writer = csv.writer(buffer)
    csv_writer.writerow(['Город', 'Бюджетный лимит', 'Всего потрачено', 'Количество локаций'])

    all_trips = Trip.query.filter_by(user_id=current_user.id).all()
    for trip in all_trips:
        csv_writer.writerow([
            trip.city,
            trip.budget_limit,
            sum(e.amount for e in trip.expenses),
            len(trip.waypoints)
        ])

    response = make_response(buffer.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=my_travel_stats_2026.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/api/my_trips')
@login_required
def api_trips():
    q = request.args.get('q', '').lower()
    trips = Trip.query.filter_by(user_id=current_user.id).filter(Trip.city.ilike(f"%{q}%")).all()
    # Важно: добавляем budget в JSON
    return jsonify([{
        "city": t.city,
        "budget": t.budget_limit,
        "file": t.ticket_file
    } for t in trips])

if __name__ == '__main__':
    # Автоматическая инициализация структуры
    for directory in [app.config['UPLOAD_FOLDER'], app.config['AVATAR_FOLDER']]:
        os.makedirs(directory, exist_ok=True)

    with app.app_context():
        db.create_all()

    app.run(debug=True)
