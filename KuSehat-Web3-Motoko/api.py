import os
import uuid
import cv2
import numpy as np
import requests
import base64
from datetime import datetime, date
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from keras.models import load_model
from pony.orm import Database, Required, Optional, PrimaryKey, Set, db_session, select, commit
from luno_python.client import Client
from flask_cors import CORS

# --- Inisialisasi Aplikasi dan Database ---
app = Flask(__name__)
CORS(app) # Izinkan permintaan dari semua asal, penting untuk interaksi dengan canister
app.secret_key = 'rahasia_kusehat_api'

# Konfigurasi Upload
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Koneksi Database (Sama seperti sebelumnya) ---
db = Database()
# PENTING: Pastikan database 'kusehat' ada di MySQL Anda
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

db.generate_mapping(create_tables=True)

# --- Setup Klien API (Luno, AI Model) ---
try:
    LUNO_API_KEY_ID = "jnm42w8w23t8v" # Ganti dengan key Anda
    LUNO_API_KEY_SECRET = "QSRtcDAysoiAs3IiRrDtqaXeO35SPzFMXU0niYUHNnc" # Ganti dengan secret Anda
    luno_client = Client(api_key_id=LUNO_API_KEY_ID, api_key_secret=LUNO_API_KEY_SECRET)
except Exception as e:
    luno_client = None
    print(f"⚠️ Peringatan: Gagal menginisialisasi klien Luno: {e}")

try:
    model = load_model("model/keras_Model.h5", compile=False)
    with open("model/labels.txt", "r") as f:
        class_names = [line.strip() for line in f.readlines()]
    print("✅ Model AI dan label berhasil dimuat.")
except Exception as e:
    model = None
    class_names = None
    print(f"❌ Gagal memuat model AI: {e}")

# --- Fungsi Helper ---
def get_gemini_explanation(class_name):
    GEMINI_API_KEY = "AIzaSyDwniC_zbYaVpRWRGjGk9HnhJWAe9IPZGM" # Ganti dengan API Key Anda
    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        f"Tolong jelaskan informasi tentang penyakit kulit berikut ini dalam format HTML yang rapi:\n\n"
        f"Nama penyakit: {class_name}\n\n"
        f"1. Deskripsi\n2. Gejala dan Penyebab\n3. Cara Penyembuhan\n4. Rekomendasi Obat"
    )
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        data = response.json()
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    except Exception:
        return "<p>Gagal mendapatkan penjelasan dari AI.</p>"

def get_exchange_reward(tujuan):
    tujuan = tujuan.lower()
    if tujuan == "dokter": return 100_000
    if tujuan == "data_ai": return 200_000
    return 0

# --- Endpoint API ---

@app.route("/api/register", methods=["POST"])
@db_session
def api_register():
    data = request.get_json()
    if User.get(Email=data['email']):
        return jsonify({"success": False, "message": "❌ Email sudah terdaftar."})
    User(NamaUser=data['nama'], Email=data['email'], Password=data['password'], Register_Date=datetime.now())
    return jsonify({"success": True, "message": "✅ Pendaftaran berhasil. Silakan login."})

@app.route("/api/login", methods=["POST"])
@db_session
def api_login():
    data = request.get_json()
    user = User.get(Email=data['email'], Password=data['password'])
    if user:
        user.Login_Date = datetime.now()
        # Mengembalikan data user yang dibutuhkan oleh frontend
        user_data = {
            "UserID": user.UserID,
            "NamaUser": user.NamaUser,
            "Email": user.Email,
            "Saldo": user.Saldo,
            "exchanges": sorted([{"Tanggal": ex.Tanggal.strftime("%Y-%m-%d %H:%M"), "Tujuan": ex.Tujuan, "SaldoReward": ex.SaldoReward, "Gambar": ex.Gambar} for ex in user.exchanges], key=lambda x: x['Tanggal'], reverse=True)
        }
        return jsonify({"success": True, "user": user_data})
    return jsonify({"success": False, "message": "❌ Email atau Password salah."})

@app.route("/api/user_data/<int:user_id>", methods=["GET"])
@db_session
def api_user_data(user_id):
    user = User.get(UserID=user_id)
    if user:
        user_data = {
            "UserID": user.UserID,
            "NamaUser": user.NamaUser,
            "Email": user.Email,
            "Saldo": user.Saldo,
            "exchanges": sorted([{"Tanggal": ex.Tanggal.strftime("%Y-%m-%d %H:%M"), "Tujuan": ex.Tujuan, "SaldoReward": ex.SaldoReward, "Gambar": ex.Gambar} for ex in user.exchanges], key=lambda x: x['Tanggal'], reverse=True)
        }
        return jsonify({"success": True, "user": user_data})
    return jsonify({"success": False, "message": "User tidak ditemukan"}), 404


@app.route("/api/update_user", methods=["POST"])
@db_session
def api_update_user():
    data = request.get_json()
    user = User.get(UserID=data['user_id'])
    if not user or user.Password != data['old_password']:
        return jsonify({"success": False, "message": "❌ Password lama tidak cocok atau user tidak ditemukan."})
    
    user.NamaUser = data['nama']
    user.Email = data['email']
    user.Password = data['new_password']
    commit()
    return jsonify({"success": True, "message": "✅ Data berhasil diperbarui."})

@app.route("/api/topup", methods=["POST"])
@db_session
def api_topup():
    data = request.get_json()
    user = User.get(UserID=data['user_id'])
    if not user:
        return jsonify({"success": False, "message": "User tidak ditemukan"}), 404

    metode = data.get("metode")
    jumlah = float(data.get("jumlah", 0))
    
    if not luno_client:
        return jsonify({"success": False, "error": "Layanan Top Up tidak tersedia saat ini."})

    try:
        asset = "XBT" if metode == "btc" else "ETH"
        res = luno_client.get_funding_address(asset=asset)
        alamat = res["address"]
        
        # Di dunia nyata, Anda akan menunggu konfirmasi blockchain.
        # Di sini kita langsung menambahkan saldo untuk tujuan demonstrasi.
        TopUp(User=user, Jumlah=jumlah, Metode=metode.upper(), Tanggal=datetime.now())
        user.Saldo += jumlah
        commit()
        
        return jsonify({"success": True, "address": alamat, "new_saldo": user.Saldo})
    except Exception as e:
        return jsonify({"success": False, "error": f"❌ Gagal mengambil alamat: {str(e)}"})

@app.route("/api/detect", methods=["POST"])
@db_session
def api_detect():
    data = request.get_json()
    user_id = data.get('user_id')
    user = User.get(UserID=user_id)
    if not user: return jsonify({"error": "User tidak valid"}), 403

    # Logika pembatasan upload
    today = date.today()
    upload_count = select(e for e in Exchange if e.User == user and e.Tanggal.date() == today and e.Tujuan == "deteksi").count()
    
    if upload_count >= 3 and user.Saldo < 150000:
        return jsonify({"error": "Batas upload harian tercapai. Silakan Top Up untuk menjadi Premium."}), 402

    if not model: return jsonify({"error": "Model AI tidak siap."}), 500

    image_b64 = data.get('image_base64')
    image_data = base64.b64decode(image_b64)
    np_arr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Simpan gambar untuk riwayat
    filename = secure_filename(f"detect_{uuid.uuid4().hex}.png")
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    cv2.imwrite(image_path, image)

    # Proses AI
    image_resized = cv2.resize(image, (224, 224))
    image_array = np.asarray(image_resized, dtype=np.float32).reshape(1, 224, 224, 3)
    image_normalized = (image_array / 127.5) - 1
    prediction = model.predict(image_normalized)
    index = np.argmax(prediction)
    class_name = class_names[index]
    confidence = float(prediction[0][index])

    explanation = get_gemini_explanation(class_name)
    
    # Catat exchange deteksi
    Exchange(User=user, Tujuan="deteksi", Gambar=filename, Diagnosa=class_name, Tanggal=datetime.now(), SaldoReward=0.0)
    
    return jsonify({
        "success": True,
        "diagnosis": class_name,
        "confidence": f"{confidence:.2%}",
        "explanation": explanation,
        "image_url": f"/static/uploads/{filename}"
    })

@app.route("/api/exchange", methods=["POST"])
@db_session
def api_exchange():
    data = request.get_json()
    user = User.get(UserID=data['user_id'])
    if not user: return jsonify({"success": False, "message": "User tidak ditemukan"}), 404

    tujuan = data.get("tujuan")
    image_b64 = data.get('image_base64')
    image_data = base64.b64decode(image_b64)
    
    filename = f"exchange_{uuid.uuid4().hex}_{secure_filename(tujuan)}.png"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(image_path, "wb") as f:
        f.write(image_data)

    reward = get_exchange_reward(tujuan)
    user.Saldo += reward
    
    Exchange(User=user, Tujuan=tujuan, Gambar=filename, Diagnosa="", Tanggal=datetime.now(), SaldoReward=reward)
    commit()
    
    return jsonify({
        "success": True, 
        "message": f"🎁 Gambar berhasil ditukar. Anda mendapat saldo IDR {reward:,}.",
        "new_saldo": user.Saldo
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5003, debug=True)
