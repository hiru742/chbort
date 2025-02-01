import logging
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Store admin IDs and user IDs
ADMINS = set()  # Add admin IDs here
USERS = set()   # Store user IDs
MESSAGES = []   # Store all messages

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    USERS.add(user_id)
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
    MESSAGES.append(message.text)
    for user_id in USERS:
        try:
            await context.bot.forward_message(chat_id=user_id, from_chat_id=message.chat_id, message_id=message.message_id)
        except Exception as e:
            logger.error(f"Failed to forward message to user {user_id}: {e}")

# Get old messages
async def get_old_messages(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in USERS:
        for msg in MESSAGES:
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Delete user messages
async def delete_user_message(update: Update, context: CallbackContext) -> None:
    await update.message.delete()

# Admin command: Get user count
async def get_user_count(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in ADMINS:
        await update.message.reply_text(f"Total users: {len(USERS)}")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Add admin
async def add_admin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in ADMINS:
        try:
            new_admin_id = int(context.args[0])
            ADMINS.add(new_admin_id)
            await update.message.reply_text(f"Added admin with ID: {new_admin_id}")
        except (IndexError, ValueError):
            await update.message.reply_text("Usage: /addadmin <user_id>")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Main function
def main() -> None:
    # Replace 'YOUR_BOT_TOKEN' with your bot's token
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

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
