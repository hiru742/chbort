import logging
import os
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from pymongo import MongoClient
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ✅ Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ✅ Environment Variables
TOKEN = os.getenv("BOT_TOKEN")  # Telegram Bot Token
MONGO_URI = os.getenv("MONGO_URI")  # MongoDB Connection
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Forwarding Channel ID (Use negative ID)
ADMINS = os.getenv("ADMINS", "").split(",")  # List of Admin User IDs

# ✅ Database Connection
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_col = db["users"]

# ✅ Initialize Bot
bot = Bot(token=TOKEN)

# ✅ Dummy Health Check Server (Required for Koyeb)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check_server():
    server = HTTPServer(("0.0.0.0", 8000), HealthCheckHandler)
    server.serve_forever()

# Start the health check server in a separate thread
health_thread = threading.Thread(target=run_health_check_server, daemon=True)
health_thread.start()

# ✅ Function to Forward New Channel Messages
async def forward_channel_post(update: Update, context: CallbackContext):
    if update.channel_post:
        message = update.channel_post
        users = users_col.find()
        for user in users:
            try:
                await bot.copy_message(chat_id=user["_id"], from_chat_id=message.chat_id, message_id=message.message_id)
            except Exception as e:
                logging.error(f"Error forwarding to {user['_id']}: {e}")

# ✅ Start Command - Register User & Show Menu
async def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    users_col.update_one({"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True)
    await update.message.reply_text("✅ Welcome! Use /menu to see available commands.")
    await delete_message(update)

# ✅ Get All Old Messages from Channel
async def get_old_messages(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    messages = context.bot.get_chat(CHANNEL_ID).get_history()
    for msg in messages:
        try:
            await bot.copy_message(chat_id=user_id, from_chat_id=CHANNEL_ID, message_id=msg.message_id)
        except Exception as e:
            logging.error(f"Error sending old messages: {e}")
    await delete_message(update)

# ✅ Show Bot Commands
async def show_menu(update: Update, context: CallbackContext):
    commands = "📌 Available Commands:\n"
    commands += "/start - Register & Receive Updates\n"
    commands += "/getall - Retrieve Old Messages\n"
    commands += "/menu - Show Commands\n"
    if str(update.message.chat_id) in ADMINS:
        commands += "\n👑 Admin Commands:\n"
        commands += "/usercount - Get User Count\n"
    await update.message.reply_text(commands)
    await delete_message(update)

# ✅ Get User Count (Admin Only)
async def get_user_count(update: Update, context: CallbackContext):
    if str(update.message.chat_id) in ADMINS:
        count = users_col.count_documents({})
        await update.message.reply_text(f"👥 Total Users: {count}")
    await delete_message(update)


# ✅ Delete User Messages
async def delete_message(update: Update):
    try:
        await asyncio.sleep(2)  # Wait before deletion
        await bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
    except:
        pass

# ✅ Main Function
def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("getall", get_old_messages))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("usercount", get_user_count))
    app.add_handler(MessageHandler(filters.Chat(CHANNEL_ID), forward_channel_post))

    # Run the bot
    app.run_polling()

if __name__ == "__main__":
    main()
