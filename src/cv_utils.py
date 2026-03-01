from facenet_pytorch import MTCNN, InceptionResnetV1
import multiprocessing as mp
from multiprocessing.synchronize import Event

from .logger import log_event, LOG_LEVEL
from .env_vars import CAMERA_INDEX, GAZE_THRESHOLD

import cv2
import torch
import numpy as np

def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"
    
def open_camera(index: int = CAMERA_INDEX):
    log_event("Opening Camera", LOG_LEVEL.DEBUG)
    cap: cv2.VideoCapture = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam at index {index}. Try 0,1,2... and check permissions.")
    return cap

def create_models(device: str):
    log_event("Creating Model", LOG_LEVEL.DEBUG)
    
    if device == "mps":
        mtcnn_device : str = "cpu"  # MTCNN can't use mps for some reason...
    mtcnn : MTCNN = MTCNN(
        image_size=160,
        margin=20,
        min_face_size=40,
        thresholds=[0.6, 0.7, 0.7],
        factor=0.709,
        post_process=True,
        device=mtcnn_device,
        keep_all=True,
        select_largest=False,
    )
    
    resnet: InceptionResnetV1 = InceptionResnetV1(pretrained="vggface2").eval().to(device)
    
    if device == "mps":
        log_event("MPS detected: MTCNN on CPU, ResNet on MPS", LOG_LEVEL.DEBUG)
    
    return mtcnn, resnet

def detect_faces(mtcnn: MTCNN, frame_rgb: np.ndarray):
    result = mtcnn.detect(frame_rgb, landmarks=True)

    if result is not None:
        if len(result) == 3:
            boxes, probs, landmarks = result
        elif len(result) == 2: # This is when no landmarks is detected
            boxes, probs = result
            landmarks = None
    else:
        boxes, probs, landmarks = None, None, None 

    return boxes, probs, landmarks

def extract_face_tensors(mtcnn: MTCNN, frame_rgb: np.ndarray, boxes: np.ndarray):
    boxes = boxes.astype(np.float32)
    faces = mtcnn.extract(frame_rgb, boxes, save_path=None)
    if faces is None:
        return None

    if isinstance(faces, list):
        faces = [f for f in faces if f is not None]
        if not faces:
            return None
        faces = torch.stack(faces, dim=0)

    if faces.dim() == 3:
        faces = faces.unsqueeze(0)

    return faces


def embed_faces(resnet: InceptionResnetV1, face_tensors: torch.Tensor, device: str):
    face_tensors = face_tensors.to(device)
    with torch.no_grad():
        embs_t = resnet(face_tensors)
    return embs_t.cpu().numpy().astype(np.float32)


def recognize_embeddings(embs: np.ndarray, db_names, db_embs: np.ndarray, sim_threshold: float):
    results = []
    for i in range(embs.shape[0]):
        if db_embs.shape[0] == 0:
            results.append(("Unknown", None))
            continue

        sims = cosine_sim(embs[i], db_embs)
        best_i = int(np.argmax(sims))
        best_sim = float(sims[best_i])

        if best_sim >= sim_threshold:
            results.append((db_names[best_i], best_sim))
        else:
            results.append(("Unknown", best_sim))
    return results

def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return (b @ a).astype(np.float32)

def calculate_head_pose(landmarks):
    if landmarks is None or len(landmarks) < 5:
        return False, 0.0, "No landmarks"

    left_eye = landmarks[0]
    right_eye = landmarks[1]
    nose = landmarks[2]
    left_mouth = landmarks[3]
    right_mouth = landmarks[4]

    eye_center = (left_eye + right_eye) / 2
    eye_distance = np.linalg.norm(right_eye - left_eye) + 1e-9

    nose_offset = nose - eye_center
    nose_x_ratio = nose_offset[0] / (eye_distance + 1e-9)

    centered_threshold = 0.15
    is_centered = abs(nose_x_ratio) < centered_threshold

    left_eye_to_nose = np.linalg.norm(nose - left_eye)
    right_eye_to_nose = np.linalg.norm(nose - right_eye)
    symmetry_ratio = min(left_eye_to_nose, right_eye_to_nose) / (max(left_eye_to_nose, right_eye_to_nose) + 1e-9)

    mouth_center = (left_mouth + right_mouth) / 2
    mouth_offset = mouth_center - eye_center
    mouth_x_ratio = mouth_offset[0] / (eye_distance + 1e-9)

    gaze_score = 1.0
    if not is_centered:
        gaze_score *= max(0, 1 - abs(nose_x_ratio) * 2)
    gaze_score *= symmetry_ratio
    if abs(mouth_x_ratio - nose_x_ratio) > 0.1:
        gaze_score *= max(0, 1 - abs(mouth_x_ratio - nose_x_ratio) * 2)

    is_looking = gaze_score > GAZE_THRESHOLD

    if is_looking:
        explanation = f"Looking (score: {gaze_score:.2f})"
    else:
        if not is_centered:
            explanation = f"Looking away (off-center: {nose_x_ratio:.2f})"
        elif symmetry_ratio < 0.7:
            explanation = f"Profile view (sym: {symmetry_ratio:.2f})"
        else:
            explanation = f"Not looking (score: {gaze_score:.2f})"

    return is_looking, gaze_score, explanation

def draw_faces(frame_bgr, boxes, labels, gaze_info=None):
    out = frame_bgr.copy()
    if boxes is None or len(boxes) == 0:
        return out

    for i, (box, label) in enumerate(zip(boxes, labels)):
        x1, y1, x2, y2 = box.astype(int)
        color = (0, 255, 0)

        if gaze_info and i < len(gaze_info):
            is_looking, _, explanation = gaze_info[i]
            if label.startswith("Unknown") and is_looking:
                color = (0, 0, 255)      
            elif is_looking:
                color = (0, 255, 0)    
            else:
                color = (0, 165, 255) 

            cv2.putText(out, explanation, (x1, y2 + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(out, label, (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return out


def opencv_debug_viewer_proc(frame_q: mp.Queue, stop_evt: Event):
    import cv2
    import time

    win = "Percepta Demo (Bounding Boxes)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    last = None
    while not stop_evt.is_set():
        try:
            while True:
                last = frame_q.get_nowait()
        except Exception:
            pass

        if last is not None:
            cv2.imshow(win, last)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            stop_evt.set()
            break

        time.sleep(0.001)

    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
