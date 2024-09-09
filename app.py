from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
import jwt
import datetime

app = Flask(__name__)
CORS(app)

mongodb_uri = os.getenv('MONGODB_URI')
jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key')

client = MongoClient(mongodb_uri)
db = client['universe_game_db']
users_collection = db['users']

@app.route('/api/auth', methods=['POST'])
def authenticate():
    data = request.json
    telegram_id = data.get('telegram_id')
    username = data.get('username')

    if not telegram_id or not username:
        return jsonify({'success': False, 'error': 'Missing telegram_id or username'}), 400

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
def get_user_data():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        decoded = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        telegram_id = decoded['telegram_id']
        
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
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

if __name__ == '__main__':
    app.run(debug=True)