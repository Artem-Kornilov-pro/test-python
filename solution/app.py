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
#from werkzeug.security import generate_password_hash, check_password_hash
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


def create_access_token(data: dict, token_version: int, expires_delta: timedelta = None):
    """
    Создает JWT токен на основе предоставленных данных, версии токена и времени жизни токена.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_version": token_version})
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
        sql.SQL("SELECT id, login, password_hash, token_version FROM users WHERE login = %s"),
        [login]
    )
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user is None:
        return jsonify({"error": "Invalid login or password"}), 401

    user_id, db_login, db_password_hash, token_version = user
    if not bcrypt.checkpw(password.encode('utf-8'), db_password_hash.encode('utf-8')):
        return jsonify({"error": "Invalid login or password"}), 401

    token_data = {"sub": str(user_id), "login": db_login}
    token = create_access_token(token_data, token_version=token_version)

    return jsonify({"token": token}), 200



@app.route("/api/me/updatePassword", methods=["POST"])
def update_password():
    """
    Эндпоинт для обновления пароля пользователя.

    Описание:
    Этот эндпоинт позволяет пользователю обновить свой пароль. 
    Старый пароль проверяется на соответствие текущему значению в базе данных, 
    а новый пароль сохраняется после успешной проверки. Все существующие токены пользователя 
    становятся недействительными за счет увеличения версии токена.

    Требования:
    - В заголовке `Authorization` должен быть передан Bearer токен.
    - В теле запроса (JSON) должны быть указаны:
        - `old_password` (строка) — текущий пароль.
        - `new_password` (строка) — новый пароль.

    Логика работы:
    1. Токен из заголовка проверяется на валидность.
    2. Старый пароль сверяется с хэшем, хранящимся в базе данных.
    3. Новый пароль хэшируется и сохраняется.
    4. Версия токена обновляется для инвалидации старых токенов.

    Возвращает:
    - 200 OK: Если пароль успешно обновлен.
    - 401 Unauthorized: Если токен недействителен, истек или неверный.
    - 400 Bad Request: Если отсутствуют обязательные поля в запросе.
    - 500 Internal Server Error: В случае непредвиденной ошибки.

    Исключения:
    - `jwt.ExpiredSignatureError`: Токен истек.
    - `jwt.InvalidTokenError`: Токен недействителен.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is missing or invalid"}), 401

    token = auth_header.split(' ')[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        token_version = payload.get("token_version")
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({"error": "Old password and new password are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Получение информации о пользователе
        cur.execute('SELECT id, password_hash, token_version FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 401

        db_user_id, db_password_hash, db_token_version = user

        # Проверка токена на соответствие версии
        if db_token_version != token_version:
            return jsonify({"error": "Token version mismatch"}), 401

        # Проверка старого пароля
        if not bcrypt.checkpw(old_password.encode('utf-8'), db_password_hash.encode('utf-8')):
            return jsonify({"error": "Old password is incorrect"}), 401

        # Хеширование нового пароля
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Обновление пароля и версии токена в базе данных
        cur.execute(
            'UPDATE users SET password_hash = %s, token_version = token_version + 1 WHERE id = %s',
            (new_password_hash, user_id)
        )
        conn.commit()

        return jsonify({"message": "Password updated successfully!"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    """
    Запуск приложения Flask.

    Приложение будет запущено на 0.0.0.0 с портом 8080 в режиме отладки.
    """
    app.run(debug=True, host="0.0.0.0", port=8080)
