import os
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
from urllib.parse import quote_plus

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB URI from environment variables
username = quote_plus(os.getenv('MONGO_USERNAME', 'valerysm'))
password = quote_plus(os.getenv('MONGO_PASSWORD', 'Janysar190615!@'))
MONGO_URI = f"mongodb+srv://{username}:{password}@betatest.4k3xh.mongodb.net/?retryWrites=true&w=majority&appName=betaTest"

def get_db():
    if 'db' not in g:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        g.db = client.universe_game_db
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.client.close()

@app.route('/')
def hello():
    return "Hello, World! Universe Game Application is running."

@app.route('/api/auth', methods=['POST'])
def authenticate():
    try:
        db = get_db()
        users_collection = db.users

        data = request.json
        user_id = str(data.get('user_id'))
        username = data.get('username')

        logger.info(f"Received auth request for user_id: {user_id}, username: {username}")

        if not user_id:
            return jsonify({'success': False, 'error': 'No User ID provided'}), 400

        user = users_collection.find_one({'_id': user_id})

        if user:
            logger.info(f"Found existing user: {user}")
            if user.get('username') != username:
                users_collection.update_one({'_id': user['_id']}, {'$set': {'username': username}})
                user['username'] = username
                logger.info(f"Updated username for user: {user}")
        else:
            new_user = {
                '_id': user_id,
                'username': username,
                'totalClicks': 0,
                'currentUniverse': 'default',
                'universes': {}
            }
            users_collection.insert_one(new_user)
            user = new_user
            logger.info(f"Created new user: {user}")

        response_data = {
            'success': True,
            'user_id': user['_id'],
            'username': user.get('username'),
            'totalClicks': user.get('totalClicks', 0),
            'currentUniverse': user.get('currentUniverse', 'default'),
            'universes': user.get('universes', {})
        }
        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/update_clicks', methods=['POST'])
def update_clicks():
    try:
        db = get_db()
        users_collection = db.users

        data = request.json
        user_id = str(data.get('user_id'))
        total_clicks = data.get('totalClicks')
        current_universe = data.get('currentUniverse', 'default')
        upgrades = data.get('upgrades', {})

        logger.info(f"Received update request for user_id: {user_id}, total_clicks: {total_clicks}")

        if not user_id or total_clicks is None:
            return jsonify({'success': False, 'error': 'User ID and totalClicks are required'}), 400

        update_data = {
            'totalClicks': total_clicks,
            'currentUniverse': current_universe,
            f"universes.{current_universe}": upgrades
        }

        logger.info(f"Updating user data: {update_data}")

        result = users_collection.update_one(
            {'_id': user_id},
            {'$set': update_data},
            upsert=True
        )

        if result.modified_count > 0 or result.upserted_id:
            logger.info(f"Successfully updated user data for user_id: {user_id}")
            return jsonify({'success': True})
        else:
            logger.warning(f"No changes made for user_id: {user_id}")
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
    app.run(host='0.0.0.0', port=port, debug=True)
    logger.info(f"App running on port {port}")