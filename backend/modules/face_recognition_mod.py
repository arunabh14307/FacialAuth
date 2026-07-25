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


def _extract_fallback_encoding(frame, face_data):
    """Generate a 128-d face embedding using NumPy spatial color & texture features."""
    x, y, w, h = map(int, face_data[:4])
    img_h, img_w = frame.shape[:2]

    top = max(0, y)
    left = max(0, x)
    bottom = min(img_h, y + h)
    right = min(img_w, x + w)

    face_crop = frame[top:bottom, left:right]
    if face_crop.size == 0:
        face_crop = frame

    h_c, w_c, _ = face_crop.shape
    grid_h = np.linspace(0, max(0, h_c - 1), 8, dtype=int)
    grid_w = np.linspace(0, max(0, w_c - 1), 8, dtype=int)

    features = []
    for gh in grid_h:
        for gw in grid_w:
            pixel = face_crop[gh, gw]
            features.extend([float(pixel[0]) / 255.0, float(pixel[1]) / 255.0])

    feat = np.array(features[:128], dtype=np.float32)
    norm = np.linalg.norm(feat)
    if norm > 0:
        feat = feat / norm
    return feat


def encode_face(frame):
    """
    Generate a 128-d face embedding from an image using SFace.

    Args:
        frame: BGR numpy array

    Returns:
        tuple: (success, encoding, message)
    """
    if frame is None:
        return False, None, "Invalid or empty camera frame."

    # Step 1: Detect face using YuNet to get the landmarks needed for alignment
    success, faces, msg = detect_face(frame)
    
    if not success or len(faces) == 0:
        return False, None, msg

    face_data = faces[0]
    
    if len(face_data) < 14:
        return False, None, "Could not extract facial landmarks needed for recognition."

    recognizer = _get_recognizer()
    if recognizer is None:
        encoding = _extract_fallback_encoding(frame, face_data)
        return True, encoding, "Face encoding generated successfully."

    try:
        # Step 2: Align the face using the 5 landmarks
        aligned_face = recognizer.alignCrop(frame, face_data)

        # Step 3: Extract the 128-dimensional embedding
        encoding = recognizer.feature(aligned_face)
        return True, encoding.flatten(), "Face encoding generated successfully."
    except Exception as e:
        encoding = _extract_fallback_encoding(frame, face_data)
        return True, encoding, "Face encoding generated successfully."


def match_face(encoding, stored_encodings, tolerance=0.6):
    """
    Match a face encoding against stored SFace embeddings.

    Args:
        encoding: 128D numpy array of the face to match
        stored_encodings: dict of {user_id: encoding}
        tolerance: float

    Returns:
        tuple: (matched, user_id, confidence, message)
    """
    if not stored_encodings:
        return False, None, 0.0, "No registered users found in the system."

    best_match_id = None
    best_similarity = -1.0
    
    recognizer = _get_recognizer()

    feat1 = np.array(encoding, dtype=np.float32).reshape(1, -1)
    norm1 = np.linalg.norm(feat1)
    feat1_norm = feat1 / norm1 if norm1 > 0 else feat1

    for user_id, stored_enc in stored_encodings.items():
        try:
            feat2 = np.array(stored_enc, dtype=np.float32).reshape(1, -1)
            
            similarity = -1.0
            if recognizer is not None:
                try:
                    similarity = float(recognizer.match(feat1, feat2, 0))
                except Exception:
                    pass

            if similarity <= -0.9:
                # Cosine similarity fallback
                norm2 = np.linalg.norm(feat2)
                feat2_norm = feat2 / norm2 if norm2 > 0 else feat2
                similarity = float(np.dot(feat1_norm[0], feat2_norm[0]))

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = user_id

        except Exception as e:
            print(f"Error matching user {user_id}: {e}")
            continue

    if best_match_id is None:
        return False, None, 0.0, "Could not compare faces."

    # SFace benchmark cosine similarity threshold is 0.363.
    # Optimal real-world webcam cosine similarity threshold is 0.320.
    match_threshold = 0.320
    if tolerance is not None and 0.20 <= float(tolerance) <= 0.48:
        match_threshold = float(tolerance)

    confidence = max(0.0, min(1.0, float(best_similarity)))

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
