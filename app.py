import os
import base64
import uuid
import cv2
import numpy as np
import requests
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from keras.models import load_model

# Konfigurasi Gemini
GEMINI_API_KEY = "AIzaSyDwniC_zbYaVpRWRGjGk9HnhJWAe9IPZGM" # Ganti dengan API Key Anda
MODEL_NAME = "gemini-1.5-flash" # Model yang lebih baru
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load model dan label
try:
    model = load_model("model/keras_Model.h5", compile=False)
    with open("model/labels.txt", "r") as f:
        class_names = f.readlines()
except IOError as e:
    print(f"Error loading model or labels: {e}")
    model = None
    class_names = []

# 🔹 Fungsi Gemini AI: Jelaskan penyakit berdasarkan nama
def get_gemini_diagnosis(disease_name):
    prompt = (
        f"Tolong jelaskan informasi tentang penyakit kulit berikut ini dalam format HTML yang rapi:\n\n"
        f"Nama penyakit: {disease_name}\n\n"
        f"Saya ingin tahu:\n"
        f"1.  **Deskripsi**: Apa itu penyakit ini?\n"
        f"2.  **Gejala dan Penyebab**: Apa saja gejala utamanya dan apa yang menyebabkannya?\n"
        f"3.  **Cara Penyembuhan**: Bagaimana cara umum untuk menanganinya?\n"
        f"4.  **Rekomendasi Obat**: Sebutkan contoh obat yang biasa digunakan (jika ada).\n"
        f"Jelaskan dengan bahasa yang mudah dimengerti oleh orang awam."
    )
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"❌ Gemini AI gagal menjawab: {str(e)}"

# 🔹 Prediksi gambar dengan Keras
def predict_keras(image_np):
    if model is None:
        return "Model tidak dimuat", 0.0
    image = cv2.resize(image_np, (224, 224), interpolation=cv2.INTER_AREA)
    image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)
    image = (image / 127.5) - 1
    prediction = model.predict(image)
    index = np.argmax(prediction)
    class_name = class_names[index].strip()
    confidence_score = float(prediction[0][index])
    return class_name, confidence_score

# 🔹 Deteksi lewat kamera
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
        f"📸 Deteksi Kamera: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan Model: {confidence:.2%}<br><br>"
        f"🧠 **Penjelasan dari Gemini AI:**<br>{gemini_info}"
    )
    return result, image_path

# 🔹 Deteksi lewat upload gambar
def detect_disease_with_upload(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return "❌ Gagal membaca file gambar", None
        
    predicted_label, confidence = predict_keras(image)
    gemini_info = get_gemini_diagnosis(predicted_label)

    result = (
        f"📤 Deteksi Upload: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan Model: {confidence:.2%}<br><br>"
        f"🧠 **Penjelasan dari Gemini AI:**<br>{gemini_info}"
    )
    return result

# 🔹 Route utama
@app.route("/", methods=["GET", "POST"])
def home():
    diagnosis = ""
    image_path = ""

    if request.method == "POST":
        method = request.form.get("method")
        if method == "upload":
            file = request.files.get("image")
            if not file or file.filename == "":
                diagnosis = "❌ Gambar tidak ditemukan."
            else:
                filename = secure_filename(file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image_path)
                diagnosis = detect_disease_with_upload(image_path)
        elif method == "camera":
            diagnosis, image_path = detect_disease_with_camera()

    return render_template("index.html", diagnosis=diagnosis, image_path=image_path)

if __name__ == "__main__":
    app.run(debug=True)
