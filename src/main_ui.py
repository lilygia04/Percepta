import tkinter as tk
from tkinter import ttk, simpledialog

from .percepta_engine import PerceptaEngine
from .logger import LOG_LEVEL, log_event
from .ui_utils import Card

class PerceptaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Percepta")
        self.geometry("520x820")
        self.configure(bg="#0B0D12")
        self.resizable(True, True)
        self.minsize(520, 820)

        # engine
        self.engine = PerceptaEngine(show_debug_window=True)
        self.engine.start()

        self.total = 0
        self.log_items = []

        self.build_ui()
        self.after(50, self.poll_engine)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        header = tk.Canvas(self, height=64, bg="#0B0D12", highlightthickness=0)
        header.pack(fill="x", pady=(16, 0), padx=16)

        header.create_rectangle(0, 0, 520, 64, fill="#6D2CF5", outline="")
        header.create_rectangle(260, 0, 520, 64, fill="#2F6BFF", outline="")

        header.create_text(60, 32, text="Percepta", fill="white", font=("Helvetica", 18, "bold"), anchor="w")
        subtitle = tk.Label(self, text="Automatic screen protection against shoulder surfing", bg="#0B0D12", fg="#A7AAB6", font=("Helvetica", 11))
        subtitle.pack(pady=(18, 10))

        row = tk.Frame(self, bg="#0B0D12")
        row.pack(padx=16, pady=10, fill="x")

        self.card_prot = Card(row, width=240, height=220)
        self.card_prot.grid(row=0, column=0, padx=(0, 12))
        self.card_priv = Card(row, width=240, height=220)
        self.card_priv.grid(row=0, column=1)

        self.card_prot.create_text(120, 70, text="🛡️", fill="#B9BECC", font=("Helvetica", 36))
        self.prot_title = self.card_prot.create_text(120, 120, text="Protection Off", fill="white", font=("Helvetica", 16, "bold"))
        self.card_prot.create_text(120, 148, text="Tap to enable screen\nprotection", fill="#A7AAB6", font=("Helvetica", 10), justify="center")
        self.btn_prot = ttk.Button(self, text="OFF", command=self.toggle_protection)
        self.place_button_over_canvas(self.card_prot, self.btn_prot, 120, 190)

        self.card_priv.create_text(120, 70, text="👤", fill="#B9BECC", font=("Helvetica", 36))
        self.priv_title = self.card_priv.create_text(120, 120, text="Private Mode", fill="white", font=("Helvetica", 16, "bold"))
        self.card_priv.create_text(120, 148, text="Only unknown faces\ntrigger alerts", fill="#A7AAB6", font=("Helvetica", 10), justify="center")
        self.btn_priv = ttk.Button(self, text="PRIVATE", command=self.toggle_private_mode)
        self.place_button_over_canvas(self.card_priv, self.btn_priv, 120, 190)

        log_card = Card(self, width=488, height=300, bg="#0F1116", border="#232633")  
        log_card.pack(padx=16, pady=0)
        log_card.create_text(40, 42, text="🕒", fill="#9B6BFF", font=("Helvetica", 16, "bold"))
        log_card.create_text(70, 42, text="Detection Log", fill="white",
                            font=("Helvetica", 14, "bold"), anchor="w")

        self.log_box = tk.Listbox(self, height=6, bg="#0F1116", fg="#D7DAE6", highlightthickness=0, bd=0, activestyle="none",  font=("Helvetica", 11))
        self.log_box.insert("end", "No detections yet")
        self.log_box.itemconfig(0, fg="#7C8090")

        log_card.create_window(244, 170, window=self.log_box, width=440, height=200)  

        bottom = tk.Frame(self, bg="#0B0D12")
        bottom.pack(padx=16, pady=16, fill="x", side="bottom") 

        self.btn_register = ttk.Button(bottom, text="Register Face", command=self.register_face)
        self.btn_register.pack(side="left")

        self.btn_quit = ttk.Button(bottom, text="Quit", command=self.on_close)
        self.btn_quit.pack(side="right")

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TButton", padding=10)
        style.map("TButton",
                foreground=[("active", "#FFFFFF")],
                background=[("active", "#1A1D27")])

    def place_button_over_canvas(self, canvas, button, cx, cy):
        canvas.create_window(cx, cy, window=button, width=110, height=34)

    def toggle_protection(self):
        is_on = (self.btn_prot["text"] == "ON")
        self.engine.command_queue.put(("SET_PROTECTION", (not is_on)))

    def toggle_private_mode(self):
        is_on = (self.btn_priv["text"] == "PRIVATE")
        self.engine.command_queue.put(("SET_PRIVATE_MODE", (not is_on)))

    def register_face(self):
        log_event("Register Face Requested", LOG_LEVEL.DEBUG)
        name = simpledialog.askstring("Register Face", "Enter name to register:")
        if not name:
            return
        self.engine.command_queue.put(("REGISTER_FACE", name.strip()))

    def on_close(self):
        log_event("Close Requested", LOG_LEVEL.DEBUG)
        try:
            self.engine.stop()
        except Exception:
            pass
        self.destroy()

    def poll_engine(self):
        try:
            while True:
                etype, payload = self.engine.event_queue.get_nowait()
                if etype == "STATUS":
                    self.apply_status(payload)
                elif etype == "DETECTION":
                    self.append_log(payload["time"], payload["msg"])
                elif etype == "TOTAL":
                    self.total = int(payload["count"])
                    self.title(f"Percepta — {self.total} detections")
        except Exception:
            pass

        self.after(50, self.poll_engine)

    def apply_status(self, st):
        standby = st.get("standby", True)
        protection = st.get("protection", False)
        private_mode = st.get("private_mode", True)

        if standby:
            pass

        if protection:
            self.card_prot.itemconfig(self.prot_title, text="Protection On")
            self.btn_prot.config(text="ON")
        else:
            self.card_prot.itemconfig(self.prot_title, text="Protection Off")
            self.btn_prot.config(text="OFF")

        if private_mode:
            self.btn_priv.config(text="PRIVATE")
        else:
            self.btn_priv.config(text="ALL")

    def append_log(self, t, msg):
        if self.log_box.size() == 1 and self.log_box.get(0) == "No detections yet":
            self.log_box.delete(0)

        line = f"{t} — {msg}"
        self.log_box.insert(0, line)  
        if self.log_box.size() > 50:
            self.log_box.delete(50, "end")