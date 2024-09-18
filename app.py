import os
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)

load_dotenv()

app = Flask(__name__)
CORS(app)

# Подключение к MongoDB
try:
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client['gwc_database']
    users = db['users']
except PyMongoError as e:
    logging.error(f"Failed to connect to MongoDB: {e}")
    exit(1)

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    if not data or 'user_id' not in data:
        abort(400, description="Missing user_id in request")
    
    user_id = data['user_id']
    
    try:
        user = users.find_one({'user_id': user_id})
        if not user:
            # Создаем нового пользователя с начальными данными
            new_user = {
                'user_id': user_id,
                'totalClicks': 0,
                'energy': 1000,
                'energyMax': 1000,
                'regenRate': 1,
                'damageLevel': 1,
                'energyLevel': 1,
                'regenLevel': 1,
                'gameScores': {
                    'appleCatcher': 0,
                    'purblePairs': 0
                },
                'eweData': {
                    'tokens': 0,
                    'farmedTokens': 0,
                    'isFarming': False,
                    'startTime': None,
                    'elapsedFarmingTime': 0
                },
                'lastUpdate': datetime.now()
            }
            users.insert_one(new_user)
            user = new_user
            logging.info(f"Created new user: {user_id}")
        else:
            logging.info(f"Found existing user: {user_id}")

        # Удаляем '_id' из ответа, так как оно не сериализуется в JSON
        user.pop('_id', None)
        return jsonify(user)
    except PyMongoError as e:
        logging.error(f"Database error: {e}")
        abort(500, description="Internal server error")

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    if not data or 'user_id' not in data or 'updates' not in data:
        abort(400, description="Missing user_id or updates in request")
    
    user_id = data['user_id']
    updates = data['updates']
    
    try:
        result = users.update_one({'user_id': user_id}, {'$set': updates})
        if result.modified_count == 0:
            logging.warning(f"No updates made for user: {user_id}")
            abort(404, description="User not found")
        logging.info(f"Updated user data: {user_id}")
        return jsonify({'status': 'success'})
    except PyMongoError as e:
        logging.error(f"Database error: {e}")
        abort(500, description="Internal server error")

@app.route('/test', methods=['GET'])
def test():
    logging.info("Test endpoint accessed")
    return "Backend is running on Render!", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logging.info(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port)