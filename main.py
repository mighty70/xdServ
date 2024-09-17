from flask import Flask, request, jsonify
import threading
import time
import requests

app = Flask(__name__)

pc_states = {"pc1": False, "pc2": False}
pc_timestamps = {"pc1": None, "pc2": None}
cancel_timers = {"pc1": None, "pc2": None}

global_lock = threading.Lock()

TELEGRAM_BOT_TOKEN = "7319554213:AAHezVAl7fX5_FProDns16Af3GAgW0Yw7lA"
TELEGRAM_CHAT_ID = 5682336970

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка отправки сообщения в Telegram: {e}")

def check_timeout():
    while True:
        with global_lock:
            current_time = time.time()
            if pc_timestamps["pc1"] and not pc_states["pc2"]:
                if current_time - pc_timestamps["pc1"] > 90:
                    send_telegram_message("ПК1 нашёл кнопку, но ПК2 не готов в течение 3 минут.")
            if pc_timestamps["pc2"] and not pc_states["pc1"]:
                if current_time - pc_timestamps["pc2"] > 90:
                    send_telegram_message("ПК2 нашёл кнопку, но ПК1 не готов в течение 3 минут.")
        time.sleep(30) 

def reset_pc_state(pc):
    with global_lock:
        pc_states[pc] = False
        pc_timestamps[pc] = None
        send_telegram_message(f"Запрос от {pc} сброшен через 10 секунд ожидания второго ПК.")

@app.route("/", methods=["GET"])
def index():
    return "Server is running!"

@app.route("/ready", methods=["POST"])
def ready():
    global pc_states, pc_timestamps, cancel_timers
    data = request.json

    with global_lock:
        pc = data["pc"]
        pc_states[pc] = True
        pc_timestamps[pc] = time.time()

        if cancel_timers[pc]:
            cancel_timers[pc].cancel()

        timer = threading.Timer(10.0, reset_pc_state, args=[pc])
        cancel_timers[pc] = timer
        timer.start()

        if pc_states["pc1"] and pc_states["pc2"]:
            if cancel_timers["pc1"]:
                cancel_timers["pc1"].cancel()
            if cancel_timers["pc2"]:
                cancel_timers["pc2"].cancel()
            return jsonify({"status": "both_ready"})
        else:
            return jsonify({"status": "waiting"})

@app.route("/accept_game", methods=["POST"])
def accept_game():
    global pc_states, pc_timestamps, cancel_timers
    data = request.json

    with global_lock:
        pc = data["pc"]
        pc_states[pc] = True
        pc_timestamps[pc] = time.time()

        if cancel_timers[pc]:
            cancel_timers[pc].cancel()

        timer = threading.Timer(10.0, reset_pc_state, args=[pc])
        cancel_timers[pc] = timer
        timer.start()

        if pc_states["pc1"] and pc_states["pc2"]:
            if cancel_timers["pc1"]:
                cancel_timers["pc1"].cancel()
            if cancel_timers["pc2"]:
                cancel_timers["pc2"].cancel()
            return jsonify({"status": "game_accepted", "message": "Оба ПК приняли игру."})
        else:
            return jsonify({"status": "waiting_for_accept", "message": "Ожидание принятия игры вторым ПК."})

@app.route("/reset", methods=["POST"])
def reset():
    global pc_states, pc_timestamps, cancel_timers
    with global_lock:
        pc_states["pc1"] = False
        pc_states["pc2"] = False
        pc_timestamps["pc1"] = None
        pc_timestamps["pc2"] = None

        if cancel_timers["pc1"]:
            cancel_timers["pc1"].cancel()
        if cancel_timers["pc2"]:
            cancel_timers["pc2"].cancel()

    return jsonify({"status": "reset"})

if __name__ == "__main__":
    threading.Thread(target=check_timeout, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
