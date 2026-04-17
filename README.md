Here’s a **clean, professional, well-structured README.md** for your project 👇 (you can directly copy-paste into your repo)

---

# 📌 D-CAPTCHA System

### 🔐 Role-Based Online Exam Proctoring System

---

## 📖 Overview

D-CAPTCHA is an advanced AI-based online exam proctoring system designed to prevent cheating using **multi-modal verification techniques**. It integrates facial recognition, voice authentication, and real-time monitoring to ensure secure and reliable online assessments.

---

## 🚀 Features

* 👤 **Face Detection & Recognition**
* 🎙️ **Voice Authentication**
* 🧠 **AI-Based Behavior Monitoring**
* 🔒 **Anti-Cheating Mechanisms**
* 📊 **Real-Time Proctoring Dashboard**
* 🧩 **Challenge-Response CAPTCHA System**

---

## 🏗️ Tech Stack

### 🔹 Backend

* FastAPI
* Uvicorn
* Pydantic

### 🔹 Frontend

* Streamlit

### 🔹 Machine Learning & CV

* OpenCV
* MediaPipe
* Ultralytics (YOLO)
* NumPy

### 🔹 Utilities

* Requests
* Pillow
* SpeechRecognition
* PyAudio

---

## 📂 Project Structure

```
D-CAPTCHA/
│── backend/                     # FastAPI backend logic
│── pages/                       # Streamlit frontend pages

│── app.py                       # Main application entry point
│── camera_diagnostic.py         # Camera testing & debugging
│── clear_database.py            # Script to reset database
│── fix_mediapipeline.py         # Fix MediaPipe related issues
│── fix_yolo.py                  # YOLO model fixes
│── migrate_database.py          # Database migration script
│── migrate_add_face_column.py   # Adds face column to DB

│── alerts                       # SQLite database file
│── yolov8n.pt                   # YOLOv8 model file

│── CAMERA_FIX_GUIDE.md          # Camera troubleshooting guide
│── .DS_Store                    # System file (should be ignored)
```

---

## ⚙️ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Vishali-m05/D-Captcha.git
cd D-Captcha
```

---

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Mac/Linux**

```bash
source venv/bin/activate
```

---

### 3️⃣ Install Dependencies

For Backend
```bash
pip install fastapi==0.109.0
pip install "uvicorn[standard]"==0.27.0
pip install pydantic==2.5.0
pip install python-multipart==0.0.6
```
For Frontend
```bash
pip install streamlit==1.29.0
```

For Machine Learning & Computer Vision
```bash
pip install opencv-python==4.8.1.78
pip install mediapipe==0.10.8
pip install ultralytics==8.0.196
```


For Utilities
```bash
pip install requests==2.31.0
pip install pillow==10.1.0
pip install numpy==1.24.3
pip install SpeechRecognition==3.10.0
pip install PyAudio==0.2.13
```

---

## ▶️ Running the Application

### 🔹 Start Backend (FastAPI)

```bash
uvicorn main:app --reload
```

---

### 🔹 Start Frontend (Streamlit)

```bash
streamlit run app.py
```

---

## 🧪 System Requirements

* Python 3.9+
* Webcam & Microphone
* Internet Connection

---

## 🔐 Security Features

* Multi-layer authentication
* Real-time monitoring
* AI-based anomaly detection
* Deepfake prevention techniques

---

## 📌 Future Enhancements

* ☁️ Cloud deployment
* 📱 Mobile support
* 🤖 Advanced AI models
* 📈 Analytics dashboard

---

## 🤝 Contributing

Contributions are welcome! Feel free to fork this repo and submit pull requests.

---

## 📜 License

This project is for educational and research purposes.

---

## 👩‍💻 Author

**Vishali M**

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!


