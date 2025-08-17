import os
import uuid
import cv2
import numpy as np
import requests
from datetime import datetime, date
from flask import Flask, request, jsonify, session
from werkzeug.utils import secure_filename
from keras.models import load_model
from pony.orm import Database, Required, Optional, PrimaryKey, Set, db_session, select
from luno_python.client import Client
from flask_cors import CORS
from pony.orm import desc

# --- Konfigurasi Aplikasi ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret-key-super-rahasia-untuk-development")
CORS(app, supports_credentials=True) # Izinkan request dari domain lain (frontend Nuxt)

# --- Konfigurasi Database (Pony ORM) ---
db = Database()
# Pastikan database 'kusehat' sudah ada di MySQL Anda
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

# --- Konfigurasi API Klien & Model---
# Ganti dengan kredensial Luno Anda atau gunakan environment variables
LUNO_API_KEY_ID = "jnm42w8w23t8v"
LUNO_API_KEY_SECRET = "QSRtcDAysoiAs3IiRrDtqaXeO35SPzFMXU0niYUHNnc"
luno_client = Client(api_key_id=LUNO_API_KEY_ID, api_key_secret=LUNO_API_KEY_SECRET)

# Ganti dengan API Key Gemini Anda yang valid
GEMINI_API_KEY = "AIzaSyDwniC_zbYaVpRWRGjGk9HnhJWAe9IPZGM"

# Pastikan path ke model dan label sudah benar
# try:
#     model = load_model("model/keras_Model.h5", compile=False)
#     with open("model/labels.txt", "r") as f:
#         class_names = [line.strip() for line in f.readlines()]
# except Exception as e:
#     print(f"Gagal memuat model atau labels: {e}")
#     model = None
#     class_names = []


# --- Helper Functions ---
@db_session
def get_user_from_session():
    """Mendapatkan objek User dari session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.get(UserID=user_id)

def get_exchange_reward(tujuan: str) -> float:
    """
    Menghitung reward saldo berdasarkan tujuan penukaran.
    Reward ini diasumsikan sebagai saldo yang dipotong.
    """
    if tujuan.lower() == "dokter":
        return 100000.0
    elif tujuan.lower() == "data_ai":
        return 200000.0
    return 0.0

# --- Endpoint API ---

@app.route("/", methods=["GET"])
def api_documentation():
    """
    API Endpoint: Dokumentasi API
    Method: GET
    Deskripsi: Mengembalikan daftar endpoint API dan cara penggunaannya.
    """
    docs = {
        "message": "Selamat datang di API KuSehat! Berikut adalah daftar endpoint yang tersedia:",
        "endpoints": {
            "/api/register": {
                "method": "POST",
                "description": "Mendaftarkan pengguna baru.",
                "body": {"nama": "string", "email": "string", "password": "string"}
            },
            "/api/login": {
                "method": "POST",
                "description": "Login pengguna dan membuat session.",
                "body": {"email": "string", "password": "string"}
            },
            "/api/logout": {
                "method": "POST",
                "description": "Logout pengguna dan menghapus session."
            },
            "/api/user": {
                "method": "GET",
                "description": "Mengambil detail profil pengguna yang sedang login."
            },
            "/api/diagnose": {
                "method": "POST",
                "description": "Menganalisis gambar yang diunggah untuk diagnosa.",
                "body": {"image": "file"}
            },
            "/api/topup": {
                "method": "POST",
                "description": "Menambahkan saldo ke akun pengguna.",
                "body": {"jumlah": "float", "metode": "string"}
            },
            "/api/exchange": {
                "method": "POST",
                "description": "Menukar saldo pengguna untuk layanan tertentu.",
                "body": {"tujuan": "string ('dokter' atau 'data_ai')"}
            }
        }
    }
    return jsonify(docs), 200

@app.route("/api/register", methods=["POST"])
@db_session
def register_user():
    """
    API Endpoint: Registrasi Pengguna Baru
    Method: POST
    Deskripsi: Mendaftarkan pengguna baru ke dalam sistem.
    Request Body:
        - nama (string): Nama lengkap pengguna.
        - email (string): Alamat email pengguna, harus unik.
        - password (string): Kata sandi pengguna.
    Response:
        - 201 Created: Jika pendaftaran berhasil.
        - 400 Bad Request: Jika data tidak lengkap.
        - 409 Conflict: Jika email sudah terdaftar.
    """
    data = request.json
    if not all(k in data for k in ['nama', 'email', 'password']):
        return jsonify({"error": "Data tidak lengkap"}), 400
    if User.get(Email=data["email"]):
        return jsonify({"error": "Email sudah terdaftar"}), 409
    
    User(NamaUser=data["nama"], Email=data["email"], Password=data["password"])
    return jsonify({"message": "Pendaftaran berhasil"}), 201

@app.route("/api/login", methods=["POST"])
@db_session
def login_user():
    """
    API Endpoint: Login Pengguna
    Method: POST
    Deskripsi: Mengautentikasi pengguna dan membuat session.
    Request Body:
        - email (string): Alamat email pengguna.
        - password (string): Kata sandi pengguna.
    Response:
        - 200 OK: Jika login berhasil, mengembalikan nama pengguna.
        - 400 Bad Request: Jika data tidak lengkap.
        - 401 Unauthorized: Jika email atau password salah.
    """
    data = request.json
    if not all(k in data for k in ['email', 'password']):
        return jsonify({"error": "Data tidak lengkap"}), 400
        
    user = User.get(Email=data["email"], Password=data["password"])
    if user:
        session['user_id'] = user.UserID
        user.Login_Date = datetime.now()
        return jsonify({"message": "Login berhasil", "user": {"nama": user.NamaUser}}), 200
    return jsonify({"error": "Email atau Password salah"}), 401

@app.route("/api/logout", methods=["POST"])
def logout_user():
    """
    API Endpoint: Logout Pengguna
    Method: POST
    Deskripsi: Menghapus session pengguna.
    Response:
        - 200 OK: Jika logout berhasil.
    """
    session.clear()
    return jsonify({"message": "Logout berhasil"}), 200

@app.route("/api/user", methods=["GET"])
@db_session
def user_profile():
    """
    API Endpoint: Profil Pengguna
    Method: GET
    Deskripsi: Mengambil detail profil pengguna yang sedang login.
    Response:
        - 200 OK: Mengembalikan detail pengguna, saldo, status premium, dan riwayat penukaran.
        - 401 Unauthorized: Jika pengguna belum login.
    """
    user = get_user_from_session()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    today_uploads = select(e for e in user.exchanges if e.Tanggal.date() == date.today() and e.Tujuan == "deteksi").count()
    
    # Ambil riwayat penukaran dan format
    exchange_history = [{
        "Tanggal": ex.Tanggal.strftime("%Y-%m-%d %H:%M"),
        "Tujuan": ex.Tujuan,
        "Reward": f'{ex.SaldoReward:.2f}',
        "Gambar": ex.Gambar
    } for ex in user.exchanges.order_by(desc(ex.Tanggal))]


    return jsonify({
        "nama": user.NamaUser,
        "email": user.Email,
        "saldo": f'{user.Saldo:.2f}',
        "uploads_today": today_uploads,
        "is_premium": user.Saldo >= 150000,
        "riwayat_penukaran": exchange_history
    }), 200


@app.route("/api/diagnose", methods=["POST"])
@db_session
def diagnose_image():
    """
    API Endpoint: Diagnosa Gambar
    Method: POST
    Deskripsi: Menganalisis gambar yang diunggah untuk diagnosa.
    Request Body:
        - image (file): File gambar untuk didiagnosa.
    Response:
        - 200 OK: Mengembalikan hasil diagnosa, tingkat kepercayaan, dan penjelasan dari AI.
        - 400 Bad Request: Jika file gambar tidak ditemukan.
        - 401 Unauthorized: Jika pengguna belum login.
    """
    user = get_user_from_session()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if 'image' not in request.files:
        return jsonify({"error": "File gambar tidak ditemukan"}), 400

    file = request.files['image']
    # --- Tempat untuk kode diagnosa AI (Keras & Gemini) ---
    # Karena model tidak dimuat, ini adalah placeholder
    class_name = "Contoh Penyakit"
    confidence = 0.95
    gemini_info = "Ini adalah penjelasan dari Gemini AI mengenai penyakit tersebut."
    
    # Simpan nama file (nama asli, bisa diganti dengan nama unik)
    filename = secure_filename(file.filename)
    # Buat entri Exchange baru untuk riwayat, SaldoReward 0 karena ini diagnosa gratis
    Exchange(User=user, Tujuan="deteksi", Gambar=filename, Diagnosa=class_name, SaldoReward=0.0)

    return jsonify({
        "penyakit": class_name,
        "kepercayaan": f"{confidence:.2%}",
        "penjelasan": gemini_info
    }), 200

@app.route("/api/topup", methods=["POST"])
@db_session
def topup():
    """
    API Endpoint: TopUp Saldo
    Method: POST
    Deskripsi: Menambahkan saldo ke akun pengguna.
    Request Body:
        - jumlah (float): Jumlah saldo yang akan ditambahkan.
        - metode (string): Metode pembayaran topup.
    Response:
        - 200 OK: Jika topup berhasil, mengembalikan saldo baru.
        - 400 Bad Request: Jika data tidak lengkap.
        - 401 Unauthorized: Jika pengguna belum login.
    """
    user = get_user_from_session()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not all(k in data for k in ['jumlah', 'metode']):
        return jsonify({"error": "Data tidak lengkap"}), 400

    try:
        jumlah_topup = float(data["jumlah"])
        metode_topup = data["metode"]
    except ValueError:
        return jsonify({"error": "Jumlah harus berupa angka"}), 400
    
    # Tambahkan saldo pengguna
    user.Saldo += jumlah_topup
    # Buat record TopUp baru
    TopUp(User=user, Jumlah=jumlah_topup, Metode=metode_topup)

    return jsonify({"message": "Top up berhasil", "saldo_baru": f'{user.Saldo:.2f}'}), 200

@app.route("/api/exchange", methods=["POST"])
@db_session
def exchange():
    """
    API Endpoint: Penukaran Saldo
    Method: POST
    Deskripsi: Mengurangi saldo pengguna untuk penukaran tertentu.
    Request Body:
        - tujuan (string): Tujuan penukaran ('dokter' atau 'data_ai').
    Response:
        - 200 OK: Jika penukaran berhasil, mengembalikan saldo baru.
        - 400 Bad Request: Jika data tidak lengkap atau saldo tidak mencukupi.
        - 401 Unauthorized: Jika pengguna belum login.
    """
    user = get_user_from_session()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    if not all(k in data for k in ['tujuan']):
        return jsonify({"error": "Data tidak lengkap"}), 400

    tujuan = data["tujuan"]
    reward = get_exchange_reward(tujuan) # Ini adalah saldo yang dipotong

    if reward > 0:
        if user.Saldo < reward:
             return jsonify({"error": "Saldo tidak mencukupi untuk penukaran ini"}), 400
        
        # Lakukan penukaran saldo
        user.Saldo -= reward
        # Buat entri Exchange baru, dengan SaldoReward sebagai nilai yang dipotong
        Exchange(User=user, Tujuan=tujuan, SaldoReward=reward, Gambar="n/a")
        return jsonify({"message": f"Penukaran untuk {tujuan} berhasil", "saldo_baru": f'{user.Saldo:.2f}'}), 200
    
    return jsonify({"error": "Tujuan penukaran tidak valid"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
