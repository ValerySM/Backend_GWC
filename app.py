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
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    with get_mongo_client() as client:
        db = client.universe_game_db
        users = db.users
        user = users.find_one_and_update(
            {"_id": user_id},
            {"$setOnInsert": {"clicks": 0}},
            upsert=True,
            return_document=True
        )

    return jsonify({"clicks": user['clicks'], "isNewUser": user.get('clicks', 0) == 0}), 200

@app.route('/update_clicks', methods=['POST'])
def update_clicks():
    user_id = request.json.get('user_id')
    clicks = request.json.get('clicks')
    
    if not user_id or clicks is None:
        return jsonify({"error": "User ID and clicks are required"}), 400

    with get_mongo_client() as client:
        db = client.universe_game_db
        users = db.users
        result = users.find_one_and_update(
            {"_id": user_id},
            {"$set": {"clicks": clicks}},
            return_document=True
        )

    if result:
        return jsonify({"success": True, "clicks": result['clicks']}), 200
    else:
        return jsonify({"error": "User not found"}), 404

@app.route('/api/log', methods=['POST', 'OPTIONS'])
def log_message():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.json
        print(f"Client log: {data}")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error logging message: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)