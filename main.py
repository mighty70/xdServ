

from flask import Flask, request, jsonify
import threading
import time
import requests

app = Flask(__name__)

# Состояние ПК и время
pc_states = {"pc1": False, "pc2": False}
pc_timestamps = {"pc1": None, "pc2": None}

global_lock = threading.Lock()

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

def reset_states():
    """Отдельная функция для сброса состояния"""
    global pc_states, pc_timestamps
    with global_lock:
        pc_states["pc1"] = False
        pc_states["pc2"] = False
        pc_timestamps["pc1"] = None
        pc_timestamps["pc2"] = None
    send_telegram_message("Состояния ПК сброшены.")

def check_and_reset_if_timeout(pc):
    """Проверка на тайм-аут и сброс состояния, если другой ПК не ответил в течение 10 секунд"""
    global pc_states, pc_timestamps
    current_time = time.time()

    if pc == "pc1" and pc_timestamps["pc2"]:
        if current_time - pc_timestamps["pc2"] > 10:
            send_telegram_message("ПК2 не ответил в течение 10 секунд после ПК1. Сброс.")
            reset_states()
    elif pc == "pc2" and pc_timestamps["pc1"]:
        if current_time - pc_timestamps["pc1"] > 10:
            send_telegram_message("ПК1 не ответил в течение 10 секунд после ПК2. Сброс.")
            reset_states()

def check_timeout():
    """Функция для регулярной проверки тайм-аутов"""
    while True:
        with global_lock:
            current_time = time.time()
            # Проверяем, не истекло ли 10 секунд с момента получения запроса от PC1 или PC2
            if pc_timestamps["pc1"] and not pc_states["pc2"]:
                if current_time - pc_timestamps["pc1"] > 10:
                    send_telegram_message("ПК1 готов, но ПК2 не ответил в течение 10 секунд. Сброс.")
                    reset_states()
            if pc_timestamps["pc2"] and not pc_states["pc1"]:
                if current_time - pc_timestamps["pc2"] > 10:
                    send_telegram_message("ПК2 готов, но ПК1 не ответил в течение 10 секунд. Сброс.")
                    reset_states()
        time.sleep(1)  # Проверяем каждую секунду

@app.route("/", methods=["GET"])
def index():
    return "Server is running!"

@app.route("/ready", methods=["POST"])
def ready():
    global pc_states, pc_timestamps
    data = request.json

    with global_lock:
        # Проверяем наличие тайм-аута для другого ПК перед обновлением состояния
        check_and_reset_if_timeout(data["pc"])

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
        # Проверяем наличие тайм-аута для другого ПК перед обновлением состояния
        check_and_reset_if_timeout(data["pc"])

        # Обновляем состояние ПК для принятия игры
        if data["pc"] == "pc1":
            pc_states["pc1"] = True
        elif data["pc"] == "pc2":
            pc_states["pc2"] = True

        # Проверяем, оба ли ПК готовы принять игру
        if pc_states["pc1"] and pc_states["pc2"]:
            return jsonify({"status": "game_accepted", "message": "Оба ПК приняли игру."})
        else:
            return jsonify({"status": "waiting_for_accept", "message": "Ожидание принятия игры вторым ПК."})

@app.route("/reset", methods=["POST"])
def reset():
    reset_states()
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    # Запуск отдельного потока для проверки тайм-аутов
    threading.Thread(target=check_timeout, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)

