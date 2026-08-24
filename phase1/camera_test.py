import cv2
import mediapipe as mp
import os
import time


# --------------------------------------------------
# GET THE PROJECT ROOT FOLDER
# --------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# --------------------------------------------------
# MODEL PATH
# --------------------------------------------------

MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    "models",
    "face_detector.task.tflite"
)


# --------------------------------------------------
# CHECK WHETHER MODEL EXISTS
# --------------------------------------------------

if not os.path.exists(MODEL_PATH):
    print("ERROR: Model file not found.")
    print("Expected location:")
    print(MODEL_PATH)
    exit()

print("Model found:")
print(MODEL_PATH)


# --------------------------------------------------
# MEDIAPIPE FACE DETECTOR SETUP
# --------------------------------------------------

BaseOptions = mp.tasks.BaseOptions

FaceDetector = mp.tasks.vision.FaceDetector
FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
RunningMode = mp.tasks.vision.RunningMode


options = FaceDetectorOptions(
    base_options=BaseOptions(
        model_asset_path=MODEL_PATH
    ),
    running_mode=RunningMode.VIDEO,
    min_detection_confidence=0.5
)


# --------------------------------------------------
# OPEN WEBCAM
# --------------------------------------------------

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open webcam.")
    exit()


print("Camera opened.")
print("Face detection started. Press Q to exit.")


# --------------------------------------------------
# CREATE FACE DETECTOR
# --------------------------------------------------

with FaceDetector.create_from_options(options) as detector:
    last_timestamp_ms = -1
    while True:

        # Read frame from webcam
        success, frame = camera.read()

        if not success:
            print("ERROR: Could not read frame.")
            break


        # ------------------------------------------
        # CONVERT BGR TO RGB
        # ------------------------------------------

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )


        # ------------------------------------------
        # CREATE MEDIAPIPE IMAGE
        # ------------------------------------------

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )


        # ------------------------------------------
        # CREATE TIMESTAMP
        # ------------------------------------------

        
        timestamp_ms = int(time.monotonic() * 1000)

        # Ensure timestamps are always strictly increasing
        if timestamp_ms <= last_timestamp_ms:
            timestamp_ms = last_timestamp_ms + 1

        last_timestamp_ms = timestamp_ms


        # ------------------------------------------
        # DETECT FACES
        # ------------------------------------------

        detection_result = detector.detect_for_video(
            mp_image,
            timestamp_ms
        )


        # ------------------------------------------
        # COUNT FACES
        # ------------------------------------------

        face_count = len(
            detection_result.detections
        )


        # ------------------------------------------
        # DRAW BOXES AROUND FACES
        # ------------------------------------------

        for detection in detection_result.detections:

            bounding_box = detection.bounding_box

            x = bounding_box.origin_x
            y = bounding_box.origin_y

            width = bounding_box.width
            height = bounding_box.height


            # Prevent negative coordinates
            x = max(0, x)
            y = max(0, y)


            # Draw bounding box
            cv2.rectangle(
                frame,
                (x, y),
                (x + width, y + height),
                (0, 255, 0),
                2
            )


            # Display label
            cv2.putText(
                frame,
                "Face Detected",
                (x, max(y - 10, 30)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )


        # ------------------------------------------
        # DISPLAY NUMBER OF FACES
        # ------------------------------------------

        cv2.putText(
            frame,
            f"Faces: {face_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


        # ------------------------------------------
        # SHOW CAMERA
        # ------------------------------------------

        cv2.imshow(
            "AI Smart Door Lock - Face Detection",
            frame
        )


        # ------------------------------------------
        # PRESS Q TO EXIT
        # ------------------------------------------

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


# --------------------------------------------------
# CLEANUP
# --------------------------------------------------

camera.release()
cv2.destroyAllWindows()

print("Camera closed.")