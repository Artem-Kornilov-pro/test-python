from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql
app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(f"postgresql://{"$POSTGRES_USER"}:{"POSTGRES_DB"}@{"http://127.0.0.1:5000"}:5432/{"init-database.sh"}")
    return conn

@app.route('/api/ping', methods=['GET'])
def send():
    return jsonify({"status": "ok"}), 200


@app.route('/api/countries', methods=['GET'])
def get_countries():
    region = request.args.get('region')  # Получаем параметр region, если он есть
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Строим SQL-запрос в зависимости от наличия параметра region
    if region:
        query = sql.SQL("SELECT * FROM countries WHERE region = %s")
        cursor.execute(query, (region))
    else:
        query = sql.SQL("SELECT * FROM countries")
        cursor.execute(query)
    
    countries = cursor.fetchall()
    cursor.close()
    conn.close()

    # Преобразуем результаты в нужный формат
    result = [
        {"name": country[1], "alpha2": country[2], "alpha3": country[3], "region": country[4]}
        for country in countries
    ]
    return jsonify(result), 200


if __name__ == "__main__":
    app.run()
