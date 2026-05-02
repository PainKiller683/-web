import os, requests
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'travel-2026-final-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

MAPS_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"
RASP_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"
WEATHER_API_KEY = "2c06abb3-fcf6-43d9-8edb-0d29f415b1e3"
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

    # 1. ИСПРАВЛЕН ДОМЕН (был yandex-net.ru, стал yandex.net)
    url = "https://yandex.net"

    params = {
        "apikey": RASP_API_KEY,
        "from": code_from,
        "to": code_to,
        "date": datetime.now().strftime('%Y-%m-%d'),
        "system": "yandex",  # 2. ОБЯЗАТЕЛЬНО: без этого s-коды не сработают!
        "format": "json",
        "lang": "ru_RU",
        "limit": 10
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        print(data)
        # Если в res есть 'error', вы увидите причину
        if 'error' in data:
            print(f"Ошибка от API: {data['error']}")

        return data.get('segments', [])
    except Exception as e:
        print(f"Ошибка API Расписаний (search): {e}")
        return []


print(get_routes('s2000002', 's9601666'))