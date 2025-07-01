import os
import base64
import uuid
import cv2
import numpy as np
import requests
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from keras.models import load_model

# Konfigurasi API You.com (pakai endpoint ydc-index.io)
YOU_API_KEY = "a0a7ea3c-70af-45b2-a1a3-13defad18b27-1RfxPyETU8N2v5f4r1d4elnD"
YOU_API_URL = "https://api.ydc-index.io/search"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load model dan label
model = load_model("model/keras_Model.h5", compile=False)
class_names = open("model/labels.txt", "r").readlines()

# 🔹 Fungsi You.com: Jelaskan penyakit berdasarkan nama (pakai ydc-index.io)
def get_you_diagnosis(disease_name):
    query = f"penyakit {disease_name}, gejala, penyebab, penyembuhan dan obat"

    try:
        headers = {"X-API-Key": YOU_API_KEY}
        params = {"query": query}
        response = requests.get(YOU_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Ambil semua snippet hasil pencarian
        snippets = data.get("snippets", [])
        if not snippets:
            return "❌ Tidak ada informasi yang ditemukan dari You.com."

        # Gabungkan semua hasil snippet
        combined = "<br>".join([s.get("snippet", "") for s in snippets])
        return combined
    except Exception as e:
        return f"❌ You AI gagal menjawab: {str(e)}"

# 🔹 Prediksi gambar dengan Keras
def predict_keras(image_np):
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
    you_info = get_you_diagnosis(predicted_label)

    result = (
        f"📸 Deteksi Kamera: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan Model: {confidence:.2%}<br><br>"
        f"🧠 You.com Info:<br>{you_info}"
    )
    return result, image_path

# 🔹 Deteksi lewat upload gambar
def detect_disease_with_upload(image_path):
    with open(image_path, "rb") as img_file:
        b64_image = base64.b64encode(img_file.read()).decode("utf-8")

    predicted_label, confidence = predict_keras(cv2.imread(image_path))
    you_info = get_you_diagnosis(predicted_label)

    result = (
        f"📤 Deteksi Upload: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan Model: {confidence:.2%}<br><br>"
        f"🧠 You.com Info:<br>{you_info}"
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
