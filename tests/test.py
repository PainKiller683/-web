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

MAPS_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"
RASP_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"
WEATHER_API_KEY = "2ec94579-9bbb-4012-81a9-cf8c4032ea93"
GEO_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"

class Trip(db.Model):
    waypoints = db.relationship('Waypoint', backref='trip', lazy=True)
    id = db.Column(db.Integer, primary_key=True)
    city_from = db.Column(db.String(100), nullable=False)
    city_to = db.Column(db.String(100), nullable=False)
    budget_limit = db.Column(db.Integer, default=0)
    days_count = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# def get_city_info(city_name):
#     geo_url = "https://geocode-maps.yandex.ru/v1"
#     params = {
#         "apikey": GEO_API_KEY,
#         "geocode": city_name,
#         "format": "json",
#         "lang": "ru_RU"
#     }
#     r = requests.get(geo_url, params=params).json()
#     # pos = r['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
#     # lon, lat = pos.split(' ')
#     r1 = f'https://api.rasp.yandex-net.ru/v3.0/search/?apikey={RASP_API_KEY}&format=json&from=c146&to=c213&lang=ru_RU&page=1&date=2026-04-30'
#     r2 = requests.get(r1).json()
#     near_url = f"https://api.rasp.yandex-net.ru/v3.0/thread/?apikey={RASP_API_KEY}&format=json&uid=098S_1_2&lang=ru_RU&show_systems=all"
#     near_url1 = requests.get(near_url).json()
#     adress = r['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty']['GeocoderMetaData']['Address']
#     # lon, lat = pos.split(' ')
#     print(r2['segments'][0]['thread']['uid'])
#     print()
#     print(near_url1)
#     return 0
# def get_station_code(lat, lon):
#     """Находит код ближайшего транспортного узла по координатам"""
#     url = "https://api.rasp.yandex-net.ru/v3.0/nearest_stations/"
#     params = {
#         "apikey": RASP_API_KEY,
#         "lat": lat,
#         "lng": lon,
#         "distance": 50,  # Радиус поиска в км
#         "format": "json",
#         "lang": "ru_RU"
#     }
#     try:
#         response = requests.get(url, params=params)
#         data = response.json()
#         # Возвращаем код станции (тип 'station') или города (тип 'settlement')
#         if data.get('stations'):
#             return data['stations'][0]['code']
#         return None
#     except Exception as e:
#         print(f"Ошибка API Расписаний (nearest): {e}")
#         return None


#<-   Не работает  ->
# def get_rasp_segments(code_from, code_to):
#     if not code_from or not code_to:
#         return []
#
#     url = "https://api.rasp.yandex-net.ru/v3.0/search/"
#     params = {
#         "apikey": RASP_API_KEY,
#         "from": code_from,
#         "to": code_to,
#         "date": datetime.now().strftime('%Y-%m-%d'),
#         "system": "yandex",
#         "transport_types": "suburban",
#         "format": "json"
#     }
#
#     try:
#         response = requests.get(url, params=params)
#         res = response.json()
#         print(res)
#         if "error" in res:
#             print(f"Ошибка API: {res['error']}")
#
#         return res.get('segments', [])
#     except Exception as e:
#         print(f"Ошибка запроса: {e}")
#         return []

import requests
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


def get_routes(code_from, code_to):
    """Получает список всех рейсов между двумя кодами станций"""
    if not code_from or not code_to:
        return []
    current_date = datetime.now().strftime('%Y-%m-%d')
    url = "https://api.rasp.yandex-net.ru/v3.0/search/"
    params = {
        "apikey": RASP_API_KEY,
        "from": code_from,
        "to": code_to,
        'date': current_date,
        "system": "yandex",
        "format": "json",
        "lang": "ru_RU",
        "limit": 10,
        'transport_types': 'plane,train,suburban,bus',
        'transfers': True
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if 'error' in data:
            print(f"Ошибка от API: {data['error']}")

        return data.get('segments', [])
    except Exception as e:
        print(f"Ошибка API Расписаний (search): {e}")
        return []

def get_today_trips(code_from, code_to):
    # 1. Получаем текущую дату в формате 2026-05-05
    today = datetime.now().strftime('%Y-%m-%d')
    current_date = datetime.now().strftime('%Y-%m-%d')
    # 2. Указываем коды станций
    # ВНИМАНИЕ: Проверьте коды! s9601931 - это Москва, s9603093 - это Тверь.
    params = {
        "apikey": RASP_API_KEY,
        "from": code_from,
        "to": code_to,
        'date': current_date,
        "system": "yandex",
        "format": "json",
        "lang": "ru_RU",
        "limit": 10,
        'transport_types': 'plane,train,suburban,bus',
        'transfers': True
    }

    try:
        response = requests.get('https://api.rasp.yandex-net.ru/v3.0/search/', params=params)
        data = response.json()

        # Генерируем "человеческую" ссылку на сайт Яндекса для пользователя
        # Чтобы он мог кликнуть и посмотреть расписание в браузере
        web_link = f"https://yandex.ru{params['from']}&toId={params['to']}&date={today}"

        return jsonify({
            "status": "success",
            "date": today,
            "segments_count": len(data.get('segments', [])),
            "api_url": response.url,  # Ссылка, по которой сходил ваш код
            "web_link": web_link,  # Ссылка для браузера
            "data": data  # Весь ответ от Яндекса
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def get_weather(lat, lon):
    url = "https://api.weather.yandex.ru/v2/forecast"
    headers = {'X-Yandex-API-Key': WEATHER_API_KEY}
    try:
        params = {'lat': lat, 'lon': lon}
        r = requests.get(url, headers=headers, params=params).json()
        return {
            "temp": f"{r['fact']['temp']}°",
            "condition": r['fact']['condition'],
            "icon": r['fact']['icon']
        }
    except:
        return {"temp": "??", "condition": "нет данных", "icon": "ovc"}

print(get_weather(get_city_info('Москва')['lat'], get_city_info('Москва')['lon']))
#
# import requests
#
# # insert your real key here!
# access_key = "your_key"
#
# headers = {
#     "X-Yandex-Weather-Key": '2ec94579-9bbb-4012-81a9-cf8c4032ea93'
# }
#
# query = """{
#   weatherByPoint(request: { lat: 52.37125, lon: 4.89388 }) {
#     now {
#       temperature
#     }
#   }
# }"""
#
# response = requests.post('https://api.weather.yandex.ru/graphql/query', headers=headers, json={'query': query})
#
# print(response.content)