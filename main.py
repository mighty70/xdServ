from flask import Flask, request, jsonify
import threading
import time
import requests

app = Flask(__name__)

# Состояние ПК и время
pc_states = {"pc1": False, "pc2": False}
pc_timestamps = {"pc1": None, "pc2": None}

global_lock = threading.Lock()

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = "7319554213:AAHezVAl7fX5_FProDns16Af3GAgW0Yw7lA"
TELEGRAM_CHAT_ID = 5682336970


def send_telegram_message(message):
    """Функция для отправки сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка отправки сообщения в Telegram: {e}")


def check_timeout():
    """Функция для проверки таймаута (3 минуты) между ПК"""
    while True:
        with global_lock:
            current_time = time.time()
            if pc_timestamps["pc1"] and not pc_states["pc2"]:
                if current_time - pc_timestamps[
                        "pc1"] > 90:  # 3 минуты = 180 секунд
                    send_telegram_message(
                        "ПК1 нашёл кнопку, но ПК2 не готов в течение 3 минут.")
            if pc_timestamps["pc2"] and not pc_states["pc1"]:
                if current_time - pc_timestamps["pc2"] > 90:
                    send_telegram_message(
                        "ПК2 нашёл кнопку, но ПК1 не готов в течение 3 минут.")
        time.sleep(30)  # Проверяем каждую минуту


@app.route("/", methods=["GET"])
def index():
    return "Server is running!"


@app.route("/ready", methods=["POST"])
def ready():
    global pc_states, pc_timestamps
    data = request.json

    with global_lock:
        # Обновляем состояние и время получения сигнала
        if data["pc"] == "pc1":
            pc_states["pc1"] = True
            pc_timestamps["pc1"] = time.time()
        elif data["pc"] == "pc2":
            pc_states["pc2"] = True
            pc_timestamps["pc2"] = time.time()

        # Проверяем, оба ли ПК готовы
        if pc_states["pc1"] and pc_states["pc2"]:
            return jsonify({"status": "both_ready"})
        else:
            return jsonify({"status": "waiting"})


@app.route("/accept_game", methods=["POST"])
def accept_game():
    global pc_states
    data = request.json

    with global_lock:
        # Проверяем, какой ПК готов принять игру
        if data["pc"] == "pc1":
            print(f"ПК1 готов: {pc_states['pc1']}")
            pc_states["pc1"] = True
        elif data["pc"] == "pc2":
            print(f"ПК2 готов: {pc_states['pc2']}")
            pc_states["pc2"] = True

        # Проверяем, оба ли ПК готовы для начала игры
        if pc_states["pc1"] and pc_states["pc2"]:
            return jsonify({"status": "both_accepted"})
        else:
            return jsonify({"status": "waiting"})


@app.route("/reset", methods=["POST"])
def reset():
    global pc_states, pc_timestamps
    with global_lock:
        # Сброс состояния для новой игры
        pc_states["pc1"] = False
        pc_states["pc2"] = False
        pc_timestamps["pc1"] = None
        pc_timestamps["pc2"] = None
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    # Запускаем отдельный поток для проверки таймаута
    threading.Thread(target=check_timeout, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
