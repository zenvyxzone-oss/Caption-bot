import whisper
import subprocess
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from googletrans import Translator

# Token Railway Variables se uthayega
TOKEN = os.getenv("BOT_TOKEN", "8636371592:AAHffOoYiJ0bCcx1lAq5Yh67i-zrgwDh0cg")

print("Loading Model...")
model = whisper.load_model("tiny") # Tiny model is best for Railway free tier
translator = Translator()

def format_time(ti):
    h, m, s = int(ti//3600), int((ti%3600)//60), int(ti%60)
    ms = int((ti - int(ti)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Video bhejein, main auto-subtitle add kar dunga!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    msg = await update.message.reply_text("📥 Downloading video...")
    
    file = await update.message.video.get_file()
    v_path = f"{user_id}.mp4"
    await file.download_to_drive(v_path)
    
    keyboard = [[
        InlineKeyboardButton("English 🇺🇸", callback_data=f"en_{user_id}"),
        InlineKeyboardButton("Hindi 🇮🇳", callback_data=f"hi_{user_id}")
    ]]
    await msg.edit_text("🌐 Subtitle language choose karein:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lang, u_id = query.data.split("_")
    v_path, s_path, o_path = f"{u_id}.mp4", f"{u_id}.srt", f"out_{u_id}.mp4"

    if not os.path.exists(v_path):
        await query.message.reply_text("❌ File nahi mili!")
        return

    m = await query.message.reply_text("⏳ Processing... (Whisper is working)")

    try:
        result = model.transcribe(v_path)
        with open(s_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(result["segments"]):
                txt = seg["text"].strip()
                if lang == "hi":
                    try: txt = translator.translate(txt, dest="hi").text
                    except: pass
                f.write(f"{i+1}\n{format_time(seg['start'])} --> {format_time(seg['end'])}\n{txt}\n\n")

        await m.edit_text("🎬 Rendering subtitles into video...")
        subprocess.run(["ffmpeg", "-y", "-i", v_path, "-vf", f"subtitles={s_path}", o_path], check=True)
        
        await query.message.reply_video(video=open(o_path, "rb"), caption="✅ Subtitles Added!")
    except Exception as e:
        await query.message.reply_text(f"❌ Error: {e}")
    finally:
        for f in [v_path, s_path, o_path]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot is LIVE! 🚀")
    app.run_polling()
    
