from flask import Flask, request, jsonify
import math
app = Flask(__name__)

@app.route('/api/ping', methods=['GET'])
def send():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run()
