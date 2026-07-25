"""
Face Recognition Module — Encodes and matches faces using SFace.

SFace is a highly accurate state-of-the-art CNN model available in OpenCV.
It extracts a 128-dimensional embedding from aligned faces.
"""

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except Exception as e:
    cv2 = None
    np = None
    HAS_OPENCV = False
    print(f"[WARN] OpenCV import error in face_recognition_mod: {e}")

import os
from backend.modules.face_detection import detect_face

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFACE_MODEL_PATH = os.path.join(base_dir, 'face_recognition_sface.onnx')

# Initialize SFace recognizer
_recognizer = None

def _get_recognizer():
    global _recognizer
    if not HAS_OPENCV or cv2 is None:
        return None
    if _recognizer is None:
        try:
            _recognizer = cv2.FaceRecognizerSF.create(
                model=SFACE_MODEL_PATH,
                config=""
            )
        except Exception as e:
            print(f"Error loading SFace model: {e}")
            return None
    return _recognizer


def encode_face(frame):
    """
    Generate a 128-d face embedding from an image using SFace.

    Args:
        frame: BGR numpy array

    Returns:
        tuple: (success, encoding, message)
            - success: bool
            - encoding: 128D numpy array
            - message: str
    """
    if frame is None:
        return False, None, "Invalid image data"

    # Step 1: Detect face using YuNet to get the landmarks needed for alignment
    success, faces, msg = detect_face(frame)
    
    if not success or len(faces) == 0:
        return False, None, msg

    face_data = faces[0]
    
    # Check if we have the 14-element array from YuNet (box + 5 landmarks)
    if len(face_data) < 14:
        return False, None, "Could not extract facial landmarks needed for recognition."

    recognizer = _get_recognizer()
    if recognizer is None:
        return False, None, "Face recognition model not found."

    try:
        # Step 2: Align the face using the 5 landmarks
        aligned_face = recognizer.alignCrop(frame, face_data)

        # Step 3: Extract the 128-dimensional embedding
        encoding = recognizer.feature(aligned_face)
        
        # SFace outputs a shape (1, 128) array, flatten it
        return True, encoding.flatten(), "Face encoding generated successfully."
    except Exception as e:
        return False, None, f"Error generating face encoding: {str(e)}"


def match_face(encoding, stored_encodings, tolerance=0.6):
    """
    Match a face encoding against stored SFace embeddings.

    Args:
        encoding: 128D numpy array of the face to match
        stored_encodings: dict of {user_id: encoding}
        tolerance: float
                   In SFace, cosine similarity >= 0.363 is a match for FPR=1e-5.
                   We'll map 'tolerance' to a suitable threshold.

    Returns:
        tuple: (matched, user_id, confidence, message)
    """
    if not stored_encodings:
        return False, None, 0.0, "No registered users found in the system."

    best_match_id = None
    best_similarity = -1.0
    
    recognizer = _get_recognizer()

    for user_id, stored_enc in stored_encodings.items():
        try:
            # SFace embeddings must be (1, 128) shape for the match function
            feat1 = encoding.reshape(1, -1)
            feat2 = np.array(stored_enc).reshape(1, -1)

            # Cosine similarity using SFace builtin function
            # Alternatively: cv2.FaceRecognizerSF_FR_COSINE = 0
            if recognizer:
                similarity = recognizer.match(feat1, feat2, 0)
            else:
                # Manual Cosine similarity fallback
                dot_product = np.dot(feat1[0], feat2[0])
                norm1 = np.linalg.norm(feat1[0])
                norm2 = np.linalg.norm(feat2[0])
                similarity = dot_product / (norm1 * norm2)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = user_id

        except Exception as e:
            print(f"Error matching user {user_id}: {e}")
            continue

    if best_match_id is None:
        return False, None, 0.0, "Could not compare faces."

    # SFace Threshold: 0.363 is highly accurate. We can adjust based on tolerance.
    # If tolerance is 0.6 (default), let's set a safe threshold.
    # Lower tolerance = Higher required threshold
    match_threshold = 0.363 + ((0.6 - tolerance) * 0.2)

    confidence = max(0.0, min(1.0, best_similarity)) # In SFace it can technically range roughly -1 to 1

    if best_similarity >= match_threshold:
        return True, best_match_id, confidence, f"Face matched with confidence {confidence:.1%}"
    else:
        return False, None, confidence, "Face not recognized. Please register first or try again."


def compare_faces(encoding1, encoding2):
    """Compare two face encodings directly."""
    feat1 = encoding1.reshape(1, -1)
    feat2 = encoding2.reshape(1, -1)
    
    recognizer = _get_recognizer()
    if recognizer:
        similarity = recognizer.match(feat1, feat2, 0)
    else:
        dot_product = np.dot(feat1[0], feat2[0])
        norm1 = np.linalg.norm(feat1[0])
        norm2 = np.linalg.norm(feat2[0])
        similarity = dot_product / (norm1 * norm2)
        
    is_same = similarity >= 0.363
    distance = 1.0 - similarity
    confidence = max(0.0, similarity)

    return is_same, distance, confidence
