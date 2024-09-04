import os
import time
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, AutoReconnect, ServerSelectionTimeoutError
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

MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

def get_mongo_client():
    for attempt in range(MAX_RETRIES):
        try:
            client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            # Проверка соединения
            client.admin.command('ismaster')
            logger.info("Successfully connected to MongoDB")
            return client
        except (ConnectionFailure, AutoReconnect, ServerSelectionTimeoutError) as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Failed to connect to MongoDB after multiple attempts")
                raise

def get_db():
    if not hasattr(g, 'mongo_client'):
        g.mongo_client = get_mongo_client()
    return g.mongo_client['universe_game_db']

@app.teardown_appcontext
def close_mongo_connection(exception):
    client = getattr(g, 'mongo_client', None)
    if client is not None:
        client.close()

@app.route('/')
def hello():
    try:
        db = get_db()
        return "Hello, World! MongoDB connected successfully."
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        return "Hello, World! Warning: MongoDB connection failed."

@app.route('/api/auth', methods=['POST'])
def authenticate():
    try:
        db = get_db()
        users_collection = db['users']

        data = request.json
        telegram_id = data.get('telegram_id')
        username = data.get('username')

        logger.info(f"Auth request for: {telegram_id}, {username}")

        if not telegram_id:
            logger.error("No Telegram ID provided")
            return jsonify({'success': False, 'error': 'No Telegram ID provided'}), 400

        user = users_collection.find_one({'telegram_id': telegram_id})

        if not user:
            new_user = {
                'telegram_id': telegram_id,
                'username': username,
                'totalClicks': 0,
                'currentUniverse': 'default',
                'universes': {}
            }
            result = users_collection.insert_one(new_user)
            logger.info(f"Created new user with ID: {result.inserted_id}")
            user = new_user
        else:
            logger.info(f"Existing user found: {user['_id']}")
            # Обновляем имя пользователя, если оно изменилось
            if user['username'] != username:
                users_collection.update_one({'_id': user['_id']}, {'$set': {'username': username}})
                user['username'] = username

        logger.info(f"Returning data for user: {user}")
        return jsonify({
            'success': True,
            'telegram_id': user['telegram_id'],
            'username': user['username'],
            'universe_data': {
                'totalClicks': user.get('totalClicks', 0),
                'universes': user.get('universes', {}),
                'currentUniverse': user.get('currentUniverse', 'default')
            }
        })
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/users', methods=['PUT'])
def update_user_data():
    try:
        db = get_db()
        users_collection = db['users']

        logger.info(f"Received update request. Headers: {request.headers}")
        logger.info(f"Request data: {request.get_data(as_text=True)}")

        data = request.json
        telegram_id = data.get('telegram_id')
        total_clicks = data.get('totalClicks')

        if not telegram_id:
            logger.error("No Telegram ID provided")
            return jsonify({'success': False, 'error': 'No Telegram ID provided'}), 400

        if total_clicks is None:
            logger.error("No totalClicks provided")
            return jsonify({'success': False, 'error': 'No totalClicks provided'}), 400

        update_data = {
            'totalClicks': total_clicks,
            'currentUniverse': data.get('currentUniverse', 'default'),
        }

        # Обновляем данные текущей вселенной
        current_universe = data.get('currentUniverse', 'default')
        if 'upgrades' in data:
            update_data[f"universes.{current_universe}"] = data['upgrades']

        result = users_collection.update_one(
            {'telegram_id': telegram_id},
            {'$set': update_data},
            upsert=True
        )

        logger.info(f"Update result: {result.modified_count}")

        if result.modified_count > 0 or result.upserted_id:
            logger.info(f"Data updated for user {telegram_id}")
            return jsonify({'success': True})
        else:
            logger.warning(f"No changes made for user {telegram_id}")
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))