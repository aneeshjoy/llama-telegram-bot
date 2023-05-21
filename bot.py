import os
from enum import Enum
import tempfile
from pathlib import Path

from telegram.constants import ChatAction, ParseMode
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, Application, \
    CallbackQueryHandler, CallbackContext
from llama_cpp import Llama
import pyttsx3
from pydub import AudioSegment

BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN is None:
    print("Error: BOT_TOKEN environment variable is not set")
    exit(1)

MODEL_PATH = os.getenv("MODEL_PATH")
if not MODEL_PATH or not os.path.isfile(MODEL_PATH):
    print("Error: MODEL_PATH environment variable is not set or the file does not exist.")
    exit(1)

ALLOWED_USERS = os.getenv("ALLOWED_USERS", "")
GPU_LAYERS = os.getenv("GPU_LAYERS", 0)

llama = Llama(model_path=MODEL_PATH, n_gpu_layers=int(GPU_LAYERS))

user_db = {}
context_len = 250

PROMPT_TEMPLATE = """You are a 6 year old girl named Alex. You answer questions in a kind manner.
{chat_history}
Q: {chat_in}.
A: """

engine = pyttsx3.init()
engine.setProperty('rate', 120)


class ChatMode(Enum):
    TEXT = 1
    VOICE = 2


# Saves last N characters of chat history in memory
def save_chat(user_id, chat_in, chat_out) -> None:
    chat_history = ""
    if user_id not in user_db:
        user_db[user_id] = {}

    try:
        chat_history = user_db[user_id]["history"]
    except KeyError:
        pass

    chat_history = f"{chat_history} {chat_in} {chat_out}"
    if len(chat_history) > context_len:
        chat_history = chat_history[-context_len:]

    user_db[user_id]["history"] = chat_history

    # print(f"history:  {chat_history}")


# Returns users chat history from memory
def get_chat_history(user_id):
    try:
        return user_db[user_id]["history"]
    except KeyError as e:
        print(e)
        pass

    return ""


# Clears users chat history in memory
def clear_chat_history(user_id):
    try:
        user_db[user_id]["history"] = ""
    except KeyError as e:
        print(e)
        pass


# Sets users chat mode
def set_chat_mode(user_id, mode):
    if user_id not in user_db:
        user_db[user_id] = {}

    try:
        user_db[user_id]["chat_mode"] = mode
    except KeyError as e:
        print(e)
        pass


# Returns users current chatmode. defaults to ChatMode.TEXT
def get_chat_mode(user_id):
    try:
        return user_db[user_id]["chat_mode"]
    except KeyError as e:
        print(e)
        pass

    return ChatMode.TEXT


# Returns greeting message on telegram /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"/start called by user={update.message.chat_id}")
    clear_chat_history(update.message.chat_id)
    await update.message.reply_text(f'Hello {update.effective_user.first_name}. I am Alex. Ask me anything. Choose: ',
                                    reply_markup=main_menu_keyboard())


# Clears chat history and returns greeting message on telegram /new_chat command
async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"/new_chat called by user={update.message.chat_id}")
    clear_chat_history(update.message.chat_id)
    await update.message.reply_text(f'Hello {update.effective_user.first_name}. I am Alex. Ask me anything. Choose:',
                                    reply_markup=main_menu_keyboard())


async def start_voice_chat(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    set_chat_mode(query.message.chat_id, ChatMode.VOICE)
    await query.answer()
    await query.message.reply_text('Voice chat enabled')


async def start_text_chat(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    set_chat_mode(query.message.chat_id, ChatMode.TEXT)
    await query.answer()
    await query.message.reply_text('Text chat enabled')


# Invokes llama api and returns generated chat response
async def generate_chat_response(prompt, temp_msg, context):
    chat_out = ""
    try:
        tokens = llama.create_completion(prompt, max_tokens=240, top_p=1, stop=["\n"], stream=True)
        resp = []
        for token in tokens:
            tok = token["choices"][0]["text"]
            if not token["choices"][0]["finish_reason"]:
                resp.append(tok)
                chat_out = ''.join(resp)
                try:
                    # Edit response message on each token to simulate streaming.
                    await context.bot.editMessageText(text=chat_out, chat_id=temp_msg.chat_id,
                                                      message_id=temp_msg.message_id)
                except Exception as e:
                    print(e)
                    # telegram complaints on duplicate edits. pass it.
                    pass

        if not resp:
            print("Empty generation")
            await context.bot.editMessageText(text='Sorry, I am went blank. Try something else',
                                              chat_id=temp_msg.chat_id, message_id=temp_msg.message_id)
    except Exception as e:
        print(f"Unexpected error: {e}")
        await context.bot.editMessageText(text='Sorry, something went wrong :(',
                                          chat_id=temp_msg.chat_id, message_id=temp_msg.message_id)
        pass
    return chat_out


# Invokes llama api and returns generated chat response
async def generate_audio_response(prompt, context, update):
    chat_out = ""
    try:
        output = llama.create_completion(prompt, max_tokens=240, top_p=1, stop=["</s>"])
        chat_out = output["choices"][0]["text"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            audio_file_name = tmp_dir / f"{update.message.chat_id}.mp3"
            audio_mp3 = str(audio_file_name)

            engine.save_to_file(chat_out, audio_mp3)
            engine.runAndWait()

            AudioSegment.from_file(audio_mp3).export(audio_mp3, format="mp3")
            voice = AudioSegment.from_mp3(audio_mp3)

            await update.message.reply_voice(audio_mp3, duration=voice.duration_seconds)

        if not chat_out:
            print("Empty generation")
            await update.message.reply_text("No comments")
    except Exception as e:
        print(f"Unexpected error: {e}")
        await update.message.reply_text("Sorry, something went wrong :(")
        pass

    return chat_out


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        voice_ogg_path = tmp_dir / "voice.ogg"

        # download
        voice_file = await context.bot.get_file(voice.file_id)
        await voice_file.download_to_drive(voice_ogg_path)

        # convert to mp3
        voice_mp3_path = tmp_dir / "voice.mp3"
        AudioSegment.from_file(voice_ogg_path).export(voice_mp3_path, format="mp3")
        audio = AudioSegment.from_mp3(voice_mp3_path)
        transcribed_text = f"I got your message of {audio.duration_seconds} secs. This feature is coming soon!"
        # TODO: Transcribe and generate response.

    await update.message.reply_text(transcribed_text, parse_mode=ParseMode.HTML)

# Handles telegram user chat message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # print(f"message received: {update.message}")
    # get chat history for user
    chat_history = get_chat_history(update.message.chat_id)
    chat_mode = get_chat_mode(update.message.chat_id)

    chat_in = update.message.text
    chat_id = update.message.chat_id
    print(f"user={chat_id}, chat: {chat_in}")

    # send typing action
    await update.message.chat.send_action(action=ChatAction.TYPING)

    prompt = PROMPT_TEMPLATE.format(chat_in=chat_in, chat_history=chat_history)
    print(f"user={chat_id}, prompt: {prompt}")

    # generate response
    if chat_mode == ChatMode.TEXT:
        temp = await update.message.reply_text("...")
        chat_out = await generate_chat_response(prompt, temp_msg=temp, context=context)
    else:
        chat_out = await generate_audio_response(prompt, context, update)

    save_chat(chat_id, chat_in, chat_out)
    print(f"user={chat_id}, response: {chat_out}")


# Register telegram bot commands
async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("/new_chat", "Start new chat"),
    ])
    print("Bot commands added")


def main_menu_keyboard():
    keyboard = [[InlineKeyboardButton('Text Chat', callback_data='text')],
                [InlineKeyboardButton('Voice Chat', callback_data='voice')]]
    return InlineKeyboardMarkup(keyboard)


if __name__ == '__main__':

    # Build the telegram bot
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(4)
        .post_init(post_init)
        .read_timeout(60)
        .write_timeout(60)
        .build()
    )

    # Convert ALLOWED_USERS string to a list.
    allowed_users = [int(user.strip()) if user.strip().isdigit() else user.strip() for user in ALLOWED_USERS.split(",")
                     if ALLOWED_USERS.strip()]

    # make user filters
    user_filter = filters.ALL
    if len(allowed_users) > 0:
        usernames = [x for x in allowed_users if isinstance(x, str)]
        user_ids = [x for x in allowed_users if isinstance(x, int)]
        user_filter = filters.User(username=usernames) | filters.User(user_id=user_ids)

    # add handlers
    app.add_handler(CommandHandler("start", start, filters=user_filter))
    app.add_handler(CommandHandler("new_chat", new_chat, filters=user_filter))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & user_filter, handle_message))
    app.add_handler(MessageHandler(filters.VOICE & user_filter, handle_voice))
    app.add_handler(CallbackQueryHandler(start_voice_chat, pattern='voice'))
    app.add_handler(CallbackQueryHandler(start_text_chat, pattern='text'))

    print("Bot started")
    if allowed_users:
        print(f"Allowed users: {allowed_users}")
    else:
        print(f"Whole world can talk to your bot. Consider adding your ID to ALLOWED_USERS to make it private")

    app.run_polling()
