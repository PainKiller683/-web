import os
import io
import csv
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Настройки приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Лимит 16МБ на файл

# Инициализация БД и Логина
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ORM МОДЕЛИ
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    trips = db.relationship('Trip', backref='owner', lazy=True)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    ticket_file = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


#РОУТЫ (ЛОГИКА)

@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(username=request.form['username'],
                    password=generate_password_hash(request.form['password']))
        db.session.add(user)
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
    city = request.form.get('city')
    file = request.files.get('ticket')
    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    new_trip = Trip(city=city, ticket_file=filename, user_id=current_user.id)
    db.session.add(new_trip)
    db.session.commit()
    return redirect(url_for('index'))


# API И ЭКСПОРТ

@app.route('/api/my_trips')
@login_required
def api_trips():
    q = request.args.get('q', '').lower()
    trips = Trip.query.filter_by(user_id=current_user.id).filter(Trip.city.ilike(f"%{q}%")).all()
    return jsonify([{"city": t.city, "file": t.ticket_file} for t in trips])


@app.route('/export')
@login_required
def export():
    trips = Trip.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['City', 'File'])
    for t in trips: writer.writerow([t.city, t.ticket_file])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True,
                     download_name='trips.csv')


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
    app.run(debug=True)