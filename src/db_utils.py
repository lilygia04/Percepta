from .logger import log_event, LOG_LEVEL
from .env_vars import DB_FILE, META_FILE

from typing import List
from pathlib import Path

import os
import numpy as np
import json
def load_db(db_file: str = DB_FILE, meta_file: str = META_FILE):
    log_event("Loading DB", LOG_LEVEL.DEBUG)
    names: List[str]= []
    embs: np.ndarray = np.empty((0, 512), dtype=np.float32)

    meta_path = Path(META_FILE)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    log_event(str(Path(DB_FILE).resolve()), LOG_LEVEL.DEBUG)
    if os.path.exists(db_file):
        data = np.load(db_file, allow_pickle=True)
        embs = data["embs"].astype(np.float32)

    log_event(str(Path(META_FILE).resolve()), LOG_LEVEL.DEBUG)
    if os.path.exists(meta_file):
        with open(meta_file, "r") as f:
            names = json.load(f)

    if len(names) != embs.shape[0]:
        names: List[str]= []
        embs: np.ndarray = np.empty((0, 512), dtype=np.float32)

    return names, embs


def save_db(names: List[str], embs: np.ndarray, db_file: str = DB_FILE, meta_file: str = META_FILE):
    np.savez(db_file, embs=embs.astype(np.float32))
    with open(meta_file, "w") as f:
        json.dump(names, f)


def clear_face_db():
    log_event("Clearning DB", LOG_LEVEL.DEBUG)
    save_db([], np.empty((0, 512), dtype=np.float32))