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

@app.route('/api/auth', methods=['POST'])
def authenticate():
    if not client:
        logger.error("Database connection failed")
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500

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
            'totalClicks': 0
        }
        result = users_collection.insert_one(new_user)
        logger.info(f"Created new user with ID: {result.inserted_id}")
        user = new_user
    else:
        logger.info(f"Existing user found: {user['_id']}")

    logger.info(f"Returning data for user: {user}")
    return jsonify({
        'success': True,
        'telegram_id': user['telegram_id'],
        'username': user['username'],
        'universe_data': {
            'totalClicks': user.get('totalClicks', 0)
        }
    })

@app.route('/api/users', methods=['PUT'])
def update_user_data():
    if not client:
        logger.error("Database connection failed")
        return jsonify({'success': False, 'error': 'Database connection failed'}), 500

    data = request.json
    telegram_id = data.get('telegram_id')
    total_clicks = data.get('totalClicks')

    if not telegram_id:
        logger.error("No Telegram ID provided")
        return jsonify({'success': False, 'error': 'No Telegram ID provided'}), 400

    if total_clicks is None:
        logger.error("No totalClicks provided")
        return jsonify({'success': False, 'error': 'No totalClicks provided'}), 400

    result = users_collection.update_one(
        {'telegram_id': telegram_id},
        {'$set': {'totalClicks': total_clicks}}
    )

    if result.modified_count > 0:
        logger.info(f"Data updated for user {telegram_id}")
        return jsonify({'success': True})
    else:
        logger.warning(f"No changes made for user {telegram_id}")
        return jsonify({'success': False, 'error': 'No changes made'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))