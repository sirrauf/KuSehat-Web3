import os
import uuid
import cv2
import numpy as np
import requests
from datetime import datetime, date
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.utils import secure_filename
from keras.models import load_model
from pony.orm import Database, Required, Optional, PrimaryKey, Set, db_session, select
from luno_python.client import Client

# Luno API Setup
LUNO_API_KEY_ID = "jnm42w8w23t8v"
LUNO_API_KEY_SECRET = "QSRtcDAysoiAs3IiRrDtqaXeO35SPzFMXU0niYUHNnc"
luno_client = Client(api_key_id=LUNO_API_KEY_ID, api_key_secret=LUNO_API_KEY_SECRET)

# Database Setup
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

app = Flask(__name__)
app.secret_key = 'rahasia_kusehat'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Memuat Model dan Label (dilakukan sekali saat aplikasi dimulai)
try:
    model = load_model("model/keras_Model.h5", compile=False)
    with open("model/labels.txt", "r") as f:
        class_names = [line.strip() for line in f.readlines()]
except Exception as e:
    print(f"Error loading model or labels: {e}")
    model = None
    class_names = []

# Gemini Setup
GEMINI_API_KEY = "AIzaSyDwniC_zbYaVpRWRGjGk9HnhJWAe9IPZGM"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

def get_gemini_explanation(disease_name):
     prompt = (
        f"Tolong jelaskan informasi tentang penyakit kulit berikut ini dalam format HTML yang rapi:\n\n"
        f"Nama penyakit: {disease_name}\n\n"
        f"1. Deskripsi singkat tentang penyakit ini\n2. Gejala dan Penyebab\n3. Cara pengobatan harus apa\n4. Rekomendasi Obat\n5.Kapan harus ke dokter\n6.Apakah penyakit ini perlu dioperasi?"
    )
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"]

        return "⚠️ Tidak ada penjelasan yang diberikan Gemini."
    except Exception:
        # fallback singkat, tanpa detail error teknis
        return "⚠️ Layanan AI sedang sibuk, silakan coba lagi nanti."

def process_image_for_detection(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            return {"error": "Gagal membaca file gambar."}
        
        image = cv2.resize(image, (224, 224))
        image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)
        image = (image / 127.5) - 1

        prediction = model.predict(image)
        index = np.argmax(prediction)
        class_name = class_names[index].strip()
        confidence = float(prediction[0][index])

        gemini_info = get_gemini_explanation(class_name)

        diagnosis = (
            f"📤 <b>Deteksi Upload:</b> <b>{class_name}</b><br>"
            f"🧪 <b>Kepercayaan:</b> {confidence:.2%}<br><br>"
            f"🧠 <b>Penjelasan Gemini AI:</b><br>{gemini_info}"
        )
        return {"diagnosis": diagnosis, "class_name": class_name}
    except Exception as e:
        return {"error": f"❌ Terjadi kesalahan saat proses AI: {e}"}

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
            return redirect(url_for("home"))

        today = date.today()
        upload_count = select(e for e in Exchange if e.User == user and e.Tanggal.date() == today and e.Tujuan == "deteksi").count()

        if upload_count >= 3:
            if user.Saldo >= 150000:
                user.Saldo -= 150000
                upload_count = 0
            else:
                return redirect(url_for("topup_page"))

        file = request.files.get("image")
        if not file or file.filename == "":
            diagnosis = "❌ Gambar tidak ditemukan."
        elif not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            diagnosis = "❌ Format file tidak didukung. Gunakan JPG, JPEG, atau PNG."
        else:
            filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)
            
            result = process_image_for_detection(image_path)
            if "error" in result:
                diagnosis = result["error"]
            else:
                diagnosis = result["diagnosis"]
                class_name = result["class_name"]
                Exchange(User=user, Tujuan="deteksi", Gambar=filename, Diagnosa=class_name, Tanggal=datetime.now(), SaldoReward=0.0)

    return render_template("index.html", diagnosis=diagnosis, image_path=image_path,
                           user=user, topup_address="", topup_error="", section="dashboard", today=date.today())

# ✅ sisanya (register, login, dashboard, topup, exchange, logout) tetap sama seperti sebelumnya
# Tidak diubah karena masalah utama hanya di fungsi get_gemini_explanation

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
