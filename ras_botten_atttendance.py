import requests
import time
import cv2
from picamera2 import Picamera2

COMMANDS_API = "https://smart-system-attendance-production-d4bd.up.railway.app/api/device/commands/pending"
DONE_API = "https://smart-system-attendance-production-d4bd.up.railway.app/api/device/command/done"
FLASK_AI = "http://192.168.1.6:5000/face-scan"
BACKEND_API = "https://smart-system-attendance-production-d4bd.up.railway.app/api/attendance/face"

last_command_id = None
SHOW_CAMERA = True

picam2 = Picamera2()

config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)

picam2.configure(config)


def capture_and_send():
    try:
        picam2.start()
        time.sleep(2)

        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        start_time = time.time()
        MAX_TIME = 30 if not face_valid else 10

        detected_frame = None
        face_valid = False

        while time.time() - start_time < MAX_TIME:

            frame = picam2.capture_array()
            h, w = frame.shape[:2]

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            if SHOW_CAMERA:
                cv2.rectangle(frame,
                              (int(w*0.25), int(h*0.2)),
                              (int(w*0.75), int(h*0.85)),
                              (0, 255, 0), 2)

                cv2.imshow("Camera", frame)
                cv2.waitKey(1)

            for (x, y, fw, fh) in faces:

                if fw < 120 or fh < 120:
                    continue

                cx = x + fw // 2
                cy = y + fh // 2

                if not (w*0.25 < cx < w*0.75 and h*0.2 < cy < h*0.85):
                    continue

                face_ratio = (fw * fh) / (w * h)

                if face_ratio < 0.08 or face_ratio > 0.40:
                    continue

                print("Good face detected")

                time.sleep(0.5)

                detected_frame = picam2.capture_array()
                face_valid = True
                break

            if face_valid:
                break

        if not face_valid:
            print("No proper face detected")
            return

        _, img_encoded = cv2.imencode('.jpg', detected_frame)
        files = {"image": ("face.jpg", img_encoded.tobytes(), "image/jpeg")}

        res = requests.post(FLASK_AI, files=files, timeout=30)
        data = res.json()

        print("FLASK RESPONSE:", data)

        if data.get("success"):
            face_vector = data.get("faceVector")

            backend_res = requests.post(
                BACKEND_API,
                json={"faceVector": face_vector},
                timeout=10
            )

            print("BACKEND RESPONSE:", backend_res.json())
        else:
            print("Face not recognized")

        time.sleep(2)

    except Exception as e:
        print("ERROR:", e)

    finally:
        try:
            picam2.stop()
        except:
            pass

        if SHOW_CAMERA:
            try:
                cv2.destroyAllWindows()
            except:
                pass


def listen_commands():
    global last_command_id

    while True:
        try:
            res = requests.get(COMMANDS_API, timeout=10)
            data = res.json()

            command = data.get("command")
            command_id = data.get("commandId")

            if command and command_id != last_command_id:
                print("New Command:", command)
                last_command_id = command_id

                if command == "open_camera":
                    capture_and_send()

                requests.post(DONE_API, json={"commandId": command_id})

        except Exception as e:
            print("Connection Error:", e)

        time.sleep(1)


if __name__ == "__main__":
    try:
        listen_commands()
    finally:
        picam2.close()