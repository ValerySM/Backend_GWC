from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from urllib.parse import quote_plus
from bson.objectid import ObjectId
import os

app = Flask(__name__)
CORS(app)

def get_mongo_client():
    username = quote_plus(os.environ.get('MONGO_USERNAME', 'valerysm'))
    password = quote_plus(os.environ.get('MONGO_PASSWORD', 'Janysar190615!@'))
    MONGO_URI = f"mongodb+srv://{username}:{password}@betatest.4k3xh.mongodb.net/?retryWrites=true&w=majority&appName=betaTest"
    return MongoClient(MONGO_URI)

@app.route('/auth', methods=['POST'])
def auth():
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    with get_mongo_client() as client:
        db = client.universe_game_db
        users = db.users
        user = users.find_one_and_update(
            {"_id": ObjectId(user_id)},
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

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    if not data or 'user_id' not in data or 'updates' not in data:
        return jsonify({"error": "Missing user_id or updates in request"}), 400
    
    user_id = data['user_id']
    updates = data['updates']
    
    with get_mongo_client() as client:
        db = client.universe_game_db
        users = db.users
        result = users.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": updates},
            return_document=True
        )

    if result:
        user_data = {k: v for k, v in result.items() if k != '_id'}
        user_data['telegram_id'] = str(result['_id'])
        return jsonify(user_data), 200
    else:
        return jsonify({"error": "User not found"}), 404

@app.route('/user/<user_id>', methods=['GET'])
def get_user(user_id):
    with get_mongo_client() as client:
        db = client.universe_game_db
        users = db.users
        user = users.find_one({"_id": ObjectId(user_id)})
        if user:
            user_data = {k: v for k, v in user.items() if k != '_id'}
            user_data['telegram_id'] = str(user['_id'])
            return jsonify(user_data), 200
        else:
            return jsonify({"error": "User not found"}), 404

@app.route('/log', methods=['POST'])
def log():
    data = request.json
    print(f"Client log: {data['message']}")
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(debug=True)