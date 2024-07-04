""" Module providing a periodic task scheduler that hourly fetches data in the background
    and stores it into the database. It also provides the API endpoints.
"""

import sys
sys.path.append('./')
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from src.weather_API_data.read_data import get_weather_data
from src.weather_API_data.fetch_data import load_config, env_config_loading
from src.weather_API_data.store_data import (
    create_weather_database,
    create_weather_table,
    insert_data
)




ENV_PATH = Path('.') / '.env'
CITIES = ["Seoul", "pusan", "Malmö", "Stockholm", "Paris", "Taipei", "London"]
CREATE_TABLE_COMMAND = """
    CREATE TABLE IF NOT EXISTS weather_data (
        id SERIAL PRIMARY KEY,
        city_name VARCHAR(255),
        temperature FLOAT,
        pressure INT,
        humidity INT,
        date_time TIMESTAMP
    )
"""
CREATE_DATABASE_COMMAND = """CREATE DATABASE weather_info_db"""
INSERT_DATA_COMMAND = """INSERT INTO weather_data (city_name, temperature, pressure, humidity, date_time)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id;"""




app = Flask(__name__)

def scheduled_job_fetch_store_wether_data():
    """ A background job that runs every hour to fetch
        weather data and store it in the databse
    """

    # Connect to weather_info_db
    config_new_db = load_config('database.ini', 'weather_info_database')
    conn_new = psycopg2.connect(**config_new_db)
    conn_new.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    api_key, api_base_url = env_config_loading(ENV_PATH)
    for city_nm in CITIES:
        # TODO undo this comment because I only need it now
        #response_data = fetch_weather_data(city_nm, api_key, api_base_url)
        response_data = {
        "current": {
            "temperature": 24,
            "pressure": 1001,
            "humidity": 74,
        }}
        insert_data(conn_new, city_nm, response_data, INSERT_DATA_COMMAND)




@app.route('/api/weather_data', methods=['GET']) #TODO this is just for testing, use <city>
def get_city_weather():
    city_name = request.args.get('city_name')
    if not city_name:
        return jsonify({"error": "city_name parameter is required"}), 400

    # Added this filter in case we want to expand
    # it to fetching weather for multiple cities
    city_filter = {'city_name' : [city_name]}

    weather_data = get_weather_data(city_filter)

    if weather_data:
        return jsonify(weather_data), 200
    else:
        return jsonify({"error": "weather data not found"}), 404



if __name__ == '__main__':
    try:
        #Create the weather database and the wethaer table if not exists
        db_connection  = create_weather_database(CREATE_DATABASE_COMMAND)
        if db_connection is not None:
            conn_tbl = create_weather_table(CREATE_TABLE_COMMAND)
        
        db_connection.close()

        # Trigger the scheduler that runs once every hour
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=scheduled_job_fetch_store_wether_data, trigger="interval", minutes=10)
        scheduler.start()

        app.run(debug=True)

    except Exception as error:
        print(f"Error in main block: {error}")
