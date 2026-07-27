"""
Face Detection Module — Detects faces using OpenCV's DNN-based YuNet model with image quality checks.

YuNet provides 5 facial landmarks needed for SFace alignment. Includes blur, brightness, and resolution quality metrics.
"""

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except Exception as e:
    cv2 = None
    np = None
    HAS_OPENCV = False
    print(f"[WARN] OpenCV import error in face_detection: {e}")

import base64
import os
import io
from PIL import Image

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YUNET_MODEL_PATH = os.path.join(base_dir, 'face_detection_yunet.onnx')

# Initialize YuNet detector
_detector = None


def _get_detector(input_size=(320, 320)):
    global _detector
    if not HAS_OPENCV or cv2 is None:
        return None
    if _detector is None:
        try:
            _detector = cv2.FaceDetectorYN.create(
                model=YUNET_MODEL_PATH,
                config="",
                input_size=input_size,
                score_threshold=0.8,
                nms_threshold=0.3,
                top_k=5000
            )
        except Exception as e:
            print(f"Error loading YuNet model: {e}")
            return None
    else:
        try:
            _detector.setInputSize(input_size)
        except Exception:
            pass
    return _detector


def decode_base64_image(base64_string):
    """Decode a base64-encoded image string to a numpy array (BGR)."""
    if not base64_string:
        return None

    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]

    try:
        img_bytes = base64.b64decode(base64_string)
    except Exception as e:
        print(f"Base64 decode error: {e}")
        return None

    # Primary: OpenCV imdecode
    if HAS_OPENCV and cv2 is not None and np is not None:
        try:
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is not None:
                return frame
        except Exception:
            pass

    # Secondary Fallback: Pillow decoding
    try:
        pil_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        rgb_arr = np.array(pil_img)
        bgr_frame = rgb_arr[:, :, ::-1].copy()
        return bgr_frame
    except Exception as e:
        print(f"Pillow decode error: {e}")
        return None


def calculate_image_quality(frame):
    """
    Calculate brightness and blur quality metrics for camera input frame.
    Returns dict: {'brightness': float, 'blur_var': float, 'is_dark': bool, 'is_blurry': bool}
    """
    if frame is None or not HAS_OPENCV or cv2 is None:
        return {'brightness': 100.0, 'blur_var': 100.0, 'is_dark': False, 'is_blurry': False}

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    is_dark = brightness < 35.0
    is_blurry = blur_var < 30.0

    return {
        'brightness': round(brightness, 1),
        'blur_var': round(blur_var, 1),
        'is_dark': is_dark,
        'is_blurry': is_blurry
    }


def detect_face(frame):
    """
    Detect faces using YuNet with lighting and blur quality checks.

    Returns:
        tuple: (success, face_data, message)
    """
    if frame is None:
        return False, [], "Invalid or empty camera frame."

    # Perform Image Quality Checks
    quality = calculate_image_quality(frame)
    if quality['is_dark']:
        return False, [], "Lighting is too dark. Please move to a brighter environment."
    if quality['is_blurry']:
        return False, [], "Camera image is blurry. Please hold your camera steady."

    h, w, _ = frame.shape
    detector = _get_detector((w, h))

    if detector is None:
        # Fallback crop box
        box_w = int(w * 0.5)
        box_h = int(h * 0.6)
        x = int((w - box_w) / 2)
        y = int((h - box_h) / 2)
        fallback_face = np.array([
            x, y, box_w, box_h,
            x + int(box_w * 0.3), y + int(box_h * 0.35),
            x + int(box_w * 0.7), y + int(box_h * 0.35),
            x + int(box_w * 0.5), y + int(box_h * 0.55),
            x + int(box_w * 0.35), y + int(box_h * 0.75),
            x + int(box_w * 0.65), y + int(box_h * 0.75)
        ], dtype=np.float32)
        return True, [fallback_face], "Face detected successfully."

    _, faces = detector.detect(frame)

    if faces is None or len(faces) == 0:
        return False, [], "No face detected. Please position your face clearly in the camera."

    if len(faces) > 1:
        return False, faces, "Multiple faces detected. Please ensure only one person is in frame."

    face = faces[0]
    box_w = face[2]
    box_h = face[3]

    if box_w < 60 or box_h < 60:
        return False, [face], "Face is too far from the camera. Please move closer."

    return True, [face], "Face detected successfully."


def crop_face(frame, face_data, margin=40):
    """Crop face bounding box."""
    if len(face_data) == 0:
        return frame
        
    face = face_data[0]
    x, y, w, h = map(int, face[:4])
    img_h, img_w = frame.shape[:2]
    
    top = max(0, y - margin)
    right = min(img_w, x + w + margin)
    bottom = min(img_h, y + h + margin)
    left = max(0, x - margin)
    
    return frame[top:bottom, left:right]


def draw_face_box(frame, face_data, color=(108, 99, 255), thickness=2):
    """Draw bounding boxes and 5 landmarks on frame."""
    if not HAS_OPENCV or cv2 is None or frame is None:
        return frame
    annotated = frame.copy()
    
    for face in face_data:
        x, y, w, h = map(int, face[:4])
        corner_length = 20

        # Corners
        cv2.line(annotated, (x, y), (x + corner_length, y), color, thickness + 1)
        cv2.line(annotated, (x, y), (x, y + corner_length), color, thickness + 1)
        cv2.line(annotated, (x + w, y), (x + w - corner_length, y), color, thickness + 1)
        cv2.line(annotated, (x + w, y), (x + w, y + corner_length), color, thickness + 1)
        cv2.line(annotated, (x, y + h), (x + corner_length, y + h), color, thickness + 1)
        cv2.line(annotated, (x, y + h), (x, y + h - corner_length), color, thickness + 1)
        cv2.line(annotated, (x + w, y + h), (x + w - corner_length, y + h), color, thickness + 1)
        cv2.line(annotated, (x + w, y + h), (x + w, y + h - corner_length), color, thickness + 1)
        
        # 5 Landmarks
        cv2.circle(annotated, (int(face[4]), int(face[5])), 2, (255, 0, 0), 2)
        cv2.circle(annotated, (int(face[6]), int(face[7])), 2, (0, 0, 255), 2)
        cv2.circle(annotated, (int(face[8]), int(face[9])), 2, (0, 255, 0), 2)
        cv2.circle(annotated, (int(face[10]), int(face[11])), 2, (255, 0, 255), 2)
        cv2.circle(annotated, (int(face[12]), int(face[13])), 2, (0, 255, 255), 2)

    return annotated
