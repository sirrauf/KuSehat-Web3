import os
import uuid
import cv2
import numpy as np
import requests
from datetime import datetime, date
from flask import Flask, request, jsonify, session, url_for
from werkzeug.utils import secure_filename
from keras.models import load_model
from pony.orm import Database, Required, Optional, PrimaryKey, Set, db_session, select
from luno_python.client import Client
from flask_cors import CORS

# --- Konfigurasi Aplikasi ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ganti-dengan-secret-key-yang-aman")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
CORS(app)

# --- Konfigurasi Database ---
db = Database()
db.bind(provider='mysql', host='localhost', user='root', passwd='', db='kusehat')

class User(db.Entity):
    _table_ = "user"
    UserID = PrimaryKey(int, auto=True)
    NamaUser = Required(str, 255)
    Email = Required(str, 255, unique=True)
    Password = Required(str, 255)
    Register_Date = Required(datetime, default=datetime.now)
    Login_Date = Optional(datetime)
    Saldo = Required(float, default=0.0)
    topups = Set("TopUp")
    exchanges = Set("Exchange")

class TopUp(db.Entity):
    _table_ = "topup"
    ID = PrimaryKey(int, auto=True)
    User = Required(User)
    Jumlah = Required(float)
    Metode = Required(str, 50)
    Tanggal = Required(datetime, default=datetime.now)

class Exchange(db.Entity):
    _table_ = "exchange"
    ID = PrimaryKey(int, auto=True)
    User = Required(User)
    Tujuan = Required(str, 50)
    Gambar = Required(str, 255)
    Diagnosa = Optional(str, 255)
    Tanggal = Required(datetime, default=datetime.now)
    SaldoReward = Required(float, default=0.0)

db.generate_mapping(create_tables=True)

# --- Load Model dan Label ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "MASUKKAN_API_KEY_GEMINI_ANDA")
model = load_model("model/keras_Model.h5", compile=False)
with open("model/labels.txt", "r") as f:
    class_names = [line.strip() for line in f.readlines()]

# --- Luno API ---
LUNO_API_KEY_ID = os.environ.get("LUNO_API_KEY_ID", "jnm42w8w23t8v")
LUNO_API_KEY_SECRET = os.environ.get("LUNO_API_KEY_SECRET", "QSRtcDAysoiAs3IiRrDtqaXeO35SPzFMXU0niYUHNnc")
luno_client = Client(api_key_id=LUNO_API_KEY_ID, api_key_secret=LUNO_API_KEY_SECRET)

# --- Helper ---
@db_session
def get_user_from_session():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.get(UserID=user_id)

def get_exchange_reward(tujuan: str) -> float:
    tujuan = tujuan.lower()
    return 100000.0 if tujuan == "dokter" else 200000.0 if tujuan == "data_ai" else 0.0

# --- Routes ---

@app.route("/", methods=["GET"])
def index():
    return """
    <h1>KuSehat Flask API</h1>
    <p>API berjalan. Gunakan Postman atau curl untuk mengakses endpoint.</p>
    <ul>
      <li><a href="/api">Lihat daftar endpoint</a></li>
    </ul>
    """

@app.route("/api", methods=["GET"])
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
        if rule.endpoint != 'static':
            output.append(f"{rule.rule} [{methods}]")
    return jsonify({"available_endpoints": output})

@app.route("/api/register", methods=["POST"])
@db_session
def register_user():
    data = request.json
    if User.get(Email=data.get("email")):
        return jsonify({"error": "Email sudah terdaftar"}), 409
    User(NamaUser=data.get("nama"), Email=data.get("email"), Password=data.get("password"))
    return jsonify({"message": "Pendaftaran berhasil"}), 201

@app.route("/api/login", methods=["POST"])
@db_session
def login_user():
    data = request.json
    user = User.get(Email=data.get("email"), Password=data.get("password"))
    if user:
        session['user_id'] = user.UserID
        user.Login_Date = datetime.now()
        return jsonify({"message": "Login berhasil", "user_id": user.UserID}), 200
    return jsonify({"error": "Email atau Password salah"}), 401

@app.route("/api/logout", methods=["POST"])
def logout_user():
    session.clear()
    return jsonify({"message": "Logout berhasil"}), 200

@app.route("/api/user", methods=["GET", "PUT"])
@db_session
def user_profile():
    user = get_user_from_session()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if request.method == "GET":
        exchanges = [{"tujuan": e.Tujuan, "tanggal": e.Tanggal.isoformat(), "reward": e.SaldoReward} for e in user.exchanges]
        return jsonify({
            "nama": user.NamaUser,
            "email": user.Email,
            "saldo": user.Saldo,
            "riwayat_penukaran": exchanges
        }), 200
    data = request.json
    if user.Password != data.get("old_password"):
        return jsonify({"error": "Password lama tidak cocok"}), 403
    user.NamaUser = data.get("nama")
    user.Email = data.get("email")
    user.Password = data.get("new_password")
    return jsonify({"message": "Data berhasil diperbarui"}), 200

@app.route("/api/diagnose", methods=["POST"])
@db_session
def diagnose_image():
    user = get_user_from_session()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    today_uploads = select(e for e in Exchange if e.User == user and e.Tanggal.date() == date.today() and e.Tujuan == "deteksi").count()
    if today_uploads >= 3 and user.Saldo < 150000:
        return jsonify({"error": "Batas upload harian tercapai. Lakukan top up untuk menjadi Premium."}), 402
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "File gambar tidak ditemukan"}), 400
    try:
        filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(image_path)
        image = cv2.resize(cv2.imread(image_path), (224, 224))
        image_array = (np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3) / 127.5) - 1
        prediction = model.predict(image_array)
        class_name = class_names[np.argmax(prediction)]
        confidence = float(np.max(prediction))
        prompt = f"Berikan penjelasan detail mengenai penyakit kulit '{class_name}'."
        response = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}", 
                                 json={"contents": [{"parts": [{"text": prompt}]}]})
        gemini_info = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Info tidak tersedia.")
        Exchange(User=user, Tujuan="deteksi", Gambar=filename, Diagnosa=class_name, SaldoReward=0.0)
        return jsonify({
            "penyakit": class_name,
            "kepercayaan": f"{confidence:.2%}",
            "penjelasan": gemini_info,
            "image_url": url_for('static', filename=f'uploads/{filename}', _external=True)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Gagal memproses gambar: {str(e)}"}), 500

@app.route("/api/exchange", methods=["POST"])
@db_session
def exchange_image():
    user = get_user_from_session()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    file = request.files.get("image")
    tujuan = request.form.get("tujuan")
    if not file or not tujuan:
        return jsonify({"error": "Data tidak lengkap"}), 400
    reward = get_exchange_reward(tujuan)
    if reward == 0:
        return jsonify({"error": "Tujuan penukaran tidak valid"}), 400
    filename = f"exchange_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    user.Saldo += reward
    Exchange(User=user, Tujuan=tujuan, Gambar=filename, SaldoReward=reward)
    return jsonify({
        "message": f"Gambar berhasil ditukar! Saldo Anda bertambah IDR {reward:,.0f}",
        "saldo_baru": user.Saldo
    }), 200

@app.route("/api/topup/address", methods=["POST"])
@db_session
def get_topup_address():
    user = get_user_from_session()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    metode_map = {"btc": "XBT", "eth": "ETH"}
    asset = metode_map.get(data.get("metode"))
    if not asset:
        return jsonify({"error": "Metode pembayaran tidak valid"}), 400
    try:
        res = luno_client.get_funding_address(asset=asset)
        TopUp(User=user, Jumlah=float(data.get("jumlah")), Metode=asset)
        return jsonify({"address": res.get("address")}), 200
    except Exception as e:
        return jsonify({"error": f"Gagal mengambil alamat deposit: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
