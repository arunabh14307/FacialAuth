"""
Gesture Detection Module — Detects facial gestures using MediaPipe FaceLandmarker Tasks API.

Supported gestures:
  - smile: via face blendshapes
  - blink: via face blendshapes
  - look_left: Head orientation (nose relative to face bounds)
  - look_right: Head orientation
  - look_up: Head orientation
  - look_down: Head orientation
"""

import random
import os

try:
    import cv2
    import numpy as np
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    HAS_MEDIAPIPE = True
except Exception as e:
    cv2 = None
    np = None
    mp = None
    python = None
    vision = None
    HAS_MEDIAPIPE = False
    print(f"[WARN] MediaPipe / OpenCV import error in gesture_detection: {e}")

# Lazy initialization of FaceLandmarker
_detector = None

def _get_detector():
    global _detector
    if not HAS_MEDIAPIPE or python is None or vision is None:
        return None
    if _detector is None:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, 'face_landmarker.task')

            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                num_faces=1)

            _detector = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Error loading FaceLandmarker: {e}")
            _detector = None
    return _detector

# MediaPipe face mesh landmarks map exactly as before
NOSE_TIP = 1
FACE_TOP = 10
FACE_BOTTOM = 152
FACE_LEFT = 234
FACE_RIGHT = 454

HEAD_TURN_THRESHOLD = 0.04
HEAD_TILT_THRESHOLD = 0.025

SUPPORTED_GESTURES = ['smile', 'blink', 'look_left', 'look_right', 'look_up', 'look_down']

def get_random_gesture():
    return random.choice(SUPPORTED_GESTURES)

def _detect_head_direction(landmarks):
    nose = np.array([landmarks[NOSE_TIP].x, landmarks[NOSE_TIP].y])
    face_left = np.array([landmarks[FACE_LEFT].x, landmarks[FACE_LEFT].y])
    face_right = np.array([landmarks[FACE_RIGHT].x, landmarks[FACE_RIGHT].y])
    face_top = np.array([landmarks[FACE_TOP].x, landmarks[FACE_TOP].y])
    face_bottom = np.array([landmarks[FACE_BOTTOM].x, landmarks[FACE_BOTTOM].y])

    face_center_x = (face_left[0] + face_right[0]) / 2.0
    face_center_y = (face_top[1] + face_bottom[1]) / 2.0

    face_width = abs(face_right[0] - face_left[0])
    face_height = abs(face_bottom[1] - face_top[1])

    if face_width == 0 or face_height == 0:
        return {g: (False, 0.0) for g in ['look_left', 'look_right', 'look_up', 'look_down']}

    x_offset = (nose[0] - face_center_x) / face_width
    y_offset = (nose[1] - face_center_y) / face_height

    results = {}
    results['look_left'] = (
        x_offset > HEAD_TURN_THRESHOLD,
        min(1.0, abs(x_offset) / HEAD_TURN_THRESHOLD) if x_offset > HEAD_TURN_THRESHOLD else 0.0
    )
    results['look_right'] = (
        x_offset < -HEAD_TURN_THRESHOLD,
        min(1.0, abs(x_offset) / HEAD_TURN_THRESHOLD) if x_offset < -HEAD_TURN_THRESHOLD else 0.0
    )
    results['look_up'] = (
        y_offset < -HEAD_TILT_THRESHOLD,
        min(1.0, abs(y_offset) / HEAD_TILT_THRESHOLD) if y_offset < -HEAD_TILT_THRESHOLD else 0.0
    )
    results['look_down'] = (
        y_offset > HEAD_TILT_THRESHOLD,
        min(1.0, abs(y_offset) / HEAD_TILT_THRESHOLD) if y_offset > HEAD_TILT_THRESHOLD else 0.0
    )
    return results

def _check_single_gesture(results, target_gesture):
    if not results.face_landmarks:
        return False, 0.0, "No face detected for gesture recognition."

    landmarks = results.face_landmarks[0]

    # Process Blendshapes & Landmark Fallback for Smile / Blink
    if target_gesture == 'smile':
        smile_score = 0.0
        if results.face_blendshapes:
            blendshapes = results.face_blendshapes[0]
            scores = {b.category_name: b.score for b in blendshapes}
            smile_score = (scores.get('mouthSmileLeft', 0.0) + scores.get('mouthSmileRight', 0.0)) / 2.0

        mouth_width = abs(landmarks[291].x - landmarks[61].x)
        face_width = abs(landmarks[454].x - landmarks[234].x)
        mouth_ratio = (mouth_width / face_width) if face_width > 0 else 0.0

        detected = (smile_score > 0.25) or (mouth_ratio > 0.40)
        confidence = max(smile_score, min(1.0, mouth_ratio / 0.42))
        return detected, confidence, "Smile detected!" if detected else "Please smile at the camera."

    if target_gesture == 'blink':
        blink_score = 0.0
        if results.face_blendshapes:
            blendshapes = results.face_blendshapes[0]
            scores = {b.category_name: b.score for b in blendshapes}
            blink_left = scores.get('eyeBlinkLeft', 0.0)
            blink_right = scores.get('eyeBlinkRight', 0.0)
            blink_score = max(blink_left, blink_right, (blink_left + blink_right) / 2.0)

        left_ear = abs(landmarks[159].y - landmarks[145].y) / max(0.001, abs(landmarks[133].x - landmarks[33].x))
        right_ear = abs(landmarks[386].y - landmarks[374].y) / max(0.001, abs(landmarks[263].x - landmarks[362].x))
        avg_ear = (left_ear + right_ear) / 2.0

        detected = (blink_score > 0.22) or (avg_ear < 0.21)
        confidence = max(blink_score, min(1.0, 0.25 / max(0.05, avg_ear)))
        return detected, confidence, "Blink detected!" if detected else "Please blink your eyes."

    # Process Head Directions
    if target_gesture in ['look_left', 'look_right', 'look_up', 'look_down']:
        directions = _detect_head_direction(landmarks)
        detected, confidence = directions[target_gesture]
        direction_name = target_gesture.replace('_', ' ')
        msg = f"{direction_name.title()} detected!" if detected else f"Please turn your head to {direction_name.replace('look ', '')}."
        return detected, confidence, msg

    return False, 0.0, "Could not determine gesture."

def detect_gesture(frame, target_gesture):
    if frame is None:
        return False, 0.0, "Invalid or empty camera frame."

    detector = _get_detector()
    if detector is None:
        return False, 0.0, "Gesture verification AI model is unavailable on this server."

    if target_gesture not in SUPPORTED_GESTURES:
        return False, 0.0, f"Unsupported gesture: {target_gesture}"

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    results = detector.detect(mp_image)

    if not results.face_landmarks:
        return False, 0.0, "No face detected for gesture recognition."

    # 1. Try primary target gesture
    detected, confidence, msg = _check_single_gesture(results, target_gesture)
    if detected:
        return True, confidence, msg

    # 2. Fallback: check any other valid gesture to verify active liveness
    for g in SUPPORTED_GESTURES:
        if g == target_gesture:
            continue
        g_detected, g_confidence, _ = _check_single_gesture(results, g)
        if g_detected:
            g_display = get_gesture_display_name(g)
            return True, g_confidence, f"Live gesture verified ({g_display})!"

    return False, 0.0, msg

def get_gesture_display_name(gesture):
    names = {
        'smile': '😊 Smile',
        'blink': '😑 Blink',
        'look_left': '👈 Look Left',
        'look_right': '👉 Look Right',
        'look_up': '👆 Look Up',
        'look_down': '👇 Look Down'
    }
    return names.get(gesture, gesture)

def get_gesture_instruction(gesture):
    instructions = {
        'smile': 'Please give a big SMILE to the camera!',
        'blink': 'Please BLINK your eyes clearly.',
        'look_left': 'Please turn your head to the LEFT.',
        'look_right': 'Please turn your head to the RIGHT.',
        'look_up': 'Please LOOK UP towards the ceiling.',
        'look_down': 'Please LOOK DOWN towards the floor.'
    }
    return instructions.get(gesture, f'Please perform: {gesture}')
