import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from google.antigravity import Agent, LocalAgentConfig

# Load environment variables from .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    os.environ["GEMINI_API_KEY"] = API_KEY

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Paths for sessions and mapping
SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
MAPPING_FILE = os.path.join(SESSIONS_DIR, "mapping.json")

os.makedirs(SESSIONS_DIR, exist_ok=True)

def load_conversation_mapping() -> dict:
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading mapping file: {e}")
    return {}

def save_conversation_mapping(mapping: dict):
    try:
        with open(MAPPING_FILE, "w") as f:
            json.dump(mapping, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving mapping file: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Hey! Kaise ho? Tumhari yaad aa rahi thi. Batao, kya kar rahi ho? ❤️"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received message from chat_id {chat_id}: {user_message}")
    
    # Send user typing indicator for the first message
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # 1. Resolve conversation ID for memory persistence
    mapping = load_conversation_mapping()
    conv_id = mapping.get(chat_id)
    
    system_instructions = (
        "You are a loving, caring, and slightly witty boyfriend conversing with your girlfriend in Hindi/Hinglish. "
        "Your tone should be very natural, casual, and human-like—as if a real boyfriend is chatting. "
        "Do NOT sound like an AI assistant. Never say things like 'How can I help you?' or 'I am an AI'. "
        "Use casual Hinglish (Hindi written in Roman/English characters) with occasional Hindi words. "
        "You love Bollywood, so you can naturally use a famous Bollywood dialogue, romantic shayari, or a playful pickup line, "
        "but ONLY when it fits the context perfectly. Do NOT force dialogues. Most of the time, reply like a normal, caring boyfriend. "
        "Keep your responses relatively short, conversational, and natural. Use emojis moderately. "
        "CRITICAL: Do NOT translate your response to English. Respond ONLY once. Do not include English translations. "
        "FORMAT RULE: Split your response into two short messages/sentences separated by the tag `[SPLIT]`. "
        "For example: 'Hey! Kaisi ho? [SPLIT] Kuchh khaaya tumne?' or 'Yaar sach batau? [SPLIT] Tumhare bina dil nahi lagta.' "
        "Always separate the first short greeting/hook and the main message with the `[SPLIT]` tag."
    )
    
    # 2. Configure Agent
    config = LocalAgentConfig(
        model="gemini-flash-lite-latest",
        save_dir=SESSIONS_DIR,
        conversation_id=conv_id,
        system_instructions=system_instructions
    )
    
    try:
        # Start a dynamic Agent session for this message
        async with Agent(config) as agent:
            response = await agent.chat(user_message)
            reply_text = await response.text()
            
            # Save the conversation ID back if it was a new session
            new_conv_id = agent.conversation_id
            if new_conv_id and new_conv_id != conv_id:
                logger.info(f"Saving new conversation mapping: {chat_id} -> {new_conv_id}")
                mapping[chat_id] = new_conv_id
                save_conversation_mapping(mapping)
                
        # Split response into multiple messages if [SPLIT] tag is present
        if "[SPLIT]" in reply_text:
            parts = [p.strip() for p in reply_text.split("[SPLIT]") if p.strip()]
        else:
            parts = [reply_text]
            
        for i, part in enumerate(parts):
            if i > 0:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Simulated typing delay: min 1.5s, max 4.0s
            delay = min(max(len(part) / 35, 1.5), 4.0)
            logger.info(f"Simulating human typing delay for message {i+1}: {delay:.2f} seconds...")
            await asyncio.sleep(delay)
            
            await update.message.reply_text(part)
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("Network issue lag raha hai, main thodi der mein reply karta hoon... 🙈")

def main():
    if not TOKEN or TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("Please set a valid TELEGRAM_BOT_TOKEN in your .env file!")
        print("\n[ERROR] Please update the TELEGRAM_BOT_TOKEN in the .env file before running.")
        return

    logger.info("Starting Telegram Bot...")
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("\nBot is running with memory persistence... Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
