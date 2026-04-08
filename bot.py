import whisper
import subprocess
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

TOKEN = "8636371592:AAHffOoYiJ0bCcx1lAq5Yh67i-zrgwDh0cg"

model = whisper.load_model("base")
translator = Translator()

# Temporary storage
user_video = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Video bhejo → language select karo → subtitle ready 🎬"
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Commands:\n"
        "/start - Start bot\n"
        "/help - Help\n\n"
        "🎬 Video bhejo → language choose karo"
    )

# Step 1: Video receive
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    file = await update.message.video.get_file()
    await file.download_to_drive(f"{user_id}.mp4")

    user_video[user_id] = f"{user_id}.mp4"

    # Inline buttons
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="en"),
            InlineKeyboardButton("English → Hindi", callback_data="hi"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌐 Select your language:",
        reply_markup=reply_markup
    )

# Step 2: Button click
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    video_path = user_video.get(user_id)

    if not video_path:
        await query.message.reply_text("❗ Video not found")
        return

    msg = await query.message.reply_text("⏳ Processing...")

    # Speech to text
    result = model.transcribe(video_path)
    text = result["text"]

    # Translation
    if query.data == "hi":
        text = translator.translate(text, dest="hi").text

    # Create SRT
    with open("sub.srt", "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"]):
            start = seg["start"]
            end = seg["end"]
            t = seg["text"]

            if query.data == "hi":
                t = translator.translate(t, dest="hi").text

            def format_time(ti):
                h = int(ti // 3600)
                m = int((ti % 3600) // 60)
                s = int(ti % 60)
                ms = int((ti - int(ti)) * 1000)
                return f"{h:02}:{m:02}:{s:02},{ms:03}"

            f.write(f"{i+1}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{t}\n\n")

    # Embed subtitle
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vf", "subtitles=sub.srt",
        "out.mp4"
    ])

    # Send result
    await query.message.reply_video(
        video=open("out.mp4", "rb"),
        caption=text[:1000]
    )

    await msg.delete()

# Run bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot running 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
