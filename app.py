from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from urllib.parse import quote_plus
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def get_mongo_client():
    username = quote_plus(os.environ.get('MONGO_USERNAME', 'valerysm'))
    password = quote_plus(os.environ.get('MONGO_PASSWORD', 'Janysar190615!@'))
    MONGO_URI = f"mongodb+srv://{username}:{password}@betatest.4k3xh.mongodb.net/?retryWrites=true&w=majority&appName=betaTest"
    return MongoClient(MONGO_URI)

@app.route('/auth', methods=['POST'])
def auth():
    try:
        user_id = request.json.get('user_id')
        print(f"Received auth request for user_id: {user_id}")
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        with get_mongo_client() as client:
            db = client.universe_game_db
            users = db.users
            user = users.find_one_and_update(
                {"_id": user_id},
                {"$setOnInsert": {
                    "totalClicks": 0,
                    "energy": 1000,
                    "energyMax": 1000,
                    "regenRate": 1,
                    "damageLevel": 1,
                    "energyLevel": 1,
                    "regenLevel": 1,
                    "gameScores": {
                        "appleCatcher": 0,
                        "purblePairs": 0
                    },
                    "eweData": {
                        "tokens": 0,
                        "farmedTokens": 0,
                        "isFarming": False,
                        "startTime": None,
                        "elapsedFarmingTime": 0
                    }
                }},
                upsert=True,
                return_document=True
            )
        
        user_data = {k: v for k, v in user.items() if k != '_id'}
        user_data['telegram_id'] = str(user['_id'])
        print(f"Sending user data: {user_data}")
        return jsonify(user_data), 200
    except Exception as e:
        print(f"Error in auth: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/update', methods=['POST'])
def update():
    try:
        data = request.json
        if not data or 'user_id' not in data or 'updates' not in data:
            return jsonify({"error": "Missing user_id or updates in request"}), 400
        
        user_id = data['user_id']
        updates = data['updates']
        
        print(f"Received update request for user_id: {user_id}")
        print(f"Updates: {updates}")

        with get_mongo_client() as client:
            db = client.universe_game_db
            users = db.users
            result = users.find_one_and_update(
                {"_id": user_id},
                {"$set": updates},
                return_document=True
            )

        if result:
            user_data = {k: v for k, v in result.items() if k != '_id'}
            user_data['telegram_id'] = str(result['_id'])
            print(f"Sending updated user data: {user_data}")
            return jsonify(user_data), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        print(f"Error in update: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/log', methods=['POST'])
def log():
    data = request.json
    print(f"Client log: {data['message']}")
    return jsonify({"status": "success"}), 200

@app.route('/', methods=['GET'])
def home():
    return "Welcome to the GWC Backend!", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)