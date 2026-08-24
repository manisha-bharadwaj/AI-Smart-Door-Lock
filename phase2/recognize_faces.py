import cv2
import face_recognition
import pickle
import os
from collections import Counter

ENCODINGS_FILE = "phase2/encodings.pkl"

# Load registered face encodings
if not os.path.exists(ENCODINGS_FILE):
    print("❌ encodings.pkl not found.")
    print("Please run register_faces.py first.")
    exit()

with open(ENCODINGS_FILE, "rb") as file:
    data = pickle.load(file)

known_encodings = data["encodings"]
known_names = data["names"]

print("Registered users:")
for name in known_names:
    print(f" - {name}")

print("\nStarting camera...")
print("Press Q to quit.")

recognition_history = []

HISTORY_SIZE = 10
# Open webcam
video_capture = cv2.VideoCapture(0)

if not video_capture.isOpened():
    print("❌ Could not open webcam.")
    exit()

while True:

    ret, frame = video_capture.read()

    if not ret:
        print("❌ Failed to read camera frame.")
        break

    # Resize frame for faster processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

    # Convert BGR → RGB
    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Find faces
    face_locations = face_recognition.face_locations(rgb_frame)

    # Generate encodings
    face_encodings = face_recognition.face_encodings(
        rgb_frame,
        face_locations
    )

    for face_location, face_encoding in zip(
        face_locations,
        face_encodings
    ):

        # Compare with registered faces
        matches = face_recognition.compare_faces(
            known_encodings,
            face_encoding,
            tolerance=0.5
        )

        name = "Unknown"

        # Calculate face distances
        face_distances = face_recognition.face_distance(
            known_encodings,
            face_encoding
        )

        if len(face_distances) > 0:

            best_match_index = face_distances.argmin()

            if matches[best_match_index]:
                name = known_names[best_match_index]

        # Add current recognition result to history
        recognition_history.append(name)

        # Keep only the most recent results
        if len(recognition_history) > HISTORY_SIZE:
            recognition_history.pop(0)

        # Use majority vote
        if recognition_history:
            most_common_name, count = Counter(
                recognition_history
            ).most_common(1)[0]

            if count >= 6:
                stable_name = most_common_name
            else:
                stable_name = "Checking..."

        else:
            stable_name = "Checking..."

        # Scale face coordinates back to original frame
        top, right, bottom, left = face_location

        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Choose status
        if stable_name == "Unknown":
            status = "UNAUTHORIZED"
        elif stable_name == "Checking...":
            status = "VERIFYING"
        else:
            status = "AUTHORIZED"

        # Draw face rectangle
        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            (0, 255, 0) if name != "Unknown" else (0, 0, 255),
            2
        )

        # Draw name
        cv2.putText(
            frame,
            f"Name: {stable_name}",
            (left, top - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        # Draw status
        cv2.putText(
            frame,
            f"Status: {status}",
            (left, top - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0) if name != "Unknown" else (0, 0, 255),
            2
        )

    # Display frame
    cv2.imshow("AI Smart Door Lock - Face Recognition", frame)

    # Quit with Q
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()