import cv2
import mediapipe as mp
import time
import numpy as np
import os


# ============================================================
# MODEL PATH
# ============================================================

# Automatically find the model relative to this Python file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)

possible_paths = [
    os.path.join(CURRENT_DIR, "models", "face_landmarker.task"),
    os.path.join(PROJECT_DIR, "models", "face_landmarker.task"),
]

MODEL_PATH = None

for path in possible_paths:
    if os.path.exists(path):
        MODEL_PATH = path
        break

if MODEL_PATH is None:
    print("❌ face_landmarker.task not found.")
    print()
    print("Please make sure face_landmarker.task is inside either:")
    print("phase3/models/")
    print("OR")
    print("models/")
    exit()

print("Model found:", MODEL_PATH)


# ============================================================
# EYE LANDMARKS
# ============================================================

LEFT_EYE = [
    33,
    160,
    158,
    133,
    153,
    144
]

RIGHT_EYE = [
    362,
    385,
    387,
    263,
    373,
    380
]


# ============================================================
# EAR CALCULATION
# ============================================================

def calculate_ear(landmarks, eye_indices):

    points = []

    for index in eye_indices:

        landmark = landmarks[index]

        points.append(
            np.array([
                landmark.x,
                landmark.y
            ])
        )

    p1, p2, p3, p4, p5, p6 = points

    vertical_1 = np.linalg.norm(p2 - p6)
    vertical_2 = np.linalg.norm(p3 - p5)

    horizontal = np.linalg.norm(p1 - p4)

    ear = (
        vertical_1 + vertical_2
    ) / (2.0 * horizontal)

    return ear


# ============================================================
# MEDIAPIPE TASKS API
# ============================================================

BaseOptions = mp.tasks.BaseOptions
VisionRunningMode = mp.tasks.vision.RunningMode
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions


options = FaceLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path=MODEL_PATH
    ),
    running_mode=VisionRunningMode.VIDEO,
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5
)


landmarker = FaceLandmarker.create_from_options(options)


# ============================================================
# BLINK DETECTION STATE
# ============================================================

eyes_closed = False
closed_frames = 0
blink_count = 0

CLOSED_FRAME_THRESHOLD = 2
# Liveness state
liveness_verified = False
liveness_time = None

# ============================================================
# EAR THRESHOLDS
# ============================================================

# Based on your measured values:
#
# Eyes OPEN  ≈ 0.404
# Eyes CLOSED ≈ 0.022

EYE_CLOSED_THRESHOLD = 0.20
EYE_OPEN_THRESHOLD = 0.30


# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("❌ Could not open webcam.")
    exit()

print("Camera started.")
print("Press Q to quit.")


# MediaPipe requires increasing timestamps
timestamp_ms = 0


# ============================================================
# MAIN LOOP
# ============================================================

while True:
# ========================================================
# LIVENESS TIMEOUT
# ========================================================

    if liveness_verified and liveness_time is not None:

        if time.time() - liveness_time > 10:

            liveness_verified = False
            liveness_time = None

            blink_count = 0
            eyes_closed = False
            closed_frames = 0

            print("Liveness expired. Resetting.")
    ret, frame = cap.read()

    if not ret:

        print("❌ Could not read frame.")
        break


    # Mirror camera
    frame = cv2.flip(frame, 1)


    # Convert BGR → RGB
    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # Convert to MediaPipe Image
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )


    # Increasing timestamp
    timestamp_ms += 33


    # Detect face landmarks
    result = landmarker.detect_for_video(
        mp_image,
        timestamp_ms
    )


    # ========================================================
    # FACE DETECTED
    # ========================================================

    if result.face_landmarks:

        # First face
        landmarks = result.face_landmarks[0]


        # ----------------------------------------------------
        # Calculate EAR
        # ----------------------------------------------------

        left_ear = calculate_ear(
            landmarks,
            LEFT_EYE
        )

        right_ear = calculate_ear(
            landmarks,
            RIGHT_EYE
        )

        ear = (
            left_ear + right_ear
        ) / 2.0


        # ----------------------------------------------------
        # Blink Detection
        # ----------------------------------------------------

        if ear < EYE_CLOSED_THRESHOLD:

            closed_frames += 1

            if closed_frames >= CLOSED_FRAME_THRESHOLD:

                eyes_closed = True


        else:

            if eyes_closed and ear > EYE_OPEN_THRESHOLD:

                blink_count += 1

                print(
                    f"Blink detected: {blink_count}"
                )

                eyes_closed = False

                # ------------------------------------------
                # Liveness verification
                # ------------------------------------------

                if blink_count >= 2 and not liveness_verified:

                    liveness_verified = True
                    liveness_time = time.time()

                    print("✅ LIVENESS VERIFIED")

            closed_frames = 0


        # ----------------------------------------------------
        # Face detected text
        # ----------------------------------------------------

        cv2.putText(
            frame,
            "FACE LANDMARKS DETECTED",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )


        # ----------------------------------------------------
        # Left EAR
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Left EAR: {left_ear:.3f}",
            (20, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # ----------------------------------------------------
        # Right EAR
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Right EAR: {right_ear:.3f}",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # ----------------------------------------------------
        # Average EAR
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Average EAR: {ear:.3f}",
            (20, 155),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2
        )


        # ----------------------------------------------------
        # Blink Count
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Blinks: {blink_count}",
            (20, 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2
        )


        # ----------------------------------------------------
        # Number of landmarks
        # ----------------------------------------------------

        cv2.putText(
            frame,
            f"Landmarks: {len(landmarks)}",
            (20, 225),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # ----------------------------------------------------
        # Eye State
        # ----------------------------------------------------

        if ear < EYE_CLOSED_THRESHOLD:

            eye_state = "EYES CLOSED"

        elif ear > EYE_OPEN_THRESHOLD:

            eye_state = "EYES OPEN"

        else:

            eye_state = "UNCERTAIN"


        cv2.putText(
            frame,
            eye_state,
            (20, 260),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2
        )
        if liveness_verified:

            cv2.putText(
                frame,
                "LIVENESS VERIFIED",
                (20, 300),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        else:

            cv2.putText(
                frame,
                "LIVENESS: NOT VERIFIED",
                (20, 300),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
    
    # ========================================================
    # NO FACE
    # ========================================================

    else:

        cv2.putText(
            frame,
            "NO FACE",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )


        # Reset blink state if no face
        eyes_closed = False
        closed_frames = 0
        blink_count = 0
        liveness_verified = False
        liveness_time = None

    # ========================================================
    # SHOW CAMERA
    # ========================================================

    cv2.imshow(
        "Phase 3 - Liveness Detection",
        frame
    )


    # ========================================================
    # KEYBOARD
    # ========================================================

    key = cv2.waitKey(1) & 0xFF


    if key == ord("q"):

        break


    # R = reset blink counter
    if key == ord("r"):

        eyes_closed = False
        closed_frames = 0
        blink_count = 0
        liveness_verified = False
        liveness_time = None
        print("Blink counter reset.")


# ============================================================
# CLEANUP
# ============================================================

cap.release()

landmarker.close()

cv2.destroyAllWindows()