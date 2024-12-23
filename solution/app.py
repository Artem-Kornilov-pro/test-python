from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/ping', methods=['GET'])
def send():
    return jsonify({"status": "ok"}), 200

@app.route('/api/countries', methods=['GET'])
def send_countries():
    return jsonify({"status": "ok"}), 200

    """Получение списка стран с возможной фильтрацией.
        Используется на странице регистрации для предоставления возможности выбора страны, к которой относится пользователь.
        Если хотя бы один переданный регион является некорректным, весь запрос считается некорректным.
        Если никакие из фильтров не переданы, необходимо вернуть все страны."""
    
if __name__ == "__main__":
    app.run()
    
