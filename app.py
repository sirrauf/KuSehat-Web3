import os
import uuid
import numpy as np
import requests
from datetime import datetime, date
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pony.orm import Database, Required, Optional, PrimaryKey, Set, db_session, select
from luno_python.client import Client

# =========================
# Setup
# =========================
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_me")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ENABLE_AI = os.getenv("ENABLE_AI", "0") == "1"  # AI nonaktif default

# =========================
# Luno API
# =========================
LUNO_API_KEY_ID = os.getenv("LUNO_API_KEY_ID", "")
LUNO_API_KEY_SECRET = os.getenv("LUNO_API_KEY_SECRET", "")
luno_client = Client(api_key_id=LUNO_API_KEY_ID, api_key_secret=LUNO_API_KEY_SECRET)

# =========================
# Database
# =========================
db = Database()
db.bind(
    provider='mysql',
    host="localhost",      
    user="root",           
    passwd="",  
    db="kusehat"           
)

class User(db.Entity):
    _table_ = "user"
    UserID = PrimaryKey(int, auto=True)
    NamaUser = Required(str)
    Email = Required(str, unique=True)
    Password = Required(str)
    Register_Date = Required(datetime)
    Login_Date = Optional(datetime)
    Saldo = Required(float, default=0.0)
    topups = Set("TopUp")
    exchanges = Set("Exchange")

class TopUp(db.Entity):
    _table_ = "topup"
    ID = PrimaryKey(int, auto=True)
    User = Required(User)
    Jumlah = Required(float)
    Metode = Required(str)
    Tanggal = Required(datetime)

class Exchange(db.Entity):
    _table_ = "exchange"
    ID = PrimaryKey(int, auto=True)
    User = Required(User)
    Tujuan = Required(str)
    Gambar = Required(str)
    Diagnosa = Required(str)
    Tanggal = Required(datetime)
    SaldoReward = Required(float)

db.generate_mapping(create_tables=False)

# =========================
# AI (lazy load)
# =========================
model = None
class_names = []

def load_ai_if_enabled():
    global model, class_names
    if not ENABLE_AI or model is not None:
        return
    try:
        from keras.models import load_model as _load_model
        model_path = "model/keras_Model.h5"
        labels_path = "model/labels.txt"
        if not (os.path.isfile(model_path) and os.path.isfile(labels_path)):
            return
        _model = _load_model(model_path, compile=False)
        with open(labels_path, "r") as f:
            _class_names = [line.strip() for line in f]
        model, class_names = _model, _class_names
    except Exception:
        pass

def process_image_for_detection(image_path):
    if not ENABLE_AI:
        return {"error": "AI detection disabled on this server."}
    load_ai_if_enabled()
    if model is None:
        return {"error": "Model not available."}
    try:
        from PIL import Image
        image = Image.open(image_path).convert("RGB").resize((224, 224))
        image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)
        image = (image / 127.5) - 1
        prediction = model.predict(image)
        index = int(np.argmax(prediction))
        class_name = class_names[index].strip()
        confidence = float(prediction[0][index])
        return {"diagnosis": f"Deteksi: {class_name} ({confidence:.2%})", "class_name": class_name}
    except Exception as e:
        return {"error": str(e)}

# =========================
# Routes
# =========================
@app.route("/")
@db_session
def home():
    diagnosis = ""
    image_path = ""
    user = None
    if "user_id" in session:
        user = User.get(UserID=session["user_id"])

    if request.method == "POST" and "image" in request.files:
        file = request.files["image"]
        if file and file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)
            result = process_image_for_detection(image_path)
            diagnosis = result.get("diagnosis", result.get("error", ""))
    return render_template("index.html", diagnosis=diagnosis, image_path=image_path, user=user)

@app.route("/register", methods=["POST"])
@db_session
def register():
    nama, email, password = request.form.get("nama"), request.form.get("email"), request.form.get("password")
    if User.get(Email=email):
        return "❌ Email sudah terdaftar."
    User(NamaUser=nama, Email=email, Password=password, Register_Date=datetime.now())
    return "✅ Registrasi berhasil"

@app.route("/login", methods=["POST"])
@db_session
def login():
    email, password = request.form.get("email"), request.form.get("password")
    user = User.get(Email=email, Password=password)
    if user:
        session["user_id"] = user.UserID
        return redirect(url_for("home"))
    return "❌ Email/Password salah"

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# =========================
# Run (local only)
# =========================
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
