import os
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

load_dotenv()

app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})

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
    
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify(error=str(e)), 500    

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
        return jsonify({'success': False, 'error': str(e)}), 500

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
    logger.info(f"App running on port {port}")