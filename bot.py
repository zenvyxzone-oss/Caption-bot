import whisper
import subprocess
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from googletrans import Translator

# --- AAPKA TOKEN ---
TOKEN = "8636371592:AAHffOoYiJ0bCcx1lAq5Yh67i-zrgwDh0cg"

# Model loading
print("Loading Whisper Model...")
model = whisper.load_model("base")
translator = Translator()

user_video = {}

# Time formatter for SRT
def format_time(ti):
    h = int(ti // 3600)
    m = int((ti % 3600) // 60)
    s = int(ti % 60)
    ms = int((ti - int(ti)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Video bhejo → language select karo → subtitle ready 🎬")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    msg = await update.message.reply_text("📥 Video download ho rahi hai...")
    
    file = await update.message.video.get_file()
    video_path = f"video_{user_id}.mp4"
    await file.download_to_drive(video_path)
    
    user_video[user_id] = video_path

    keyboard = [[
        InlineKeyboardButton("English 🇺🇸", callback_data="en"),
        InlineKeyboardButton("Hindi 🇮🇳", callback_data="hi")
    ]]
    await msg.edit_text("🌐 Subtitle ki language chunein:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    video_path = user_video.get(user_id)
    srt_path = f"sub_{user_id}.srt"
    out_path = f"out_{user_id}.mp4"

    if not video_path or not os.path.exists(video_path):
        await query.message.reply_text("❌ File nahi mili, dobara try karein.")
        return

    status = await query.message.reply_text("⏳ Processing shuru... (Isme 1-2 minute lag sakte hain)")

    try:
        # Step 1: Transcribe
        await status.edit_text("✍️ Awaaz ko text mein badla ja raha hai...")
        result = model.transcribe(video_path)
        
        # Step 2: Create SRT
        await status.edit_text("📝 Subtitles file ban rahi hai...")
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(result["segments"]):
                t = seg["text"].strip()
                if query.data == "hi":
                    try:
                        t = translator.translate(t, dest="hi").text
                    except: pass
                
                f.write(f"{i+1}\n{format_time(seg['start'])} --> {format_time(seg['end'])}\n{t}\n\n")

        # Step 3: Burn subtitles with FFmpeg
        await status.edit_text("🎬 Video render ho rahi hai...")
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"subtitles={srt_path}",
            out_path
        ], check=True)

        # Step 4: Send Video
        await query.message.reply_video(video=open(out_path, "rb"), caption="✅ Done!")

    except Exception as e:
        await query.message.reply_text(f"❌ Error aaya: {str(e)}")
    
    finally:
        # Sab kuch saaf (cleanup) karein
        await status.delete()
        for f in [video_path, srt_path, out_path]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot is running! 🚀")
    app.run_polling()
    
