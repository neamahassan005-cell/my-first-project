import requests
import time
import cv2
import threading
from picamera2 import Picamera2
from razrc522 import RFID

FLASK_AI = "http://192.168.1.6:5000/face-scan"

CARD_API = "https://smart-system-attendance-production-d4bd.up.railway.app/api/attendance/card-verified"
QR_API = "https://smart-system-attendance-production-d4bd.up.railway.app/api/attendance/qr-verified"

rfid = RFID()

qr_data = None
last_card_time = 0


cam = Picamera2()
config = cam.create_preview_configuration(
    main={"format": "RGB888", "size": (640, 480)}
)
cam.configure(config)
cam.start()
time.sleep(1)


def qr_listener():
    global qr_data
    while True:
        data = input().strip()
        if data:
            qr_data = data


def read_rfid_non_block():
    rfid.set_antenna(True)

    start = time.time()

    while time.time() - start < 0.3:
        (error, _) = rfid.request()

        if not error:
            (error, uid) = rfid.anticoll()

            if not error:
                return "".join([str(i) for i in uid])

        time.sleep(0.05)

    return None


def capture_face():
    start = time.time()

    while time.time() - start < 10:
        frame = cam.capture_array()

        cv2.imshow("Camera", frame)
        cv2.waitKey(1)

        _, img = cv2.imencode('.jpg', frame)

        try:
            res = requests.post(
                FLASK_AI,
                files={"image": img.tobytes()},
                timeout=10
            )

            data = res.json()

            if data.get("success"):
                return data.get("faceVector")

        except:
            pass

    return None


def send_card(card, face):
    try:
        return requests.post(
            CARD_API,
            json={
                "cardNumber": card,
                "faceId": ",".join(map(str, face))
            },
            timeout=10
        ).json()
    except:
        return None


def send_qr(qr, face):
    try:
        return requests.post(
            QR_API,
            json={
                "qr_code": qr,
                "faceId": ",".join(map(str, face))
            },
            timeout=10
        ).json()
    except:
        return None


def main_loop():
    global qr_data, last_card_time

    while True:

        card = read_rfid_non_block()
        if card and time.time() - last_card_time > 3:
            last_card_time = time.time()

            print("RFID DETECTED:", card)

            face = capture_face()
            if face:
                result = send_card(card, face)
                print("CARD RESULT:", result)

            time.sleep(2)

        if qr_data:
            qr = qr_data
            qr_data = None

            print("QR DETECTED:", qr)

            face = capture_face()
            if face:
                result = send_qr(qr, face)
                print("QR RESULT:", result)

            time.sleep(2)


if __name__ == "__main__":
    threading.Thread(target=qr_listener, daemon=True).start()

    try:
        main_loop()
    finally:
        cam.stop()
        cv2.destroyAllWindows()