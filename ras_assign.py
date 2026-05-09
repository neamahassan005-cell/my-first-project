import cv2
import requests
from picamera2 import Picamera2

AI_SERVER_URL = "http://192.168.8.100:5000/register"

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def capture_and_register():
    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
    picam2.configure(config)

    emp_id = input("Enter Employee ID: ").strip()
    emp_name = input("Enter Employee Name: ").strip()

    picam2.start()

    while True:
        frame = picam2.capture_array()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        display_frame = frame.copy()
        face_ready = False

        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            if w > 150 and h > 150:
                face_ready = True
                cv2.putText(
                    display_frame,
                    "Face Ready - Press S",
                    (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

        cv2.imshow("Register", display_frame)

        key = cv2.waitKey(1)

        if key == ord('s'):
            if not face_ready:
                print("Face not clear")
                continue

            _, img_encoded = cv2.imencode('.jpg', frame)

            files = {'image': ('face.jpg', img_encoded.tobytes(), 'image/jpeg')}
            data = {
                'employee_id': emp_id,
                'employee_name': emp_name
            }

            try:
                res = requests.post(AI_SERVER_URL, files=files, data=data)
                print(res.json())
            except Exception as e:
                print(e)

            break

        elif key == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    capture_and_register()