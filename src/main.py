import os
import logging
import asyncio
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from data_manager import DataManager
from agents.router_agent import RouterAgent

# Load env
load_dotenv()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize systems
dm = DataManager()
agent = RouterAgent(dm)

def _agent_response_text(result) -> str:
    if isinstance(result, dict):
        return str(result.get("response", ""))
    return str(result)

def _photo_suffix(file_path: str = "") -> str:
    suffix = Path(file_path or "").suffix.lower()
    return suffix if suffix and len(suffix) <= 10 else ".jpg"

def _new_photo_temp_path(file_path: str = "") -> str:
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        prefix="foodflow_telegram_",
        suffix=_photo_suffix(file_path),
    )
    temp_file.close()
    return temp_file.name

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! I am your FoodFlow assistant. I can help you manage your kitchen and diet. Send me messages like 'I bought milk' or 'What should I cook?'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    # Process with Agent
    result = await asyncio.to_thread(agent.process_message, user_text)
    response = _agent_response_text(result)
    
    await context.bot.send_message(chat_id=chat_id, text=response)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Retrieve photo file
    photo_file = await update.message.photo[-1].get_file()
    custom_path = _new_photo_temp_path(getattr(photo_file, "file_path", ""))
    await photo_file.download_to_drive(custom_path)
    
    user_text = update.message.caption or "Analyze this image"
    
    try:
        result = await asyncio.to_thread(agent.process_message, user_text, custom_path)
        response = _agent_response_text(result)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    finally:
        # Cleanup
        if os.path.exists(custom_path):
            os.remove(custom_path)

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        print("Error: TELEGRAM_TOKEN not set in .env")
        exit(1)
        
    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    photo_handler = MessageHandler(filters.PHOTO, handle_photo)
    
    application.add_handler(start_handler)
    application.add_handler(msg_handler)
    application.add_handler(photo_handler)
    
    print("Bot is running...")
    application.run_polling()
