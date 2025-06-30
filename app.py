import os
import base64
import uuid
import cv2
import numpy as np
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from keras.models import load_model  # Ganti dari TFLite ke Keras

# Ganti OpenAI dengan gpt4free
import g4f
from g4f import ChatCompletion, Provider

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Load Keras Model
model = load_model("model/keras_Model.h5", compile=False)
class_names = open("model/labels.txt", "r").readlines()

# 🔹 Fungsi GPT dengan Prompt Otomatis (pakai gpt4free)
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

    response = ChatCompletion.create(
        model=g4f.models.gpt_4,
        provider=Provider.You,
        messages=[
            {"role": "system", "content": "Kamu adalah dokter AI yang memberikan informasi penyakit secara akurat dan mudah dipahami."},
            {"role": "user", "content": prompt}
        ]
    )
    return response

# 🔹 Fungsi Prediksi menggunakan Keras
def predict_keras(image_np):
    image = cv2.resize(image_np, (224, 224), interpolation=cv2.INTER_AREA)
    image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)
    image = (image / 127.5) - 1  # Normalisasi
    prediction = model.predict(image)
    index = np.argmax(prediction)
    class_name = class_names[index].strip()
    confidence_score = float(prediction[0][index])
    return class_name, confidence_score

# 🔹 Fungsi Kamera
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

    predicted_label, confidence = predict_keras(frame)
    gpt_info = get_gpt_diagnosis(predicted_label)

    result = (
        f"📸 Deteksi Kamera: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan Model: {confidence:.2%}<br><br>"
        f"🧠 GPT-4free Menjawab:<br>{gpt_info}"
    )
    return result, image_path

# 🔹 Fungsi Upload Gambar
def detect_disease_with_upload(image_path):
    with open(image_path, "rb") as img_file:
        b64_image = base64.b64encode(img_file.read()).decode("utf-8")

    prompt = (
        "Saya mengunggah gambar penyakit kulit. Tolong bantu identifikasi dan jawab secara detail:\n"
        "- Nama penyakit\n"
        "- Deskripsi penyakit\n"
        "- Cara penyembuhan\n"
        "- Nama obat yang umum digunakan\n\n"
        "Berikan jawaban dengan bahasa yang mudah dimengerti.\n"
        f"Gambar base64:\n{b64_image}"
    )

    response = ChatCompletion.create(
        model=g4f.models.gpt_4,
        provider=Provider.You,
        messages=[
            {"role": "system", "content": "Kamu adalah asisten dokter AI yang sangat pintar dan menjelaskan penyakit dengan bahasa awam."},
            {"role": "user", "content": prompt}
        ]
    )
    return response

# 🔹 Halaman beranda/home
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
                gpt_result = detect_disease_with_upload(image_path)
                diagnosis = f"🧠 GPT-4free Analisa Upload Gambar:<br>{gpt_result}"

        elif method == "camera":
            diagnosis, image_path = detect_disease_with_camera()

    return render_template("index.html", diagnosis=diagnosis, image_path=image_path)

if __name__ == "__main__":
    app.run(debug=True)
