from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import jwt
import datetime
from functools import wraps

load_dotenv()

app = Flask(__name__)
CORS(app)

mongodb_uri = os.getenv('MONGODB_URI')
jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key')

client = MongoClient(mongodb_uri)
db = client['universe_game_db']
users_collection = db['users']

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            token = token.split()[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            current_user = users_collection.find_one({'telegram_id': data['telegram_id']})
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

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

    token = jwt.encode({
        'telegram_id': telegram_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }, jwt_secret, algorithm='HS256')

    return jsonify({
        'success': True,
        'token': token
    })

@app.route('/api/user', methods=['GET', 'PUT'])
@token_required
def user_data(current_user):
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'telegram_id': current_user['telegram_id'],
            'username': current_user['username'],
            'totalClicks': current_user['totalClicks'],
            'currentUniverse': current_user['currentUniverse'],
            'universes': current_user['universes']
        })
    elif request.method == 'PUT':
        data = request.json
        update_data = {}
        if 'totalClicks' in data:
            update_data['totalClicks'] = data['totalClicks']
        if 'currentUniverse' in data:
            update_data['currentUniverse'] = data['currentUniverse']
        if 'universes' in data:
            update_data['universes'] = data['universes']
        
        if update_data:
            users_collection.update_one(
                {'telegram_id': current_user['telegram_id']},
                {'$set': update_data}
            )
            return jsonify({'success': True, 'message': 'User data updated successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'No data to update'}), 400

@app.route('/api/log', methods=['POST'])
@token_required
def log_message(current_user):
    data = request.json
    message = data.get('message')
    if not message:
        return jsonify({'success': False, 'error': 'No message provided'}), 400
    print(f"Log from {current_user['username']}: {message}")
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)