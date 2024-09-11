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
        return jsonify({'success': False, 'error': 'import os
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    raise ValueError("No MONGODB_URI set for Flask application")

def get_db():
    if 'db' not in g:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        g.db = client['universe_game_db']
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.client.close()

@app.route('/')
def hello():
    return "Hello, World! Application is running."

@app.route('/api/auth', methods=['POST'])
def authenticate():
    try:
        db = get_db()
        users_collection = db['users']

        data = request.json
        telegram_id = str(data.get('telegram_id'))
        username = data.get('username')

        logger.info(f"Received auth request for telegram_id: {telegram_id}, username: {username}")

        if not telegram_id:
            return jsonify({'success': False, 'error': 'No Telegram ID provided'}), 400

        user = users_collection.find_one({'telegram_id': telegram_id})

        if user:
            logger.info(f"Found existing user: {user}")
        else:
            logger.info(f"User not found, creating new user")

        if not user:
            new_user = {
                'telegram_id': telegram_id,
                'username': username,
                'totalClicks': 0,
                'currentUniverse': 'default',
                'universes': {}
            }
            result = users_collection.insert_one(new_user)
            user = new_user
            logger.info(f"Created new user: {user}")
        else:
            if user['username'] != username:
                users_collection.update_one({'_id': user['_id']}, {'$set': {'username': username}})
                user['username'] = username
                logger.info(f"Updated username for user: {user}")

        response_data = {
            'success': True,
            'telegram_id': user['telegram_id'],
            'username': user['username'],
            'totalClicks': user.get('totalClicks', 0),
            'currentUniverse': user.get('currentUniverse', 'default'),
            'universes': user.get('universes', {})
        }
        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/users', methods=['PUT'])
def update_user_data():
    try:
        db = get_db()
        users_collection = db['users']

        data = request.json
        telegram_id = str(data.get('telegram_id'))
        total_clicks = data.get('totalClicks')

        logger.info(f"Received update request for telegram_id: {telegram_id}, total_clicks: {total_clicks}")

        if not telegram_id:
            return jsonify({'success': False, 'error': 'No Telegram ID provided'}), 400

        if total_clicks is None:
            return jsonify({'success': False, 'error': 'No totalClicks provided'}), 400

        update_data = {
            'totalClicks': total_clicks,
            'currentUniverse': data.get('currentUniverse', 'default'),
        }

        current_universe = data.get('currentUniverse', 'default')
        if 'upgrades' in data:
            update_data[f"universes.{current_universe}"] = data['upgrades']

        logger.info(f"Updating user data: {update_data}")

        result = users_collection.update_one(
            {'telegram_id': telegram_id},
            {'$set': update_data},
            upsert=True
        )

        if result.modified_count > 0 or result.upserted_id:
            logger.info(f"Successfully updated user data for telegram_id: {telegram_id}")
            return jsonify({'success': True})
        else:
            logger.warning(f"No changes made for telegram_id: {telegram_id}")
            return jsonify({'success': False, 'error': 'No changes made'}), 400
    except Exception as e:
        logger.error(f"Error updating user data: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/log', methods=['POST'])
def log_message():
    try:
        data = request.json
        logger.info(f"Client log: {data}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error logging message: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
    logger.info(f"App running on port {port}")Missing telegram_id or username'}), 400

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