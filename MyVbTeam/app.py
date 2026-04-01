from flask import Flask, render_template, request, redirect, session, send_from_directory
from werkzeug.utils import secure_filename
import os
import json

app = Flask(__name__)
app.secret_key = "volleyballcaptain"
ADMIN_PASSWORD = "volleyballcaptain"

DATA_FILE = "data.json"
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Global data
players = []
training_sessions = []
training_cost_per_session = 0.0

# -----------------------
# Save and load data
# -----------------------

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "players": players,
            "training_sessions": training_sessions,
            "training_cost_per_session": training_cost_per_session
        }, f)

def load_data():
    global players, training_sessions, training_cost_per_session
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        players = data.get("players", [])
        training_sessions = data.get("training_sessions", [])
        training_cost_per_session = data.get("training_cost_per_session", 0.0)

        # Make sure every player has all the fields we need
        for player in players:
            if "games_amount" not in player:
                player["games_amount"] = 0.0
            if "games_paid" not in player:
                player["games_paid"] = 0.0
            if "training_amount" not in player:
                player["training_amount"] = 0.0
            if "training_paid" not in player:
                player["training_paid"] = 0.0
            if "training_sessions_paid" not in player:
                player["training_sessions_paid"] = []
            if "photo" not in player:
                player["photo"] = None
    except:
        players = []
        training_sessions = []
        training_cost_per_session = 0.0

load_data()

# -----------------------
# Login / logout
# -----------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
        return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# -----------------------
# uploaded photos
# -----------------------

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/upload_photo/<int:index>", methods=["POST"])
def upload_photo(index):
    if not session.get("admin"):
        return redirect("/")
    file = request.files["photo"]
    if file and "." in file.filename and file.filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS:
        filename = secure_filename(f"player_{index}_{file.filename}")
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        players[index]["photo"] = filename
        save_data()
    return redirect("/")

# -----------------------
# Main dashboard
# -----------------------

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if not session.get("admin"):
            return redirect("/")
        name = request.form["name"]
        players.append({
            "name": name,
            "games_amount": 0.0,
            "games_paid": 0.0,
            "training_amount": 0.0,
            "training_paid": 0.0,
            "training_sessions_paid": [],
            "photo": None
        })
        save_data()
        return redirect("/")
    is_admin = session.get("admin", False)
    return render_template("index.html", players=players, is_admin=is_admin)

# -----------------------
# Setting Team-wide payments
# -----------------------

@app.route("/set_team_games_amount", methods=["POST"])
def set_team_games_amount():
    if not session.get("admin"):
        return redirect("/")
    total = float(request.form["total"])
    per_player = round(total / len(players), 2)
    for player in players:
        player["games_amount"] = per_player
    save_data()
    return redirect("/")

@app.route("/set_team_training_amount", methods=["POST"])
def set_team_training_amount():
    if not session.get("admin"):
        return redirect("/")
    total = float(request.form["total"])
    per_player = round(total / len(players), 2)
    for player in players:
        player["training_amount"] = per_player
    save_data()
    return redirect("/")

# -----------------------
# Per-player payments
# -----------------------

@app.route("/add_games_payment/<int:index>", methods=["POST"])
def add_games_payment(index):
    if not session.get("admin"):
        return redirect("/")
    players[index]["games_paid"] += float(request.form["payment"])
    save_data()
    return redirect("/")

@app.route("/add_training_payment/<int:index>", methods=["POST"])
def add_training_payment(index):
    if not session.get("admin"):
        return redirect("/")
    players[index]["training_paid"] += float(request.form["payment"])
    save_data()
    return redirect("/")

# -----------------------
# Training sessions
# -----------------------

@app.route("/set_training_cost", methods=["POST"])
def set_training_cost():
    global training_cost_per_session
    if not session.get("admin"):
        return redirect("/training")
    training_cost_per_session = float(request.form["cost"])
    save_data()
    return redirect("/training")

@app.route("/add_training_session", methods=["POST"])
def add_training_session():
    if not session.get("admin"):
        return redirect("/training")
    date = request.form["date"]
    if date not in training_sessions:
        training_sessions.append(date)
        training_sessions.sort()
    save_data()
    return redirect("/training")

@app.route("/delete_training_session", methods=["POST"])
def delete_training_session():
    if not session.get("admin"):
        return redirect("/training")
    date = request.form["date"]
    if date in training_sessions:
        training_sessions.remove(date)
    for player in players:
        if date in player["training_sessions_paid"]:
            player["training_sessions_paid"].remove(date)
        player["training_paid"] = len(player["training_sessions_paid"]) * training_cost_per_session
    save_data()
    return redirect("/training")

@app.route("/toggle_training_payment", methods=["POST"])
def toggle_training_payment():
    if not session.get("admin"):
        return redirect("/training")
    index = int(request.form["index"])
    date = request.form["date"]
    paid_sessions = players[index]["training_sessions_paid"]

    if date in paid_sessions:
        paid_sessions.remove(date)
        is_paid = False
    else:
        paid_sessions.append(date)
        is_paid = True

    players[index]["training_paid"] = len(paid_sessions) * training_cost_per_session
    save_data()

    # If called from JavaScript, return JSON so the page doesn't reload
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"is_paid": is_paid, "training_paid": players[index]["training_paid"]}
    return redirect("/training")

@app.route("/training")
def training():
    is_admin = session.get("admin", False)
    return render_template("training.html",
                           players=players,
                           training_sessions=training_sessions,
                           is_admin=is_admin,
                           cost_per_session=training_cost_per_session)

if __name__ == "__main__":
    app.run(debug=True)