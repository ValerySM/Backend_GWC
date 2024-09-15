from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from urllib.parse import quote_plus
import os
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mongo_client():
    username = quote_plus(os.environ.get('MONGO_USERNAME', 'valerysm'))
    password = quote_plus(os.environ.get('MONGO_PASSWORD', 'Janysar190615!@'))
    MONGO_URI = f"mongodb+srv://{username}:{password}@betatest.4k3xh.mongodb.net/?retryWrites=true&w=majority&appName=betaTest"
    return MongoClient(MONGO_URI)

@app.route('/auth', methods=['POST'])
def auth():
    telegram_id = request.json.get('telegram_id')
    if not telegram_id:
        return jsonify({"error": "Telegram ID is required"}), 400

    with get_mongo_client() as client:
        db = client.universe_game_db
        users = db.users
        user = users.find_one_and_update(
            {"_id": telegram_id},
            {"$setOnInsert": {"totalClicks": 0, "currentUniverse": "default", "universes": {}}},
            upsert=True,
            return_document=True
        )

    logger.info(f"User authenticated: {telegram_id}")
    return jsonify({
        "success": True,
        "user_id": user['_id'],
        "totalClicks": user['totalClicks'],
        "currentUniverse": user['currentUniverse'],
        "universes": user['universes'],
        "isNewUser": user.get('totalClicks', 0) == 0
    }), 200

@app.route('/update_clicks', methods=['POST'])
def update_clicks():
    telegram_id = request.json.get('telegram_id')
    total_clicks = request.json.get('totalClicks')
    current_universe = request.json.get('currentUniverse', 'default')
    upgrades = request.json.get('upgrades', {})
    
    if not telegram_id or total_clicks is None:
        return jsonify({"error": "Telegram ID and totalClicks are required"}), 400

    with get_mongo_client() as client:
        db = client.universe_game_db
        users = db.users
        result = users.find_one_and_update(
            {"_id": telegram_id},
            {"$set": {
                "totalClicks": total_clicks,
                "currentUniverse": current_universe,
                f"universes.{current_universe}": upgrades
            }},
            return_document=True
        )

    if result:
        logger.info(f"Updated clicks for user {telegram_id}: {total_clicks}")
        return jsonify({"success": True, "totalClicks": result['totalClicks']}), 200
    else:
        logger.warning(f"User not found: {telegram_id}")
        return jsonify({"error": "User not found"}), 404

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