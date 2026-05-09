from flask import Flask, request, jsonify
import requests
import easyocr
import re
import os
import time

app = Flask(__name__)

ONLINE_API = "https://smart-system-attendance-production-d4bd.up.railway.app/api/parking/enter/camera"

UPLOAD = "images"
os.makedirs(UPLOAD, exist_ok=True)

reader = easyocr.Reader(['en'], gpu=False)


def extract(img_path):
    res = reader.readtext(img_path)

    if not res:
        return "UNKNOWN", 0.0

    res = [r for r in res if r[2] > 0.4]
    if not res:
        return "UNKNOWN", 0.0

    best = max(res, key=lambda x: x[2])

    plate = re.sub(r'[^A-Z0-9]', '', best[1].upper())
    conf = float(best[2])

    return (plate if plate else "UNKNOWN"), conf


@app.route('/process_camera', methods=['POST'])
def process():
    try:
        file = request.files['image']

        path = os.path.join(UPLOAD, f"{int(time.time()*1000)}.jpg")
        file.save(path)

        plate, conf = extract(path)

        print("[AI] plate=", plate, "conf=", conf)

        try:
            os.remove(path)
        except:
            pass

        if plate == "UNKNOWN":
            return jsonify({
                "allowed": False,
                "action": "ignore",
                "message": "no_plate"
            }), 200

        if conf < 0.6:
            return jsonify({
                "allowed": False,
                "action": "ignore",
                "message": "low_confidence"
            }), 200

        try:
            res = requests.post(
                ONLINE_API,
                json={
                    "plateNumber": plate,
                    "confidence": conf
                },
                timeout=10
            )

            data = res.json()

            return jsonify({
                "allowed": data.get("allowed", False),
                "action": "open" if data.get("allowed") else "rfid_required",
                "message": data.get("message", "")
            }), 200

        except Exception as e:
            print("[ONLINE ERROR]", e)

            return jsonify({
                "allowed": False,
                "action": "ignore",
                "message": "error"
            }), 200

    except Exception as e:
        print("[SERVER ERROR]", e)

        return jsonify({
            "allowed": False,
            "action": "ignore",
            "message": "error"
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)