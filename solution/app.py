from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()
app = Flask(__name__)

# Получаем данные для подключения к базе данных из переменной окружения
postgres_username = os.getenv("POSTGRES_USERNAME")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_port = os.getenv("POSTGRES_PORT")
postgres_database = os.getenv("POSTGRES_DATABASE")
postgres_host = os.getenv("POSTGRES_HOST")

def get_db_connection():
    """
    Устанавливает и возвращает подключение к базе данных PostgreSQL.

    Подключение настроено для работы с базой данных `postgres` на локальном сервере.
    Используется имя пользователя из переменной окружения `POSTGRES_USERNAME`.
    
    Returns:
        psycopg2.connection: Объект подключения к базе данных.
    """
    return psycopg2.connect(
        host=postgres_host,
        dbname=postgres_database,
        user=postgres_username,
        password=postgres_password,  
        port=postgres_port 
    )


@app.route('/api/ping', methods=['GET'])
def send():
    """
    Простой эндпоинт для проверки работоспособности API.

    Этот маршрут используется для тестирования доступности сервера.
    Ответ всегда будет содержать статус "ok" с кодом 200.

    Returns:
        jsonify: Ответ в формате JSON с сообщением о статусе.
    """
    return jsonify({"status": "ok"}), 200


@app.route('/api/countries', methods=['GET'])
def get_countries():
    """
    Получение списка стран, с возможностью фильтрации по региону.

    Если параметр `region` передан в запросе, то будет выполнен фильтр по региону.
    В противном случае возвращаются все страны из базы данных.

    Returns:
        jsonify: Список стран в формате JSON.
        200 OK: Если запрос успешен.
        500 Internal Server Error: Если возникла ошибка при запросе к базе данных.
    """
    # Получаем параметр 'region' из строки запроса, если он существует
    region = request.args.get('region')
    
    try:
        # Подключение к базе данных
        conn = get_db_connection()
        cursor = conn.cursor()

        # Строим SQL-запрос в зависимости от наличия параметра region
        if region:
            query = sql.SQL("SELECT * FROM countries WHERE region = %s")
            cursor.execute(query, (region,))
        else:
            query = sql.SQL("SELECT * FROM countries")
            cursor.execute(query)

        countries = cursor.fetchall()  # Получаем все результаты запроса

        # Преобразуем результаты в формат, который вернем пользователю
        result = [
            {"name": country[1], "alpha2": country[2], "alpha3": country[3], "region": country[4]}
            for country in countries
        ]
        
        # Закрытие соединения с базой данных
        cursor.close()
        conn.close()

        return jsonify(result), 200

    except Exception as e:
        # Логирование ошибки и возврат сообщения о внутренней ошибке
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/countries/<alpha2>', methods=['GET'])
def get_country_by_alpha2(alpha2):
    """
    Получение информации о стране по её уникальному двухбуквенному коду (alpha2).

    Этот маршрут позволяет получить информацию о стране по её двухбуквенному коду.
    Код всегда преобразуется в верхний регистр перед выполнением запроса.

    Args:
        alpha2 (str): Двухбуквенный код страны (например, "US", "GB").

    Returns:
        jsonify: Информация о стране в формате JSON.
        200 OK: Если страна найдена.
        404 Not Found: Если страна с таким кодом не найдена.
        500 Internal Server Error: Если произошла ошибка при запросе к базе данных.
    """
    try:
        # Подключение к базе данных
        conn = get_db_connection()
        cursor = conn.cursor()

        # Строим SQL-запрос для поиска страны по двухбуквенному коду
        query = sql.SQL("SELECT * FROM countries WHERE alpha2 = %s")
        cursor.execute(query, (alpha2.upper(),))  # Преобразуем код в верхний регистр для поиска

        country = cursor.fetchone()  # Получаем одну запись, так как alpha2 уникален

        if country:
            # Преобразуем результат в формат для ответа
            result = {
                "name": country[1],
                "alpha2": country[2],
                "alpha3": country[3],
                "region": country[4]
            }
            cursor.close()
            conn.close()
            return jsonify(result), 200
        else:
            cursor.close()
            conn.close()
            return jsonify({"error": "Country not found"}), 404

    except Exception as e:
        # Логирование ошибки и возврат сообщения о внутренней ошибке
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/auth/register', methods=['POST'])
def post_regisrer():
    """
    Регистрация нового пользователя.

    Этот маршрут предназначен для обработки запросов на регистрацию пользователя.
    Пока что этот эндпоинт возвращает только статус "ok", в будущем нужно добавить логику регистрации.

    Returns:
        jsonify: Статус успешной регистрации.
        200 OK: Если регистрация прошла успешно.
    """
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # Запуск приложения Flask в режиме отладки
    app.run(debug=True, host="0.0.0.0", port="8080" )

