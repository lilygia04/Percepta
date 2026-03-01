import time
from datetime import datetime
import threading
import queue
import multiprocessing as mp
import cv2
import numpy as np
import threading

from multiprocessing.synchronize import Event
from .logger import LOG_LEVEL, log_event, fmt_time
from .env_vars import CAMERA_INDEX, SIM_THRESHOLD, AUTO_LOCK_DELAY, SHIELD_DELAY
from .cv_utils import get_device, create_models, open_camera, detect_faces, calculate_head_pose, extract_face_tensors,embed_faces, recognize_embeddings, draw_faces, opencv_debug_viewer_proc
from .db_utils import load_db, save_db, clear_face_db
from .security_overlays import OverlayManager, lock_screen
from .misc import st_post

class PerceptaEngine:
    def __init__(self, camera_index=CAMERA_INDEX, show_debug_window = False):
        mp.set_start_method("spawn", force=True)
        log_event("Creating Percepta Engine", LOG_LEVEL.DEBUG)

        self.camera_index = camera_index
        self.show_debug_window = show_debug_window

        self.dbg_q = mp.Queue(maxsize=2)  
        self.dbg_stop = mp.Event()
        self.dbg_proc = None
        if self.show_debug_window:
            self.dbg_proc = mp.Process(
                target=opencv_debug_viewer_proc,
                args=(self.dbg_q, self.dbg_stop),
                daemon=True
            )
            self.dbg_proc.start()

        self.command_queue = queue.Queue()
        self.event_queue = queue.Queue()

        self.thr1 = None
        self.thr1_stop = threading.Event()

        self.protection_enabled = False
        self.private_mode = True
        self.logging_enabled = True
        self.total_detections = 0

        self.device = get_device()
        self.mtcnn, self.resnet = create_models(self.device)
        self.db_names, self.db_embs = load_db()
        self.cap = open_camera(self.camera_index)

        self.last_boxes = None
        self.last_embs = None
        self.overlay_active = False
        self.unknown_looking_start_time = None

        self.no_face_start_time = None
        self.lock_triggered = False
        self.frame_lock = threading.Lock()
        self.latest_frame_bgr = None   
        self.overlay_manager = OverlayManager()

        self.publish_status()

    def start(self):
        log_event("Starting Percepta Engine", LOG_LEVEL.DEBUG)
        if self.thr1 is not None and self.thr1.is_alive():
            return
        self.thr1_stop.clear()
        self.thr1 = threading.Thread(target=self.loop, daemon=True)
        self.thr1.start()

    def stop(self):
        self.command_queue.put(("QUIT", None))
        
    def get_latest_frame(self):
        with self.frame_lock:
            return None if self.latest_frame_bgr is None else self.latest_frame_bgr.copy()
    def publish_status(self):
        standby = not self.protection_enabled
        self.event_queue.put(("STATUS", {
            "standby": standby,
            "protection": self.protection_enabled,
            "private_mode": self.private_mode,
            "private_mode": self.private_mode,
            "registered": len(self.db_names),
        }))
        self.event_queue.put(("TOTAL", {"count": self.total_detections}))

    def emit_detection(self, msg: str):
        self.total_detections += 1
        payload = {"time": fmt_time(), "msg": msg}
        self.event_queue.put(("DETECTION", payload))
        self.event_queue.put(("TOTAL", {"count": self.total_detections}))

        st_post({
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": "detection",
            "time_local": payload["time"],
            "message": msg,
            "source": "percepta_engine",
        })

        log_event(msg, LOG_LEVEL.DEBUG)

    def handle_commands(self):
        try:
            cmd, val = self.command_queue.get_nowait()
        except queue.Empty:
            return

        if cmd == "SET_PROTECTION":
            log_event("Toggle Protection Percepta Engine", LOG_LEVEL.DEBUG)
            self.protection_enabled = bool(val)
            if not self.protection_enabled:
                self.overlay_active = False
                self.unknown_looking_start_time = None
            self.publish_status()
            self.emit_detection(f"Protection toggled {'ON' if self.protection_enabled else 'OFF'}")

        elif cmd == "SET_PRIVATE_MODE":
            log_event("Toggle Private Mode Percepta Engine", LOG_LEVEL.DEBUG)
            self.private_mode = bool(val)
            self.publish_status()
            self.emit_detection(f"Private Mode {'ON' if self.private_mode else 'OFF'}")

        elif cmd == "REGISTER_FACE":
            log_event("Registering Face Percepta Engine", LOG_LEVEL.DEBUG)
            name = (val or "").strip()
            if not name:
                self.event_queue.put(("DETECTION", {"time": fmt_time(), "msg": "Register cancelled (empty name)"}))
                return
            self.register_largest_face(name)

        elif cmd == "QUIT":
            log_event("QUIT Requested", LOG_LEVEL.DEBUG)
            print(self.private_mode)
            if not self.private_mode:
                clear_face_db()
            if self.show_debug_window:
                try:
                    self.dbg_stop.set()
                    if self.dbg_proc is not None:
                        self.dbg_proc.join(timeout=1.0)
                except Exception:
                    pass
            self.thr1_stop.set()

    def register_largest_face(self, name: str):
        if self.last_boxes is None or self.last_embs is None or self.last_embs.shape[0] == 0:
            self.event_queue.put(("DETECTION", {"time": fmt_time(), "msg": "No face detected to register"}))
            return

        boxes = self.last_boxes
        embs = self.last_embs
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        idx = int(np.argmax(areas))

        self.db_names.append(name)
        self.db_embs = np.vstack([self.db_embs, embs[idx].reshape(1, -1)])

        save_db(self.db_names, self.db_embs)

        self.publish_status()
        self.emit_detection(f"Registered face: {name}")

    def loop(self):
        try:
            while not self.thr1_stop.is_set():
                self.handle_commands()
                ret, frame_bgr = self.cap.read()
                if not ret:
                    log_event("Camera Returned Empty", LOG_LEVEL.DEBUG)
                    time.sleep(0.05)
                    continue

                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                boxes, probs, landmarks = detect_faces(self.mtcnn, frame_rgb)

                labels = []
                gaze_is_looking = []

                has_registered_users = (len(self.db_names) > 0 and self.db_embs.shape[0] > 0)

                if boxes is not None and len(boxes) > 0:
                    face_tensors = extract_face_tensors(self.mtcnn, frame_rgb, boxes)
                    if face_tensors is not None:
                        embs = embed_faces(self.resnet, face_tensors, self.device)
                        rec = recognize_embeddings(embs, self.db_names, self.db_embs, SIM_THRESHOLD)

                        for name, sim in rec:
                            
                            labels.append(name if sim is None else f"{name} ({sim:.2f})")
                            log_event(name if sim is None else f"Found Face Tensor, {name} ({sim:.2f})", LOG_LEVEL.DEBUG)

                        # gaze
                        gaze_info = []
                        if landmarks is not None:
                            for i in range(len(boxes)):
                                if landmarks[i] is not None:
                                    is_looking, score, explaination = calculate_head_pose(landmarks[i])
                                    gaze_info.append((is_looking, score, explaination))
                                    gaze_is_looking.append(is_looking)
                                else:
                                    gaze_is_looking.append(False)
                                    gaze_info.append((False, 0.0, "No landmarks"))
                        else:
                            gaze_is_looking = [False] * len(boxes)
                            gaze_info = [(False, 0.0, "No landmarks")] * len(boxes)

                        self.last_boxes = boxes
                        self.last_embs = embs
                    else:
                        self.last_boxes = boxes
                        self.last_embs = None
                else:
                    self.last_boxes = None
                    self.last_embs = None
                annotated = frame_bgr.copy()
                if boxes is not None and len(boxes) > 0 and len(labels) == len(boxes):
                    annotated = draw_faces(annotated, boxes, labels, gaze_info=gaze_info)

                with self.frame_lock:
                    self.latest_frame_bgr = annotated

                #AUtolock
                known_face_detected = any((not lab.startswith("Unknown")) for lab in labels) if labels else False
                if not has_registered_users:
                    self.no_face_start_time = None
                    self.lock_triggered = False
                elif self.protection_enabled:
                    if not known_face_detected:
                        if self.no_face_start_time is None and not self.lock_triggered:
                            self.no_face_start_time = time.time()
                        elif not self.lock_triggered and self.no_face_start_time is not None:
                            if (time.time() - self.no_face_start_time) >= AUTO_LOCK_DELAY:
                                self.emit_detection("Auto-lock triggered (no known face)")
                                self.lock_triggered = True
                                self.no_face_start_time = None

                                if not self.private_mode:
                                    clear_face_db()
                                    self.db_names, self.db_embs = load_db()
                                    self.publish_status()

                                lock_screen()
                    else:
                        self.no_face_start_time = None
                        self.lock_triggered = False

                # Privacy Sheild
                if not self.protection_enabled or not has_registered_users:
                    self.unknown_looking_start_time = None
                    if self.overlay_active:
                        self.overlay_active = False
                elif self.protection_enabled:
                    trigger = any(lab.startswith("Unknown") and look for lab, look in zip(labels, gaze_is_looking))
                    if trigger:
                        if self.unknown_looking_start_time is None:
                            self.unknown_looking_start_time = time.time()
                        elif (not self.overlay_active) and (time.time() - self.unknown_looking_start_time) > SHIELD_DELAY:  
                            self.overlay_active = True
                            log_event("Privacy Screen Activated", LOG_LEVEL.DEBUG)
                            self.overlay_manager.show()
                            self.emit_detection("Shield activated (viewer detected)")
                    else:
                        self.unknown_looking_start_time = None
                        if self.overlay_active:
                            self.overlay_active = False
                            self.overlay_manager.hide()
                            self.emit_detection("Shield cleared")

                if self.show_debug_window and self.dbg_proc is not None and self.dbg_proc.is_alive():
                    try:
                        if self.dbg_q.full():
                            try:
                                _ = self.dbg_q.get_nowait()
                            except Exception:
                                pass
                        self.dbg_q.put_nowait(annotated)
                    except Exception:
                        pass

                    if self.dbg_stop.is_set():
                        self.thr1_stop.set()
        finally:
            try:
                self.cap.release()
            except Exception:
                pass
            if self.show_debug_window:
                try:
                    if self.show_debug_window:
                        self.dbg_stop.set()
                        if self.dbg_proc is not None:
                            self.dbg_proc.join(timeout=1.0)
                except Exception:
                    pass

            if not self.private_mode:
                clear_face_db()
                self.db_names, self.db_embs = load_db()
                self.publish_status()
