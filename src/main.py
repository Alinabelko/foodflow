import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from data_manager import DataManager
from agent import NutritionAgent

# Load env
load_dotenv()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize systems
dm = DataManager()
agent = NutritionAgent(dm)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! I am your FoodFlow assistant. I can help you manage your kitchen and diet. Send me messages like 'I bought milk' or 'What should I cook?'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    # Process with Agent
    response = agent.process_message(user_text)
    
    await context.bot.send_message(chat_id=chat_id, text=response)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Retrieve photo file
    photo_file = await update.message.photo[-1].get_file()
    # Save to temp
    custom_path = f"temp_{photo_file.file_unique_id}.jpg"
    await photo_file.download_to_drive(custom_path)
    
    user_text = update.message.caption or "Analyze this image"
    
    # Process with Agent (assuming agent handles image path)
    # Note: Agent needs to implement image reading logic or pass URL if using GPT-4-Vision with URLs
    # For local files with standard OpenAI lib, we'd base64 encode it in agent.py
    try:
        response = agent.process_message(user_text, image_path=custom_path)
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
