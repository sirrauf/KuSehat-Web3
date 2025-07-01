import os
import base64
import uuid
import cv2
import numpy as np
import requests
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from keras.models import load_model

# ✅ API Key YouChat (via OpenRouter.ai atau proxy)
YOU_API_KEY = os.getenv("YOU_API_KEY", "02c4585f-a3e2-4cfc-a0f8-042c003b3c03<__>1RfxPyETU8N2v5f4r1d4elnD")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load model dan label
model = load_model("model/keras_Model.h5", compile=False)
class_names = open("model/labels.txt", "r").readlines()

# 🔹 Fungsi diagnosis penyakit dari teks (YouChat)
def get_you_diagnosis(disease_name):
    prompt = (
        f"Tolong jelaskan informasi tentang penyakit berikut ini:\n\n"
        f"Nama penyakit: {disease_name}\n\n"
        f"Saya ingin tahu:\n"
        f"- Apa itu penyakit ini?\n"
        f"- Bagaimana gejala dan penyebabnya?\n"
        f"- Bagaimana cara penyembuhannya?\n"
        f"- Obat untuk penyakit ini?\n"
        f"Jelaskan dengan bahasa awam."
    )

    try:
        headers = {
            "Authorization": f"Bearer {YOU_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "youchat",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ YouChat gagal menjawab: {str(e)}"

# 🔹 Fungsi diagnosis berdasarkan gambar upload (YouChat)
def get_you_diagnosis_from_image(image_path):
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        prompt = (
            "Saya mengunggah gambar penyakit kulit. Tolong bantu identifikasi dan jawab secara detail:\n"
            "- Nama penyakit\n"
            "- Deskripsi penyakit\n"
            "- Cara penyembuhan\n"
            "- Nama obat\n\n"
            "Jawab dengan bahasa mudah dimengerti.\n"
            f"Gambar base64:\n{image_data}"
        )

        headers = {
            "Authorization": f"Bearer {YOU_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "youchat",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ YouChat gagal menjawab: {str(e)}"

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
    gpt_info = get_you_diagnosis(predicted_label)

    result = (
        f"📸 Deteksi Kamera: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan Model: {confidence:.2%}<br><br>"
        f"🧠 YouChat Menjawab:<br>{gpt_info}"
    )
    return result, image_path

# 🔹 Deteksi lewat upload gambar
def detect_disease_with_upload(image_path):
    return get_you_diagnosis_from_image(image_path)

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
                gpt_result = detect_disease_with_upload(image_path)
                diagnosis = f"🧠 YouChat Analisa Upload Gambar:<br>{gpt_result}"
        elif method == "camera":
            diagnosis, image_path = detect_disease_with_camera()

    return render_template("index.html", diagnosis=diagnosis, image_path=image_path)

if __name__ == "__main__":
    app.run(debug=True)
