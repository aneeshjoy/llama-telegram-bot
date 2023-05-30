# Llama.cpp Telegram Bot
A simple Telegram chat bot for LLMs supported by [llama.cpp](https://github.com/ggerganov/llama.cpp)

Easiest way to share your selfhosted ChatGPT style interface with friends and family! 
Even group chat with your AI friend!

## Demo




https://github.com/aneeshjoy/llama-telegram-bot/assets/5285961/8a62e601-f298-48c2-9ed9-d2b3d041d2f7



## Features
1. Easy to setup and run
2. Group chat
3. Whitelist to restrict to a limited set of users
4. Unlimited chats - Sliding window
5. Typing indicator
6. Streaming responses
7. New chat command
8. Supports LLMs supported by [llama.cpp](https://github.com/ggerganov/llama.cpp)
9. GPU Acceleration support
10. Voice chat

## Installation
### What do you need?
1. A free Telegram bot token from [@BotFather](https://t.me/BotFather)
2. A [Llama.cpp](https://github.com/ggerganov/llama.cpp) supported model in your local system 

## Manual Installation
````
$ git clone https://github.com/aneeshjoy/llama-telegram-bot.git
$ cd llama-telegram-bot
$ sudo pip3 install -r requirements.txt
$ export BOT_TOKEN=<Your Telegram bot token>
$ export MODEL_PATH=/path/to/your/model/file
$ python3 bot.py
````

## GPU Acceleration
For GPU acceleration specify additional environment variables:
```
LLAMA_CUBLAS=1 CMAKE_ARGS="-DLLAMA_CUBLAS=ON" FORCE_CMAKE=1 pip3 install -r requirements.txt
```

## Using Prebuilt Docker image 

You can use pre-built docker image to run the bot. Follow these steps:

1. Clone the repo or download `docker-compose.yml`
```
$ git clone https://github.com/aneeshjoy/llama-telegram-bot.git
$ cd llama-telegram-bot
```
2. Update BOT_TOKEN env variable in  `docker-compose.yml` file
3. Update MODEL_PATH env variable in `docker-compose.yml` file
4. Update `- /path/to/models` in `docker-compose.yml` to point to the folder which contains the model
5. Run the bot

```
$ docker-compose up
```

## Using Self built Docker image 
You can build your own docker image to run the bot. Follow these steps:

1. Clone the repo
```
$ git clone https://github.com/aneeshjoy/llama-telegram-bot.git
$ cd llama-telegram-bot
```
2. Update BOT_TOKEN env variable in  `docker-compose-build.yml` file
3. Update MODEL_PATH env variable in `docker-compose-build.yml` file
4. Update `- /path/to/models` in `docker-compose-build.yml` to point to the folder which contains the model
5. Run the bot

```
$ docker-compose -f docker-compose-build.yml up --build 
```

## Usage

Once the bot is running, you can use the following commands to generate text:

- `/start` - Get a welcome message from the bot.
- `/new_chat` - To start a new conversation.


## Contributing

To contribute, please:

1. Fork the repository.
2. Create a new branch for your changes.
3. Make your changes and commit them.
4. Push your changes to your fork.
5. Submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more information.

## Credits

* [llama.cpp](https://github.com/ggerganov/llama.cpp)
* [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
* [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
