import os
import uuid
import cv2
import numpy as np
import requests
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.utils import secure_filename
from keras.models import load_model
from pony.orm import Database, Required, Optional, PrimaryKey, Set, db_session
from luno_python.client import Client

# 🔐 Konfigurasi API Luno
LUNO_API_KEY_ID = "ngj6vvfjtxykp"
LUNO_API_KEY_SECRET = "ANqZRoFWc-te-CUFxsOzMBoQruBvjOMP_RZQGoDDFso"
luno_client = Client(api_key_id=LUNO_API_KEY_ID, api_key_secret=LUNO_API_KEY_SECRET)

# ─────────────────────────────────────────────
# 🔹 Database Setup
db = Database()
db.bind(provider='mysql', host='localhost', user='root', passwd='', db='kusehat')

class User(db.Entity):
    _table_ = "user"
    UserID = PrimaryKey(int, auto=True)
    NamaUser = Required(str)
    Email = Required(str, unique=True)
    Password = Required(str)
    Register_Date = Required(datetime)
    Login_Date = Optional(datetime)
    Saldo = Required(float, default=0.0)
    topups = Set("TopUp")  # ✅ Reverse relasi TopUp

class TopUp(db.Entity):
    _table_ = "topup"
    ID = PrimaryKey(int, auto=True)
    User = Required(User)
    Jumlah = Required(float)
    Metode = Required(str)
    Tanggal = Required(datetime)

db.generate_mapping(create_tables=True)

# ─────────────────────────────────────────────
# 🔹 Flask Setup
app = Flask(__name__)
app.secret_key = 'rahasia_kusehat'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─────────────────────────────────────────────
# 🔹 Load AI Model
try:
    model = load_model("model/keras_Model.h5", compile=False)
    with open("model/labels.txt", "r") as f:
        class_names = f.readlines()
except Exception as e:
    print(f"❌ Gagal memuat model atau label: {e}")
    model = None
    class_names = []

# ─────────────────────────────────────────────
# 🔹 Gemini AI Setup
GEMINI_API_KEY = "AIzaSyDwniC_zbYaVpRWRGjGk9HnhJWAe9IPZGM"
MODEL_NAME = "gemini-1.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"

def get_gemini_diagnosis(disease_name):
    prompt = (
        f"Tolong jelaskan informasi tentang penyakit kulit berikut ini dalam format HTML yang rapi:\n\n"
        f"Nama penyakit: {disease_name}\n\n"
        f"1. Deskripsi\n2. Gejala dan Penyebab\n3. Cara Penyembuhan\n4. Rekomendasi Obat"
    )
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"❌ Gemini AI gagal memberikan penjelasan: {e}"

# ─────────────────────────────────────────────
# 🔹 AI Deteksi Penyakit
def predict_keras(image_np):
    if model is None:
        return "Model tidak dimuat", 0.0
    image = cv2.resize(image_np, (224, 224))
    image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)
    image = (image / 127.5) - 1
    prediction = model.predict(image)
    index = np.argmax(prediction)
    class_name = class_names[index].strip()
    confidence = float(prediction[0][index])
    return class_name, confidence

def detect_disease_with_camera():
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return "❌ Kamera tidak tersedia", None
    ret, frame = cam.read()
    cam.release()
    if not ret:
        return "❌ Gagal mengambil gambar", None

    filename = f"{uuid.uuid4().hex}.jpg"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    cv2.imwrite(image_path, frame)

    predicted_label, confidence = predict_keras(frame)
    gemini_info = get_gemini_diagnosis(predicted_label)

    result = (
        f"📸 <b>Deteksi Kamera</b>: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan: {confidence:.2%}<br><br>"
        f"🧠 <b>Penjelasan Gemini AI:</b><br>{gemini_info}"
    )
    return result, image_path

def detect_disease_with_upload(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return "❌ Gagal membaca gambar", None

    predicted_label, confidence = predict_keras(image)
    gemini_info = get_gemini_diagnosis(predicted_label)

    result = (
        f"📤 <b>Deteksi Upload</b>: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan: {confidence:.2%}<br><br>"
        f"🧠 <b>Penjelasan Gemini AI:</b><br>{gemini_info}"
    )
    return result, image_path

# ─────────────────────────────────────────────
# 🔹 ROUTES
@app.route("/", methods=["GET", "POST"])
def home():
    diagnosis = ""
    image_path = ""

    if request.method == "POST":
        method = request.form.get("method", "")
        if method == "upload":
            file = request.files.get("image")
            if not file or file.filename == "":
                diagnosis = "❌ Gambar tidak ditemukan."
            else:
                filename = secure_filename(file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image_path)
                diagnosis, image_path = detect_disease_with_upload(image_path)
        elif method == "camera":
            diagnosis, image_path = detect_disease_with_camera()
        else:
            diagnosis = "❌ Permintaan tidak dikenali."

    user = None
    if "user_id" in session:
        with db_session:
            user = User.get(UserID=session["user_id"])

    return render_template("index.html", diagnosis=diagnosis, image_path=image_path,
                           user=user, topup_address="", topup_error="")

@app.route("/register", methods=["POST"])
@db_session
def register():
    nama = request.form.get("nama")
    email = request.form.get("email")
    password = request.form.get("password")

    if User.get(Email=email):
        return "❌ Email sudah terdaftar."

    User(
        NamaUser=nama,
        Email=email,
        Password=password,
        Register_Date=datetime.now()
    )
    return "✅ Pendaftaran berhasil. Silakan login."

@app.route("/login", methods=["POST"])
@db_session
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    user = User.get(Email=email, Password=password)

    if user:
        session['user_id'] = user.UserID
        return redirect(url_for("dashboard"))
    else:
        return "❌ Email atau Password salah."

@app.route("/dashboard")
@db_session
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("home"))

    user = User.get(UserID=user_id)
    return render_template("index.html", diagnosis="", image_path="", user=user,
                           topup_address="", topup_error="")

@app.route("/update_user", methods=["POST"])
@db_session
def update_user():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("home"))

    user = User.get(UserID=user_id)
    old_password = request.form.get("old_password")

    if user.Password != old_password:
        return "❌ Password lama tidak cocok."

    user.NamaUser = request.form.get("nama")
    user.Email = request.form.get("email")
    user.Password = request.form.get("new_password")
    return redirect(url_for("dashboard"))

@app.route("/topup", methods=["POST"])
@db_session
def topup():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("home"))

    metode = request.form.get("metode")
    jumlah = float(request.form.get("jumlah", 0))
    alamat = ""
    error = ""

    try:
        if metode == "btc":
            res = luno_client.get_funding_address(asset="XBT")
            alamat = res["address"]
        elif metode == "eth":
            res = luno_client.get_funding_address(asset="ETH")
            alamat = res["address"]
        elif metode == "usdt":
            error = "❌ USDT (TRC20) belum didukung oleh Luno API."
        else:
            error = "❌ Metode tidak valid."
    except Exception as e:
        error = f"❌ Gagal mengambil alamat: {str(e)}"

    user = User.get(UserID=user_id)

    if not error:
        TopUp(User=user, Jumlah=jumlah, Metode=metode.upper(), Tanggal=datetime.now())
        user.Saldo += jumlah

    return render_template("index.html", diagnosis="", image_path="", user=user,
                           topup_address=alamat, topup_error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
