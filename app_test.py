import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>DeepFake Detector</h1><p>Сайт работает! Идёт настройка...</p>"

@app.route("/status")
def status():
    return {"status": "ok", "message": "Сервер работает!"}

@app.route("/admin")
def admin():
    return "<h1>Админ-панель</h1><p>В разработке...</p>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
