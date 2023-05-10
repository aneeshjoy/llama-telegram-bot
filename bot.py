import os

from telegram.constants import ChatAction
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, Application
from llama_cpp import Llama


BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN is None:
    print("Error: BOT_TOKEN environment variable is not set")
    exit(1)

MODEL_PATH = os.getenv("MODEL_PATH")
if not MODEL_PATH or not os.path.isfile(MODEL_PATH):
    print("Error: MODEL_PATH environment variable is not set or the file does not exist.")
    exit(1)

ALLOWED_USERS = os.getenv("ALLOWED_USERS", "")

llama = Llama(model_path=MODEL_PATH)

memory = {}
context_len = 256

PROMPT_TEMPLATE = """You are a 6 year old girl named Alex. You answer questions in a kind manner.
{chat_history}
Q: {chat_in}.
A: """


# Saves last N characters of chat history in memory
def save_chat(user_id, chat_in, chat_out) -> None:
    chat_history = ""
    try:
        chat_history = memory[user_id]
    except KeyError:
        pass

    chat_history = f"{chat_history} {chat_in} {chat_out}"
    if len(chat_history) > context_len:
        chat_history = chat_history[-context_len:]

    memory[user_id] = chat_history

    # print(f"history:  {chat_history}")


# Returns users chat history from memory
def get_chat_history(user_id):
    try:
        return memory[user_id]
    except KeyError:
        pass
    return ""

# Clears users chat history in memory
def clear_chat_history(user_id):
    try:
        memory[user_id] = ""
    except KeyError:
        pass


# Returns greeting message on telegram /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"/start called by user={update.message.chat_id}")
    clear_chat_history(update.message.chat_id)
    await update.message.reply_text(f'Hello {update.effective_user.first_name}. I am Alex. Ask me anything')


# Clears chat history and returns greeting message on telegram /new_chat command
async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"/new_chat called by user={update.message.chat_id}")
    clear_chat_history(update.message.chat_id)
    await update.message.reply_text(f'Hello {update.effective_user.first_name}. I am Alex. Ask me anything')


# Invokes llama api and returns generated chat response
async def generate_chat_response(prompt, temp_msg, context):
    chat_out = ""
    try:
        tokens = llama.create_completion(prompt, max_tokens=100, top_p=1, stop=["\n"], stream=True)
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
                except:
                    # telegram complaints on duplicate edits. pass it.
                    pass

        if len(resp) == 0:
            print("Empty generation")
            await context.bot.editMessageText(text='Sorry, I am went blank. Try something else',
                                                  chat_id=temp_msg.chat_id, message_id=temp_msg.message_id)
    except:
        print("Unexpected error")
        await context.bot.editMessageText(text='Sorry, something went wrong :(',
                                          chat_id=temp_msg.chat_id, message_id=temp_msg.message_id)
        pass

    return chat_out


# Handles telegram user chat message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # print(f"message received: {update.message}")
    # get chat history for user
    chat_history = get_chat_history(update.message.chat_id)
    chat_in = update.message.text
    chat_id = update.message.chat_id
    print(f"user={chat_id}, chat: {chat_in}")

    # send a typing indicator
    temp = await update.message.reply_text("...")
    # send typing action
    await update.message.chat.send_action(action=ChatAction.TYPING)

    prompt = PROMPT_TEMPLATE.format(chat_in=chat_in, chat_history=chat_history)
    print(f"user={chat_id}, prompt: {prompt}")

    # generate response
    chat_out = await generate_chat_response(prompt, temp, context)
    save_chat(chat_id, chat_in, chat_out)
    print(f"user={chat_id}, response: {chat_out}")


# Register telegram bot commands
async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("/new_chat", "Start new chat"),
    ])
    print("Bot commands added")

if __name__ == '__main__':
    # Build the telegram bot
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(4)
        .post_init(post_init)
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

    print("Bot started")
    if allowed_users:
        print(f"Allowed users: {allowed_users}")
    else:
        print(f"Whole world can talk to your bot. Consider adding your ID to ALLOWED_USERS to make it private")

    app.run_polling()
