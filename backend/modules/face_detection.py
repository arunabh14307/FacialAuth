"""
Face Detection Module — Detects faces using OpenCV's DNN-based YuNet model.

YuNet is highly accurate and provides 5 facial landmarks needed for SFace alignment.
"""

import cv2
import numpy as np
import base64
import os

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YUNET_MODEL_PATH = os.path.join(base_dir, 'face_detection_yunet.onnx')

# Initialize YuNet detector
_detector = None

def _get_detector(input_size=(320, 320)):
    global _detector
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
        _detector.setInputSize(input_size)
    return _detector


def decode_base64_image(base64_string):
    """Decode a base64-encoded image string to a numpy array (BGR)."""
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]

    img_bytes = base64.b64decode(base64_string)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return frame


def detect_face(frame):
    """
    Detect faces using YuNet.

    Args:
        frame: BGR numpy array (from OpenCV or decoded base64)

    Returns:
        tuple: (success, face_data, message)
            - success: bool
            - face_data: raw face data from YuNet including box and 5 landmarks (if single face detected, list of length 1)
            - message: str
    """
    if frame is None:
        return False, [], "Invalid image data"

    h, w, _ = frame.shape
    detector = _get_detector((w, h))

    if detector is None:
        return False, [], "Face detector model not found."

    # YuNet expects BGR format
    _, faces = detector.detect(frame)

    if faces is None or len(faces) == 0:
        return False, [], "No face detected. Please position your face clearly in the camera."

    if len(faces) > 1:
        return False, faces, "Multiple faces detected. Please ensure only one person is in frame."

    # Check bounding box dimensions
    face = faces[0]
    box_w = face[2]
    box_h = face[3]

    if box_w < 60 or box_h < 60:
        return False, [face], "Face is too far from the camera. Please move closer."

    return True, [face], "Face detected successfully."


def crop_face(frame, face_data, margin=40):
    """
    Crop the face based on the detected bounding box.
    """
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
    """
    Draw bounding boxes and landmarks.
    """
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
        
        # Draw 5 landmarks
        cv2.circle(annotated, (int(face[4]), int(face[5])), 2, (255, 0, 0), 2)  # Right eye
        cv2.circle(annotated, (int(face[6]), int(face[7])), 2, (0, 0, 255), 2)  # Left eye
        cv2.circle(annotated, (int(face[8]), int(face[9])), 2, (0, 255, 0), 2)  # Nose
        cv2.circle(annotated, (int(face[10]), int(face[11])), 2, (255, 0, 255), 2)  # Right mouth corner
        cv2.circle(annotated, (int(face[12]), int(face[13])), 2, (0, 255, 255), 2)  # Left mouth corner

    return annotated
