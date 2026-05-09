from flask import Flask, request, jsonify
import face_recognition
import requests

app = Flask(__name__)

BACKEND_API_URL = "https://smart-system-attendance-production-d4bd.up.railway.app/api/face/assign"

@app.route("/register", methods=["POST"])
def register_face():
    try:
        if "image" not in request.files:
            return jsonify({"success": False, "message": "No image"}), 400

        emp_id = request.form.get("employee_id")
        file = request.files["image"]

        image = face_recognition.load_image_file(file)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) == 0:
            return jsonify({"success": False, "message": "No face detected"}), 400

        face_vector = encodings[0].tolist()

        payload = {
            "employeeNumber": emp_id,
            "faceId": face_vector
        }

        res = requests.post(BACKEND_API_URL, json=payload, timeout=15)

        print("Backend status:", res.status_code)
        print("Backend response:", res.text)

        return jsonify({
            "success": True,
            "message": "Face registered and sent to backend",
            "backend_status": res.status_code,
            "backend_response": res.text
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)