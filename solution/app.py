"""
Модуль API на Flask для работы с PostgreSQL и аутентификацией пользователей.
Функционал включает регистрацию, вход в систему, получение данных о странах, 
а также создание и использование JWT токенов для аутентификации.
"""

from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
import bcrypt

# Загружаем переменные окружения из файла .env
load_dotenv()
app = Flask(__name__)

# Конфигурация для JWT
SECRET_KEY = os.getenv("RANDOM_SECRET", "your_secret_key")  # Секретный ключ для JWT
ALGORITHM = "HS256"  # Алгоритм шифрования
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Время жизни токена в минутах (например, 60 минут)

# Получаем данные для подключения к базе данных из переменной окружения
postgres_username = os.getenv("POSTGRES_USERNAME")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_port = os.getenv("POSTGRES_PORT")
postgres_database = os.getenv("POSTGRES_DATABASE")
postgres_host = os.getenv("POSTGRES_HOST")


def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    Создает JWT токен на основе предоставленных данных и времени жизни токена.

    Args:
        data (dict): Данные, которые будут зашифрованы в токене.
        expires_delta (timedelta, optional): Время жизни токена. Если не указано, используется значение по умолчанию.

    Returns:
        str: Зашифрованный JWT токен.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


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
    region = request.args.get('region')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if region:
            query = sql.SQL("SELECT * FROM countries WHERE region = %s")
            cursor.execute(query, (region,))
        else:
            query = sql.SQL("SELECT * FROM countries")
            cursor.execute(query)

        countries = cursor.fetchall()
        result = [
            {"name": country[1], "alpha2": country[2], "alpha3": country[3], "region": country[4]}
            for country in countries
        ]
        cursor.close()
        conn.close()
        return jsonify(result), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/countries/<alpha2>', methods=['GET'])
def get_country_by_alpha2(alpha2):
    """
    Получение информации о стране по её уникальному двухбуквенному коду (alpha2).

    Args:
        alpha2 (str): Двухбуквенный код страны (например, "US", "GB").

    Returns:
        jsonify: Информация о стране в формате JSON.
        200 OK: Если страна найдена.
        404 Not Found: Если страна с таким кодом не найдена.
        500 Internal Server Error: Если произошла ошибка при запросе к базе данных.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = sql.SQL("SELECT * FROM countries WHERE alpha2 = %s")
        cursor.execute(query, (alpha2.upper(),))
        country = cursor.fetchone()

        if country:
            result = {"name": country[1], "alpha2": country[2], "alpha3": country[3], "region": country[4]}
            cursor.close()
            conn.close()
            return jsonify(result), 200
        else:
            cursor.close()
            conn.close()
            return jsonify({"error": "Country not found"}), 404

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """
    Эндпоинт для регистрации нового пользователя.

    Ожидает JSON с полями 'login' и 'password'.
    Логин должен быть уникальным. Пароль будет хешироваться перед сохранением в базе данных.

    Returns:
        jsonify: Уведомление об успешной регистрации или ошибка.
        201 Created: Если пользователь успешно зарегистрирован.
        400 Bad Request: Если логин уже существует или отсутствуют обязательные поля.
        500 Internal Server Error: В случае ошибки базы данных.
    """
    data = request.get_json()
    login = data.get('login')
    password = data.get('password')

    if not login or not password:
        return jsonify({"error": "Login and password are required"}), 400

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT id FROM users WHERE login = %s', (login,))
        existing_user = cur.fetchone()

        if existing_user:
            return jsonify({"error": "User with this login already exists"}), 400

        cur.execute(
            'INSERT INTO users (login, password_hash) VALUES (%s, %s)',
            (login, password_hash)
        )
        conn.commit()
        return jsonify({"message": "User registered successfully!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


@app.route("/api/auth/sign-in", methods=["POST"])
def auth_sign_in():
    """
    Эндпоинт для аутентификации пользователя.

    Ожидает JSON с полями 'login' и 'password'.
    После успешной аутентификации возвращает JWT токен.

    Returns:
        jsonify: JWT токен или сообщение об ошибке.
        200 OK: Если вход выполнен успешно.
        401 Unauthorized: Если логин или пароль неверны.
        400 Bad Request: Если отсутствуют обязательные поля.
    """
    data = request.get_json()
    login = data.get("login")
    password = data.get("password")

    if not login or not password:
        return jsonify({"error": "Login and password are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        sql.SQL("SELECT id, login, password_hash FROM users WHERE login = %s"),
        [login]
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user is None:
        return jsonify({"error": "Invalid login or password"}), 401

    user_id, db_login, db_password_hash = user
    if not bcrypt.checkpw(password.encode('utf-8'), db_password_hash.encode('utf-8')):
        return jsonify({"error": "Invalid login or password"}), 401

    token_data = {"sub": str(user_id), "login": db_login}
    token = create_access_token(token_data)

    return jsonify({"token": token}), 200


if __name__ == "__main__":
    """
    Запуск приложения Flask.

    Приложение будет запущено на 0.0.0.0 с портом 8080 в режиме отладки.
    """
    app.run(debug=True, host="0.0.0.0", port=8080)
