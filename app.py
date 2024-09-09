from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
CORS(app)

mongodb_uri = os.getenv('MONGODB_URI')
jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key')

# Создаем MongoClient внутри функции, чтобы избежать проблем с форком
def get_db():
    client = MongoClient(mongodb_uri)
    return client['universe_game_db']

# Декоратор для проверки JWT токена
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            jwt.decode(token, jwt_secret, algorithms=['HS256'])
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/auth', methods=['POST'])
def authenticate():
    data = request.json
    telegram_id = data.get('telegram_id')
    username = data.get('username')

    if not telegram_id or not username:
        return jsonify({'success': False, 'error': 'Missing telegram_id or username'}), 400

    db = get_db()
    users_collection = db['users']

    user = users_collection.find_one({'telegram_id': telegram_id})

    if not user:
        user = {
            'telegram_id': telegram_id,
            'username': username,
            'totalClicks': 0,
            'currentUniverse': 'default',
            'universes': {}
        }
        users_collection.insert_one(user)

    # Создаем JWT токен
    token = jwt.encode({
        'telegram_id': telegram_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }, jwt_secret, algorithm='HS256')

    return jsonify({
        'success': True,
        'token': token
    })

@app.route('/api/user', methods=['GET'])
@token_required
def get_user_data():
    token = request.headers.get('Authorization')
    decoded = jwt.decode(token, jwt_secret, algorithms=['HS256'])
    telegram_id = decoded['telegram_id']
    
    db = get_db()
    users_collection = db['users']
    user = users_collection.find_one({'telegram_id': telegram_id})
    
    if user:
        return jsonify({
            'success': True,
            'telegram_id': user['telegram_id'],
            'username': user['username'],
            'totalClicks': user['totalClicks'],
            'currentUniverse': user['currentUniverse'],
            'universes': user['universes']
        })
    else:
        return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/api/log', methods=['POST'])
@token_required
def log_message():
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({'success': False, 'error': 'No message provided'}), 400
    
    print(f"Log: {message}")  # Просто выводим сообщение в консоль
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)