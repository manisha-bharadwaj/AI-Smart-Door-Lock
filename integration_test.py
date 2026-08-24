import cv2
import face_recognition
import mediapipe as mp
import pickle
import os
import time
from collections import deque
import numpy as np


# ============================================================
# FILE PATHS
# ============================================================

ENCODINGS_FILE = "phase2/encodings.pkl"
MODEL_PATH = "models/face_landmarker.task"


# ============================================================
# CHECK FILES
# ============================================================

if not os.path.exists(ENCODINGS_FILE):
    print("❌ encodings.pkl not found.")
    print("Run: python phase2/register_faces.py")
    exit()

if not os.path.exists(MODEL_PATH):
    print("❌ face_landmarker.task not found.")
    print("Place it inside the models folder.")
    exit()


# ============================================================
# LOAD FACE DATABASE
# ============================================================

with open(ENCODINGS_FILE, "rb") as file:
    data = pickle.load(file)

known_encodings = data["encodings"]
known_names = data["names"]

print("Registered users:")

for name in known_names:
    print(f" - {name}")


# ============================================================
# MEDIAPIPE FACE LANDMARKER
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
    num_faces=2,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

landmarker = FaceLandmarker.create_from_options(options)


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
# EAR FUNCTION
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

    if horizontal == 0:
        return 0

    return (
        vertical_1 + vertical_2
    ) / (2.0 * horizontal)


# ============================================================
# LIVENESS SETTINGS
# ============================================================

EYE_CLOSED_THRESHOLD = 0.20
EYE_OPEN_THRESHOLD = 0.30

CLOSED_FRAME_THRESHOLD = 2

blink_count = 0
eyes_closed = False
closed_frames = 0

liveness_verified = False
liveness_time = None


# ============================================================
# RECOGNITION SETTINGS
# ============================================================

RECOGNITION_INTERVAL = 5

frame_counter = 0

recognition_history = deque(maxlen=6)

STABLE_MATCH_COUNT = 4

stable_name = "Unknown"

last_authorized_time = 0

IDENTITY_GRACE_PERIOD = 2.0


# ============================================================
# MULTIPLE FACE SECURITY STATE
# ============================================================

multiple_faces_detected = False


# ============================================================
# RESET LIVENESS
# ============================================================

def reset_liveness():

    global blink_count
    global eyes_closed
    global closed_frames
    global liveness_verified
    global liveness_time

    blink_count = 0
    eyes_closed = False
    closed_frames = 0

    liveness_verified = False
    liveness_time = None


# ============================================================
# RESET IDENTITY
# ============================================================

def reset_identity():

    global stable_name
    global last_authorized_time

    stable_name = "Unknown"
    last_authorized_time = 0

    recognition_history.clear()


# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("❌ Could not open webcam.")

    landmarker.close()

    exit()


# ============================================================
# CAMERA OPTIMIZATION
# ============================================================

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)


print()
print("======================================")
print("AI SMART DOOR LOCK")
print("INTEGRATED PHASE 1 + 2 + 3")
print("======================================")
print("Press Q to quit.")
print("Press R to reset.")
print("======================================")
print()


# ============================================================
# MEDIAPIPE TIMESTAMPS
# ============================================================

timestamp_ms = 0


# ============================================================
# FULLSCREEN WINDOW
# ============================================================

WINDOW_NAME = "AI Smart Door Lock"

cv2.namedWindow(
    WINDOW_NAME,
    cv2.WINDOW_NORMAL
)

cv2.setWindowProperty(
    WINDOW_NAME,
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    ret, frame = cap.read()

    if not ret:

        print("❌ Camera frame error.")
        break


    # --------------------------------------------------------
    # Mirror camera
    # --------------------------------------------------------

    frame = cv2.flip(frame, 1)

    frame_counter += 1

    # Reset EAR every frame
    ear = None


    # ========================================================
    # PHASE 3 — MEDIAPIPE
    # ========================================================

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )

    timestamp_ms += 33

    result = landmarker.detect_for_video(
        mp_image,
        timestamp_ms
    )


    # ========================================================
    # FACE COUNT SECURITY CHECK
    # ========================================================

    face_count = len(result.face_landmarks)


    # ========================================================
    # NO FACE
    # ========================================================

    if face_count == 0:

        multiple_faces_detected = False

        reset_identity()
        reset_liveness()

        status = "WAITING"
        liveness_status = "NOT REQUIRED"

        cv2.putText(
            frame,
            "NO FACE",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2
        )

        cv2.putText(
            frame,
            "Waiting for person...",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


    # ========================================================
    # MULTIPLE FACES
    # ========================================================

    elif face_count > 1:

        multiple_faces_detected = True

        reset_identity()
        reset_liveness()

        status = "UNAUTHORIZED"
        liveness_status = "NOT ALLOWED"

        cv2.putText(
            frame,
            "MULTIPLE FACES - ACCESS DENIED",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

        cv2.putText(
            frame,
            f"Faces detected: {face_count}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )


    # ========================================================
    # EXACTLY ONE FACE
    # ========================================================

    else:

        multiple_faces_detected = False

        landmarks = result.face_landmarks[0]


        # ====================================================
        # PHASE 2 — FACE RECOGNITION
        # ONLY EVERY FEW FRAMES
        # ====================================================

        if frame_counter % RECOGNITION_INTERVAL == 0:

            small_frame = cv2.resize(
                frame,
                (0, 0),
                fx=0.25,
                fy=0.25
            )

            rgb_small = cv2.cvtColor(
                small_frame,
                cv2.COLOR_BGR2RGB
            )

            face_locations = face_recognition.face_locations(
                rgb_small,
                model="hog"
            )


            if len(face_locations) == 1:

                face_encodings = face_recognition.face_encodings(
                    rgb_small,
                    face_locations
                )

                current_name = "Unknown"


                if len(face_encodings) > 0:

                    face_encoding = face_encodings[0]

                    matches = face_recognition.compare_faces(
                        known_encodings,
                        face_encoding,
                        tolerance=0.5
                    )

                    face_distances = face_recognition.face_distance(
                        known_encodings,
                        face_encoding
                    )


                    if len(face_distances) > 0:

                        best_match_index = face_distances.argmin()

                        if matches[best_match_index]:

                            current_name = (
                                known_names[
                                    best_match_index
                                ]
                            )


                # --------------------------------------------
                # Add recognition result
                # --------------------------------------------

                recognition_history.append(
                    current_name
                )


                # --------------------------------------------
                # Count recognition results
                # --------------------------------------------

                name_counts = {}

                for name in recognition_history:

                    name_counts[name] = (
                        name_counts.get(name, 0) + 1
                    )


                best_name = max(
                    name_counts,
                    key=name_counts.get
                )

                best_count = name_counts[best_name]


                # --------------------------------------------
                # Stable AUTHORIZED identity
                # --------------------------------------------

                if best_name != "Unknown":

                    if best_count >= STABLE_MATCH_COUNT:

                        stable_name = best_name

                        last_authorized_time = time.time()


                # --------------------------------------------
                # Stable UNKNOWN
                # --------------------------------------------

                elif best_count >= STABLE_MATCH_COUNT:

                    if (
                        time.time()
                        - last_authorized_time
                        > IDENTITY_GRACE_PERIOD
                    ):

                        stable_name = "Unknown"


        # ====================================================
        # IDENTITY DECISION
        # ====================================================

        if stable_name == "Unknown":

            reset_liveness()

            status = "UNAUTHORIZED"
            liveness_status = "NOT REQUIRED"


        else:

            status = "AUTHORIZED"


            # =================================================
            # PHASE 3 — LIVENESS
            # =================================================

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


            # -----------------------------------------------
            # BLINK STATE MACHINE
            # -----------------------------------------------

            if ear < EYE_CLOSED_THRESHOLD:

                closed_frames += 1

                if (
                    closed_frames
                    >= CLOSED_FRAME_THRESHOLD
                ):

                    eyes_closed = True


            else:

                if (
                    eyes_closed
                    and ear > EYE_OPEN_THRESHOLD
                ):

                    blink_count += 1

                    print(
                        f"Blink detected: "
                        f"{blink_count}"
                    )

                    eyes_closed = False


                    # ----------------------------------------
                    # TWO BLINKS = LIVE
                    # ----------------------------------------

                    if blink_count >= 2:

                        liveness_verified = True

                        liveness_time = time.time()

                        print(
                            "✅ LIVENESS VERIFIED"
                        )


                closed_frames = 0


            # -----------------------------------------------
            # LIVENESS TIMEOUT
            # -----------------------------------------------

            if (
                liveness_verified
                and liveness_time is not None
            ):

                if (
                    time.time()
                    - liveness_time
                    > 10
                ):

                    reset_liveness()

                    print(
                        "Liveness expired."
                    )


            # -----------------------------------------------
            # LIVENESS DISPLAY
            # -----------------------------------------------

            if liveness_verified:

                liveness_status = "VERIFIED"

            else:

                liveness_status = (
                    f"BLINKS {blink_count}/2"
                )


        # ====================================================
        # DRAW FACE BOX
        # ====================================================

        xs = [
            landmark.x
            for landmark in landmarks
        ]

        ys = [
            landmark.y
            for landmark in landmarks
        ]

        h, w, _ = frame.shape

        left = max(
            0,
            int(min(xs) * w) - 20
        )

        right = min(
            w,
            int(max(xs) * w) + 20
        )

        top = max(
            0,
            int(min(ys) * h) - 20
        )

        bottom = min(
            h,
            int(max(ys) * h) + 20
        )


        # ====================================================
        # COLORS
        # ====================================================

        if status == "AUTHORIZED":

            box_color = (0, 255, 0)

        else:

            box_color = (0, 0, 255)


        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            box_color,
            2
        )


        # ====================================================
        # INFORMATION ON CAMERA
        # ====================================================

        cv2.putText(
            frame,
            f"Identity: {stable_name}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            box_color,
            2
        )

        cv2.putText(
            frame,
            f"Status: {status}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            box_color,
            2
        )

        cv2.putText(
            frame,
            f"Liveness: {liveness_status}",
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (
                (0, 255, 0)
                if liveness_verified
                else (0, 255, 255)
            ),
            2
        )

        cv2.putText(
            frame,
            f"Blinks: {blink_count}/2",
            (20, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2
        )


        if ear is not None:

            cv2.putText(
                frame,
                f"EAR: {ear:.3f}",
                (20, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )


    # ========================================================
    # FINAL SECURITY CONDITION
    # ========================================================

    access_ready = (
        stable_name != "Unknown"
        and liveness_verified
        and not multiple_faces_detected
    )


    # ========================================================
    # DISPLAY FINAL ACCESS STATE ON CAMERA
    # ========================================================

    if multiple_faces_detected:

        cv2.putText(
            frame,
            "ACCESS: DENIED",
            (20, 220),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

    elif access_ready:

        cv2.putText(
            frame,
            "ACCESS: GRANTED",
            (20, 220),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    else:

        cv2.putText(
            frame,
            "ACCESS: NOT READY",
            (20, 220),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )


    # ========================================================
    # FULLSCREEN SIMPLE DOOR DISPLAY
    # ========================================================

    # Full HD canvas
    screen_width = 1920
    screen_height = 1080

    door_display = np.zeros(
        (screen_height, screen_width, 3),
        dtype=np.uint8
    )


    # ========================================================
    # TITLE
    # ========================================================

    title = "AI SMART DOOR LOCK"

    title_size = cv2.getTextSize(
        title,
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        3
    )[0]

    title_x = (
        screen_width - title_size[0]
    ) // 2

    cv2.putText(
        door_display,
        title,
        (title_x, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (255, 255, 255),
        3
    )


    subtitle = "PHASE 1 + 2 + 3 INTEGRATED"

    subtitle_size = cv2.getTextSize(
        subtitle,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        2
    )[0]

    subtitle_x = (
        screen_width - subtitle_size[0]
    ) // 2

    cv2.putText(
        door_display,
        subtitle,
        (subtitle_x, 95),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (170, 170, 170),
        2
    )


    # ========================================================
    # CAMERA SIZE
    # ========================================================

    camera_width = 1280
    camera_height = 720

    camera_view = cv2.resize(
        frame,
        (camera_width, camera_height)
    )


    # ========================================================
    # CAMERA POSITION
    # ========================================================

    camera_x = (
        screen_width - camera_width
    ) // 2

    camera_y = 130


    # ========================================================
    # PLACE CAMERA INSIDE DOOR
    # ========================================================

    door_display[
        camera_y:camera_y + camera_height,
        camera_x:camera_x + camera_width
    ] = camera_view


    # ========================================================
    # SIMPLE DOOR FRAME
    # ========================================================

    # Outer door frame
    cv2.rectangle(
        door_display,
        (
            camera_x - 20,
            camera_y - 20
        ),
        (
            camera_x + camera_width + 20,
            camera_y + camera_height + 20
        ),
        (130, 130, 130),
        14
    )

    # Inner door frame
    cv2.rectangle(
        door_display,
        (
            camera_x - 7,
            camera_y - 7
        ),
        (
            camera_x + camera_width + 7,
            camera_y + camera_height + 7
        ),
        (60, 60, 60),
        5
    )


    # ========================================================
    # DOOR HANDLE
    # ========================================================

    handle_x = (
        camera_x
        + camera_width
        - 40
    )

    handle_y = (
        camera_y
        + camera_height // 2
    )

    cv2.circle(
        door_display,
        (handle_x, handle_y),
        16,
        (190, 190, 190),
        -1
    )

    cv2.circle(
        door_display,
        (handle_x, handle_y),
        8,
        (60, 60, 60),
        -1
    )


    # ========================================================
    # BOTTOM STATUS AREA
    # ========================================================

    status_y = 920


    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------

    cv2.putText(
        door_display,
        f"Identity: {stable_name}",
        (camera_x, status_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (255, 255, 255),
        2
    )


    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if stable_name == "Unknown":

        bottom_status_color = (
            0,
            0,
            255
        )

    else:

        bottom_status_color = (
            0,
            255,
            0
        )

    cv2.putText(
        door_display,
        f"Status: {status}",
        (camera_x, status_y + 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        bottom_status_color,
        2
    )


    # --------------------------------------------------------
    # LIVENESS
    # --------------------------------------------------------

    if liveness_verified:

        liveness_color = (
            0,
            255,
            0
        )

    else:

        liveness_color = (
            0,
            255,
            255
        )

    cv2.putText(
        door_display,
        f"Liveness: {liveness_status}",
        (camera_x, status_y + 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        liveness_color,
        2
    )


    # ========================================================
    # ACCESS STATUS
    # ========================================================

    if multiple_faces_detected:

        access_text = "ACCESS: DENIED"

        access_color = (
            0,
            0,
            255
        )

    elif access_ready:

        access_text = "ACCESS: GRANTED"

        access_color = (
            0,
            255,
            0
        )

    else:

        access_text = "ACCESS: NOT READY"

        access_color = (
            0,
            255,
            255
        )


    access_size = cv2.getTextSize(
        access_text,
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        3
    )[0]

    access_x = (
        camera_x
        + camera_width
        - access_size[0]
    )


    cv2.putText(
        door_display,
        access_text,
        (access_x, status_y + 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        access_color,
        3
    )


    # ========================================================
    # KEYBOARD HELP
    # ========================================================

    controls = "Q - Quit    |    R - Reset"

    controls_size = cv2.getTextSize(
        controls,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        1
    )[0]

    controls_x = (
        screen_width - controls_size[0]
    ) // 2

    cv2.putText(
        door_display,
        controls,
        (controls_x, 1060),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (130, 130, 130),
        1
    )


    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        WINDOW_NAME,
        door_display
    )


    # ========================================================
    # KEYBOARD
    # ========================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break

    if key == ord("r"):

        reset_identity()
        reset_liveness()

        multiple_faces_detected = False

        print("System reset.")


# ============================================================
# CLEANUP
# ============================================================

cap.release()

landmarker.close()

cv2.destroyAllWindows()