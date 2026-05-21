import customtkinter as ctk

def _get_gui():
    try:
        import src.gui as gui
    except ImportError:
        import gui
    return gui

class CompactPedalboardFrame(ctk.CTkFrame):
    """Grid layout for pedalboard (shared between Main and Remote)"""
    def __init__(self, parent, device_def, profile, callback_press):
        from i18n import _
        self._ = _
        super().__init__(parent, fg_color="transparent")
        self.device_def = device_def
        self.profile = profile
        self.callback_press = callback_press
        self.btn_map = {} # Map CC -> Button Widget

        self.update_layout()

    def set_profile(self, new_profile):
        self.profile = new_profile
        self.update_layout()

    def set_device_def(self, new_def):
        self.device_def = new_def
        self.update_layout()

    def flash_button(self, cc):
        """Simulate a visual flash on the specific button"""
        gui = _get_gui()
        if cc in self.btn_map:
            btn = self.btn_map[cc]
            original_color = btn.cget("fg_color")
            original_text_color = btn.cget("text_color")
            # Flash Color: Electric Neon Cyan
            btn.configure(fg_color="#00E5FF", text_color=gui.BG_COLOR) 
            self.after(150, lambda: btn.configure(fg_color=original_color, text_color=original_text_color))

    def _get_icon_for_name(self, name):
        """Convertit les mots clés en icônes pour le mode Remote"""
        n = name.lower()
        # Transport
        if "play" in n and "pause" in n: return "⏯"
        if "play" in n: return "▶"
        if "pause" in n: return "⏸"
        if "stop" in n: return "■"
        if "rec" in n: return "●"
        if "prev" in n or "rewind" in n or "back" in n: return "⏪"
        if "next" in n or "forward" in n: return "⏩"
        if "loop" in n: return "⟳"
        # Audio
        if "mute" in n: return "🔇"
        if "vol" in n or "audio" in n: return "🔊"
        if "pan" in n: return "↔"
        # Tools
        if "speed" in n or "tempo" in n or "bpm" in n: return "⏱"
        if "pitch" in n or "key" in n or "tune" in n: return "♪"
        if "metro" in n: return "◴"
        if "marker" in n: return "📍"
        # Navigation
        if "up" in n: return "▲"
        if "down" in n: return "▼"
        if "left" in n: return "◄"
        if "right" in n: return "►"
        if "enter" in n or "ok" in n: return "✓"
        if "undo" in n: return "↶"
        if "redo" in n: return "↷"
        # Generic
        return "⚡"

    def update_layout(self):
        # Clear existing buttons
        for w in self.winfo_children():
            w.destroy()
        self.btn_map.clear()

        none_lbl = self._("gui.lbl_none")
        is_virtual = False
        if self.profile and (self.profile.get("device_name") == none_lbl or self.profile.get("device_name") == "Aucun"):
            is_virtual = True
        elif not self.device_def or self.device_def.get("name") == none_lbl or not self.device_def.get("buttons"):
            is_virtual = True

        if is_virtual:
            # Grille dynamique (Option A) basée uniquement sur les mappings configurés
            buttons_def = []
            mappings = self.profile.get("mappings", []) if self.profile else []
            for m in mappings:
                cc = m.get("midi_cc")
                name = m.get("name", "Bouton")
                if cc is not None:
                    buttons_def.append({
                        "cc": cc,
                        "short_label": name[:12], # le nom de l'action abrégé
                        "label": name
                    })
            if not buttons_def:
                # Aucun bouton virtuel configuré
                msg = self._("gui.lbl_no_virtual_buttons", "Aucun bouton virtuel")
                lbl_empty = ctk.CTkLabel(self, text=msg, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="gray")
                lbl_empty.pack(pady=20, padx=10)
                return
        else:
            if not self.device_def or "buttons" not in self.device_def:
                msg = self._("gui.lbl_no_device_def")
                if self.device_def is None: msg += " (None)"
                elif "buttons" not in self.device_def: msg += " (No Buttons)"
                ctk.CTkLabel(self, text=msg).pack(pady=20)
                return
            buttons_def = self.device_def["buttons"]

        # Mapping Map : CC -> {name, custom_icon}
        mapping_map = {}
        if self.profile:
            for m in self.profile.get("mappings", []):
                cc = m.get("midi_cc")
                if cc is not None:
                    mapping_map[cc] = m

        # Grid logic
        if is_virtual:
            cols = min(5, len(buttons_def))
            if cols < 1: cols = 1
        else:
            cols = 10 # 10 Columns for standard AIRSTEP (5 Short + 5 Long)
            if len(buttons_def) > 10:
                 cols = 10 # split into rows

        for i, btn_data in enumerate(buttons_def):
            cc = btn_data["cc"]
            default_label = btn_data["label"]

            if is_virtual:
                short_lbl = btn_data.get("short_label", default_label)
            else:
                # Priorité au short_label explicite si configuré
                short_lbl = btn_data.get("short_label")
                if not short_lbl:
                    # Clean Physical Index (Top Label)
                    short_lbl = default_label.replace("Bouton ", "").replace("Button ", "").replace("Footswitch ", "")
                    if "(" in short_lbl: short_lbl = short_lbl.split("(")[0].strip()
                    
                    # Handle Long Press Labels
                    is_long_press = "Long Press" in default_label
                    if is_long_press:
                        base = default_label.replace("Long Press ", "").strip()
                        if "(" in base: base = base.split("(")[0].strip()
                        short_lbl = f"{base} ({self._('gui.lbl_hold')})"
            
            # Determine Icon & State
            mapping_data = mapping_map.get(cc, None)

            if mapping_data:
                action_name = mapping_data.get("name", "")
                custom_icon = mapping_data.get("custom_icon")
                if custom_icon: icon = custom_icon
                else: icon = self._get_icon_for_name(action_name)
                
                main_text = icon
                gui = _get_gui()
                btn_color = gui.ACCENT_COLOR 
                hover_color = gui.ACCENT_HOVER
                state = "normal"
                text_color = gui.TEXT_PRIMARY
                border_w = 0
                border_c = btn_color
            else:
                gui = _get_gui()
                main_text = ""
                btn_color = gui.CARD_BG
                hover_color = gui.CARD_BG
                state = "disabled"
                text_color = "gray25"
                border_w = 1
                border_c = gui.BORDER_COLOR

            # Layout Calculation
            row = i // cols
            col = i % cols
            
            # Container
            container = ctk.CTkFrame(self, fg_color="transparent")
            container.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

            # 1. Top Label (Physical Index)
            gui = _get_gui()
            lbl_phy = ctk.CTkLabel(
                container,
                text=short_lbl,
                font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                text_color=gui.TEXT_SECONDARY,
                wraplength=70,
                height=24
            )
            lbl_phy.pack(side="top", pady=(0, 2))

            # 2. Main Button (Icon)
            btn = ctk.CTkButton(
                container,
                text=main_text,
                font=ctk.CTkFont(family="Segoe UI Symbol", size=16), # Compact Icon
                fg_color=btn_color,
                hover_color=hover_color,
                text_color=text_color,
                state=state,
                height=36, 
                width=40,
                corner_radius=8,
                border_width=border_w,
                border_color=border_c,
                command=lambda c=cc: self.on_btn_click(c)
            )
            btn.pack(side="top", fill="both", expand=True)
            
            # Store in map
            self.btn_map[cc] = btn

        # Configure columns weight for responsiveness
        for c in range(cols):
            self.grid_columnconfigure(c, weight=1)
        # Configure rows
        rows = (len(buttons_def) - 1) // cols + 1
        for r in range(rows):
            self.grid_rowconfigure(r, weight=1)

    def on_btn_click(self, cc):
        self.flash_button(cc) # Visual immediate feedback
        self.callback_press(cc)


class RemoteControl(ctk.CTkToplevel):
    def __init__(self, parent, device_def, profile, callback_press, callback_close, callback_open_conf=None, callback_open_web=None):
        super().__init__(parent)
        self.callback_press = callback_press
        self.callback_close = callback_close
        self.callback_open_conf = callback_open_conf
        self.callback_open_web = callback_open_web
        from i18n import _
        self._ = _
        self.device_def = device_def
        self.profile = profile

        self.is_minimized = False
        self.saved_geometry = "400x300+100+100"

        # Style: Modern Cockpit
        gui = _get_gui()
        self.bg_color = gui.BG_COLOR
        self.header_color = gui.CARD_BG
        self.hover_color = gui.BTN_SECONDARY
        self.border_color = gui.BORDER_COLOR

        # Window Setup
        self.title(self._("gui.title_remote"))
        self.overrideredirect(True) # Frameless
        self.attributes("-topmost", True)
        self.configure(fg_color=self.bg_color)

        # Dragging logic
        self.x_offset = 0
        self.y_offset = 0
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

        self.build_ui()
        self.update_layout()

    def start_move(self, event):
        self.x_offset = event.x
        self.y_offset = event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self.x_offset)
        y = self.winfo_y() + (event.y - self.y_offset)
        self.geometry(f"+{x}+{y}")

    def build_ui(self):
        gui = _get_gui()
        # Main Outer Container mimicking a modern premium frame border
        self.main_border_frame = ctk.CTkFrame(self, fg_color=self.bg_color, border_width=1, border_color=self.border_color, corner_radius=10)
        self.main_border_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # --- Header (Barre de titre custom) ---
        self.header = ctk.CTkFrame(self.main_border_frame, height=28, fg_color=self.header_color, corner_radius=10)
        self.header.pack(fill="x", side="top", padx=1, pady=1)

        # Bind move on header too
        self.header.bind("<ButtonPress-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)

        # Title / Handle
        title_text = f"{self._('gui.lbl_remote_prefix')} - {self.profile.get('name', 'Profile')}" if self.profile else self._("gui.title_remote")
        if len(title_text) > 25: title_text = title_text[:25] + "..."

        self.lbl_title = ctk.CTkLabel(self.header, text=title_text, text_color=gui.TEXT_SECONDARY, width=120, anchor="w", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"))
        self.lbl_title.pack(side="left", padx=10, fill="x", expand=True)
        self.lbl_title.bind("<ButtonPress-1>", self.start_move)
        self.lbl_title.bind("<B1-Motion>", self.do_move)

        # Close Button (X)
        self.btn_close = ctk.CTkButton(self.header, text="✕", width=28, height=22,
                                       fg_color="transparent", hover_color="#c42b1c",
                                       text_color=gui.TEXT_SECONDARY,
                                       font=ctk.CTkFont(size=9),
                                       command=self.close_remote)
        self.btn_close.pack(side="right", padx=1, pady=1)

        # Minimize Button (_)
        self.btn_min = ctk.CTkButton(self.header, text="—", width=28, height=22,
                                     fg_color="transparent", hover_color=self.hover_color,
                                     text_color=gui.TEXT_SECONDARY,
                                     font=ctk.CTkFont(size=9),
                                     command=self.toggle_minimize)
        self.btn_min.pack(side="right", padx=1, pady=1)

        # Config Button (Left) - Uses Segoe MDL2 Assets (Windows Native Icons)
        # \uE713 = Settings Gear (Wireframe) | "Cardan" style
        if self.callback_open_conf:
            self.btn_conf = ctk.CTkButton(self.header, text="\uE713", width=28, height=22,
                                          fg_color="transparent", hover_color=self.hover_color,
                                          text_color=gui.TEXT_SECONDARY,
                                          font=ctk.CTkFont(family="Segoe MDL2 Assets", size=10),
                                          command=self.callback_open_conf)
            self.btn_conf.pack(side="left", padx=1, pady=1)

        # Web Button (Left) - Uses Segoe MDL2 Assets
        # \uE12B = World/Globe (Windows style)
        if self.callback_open_web:
            self.btn_web = ctk.CTkButton(self.header, text="\uE12B", width=28, height=22,
                                         fg_color="transparent", hover_color=self.hover_color,
                                         text_color=gui.TEXT_SECONDARY,
                                         font=ctk.CTkFont(family="Segoe MDL2 Assets", size=10),
                                         command=self.callback_open_web)
            self.btn_web.pack(side="left", padx=1, pady=1)

        # --- Main Container (Holds Content) ---
        self.main_container = ctk.CTkFrame(self.main_border_frame, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=2, pady=2)

        # --- Content (Grid of Buttons) ---
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(side="top", fill="both", expand=True, padx=4, pady=4)

        # Instantiate Component
        self.pedalboard_frame = CompactPedalboardFrame(self.content_frame, self.device_def, self.profile, self.on_btn_click)
        self.pedalboard_frame.pack(fill="both", expand=True)

    def update_layout(self):
        # Just resize window logic, frame handles buttons
        self.update_idletasks()
        
        w = self.content_frame.winfo_reqwidth() + 20
        h = self.content_frame.winfo_reqheight() + 40 # + header

        # Clamp min size
        w = max(200, w)
        h = max(100, h)

        # Center on screen if first launch, else keep position
        if "+" not in self.geometry():
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            x = (screen_w // 2) - (w // 2)
            y = (screen_h // 2) - (h // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        else:
            # Just resize, keep x/y
            curr_x = self.winfo_x()
            curr_y = self.winfo_y()
            self.geometry(f"{w}x{h}+{curr_x}+{curr_y}")

    def on_btn_click(self, cc):
        # Flash visual effect could be added here
        self.callback_press(cc)

    def flash_button(self, cc):
        """Delegates flash to the frame"""
        if self.pedalboard_frame:
            self.pedalboard_frame.flash_button(cc)

    def toggle_minimize(self):
        """Minimizes to Taskbar (Standard Behavior)"""
        # To minimize a frameless window (overrideredirect), we must temporarily enable the frame
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self.on_restore)

    def on_restore(self, event):
        """Restores frameless state when opened from Taskbar"""
        if self.state() == "normal":
            self.overrideredirect(True)
            self.unbind("<Map>")

    def set_profile(self, new_profile):
        if not new_profile: return
        # Check if changed (by name)
        current_name = self.profile.get("name") if self.profile else ""
        new_name = new_profile.get("name")
        print(f"[REMOTE DEBUG] set_profile called with: {new_name}")
        
        if current_name != new_name:
            print(f"[REMOTE DEBUG] Applying profile change: {current_name} -> {new_name}")
            self.profile = new_profile
            self.pedalboard_frame.set_profile(new_profile)

            # Update Title
            title_text = f"{self._('gui.lbl_remote_prefix')} - {new_name}"
            if len(title_text) > 25: title_text = title_text[:25] + "..."
            self.lbl_title.configure(text=title_text)

            self.update_layout()

    def close_remote(self):
        self.callback_close()
        self.destroy()
