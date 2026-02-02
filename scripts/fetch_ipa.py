import os
import sys
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Config
API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION_STR = os.environ["TELEGRAM_SESSION"]
BOT_USERNAME = "@fastdecryptbot" # Or @eeveedecrypterbot
DOWNLOAD_DIR = "build_temp"

async def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_ipa.py <app_store_url>")
        sys.exit(1)

    app_url = sys.argv[1]
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    print(f"🤖 Connecting to Telegram...")
    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    await client.start()

    print(f"📨 Sending request to {BOT_USERNAME} for: {app_url}")
    
    async with client.conversation(BOT_USERNAME, timeout=300) as conv:
        # Send the link
        await conv.send_message(app_url)
        
        print("⏳ Waiting for bot response (this may take a few minutes)...")
        
        # Wait for a response containing a file
        response = await conv.get_response()
        
        # Sometimes bots send a "Processing..." message first, so we might need to wait for the next one
        while "processing" in response.text.lower() or "queue" in response.text.lower():
            print(f"Bot says: {response.text} - Waiting..." )
            response = await conv.get_response()

        if response.media:
            print("📦 File found! Downloading...")
            
            # Progress callback
            def progress_callback(current, total):
                print(f"Download: {current * 100 / total:.1f}%", end='\r')

            path = await response.download_media(file=DOWNLOAD_DIR, progress_callback=progress_callback)
            print(f"\n✅ Download complete: {path}")
            
            # Rename to standard name for the next step
            final_path = os.path.join(DOWNLOAD_DIR, "source.ipa")
            os.rename(path, final_path)
        else:
            print("❌ Bot did not return a file. Response text:")
            print(response.text)
            sys.exit(1)

    await client.disconnect()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
