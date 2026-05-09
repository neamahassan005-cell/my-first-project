import requests
import time
import lgpio
from picamera2 import Picamera2
import cv2
from razrc522 import RFID

LAPTOP_URL = "http://192.168.8.152:5000/process_camera"
RFID_API   = "https://smart-system-attendance-production-d4bd.up.railway.app/api/parking/enter/rfid"

h = lgpio.gpiochip_open(0)
SERVO_PIN = 13
lgpio.gpio_claim_output(h, SERVO_PIN)

def angle_to_pulse(angle):
    return int(500 + (angle / 180.0) * 2000)

def open_gate():
    print("ðŸ”¥ SERVO START")

    lgpio.tx_servo(h, SERVO_PIN, 1500)
    time.sleep(3)

    lgpio.tx_servo(h, SERVO_PIN, 500)
    time.sleep(1)

    lgpio.tx_servo(h, SERVO_PIN, 0)

    print("ðŸ”¥ SERVO DONE")

rfid = RFID()

def read_rfid(timeout=10):
    print("[RFID] Place card...")

    start = time.time()
    rfid.set_antenna(True)

    try:
        while time.time() - start < timeout:

            (error, _) = rfid.request()

            if not error:
                (error, uid) = rfid.anticoll()

                if not error:
                    card = "".join([str(i) for i in uid])

                    print("âœ… Card Detected!")
                    print("UID:", card)

                    rfid.stop_crypto()
                    return card

            time.sleep(0.3)

    except Exception as e:
        print("[RFID ERROR]", e)

    print("[RFID] Timeout")
    return None


def send_rfid(card):
    try:
        res = requests.post(RFID_API, json={"cardNumber": card}, timeout=10)
        data = res.json()
        return data.get("allowed", False)
    except Exception as e:
        print("[RFID SERVER ERROR]", e)
        return False

class System:
    def __init__(self):
        self.cam = Picamera2()
        self.cam.configure(self.cam.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        ))
        self.cam.start()

        time.sleep(2)

        self.mode = "camera"
        self.last_request = 0

        print("[SYSTEM] READY")

    def send_to_ai(self, frame):
        try:
            _, img = cv2.imencode('.jpg', frame)

            res = requests.post(
                LAPTOP_URL,
                files={'image': img.tobytes()},
                timeout=10
            )

            if res.status_code == 200:
                return res.json()

        except Exception as e:
            print("[AI ERROR]", e)

        return {"allowed": False, "message": "ERROR"}

    def handle_camera(self, frame):

        if time.time() - self.last_request < 2:
            return

        result = self.send_to_ai(frame)

        allowed = result.get("allowed", False)
        message = result.get("message", "").lower()

        print("[CAMERA]", result)

        if allowed:
            print("ðŸ”¥ OPEN FROM CAMERA")
            open_gate()
            return

        if "not registered" in message:
            print("[SWITCH] CAMERA â†’ RFID")
            self.mode = "rfid"

        self.last_request = time.time()

    def handle_rfid(self):

        print("[RFID MODE] Waiting card...")

       
        self.cam.stop()

        card = read_rfid(timeout=10)

        if card:
            if send_rfid(card):
                print("[ACCESS] RFID OK")
                print("ðŸ”¥ OPEN FROM RFID")

                open_gate()
                time.sleep(2)

            else:
                print("[DENIED] RFID rejected")
        else:
            print("[NO CARD]")

      
        self.cam.start()

        print("[SWITCH] RFID â†’ CAMERA")
        self.mode = "camera"

    
    def start(self):

        while True:
            frame = self.cam.capture_array()
            cv2.imshow("CAM", frame)

            if self.mode == "camera":
                self.handle_camera(frame)

            elif self.mode == "rfid":
                self.handle_rfid()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()

        try:
            lgpio.gpiochip_close(h)
        except:
            pass


if __name__ == "__main__":
    System().start()
