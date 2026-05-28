import customtkinter as ctk
import logging
import json
import os
import sys
import time
import threading
import datetime
import pygetwindow as gw
import keyboard
import mido
import pystray
import webbrowser
from PIL import Image
from utils import get_app_dir, get_data_dir
def get_resource_path(relative_path):
    """Trouve les fichiers aussi bien en Dev qu'en EXE PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# CORRECTION : On pointe vers assets/icon.png, pas juste icon.png
ICON_PNG_PATH = get_resource_path(os.path.join("assets", "icon.png"))
LOGO_PATH = get_resource_path(os.path.join("assets", "logo.png"))

try:
    from profile_manager import ProfileManager
    from device_manager import DeviceManager, DEFAULT_AIRSTEP_DEF
    from env_manager import EnvManager
    from midi_engine import MidiManager
    from action_handler import ActionHandler
    from library_manager import LibraryManager
    from config_manager import ConfigManager
    from remote_gui import RemoteControl, CompactPedalboardFrame
    
    # ContextMonitor Import with specific debug
    try:
        from context_monitor import ContextMonitor
    except ImportError as e:
        # If this fails in frozen app, it's fatal if fallback also fails. 
        # But we let it bubble to outer except for now, 
        # assuming --hidden-import fixed the missing file.
        raise e

except ImportError:
    from src.profile_manager import ProfileManager
    from src.device_manager import DeviceManager, DEFAULT_AIRSTEP_DEF
    from src.env_manager import EnvManager
    from src.midi_engine import MidiManager
    from src.action_handler import ActionHandler
    from src.library_manager import LibraryManager
    from src.remote_gui import RemoteControl, CompactPedalboardFrame
    from src.context_monitor import ContextMonitor

from i18n import _

# Configuration de l'apparence
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- SYSTÈME DE THÈMES DYNAMIQUES ET UNIFIÉS (SKINS) ---
THEMES = {
    "steel_blue": {
        "BG_COLOR": "#0B0F19",
        "CARD_BG": "#131B2E",
        "BORDER_COLOR": "#223154",
        "ACCENT_COLOR": "#3B82F6",      # Bleu acier technologique
        "ACCENT_HOVER": "#2563EB",
        "ACCENT_LIGHT": "#60A5FA",
        "BTN_SECONDARY": "#1E293B",
        "BTN_SECONDARY_HOVER": "#334155",
        "TEXT_PRIMARY": "#F9FAFB",
        "TEXT_SECONDARY": "#9CA3AF",
        "LCD_BG": "#070A13",
        "LCD_TEXT": "#10B981",
        "LED_CONNECTED": "#10B981",
        "LED_DISCONNECTED": "#EF4444",
        "LED_OFF": "#2B3B60"
    },
    "amethyst": {
        "BG_COLOR": "#0B0F19",
        "CARD_BG": "#131B2E",
        "BORDER_COLOR": "#223154",
        "ACCENT_COLOR": "#8B5CF6",      # Violet améthyste
        "ACCENT_HOVER": "#7C3AED",
        "ACCENT_LIGHT": "#A78BFA",
        "BTN_SECONDARY": "#1E293B",
        "BTN_SECONDARY_HOVER": "#334155",
        "TEXT_PRIMARY": "#F9FAFB",
        "TEXT_SECONDARY": "#9CA3AF",
        "LCD_BG": "#070A13",
        "LCD_TEXT": "#10B981",
        "LED_CONNECTED": "#10B981",
        "LED_DISCONNECTED": "#EF4444",
        "LED_OFF": "#2B3B60"
    },
    "emerald": {
        "BG_COLOR": "#0B0F19",
        "CARD_BG": "#131B2E",
        "BORDER_COLOR": "#223154",
        "ACCENT_COLOR": "#10B981",      # Vert émeraude
        "ACCENT_HOVER": "#059669",
        "ACCENT_LIGHT": "#34D399",
        "BTN_SECONDARY": "#1E293B",
        "BTN_SECONDARY_HOVER": "#334155",
        "TEXT_PRIMARY": "#F9FAFB",
        "TEXT_SECONDARY": "#9CA3AF",
        "LCD_BG": "#070A13",
        "LCD_TEXT": "#10B981",
        "LED_CONNECTED": "#10B981",
        "LED_DISCONNECTED": "#EF4444",
        "LED_OFF": "#2B3B60"
    },
    "amber": {
        "BG_COLOR": "#0B0F19",
        "CARD_BG": "#131B2E",
        "BORDER_COLOR": "#223154",
        "ACCENT_COLOR": "#F59E0B",      # Ambre/Orange
        "ACCENT_HOVER": "#D97706",
        "ACCENT_LIGHT": "#FBBF24",
        "BTN_SECONDARY": "#1E293B",
        "BTN_SECONDARY_HOVER": "#334155",
        "TEXT_PRIMARY": "#F9FAFB",
        "TEXT_SECONDARY": "#9CA3AF",
        "LCD_BG": "#070A13",
        "LCD_TEXT": "#10B981",
        "LED_CONNECTED": "#10B981",
        "LED_DISCONNECTED": "#EF4444",
        "LED_OFF": "#2B3B60"
    }
}

try:
    from config_manager import ConfigManager
    cm = ConfigManager()
    active_theme = cm.get("theme", "steel_blue")
except Exception:
    active_theme = "steel_blue"

if active_theme not in THEMES:
    active_theme = "steel_blue"

theme_colors = THEMES[active_theme]
BG_COLOR = theme_colors["BG_COLOR"]
CARD_BG = theme_colors["CARD_BG"]
BORDER_COLOR = theme_colors["BORDER_COLOR"]
ACCENT_COLOR = theme_colors["ACCENT_COLOR"]
ACCENT_HOVER = theme_colors["ACCENT_HOVER"]
ACCENT_LIGHT = theme_colors["ACCENT_LIGHT"]
BTN_SECONDARY = theme_colors["BTN_SECONDARY"]
BTN_SECONDARY_HOVER = theme_colors["BTN_SECONDARY_HOVER"]
TEXT_PRIMARY = theme_colors["TEXT_PRIMARY"]
TEXT_SECONDARY = theme_colors["TEXT_SECONDARY"]
LCD_BG = theme_colors["LCD_BG"]
LCD_TEXT = theme_colors["LCD_TEXT"]
LED_CONNECTED = theme_colors["LED_CONNECTED"]
LED_DISCONNECTED = theme_colors["LED_DISCONNECTED"]
LED_OFF = theme_colors["LED_OFF"]

class CTkMessageBox(ctk.CTkToplevel):
    def __init__(self, title=_("gui.msg_title"), message="", icon="info", option_text_1=_("gui.btn_ok"), option_text_2=None):
        super().__init__()
        self.title(title)
        self.geometry("400x200")
        self.configure(fg_color=BG_COLOR)
        self.attributes("-topmost", True)

        self.update_idletasks()
        try:
            x = (self.winfo_screenwidth() // 2) - (400 // 2)
            y = (self.winfo_screenheight() // 2) - (200 // 2)
            self.geometry(f"+{x}+{y}")
        except: pass

        self.result = None

        self.label = ctk.CTkLabel(self, text=message, wraplength=350, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12))
        self.label.pack(pady=30, padx=20, fill="both", expand=True)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=20)

        if option_text_2:
            self.btn2 = ctk.CTkButton(self.btn_frame, text=option_text_2, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11), command=lambda: self.on_click(False))
            self.btn2.pack(side="left", padx=10)

        self.btn1 = ctk.CTkButton(self.btn_frame, text=option_text_1, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=lambda: self.on_click(True))
        self.btn1.pack(side="left", padx=10)

        self.grab_set()
        self.wait_window()

    def on_click(self, value):
        self.result = value
        self.destroy()

    @staticmethod
    def show_info(title, message):
        CTkMessageBox(title, message, option_text_1="OK")

    @staticmethod
    def show_error(title, message):
        CTkMessageBox(title, message, option_text_1="OK")

    @staticmethod
    def ask_yes_no(title, message):
        msg = CTkMessageBox(title, message, option_text_1=_("gui.btn_yes"), option_text_2=_("gui.btn_no"))
        return msg.result

class ShortcutsDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_text, callback):
        super().__init__(parent)
        self.callback = callback
        self.title(_("gui.title_shortcuts"))
        self.geometry("600x600")
        self.configure(fg_color=BG_COLOR)
        self.attributes("-topmost", True)

        self.textbox = ctk.CTkTextbox(self, fg_color=CARD_BG, border_color=BORDER_COLOR, border_width=1, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox.pack(fill="both", expand=True, padx=20, pady=20)
        self.textbox.insert("0.0", initial_text)

        self.btn_save = ctk.CTkButton(self, text=_("gui.btn_save"), fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.save)
        self.btn_save.pack(pady=(0, 20), padx=20, fill="x")

    def save(self):
        text = self.textbox.get("0.0", "end").strip()
        self.callback(text)
        self.destroy()

class SyncConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, parent, analysis_result, callback):
        super().__init__(parent)
        self.title("Récapitulatif de Synchronisation")
        self.geometry("950x850")
        self.configure(fg_color=BG_COLOR)
        self.attributes("-topmost", True)
        self.callback = callback
        self.vars = {"pull": [], "push": [], "delete_remote": [], "delete_local": []}
        self.section_cbs = {} # Global checkboxes
        
        # Handle close window (X button)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.grab_set()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR, corner_radius=8)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.scroll, text="Vérifiez les actions avant de lancer la synchronisation :", 
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(pady=10)

        # Build sections
        self._add_section("📥 Téléchargements (Cloud ➔ PC)", analysis_result.get("pull", []), "pull", "#10B981", default=True)
        self._add_section("📤 Envois (PC ➔ Cloud)", analysis_result.get("push", []), "push", "#8B5CF6", default=True)
        self._add_section("🗑️ Suppressions sur le Cloud (Cloud ❌)", analysis_result.get("delete_remote", []), "delete_remote", "#EF4444", default=False)
        self._add_section("🗑️ Suppressions sur ce PC (PC ❌)", analysis_result.get("delete_local", []), "delete_local", "#EF4444", default=False)

        # Execution Section
        ctk.CTkLabel(self, text="Progression & Logs", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(pady=(10, 5))
        self.progress_bar = ctk.CTkProgressBar(self, width=800, progress_color=ACCENT_COLOR, fg_color=BORDER_COLOR)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)
        
        self.log_box = ctk.CTkTextbox(self, height=180, font=ctk.CTkFont(family="Consolas", size=11), fg_color=LCD_BG, border_color=BORDER_COLOR, border_width=1, text_color=LCD_TEXT)
        self.log_box.pack(fill="both", expand=True, padx=20, pady=5)
        self.log_box.configure(state="disabled")

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", side="bottom", pady=20, padx=20)
        
        self.btn_sync = ctk.CTkButton(self.btn_frame, text="Lancer la Synchronisation", fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.on_sync)
        self.btn_sync.pack(side="right", padx=10)
        
        self.btn_cancel = ctk.CTkButton(self.btn_frame, text="Fermer / Annuler", fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12), command=self.on_cancel)
        self.btn_cancel.pack(side="right", padx=10)

    def on_cancel(self):
        self.callback(None)
        self.destroy()

    def log_msg(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _add_section(self, title, items, key, color, default=True):
        if not items: return
        
        header_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=(15, 5))
        
        ctk.CTkLabel(header_frame, text=title, font=ctk.CTkFont(family="Segoe UI", weight="bold", size=13), text_color=color).pack(side="left")
        
        # Select All checkbox
        toggle_var = ctk.BooleanVar(value=default)
        cb_all = ctk.CTkCheckBox(header_frame, text="Tout sélectionner", font=ctk.CTkFont(family="Segoe UI", size=11), 
                                 variable=toggle_var, command=lambda k=key, v=toggle_var: self._toggle_all(k, v),
                                 fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color=TEXT_SECONDARY)
        cb_all.pack(side="right", padx=10)
        self.section_cbs[key] = (cb_all, toggle_var)
        
        # Direction mapping
        dir_map = {
            "pull": "Cloud ➔ PC",
            "push": "PC ➔ Cloud",
            "delete_remote": "Cloud ❌",
            "delete_local": "PC ❌"
        }
        direction = dir_map.get(key, "")
        
        for item in items:
            path = item["path"] if isinstance(item, dict) else item
            reason = item.get("reason", "") if isinstance(item, dict) else ""
            
            display_text = f"{direction} : {path}"
            if reason: display_text += f" ({reason})"
            
            var = ctk.BooleanVar(value=default)
            cb = ctk.CTkCheckBox(self.scroll, text=display_text, variable=var, font=ctk.CTkFont(family="Segoe UI", size=11),
                                 fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY)
            cb.pack(anchor="w", padx=20, pady=2)
            self.vars[key].append((item, var))

    def _toggle_all(self, key, master_var):
        val = master_var.get()
        for item, var in self.vars[key]:
            var.set(val)

    def on_sync(self):
        self.btn_sync.configure(state="disabled")
        self.btn_cancel.configure(state="disabled")
        final_res = {
            "pull": [i for i, v in self.vars["pull"] if v.get()],
            "push": [i for i, v in self.vars["push"] if v.get()],
            "delete_remote": [i for i, v in self.vars["delete_remote"] if v.get()],
            "delete_local": [i for i, v in self.vars["delete_local"] if v.get()]
        }
        self.callback(final_res)
        # We DON'T destroy yet, as we want to see logs. 
        # run_sync will re-enable the cancel button at the end.

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, profile_manager, action_handler, env_manager, midi_manager):
        super().__init__(parent)
        self.title(_("gui.tab_settings"))
        self.geometry("450x510")
        self.configure(fg_color=BG_COLOR)
        self.attributes("-topmost", True)
        self.profile_manager = profile_manager
        self.action_handler = action_handler
        self.env_manager = env_manager
        self.midi_manager = midi_manager

        try:
            self.tabview = ctk.CTkTabview(self, fg_color=BG_COLOR,
                                          segmented_button_fg_color=CARD_BG,
                                          segmented_button_selected_color=ACCENT_COLOR,
                                          segmented_button_selected_hover_color=ACCENT_HOVER,
                                          segmented_button_unselected_color=BTN_SECONDARY,
                                          segmented_button_unselected_hover_color=BTN_SECONDARY_HOVER,
                                          text_color=TEXT_PRIMARY)
            self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
            self.tabview.add(_("web.tab_general"))
            self.tabview.add(_("gui.tab_backup"))

            # Tab General
            tab_gen = self.tabview.tab(_("web.tab_general"))
            ctk.CTkLabel(tab_gen, text=_("gui.lbl_debounce"), text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(pady=(20, 5))

            current_val = action_handler.debounce_delay if action_handler else 0.15
            self.lbl_debounce = ctk.CTkLabel(tab_gen, text=f"{int(current_val * 1000)} ms", text_color=ACCENT_LIGHT, font=ctk.CTkFont(family="Consolas", size=14, weight="bold"))
            self.lbl_debounce.pack()

            self.slider = ctk.CTkSlider(tab_gen, from_=0, to=1000, number_of_steps=100, command=self.update_label,
                                        button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER, progress_color=ACCENT_COLOR, fg_color=BORDER_COLOR)
            self.slider.set(current_val * 1000)
            self.slider.pack(pady=10, padx=20, fill="x")

            ctk.CTkLabel(tab_gen, text=_("gui.lbl_debounce_hint"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=10)).pack()

            # Language Selector
            ctk.CTkLabel(tab_gen, text=_("gui.lbl_lang"), text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(pady=(10, 2))
            from config_manager import ConfigManager
            cm = ConfigManager()
            current_lang = cm.get("language", "fr")
            self.lang_combo = ctk.CTkComboBox(tab_gen, values=["fr", "en"], command=self.update_lang, state="readonly",
                                              fg_color=CARD_BG, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                              dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY)
            self.lang_combo.set(current_lang)
            self.lang_combo.pack(pady=2)

            # Theme Selector
            ctk.CTkLabel(tab_gen, text=_("gui.lbl_theme"), text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(pady=(10, 2))
            current_theme = cm.get("theme", "steel_blue")
            self.theme_combo = ctk.CTkComboBox(tab_gen, values=["steel_blue", "amethyst", "emerald", "amber"], command=self.update_theme, state="readonly",
                                               fg_color=CARD_BG, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                               dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY)
            self.theme_combo.set(current_theme)
            self.theme_combo.pack(pady=2)

            ctk.CTkLabel(tab_gen, text=_("gui.lbl_restart_hint"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=10)).pack(pady=(5, 0))

            # Tab Backup
            tab_backup = self.tabview.tab(_("gui.tab_backup"))
            ctk.CTkButton(tab_backup, text=_("gui.btn_export_conf"), fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12), command=self.export_conf).pack(pady=20, padx=20, fill="x")
            ctk.CTkButton(tab_backup, text=_("gui.btn_import_conf"), fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12), command=self.import_conf).pack(pady=10, padx=20, fill="x")

            # Force set tab
            self.tabview.set(_("web.tab_general"))

            # Tab MIDI Output
            tab_midi = self.tabview.add(_("gui.lbl_midi_out"))
            ctk.CTkLabel(tab_midi, text=_("gui.lbl_midi_out"), text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(pady=(20, 5))
            
            self.midi_checkboxes = []
            self.scroll_midi = ctk.CTkScrollableFrame(tab_midi, width=300, height=200, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR, corner_radius=6)
            self.scroll_midi.pack(pady=5, fill="both", expand=True)
            
            # Get Status (Available + Missing Configured)
            ports_status = self.midi_manager.get_ports_status()
            
            if not ports_status:
                ctk.CTkLabel(self.scroll_midi, text=_("gui.lbl_no_midi"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=12)).pack()
            
            for p in ports_status:
                name = p["name"]
                is_selected = p["selected"]
                is_connected = p["connected"]
                is_available = p["available"]
                
                # Label text logic
                lbl_text = name
                text_color = TEXT_PRIMARY # default
                
                if not is_available:
                    lbl_text += f" ({_('gui.lbl_absent')})"
                    text_color = "orange"
                elif is_selected and not is_connected:
                    lbl_text += f" ({_('gui.lbl_error')})"
                    text_color = "#EF4444"
                
                chk = ctk.CTkCheckBox(self.scroll_midi, text=lbl_text, text_color=text_color,
                                     fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER)
                if is_selected:
                    chk.select()
                
                chk.pack(anchor="w", pady=4, padx=10)
                # Store (checkbox_widget, port_name)
                self.midi_checkboxes.append((chk, name))

            ctk.CTkButton(tab_midi, text=_("gui.btn_apply"), fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.save_midi_out).pack(pady=20)
            ctk.CTkLabel(tab_midi, text=_("gui.lbl_midi_multi_hint"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=10)).pack()

        except Exception as e:
            # log_debug handles the error silently or we just pass
            # with open("debug.log", "a") as f:
            #     import traceback
            #     f.write(f"SETTINGS ERROR: {e}\n{traceback.format_exc()}\n")
            CTkMessageBox.show_error(_("gui.msg_error"), f"{_('gui.msg_settings_error')}\n{e}")

    def save_midi_out(self):
        selected_ports = []
        for chk, name in self.midi_checkboxes:
            if chk.get() == 1:
                selected_ports.append(name)
        
        # Apply to Engine
        self.midi_manager.set_output_ports(selected_ports)
        
        # Persist to Config
        try:
            self.master.settings["midi_output_names"] = selected_ports
            cm = ConfigManager()
            cm.set("midi_output_names", selected_ports)
            
            # Legacy cleanup: clear single port config to avoid confusion? 
            # Or just leave it. Let's leave it.
            CTkMessageBox.show_info(_("gui.msg_info"), f"{_('gui.msg_ports_active')} : {len(selected_ports)}\n {_('gui.msg_saved')}")
        except Exception as e:
            CTkMessageBox.show_error(_("gui.msg_save_error"), str(e))

    def update_label(self, value):
        self.lbl_debounce.configure(text=f"{int(value)} ms")
        if self.action_handler:
            self.action_handler.set_debounce_delay(value / 1000.0)

    def update_lang(self, value):
        from config_manager import ConfigManager
        cm = ConfigManager()
        cm.set("language", value)
        CTkMessageBox.show_info(_("gui.msg_lang_changed_title"), _("gui.msg_lang_changed_text"))

    def update_theme(self, value):
        from config_manager import ConfigManager
        cm = ConfigManager()
        cm.set("theme", value)
        CTkMessageBox.show_info(_("gui.msg_theme_changed_title"), _("gui.msg_theme_changed_text"))

    def export_conf(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[(_("gui.filetype_zip"), "*.zip")])
        if path:
            ok, msg = self.profile_manager.export_backup(path)
            if ok: CTkMessageBox.show_info(_("gui.msg_success"), _("gui.msg_export_success"))
            else: CTkMessageBox.show_error(_("gui.msg_error"), msg)

    def import_conf(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[(_("gui.filetype_zip"), "*.zip")])
        if path:
            if CTkMessageBox.ask_yes_no(_("gui.msg_warning"), _("gui.msg_import_confirm")):
                ok, msg = self.profile_manager.import_backup(path)
                if ok:
                    CTkMessageBox.show_info(_("gui.msg_success"), _("gui.msg_import_success"))
                else:
                    CTkMessageBox.show_error(_("gui.msg_error"), msg)

class DeviceEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, manager, current_def=None, callback=None):
        super().__init__(parent)
        self.parent = parent
        self.manager = manager
        self.callback = callback
        
        self.transient(parent)
        self.grab_set()
        
        # Style & Design: Sticky Footer Layout
        self.title(_("gui.title_device_editor", default="Éditeur de télécommande"))
        self.geometry("620x750")
        self.configure(fg_color=BG_COLOR)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.lift()
        self.focus_force()
        
        self.definition = current_def if current_def else {"name": "", "buttons": []}
        
        # Initialisation des variables d'état
        self.device_name = self.definition.get("name", "")
        
        # Migration rétrocompatible si l'ancien profil était simple (USB ou BLE)
        self.physical_devices = self.definition.get("physical_devices", [])
        if not self.physical_devices:
            conn_type = self.definition.get("connection_type", "Virtuel")
            midi_port = self.definition.get("midi_port", "")
            if conn_type in ("USB", "BLE") and midi_port:
                self.physical_devices = [{"type": conn_type, "name": midi_port}]
                
        self.buttons = self.definition.get("buttons", [])
        self.key_rows = []
        
        # Variable du scan physique
        self.last_scanned_ports = []
        self.scanner_running = True
        self.checkbox_vars = {}
        
        # Sticky Footer Layout
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Body
        self.grid_rowconfigure(2, weight=0)  # Footer
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color=CARD_BG, height=70, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="nsew")
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_rowconfigure(0, weight=1)
        
        self.lbl_step_title = ctk.CTkLabel(self.header_frame, text=_("gui.title_device_editor", default="Éditeur de télécommande"), text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"))
        self.lbl_step_title.grid(row=0, column=0, pady=20, padx=20, sticky="w")
        
        # 2. Body Container (Scrollable Frame unique pour tout le contenu)
        self.body_container = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.body_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # 3. Footer Frame
        self.footer_frame = ctk.CTkFrame(self, fg_color=CARD_BG, height=60, corner_radius=0)
        self.footer_frame.grid(row=2, column=0, sticky="nsew")
        self.footer_frame.grid_propagate(False)
        
        self.btn_cancel = ctk.CTkButton(self.footer_frame, text=_("gui.btn_cancel"), width=100, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.close_and_stop)
        self.btn_cancel.pack(side="left", padx=20, pady=15)
        
        self.btn_save = ctk.CTkButton(self.footer_frame, text=_("gui.btn_save"), width=100, fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.save)
        self.btn_save.pack(side="right", padx=20, pady=15)
        
        # Dessiner le contenu statique
        self.draw_ui_content()
        
        # Launch Scan Thread
        import threading
        self.scan_thread = threading.Thread(target=self._background_scan, daemon=True)
        self.scan_thread.start()
        
        # Clean protocol on window close
        self.protocol("WM_DELETE_WINDOW", self.close_and_stop)

    def close_and_stop(self):
        self.scanner_running = False
        self.destroy()

    def _background_scan(self):
        import time
        import asyncio
        
        midi_mgr = None
        if hasattr(self, 'parent') and hasattr(self.parent, 'parent') and hasattr(self.parent.parent, 'midi_manager'):
            midi_mgr = self.parent.parent.midi_manager
            
        has_active_ble_provider = False
        if midi_mgr:
            try:
                from midi_engine import BleakProvider
                active_ble_provs = [p for p in midi_mgr.active_providers if isinstance(p, BleakProvider)]
                if active_ble_provs:
                    has_active_ble_provider = True
                    print(f"[WIZARD SCAN] Détection d'un BleakProvider principal actif ({len(active_ble_provs)}). Réutilisation du scan en cours.")
            except Exception as e:
                print(f"[WIZARD SCAN] Erreur détection provider BLE: {e}")
                
        if not has_active_ble_provider:
            print("[WIZARD SCAN] Démarrage du scan BLE autonome robuste (event loop persistante)...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def scan_loop_async():
                from bleak import BleakScanner
                import mido
                
                scanner = None
                try:
                    scanner = BleakScanner()
                except Exception as e:
                    print(f"[WIZARD SCAN] Impossible d'initialiser BleakScanner: {e}")
                    
                while self.scanner_running:
                    try:
                        usb_ports = mido.get_input_names()
                    except Exception as e:
                        print(f"[WIZARD SCAN] Erreur scan USB: {e}")
                        usb_ports = []
                        
                    ble_ports = []
                    if scanner:
                        try:
                            devices = await scanner.discover(timeout=2.0)
                            ble_ports = [d.name for d in devices if d.name]
                        except Exception as e:
                            print(f"[WIZARD SCAN] Erreur scan BLE autonome: {e}")
                            
                    scanned = []
                    for p in usb_ports:
                        if p not in scanned:
                            scanned.append({"name": p, "type": "USB"})
                    for p in ble_ports:
                        if not any(x["name"] == p for x in scanned):
                            scanned.append({"name": p, "type": "BLE"})
                            
                    if scanned != self.last_scanned_ports:
                        self.last_scanned_ports = scanned
                        if self.scanner_running:
                            self.after(0, self.update_scanned_ports_ui)
                            
                    await asyncio.sleep(2.0)
                    
            try:
                loop.run_until_complete(scan_loop_async())
            except Exception as e:
                print(f"[WIZARD SCAN] Échec de la boucle asynchrone autonome: {e}")
            finally:
                loop.close()
                
        else:
            print("[WIZARD SCAN] Utilisation du scan passif via le BleakProvider principal...")
            import mido
            loop_count = 0
            while self.scanner_running:
                if midi_mgr and (loop_count % 4 == 0):
                    try:
                        midi_mgr.force_rescan()
                    except Exception as e:
                        print(f"[WIZARD SCAN] Erreur lors du force_rescan: {e}")
                        
                try:
                    usb_ports = mido.get_input_names()
                except:
                    usb_ports = []
                    
                ble_ports = []
                if midi_mgr:
                    try:
                        ble_ports = list(midi_mgr.get_ports())
                    except Exception as e:
                        print(f"[WIZARD SCAN] Erreur lecture ports passifs: {e}")
                        
                scanned = []
                for p in usb_ports:
                    if p not in scanned:
                        scanned.append({"name": p, "type": "USB"})
                for p in ble_ports:
                    if not any(x["name"] == p for x in scanned):
                        scanned.append({"name": p, "type": "BLE"})
                        
                if scanned != self.last_scanned_ports:
                    self.last_scanned_ports = scanned
                    if self.scanner_running:
                        self.after(0, self.update_scanned_ports_ui)
                        
                time.sleep(2.0)
                loop_count += 1

    def draw_ui_content(self):
        # 1. Champ de nom de la télécommande
        lbl_name = ctk.CTkLabel(self.body_container, text=_("gui.lbl_model_name", default="Nom du modèle :"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        lbl_name.pack(pady=(10, 2), padx=10, anchor="w")
        self.entry_name = ctk.CTkEntry(self.body_container, fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12))
        self.entry_name.pack(pady=(0, 15), padx=10, fill="x")
        self.entry_name.insert(0, self.device_name)
        
        # 2. Section des périphériques physiques
        lbl_ports = ctk.CTkLabel(self.body_container, text=_("gui.wizard_lbl_ports", default="Périphériques physiques à agréger (laisser vide si virtuel uniquement) :"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        lbl_ports.pack(pady=(5, 2), padx=10, anchor="w")
        
        self.ports_container = ctk.CTkFrame(self.body_container, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR, corner_radius=8)
        self.ports_container.pack(pady=(0, 15), padx=10, fill="x")
        
        self.update_scanned_ports_ui()
        
        # 3. Section de la liste des touches
        lbl_keys = ctk.CTkLabel(self.body_container, text=_("gui.lbl_buttons_list", default="Grille des touches de contrôle :"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        lbl_keys.pack(pady=(10, 2), padx=10, anchor="w")
        
        btn_add = ctk.CTkButton(self.body_container, text=f"+ {_('gui.btn_add_button', default='Ajouter Bouton')}", fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=lambda: self.draw_key_row("", "", ""))
        btn_add.pack(pady=(0, 10), padx=10, anchor="w")
        
        self.keys_container = ctk.CTkFrame(self.body_container, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR, corner_radius=8)
        self.keys_container.pack(pady=(0, 10), padx=10, fill="x")

        # Ligne d'en-têtes de colonnes stylisée
        header_row = ctk.CTkFrame(self.keys_container, fg_color="transparent")
        header_row.pack(fill="x", pady=(8, 4), padx=10)
        
        lbl_h_type = ctk.CTkLabel(header_row, text=_("gui.col_h_type", default="Type"), width=80, text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), anchor="w")
        lbl_h_type.pack(side="left", padx=5)
        
        lbl_h_cc = ctk.CTkLabel(header_row, text=_("gui.col_h_cc", default="Code CC"), width=50, text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), anchor="w")
        lbl_h_cc.pack(side="left", padx=5)
        
        lbl_h_chan = ctk.CTkLabel(header_row, text=_("gui.col_h_chan", default="Canal"), width=70, text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), anchor="w")
        lbl_h_chan.pack(side="left", padx=5)
        
        lbl_h_short = ctk.CTkLabel(header_row, text=_("gui.col_h_short", default="Label Court"), width=60, text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), anchor="w")
        lbl_h_short.pack(side="left", padx=5)
        
        lbl_h_desc = ctk.CTkLabel(header_row, text=_("gui.col_h_desc", default="Description complète du Bouton"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), anchor="w")
        lbl_h_desc.pack(side="left", fill="x", expand=True, padx=5)
        
        # Subtle horizontal separator under headers
        h_sep = ctk.CTkFrame(self.keys_container, height=1, fg_color=BORDER_COLOR)
        h_sep.pack(fill="x", padx=10, pady=(2, 6))
        
        for btn in self.buttons:
            self.draw_key_row(
                cc=btn.get("cc", ""), 
                label=btn.get("label", ""), 
                short_label=btn.get("short_label", ""), 
                is_virt=btn.get("is_virtual", btn.get("cc", 0) < 0),
                midi_channel=btn.get("midi_channel", 16)
            )

    def update_scanned_ports_ui(self):
        if not hasattr(self, "ports_container") or not self.ports_container.winfo_exists():
            return
            
        for w in self.ports_container.winfo_children():
            w.destroy()
            
        all_display_ports = list(self.last_scanned_ports)
        for dev in self.physical_devices:
            if not any(x["name"] == dev["name"] for x in all_display_ports):
                all_display_ports.append({"name": dev["name"], "type": dev["type"], "absent": True})
                
        if not all_display_ports:
            lbl_empty = ctk.CTkLabel(self.ports_container, text=_("gui.msg_no_device_found"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=11))
            lbl_empty.pack(pady=20)
            return
            
        for p in all_display_ports:
            row = ctk.CTkFrame(self.ports_container, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=10)
            
            p_name = p["name"]
            p_type = p["type"]
            is_absent = p.get("absent", False)
            
            if p_name not in self.checkbox_vars:
                var = ctk.BooleanVar(value=any(x["name"] == p_name for x in self.physical_devices))
                self.checkbox_vars[p_name] = (var, p_type)
            else:
                var = self.checkbox_vars[p_name][0]
                
            def on_checkbox_toggled(n=p_name, v=var, t=p_type):
                if v.get():
                    if not any(x["name"] == n for x in self.physical_devices):
                        self.physical_devices.append({"type": t, "name": n})
                else:
                    self.physical_devices = [x for x in self.physical_devices if x["name"] != n]
            
            chk = ctk.CTkCheckBox(row, text=p_name, variable=var, font=ctk.CTkFont(family="Segoe UI", size=11), fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, command=on_checkbox_toggled)
            chk.pack(side="left", padx=5)
            
            lbl_badge = ctk.CTkLabel(row, text=f" [{p_type}] ", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color="#00E5FF" if p_type == "BLE" else TEXT_SECONDARY)
            lbl_badge.pack(side="right", padx=5)
            
            if is_absent:
                lbl_badge.configure(text=f" [{p_type} - {_('gui.lbl_absent', default='Absent')}] ", text_color="#EF4444")

    def draw_key_row(self, cc, label, short_label="", is_virt=False, midi_channel=16):
        if not hasattr(self, "keys_container") or not self.keys_container.winfo_exists():
            return
            
        row = ctk.CTkFrame(self.keys_container, fg_color="transparent")
        row.pack(fill="x", pady=4, padx=10)
        
        row_state = {
            "widget": row,
            "is_virtual": is_virt,
            "orig_cc": cc
        }
        
        e_cc = ctk.CTkEntry(row, width=50, placeholder_text=_("gui.placeholder_cc"), fg_color=BG_COLOR, border_color=BORDER_COLOR, font=ctk.CTkFont(family="Consolas", size=11))
        
        # ComboBox pour le canal MIDI d'entrée
        combo_ch = ctk.CTkComboBox(row, width=70, fg_color=BG_COLOR, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                    dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY,
                                    font=ctk.CTkFont(family="Segoe UI", size=11))
        
        input_ch_values = [str(i) for i in range(1, 16)] + ["16"]
        combo_ch.configure(values=input_ch_values)
        combo_ch.set(str(midi_channel))
        
        def toggle_type(rs=row_state, entry=e_cc, cmb=combo_ch):
            if rs["is_virtual"]:
                rs["is_virtual"] = False
                btn_type.configure(text=_("gui.lbl_btn_physical", default="Physique"), text_color=TEXT_PRIMARY)
                entry.configure(state="normal", text_color=TEXT_PRIMARY)
                entry.delete(0, "end")
                cmb.configure(state="normal")
                
                if isinstance(rs["orig_cc"], int) and rs["orig_cc"] >= 0:
                    entry.insert(0, str(rs["orig_cc"]))
                else:
                    entry.insert(0, "")
            else:
                rs["is_virtual"] = True
                btn_type.configure(text=_("gui.lbl_btn_virtual"), text_color="#00E5FF")
                entry.delete(0, "end")
                entry.insert(0, _("gui.lbl_virtual"))
                entry.configure(state="disabled", text_color="#00E5FF")
                cmb.set("16")
                cmb.configure(state="disabled")
                
        btn_type = ctk.CTkButton(row, width=80, height=26, text="", fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), command=toggle_type)
        btn_type.pack(side="left", padx=5)
        row_state["btn_type"] = btn_type
        
        if is_virt:
            btn_type.configure(text=_("gui.lbl_btn_virtual"), text_color="#00E5FF")
            e_cc.insert(0, _("gui.lbl_virtual"))
            e_cc.configure(state="disabled", text_color="#00E5FF")
            combo_ch.set("16")
            combo_ch.configure(state="disabled")
        else:
            btn_type.configure(text=_("gui.lbl_btn_physical", default="Physique"), text_color=TEXT_PRIMARY)
            val_display = str(cc) if (cc != "" and cc is not None) else ""
            e_cc.insert(0, val_display)
            e_cc.configure(state="normal", text_color=TEXT_PRIMARY)
            combo_ch.configure(state="normal")
            
        e_cc.pack(side="left", padx=5)
        row_state["entry_cc"] = e_cc
        
        # Pack canal d'entrée juste à côté du CC
        combo_ch.pack(side="left", padx=5)
        row_state["combo_ch"] = combo_ch
        
        e_short = ctk.CTkEntry(row, width=60, placeholder_text=_("gui.placeholder_short_lbl"), fg_color=BG_COLOR, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11))
        e_short.insert(0, str(short_label))
        e_short.pack(side="left", padx=5)
        row_state["entry_short"] = e_short
        
        e_lbl = ctk.CTkEntry(row, placeholder_text=_("gui.placeholder_btn_name"), fg_color=BG_COLOR, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11))
        e_lbl.insert(0, str(label))
        e_lbl.pack(side="left", fill="x", expand=True, padx=5)
        row_state["entry_lbl"] = e_lbl
        
        def delete_key(rs=row_state):
            if rs in self.key_rows:
                self.key_rows.remove(rs)
            rs["widget"].destroy()
            
        btn_del = ctk.CTkButton(row, text="✕", width=30, height=26, fg_color="#EF4444", hover_color="#DC2626", text_color="#FFFFFF", font=ctk.CTkFont(size=10, weight="bold"), command=delete_key)
        btn_del.pack(side="right", padx=5)
        
        self.key_rows.append(row_state)

    def save(self):
        used_ccs = set()
        pending_rows = []
        
        for row in self.key_rows:
            is_virt = row["is_virtual"]
            orig_cc = row["orig_cc"]
            lbl = row["entry_lbl"].get().strip()
            
            if not lbl:
                CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_config_error", default="Le label complet du bouton ne peut pas être vide."))
                return
                
            if is_virt:
                if isinstance(orig_cc, int) and orig_cc < 0:
                    used_ccs.add(orig_cc)
                    pending_rows.append((row, orig_cc))
                else:
                    pending_rows.append((row, None))
            else:
                cc_str = row["entry_cc"].get().strip()
                if not cc_str:
                    CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_config_error", default="Veuillez spécifier un code CC pour tous les boutons physiques."))
                    return
                if not (cc_str.isdigit() or (cc_str.startswith("-") and cc_str[1:].isdigit())):
                    CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_config_error", default="Le code CC doit être un entier numérique valide."))
                    return
                cc = int(cc_str)
                if cc in used_ccs:
                    CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_config_error", default=f"Le code CC {cc} est assigné en double."))
                    return
                used_ccs.add(cc)
                pending_rows.append((row, cc))
                
        next_virtual = -1
        buttons_data = []
        
        for row, assigned_cc in pending_rows:
            lbl = row["entry_lbl"].get().strip()
            short_lbl = row["entry_short"].get().strip()
            is_virt = row["is_virtual"]
            
            final_cc = assigned_cc
            if final_cc is None:
                while next_virtual in used_ccs:
                    next_virtual -= 1
                final_cc = next_virtual
                used_ccs.add(final_cc)
                
            if not short_lbl:
                if "Long Press" in lbl:
                    base = lbl.replace("Long Press ", "").strip()
                    if "(" in base: base = base.split("(")[0].strip()
                    short_lbl = f"{base} (H)"
                else:
                    short = lbl.replace("Bouton ", "").replace("Button ", "").replace("Footswitch ", "")
                    if "(" in short: short = short.split("(")[0].strip()
                    short_lbl = short[:8]
                    
            # Extraction du canal MIDI d'entrée configuré
            in_ch = 16
            if "combo_ch" in row:
                try:
                    in_ch = int(row["combo_ch"].get())
                except:
                    pass

            buttons_data.append({
                "cc": final_cc,
                "short_label": short_lbl,
                "label": lbl,
                "is_virtual": is_virt,
                "midi_channel": in_ch
            })
            
        new_name = self.entry_name.get().strip() if hasattr(self, "entry_name") else self.device_name
        if not new_name:
            CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_device_name_empty"))
            return
            
        old_name = self.definition.get("name", "")
        if new_name.lower() != old_name.lower():
            if any(d.get("name", "").lower() == new_name.lower() for d in self.manager.definitions):
                CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_device_exists"))
                return
                
        data = {
            "name": new_name,
            "connection_type": "Composite",
            "physical_devices": self.physical_devices,
            "buttons": buttons_data
        }
        
        self.scanner_running = False
        
        if old_name and new_name.lower() != old_name.lower():
            self.manager.delete_definition(old_name)
            
        self.manager.save_definition(data)
        
        if self.callback:
            self.callback()
            
        self.destroy()


class ProfileEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_profile, callback):
        super().__init__(parent)
        self.callback = callback
        self.current_profile = current_profile

        # V10: Unified Create/Edit UI
        is_create = current_profile is None
        self.title(_("gui.title_new_profile") if is_create else _("gui.title_profile_editor"))
        self.geometry("380x320")
        self.configure(fg_color=BG_COLOR)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Name
        ctk.CTkLabel(self, text=_("gui.lbl_profile_full_name"), font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY).pack(pady=(15, 5), padx=20, anchor="w")
        self.entry_name = ctk.CTkEntry(self, width=340, fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12))
        self.entry_name.pack(padx=20)
        self.entry_name.insert(0, "" if is_create else current_profile.get("name", ""))

        # Master Vol Frame
        self.vol_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.vol_frame.pack(pady=(15, 5), padx=20, fill="x")
        
        # Label that will hold the percentage
        self.lbl_vol = ctk.CTkLabel(self.vol_frame, text=f"{_('gui.lbl_master_vol')} : 100%", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_vol.pack(anchor="w")
        
        # Slider
        self.slider_vol = ctk.CTkSlider(self.vol_frame, from_=0, to=100, number_of_steps=100, command=self.on_slider_change, progress_color=ACCENT_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER)
        self.slider_vol.pack(fill="x", pady=5)
        
        # Init value
        saved_vol = "" if is_create else current_profile.get("target_volume", "")
        if saved_vol:
            try:
                val = float(saved_vol)
            except: val = 100.0
        else:
            val = 100.0
            
        self.slider_vol.set(val)
        self.on_slider_change(val)

        # Associated Controller / Telecommande associee
        ctk.CTkLabel(self, text=_("gui.lbl_associated_device"), font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY).pack(pady=(15, 5), padx=20, anchor="w")
        
        none_lbl = _("gui.lbl_none")
        devices = [d.get("name") for d in parent.device_manager.definitions]
        device_values = [none_lbl] + devices
        
        self.combo_device = ctk.CTkComboBox(self, values=device_values, width=340, fg_color=CARD_BG, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER, dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY)
        self.combo_device.pack(padx=20)
        
        # Init value
        device_name = none_lbl
        if not is_create:
            device_name = current_profile.get("device_name", none_lbl)
            if not device_name:
                device_name = none_lbl
            
        if device_name not in device_values:
            device_values.append(device_name)
            self.combo_device.configure(values=device_values)
        self.combo_device.set(device_name)

        # Save / Cancel Button Frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20, fill="x", padx=20)
        btn_cancel = ctk.CTkButton(btn_frame, text=_("gui.btn_cancel"), width=120, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.destroy)
        btn_cancel.pack(side="left")
        btn_save = ctk.CTkButton(btn_frame, text=_("gui.btn_save"), width=120, fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.save)
        btn_save.pack(side="right")

    def on_slider_change(self, value):
        self.lbl_vol.configure(text=f"{_('gui.lbl_master_vol')} : {int(value)}%")

    def save(self):
        new_name = self.entry_name.get().strip()
        new_val = str(int(self.slider_vol.get()))
        new_device = self.combo_device.get()
        
        if not new_name:
            CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_profile_name_empty"))
            return

        self.callback(new_name, new_val, new_device)
        self.destroy()



class DeviceManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.manager = parent.device_manager
        
        self.title(_("gui.title_device_manager"))
        self.geometry("520x450")
        self.configure(fg_color=BG_COLOR)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        # Header Frame
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(header, text=_("gui.title_device_manager"), font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        
        btn_new = ctk.CTkButton(header, text=_("gui.btn_new_device"), fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.create_new_device, height=26)
        btn_new.pack(side="right")

        # Scroll Frame
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR, corner_radius=8)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.refresh_list()

    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        none_lbl = _("gui.lbl_none")
        active_name = none_lbl
        if self.parent.current_profile:
            active_name = self.parent.current_profile.get("device_name", none_lbl)

        self.manager.load_all_definitions()
        
        if not self.manager.definitions:
            lbl_empty = ctk.CTkLabel(self.scroll_frame, text=_("gui.lbl_no_device_def"), text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=12))
            lbl_empty.pack(pady=40)
            return

        for defn in self.manager.definitions:
            name = defn.get("name", "Unknown")
            is_active = (name.lower() == active_name.lower())

            item = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            item.pack(fill="x", pady=4, padx=5)

            if is_active:
                item.configure(fg_color=BG_COLOR)

            lbl_frame = ctk.CTkFrame(item, fg_color="transparent")
            lbl_frame.pack(side="left", fill="both", expand=True, padx=5)

            display_name = name[:25] + "..." if len(name) > 25 else name
            lbl_name = ctk.CTkLabel(lbl_frame, text=display_name, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold" if is_active else "normal"), text_color=ACCENT_COLOR if is_active else TEXT_PRIMARY)
            lbl_name.pack(side="left", anchor="w")

            if is_active:
                lbl_act = ctk.CTkLabel(lbl_frame, text=f"  {_('gui.lbl_active_indicator')}", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color="#10B981")
                lbl_act.pack(side="left")

            acts = ctk.CTkFrame(item, fg_color="transparent")
            acts.pack(side="right", padx=5)

            btn_dup = ctk.CTkButton(acts, text=_("gui.btn_duplicate"), width=70, height=24, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=10), command=lambda d=defn: self.duplicate_device(d))
            btn_dup.pack(side="left", padx=2)

            btn_edit = ctk.CTkButton(acts, text="✎", width=30, height=24, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=10), command=lambda d=defn: self.edit_device(d))
            btn_edit.pack(side="left", padx=2)

            btn_del = ctk.CTkButton(acts, text="✕", width=30, height=24, fg_color="#EF4444", hover_color="#DC2626", text_color="#FFFFFF", font=ctk.CTkFont(size=10, weight="bold"), command=lambda n=name: self.delete_device(n))
            btn_del.pack(side="left", padx=2)

    def create_new_device(self):
        dialog = ctk.CTkInputDialog(title=_("gui.btn_new_device"), text=_("gui.msg_new_device_name", default="Nom de la nouvelle télécommande :"))
        new_name = dialog.get_input()
        if new_name is None: return
        new_name = new_name.strip()
        if not new_name:
            CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_device_name_empty"))
            return

        if any(d.get("name", "").lower() == new_name.lower() for d in self.manager.definitions):
            CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_device_exists"))
            return

        data = {
            "name": new_name,
            "connection_type": "Composite",
            "physical_devices": [],
            "buttons": []
        }
        self.manager.save_definition(data)
        self.on_editor_saved()

    def edit_device(self, defn):
        DeviceEditorDialog(self, self.manager, defn, self.on_editor_saved)

    def on_editor_saved(self):
        self.refresh_list()
        self.parent.update_profile_device_combo_list()
        self.parent.update_device_def()

    def duplicate_device(self, defn):
        dialog = ctk.CTkInputDialog(title=_("gui.btn_duplicate"), text=_("gui.msg_new_profile_name"))
        new_name = dialog.get_input()
        if new_name is None: return
        new_name = new_name.strip()
        if not new_name:
            CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_device_name_empty"))
            return

        if any(d.get("name", "").lower() == new_name.lower() for d in self.manager.definitions):
            CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_device_exists"))
            return

        import copy
        new_def = copy.deepcopy(defn)
        new_def["name"] = new_name
        
        self.manager.save_definition(new_def)
        self.refresh_list()
        self.parent.update_profile_device_combo_list()

    def delete_device(self, name):
        if CTkMessageBox.ask_yes_no(_("gui.msg_confirm"), _("gui.msg_delete_device_confirm").replace("{name}", name)):
            self.manager.delete_definition(name)
            
            # Si le profil actif utilisait cette telecommande, le remettre a None
            none_lbl = _("gui.lbl_none")
            if self.parent.current_profile and self.parent.current_profile.get("device_name", "") == name:
                self.parent.current_profile["device_name"] = none_lbl
                self.parent.profile_manager.save_profile(self.parent.current_profile)

            self.refresh_list()
            self.parent.update_profile_device_combo_list()
            self.parent.update_device_def()


class MappingDialog(ctk.CTkToplevel):
    """Fenêtre popup pour ajouter/éditer un mapping"""
    def __init__(self, parent, callback, device_def=None, initial_data=None, profile_context=None, action_handler=None):
        super().__init__(parent)
        self.callback = callback
        self.initial_data = initial_data
        self.current_rec_data = None # Store scan codes from recording
        self.profile_context = profile_context # {app_context, window_title_filter}
        self.action_handler = action_handler

        self.title(_("gui.title_edit_action") if initial_data else _("gui.title_add_action"))
        self.geometry("450x480")
        self.configure(fg_color=BG_COLOR)
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text=_("gui.lbl_action_name"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=(15,2), padx=20, anchor="w")
        self.entry_name = ctk.CTkEntry(self, placeholder_text=_("gui.placeholder_action_name"), fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12))
        self.entry_name.pack(pady=(0, 5), padx=20, fill="x")
        if initial_data:
            self.entry_name.insert(0, initial_data.get("name", ""))

        ctk.CTkLabel(self, text=_("gui.lbl_button_midi_cc"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=(5,2), padx=20, anchor="w")

        self.combo_cc = ctk.CTkComboBox(self, fg_color=CARD_BG, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                        dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY,
                                        font=ctk.CTkFont(family="Segoe UI", size=12))
        self.combo_cc.pack(pady=(0, 5), padx=20, fill="x")

        # Populate values
        values = []
        if device_def:
            for b in device_def.get("buttons", []):
                cc = b['cc']
                lbl = b['label']
                if cc < 0:
                     values.append(f"{cc} - {lbl} ({_('gui.lbl_virtual')})")
                else:
                     values.append(f"{cc} - {lbl}")

        if not values:
            values = ["54", "55", "56", "57", "58"]

        self.combo_cc.configure(values=values)

        # Select Initial Value
        if initial_data:
            target_cc = initial_data.get("midi_cc")
            # Find matching string
            match = next((v for v in values if v.startswith(f"{target_cc} -") or v == str(target_cc)), str(target_cc))
            self.combo_cc.set(match)
        elif values:
            self.combo_cc.set(values[0])

        # Icon Selector
        ctk.CTkLabel(self, text=_("gui.lbl_icon_opt"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=(5,2), padx=20, anchor="w")
        self.combo_icon = ctk.CTkComboBox(self, values=[_("gui.lbl_auto"), "▶", "⏸", "■", "●", "⏪", "⏩", "⟳", "🔇", "🔊", "↔", "⏱", "♪", "◴", "📍", "▲", "▼", "◄", "►", "✓", "↶", "↷", "⚡", "⚙", "📂", "🎸", "🎤", "🎹"],
                                          fg_color=CARD_BG, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                          dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY,
                                          font=ctk.CTkFont(family="Segoe UI", size=12))
        self.combo_icon.pack(pady=(0, 5), padx=20, fill="x")

        if initial_data and initial_data.get("custom_icon"):
            self.combo_icon.set(initial_data.get("custom_icon"))
        else:
            self.combo_icon.set(_("gui.lbl_auto"))

        # Action Type Selector
        ctk.CTkLabel(self, text=_("gui.lbl_action_type"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=(5,2), padx=20, anchor="w")
        self.combo_type = ctk.CTkComboBox(self, values=[_("gui.type_hotkey"), _("gui.type_command"), _("gui.type_midi")], command=self.update_ui_state,
                                          fg_color=CARD_BG, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                          dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY,
                                          font=ctk.CTkFont(family="Segoe UI", size=12))
        self.combo_type.pack(pady=(0, 5), padx=20, fill="x")

        # --- Frames for different types ---
        self.frame_hotkey = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_command = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_midi = ctk.CTkFrame(self, fg_color="transparent")

        # 1. Hotkey UI
        ctk.CTkLabel(self.frame_hotkey, text=_("gui.lbl_keyboard_key"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=(5,2), anchor="w")
        self.sub_hotkey = ctk.CTkFrame(self.frame_hotkey, fg_color="transparent")
        self.sub_hotkey.pack(fill="x")
        
        self.entry_key = ctk.CTkEntry(self.sub_hotkey, placeholder_text="space", fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Consolas", size=12))
        self.entry_key.pack(side="left", fill="x", expand=True)

        self.btn_test = ctk.CTkButton(self.sub_hotkey, text="▶", width=30, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.test_mapping)
        self.btn_test.pack(side="right", padx=(5,0))

        self.btn_rec = ctk.CTkButton(self.sub_hotkey, text=_("gui.btn_rec"), width=60, fg_color="#EF4444", hover_color="#DC2626", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.start_recording)
        self.btn_rec.pack(side="right", padx=(5,0))
        
        self.lbl_scan_info = ctk.CTkLabel(self.frame_hotkey, text="", text_color="gray", font=("Arial", 10))
        self.lbl_scan_info.pack(pady=(2, 5))

        # 2. Command UI
        ctk.CTkLabel(self.frame_command, text=_("gui.lbl_command"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=(5,2), anchor="w")
        self.entry_cmd = ctk.CTkEntry(self.frame_command, placeholder_text="media_play_pause", fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=12))
        self.entry_cmd.pack(fill="x")

        # 3. MIDI Out UI
        ctk.CTkLabel(self.frame_midi, text=_("gui.lbl_midi_msg"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=(5,2), anchor="w")
        
        f_midi_row = ctk.CTkFrame(self.frame_midi, fg_color="transparent")
        f_midi_row.pack(fill="x")
        
        # Channel
        ctk.CTkLabel(f_midi_row, text=_("gui.lbl_midi_ch"), font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY).pack(side="left", padx=2)
        self.entry_midi_ch = ctk.CTkEntry(f_midi_row, width=40, fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Consolas", size=12))
        self.entry_midi_ch.pack(side="left", padx=2)
        self.entry_midi_ch.insert(0, "1")

        # CC
        ctk.CTkLabel(f_midi_row, text=_("gui.lbl_midi_cc"), font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY).pack(side="left", padx=2)
        self.entry_midi_cc = ctk.CTkEntry(f_midi_row, width=40, fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Consolas", size=12))
        self.entry_midi_cc.pack(side="left", padx=2)
        
        # Value
        ctk.CTkLabel(f_midi_row, text=_("gui.lbl_midi_val"), font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY).pack(side="left", padx=2)
        self.entry_midi_val = ctk.CTkEntry(f_midi_row, width=40, fg_color=CARD_BG, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Consolas", size=12))
        self.entry_midi_val.pack(side="left", padx=2)
        self.entry_midi_val.insert(0, "127")

        # Load Initial Data
        if initial_data:
            a_type = initial_data.get("action_type", "hotkey")
            
            if a_type == "midi":
                 self.combo_type.set(_("gui.type_midi"))
                 self.entry_midi_ch.delete(0, "end")
                 self.entry_midi_ch.insert(0, str(initial_data.get("output_channel", 1)))
                 self.entry_midi_cc.delete(0, "end")
                 self.entry_midi_cc.insert(0, str(initial_data.get("output_cc", 0)))
                 self.entry_midi_val.delete(0, "end")
                 self.entry_midi_val.insert(0, str(initial_data.get("output_value", 127)))
                 
            elif a_type == "command":
                 self.combo_type.set(_("gui.type_command"))
                 self.entry_cmd.insert(0, initial_data.get("action_value", ""))
                 
            else:
                 self.combo_type.set(_("gui.type_hotkey"))
                 self.entry_key.insert(0, initial_data.get("action_value", ""))

        self.update_ui_state(self.combo_type.get())

        self.btn_save = ctk.CTkButton(self, text=_("gui.btn_validate"), fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.save_mapping)
        self.btn_save.pack(pady=15, padx=20, fill="x")

    def update_ui_state(self, choice):
        self.frame_hotkey.pack_forget()
        self.frame_command.pack_forget()
        self.frame_midi.pack_forget()
        
        if choice == _("gui.type_hotkey"):
            self.frame_hotkey.pack(fill="x", padx=20, pady=5)
        elif choice == _("gui.type_command"):
            self.frame_command.pack(fill="x", padx=20, pady=5)
        elif choice == _("gui.type_midi"):
            self.frame_midi.pack(fill="x", padx=20, pady=5)

    def start_recording(self):
        self.btn_rec.configure(text="...", state="disabled")
        self.entry_key.delete(0, "end")
        self.entry_key.insert(0, _("gui.msg_press_key"))

        def _rec_thread():
            try:
                # Advanced recording to capture Scan Code
                pressed_scancodes = set()
                while True:
                    e = keyboard.read_event(suppress=False)
                    if e.event_type == keyboard.KEY_DOWN:
                        pressed_scancodes.add(e.scan_code)

                        # Improved modifier detection for AltGr/Right Alt
                        is_mod = keyboard.is_modifier(e.scan_code) or e.name in ['right alt', 'alt gr', 'right ctrl', 'right shift']

                        if not is_mod:
                            # Non-modifier key pressed -> Determine context
                            # Capture all other pressed keys as modifiers
                            current_modifiers_sc = [sc for sc in pressed_scancodes if sc != e.scan_code]

                            # Construct display name (best effort)
                            # We still want to show names like "Ctrl+C" even if we use scan codes internally
                            mod_names = []
                            def safe_is_pressed(k):
                                try: return keyboard.is_pressed(k)
                                except: return False

                            if safe_is_pressed('ctrl'): mod_names.append('ctrl')
                            if safe_is_pressed('shift'): mod_names.append('shift')
                            if safe_is_pressed('alt'): mod_names.append('alt')
                            if safe_is_pressed('right alt') or safe_is_pressed('alt gr'): mod_names.append('alt gr')
                            if safe_is_pressed('windows'): mod_names.append('windows')

                            # Deduplicate
                            mod_names = sorted(list(set(mod_names)))
                            full_name = "+".join(mod_names + [e.name])

                            res = {
                                "scan_code": e.scan_code,
                                "modifiers": mod_names,
                                "modifier_scan_codes": current_modifiers_sc,
                                "name": full_name
                            }
                            self.after(0, lambda: self.finish_recording(res))
                            break
                    elif e.event_type == keyboard.KEY_UP:
                         if e.scan_code in pressed_scancodes:
                             pressed_scancodes.discard(e.scan_code)
            except Exception as e:
                # with open("debug.log", "a") as f:
                #     import traceback
                #     f.write(f"REC ERROR: {e}\n{traceback.format_exc()}\n")
                self.after(0, lambda: self.finish_recording(None))

        threading.Thread(target=_rec_thread, daemon=True).start()

    def finish_recording(self, result):
        if result:
            self.entry_key.delete(0, "end")
            self.entry_key.insert(0, result["name"])
            self.current_rec_data = result
            self.lbl_scan_info.configure(text=f"{_('gui.lbl_scan_code')}: {result['scan_code']} (+{len(result.get('modifier_scan_codes', []))} mods)")
        else:
            self.entry_key.delete(0, "end")
            self.entry_key.insert(0, _("gui.lbl_error"))
            self.lbl_scan_info.configure(text="")

        self.btn_rec.configure(text="REC", state="normal")

    def test_mapping(self):
        """Teste le mapping avec un compte à rebours pour laisser l'utilisateur changer le focus"""
        mapping_data = self._build_mapping_data_from_ui()
        if not mapping_data: return

        if not self.action_handler:
             CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_handler_missing"))
             return

        # Disable button
        self.btn_test.configure(state="disabled")

        # Countdown 3s
        def _countdown(count):
            if not self.winfo_exists(): return

            if count > 0:
                self.btn_test.configure(text=str(count))
                self.after(1000, lambda: _countdown(count - 1))
            else:
                # Trigger !
                self.btn_test.configure(text="Go!", fg_color="green")
                self.action_handler.trigger_keystroke(mapping_data)

                # Reset UI
                self.after(500, lambda: self._reset_test_btn())

        _countdown(3)

    def _reset_test_btn(self):
        try:
            self.btn_test.configure(text="▶", state="normal", fg_color="#444")
        except: pass

    def _build_mapping_data_from_ui(self):
        val = self.combo_cc.get()
        try:
            if " - " in val:
                cc = int(val.split(" - ")[0])
            else:
                cc = int(val)
        except ValueError:
            CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_midi_cc_invalid"))
            return None

        scan_code = None
        modifiers = []
        modifier_scan_codes = []
        
        type_choice = self.combo_type.get()
        action_type = "hotkey"
        if type_choice == _("gui.type_command"): action_type = "command"
        elif type_choice == _("gui.type_midi"): action_type = "midi"
        
        action_val = ""
        
        # Output MIDI placeholders
        out_ch = 1
        out_cc = 0
        out_val = 127

        if type_choice == "Raccourci Clavier":
            action_type = "hotkey"
            action_val = self.entry_key.get()
            
            if self.current_rec_data and self.current_rec_data.get("name") == action_val:
                 scan_code = self.current_rec_data.get("scan_code")
                 modifiers = self.current_rec_data.get("modifiers")
                 modifier_scan_codes = self.current_rec_data.get("modifier_scan_codes", [])
            elif self.initial_data and self.initial_data.get("action_value") == action_val:
                 scan_code = self.initial_data.get("action_scan_code")
                 modifiers = self.initial_data.get("action_modifiers")
                 modifier_scan_codes = self.initial_data.get("action_modifier_scan_codes", [])

        elif action_type == "command":
            action_val = self.entry_cmd.get()
        elif action_type == "midi":
            try:
                out_ch = int(self.entry_midi_ch.get())
                out_cc = int(self.entry_midi_cc.get())
                out_val = int(self.entry_midi_val.get())
                action_val = f"MIDI ch{out_ch} cc{out_cc} v{out_val}" # For display
            except:
                CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_midi_vals_invalid"))
                return None

        icon_val = self.combo_icon.get()
        custom_icon = icon_val if icon_val != _("gui.lbl_auto") else None

        return {
            "name": self.entry_name.get() or _("gui.lbl_no_name"),
            "midi_cc": cc,
            "midi_channel": 16, # Input Channel (Default Omni)
            "trigger_value": "any",
            
            "action_type": action_type,
            "action_value": action_val,
            
            # Hotkey specific
            "action_scan_code": scan_code,
            "action_modifiers": modifiers,
            "action_modifier_scan_codes": modifier_scan_codes,
            
            # MIDI specific
            "output_channel": out_ch,
            "output_cc": out_cc,
            "output_value": out_val,
            
            "custom_icon": custom_icon
        }

    def save_mapping(self):
        data = self._build_mapping_data_from_ui()
        if data:
            self.callback(data)
            self.destroy()


# VirtualPedalboard replaced by CompactPedalboardFrame from remote_gui.py

class GuitarPracticeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(_("gui.main_title"))
        self.geometry("1000x750")
        self.configure(fg_color=BG_COLOR)

        self.tray_icon = None
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        try:
            self.iconbitmap(ICON_PNG_PATH)
        except: pass

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.profile_manager = ProfileManager()
        self.profile_manager.migrate_legacy_config()

        self.env_manager = EnvManager()
        # V6.1: Force use of DATA_DIR for library stability
        lib_path = os.path.join(get_data_dir(), "library.json")
        self.library_manager = LibraryManager(lib_path)

        self.device_manager = DeviceManager()
        self.current_device_def = None

        self.profiles = []
        self.current_profile = None
        self.manual_override_profile = None # For Smart Launcher
        self.mapping_indicators = {}
        self.mapping_indicators = {}
        # New Stateful MidiManager (Radical Stabilization)
        self.midi_manager = MidiManager(self.midi_callback, on_config_change=self.on_midi_config_change)
        
        self.action_handler = ActionHandler()
        self.action_handler.set_profile_manager(self.profile_manager)
        self.action_handler.set_midi_manager(self.midi_manager)
        self.action_handler.register_listener(self.on_data_received)
        self.action_handler.start_monitoring()
        self.settings = {"midi_device_name": "", "connection_mode": "MIDO"}
        self.remote_win = None

        # --- Context Monitor ---
        # Starts a background thread to detect active windows
        self.context_monitor = ContextMonitor(self.profile_manager, self.action_handler, self.on_context_change)
        self.context_monitor.start()

        self.create_sidebar()
        self.create_main_area()

        # Start Connection Monitor (AFTER UI creation)
        self._monitor_connection_status()

        self.load_data()
        # SILENT STARTUP: Removed explicit refresh
        # self.refresh_midi_ports()
        
        self.setup_tray()
        self.last_flash_time = 0
        self._revert_timer = None
        
        # Start Engine (Delayed)
        self.after(1000, self.start_engine)

    def start_engine(self):
        try:
            self.log_debug("Starting Engine (Silent): Delegating to update_device_def")
            self.update_device_def()
        except Exception as e:
            self.log_debug(f"Startup Error: {e}")

    def on_context_change(self, profile):
        """Callback from ContextMonitor when window changes"""
        # Update UI if allowed
        if not profile: return

        # Thread-safe UI update
        def _update():
            # Debug Log
            prof_name = profile.get("name") if profile else "None"
            self.log_debug(f"on_context_change callback triggered for: {prof_name}")
            
            # Avoid loop if same
            if self.current_profile and self.current_profile.get("name") == prof_name:
                 self.log_debug(f"Profile {prof_name} already active. Skipping UI refresh.")
                 return

            self.log_debug(f"Auto-Switch Profile: {prof_name}")
            
            # Select in Main UI
            self.select_profile_by_name(prof_name)
            
            # Update Remote Control specifically if open
            if hasattr(self, 'remote_win') and self.remote_win and self.remote_win.winfo_exists():
                self.log_debug(f"Updating Remote Window to {prof_name}")
                self.remote_win.set_profile(profile)
            else:
                self.log_debug(f"Remote window not open or invalid.")

        self.after(0, _update)

    def on_midi_config_change(self, new_ports):
        """Callback from MidiManager when ports are auto-healed (fuzzy match)"""
        self.settings["midi_output_names"] = new_ports
        # Trigger silent save
        self.after(0, lambda: self.save_all(silent=True))

    def log_debug(self, message):
        # logging is now disabled to save disk space
        pass

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=CARD_BG)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Spacer is row 5

        # 1. Logo
        try:
             pil_img = Image.open(LOGO_PATH)
             logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(220, 40))
             self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="", image=logo_img)
        except Exception as e:
             print(f"Logo Load Error: {e}")
             self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MIDI-KBD\nControl", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=ACCENT_LIGHT)
        self.logo_label.grid(row=0, column=0, padx=10, pady=(10, 5))

        # 2. Associated Controller (Télécommande associée)
        self.lbl_profile_device = ctk.CTkLabel(self.sidebar_frame, text=_("gui.lbl_associated_device"), anchor="w", text_color=TEXT_SECONDARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"))
        self.lbl_profile_device.grid(row=1, column=0, padx=20, pady=(5, 0), sticky="w")

        self.profile_device_combo = ctk.CTkComboBox(self.sidebar_frame, values=[], command=self.change_profile_device, height=26,
                                                    fg_color=BG_COLOR, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                                    dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY)
        self.profile_device_combo.grid(row=2, column=0, padx=20, pady=(0, 5))

        # 3. Device & Settings
        self.settings_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.settings_frame.grid(row=3, column=0, padx=10, pady=5)

        # Ligne 1 : Bouton Modifier Direct (toute la largeur)
        self.btn_modify_active_device = ctk.CTkButton(
            self.settings_frame,
            text=_("gui.btn_modify_device", default="✎ Modifier"),
            width=184,
            height=26,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.modify_active_device
        )
        self.btn_modify_active_device.pack(side="top", fill="x", pady=(0, 4))

        # Ligne 2 : Conteneur des boutons d'administration
        self.settings_row2 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.settings_row2.pack(side="top", fill="x")

        # Bouton Bibliothèque (Gérer)
        self.btn_edit_device = ctk.CTkButton(
            self.settings_row2,
            text=_("gui.btn_device_library", default="📁 Gérer"),
            width=90,
            height=24,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            command=self.open_device_editor
        )
        self.btn_edit_device.pack(side="left", padx=2)

        # Bouton Paramètres Globaux
        self.btn_settings = ctk.CTkButton(
            self.settings_row2,
            text=f"🛠 {_('gui.btn_settings')}",
            width=90,
            height=24,
            fg_color=BTN_SECONDARY,
            hover_color=BTN_SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            command=self.open_settings
        )
        self.btn_settings.pack(side="left", padx=2)

        self.status_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.status_frame.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        # Connection State
        self.conn_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.conn_frame.pack(fill="x", pady=2)

        self.lbl_conn_led = ctk.CTkLabel(self.conn_frame, text="●", font=ctk.CTkFont(size=18), text_color=LED_DISCONNECTED)
        self.lbl_conn_led.pack(side="left", padx=(0, 5))
        self.lbl_conn_text = ctk.CTkLabel(self.conn_frame, text=_("gui.lbl_disconnected"), font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_conn_text.pack(side="left")

        # LCD Monitor
        self.monitor_frame = ctk.CTkFrame(self.status_frame, fg_color=LCD_BG, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        self.monitor_frame.pack(fill="x", pady=5)

        self.lbl_monitor_cc = ctk.CTkLabel(self.monitor_frame, text=f"{_('gui.lbl_monitor_cc')}: --", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color=LCD_TEXT)
        self.lbl_monitor_cc.pack(side="left", padx=10, pady=5)

        self.lbl_monitor_ch = ctk.CTkLabel(self.monitor_frame, text=f"{_('gui.lbl_monitor_ch')}: --", font=ctk.CTkFont(family="Consolas", size=10), text_color=LCD_TEXT)
        self.lbl_monitor_ch.pack(side="right", padx=10, pady=5)



        # Spacer (Row 5 is Spacer row, let's add a label to push content up)
        self.spacer_lbl = ctk.CTkLabel(self.sidebar_frame, text="")
        self.spacer_lbl.grid(row=5, column=0)

        # 5. Startup
        is_startup = self.check_startup_status()
        self.startup_var = ctk.BooleanVar(value=is_startup)
        self.chk_startup = ctk.CTkCheckBox(self.sidebar_frame, text=_("gui.lbl_launch_at_startup"), variable=self.startup_var, command=self.toggle_startup,
                                           font=ctk.CTkFont(family="Segoe UI", size=11), text_color=TEXT_SECONDARY, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER)
        self.chk_startup.grid(row=6, column=0, padx=20, pady=10, sticky="w")

        # 6. Global Actions
        self.btn_remote = ctk.CTkButton(self.sidebar_frame, text=_("gui.btn_detach_remote"), command=self.open_remote_control, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, height=28)
        self.btn_remote.grid(row=7, column=0, padx=20, pady=(10, 2))

        self.btn_sync = ctk.CTkButton(self.sidebar_frame, text="☁ Sync", command=self.open_sync_dialog, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY, height=28)
        self.btn_sync.grid(row=8, column=0, padx=20, pady=(2, 5))

        self.save_button = ctk.CTkButton(self.sidebar_frame, text=_("gui.btn_save_all"), command=lambda: self.save_all(silent=False), fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", height=28)
        self.save_button.grid(row=9, column=0, padx=20, pady=(5, 20))

    def create_main_area(self):
        # Configuration de la grille principale
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)

        # --- Zone 1: Sélection du Profil ---
        self.profile_frame = ctk.CTkFrame(self, corner_radius=8, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR)
        self.profile_frame.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(self.profile_frame, text=_("gui.lbl_profile", default="Profil :"), font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left", padx=(10, 5), pady=6)

        self.profile_combo = ctk.CTkComboBox(self.profile_frame, width=200, height=26, command=self.on_profile_change,
                                            fg_color=BG_COLOR, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER,
                                            dropdown_fg_color=CARD_BG, dropdown_hover_color=ACCENT_HOVER, dropdown_text_color=TEXT_PRIMARY, text_color=TEXT_PRIMARY,
                                            font=ctk.CTkFont(family="Segoe UI", size=12))
        self.profile_combo.pack(side="left", padx=4, pady=6)

        self.btn_new_profile = ctk.CTkButton(self.profile_frame, text="+", width=26, height=26, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), command=self.create_new_profile)
        self.btn_new_profile.pack(side="left", padx=4, pady=6)

        self.btn_dup_profile = ctk.CTkButton(self.profile_frame, text="❐", width=26, height=26, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), command=self.duplicate_current_profile)
        self.btn_dup_profile.pack(side="left", padx=4, pady=6)

        self.btn_edit_profile = ctk.CTkButton(self.profile_frame, text="✎", width=26, height=26, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), command=self.edit_current_profile)
        self.btn_edit_profile.pack(side="left", padx=4, pady=6)

        self.btn_del_profile = ctk.CTkButton(self.profile_frame, text=_("gui.btn_delete_short"), width=44, height=26, fg_color="#EF4444", hover_color="#DC2626", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.delete_current_profile)
        self.btn_del_profile.pack(side="left", padx=4, pady=6)

        # Shortcut Memo Button
        self.btn_shortcuts = ctk.CTkButton(self.profile_frame, text=f"📝 {_('gui.btn_memo')}", width=80, height=26, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.open_shortcuts_dialog)
        self.btn_shortcuts.pack(side="right", padx=10, pady=6)

        # --- Zone 2: Règles de Détection ---
        self.rules_frame = ctk.CTkFrame(self, corner_radius=8, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR)
        self.rules_frame.grid(row=1, column=1, padx=10, pady=(5, 5), sticky="ew")
        
        self.rules_frame.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(self.rules_frame, text=_("gui.lbl_rules"), width=60, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY).grid(row=0, column=0, padx=(10, 2), pady=6)

        self.entry_app_rule = ctk.CTkEntry(self.rules_frame, placeholder_text=_("gui.placeholder_process"), height=26, fg_color=BG_COLOR, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11))
        self.entry_app_rule.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        self.btn_scan_app = ctk.CTkButton(self.rules_frame, text=_("gui.btn_scan_app"), width=70, height=26, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11), command=lambda: self.scan_window("app"))
        self.btn_scan_app.grid(row=0, column=2, padx=4, pady=6)

        self.entry_title_rule = ctk.CTkEntry(self.rules_frame, placeholder_text=_("gui.placeholder_title_opt"), height=26, fg_color=BG_COLOR, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11))
        self.entry_title_rule.grid(row=0, column=3, padx=4, pady=6, sticky="ew")

        self.btn_scan_title = ctk.CTkButton(self.rules_frame, text=_("gui.btn_scan_title"), width=70, height=26, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11), command=lambda: self.scan_window("title"))
        self.btn_scan_title.grid(row=0, column=4, padx=4, pady=6)

        self.entry_vol_rule = ctk.CTkEntry(self.rules_frame, placeholder_text=_("gui.placeholder_os_vol"), height=26, width=70, fg_color=BG_COLOR, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11))
        self.entry_vol_rule.grid(row=0, column=5, padx=4, pady=6)

        self.rules_frame.grid_columnconfigure(1, weight=1)
        self.rules_frame.grid_columnconfigure(3, weight=1)

        self.btn_apply_rules = ctk.CTkButton(self.rules_frame, text="✓", width=26, height=26, fg_color="#10B981", hover_color="#059669", text_color="#FFFFFF", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), command=self.apply_rules_to_profile)
        self.btn_apply_rules.grid(row=0, column=6, padx=(4, 10), pady=6)

        # --- Zone 3: Header Mappings (New) ---
        self.mappings_header = ctk.CTkFrame(self, fg_color="transparent")
        self.mappings_header.grid(row=2, column=1, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(self.mappings_header, text=_("gui.lbl_mappings"), font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        self.add_mapping_btn = ctk.CTkButton(self.mappings_header, text=f"+ {_('gui.btn_add')}", width=80, height=26, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color=TEXT_PRIMARY, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), command=self.open_add_dialog)
        self.add_mapping_btn.pack(side="right")

        # --- Zone 4: Liste des Mappings ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color=CARD_BG, border_width=1, border_color=BORDER_COLOR, corner_radius=8)
        self.scrollable_frame.grid(row=3, column=1, padx=10, pady=(0, 10), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # --- Zone 5: Pédalier Virtuel ---
        self.virtual_pedalboard = CompactPedalboardFrame(self, self.current_device_def, self.current_profile, self.simulate_midi_press)
        self.virtual_pedalboard.grid(row=4, column=1, padx=10, pady=(0, 15), sticky="")


    def load_data(self):
        # 1. Load Global Settings
        from utils import get_app_dir
        config_path = os.path.join(get_app_dir(), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings = data.get("settings", {"midi_device_name": "", "connection_mode": "MIDO"})
                    
                    if "midi_output_names" not in self.settings:
                        from config_manager import ConfigManager
                        cm = ConfigManager()
                        self.settings["midi_output_names"] = cm.get("midi_output_names", [])

                    mode = self.settings.get("connection_mode", "MIDO")
                    if mode == "BLE": 
                        target = self.settings.get("midi_device_name_ble", self.settings.get("midi_device_name", ""))
                    else: 
                        target = self.settings.get("midi_device_name_usb", self.settings.get("midi_device_name", ""))
                    
                    # LOAD MIDI OUTPUT
                    # LOAD MIDI OUTPUT (Multi-Port Support)
                    out_ports = self.settings.get("midi_output_names", [])
                    
                    # Migration: If list empty but legacy single port exists
                    if not out_ports:
                        old_port = self.settings.get("midi_output_port", None)
                        if old_port:
                            out_ports = [old_port]
                            # Auto-migrate config in memory (will be saved on exit)
                            self.settings["midi_output_names"] = out_ports
                            
                            
                    resolved = self.midi_manager.set_output_ports(out_ports)
                    if resolved and resolved != out_ports:
                        self.settings["midi_output_names"] = resolved
                        # Persist smart match automatically
                        try:
                            from config_manager import ConfigManager
                            cm = ConfigManager()
                            cm.set("midi_output_names", resolved)
                        except: pass

            except: pass

        # 2. Update Device Def
        self.update_device_def()

        # 3. Load Profiles
        self.profiles = self.profile_manager.load_all_profiles()
        self.update_profile_combo()
        if self.profiles:
            self.select_profile_by_name(self.profiles[0]["name"])
        else:
            self.create_default_profile()

        # 4. Smart Launcher Wiring
        self.library_manager.import_apps_from_profiles(self.profile_manager)
        self.library_manager.set_force_profile_callback(self.force_profile_switch)

    def update_device_def(self):
        none_lbl = _("gui.lbl_none")
        
        # Le périphérique est associé au profil courant
        device_name = none_lbl
        if self.current_profile:
            device_name = self.current_profile.get("device_name", none_lbl)
            if not device_name:
                device_name = none_lbl

        if device_name == none_lbl or not device_name:
            new_def = {"name": none_lbl, "buttons": []}
        else:
            # Chercher dans les définitions par nom logique exact
            new_def = self.device_manager.get_definition_by_name(device_name)
            
            # Fallback rétrocompatible
            if not new_def:
                new_def = self.device_manager.get_definition_for_port(device_name)

            # Ultimate Fallback: Just take the first one available
            if not new_def and self.device_manager.definitions:
                 new_def = self.device_manager.definitions[0]

            # Absolute Last Resort: Hardcoded default
            if not new_def:
                new_def = {"name": _("gui.lbl_no_device"), "buttons": []}

        self.current_device_def = new_def
        self.log_debug(f"Device Definition set to: {self.current_device_def.get('name')}")
        
        # Propager la configuration de télécommande active au ActionHandler pour le filtrage par canal
        if hasattr(self, 'action_handler') and self.action_handler:
            self.action_handler.set_active_device_def(self.current_device_def)

        if hasattr(self, 'virtual_pedalboard'):
            self.virtual_pedalboard.set_device_def(self.current_device_def)

        # Commutation dynamique du moteur MIDI d'après la télécommande associée
        conn_type = self.current_device_def.get("connection_type", "Virtuel") if self.current_device_def else "Virtuel"
        midi_port = self.current_device_def.get("midi_port", "") if self.current_device_def else ""

        if conn_type == "Composite":
            physical_devices = self.current_device_def.get("physical_devices", [])
            if not physical_devices:
                self.log_debug("Composite switching: no physical devices specified, fallback to virtual mode.")
                self.settings["connection_mode"] = "Virtuel"
                self.settings["midi_device_name"] = ""
                self.midi_manager.switch_mode(None, None)
            else:
                self.log_debug(f"Switching engine to Composite. Physical devices: {physical_devices}")
                self.settings["connection_mode"] = "Composite"
                self.settings["midi_device_name"] = "Composite"
                self.midi_manager.switch_composite(physical_devices)
        elif conn_type in ("USB", "BLE"):
            self.log_debug(f"Switching engine to physical: Mode={conn_type}, Port={midi_port}")
            self.settings["connection_mode"] = "MIDO" if conn_type == "USB" else "BLE"
            self.settings["midi_device_name"] = midi_port
            if conn_type == "USB":
                self.settings["midi_device_name_usb"] = midi_port
            else:
                self.settings["midi_device_name_ble"] = midi_port
            self.midi_manager.switch_mode(conn_type, midi_port)
        else:
            self.log_debug("Switching engine to virtual. Stopping physical connection.")
            self.settings["connection_mode"] = "Virtuel"
            self.settings["midi_device_name"] = ""
            self.midi_manager.switch_mode(None, None)

        # Persist connection mode and device name to config.json immediately
        self.save_all(silent=True)


        # Update buttons state and text
        if self.current_device_def and self.current_device_def.get("name") not in (none_lbl, "None", "Aucun", ""):
            btn_text = f"✎ {self.current_device_def['name'][:10]}"
            self.btn_modify_active_device.configure(state="normal", text=btn_text)
        else:
            self.btn_modify_active_device.configure(state="disabled", text=f"✎ {none_lbl}")

        self.btn_edit_device.configure(text=_("gui.btn_device_library", default="📁 Gérer"), state="normal")

    def modify_active_device(self):
        none_lbl = _("gui.lbl_none")
        if self.current_device_def and self.current_device_def.get("name") not in (none_lbl, "None", "Aucun", ""):
            DeviceEditorDialog(self, self.device_manager, self.current_device_def, self.on_active_device_saved)

    def on_active_device_saved(self):
        self.device_manager.load_all_definitions()
        self.update_profile_device_combo_list()
        self.update_device_def()

    def open_device_editor(self):
        DeviceManagerDialog(self)

    def open_settings(self):
        SettingsDialog(self, self.profile_manager, self.action_handler, self.env_manager, self.midi_manager)

    def open_sync_dialog(self):
        from utils import get_app_dir
        import threading
        import json
        import os
        
        config_path = os.path.join(get_app_dir(), "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                conf = json.load(f)
        except:
            conf = {}
        sync_conf = conf.get("sync", {"type": "sftp", "host": "", "port": 22, "username": "", "password": "", "remote_dir": "", "target_dir": ""})

        # Load saved categories or defaults
        stored_cats = sync_conf.get("categories", ["exe", "medias", "data", "system", "profiles", "devices"])

        dialog = ctk.CTkToplevel(self)
        dialog.title(_("sync.title"))
        dialog.geometry("520x450")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        tabs = ctk.CTkTabview(dialog)
        tabs.pack(fill="both", expand=True, padx=10, pady=5)
        tab_sync = tabs.add("Synchronisation")
        tab_conf = tabs.add("SFTP")
        tab_webdav = tabs.add("WebDAV")
        tab_local = tabs.add("Local")

        # --- TAB SYNC ---
        ctk.CTkLabel(tab_sync, text=_("sync.title"), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        type_var = ctk.StringVar(value=sync_conf.get("type", "sftp"))
        radio_frame = ctk.CTkFrame(tab_sync, fg_color="transparent")
        radio_frame.pack(pady=5)
        ctk.CTkRadioButton(radio_frame, text="SFTP", variable=type_var, value="sftp").pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_frame, text="WebDAV", variable=type_var, value="webdav").pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_frame, text="Local", variable=type_var, value="local").pack(side="left", padx=10)
        
        # Sync Mode selection
        ctk.CTkLabel(tab_sync, text="Mode de Synchronisation:", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 0))
        mode_var = ctk.StringVar(value=sync_conf.get("mode", "Bidirectionnel (Auto)"))
        mode_menu = ctk.CTkOptionMenu(tab_sync, values=["Bidirectionnel (Auto)", "Réception (Pull Only)", "Envoi (Push Only)"], variable=mode_var)
        mode_menu.pack(pady=5)
        
        # Categories Frame
        cat_frame = ctk.CTkFrame(tab_sync)
        cat_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(cat_frame, text=_("sync.lbl_categories"), font=ctk.CTkFont(size=12, weight="bold")).pack(pady=5)
        
        cat_vars = {}
        categories = [
            ("exe", _("sync.cat_exe")),
            ("medias", _("sync.cat_medias")),
            ("data", _("sync.cat_data")),
            ("profiles", _("sync.cat_profiles")),
            ("devices", _("sync.cat_devices")),
            ("system", _("sync.cat_system"))
        ]
        
        def open_exceptions_modal(category_key, category_label):
            import traceback
            import logging
            
            try:
                from sync_manager import SyncManager, LocalProvider
                
                exc_dialog = ctk.CTkToplevel(dialog)
                exc_dialog.title(f"Exceptions : {category_label}")
                exc_dialog.geometry("500x600")
                exc_dialog.grab_set()
                
                lbl_info = ctk.CTkLabel(exc_dialog, text=f"Cochez les fichiers locaux que vous souhaitez IGNORER\nlors de la synchronisation (catégorie : {category_label}).", justify="left", font=ctk.CTkFont(weight="bold"))
                lbl_info.pack(pady=10, padx=10, fill="x")
                
                scroll_frame = ctk.CTkScrollableFrame(exc_dialog)
                scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
                
                # Charger les fichiers locaux
                app_dir = get_app_dir()
                mgr = SyncManager(app_dir, LocalProvider(app_dir))
                local_files = mgr._list_local_files()
                
                # Filtrer par catégorie
                cat_files = [p for p in local_files.keys() if mgr._is_in_selected_categories(p, [category_key])]
                cat_files.sort(key=str.lower)
                
                current_exceptions = sync_conf.get("exceptions", [])
                checkboxes = {}
                
                for file_path in cat_files:
                    var = ctk.BooleanVar(value=file_path in current_exceptions)
                    cb = ctk.CTkCheckBox(scroll_frame, text=file_path, variable=var, font=ctk.CTkFont(size=11))
                    cb.pack(fill="x", pady=2, padx=5)
                    checkboxes[file_path] = var
                    
                def save_exceptions():
                    # Nettoyer les anciennes exceptions de cette catégorie
                    new_exceptions = [e for e in current_exceptions if e not in cat_files]
                    # Ajouter les nouvelles
                    for file_path, var in checkboxes.items():
                        if var.get():
                            new_exceptions.append(file_path)
                    sync_conf["exceptions"] = new_exceptions
                    self.config_manager.set("sync", sync_conf)
                    exc_dialog.destroy()
                    
                btn_save_exc = ctk.CTkButton(exc_dialog, text=_("gui.btn_save"), command=save_exceptions)
                btn_save_exc.pack(pady=10)
            except Exception as e:
                logging.error(f"[EXCEPTIONS MODAL CRASH] {e}\n{traceback.format_exc()}")


        # Create grid for checkboxes
        cb_container = ctk.CTkFrame(cat_frame, fg_color="transparent")
        cb_container.pack(pady=5)
        for i, (key, label) in enumerate(categories):
            var = ctk.BooleanVar(value=key in stored_cats)
            cat_vars[key] = var
            
            cell = ctk.CTkFrame(cb_container, fg_color="transparent")
            cell.grid(row=i//2, column=i%2, padx=10, pady=3, sticky="w")
            
            cb = ctk.CTkCheckBox(cell, text=label, variable=var, font=ctk.CTkFont(size=11))
            cb.pack(side="left")
            
            btn_cfg = ctk.CTkButton(cell, text="⚙️", width=24, height=24, fg_color="transparent", 
                                  hover_color=("gray70", "gray30"), text_color=("black", "white"),
                                  command=lambda k=key, l=label: open_exceptions_modal(k, l))
            btn_cfg.pack(side="left", padx=5)


        # Progress status (minimal)
        lbl_status = ctk.CTkLabel(tab_sync, text=_("gui.status_wait"), text_color="gray")
        lbl_status.pack(pady=10)

        # --- TAB CONF SFTP ---
        # (Same as before but with better labels)
        ctk.CTkLabel(tab_conf, text="Serveur / Host:", anchor="w").pack(fill="x", padx=10)
        e_host = ctk.CTkEntry(tab_conf)
        e_host.insert(0, str(sync_conf.get("host", "")))
        e_host.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(tab_conf, text="Port:", anchor="w").pack(fill="x", padx=10)
        e_port = ctk.CTkEntry(tab_conf)
        e_port.insert(0, str(sync_conf.get("port", "22")))
        e_port.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(tab_conf, text="Utilisateur:", anchor="w").pack(fill="x", padx=10)
        e_user = ctk.CTkEntry(tab_conf)
        e_user.insert(0, str(sync_conf.get("username", "")))
        e_user.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(tab_conf, text="Mot de passe:", anchor="w").pack(fill="x", padx=10)
        e_pass = ctk.CTkEntry(tab_conf, show="*")
        e_pass.insert(0, str(sync_conf.get("password", "")))
        e_pass.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(tab_conf, text="Dossier Distant:", anchor="w").pack(fill="x", padx=10)
        e_dir = ctk.CTkEntry(tab_conf)
        e_dir.insert(0, str(sync_conf.get("remote_dir", "")))
        e_dir.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(tab_conf, text=_("sync.manual_skew_hours"), anchor="w").pack(fill="x", padx=10)
        e_skew = ctk.CTkEntry(tab_conf)
        e_skew.insert(0, str(sync_conf.get("manual_skew_hours_sftp", sync_conf.get("manual_skew_hours", "0"))))
        e_skew.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(tab_conf, text=_("gui.btn_save"), command=lambda: save_conf() and lbl_status.configure(text="Config SFTP Sauvée.", text_color="green"), fg_color="green", hover_color="darkgreen").pack(pady=5)

        # --- TAB CONF WEBDAV ---
        ctk.CTkLabel(tab_webdav, text="URL WebDAV (ex: https://cloud.com/dav):", anchor="w").pack(fill="x", padx=10)
        e_wd_url = ctk.CTkEntry(tab_webdav)
        e_wd_url.insert(0, str(sync_conf.get("webdav_url", "")))
        e_wd_url.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(tab_webdav, text="Utilisateur:", anchor="w").pack(fill="x", padx=10)
        e_wd_user = ctk.CTkEntry(tab_webdav)
        e_wd_user.insert(0, str(sync_conf.get("webdav_user", "")))
        e_wd_user.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(tab_webdav, text="Mot de passe:", anchor="w").pack(fill="x", padx=10)
        e_wd_pass = ctk.CTkEntry(tab_webdav, show="*")
        e_wd_pass.insert(0, str(sync_conf.get("webdav_pass", "")))
        e_wd_pass.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(tab_webdav, text=_("sync.manual_skew_hours"), anchor="w").pack(fill="x", padx=10)
        e_wd_skew = ctk.CTkEntry(tab_webdav)
        e_wd_skew.insert(0, str(sync_conf.get("manual_skew_hours_webdav", sync_conf.get("manual_skew_hours", "0"))))
        e_wd_skew.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(tab_webdav, text=_("gui.btn_save"), command=lambda: save_conf() and lbl_status.configure(text="Config WebDAV Sauvée.", text_color="green"), fg_color="green", hover_color="darkgreen").pack(pady=5)

        # --- TAB LOCAL ---
        ctk.CTkLabel(tab_local, text="Chemin du dossier (ex: Dropbox/AirstepSync):", anchor="w").pack(fill="x", padx=10, pady=(10,0))
        e_local_dir = ctk.CTkEntry(tab_local)
        e_local_dir.insert(0, str(sync_conf.get("target_dir", "")))
        e_local_dir.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(tab_local, text=_("sync.manual_skew_hours"), anchor="w").pack(fill="x", padx=10)
        e_local_skew = ctk.CTkEntry(tab_local)
        e_local_skew.insert(0, str(sync_conf.get("manual_skew_hours_local", sync_conf.get("manual_skew_hours", "0"))))
        e_local_skew.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(tab_local, text=_("gui.btn_save"), command=lambda: save_conf() and lbl_status.configure(text="Config Locale Sauvée.", text_color="green"), fg_color="green", hover_color="darkgreen").pack(pady=5)
        
        def pick_local():
            import tkinter.filedialog
            folder = tkinter.filedialog.askdirectory(parent=dialog)
            if folder:
                e_local_dir.delete(0, "end")
                e_local_dir.insert(0, folder)
        ctk.CTkButton(tab_local, text="Parcourir", command=pick_local, fg_color="#555").pack(pady=5)

        def save_conf():
            try:
                sync_conf["host"] = e_host.get()
                sync_conf["port"] = int(e_port.get() or 22)
                sync_conf["username"] = e_user.get()
                sync_conf["password"] = e_pass.get()
                sync_conf["remote_dir"] = e_dir.get()
                sync_conf["target_dir"] = e_local_dir.get()
                sync_conf["webdav_url"] = e_wd_url.get()
                sync_conf["webdav_user"] = e_wd_user.get()
                sync_conf["webdav_pass"] = e_wd_pass.get()
                sync_conf["type"] = type_var.get()
                sync_conf["mode"] = mode_var.get()
                
                # Save manual skew (Partitioned V9.6.50)
                try:
                    sync_conf["manual_skew_hours_sftp"] = float(e_skew.get() or 0)
                    sync_conf["manual_skew_hours_webdav"] = float(e_wd_skew.get() or 0)
                    sync_conf["manual_skew_hours_local"] = float(e_local_skew.get() or 0)
                    
                    # Set current based on active type for backward compatibility
                    if sync_conf["type"] == "sftp": sync_conf["manual_skew_hours"] = sync_conf["manual_skew_hours_sftp"]
                    elif sync_conf["type"] == "webdav": sync_conf["manual_skew_hours"] = sync_conf["manual_skew_hours_webdav"]
                    else: sync_conf["manual_skew_hours"] = sync_conf["manual_skew_hours_local"]
                except:
                    pass
                
                # Save categories
                active_cats = [k for k, v in cat_vars.items() if v.get()]
                sync_conf["categories"] = active_cats
                
                conf["sync"] = sync_conf
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(conf, f, indent=4)
                return True
            except Exception as e:
                lbl_status.configure(text=f"Erreur config: {e}", text_color="red")
                tabs.set("Synchronisation")
                return False


        # --- RUN logic ---
        def run_sync():
            if not save_conf(): return
            
            btn_sync.configure(state="disabled")
            lbl_status.configure(text=_("sync.status_analyzing"), text_color="orange")
            
            modal_container = [None] # To store modal reference
            
            def _thread():
                try:
                    from sync_manager import SyncManager, LocalProvider, SftpProvider, WebdavProvider
                    
                    with open(config_path, "r", encoding="utf-8") as f:
                        fresh_conf = json.load(f)
                    current_sync_conf = fresh_conf.get("sync", {})
                    shared_fields = current_sync_conf.get("shared_fields", None)
                    selected_cats = current_sync_conf.get("categories", None)
                    
                    if current_sync_conf.get("type", "sftp") == "sftp":
                        provider = SftpProvider(
                            current_sync_conf.get("host"), current_sync_conf.get("port", 22),
                            current_sync_conf.get("username"), current_sync_conf.get("password", ""),
                            current_sync_conf.get("remote_dir", "/var/www/airstep")
                        )
                    elif current_sync_conf.get("type") == "webdav":
                        provider = WebdavProvider(
                            current_sync_conf.get("webdav_url"),
                            current_sync_conf.get("webdav_user"),
                            current_sync_conf.get("webdav_pass")
                        )
                    else:
                        local_target = current_sync_conf.get("target_dir", "")
                        if not local_target:
                            raise ValueError("Le dossier Cloud local n'est pas configuré.")
                        provider = LocalProvider(local_target)
                        
                    mgr = SyncManager(get_app_dir(), provider, shared_fields=shared_fields)
                    
                    # Progress Callback setup
                    def on_progress(current, total, filename, stage, reason=None):
                        pct = current / total if total > 0 else 1
                        
                        # Use modal widgets if available
                        if modal_container[0]:
                            modal_container[0].progress_bar.set(pct)
                            r_text = f" ({reason})" if reason else ""
                            if stage == "pull":
                                modal_container[0].log_msg(_("sync.stage_pull", file=filename) + r_text)
                            elif stage == "push":
                                modal_container[0].log_msg(_("sync.stage_push", file=filename) + r_text)
                            elif stage == "delete_remote":
                                modal_container[0].log_msg(f"🗑️ [DEL REMOTE] {filename}")
                            elif stage == "delete_local":
                                modal_container[0].log_msg(f"🗑️ [DEL LOCAL] {filename}")
                        else:
                            if stage == "analyzing":
                                lbl_status.configure(text=_("sync.status_analyzing"))
                    
                    mgr.set_progress_callback(on_progress)
                    
                    sync_mode = current_sync_conf.get("mode", "Bidirectionnel (Auto)")
                    exceptions = current_sync_conf.get("exceptions", [])
                    manual_skew_h = current_sync_conf.get("manual_skew_hours", 0)
                    manual_skew_s = manual_skew_h * 3600
                    
                    try:
                        res = mgr.analyze(selected_categories=selected_cats, mode=sync_mode, exceptions=exceptions, manual_skew=manual_skew_s)
                    except Exception as e:
                        err_msg = str(e)
                        def show_err():
                            lbl_status.configure(text=f"Erreur réseau: {err_msg}", text_color="red")
                            btn_sync.configure(state="normal")
                        dialog.after(0, show_err)
                        return
                    
                    # V9.1: Apply Sync Mode filtering
                    sync_mode = current_sync_conf.get("mode", "Bidirectionnel (Auto)")
                    if "Réception" in sync_mode:
                        res["push"] = []
                        res["delete_remote"] = []
                    elif "Envoi" in sync_mode:
                        res["pull"] = []
                        res["delete_local"] = []
                    
                    # V9.1: Sync Confirmation Logic
                    sync_event = threading.Event()
                    final_choice = {"res": None}
                    
                    def on_user_choice(choice):
                        final_choice["res"] = choice
                        sync_event.set()
                    
                    if not any(res.values()):
                        def nothing_ui():
                            lbl_status.configure(text=_("sync.status_uptodate"), text_color="green")
                            btn_sync.configure(state="normal")
                        dialog.after(0, nothing_ui)
                        return
                    
                    # V9.6.22: Translated summary message
                    summary_text = _("sync.msg_analysis_res", pull=len(res['pull']), push=len(res['push']))
                    def info_ui():
                        lbl_status.configure(text=summary_text, text_color="green")
                    dialog.after(0, info_ui)

                    # Show dialog on main thread
                    def show_dialog():
                        modal_container[0] = SyncConfirmationDialog(dialog, res, on_user_choice)
                    
                    dialog.after(0, show_dialog)
                    
                    # Wait for user
                    def wait_ui():
                        lbl_status.configure(text="En attente du récapitulatif...", text_color="orange")
                    dialog.after(0, wait_ui)
                    
                    sync_event.wait()
                    
                    res = final_choice["res"]
                    if res is None: # Window closed via X
                        def cancel_ui():
                            lbl_status.configure(text=_("gui.status_wait"), text_color="gray")
                            btn_sync.configure(state="normal")
                        dialog.after(0, cancel_ui)
                        return
                        
                    if not any(res.values()):
                        def empty_ui():
                            lbl_status.configure(text="Aucune action sélectionnée.", text_color="orange")
                            btn_sync.configure(state="normal")
                        dialog.after(0, empty_ui)
                        return

                    def work_ui():
                        lbl_status.configure(text="Synchronisation en cours...", text_color="blue")
                    dialog.after(0, work_ui)
                    
                    mgr.sync(res, selected_categories=selected_cats)
                    
                    def done_ui():
                        lbl_status.configure(text=_("sync.status_finished"), text_color="green")
                        if modal_container[0]:
                            modal_container[0].log_msg("✅ " + _("sync.status_finished"))
                            modal_container[0].btn_cancel.configure(state="normal", text=_("web.btn_close"), fg_color="green")
                    dialog.after(0, done_ui)
                    
                    # Refresh library logic
                    if res['pull']:
                        try:
                            import urllib.request
                            req = urllib.request.Request("http://127.0.0.1:8000/api/local/refresh_from_sidecars", method="POST")
                            with urllib.request.urlopen(req, timeout=5) as response:
                                pass
                        except: pass
                    
                    # Restart logic for EXE update
                    if res['pull'] and any("GuitarPracticeTool.exe" in p for p in res['pull']):
                        script = mgr.generate_bootstrapper_script()
                        import tkinter.messagebox
                        if tkinter.messagebox.askyesno("Mise à jour disponible", "Une nouvelle version de l'application a été téléchargée. Voulez-vous redémarrer pour l'installer ?"):
                            lbl_status.configure(text="Redémarrage pour mise à jour...", text_color="red")
                            import subprocess
                            subprocess.Popen(script, shell=True)
                            dialog.destroy()
                            self.quit_app()

                except Exception as e:
                    import traceback
                    logging.warning(f"[SYNC] Erreur critique durant la synchronisation : {e}")
                    logging.warning(traceback.format_exc())
                    lbl_status.configure(text=f"Erreur: {str(e)}", text_color="red")
                finally:
                    btn_sync.configure(state="normal")
            
            threading.Thread(target=_thread, daemon=True).start()

        btn_sync = ctk.CTkButton(tab_sync, text=_("sync.btn_analyze"), command=run_sync, fg_color="#0066cc", hover_color="#004499", height=32)
        btn_sync.pack(pady=(10, 5))
        ctk.CTkButton(dialog, text=_("web.btn_close"), command=dialog.destroy, fg_color="transparent", border_width=1, text_color="gray").pack(pady=5)

    def on_device_saved(self):
        # Reload definitions
        self.device_manager.load_all_definitions()
        self.update_device_def()
        # Update Main UI Frame
        if hasattr(self, 'virtual_pedalboard'):
            self.virtual_pedalboard.set_device_def(self.current_device_def)
        self.refresh_ui_for_profile()

    def create_default_profile(self):
        default = {
            "name": "Global / Desktop",
            "app_context": "",
            "window_title_filter": "",
            "target_volume": "",
            "mappings": []
        }
        self.profile_manager.save_profile(default)
        self.profiles = self.profile_manager.load_all_profiles()
        self.update_profile_combo()
        self.select_profile_by_name(default["name"])

    def update_profile_combo(self):
        names = [p["name"] for p in self.profiles]
        self.profile_combo.configure(values=names)

    def select_profile_by_name(self, name):
        self.log_debug(f"select_profile_by_name called: {name} (AppID: {id(self)})")
        new_prof = next((p for p in self.profiles if p["name"] == name), None)
        if new_prof:
             self.log_debug(f"Found Profile Object: {new_prof.get('name')} (ID: {id(new_prof)})")
             self.profile_combo.set(name) # Update combo box to reflect selection
        else:
             self.log_debug(f"Profile Object NOT FOUND for: {name}")
             # Fallback to first profile if not found, or clear selection
             if self.profiles:
                 self.profile_combo.set(self.profiles[0]["name"])
                 new_prof = self.profiles[0]
             else:
                 self.profile_combo.set("") # Clear selection if no profiles

        self.current_profile = new_prof
        if self.action_handler:
            self.action_handler.set_current_profile(new_prof)
            
        self.refresh_ui_for_profile()

    def on_profile_change(self, choice):
        self.select_profile_by_name(choice)

    def reload_and_refresh(self):
        """Reloads profiles from manager (disk), re-syncs current profile, and refreshes UI."""
        print("[GUI] Reloading profiles and refreshing UI...")
        
        # 1. Update List from Manager (Manager already reloaded from disk on save)
        self.profiles = self.profile_manager.profiles
        
        # 2. Re-acquire Current Profile Object (Sync Memory)
        if self.current_profile:
            # FIX: Use NAME as key, because ID does not exist in our simple JSONs
            current_name = self.current_profile.get("name")
            found = next((p for p in self.profiles if p.get("name") == current_name), None)
            
            if found:
                self.current_profile = found
                self.log_debug(f"Synced current profile: {found.get('name')}")
            else:
                self.log_debug(f"Warning: Current profile '{current_name}' not found after reload (Renamed?)")
                # Fallback: Don't change self.current_profile immediately, or handle gracefully
                # If not found, it might have been deleted? But we just saved it.
                # Just keep the old object reference as a fallback? No, that breaks sync.
                # If save succeeded, it MUST be there.
                pass
        
        # 3. Refresh UI
        self.refresh_ui_for_profile()
        
        # 4. Notify Server (TODO: Add Broadcast Callback if needed)
        # For now, UI refresh is key.

    def refresh_ui_for_profile(self):
        if not self.current_profile: return

        # Synchroniser le périphérique associé à ce profil
        device_name = self.current_profile.get("device_name")
        none_lbl = _("gui.lbl_none")
        if not device_name:
            # Fallback rétrocompatible vers les paramètres globaux (ou "Aucun")
            mode = self.settings.get("connection_mode", "MIDO")
            device_name = self.settings.get("midi_device_name_ble" if mode == "BLE" else "midi_device_name_usb", self.settings.get("midi_device_name", none_lbl))
            if not device_name:
                device_name = none_lbl
            self.current_profile["device_name"] = device_name
            try:
                self.profile_manager.save_profile(self.current_profile)
            except Exception as e:
                print(f"[GUI] Error auto-saving profile with default device: {e}")

        # Mettre à jour l'affichage de la combo profile_device_combo
        if hasattr(self, "profile_device_combo"):
            # S'assurer que les valeurs proposées sont à jour
            self.update_profile_device_combo_list()
            
            current_values = list(self.profile_device_combo.cget("values") or [])
            if device_name not in current_values:
                current_values.insert(0, device_name)
                self.profile_device_combo.configure(values=current_values)
            self.profile_device_combo.set(device_name)

        self.update_device_def()

        # Update Pedalboard
        if hasattr(self, 'virtual_pedalboard'):
            self.virtual_pedalboard.set_device_def(self.current_device_def)
            self.virtual_pedalboard.set_profile(self.current_profile)

        self.entry_app_rule.delete(0, "end")
        self.entry_app_rule.insert(0, self.current_profile.get("app_context", ""))

        self.entry_title_rule.delete(0, "end")
        self.entry_title_rule.insert(0, self.current_profile.get("window_title_filter", ""))
        
        self.entry_vol_rule.delete(0, "end")
        self.entry_vol_rule.insert(0, self.current_profile.get("target_volume", ""))

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.mapping_indicators = {}

        # Configuration de la grille unifiée de la table (comme un tableau Excel)
        self.scrollable_frame.grid_columnconfigure(0, weight=0, minsize=40)  # État / LED
        self.scrollable_frame.grid_columnconfigure(1, weight=3, minsize=150) # Nom du Mapping
        self.scrollable_frame.grid_columnconfigure(2, weight=2, minsize=100) # Bouton Physique
        self.scrollable_frame.grid_columnconfigure(3, weight=4, minsize=200) # Action / Détails
        self.scrollable_frame.grid_columnconfigure(4, weight=0, minsize=32)  # Action ▲
        self.scrollable_frame.grid_columnconfigure(5, weight=0, minsize=32)  # Action ▼
        self.scrollable_frame.grid_columnconfigure(6, weight=0, minsize=32)  # Action ✎
        self.scrollable_frame.grid_columnconfigure(7, weight=0, minsize=32)  # Action X

        # --- En-têtes de colonnes (Style Tableau Excel Professionnel) ---
        lbl_h_led = ctk.CTkLabel(self.scrollable_frame, text=_("gui.col_state"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY, anchor="w")
        lbl_h_led.grid(row=0, column=0, padx=(10, 5), pady=(8, 4), sticky="w")
        
        lbl_h_name = ctk.CTkLabel(self.scrollable_frame, text=_("gui.col_name"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY, anchor="w")
        lbl_h_name.grid(row=0, column=1, padx=5, pady=(8, 4), sticky="w")
        
        lbl_h_btn = ctk.CTkLabel(self.scrollable_frame, text=_("gui.col_btn"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY, anchor="w")
        lbl_h_btn.grid(row=0, column=2, padx=10, pady=(8, 4), sticky="w")
        
        lbl_h_details = ctk.CTkLabel(self.scrollable_frame, text=_("gui.col_details"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY, anchor="w")
        lbl_h_details.grid(row=0, column=3, padx=10, pady=(8, 4), sticky="w")
        
        lbl_h_actions = ctk.CTkLabel(self.scrollable_frame, text=_("gui.col_actions"), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY, anchor="center")
        lbl_h_actions.grid(row=0, column=4, columnspan=4, padx=5, pady=(8, 4), sticky="ew")

        # Ligne de séparation sous les en-têtes
        sep_h = ctk.CTkFrame(self.scrollable_frame, height=2, fg_color=BORDER_COLOR)
        sep_h.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(2, 6))

        mappings = self.current_profile.get("mappings", [])
        for index, mapping in enumerate(mappings):
            self.create_mapping_card(index, mapping)

    def create_mapping_card(self, index, mapping):
        grid_row = index * 2 + 2

        # Col 0: LED Indicator
        lbl_led = ctk.CTkLabel(self.scrollable_frame, text="●", font=ctk.CTkFont(size=14), text_color=LED_OFF, width=20, anchor="w")
        lbl_led.grid(row=grid_row, column=0, padx=(10, 5), pady=6, sticky="w")
        
        cc = mapping.get('midi_cc')
        if cc is not None:
             self.mapping_indicators.setdefault(cc, []).append(lbl_led)
             
        # Col 1: Name (No aggressive truncation, left justified, sticky ew)
        raw_name = mapping.get('name', '???')
        lbl_name = ctk.CTkLabel(self.scrollable_frame, text=raw_name, anchor="w", justify="left", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_PRIMARY)
        lbl_name.grid(row=grid_row, column=1, padx=5, pady=6, sticky="ew")
        
        # Col 2: Button Name (No aggressive truncation, left justified, sticky ew)
        btn_label = f"CC {cc}"
        if self.current_device_def:
             match = next((b for b in self.current_device_def['buttons'] if b['cc'] == cc), None)
             if match:
                 btn_label = match['label']
                 
                 # Récupération du canal défini sur la télécommande pour ce bouton physique
                 map_ch = match.get('midi_channel')
                 if map_ch is not None and int(map_ch) != 16:
                      btn_label += f" (Ch {map_ch})"
             
        lbl_btn = ctk.CTkLabel(self.scrollable_frame, text=btn_label, anchor="w", justify="left", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_SECONDARY)
        lbl_btn.grid(row=grid_row, column=2, padx=10, pady=6, sticky="ew")
        
        # Col 3: Details (No aggressive truncation, left justified, sticky ew)
        raw_details = f"({cc}) {mapping.get('action_value')}"
        lbl_details = ctk.CTkLabel(self.scrollable_frame, text=raw_details, text_color=ACCENT_LIGHT, font=ctk.CTkFont(family="Consolas", size=11), anchor="w", justify="left")
        lbl_details.grid(row=grid_row, column=3, padx=10, pady=6, sticky="ew")
        
        # Col 4: Up
        btn_up = ctk.CTkButton(self.scrollable_frame, text="▲", width=24, height=22, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY,
                               font=ctk.CTkFont(size=10), command=lambda i=index: self.move_mapping_up(i))
        btn_up.grid(row=grid_row, column=4, padx=2, pady=6)

        # Col 5: Down
        btn_down = ctk.CTkButton(self.scrollable_frame, text="▼", width=24, height=22, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY,
                                 font=ctk.CTkFont(size=10), command=lambda i=index: self.move_mapping_down(i))
        btn_down.grid(row=grid_row, column=5, padx=2, pady=6)

        # Col 6: Edit
        edit_btn = ctk.CTkButton(self.scrollable_frame, text="✎", width=24, height=22, fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY,
                                 font=ctk.CTkFont(size=10), command=lambda i=index: self.edit_mapping(i))
        edit_btn.grid(row=grid_row, column=6, padx=2, pady=6)

        # Col 7: Del
        del_btn = ctk.CTkButton(self.scrollable_frame, text="X", width=24, height=22, fg_color="#EF4444", hover_color="#DC2626", text_color="#FFFFFF",
                                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), command=lambda i=index: self.delete_mapping(i))
        del_btn.grid(row=grid_row, column=7, padx=(2, 10), pady=6)

        # Subtle separator line under the row
        sep_row = grid_row + 1
        sep = ctk.CTkFrame(self.scrollable_frame, height=1, fg_color=BORDER_COLOR)
        sep.grid(row=sep_row, column=0, columnspan=8, sticky="ew", pady=(4, 0))

    # --- Actions Profils ---
    def create_new_profile(self):
        ProfileEditorDialog(self, None, self.on_profile_created)

    def on_profile_created(self, name, vol, device):
        # Vérification des doublons
        for p in self.profiles:
            if p["name"] == name:
                CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_profile_exists"))
                return

        new_p = {
            "name": name,
            "app_context": f"{name.lower()}.exe",
            "window_title_filter": "",
            "target_volume": vol,
            "device_name": device,
            "mappings": []
        }

        if self.profile_manager.save_profile(new_p):
            self.profiles = self.profile_manager.load_all_profiles()
            self.update_profile_combo()
            self.select_profile_by_name(name)

    def create_profile_by_name(self, name, auto_context=False):
        """Creates a profile programmatically and selects it."""
        # Check duplication
        for p in self.profiles:
            if p["name"] == name:
                self.select_profile_by_name(name)
                return

        context = ""
        if auto_context:
            context = f"{name.lower()}.exe"

        new_p = {
            "name": name,
            "app_context": context,
            "window_title_filter": "",
            "target_volume": "",
            "device_name": _("gui.lbl_none"),
            "mappings": []
        }

        if self.profile_manager.save_profile(new_p):
            self.profiles = self.profile_manager.load_all_profiles()
            self.update_profile_combo()
            self.select_profile_by_name(name)

    def duplicate_current_profile(self):
        if not self.current_profile: return

        old_name = self.current_profile["name"]

        dialog = ctk.CTkInputDialog(text=_("gui.msg_new_profile_name"), title=_("gui.title_dup_profile"))

        new_name = dialog.get_input()
        if not new_name: return

        # Check if exists
        for p in self.profiles:
            if p["name"] == new_name:
                CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_profile_exists"))
                return

        # Deep copy manually
        import copy
        new_profile = copy.deepcopy(self.current_profile)
        new_profile["name"] = new_name

        if self.profile_manager.save_profile(new_profile):
            self.profiles = self.profile_manager.load_all_profiles()
            self.update_profile_combo()
            self.select_profile_by_name(new_name)
            CTkMessageBox.show_info(_("gui.msg_success"), f"{_('gui.msg_profile_duplicated')} : {new_name}")

    def edit_current_profile(self):
        if not self.current_profile: return
        ProfileEditorDialog(self, self.current_profile, self.on_profile_edited)

    def on_profile_edited(self, new_name, new_vol, new_device):
        old_name = self.current_profile.get("name")
        
        # Check name collision
        if new_name != old_name:
            for p in self.profiles:
                if p["name"] == new_name:
                    CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_profile_exists"))
                    return
        
        self.current_profile["name"] = new_name
        self.current_profile["target_volume"] = new_vol
        self.current_profile["device_name"] = new_device
        
        # Save new
        if self.profile_manager.save_profile(self.current_profile):
            # If renamed, delete the old file
            if old_name and old_name != new_name:
                self.profile_manager.delete_profile(old_name)
            
            self.profiles = self.profile_manager.load_all_profiles()
            self.update_profile_combo()
            self.select_profile_by_name(new_name)

    def delete_current_profile(self):
        if not self.current_profile: return
        name = self.current_profile["name"]
        if CTkMessageBox.ask_yes_no(_("gui.msg_confirm"), f"{_('gui.msg_delete_profile')} '{name}'?"):
            self.profile_manager.delete_profile(name)
            self.profiles = self.profile_manager.load_all_profiles()
            self.update_profile_combo()
            if self.profiles:
                self.select_profile_by_name(self.profiles[0]["name"])
            else:
                self.create_default_profile()

    def apply_rules_to_profile(self):
        if not self.current_profile: return
        self.current_profile["app_context"] = self.entry_app_rule.get()
        self.current_profile["window_title_filter"] = self.entry_title_rule.get()
        self.current_profile["target_volume"] = self.entry_vol_rule.get()
        self.profile_manager.save_profile(self.current_profile)
        self.btn_apply_rules.configure(fg_color="#059669")
        self.after(500, lambda: self.btn_apply_rules.configure(fg_color="#10B981"))

    # --- Shortcuts Memo ---
    def open_shortcuts_dialog(self):
        if not self.current_profile: return
        text = self.current_profile.get("shortcuts_text", "")
        ShortcutsDialog(self, text, self.on_shortcuts_saved)

    def on_shortcuts_saved(self, text):
        if self.current_profile:
            self.current_profile["shortcuts_text"] = text
            self.profile_manager.save_profile(self.current_profile)

    # --- Actions Mappings ---
    def open_add_dialog(self):
        self.log_debug("open_add_dialog called")
        try:
            if not self.current_profile:
                 self.log_debug("No profile selected")
                 CTkMessageBox.show_info(_("gui.msg_warning"), _("gui.msg_no_profile_selected"))
                 return

            # PAUSE MONITORING to prevent conflict
            if hasattr(self, 'context_monitor') and self.context_monitor:
                self.log_debug("Pausing Monitor...")
                self.context_monitor.pause_monitoring(True)
            else:
                self.log_debug("Context Monitor NOT found or None")

            ctx = {
                "app_context": self.current_profile.get("app_context", ""),
                "window_title_filter": self.current_profile.get("window_title_filter", "")
            }
            self.log_debug(f"Creating MappingDialog with ctx: {ctx}")
            
            dialog = MappingDialog(self, self.add_mapping_callback, self.current_device_def, profile_context=ctx, action_handler=self.action_handler)
            
            self.log_debug("MappingDialog created, binding protocol...")
            dialog.protocol("WM_DELETE_WINDOW", lambda: self.on_mapping_dialog_close(dialog))
            self.log_debug("Dialog open sequence complete.")
            
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            self.log_debug(f"FATAL ERROR in open_add_dialog: {e}\n{err_msg}")
            
            # RESUME if error
            if hasattr(self, 'context_monitor') and self.context_monitor:
                self.context_monitor.pause_monitoring(False)
            
            CTkMessageBox.show_error(_("gui.msg_error"), f"{_('gui.msg_open_error')}:\n{e}")

    def on_mapping_dialog_close(self, dialog):
        # RESUME MONITORING
        if hasattr(self, 'context_monitor') and self.context_monitor:
            self.context_monitor.pause_monitoring(False)
        dialog.destroy()

    def add_mapping_callback(self, data):
        if self.current_profile:
            self.current_profile["mappings"].append(data)
            self.profile_manager.save_profile(self.current_profile)
            self.reload_and_refresh()
            
            # RESUME MONITORING (Success Case)
            if hasattr(self, 'context_monitor') and self.context_monitor:
                self.context_monitor.pause_monitoring(False)

    def edit_mapping(self, index):
        if not self.current_profile: return
        data = self.current_profile["mappings"][index]
        
        # PAUSE MONITORING
        if hasattr(self, 'context_monitor') and self.context_monitor:
            self.context_monitor.pause_monitoring(True)

        ctx = {
            "app_context": self.current_profile.get("app_context", ""),
            "window_title_filter": self.current_profile.get("window_title_filter", "")
        }
        dialog = MappingDialog(self, lambda d: self.update_mapping(index, d), self.current_device_def, initial_data=data, profile_context=ctx, action_handler=self.action_handler)
        # Handle Cancel/Close via X
        dialog.protocol("WM_DELETE_WINDOW", lambda: self.on_mapping_dialog_close(dialog))

    def update_mapping(self, index, data):
        if self.current_profile:
            self.current_profile["mappings"][index] = data
            self.profile_manager.save_profile(self.current_profile)
            self.reload_and_refresh()

            # RESUME MONITORING (Success Case)
            if hasattr(self, 'context_monitor') and self.context_monitor:
                self.context_monitor.pause_monitoring(False)

    def delete_mapping(self, index):
        if self.current_profile:
            del self.current_profile["mappings"][index]
            self.profile_manager.save_profile(self.current_profile)
            self.reload_and_refresh()

    def move_mapping_up(self, index):
        if not self.current_profile or index <= 0: return
        mappings = self.current_profile["mappings"]
        mappings[index], mappings[index-1] = mappings[index-1], mappings[index]
        self.profile_manager.save_profile(self.current_profile)
        self.reload_and_refresh()

    def move_mapping_down(self, index):
        if not self.current_profile: return
        mappings = self.current_profile["mappings"]
        if index >= len(mappings) - 1: return
        mappings[index], mappings[index+1] = mappings[index+1], mappings[index]
        self.profile_manager.save_profile(self.current_profile)
        self.reload_and_refresh()

    # --- Save ---
    def save_all(self, silent=False):
        # We NO LONGER read from device_combo here!
        # The combo box might still be showing "FS-1-WL" 
        # while taking 800ms to switch to "AIRSTEP" after a mode change.
        # Reading it here would aggressively overwrite the correct memory.
        # self.settings["midi_device_name"] is already maintained by change_mode and _finalize_refresh.
        
        try:
            from config_manager import ConfigManager
            cm = ConfigManager()
            for k, v in self.settings.items():
                k_upper = k.upper()
                # PROTECTION : Ne jamais sauvegarder ou écraser des clés API ou secrètes depuis la GUI native
                is_secret = "API_KEY" in k_upper or "SECRET" in k_upper or "KEY" in k_upper or k_upper in ["YOUTUBE_API_KEY", "GETSONGBPM_API_KEY", "GETSONG_API_KEY"]
                if is_secret:
                    continue
                cm.set(k, v)
        except Exception as e:
            if not silent: CTkMessageBox.show_error(_("gui.msg_error"), f"{_('gui.msg_config_error')}: {e}")
            return

        try:
            for p in self.profiles:
                self.profile_manager.save_profile(p)
            if not silent: CTkMessageBox.show_info(_("gui.msg_success"), _("gui.msg_config_saved"))
        except Exception as e:
            if not silent: CTkMessageBox.show_error(_("gui.msg_error"), f"{_('gui.msg_profiles_error')}: {e}")

    # --- Remote Control ---
    def toggle_remote_control(self):
        # If open, close it and show nothing (like on_remote_close)
        if hasattr(self, 'remote_win') and self.remote_win:
            try:
                if self.remote_win.winfo_exists():
                    self.remote_win.destroy()
                    self.remote_win = None
                    return
            except:
                self.remote_win = None
        
        # If closed, open it
        self.open_remote_control()

    def open_remote_control(self):
        if not self.current_device_def:
            CTkMessageBox.show_error(_("gui.msg_error"), _("gui.msg_no_device_def"))
            return

        # Singleton Check
        if hasattr(self, 'remote_win') and self.remote_win:
            try:
                if self.remote_win.winfo_exists():
                    # Déjà ouvert : on restaure
                    self.withdraw() 
                    self.remote_win.deiconify()
                    self.remote_win.lift()
                    self.remote_win.focus_force()
                    return
                else:
                    self.remote_win = None # Cleaning up dead reference
            except:
                self.remote_win = None

        # Hide Main Window
        self.withdraw()

        # Create Remote
        self.remote_win = RemoteControl(
            self,
            self.current_device_def,
            self.current_profile,
            callback_press=self.simulate_midi_press,
            callback_close=self.on_remote_close,
            callback_open_conf=lambda: (self.deiconify(), self.lift(), self.focus_force()),
            callback_open_web=self.open_web
        )
        # Start monitoring background context
        self.after(500, self._monitor_remote_context)

    def force_profile_switch(self, profile_name):
        """Called by LibraryManager when launching an app"""
        found = next((p for p in self.profiles if p.get("name") == profile_name), None)
        if found:
            self.manual_override_profile = found
            self.log_debug(f"FORCE PROFILE: {profile_name}")
            # Immediate Update
            self.current_profile = found
            if self.remote_win: self.remote_win.set_profile(found)
        else:
            self.log_debug(f"Cannot force profile: {profile_name} not found")

    def _monitor_remote_context(self):
        # Stop if remote is closed
        if not self.remote_win or not self.remote_win.winfo_exists():
            return

        # 1. Check Manual Override
        if self.manual_override_profile:
            # Check if we should release the lock?
            # For now, we assume user wants to stay on it until they change focus manually?
            # Or implementing a "Release" logic.
            # Simpler: If we are locked, we check if the active window is DIFFERENT from the locked context.
            # But the requirement is strict: "Force le changement".
            # We keep it locked. But how to unlock?
            # Let's say if user clicks on the remote, we are good.
            # If user switches window naturally, we might want to unlock.
            # But "Smart Launcher" implies we want the controls for that app.

            # Re-confirm logic: "set_manual_override".
            # We stick to the override until explicitly cleared.
            pass
        else:
            # 2. Auto-Detect
            if self.action_handler:
                # Avoid detecting the remote itself
                ignore = ["Remote -", "Midi-Kbd Remote", "Midi-Kbd Control Studio"]

                # Find best profile for current active window
                new_profile = self.action_handler.find_matching_profile(self.profiles, ignore_titles=ignore)

                if new_profile and new_profile != self.current_profile:
                    # Update Remote UI
                    self.remote_win.set_profile(new_profile)
                    # Update internal state for click handling
                    self.current_profile = new_profile

        # Loop
        self.after(500, self._monitor_remote_context)

    def on_remote_close(self):
        # self.deiconify() # On ne ré-ouvre PAS le backend automatiquement
        self.remote_win = None
        # Monitor loop stops automatically via winfo_exists check

    # --- Scan Tools ---
    def scan_window(self, target_type):
        btn = self.btn_scan_app if target_type == "app" else self.btn_scan_title
        original_text = btn.cget("text")

        self.attributes("-topmost", True)

        def _scan_thread():
            for i in range(3, 0, -1):
                btn.configure(text=f"{i}...")
                time.sleep(1)

            self.after(0, lambda: self.attributes("-topmost", False))

            try:
                win = gw.getActiveWindow()
                if win:
                    titre = win.title
                    if target_type == "title":
                        cleaned_title = titre
                        if "YouTube" in titre:
                            cleaned_title = "YouTube"
                        else:
                            suffixes = [" - Google Chrome", " - Mozilla Firefox", " - Microsoft Edge", " - Opera"]
                            for suffix in suffixes:
                                if cleaned_title.endswith(suffix):
                                    cleaned_title = cleaned_title[:-len(suffix)]
                                    break
                        self.after(0, lambda: self._update_entry(self.entry_title_rule, cleaned_title))
                    else:
                        val = titre
                        if "Chrome" in titre or "Google" in titre: val = "chrome.exe"
                        elif "VLC" in titre: val = "vlc.exe"
                        elif "Moises" in titre: val = "moises.exe"
                        elif "Reaper" in titre: val = "reaper.exe"
                        self.after(0, lambda: self._update_entry(self.entry_app_rule, val))
            except Exception as e:
                print(e)
            self.after(0, lambda: btn.configure(text=original_text))
        threading.Thread(target=_scan_thread, daemon=True).start()

    def _update_entry(self, entry_widget, value):
        entry_widget.delete(0, "end")
        entry_widget.insert(0, value)
        # Auto apply
        self.apply_rules_to_profile()





    def change_profile_device(self, choice):
        if not choice or not self.current_profile: return
        self.current_profile["device_name"] = choice
        
        try:
            self.profile_manager.save_profile(self.current_profile)
        except Exception as e:
            print(f"[GUI] Error saving profile device change: {e}")
            
        self.update_device_def()
        
        # Feedback UI pour la télécommande virtuelle
        if hasattr(self, 'virtual_pedalboard'):
            self.virtual_pedalboard.set_device_def(self.current_device_def)
            self.virtual_pedalboard.set_profile(self.current_profile)

    def update_profile_device_combo_list(self):
        if not hasattr(self, "profile_device_combo"):
            return
        none_lbl = _("gui.lbl_none")
        devices = [d.get("name") for d in self.device_manager.definitions]
        device_values = [none_lbl] + devices
        
        # Conserver la sélection actuelle
        current_sel = self.profile_device_combo.get()
        
        self.profile_device_combo.configure(values=device_values)
        if current_sel in device_values:
            self.profile_device_combo.set(current_sel)
        else:
            self.profile_device_combo.set(none_lbl)

    def midi_callback(self, msg):
        """Callback principal du moteur MIDI"""
        if not msg: return
        
        # On ne traite que les Control Change pour l'instant
        if msg.type == 'control_change':
            cc = msg.control
            val = msg.value
            chan = msg.channel + 1 # 1-based for display
            
            # Action Handler
            if self.action_handler:
                print(f"[MAIN] Message MIDI reçu de l'engine: {msg}") # Diagnostic Log
                self.action_handler.execute(cc, val, chan, self.profiles, self.manual_override_profile, midi_manager=self.midi_manager)

    def on_data_received(self, cc=None, value=None, channel=None):
        if cc is not None:
            # Update LCD
            self.lbl_monitor_cc.configure(text=f"CC: {cc}")
            self.lbl_monitor_ch.configure(text=f"CH: {channel}" if channel else "CH: ?")

            # Flash LCD text
            try:
                self.lbl_monitor_cc.configure(text_color="#00FF00")
                self.after(100, lambda: self.lbl_monitor_cc.configure(text_color=("black", "white")))

                # Flash Connection LED (Activity Confirmation)
                self.lbl_conn_led.configure(text_color="#00FF00")
                self.after(100, lambda: self.lbl_conn_led.configure(text_color="green"))
            except: pass

            self.flash_mapping_row(cc)

            # Flash Remote
            if hasattr(self, 'remote_win') and self.remote_win and self.remote_win.winfo_exists():
                self.remote_win.flash_button(cc)

            # Flash Main UI
            if hasattr(self, 'virtual_pedalboard'):
                self.virtual_pedalboard.flash_button(cc)

    def flash_mapping_row(self, cc):
        indicators = self.mapping_indicators.get(cc, [])
        for lbl in indicators:
             try:
                # Flash Color: Electric Neon Cyan
                lbl.configure(text_color="#00E5FF")
                self.after(200, lambda l=lbl: l.configure(text_color=LED_OFF))
             except: pass

    def _monitor_connection_status(self):
        """Vérifie périodiquement l'état de la connexion d'après la télécommande active"""
        conn_type = "Virtuel"
        if hasattr(self, 'current_device_def') and self.current_device_def:
            conn_type = self.current_device_def.get("connection_type", "Virtuel")
            
        none_lbl = _("gui.lbl_none")
        if (hasattr(self, 'current_device_def') and self.current_device_def and 
            self.current_device_def.get("name") == none_lbl):
            conn_type = "Virtuel"

        if conn_type == "Virtuel":
            self.midi_manager.set_scanning(False)
            self.update_status(True, is_virtual=True)
        else:
            # Périphérique physique requis
            self.midi_manager.set_scanning(True)
            connected = self.midi_manager.is_connected
            self.update_status(connected, is_virtual=False)
        
        # Loop 1s
        self.after(1000, self._monitor_connection_status)

    def update_status(self, connected, message=None, is_virtual=False):
        # Initialisation ou nettoyage des widgets dynamiques
        if not hasattr(self, "dynamic_status_widgets"):
            self.dynamic_status_widgets = []
        for widget in self.dynamic_status_widgets:
            try:
                widget.destroy()
            except:
                pass
        self.dynamic_status_widgets.clear()

        if is_virtual:
            # Réafficher les labels de base si besoin
            self.lbl_conn_led.pack(side="left", padx=(0, 5))
            self.lbl_conn_text.pack(side="left")
            self.lbl_conn_led.configure(text_color="#00E5FF") # Bleu fluo
            self.lbl_conn_text.configure(text=_("gui.lbl_virtual_mode"))
            return

        # Si le mode de connexion physique est actif, on récupère le statut individuel de chaque périphérique
        providers_status = []
        if hasattr(self, "midi_manager") and self.midi_manager:
            providers_status = self.midi_manager.get_providers_status()

        if not providers_status:
            # Mode de connexion par défaut ou aucun périphérique
            self.lbl_conn_led.pack(side="left", padx=(0, 5))
            self.lbl_conn_text.pack(side="left")
            conn_type = "Virtuel"
            if hasattr(self, 'current_device_def') and self.current_device_def:
                conn_type = self.current_device_def.get("connection_type", "Virtuel")
            if conn_type == "Virtuel":
                self.lbl_conn_led.configure(text_color="#00E5FF") # Bleu fluo
                self.lbl_conn_text.configure(text=_("gui.lbl_virtual_mode"))
            else:
                self.lbl_conn_led.configure(text_color=LED_DISCONNECTED)
                self.lbl_conn_text.configure(text=_("gui.lbl_disconnected"))
            return

        # Si nous sommes en mode multi-périphériques / composite
        num_connected = sum(1 for p in providers_status if p.get("connected", False))
        num_total = len(providers_status)

        # Détermination de la couleur de la LED globale
        if num_connected == num_total:
            global_led_color = LED_CONNECTED
        elif num_connected > 0:
            global_led_color = "#FFA500" # Orange
        else:
            global_led_color = LED_DISCONNECTED
        self.lbl_conn_led.configure(text_color=global_led_color)

        # C'est du multi-périphérique : on masque les labels standard de connexion mono-périphérique
        # pour éviter d'avoir la LED globale ● doublée
        self.lbl_conn_led.pack_forget()
        self.lbl_conn_text.pack_forget()

        # Construction dynamique des labels de chaque périphérique
        for idx, p in enumerate(providers_status):
            p_name = p.get("name", "Appareil")
            p_connected = p.get("connected", False)
            
            # 1. LED pour ce périphérique
            led_color = "#00FF00" if p_connected else "#FF0000"
            led_lbl = ctk.CTkLabel(
                self.conn_frame, 
                text="●", 
                font=ctk.CTkFont(size=14), 
                text_color=led_color
            )
            led_lbl.pack(side="left", padx=(0, 2))
            self.dynamic_status_widgets.append(led_lbl)

            # 2. Nom du périphérique
            name_lbl = ctk.CTkLabel(
                self.conn_frame, 
                text=p_name, 
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), 
                text_color=TEXT_PRIMARY
            )
            name_lbl.pack(side="left", padx=(0, 5))
            self.dynamic_status_widgets.append(name_lbl)

            # 3. Séparateur (sauf pour le dernier)
            if idx < num_total - 1:
                sep_lbl = ctk.CTkLabel(
                    self.conn_frame, 
                    text="|", 
                    font=ctk.CTkFont(family="Segoe UI", size=11), 
                    text_color="#555555"
                )
                sep_lbl.pack(side="left", padx=(2, 5))
                self.dynamic_status_widgets.append(sep_lbl)

    def check_startup_status(self):
        startup_dir = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        self.startup_bat = os.path.join(startup_dir, "AirstepSmartControl.bat")
        return os.path.exists(self.startup_bat)

    def toggle_startup(self):
        if self.startup_var.get():
            import sys
            if getattr(sys, 'frozen', False):
                 target = f'"{sys.executable}"'
            else:
                 cwd = os.getcwd()
                 target = f'"{sys.executable}" "{os.path.join(cwd, "src", "main.py")}"'
            content = f'@echo off\ncd /d "{os.getcwd()}"\nstart "" {target}'
            try:
                with open(self.startup_bat, "w") as f:
                    f.write(content)
            except Exception as e:
                CTkMessageBox.show_error(_("gui.msg_error"), f"{_('gui.msg_startup_error')}: {e}")
        else:
            if os.path.exists(self.startup_bat):
                try: os.remove(self.startup_bat)
                except: pass

    # --- Tray System ---
    def setup_tray(self):
        def _create_tray():
            try:
                # Use the robust path directly
                image = Image.open(ICON_PNG_PATH)
                menu = pystray.Menu(
                    pystray.MenuItem(_("gui.menu_remote"), self.open_remote_from_tray, default=True),
                    pystray.MenuItem(_("gui.menu_config"), self.open_conf_from_tray),
                    pystray.MenuItem(_("gui.menu_web"), self.open_web),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(_("gui.menu_quit"), self.quit_app)
                )
                self.tray_icon = pystray.Icon("GuitarPracticeTool", image, "GuitarPracticeTool", menu)
                self.tray_icon.run()
            except Exception as e:
                self.log_debug(f"Erreur Tray: {e}")
        threading.Thread(target=_create_tray, daemon=True).start()

    def open_remote_from_tray(self, icon=None, item=None):
        self.after(0, self.open_remote_control)

    def open_conf_from_tray(self, icon=None, item=None):
        self.after(0, lambda: (self.deiconify(), self.lift(), self.focus_force()))

    def open_web(self, icon=None, item=None):
        try:
            port = self.settings.get("app_port", 8000)
            # Default is 8000 if not in settings, but ConfigManager might have it.
            # Ideally we check where 'config' variable ended up, but here we use self.settings dict.
            # self.settings is loaded from config.json.
            url = f"http://127.0.0.1:{port}"
            webbrowser.open(url)
        except: pass

    def minimize_to_tray(self):
        self.withdraw()

    def restore_window(self, icon=None, item=None):
        self.after(0, self._restore_main_thread)

    def _restore_main_thread(self):
        # Prioritize restoring the Remote if it exists
        if hasattr(self, 'remote_win') and self.remote_win and self.remote_win.winfo_exists():
            self.remote_win.deiconify()
            self.remote_win.lift()
            self.remote_win.focus_force()
        else:
            self.deiconify()
            self.lift()
            self.focus_force()

    def simulate_midi_press(self, cc):
        """Simule l'appui physique sur une pédale (Feedback GUI + Action)"""
        # 1. Feedback GUI (LEDs, LCD)
        self.on_data_received(cc, 16) # Canal 16 par défaut pour la simulation

        # 2. Exécution réelle de l'action
        # On simule un message VALUE=127 (Press)
        # On force le profil actuel pour activer le "Focus Switch"
        if self.action_handler:
            self.log_debug(f"SIMULATE PRESS: AppID={id(self)}, CurrentProfile={self.current_profile.get('name') if self.current_profile else 'None'}, ID={id(self.current_profile) if self.current_profile else 'None'}")
            self.action_handler.execute(cc, 127, 16, self.profiles, force_target_profile=self.current_profile, midi_manager=self.midi_manager)

    def quit_app(self, icon=None, item=None):
        if self.tray_icon: self.tray_icon.stop()
        # Shutdown Manager
        if self.midi_manager and self.midi_manager.current_provider:
             self.midi_manager.current_provider.stop()
             
        if self.context_monitor: self.context_monitor.stop()
        self.quit()
