import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from google.antigravity import Agent, LocalAgentConfig

# Load environment variables
load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
GIRLFRIEND_USERNAME = os.getenv("GIRLFRIEND_USERNAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

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

# Validate credentials
if not API_ID or not API_HASH:
    logger.error("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in your .env file!")
    print("\n[ERROR] Please update TELEGRAM_API_ID and TELEGRAM_API_HASH in the .env file.")
    exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error("TELEGRAM_API_ID must be an integer!")
    exit(1)

# Initialize Telethon Client (saves session details in 'session_name.session')
client = TelegramClient('session_name', API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):
    # Only process private direct messages (DMs)
    if not event.is_private:
        return
        
    sender = await event.get_sender()
    if not sender:
        return

    # Filter messages so we only reply to the girlfriend
    target_username = (GIRLFRIEND_USERNAME or "").lstrip('@').lower()
    sender_username = (sender.username or "").lower()
    sender_phone = getattr(sender, 'phone', '') or ""

    is_girlfriend = False
    if target_username and sender_username == target_username:
        is_girlfriend = True
    elif GIRLFRIEND_USERNAME and (GIRLFRIEND_USERNAME in sender_phone or sender_phone == GIRLFRIEND_USERNAME):
        is_girlfriend = True

    if not is_girlfriend:
        return

    chat_id = str(event.chat_id)
    user_message = event.text
    logger.info(f"Girlfriend messaged: {user_message}")

    # Send "typing" indicator continuously while creating response
    async with client.action(event.chat_id, 'typing'):
        
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
            # Start dynamic Agent session
            async with Agent(config) as agent:
                response = await agent.chat(user_message)
                reply_text = await response.text()
                
                # Save conversation mapping
                new_conv_id = agent.conversation_id
                if new_conv_id and new_conv_id != conv_id:
                    logger.info(f"Saving new conversation mapping: {chat_id} -> {new_conv_id}")
                    mapping[chat_id] = new_conv_id
                    save_conversation_mapping(mapping)
                    
            # Split responses
            if "[SPLIT]" in reply_text:
                parts = [p.strip() for p in reply_text.split("[SPLIT]") if p.strip()]
            else:
                parts = [reply_text]
                
            for i, part in enumerate(parts):
                if i > 0:
                    await asyncio.sleep(0.5)
                    # Send typing indicator for the follow-up message
                    async with client.action(event.chat_id, 'typing'):
                        delay = min(max(len(part) / 35, 1.5), 4.0)
                        logger.info(f"Simulating human typing delay for message {i+1}: {delay:.2f} seconds...")
                        await asyncio.sleep(delay)
                        await event.reply(part)
                else:
                    delay = min(max(len(part) / 35, 1.5), 4.0)
                    logger.info(f"Simulating human typing delay for message {i+1}: {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                    await event.reply(part)
                    
        except Exception as e:
            logger.error(f"Error handling userbot message: {e}")
            await event.reply("Network issue lag raha hai, main thodi der mein reply karta hoon... 🙈")

async def main():
    logger.info("Starting Telegram Userbot Client...")
    await client.start()
    logger.info("Userbot is successfully running. Listening for girlfriend's messages...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
