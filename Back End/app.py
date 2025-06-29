import os
import base64
import uuid
import cv2
import numpy as np
import tensorflow as tf
from flask import Flask, render_template, request
from openai import OpenAI
from werkzeug.utils import secure_filename
from modelsdb import db, User, Checklist, Item
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# GPT via OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="<OPENROUTER_API_KEY>",  # Ganti dengan API key OpenRouter Anda
)

# Load TFLite Model
interpreter = tf.lite.Interpreter(model_path="model/model.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Load Labels
with open("model/labels.txt", "r") as f:
    labels = [line.strip() for line in f.readlines()]


# 🔹 Fungsi GPT dengan Prompt Otomatis
def get_gpt_diagnosis(disease_name):
    prompt = (
        f"Tolong jelaskan informasi tentang penyakit berikut ini:\n\n"
        f"Nama penyakit: {disease_name}\n\n"
        f"Saya ingin tahu:\n"
        f"- Apa itu penyakit ini?\n"
        f"- Bagaimana gejala dan penyebabnya?\n"
        f"- Bagaimana cara penyembuhannya?\n"
        f"- Apa saja obat atau salep yang umum digunakan untuk penyakit ini?\n"
        f"Jelaskan dengan bahasa yang mudah dipahami masyarakat awam."
    )

    response = client.chat.completions.create(
        model="openai/gpt-4o",
        extra_headers={
            "HTTP-Referer": "https://yourdomain.com",
            "X-Title": "AI Deteksi Penyakit Otomatis"
        },
        messages=[
            {"role": "system", "content": "Kamu adalah dokter AI yang memberikan informasi penyakit secara akurat dan mudah dipahami."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


# 🔹 Fungsi Prediksi TFLite
def predict_tflite(image_np):
    image = cv2.resize(image_np, (224, 224))  # Sesuaikan dengan ukuran model
    input_data = np.expand_dims(image, axis=0).astype(np.float32) / 255.0
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])
    pred_index = np.argmax(output_data)
    return labels[pred_index], float(output_data[0][pred_index])


# 🔹 Fungsi Kamera (OpenCV)
def detect_disease_with_camera():
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return "❌ Kamera tidak tersedia", None

    ret, frame = cam.read()
    cam.release()

    if not ret:
        return "❌ Gagal mengambil gambar dari kamera", None

    filename = f"{uuid.uuid4().hex}.jpg"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    cv2.imwrite(image_path, frame)

    predicted_label, confidence = predict_tflite(frame)
    gpt_info = get_gpt_diagnosis(predicted_label)

    result = (
        f"📸 Deteksi Kamera: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan Model: {confidence:.2%}<br><br>"
        f"🧠 GPT-4o Menjawab:<br>{gpt_info}"
    )
    return result, image_path


# 🔹 Fungsi Upload Gambar (tanpa TFLite, hanya GPT)
def detect_disease_with_upload(image_path):
    with open(image_path, "rb") as img_file:
        b64_image = base64.b64encode(img_file.read()).decode("utf-8")

    prompt = (
        "Saya mengunggah gambar penyakit kulit. Tolong bantu identifikasi dan jawab secara detail:\n"
        "- Nama penyakit\n"
        "- Deskripsi penyakit\n"
        - "Cara penyembuhan\n"
        "- Nama obat yang umum digunakan\n\n"
        "Berikan jawaban dengan bahasa yang mudah dimengerti.\n"
        f"Gambar base64:\n{b64_image}"
    )

    response = client.chat.completions.create(
        model="openai/gpt-4o",
        extra_headers={
            "HTTP-Referer": "https://yourdomain.com",
            "X-Title": "AI Upload Gambar Penyakit"
        },
        messages=[
            {"role": "system", "content": "Kamu adalah asisten dokter AI yang sangat pintar dan menjelaskan penyakit dengan bahasa awam."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# Route Halaman Beranda atau Halaman Home 
@app.route("/")
def home():
    render_template("index.html")
    
# ROUTE Dashboard User
@app.route("/dashboarduser", methods=["GET", "POST"])
def dashboarduser():
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
                gpt_result = detect_disease_with_upload(image_path)
                diagnosis = f"🧠 GPT-4o Analisa Upload Gambar:<br>{gpt_result}"

        elif method == "camera":
            diagnosis, image_path = detect_disease_with_camera()

    return render_template("index.html", diagnosis=diagnosis, image_path=image_path)

if __name__ == "__main__":
    app.run(debug=True)