import time
from multiprocessing.synchronize import Event
from multiprocessing.queues import Queue

import multiprocessing as mp
import sys 
import os 


class OverlayManager:
    def __init__(self):
        self.process = None
        self.start_persistent_overlay()
    
    def start_persistent_overlay(self):
        self.stop_event: Event = mp.Event()
        self.show_event: Event = mp.Event()
        self.text_queue: Queue = mp.Queue()
        
        self.process = mp.Process(
            target=self.persistent_overlay_process,
            args=(self.stop_event, self.show_event, self.text_queue),
            daemon=True
        )
        self.process.start()

    @staticmethod
    def persistent_overlay_process(stop_event, show_event, text_queue):
        import tkinter as tk
        
        root = None
        canvas = None
        w, h = 0, 0
        
        def create_window():
            nonlocal root, canvas, w, h
            if root is not None:
                return
                
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            
            try:
                root.attributes("-alpha", 0.0)
            except Exception:
                pass
            
            try:
                root.attributes("-fullscreen", True)
            except Exception:
                pass
            
            root.update_idletasks()
            w = root.winfo_screenwidth()
            h = root.winfo_screenheight()
            root.geometry(f"{w}x{h}+0+0")
            
            root.configure(bg="black")
            
            canvas = tk.Canvas(root, width=w, height=h, highlightthickness=0,  bd=0, bg="black")
            canvas.pack(fill="both", expand=True)
            
            canvas.create_text(w // 2, int(h * 0.42), text="PRIVACY MODE", fill="white", font=("Helvetica", 52, "bold"), tags="text")
            canvas.create_text(w // 2, int(h * 0.50), text="Unauthorized viewer detected — screen obscured",  fill="#cfcfcf", font=("Helvetica", 22), tags="text")
            
            root.update()
        
        def check_events():
            if stop_event.is_set():
                if root:
                    root.destroy()
                return
            
            if show_event.is_set():
                create_window()
                if root:
                    try:
                        root.attributes("-alpha", 0.88)
                    except Exception:
                        pass
                    root.deiconify()
                    root.focus_force()
                    root.lift()  # Bring the windo to the front to block
            else:
                if root:
                    try:
                        root.attributes("-alpha", 0.0)
                    except Exception:
                        pass
                    root.overrideredirect(False)
                    root.iconify()  
                    root.update() 
                    root.withdraw()
            
            root.after(10, check_events) if root else None
        
        create_window()
        if root:
            root.withdraw()  # Hide on startup
            try:
                root.attributes("-alpha", 0.0)
            except Exception:
                pass
            root.after(10, check_events)
            root.mainloop()
    
    def show(self, title: str="PRIVACY MODE", subtitle: str="Unauthorized viewer detected — screen obscured"):
        if self.process and self.process.is_alive():
            self.show_event.set()
            self.text_queue.put((title, subtitle))
    
    def hide(self):
        if self.process and self.process.is_alive():
            self.show_event.clear()
            time.sleep(0.01)
    
    def stop(self):
        if self.process and self.process.is_alive():
            self.stop_event.set()
            self.process.join(timeout=1.0)

def lock_screen():
    try:
        if sys.platform == "darwin":
            os.system("pmset displaysleepnow")
        elif sys.platform == "win32":
            # This is not tested as We don't have a windows...
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        else:
            print(f"Unsupported OS for screen locking: {sys.platform}")
    except Exception as e:
        print(f"Unexpected error locking screen: {e}")
