import os, requests
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

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

def get_city_info(city_name):
    #Код для работы геокодера
        # geo_url = "https://geocode-maps.yandex.ru/v1"
        # params = {
        #     "apikey": GEO_API_KEY,
        #     "geocode": city_name,
        #     "format": "json",
        #     "lang": "ru_RU"
        # }
        # r = requests.get(geo_url, params=params).json()
    #Координаты
        # pos = r['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
        # lon, lat = pos.split(' ')

    #Рейсы от точки до точки(нужны коды городов)
        # r1 = f'https://api.rasp.yandex-net.ru/v3.0/search/?apikey={RASP_API_KEY}&format=json&from=c146&to=c213&lang=ru_RU&page=1&date=2026-04-30'
        # r2 = requests.get(r1).json()

    #Вывод uid(id рейсов)
        # print(r2['segments'][0]['thread']['uid'])

    #По id вывод рейса(полная информация)
        # near_url = f"https://api.rasp.yandex-net.ru/v3.0/thread/?apikey={RASP_API_KEY}&format=json&uid=098S_1_2&lang=ru_RU&show_systems=all"
        # near_url1 = requests.get(near_url).json()
        # print(near_url1)
    return 0

print(get_city_info('Москва'))