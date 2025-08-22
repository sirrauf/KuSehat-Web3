import os
import uuid
import numpy as np
import requests
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.utils import secure_filename
from pony.orm import Database, Required, Optional, PrimaryKey, Set, db_session
from luno_python.client import Client
from PIL import Image

# =========================
# Setup
# =========================
app = Flask(__name__)
app.secret_key = "change_me"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ENABLE_AI = True
GEMINI_API_KEY = "AIzaSyDb3F5n7dHIHlz9dnUE2rMKh6kXQM8IcB4"   # hardcode API Key

# =========================
# Database
# =========================
db = Database()
db.bind(
    provider='mysql',
    host="localhost",
    user="root",
    passwd="",        # ganti sesuai konfigurasi MySQL kamu
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
    PaketAktif = Required(bool, default=False)   # 🔑 paket seumur hidup
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

# =========================
# AI Keras (lazy load)
# =========================
model = None
class_names = []

def load_ai_model():
    global model, class_names
    if model is not None:
        return
    try:
        from keras.models import load_model
        model_path = "model/keras_Model.h5"
        labels_path = "model/labels.txt"
        if not (os.path.isfile(model_path) and os.path.isfile(labels_path)):
            return
        _model = load_model(model_path, compile=False)
        with open(labels_path, "r") as f:
            _class_names = [line.strip() for line in f]
        model, class_names = _model, _class_names
    except Exception as e:
        print("Gagal load model AI:", str(e))

def detect_disease(image_path):
    """Deteksi penyakit menggunakan model AI"""
    load_ai_model()
    if model is None:
        return {"class_name": "Tidak diketahui", "confidence": 0.0}

    image = Image.open(image_path).convert("RGB").resize((224, 224))
    image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)
    image = (image / 127.5) - 1
    prediction = model.predict(image)
    index = int(np.argmax(prediction))
    class_name = class_names[index].strip()
    confidence = float(prediction[0][index])
    return {"class_name": class_name, "confidence": confidence}

def analyze_with_gemini(disease_name, confidence):
    """Analisis lanjutan menggunakan Gemini API"""
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY belum diatur"

    prompt = f"""
    Terdeteksi penyakit bernama: {disease_name} 
    dengan tingkat deteksi penyakit {confidence:.2%}.
    
    Tolong berikan analisis medis dengan format berikut:
    1. Deskripsi singkat penyakit ini
    2. Obat dan tindakan medis seperti apa
    3. Cara penyembuhan secara medis
    4. Kapan harus ke dokter
    """

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={"Content-Type": "application/json"}
        )
        if response.ok:
            data = response.json()
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "❌ Tidak ada hasil.")
        else:
            return f"❌ Error Gemini: {response.text}"
    except Exception as e:
        return f"❌ Gagal akses Gemini: {str(e)}"

# =========================
# Routes
# =========================
@app.route("/", methods=["GET", "POST"])
@db_session
def home():
    diagnosis = ""
    image_path = ""
    user = None
    if "user_id" in session:
        user = User.get(UserID=session["user_id"])

    if request.method == "POST" and "image" in request.files:
        if not user:
            return "❌ Harus login dulu."

        # 🔑 cek paket user
        if not user.PaketAktif:
            if user.Saldo < 150000:
                return "❌ Saldo tidak cukup untuk aktivasi paket (Rp 150.000)"
            user.Saldo -= 150000
            user.PaketAktif = True   # aktifkan paket selamanya

        file = request.files["image"]
        if file and file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)

            # Step 1: deteksi AI
            result = detect_disease(image_path)
            disease_name = result["class_name"]
            confidence = result["confidence"]

            # Step 2: analisis Gemini
            gemini_result = analyze_with_gemini(disease_name, confidence)

            diagnosis = f"""
            🦠 Penyakit terdeteksi: {disease_name}
            📊 Tingkat deteksi penyakit: {confidence:.2%}
            
            📋 Analisis Gemini:
            {gemini_result}
            """

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
@app.route("/topup", methods=["POST"])
@db_session
def topup():
    """
    Menangani permintaan top up dari pengguna.
    """
    # 1. Pastikan pengguna sudah login
    if "user_id" not in session:
        # Jika tidak login, kembalikan ke halaman utama dengan pesan error
        return render_template("index.html", 
                               topup_error="Anda harus login untuk melakukan top up.", 
                               section="topup")

    # 2. Ambil data dari form
    user = User.get(UserID=session["user_id"])
    jumlah_str = request.form.get("jumlah")
    metode = request.form.get("metode")

    # 3. Validasi input
    if not jumlah_str or not metode:
        return render_template("index.html", 
                               user=user, 
                               topup_error="Jumlah dan metode pembayaran harus diisi.", 
                               section="topup")

    try:
        jumlah = float(jumlah_str)
        if jumlah <= 0:
            raise ValueError("Jumlah harus positif")
    except ValueError:
        return render_template("index.html", 
                               user=user, 
                               topup_error="Jumlah yang dimasukkan tidak valid.", 
                               section="topup")

    # 4. Simulasi pembuatan alamat deposit (untuk tujuan demo)
    # Di aplikasi nyata, ini akan memanggil API dari payment gateway crypto
    topup_address = ""
    if metode == "btc":
        topup_address = f"btc_demo_address_{uuid.uuid4().hex}"
    elif metode == "eth":
        topup_address = f"0x_eth_demo_address_{uuid.uuid4().hex}"
    
    # 5. Catat transaksi topup di database
    # PENTING: Di aplikasi nyata, saldo pengguna baru ditambahkan SETELAH 
    # pembayaran dikonfirmasi di blockchain, biasanya melalui webhook.
    # Untuk penyederhanaan, kita langsung tambahkan di sini.
    TopUp(User=user, Jumlah=jumlah, Metode=metode, Tanggal=datetime.now())
    user.Saldo += jumlah

    # 6. Tampilkan kembali halaman dengan alamat deposit
    # Variabel `section="topup"` penting agar halaman tetap di tab Top Up
    return render_template("index.html", 
                           user=user, 
                           topup_address=topup_address, 
                           section="topup")
    
@app.route("/exchange", methods=["POST"])
@db_session
def exchange():
    if "user_id" not in session:
        return "❌ Harus login dulu."

    user = User.get(UserID=session["user_id"])
    tujuan = request.form.get("tujuan")
    file = request.files.get("image")
    if not file:
        return "❌ Gambar tidak ada."

    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(image_path)

    reward = 100000.0 if tujuan == "dokter" else 200000.0

    Exchange(User=user, Tujuan=tujuan, Gambar=filename,
             Diagnosa="Upload ke exchange",
             Tanggal=datetime.now(), SaldoReward=reward)
    user.Saldo += reward

    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
