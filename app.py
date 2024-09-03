import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import uuid

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    raise ValueError("No MONGODB_URI set for Flask application")

try:
    client = MongoClient(mongodb_uri)
    client.admin.command('ismaster')
    db = client['universe_game_db']
    users_collection = db['users']
    logger.info("Successfully connected to MongoDB")
except ConnectionFailure:
    logger.error("Server not available")
    client = None

@app.route('/')
def hello():
    if client:
        return "Hello, World! MongoDB connected successfully."
    else:
        return "Hello, World! Warning: MongoDB connection failed."

@app.route('/api/generate_token', methods=['POST'])
def generate_token():
    if not client:
        logger.error("Database connection failed")
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500

    data = request.json
    telegram_id = data.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'success': False, 'error': 'No Telegram ID provided'}), 400

    token = str(uuid.uuid4())
    expiration_time = datetime.utcnow() + timedelta(minutes=15)
    
    users_collection.update_one(
        {'telegram_id': telegram_id},
        {
            '$set': {
                'temp_token': token,
                'temp_token_expiration': expiration_time
            },
            '$setOnInsert': {
                'totalClicks': 0,
                'universes': {
                    'default': {
                        'damageLevel': 1,
                        'energyLevel': 1,
                        'regenLevel': 1,
                        'energy': 1000,
                        'energyMax': 1000,
                        'regenRate': 1
                    }
                },
                'currentUniverse': 'default'
            }
        },
        upsert=True
    )
    
    logger.info(f"Generated token for Telegram ID: {telegram_id}")
    return jsonify({'success': True, 'token': token})

@app.route('/api/auth', methods=['POST'])
def authenticate():
    if not client:
        logger.error("Database connection failed")
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500

    data = request.json
    token = data.get('token')

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 400

    user = users_collection.find_one({
        'temp_token': token,
        'temp_token_expiration': {'$gt': datetime.utcnow()}
    })

    if not user:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    session_token = str(uuid.uuid4())
    session_expiration = datetime.utcnow() + timedelta(days=7)

    users_collection.update_one(
        {'_id': user['_id']},
        {
            '$unset': {'temp_token': "", 'temp_token_expiration': ""},
            '$set': {
                'session_token': session_token,
                'session_token_expiration': session_expiration
            }
        }
    )

    logger.info(f"User authenticated: {user['telegram_id']}")
    logger.info(f"Created session token: {session_token} for user {user['telegram_id']}")
    
    return jsonify({
        'success': True,
        'universe_data': {
            'totalClicks': user.get('totalClicks', 0),
            'universes': user.get('universes', {
                'default': {
                    'damageLevel': 1,
                    'energyLevel': 1,
                    'regenLevel': 1,
                    'energy': 1000,
                    'energyMax': 1000,
                    'regenRate': 1
                }
            }),
            'currentUniverse': user.get('currentUniverse', 'default')
        },
        'session_token': session_token
    })

@app.route('/api/users', methods=['PUT'])
def update_user_data():
    if not client:
        logger.error("Database connection failed")
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500

    auth_header = request.headers.get('Authorization')
    if not auth_header:
        logger.error("No authorization header")
        return jsonify({'success': False, 'error': 'No authorization header'}), 401

    token = auth_header.split(' ')[1]
    user = users_collection.find_one({
        'session_token': token,
        'session_token_expiration': {'$gt': datetime.utcnow()}
    })

    if not user:
        logger.error(f"User not found for token: {token}")
        return jsonify({'success': False, 'error': 'Invalid or expired session token'}), 401

    data = request.json
    logger.info(f"Received data for user {user['telegram_id']}: {data}")

    try:
        update_data = {
            'totalClicks': data['totalClicks'],
            'currentUniverse': data['currentUniverse'],
            f"universes.{data['currentUniverse']}": data['upgrades']
        }

        logger.info(f"Updating data for user {user['telegram_id']}: {update_data}")

        result = users_collection.update_one(
            {'_id': user['_id']},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"Data updated for user {user['telegram_id']}")
        else:
            logger.warning(f"No changes made for user {user['telegram_id']}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating user data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))