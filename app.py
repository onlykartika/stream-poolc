import os
import time
import base64
import requests
from flask import Flask, request, jsonify

# ================= FLASK APP =================
app = Flask(__name__)

# ================= ENV =================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is required")

# ================= GITHUB CONFIG =================
# 🔴 REPO BARU
GITHUB_REPO = "onlykartika/stream-poolc"

# Folder penyimpanan gambar di repo
GITHUB_IMAGES_DIR = "images"

GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "User-Agent": "ESP32-CAM-Image-Server",
    "Accept": "application/vnd.github.v3+json"
}

# ================= HEALTH CHECK =================
@app.route("/", methods=["GET"])
def health():
    return "ESP32-CAM Image Upload Server (stream-poolc) is running"

# ================= IMAGE UPLOAD =================
@app.route("/upload", methods=["POST"])
def upload():
    if not request.data:
        return jsonify({"error": "no image received"}), 400

    # Ambil ESP ID dari header
    esp_id = request.headers.get("X-ESP-ID", "unknown")

    timestamp = int(time.time())
    filename = f"{esp_id}_{timestamp}.jpg"

    print(f"[INFO] Image received from {esp_id}, size={len(request.data)} bytes")

    # Encode ke base64
    image_b64 = base64.b64encode(request.data).decode("utf-8")

    # Path di GitHub: images/<esp_id>/<filename>
    github_path = f"{GITHUB_IMAGES_DIR}/{esp_id}/{filename}"
    put_url = f"{GITHUB_API_BASE}/{github_path}"

    # Upload ke GitHub
    response = requests.put(
        put_url,
        headers=GITHUB_HEADERS,
        json={
            "message": f"Upload image from {esp_id}",
            "content": image_b64
        },
        timeout=20
    )

    if response.status_code not in (200, 201):
        return jsonify({
            "error": "github upload failed",
            "status_code": response.status_code,
            "detail": response.text
        }), 500

    print(f"[OK] Image uploaded to {github_path}")

    return jsonify({
        "status": "ok",
        "esp_id": esp_id,
        "filename": filename,
        "github_path": github_path,
        "repo": GITHUB_REPO
    }), 200


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
