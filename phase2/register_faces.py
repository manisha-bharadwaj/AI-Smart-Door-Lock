import face_recognition
import pickle
import os

KNOWN_FACES_DIR = "phase2/known_faces"
ENCODINGS_FILE = "phase2/encodings.pkl"


def register_faces():
    known_encodings = []
    known_names = []

    for filename in os.listdir(KNOWN_FACES_DIR):

        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        image_path = os.path.join(KNOWN_FACES_DIR, filename)

        print(f"Processing: {filename}")

        image = face_recognition.load_image_file(image_path)

        face_locations = face_recognition.face_locations(image)

        if len(face_locations) == 0:
            print(f"❌ No face found in {filename}")
            continue

        if len(face_locations) > 1:
            print(f"❌ Multiple faces found in {filename}")
            continue

        face_encodings = face_recognition.face_encodings(
            image,
            face_locations
        )

        if len(face_encodings) == 0:
            print(f"❌ Could not generate encoding for {filename}")
            continue

        encoding = face_encodings[0]

        name = os.path.splitext(filename)[0]

        known_encodings.append(encoding)
        known_names.append(name)

        print(f"✅ Registered: {name}")

    data = {
        "encodings": known_encodings,
        "names": known_names
    }

    with open(ENCODINGS_FILE, "wb") as file:
        pickle.dump(data, file)

    print("\n==============================")
    print("Face registration completed!")
    print(f"Registered faces: {len(known_names)}")
    print(f"Saved to: {ENCODINGS_FILE}")
    print("==============================")


if __name__ == "__main__":
    register_faces()