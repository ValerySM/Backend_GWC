import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import telebot

load_dotenv()

app = Flask(__name__)
CORS(app)

# Подключение к MongoDB
client = MongoClient(os.getenv('MONGO_URI'))
db = client['gwc_database']
users = db['users']

# Инициализация бота
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    user_id = data['user_id']
    
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
            'lastUpdate': None
        }
        users.insert_one(new_user)
        user = new_user

    # Удаляем '_id' из ответа, так как оно не сериализуется в JSON
    user.pop('_id', None)
    return jsonify(user)

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    user_id = data['user_id']
    updates = data['updates']
    
    users.update_one({'user_id': user_id}, {'$set': updates})
    return jsonify({'status': 'success'})

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"Welcome! Click the button below to start playing.", 
                 reply_markup=telebot.types.InlineKeyboardMarkup().add(
                     telebot.types.InlineKeyboardButton(
                         text="Play", 
                         web_app=telebot.types.WebAppInfo(url=f"{os.getenv('WEBAPP_URL')}?user_id={user_id}")
                     )
                 ))

if __name__ == '__main__':
    app.run(debug=True)