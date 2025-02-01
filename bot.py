import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ADMIN_IDS = list(map(int, os.getenv("ADMINS", "").split(",")))  # Convert to list of integers

# Setup logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_collection = db["users"]
messages_collection = db["messages"]

# Initialize bot application
app = Application.builder().token(BOT_TOKEN).build()

# ✅ Health Check Server (Required for Koyeb)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_check_server():
    server = HTTPServer(("0.0.0.0", 8000), HealthCheckHandler)
    server.serve_forever()

# Run health check in background
threading.Thread(target=run_health_check_server, daemon=True).start()

# ✅ Register Users
async def register_user(user_id):
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})

# ✅ Command: /start
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    await register_user(user_id)
    await update.message.reply_text("Welcome! Use /getall to get old messages. Use /menu for commands.")
    await update.message.delete()

# ✅ Command: Get Old Messages
async def get_all_messages(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    messages = messages_collection.find().sort("_id", 1)

    for msg in messages:
        await context.bot.send_message(chat_id=user_id, text=msg["text"])

    await update.message.delete()

# ✅ Forward Channel Posts to Users
async def forward_channel_post(update: Update, context: CallbackContext):
    if update.channel_post:
        message_text = update.channel_post.text or update.channel_post.caption
        if not message_text:
            return
        
        # Log the incoming message
        logger.info(f"Forwarding new message: {message_text}")

        # Save message to database
        messages_collection.insert_one({"text": message_text})  # Store in DB

        # Forward message to users
        users = users_collection.find()

        for user in users:
            try:
                await context.bot.send_message(chat_id=user["user_id"], text=message_text)
                logger.info(f"Message forwarded to {user['user_id']}")
            except Exception as e:
                logger.warning(f"Failed to send message to {user['user_id']}: {e}")

# ✅ Command: User Count (Admin Only)
async def user_count(update: Update, context: CallbackContext):
    if update.message.from_user.id in ADMIN_IDS:
        count = users_collection.count_documents({})
        await update.message.reply_text(f"Total Users: {count}")
        await update.message.delete()

# ✅ Command: Show Menu
async def menu(update: Update, context: CallbackContext):
    commands = """
Available Commands:
/getall - Get old messages
/menu - Show this menu

(Admins)
/usercount - Get total users
    """
    await update.message.reply_text(commands)
    await update.message.delete()

# ✅ Auto-delete user messages
async def delete_user_messages(update: Update, context: CallbackContext):
    await update.message.delete()

# ✅ Add Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("getall", get_all_messages))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("usercount", user_count))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, delete_user_messages))
app.add_handler(MessageHandler(filters.Chat(CHANNEL_ID) & filters.ALL, forward_channel_post))

# ✅ Start the bot
if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
