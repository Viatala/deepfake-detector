import os
import json
import time
import requests
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename
import config

app = Flask(__name__)
app.secret_key = config.ADMIN_SECRET
app.config["MAX_CONTENT_LENGTH"] = config.MAX_FILE_SIZE

# ── Stats ──────────────────────────────────────────────
stats = {
    "total_requests": 0,
    "real_count": 0,
    "fake_count": 0,
    "errors": 0,
    "last_request": None,
    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "enabled": config.SITE_ENABLED,
}

LOGS = []

def add_log(msg):
    LOGS.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "msg": msg,
    })
    if len(LOGS) > 100:
        LOGS.pop(0)

# ── Auth helper ────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ── Routes: public ─────────────────────────────────────
@app.route("/")
def index():
    if not stats["enabled"]:
        return render_template("maintenance.html"), 503
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if not stats["enabled"]:
        return jsonify({"error": "Сайт на обслуживании"}), 503

    if "file" not in request.files:
        return jsonify({"error": "Файл не загружен"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Файл не выбран"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in config.ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Формат .{ext} не поддерживается"}), 400

    # Save temp
    filename = secure_filename(f"{int(time.time())}_{file.filename}")
    filepath = os.path.join(app.root_path, "uploads", filename)
    file.save(filepath)

    stats["total_requests"] += 1
    stats["last_request"] = datetime.now().strftime("%H:%M:%S")
    add_log(f"Запрос от {request.remote_addr}: {file.filename}")

    # Call Hugging Face API
    try:
        with open(filepath, "rb") as f:
            image_bytes = f.read()

        headers = {}
        if config.HF_API_TOKEN:
            headers["Authorization"] = f"Bearer {config.HF_API_TOKEN}"

        response = requests.post(
            config.HF_MODEL_URL,
            headers=headers,
            data=image_bytes,
            timeout=60,
        )

        if response.status_code == 503:
            # Model is loading, wait and retry
            time.sleep(10)
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            response = requests.post(
                config.HF_MODEL_URL,
                headers=headers,
                data=image_bytes,
                timeout=60,
            )

        if response.status_code != 200:
            stats["errors"] += 1
            add_log(f"Ошибка API: {response.status_code}")
            return jsonify({"error": f"Ошибка ИИ-модели ({response.status_code})"}), 500

        result = response.json()

        # Parse result
        if isinstance(result, list) and len(result) > 0:
            predictions = result[0] if isinstance(result[0], list) else result
            best = max(predictions, key=lambda x: x.get("score", 0))
            label = best.get("label", "unknown").upper()
            score = round(best.get("score", 0) * 100, 1)

            if "REAL" in label or "REAL" in label.upper():
                stats["real_count"] += 1
                verdict = "НАСТОЯЩЕЕ"
                color = "#4CAF50"
                icon = "✅"
            else:
                stats["fake_count"] += 1
                verdict = "СГЕНЕРИРОВАНО ИИ"
                color = "#f44336"
                icon = "🚨"

            add_log(f"Результат: {verdict} ({score}%)")
            os.remove(filepath)

            return jsonify({
                "verdict": verdict,
                "confidence": score,
                "color": color,
                "icon": icon,
                "label": label,
            })
        else:
            stats["errors"] += 1
            add_log("Неожиданный формат ответа от API")
            return jsonify({"error": "Не удалось проанализировать"}), 500

    except requests.exceptions.Timeout:
        stats["errors"] += 1
        add_log("Таймаут запроса к API")
        return jsonify({"error": "ИИ-модель не отвечает, попробуйте позже"}), 504
    except Exception as e:
        stats["errors"] += 1
        add_log(f"Ошибка: {str(e)}")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


# ── Routes: admin ──────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session["admin"] = True
            add_log("Админ вошёл в панель")
            return redirect(url_for("admin_panel"))
        flash("Неверный логин или пароль", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def admin_panel():
    return render_template("admin.html", stats=stats, logs=list(reversed(LOGS)))

@app.route("/admin/toggle", methods=["POST"])
@admin_required
def admin_toggle():
    stats["enabled"] = not stats["enabled"]
    status = "включён" if stats["enabled"] else "выключен"
    add_log(f"Сайт {status}")
    return redirect(url_for("admin_panel"))

@app.route("/admin/reset-stats", methods=["POST"])
@admin_required
def admin_reset_stats():
    stats["total_requests"] = 0
    stats["real_count"] = 0
    stats["fake_count"] = 0
    stats["errors"] = 0
    add_log("Статистика сброшена")
    return redirect(url_for("admin_panel"))

@app.route("/admin/clear-logs", methods=["POST"])
@admin_required
def admin_clear_logs():
    LOGS.clear()
    add_log("Логи очищены")
    return redirect(url_for("admin_panel"))

# ── Maintenance page ───────────────────────────────────
@app.route("/status")
def status():
    return jsonify({
        "enabled": stats["enabled"],
        "total_requests": stats["total_requests"],
        "uptime": stats["start_time"],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
