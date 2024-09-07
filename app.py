from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongodb_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongodb_uri)
db = client['universe_game_db']

@app.route('/api/auth', methods=['POST'])
def authenticate():
    try:
        data = request.json
        telegram_id = str(data.get('telegram_id'))

        logger.info(f"Received auth request for telegram_id: {telegram_id}")

        if not telegram_id:
            return jsonify({'success': False, 'error': 'No Telegram ID provided'}), 400

        user = db.users.find_one({'telegram_id': telegram_id})

        if not user:
            user = {
                'telegram_id': telegram_id,
                'totalClicks': 0
            }
            db.users.insert_one(user)
            logger.info(f"Created new user: {user}")
        else:
            logger.info(f"Found existing user: {user}")

        response_data = {
            'success': True,
            'telegram_id': user['telegram_id'],
            'totalClicks': user['totalClicks']
        }
        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error during authentication: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/users', methods=['PUT'])
def update_user_data():
    try:
        data = request.json
        telegram_id = str(data.get('telegram_id'))
        total_clicks = data.get('totalClicks')

        logger.info(f"Received update request for telegram_id: {telegram_id}, total_clicks: {total_clicks}")

        if not telegram_id:
            return jsonify({'success': False, 'error': 'No Telegram ID provided'}), 400

        if total_clicks is None:
            return jsonify({'success': False, 'error': 'No totalClicks provided'}), 400

        result = db.users.update_one(
            {'telegram_id': telegram_id},
            {'$set': {'totalClicks': total_clicks}},
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

if __name__ == '__main__':
    app.run(debug=True)