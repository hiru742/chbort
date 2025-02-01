import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from pymongo import MongoClient

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")  # Default to local MongoDB
DB_NAME = "telegram_bot"
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
users_collection = db["users"]
messages_collection = db["messages"]
admins_collection = db["admins"]

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    users_collection.update_one({"_id": user_id}, {"$set": {"username": update.message.from_user.username}}, upsert=True)
    await update.message.reply_text("Welcome! Use /help to see available commands.")

# Help command
async def help_command(update: Update, context: CallbackContext) -> None:
    commands = """
    Available commands:
    /start - Start the bot
    /help - Show this help message
    /getoldmessages - Get all old messages
    """
    await update.message.reply_text(commands)

# Forward messages to all users
async def forward_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    message_data = {
        "text": message.text,
        "chat_id": message.chat_id,
        "message_id": message.message_id,
        "timestamp": message.date
    }
    messages_collection.insert_one(message_data)

    # Forward the message to all users
    for user in users_collection.find():
        try:
            await context.bot.forward_message(chat_id=user["_id"], from_chat_id=message.chat_id, message_id=message.message_id)
        except Exception as e:
            logger.error(f"Failed to forward message to user {user['_id']}: {e}")

# Get old messages
async def get_old_messages(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if users_collection.find_one({"_id": user_id}):
        for msg in messages_collection.find().sort("timestamp"):
            await update.message.reply_text(msg["text"])
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Delete user messages
async def delete_user_message(update: Update, context: CallbackContext) -> None:
    await update.message.delete()

# Admin command: Get user count
async def get_user_count(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if admins_collection.find_one({"_id": user_id}):
        user_count = users_collection.count_documents({})
        await update.message.reply_text(f"Total users: {user_count}")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Add admin
async def add_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if admins_collection.find_one({"_id": user_id}):
        try:
            new_admin_id = int(context.args[0])
            admins_collection.update_one({"_id": new_admin_id}, {"$set": {"username": update.message.from_user.username}}, upsert=True)
            await update.message.reply_text(f"Added admin with ID: {new_admin_id}")
        except (IndexError, ValueError):
            await update.message.reply_text("Usage: /addadmin <user_id>")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Main function
def main() -> None:
    # Replace 'YOUR_BOT_TOKEN' with your bot's token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is missing!")

    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("getoldmessages", get_old_messages))
    application.add_handler(CommandHandler("getusercount", get_user_count))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))
    application.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, delete_user_message))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
