import telebot
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import urllib.parse

BOT_TOKEN = '7280558655:AAEFiRuOTmd0tqgVaTUSQ9DEEZdOARYpcCw'
BACKEND_URL = 'https://backend-gwc-1.onrender.com'
WEBAPP_URL = 'https://valerysm.github.io/Frontend_GWC/'

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    try:
        # Send telegram_id and username to backend
        response = requests.post(f'{BACKEND_URL}/api/auth', json={
            'telegram_id': telegram_id,
            'username': username
        })
        
        # Check server response
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                # Encode username for handling special characters
                encoded_username = urllib.parse.quote(username)
                webapp_link = f'{WEBAPP_URL}?telegram_id={telegram_id}&username={encoded_username}'
                
                keyboard = InlineKeyboardMarkup()
                webapp_button = InlineKeyboardButton("Play", web_app=WebAppInfo(url=webapp_link))
                keyboard.add(webapp_button)
                
                bot.send_message(
                    message.chat.id, 
                    "Welcome! Click the button to open the application:",
                    reply_markup=keyboard
                )
            else:
                bot.reply_to(message, f"Server error: {data.get('error', 'Unknown error')}")
        else:
            bot.reply_to(message, f"Error: {response.status_code} - {response.text}")
    
    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"Server connection error: {e}")

bot.polling()