from flask import Flask, request, jsonify, g
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import AutoReconnect
from dotenv import load_dotenv
import os
import jwt
import datetime
from functools import wraps
import logging

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongodb_uri = os.getenv('MONGODB_URI')
jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key')

def get_db():
    if 'db' not in g:
        g.db = MongoClient(mongodb_uri)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            token = token.split()[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            db = get_db()
            users_collection = db['universe_game_db']['users']
            current_user = users_collection.find_one({'telegram_id': data['telegram_id']})
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        except Exception as e:
            logger.error(f"Error in token validation: {str(e)}")
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/')
def root():
    return jsonify({'message': 'Welcome to the Universe Game API'}), 200

@app.route('/api/auth', methods=['POST'])
def authenticate():
    logger.info("Received authentication request")
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        username = data.get('username')

        if not telegram_id or not username:
            return jsonify({'success': False, 'error': 'Missing telegram_id or username'}), 400

        db = get_db()
        users_collection = db['universe_game_db']['users']

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

        logger.info(f"Authentication successful for user {username}")
        return jsonify({
            'success': True,
            'token': token
        })
    except AutoReconnect:
        logger.error("Database connection error")
        return jsonify({'success': False, 'error': 'Database connection error. Please try again.'}), 503
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500

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
        try:
            data = request.json
            update_data = {}
            if 'totalClicks' in data:
                update_data['totalClicks'] = data['totalClicks']
            if 'currentUniverse' in data:
                update_data['currentUniverse'] = data['currentUniverse']
            if 'universes' in data:
                update_data['universes'] = data['universes']
            
            if update_data:
                db = get_db()
                users_collection = db['universe_game_db']['users']
                users_collection.update_one(
                    {'telegram_id': current_user['telegram_id']},
                    {'$set': update_data}
                )
                logger.info(f"Updated data for user {current_user['username']}")
                return jsonify({'success': True, 'message': 'User data updated successfully'}), 200
            else:
                return jsonify({'success': False, 'message': 'No data to update'}), 400
        except Exception as e:
            logger.error(f"Error updating user data: {str(e)}")
            return jsonify({'success': False, 'error': 'An error occurred while updating user data'}), 500

@app.route('/api/log', methods=['POST'])
@token_required
def log_message(current_user):
    try:
        data = request.json
        message = data.get('message')
        if not message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400
        logger.info(f"Log from {current_user['username']}: {message}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error logging message: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while logging the message'}), 500

if __name__ == '__main__':
    app.run(debug=True)