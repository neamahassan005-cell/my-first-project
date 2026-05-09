from flask import Flask, request, jsonify
import face_recognition

app = Flask(__name__)

@app.route("/face-scan", methods=["POST"])
def face_scan():
    try:
        if "image" not in request.files:
            return jsonify({"success": False, "message": "No image"}), 400

        file = request.files["image"]

        image = face_recognition.load_image_file(file)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) == 0:
            return jsonify({"success": False, "message": "No face detected"}), 400

        face_vector = encodings[0].tolist()

        if not isinstance(face_vector, list):
            return jsonify({"success": False, "message": "Encoding error"}), 500

        return jsonify({
            "success": True,
            "faceVector": face_vector
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)