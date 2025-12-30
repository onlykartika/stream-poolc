import os
import time
import json
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
GITHUB_REPO = "onlykartika/stream-poolc"
GITHUB_IMAGES_DIR = "images"
GITHUB_INDEX_FILE = "images.json"

GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "User-Agent": "ESP32-CAM-Image-Server",
    "Accept": "application/vnd.github.v3+json"
}

# ================= HELPER =================
def get_images_index():
    """Ambil images.json dari GitHub (kalau ada)"""
    url = f"{GITHUB_API_BASE}/{GITHUB_INDEX_FILE}"
    res = requests.get(url, headers=GITHUB_HEADERS, timeout=10)

    if res.status_code == 200:
        content = base64.b64decode(res.json()["content"]).decode("utf-8")
        return json.loads(content), res.json()["sha"]

    return {}, None


def save_images_index(data, sha=None):
    """Upload images.json ke GitHub"""
    content_b64 = base64.b64encode(
        json.dumps(data, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "Update images.json",
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha

    url = f"{GITHUB_API_BASE}/{GITHUB_INDEX_FILE}"
    return requests.put(url, headers=GITHUB_HEADERS, json=payload, timeout=15)

# ================= HEALTH CHECK =================
@app.route("/", methods=["GET"])
def health():
    return "ESP32-CAM Image Upload Server + JSON Index (stream-poolc)"

# ================= IMAGE UPLOAD =================
@app.route("/upload", methods=["POST"])
def upload():
    if not request.data:
        return jsonify({"error": "no image received"}), 400

    esp_id = request.headers.get("X-ESP-ID", "unknown")
    timestamp = int(time.time())
    filename = f"{esp_id}_{timestamp}.jpg"

    print(f"[INFO] Image from {esp_id}, size={len(request.data)} bytes")

    # ===== UPLOAD IMAGE =====
    image_b64 = base64.b64encode(request.data).decode("utf-8")
    image_path = f"{GITHUB_IMAGES_DIR}/{esp_id}/{filename}"
    image_url = f"{GITHUB_API_BASE}/{image_path}"

    img_res = requests.put(
        image_url,
        headers=GITHUB_HEADERS,
        json={
            "message": f"Upload image from {esp_id}",
            "content": image_b64
        },
        timeout=20
    )

    if img_res.status_code not in (200, 201):
        return jsonify({
            "error": "image upload failed",
            "detail": img_res.text
        }), 500

    print(f"[OK] Image uploaded: {image_path}")

    # ===== UPDATE images.json =====
    try:
        index_data, sha = get_images_index()

        if esp_id not in index_data:
            index_data[esp_id] = []

        index_data[esp_id].append({
            "filename": filename,
            "path": image_path,
            "timestamp": timestamp
        })

        save_res = save_images_index(index_data, sha)

        if save_res.status_code in (200, 201):
            print("[OK] images.json updated")
        else:
            print("[WARN] Failed updating images.json")

    except Exception as e:
        print(f"[WARN] images.json error: {e}")

    return jsonify({
        "status": "ok",
        "esp_id": esp_id,
        "filename": filename,
        "image_path": image_path,
        "repo": GITHUB_REPO
    }), 200

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
