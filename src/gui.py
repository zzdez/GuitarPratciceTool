import os
import sys

# V21: Bypass same-origin, CORS and iframe SAMEORIGIN/CSP constraints globally for Songsterr embedding
# Only set environment flags if this is the main GUI process
if "--multiprocessing-fork" not in "".join(sys.argv):
    os.environ["QTWEBENGINE_DISABLE_CONTENT_SECURITY_POLICY"] = "1"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-web-security --allow-running-insecure-content"

import json
import logging
import threading
from PIL import Image

from PySide6.QtCore import QUrl, QObject, Slot, Signal, Qt, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu, QFileDialog, QStyle, QStackedWidget, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLabel, QTabWidget, QTabBar
from PySide6.QtGui import QIcon, QAction, QCursor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEngineScript, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel

from utils import get_app_dir, get_data_dir

def get_resource_path(relative_path):
    """Trouve les fichiers aussi bien en Dev qu'en EXE PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ICON_PNG_PATH = get_resource_path(os.path.join("assets", "icon.png"))
LOGO_PATH = get_resource_path(os.path.join("assets", "logo.png"))

# Managers imports
try:
    from profile_manager import ProfileManager
    from device_manager import DeviceManager, DEFAULT_AIRSTEP_DEF
    from env_manager import EnvManager
    from midi_engine import MidiManager
    from action_handler import ActionHandler
    from library_manager import LibraryManager
    from config_manager import ConfigManager
    from context_monitor import ContextMonitor
except ImportError:
    from src.profile_manager import ProfileManager
    from src.device_manager import DeviceManager, DEFAULT_AIRSTEP_DEF
    from src.env_manager import EnvManager
    from src.midi_engine import MidiManager
    from src.action_handler import ActionHandler
    from src.library_manager import LibraryManager
    from src.config_manager import ConfigManager
    from src.context_monitor import ContextMonitor

from i18n import _

# -------------------------------------------------------------
# THREAD-SAFE NATIVE DIALOGS HELPER
# -------------------------------------------------------------
class DialogHelper(QObject):
    select_folder_signal = Signal(object)
    select_file_signal = Signal(object)

    def __init__(self, parent_win):
        super().__init__()
        self.parent_win = parent_win
        self.select_folder_signal.connect(self._select_folder)
        self.select_file_signal.connect(self._select_file)

    def _select_folder(self, ctx):
        try:
            path = QFileDialog.getExistingDirectory(self.parent_win, "Sélectionner un dossier")
            ctx["path"] = path
        except Exception as e:
            print(f"Select Folder Error: {e}")
        finally:
            ctx["event"].set()

    def _select_file(self, ctx):
        try:
            path, _ = QFileDialog.getOpenFileName(
                self.parent_win,
                "Ajouter un fichier",
                "",
                "Media (*.mp3 *.wav *.flac *.m4a *.mp4 *.mkv *.webm *.ogg);;All (*.*)"
            )
            ctx["path"] = path
        except Exception as e:
            print(f"Select File Error: {e}")
        finally:
            ctx["event"].set()

# -------------------------------------------------------------
# COCKPIT WEB PAGE INTERCEPTOR (Prevents iframe-busting on Songsterr)
# -------------------------------------------------------------
class CockpitWebPage(QWebEnginePage):
    def __init__(self, window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = window

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        url_str = url.toString()
        # If it's an external http/https URL that is not embeddable media or local API
        if url_str.startswith("http") and not self.is_embeddable_media(url_str):
            print(f"[NAV] Intercepted navigation to external: {url_str}")
            # Use app.after or direct call to load external URL
            self.window.load_external_url(url)
            return False # Block it from the main web view
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)

    def is_embeddable_media(self, url_str):
        url_lower = url_str.lower()
        return (
            "youtube.com/embed/" in url_lower or
            "youtube-nocookie.com/embed/" in url_lower or
            "player.vimeo.com/" in url_lower or
            "dailymotion.com/embed/" in url_lower or
            "localhost" in url_lower or
            "127.0.0.1" in url_lower
        )

# -------------------------------------------------------------
# REMOTE WEBVIEW PYTHON BRIDGE (Qt WebChannel)
# -------------------------------------------------------------
class RemoteBridge(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.drag_start_pos = None

    @Slot()
    def start_drag(self):
        self.drag_start_pos = QCursor.pos() - self.window.pos()

    @Slot(int, int)
    def move_drag(self, x, y):
        if self.drag_start_pos is not None:
            self.window.move(QCursor.pos() - self.drag_start_pos)

    @Slot()
    def minimize(self):
        self.window.showMinimized()

    @Slot()
    def close(self):
        self.window.hide()

# -------------------------------------------------------------
# FLOATING BORDERLESS REMOTE CONTROL WINDOW
# -------------------------------------------------------------
class RemoteControlWindow(QMainWindow):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        
        self.setWindowTitle("MIDI-KBD Remote")
        self.resize(500, 110) # Redesigned V5 compact size (-40% height)
        
        # Frameless, Always on Top, SubWindow to avoid taskbar pollution
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow)
        
        # Support transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # WebView setup
        self.web_view = QWebEngineView(self)
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.setCentralWidget(self.web_view)
        
        # Expose JS Bridge
        self.channel = QWebChannel()
        self.bridge = RemoteBridge(self)
        self.channel.registerObject("pywebview", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        
        # Load static served remote page
        self.web_view.setUrl(QUrl("http://127.0.0.1:8000/remote"))

    def flash_button(self, cc):
        """Pass a visual LED flash event down to remote.html Javascript."""
        js_code = f"if (typeof flashButton === 'function') flashButton({cc});"
        self.web_view.page().runJavaScript(js_code)

# -------------------------------------------------------------
# MAIN APP WINDOW (Cockpit WebView & Logic Center)
# -------------------------------------------------------------
class MidiKbdApp(QMainWindow):
    def __init__(self):
        # Create QApplication if it doesn't exist
        self.qt_app = QApplication.instance()
        if not self.qt_app:
            # V21: Bypass CORS and iframe SAMEORIGIN/CSP constraints for Songsterr embedding
            if "--disable-web-security" not in sys.argv:
                sys.argv.append("--disable-web-security")
            if "--allow-running-insecure-content" not in sys.argv:
                sys.argv.append("--allow-running-insecure-content")
            self.qt_app = QApplication(sys.argv)

        # Global WebEngine configuration to bypass frame security checks
        profile = QWebEngineProfile.defaultProfile()
        
        # V21: Set standard Chrome User Agent to bypass browser-specific blocks on sites like Songsterr
        profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        g_settings = profile.settings()
        g_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        g_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        g_settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)

        # V21: Inject UserScript to bypass JavaScript-based frame-busting (window.top !== window.self checks)
        frame_bypass_script = QWebEngineScript()
        frame_bypass_script.setSourceCode("""
            try {
                Object.defineProperty(window, 'top', {
                    get: function() { return window; }
                });
                Object.defineProperty(window, 'parent', {
                    get: function() { return window; }
                });
                Object.defineProperty(window, 'frameElement', {
                    get: function() { return null; }
                });
            } catch(e) {}
        """)
        frame_bypass_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        frame_bypass_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        frame_bypass_script.setRunsOnSubFrames(True)
        
        profile.scripts().insert(frame_bypass_script)

        super().__init__()

        self.setWindowTitle(_("gui.main_title"))
        self.resize(1200, 800)


        if os.path.exists(ICON_PNG_PATH):
            self.setWindowIcon(QIcon(ICON_PNG_PATH))

        # Initialise Config & Managers
        self.profile_manager = ProfileManager()
        self.profile_manager.migrate_legacy_config()
        
        self.env_manager = EnvManager()
        
        lib_path = os.path.join(get_data_dir(), "library.json")
        self.library_manager = LibraryManager(lib_path)
        
        self.device_manager = DeviceManager()
        self.current_device_def = None
        self.profiles = []
        self.current_profile = None
        self.manual_override_profile = None

        # Settings
        self.settings = {"midi_device_name": "", "connection_mode": "MIDO"}
        self.remote_win = None

        # Dialog helper (signal/slot bridge)
        self.dialog_helper = DialogHelper(self)

        # Beautiful Premium Tab Widget for multi-tab browsing
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True) # Sleek flat borderless tab look
        
        # Style sheet matching the premium dark cockpit theme
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #0e0e0e;
            }
            QTabBar {
                background-color: #121212;
                border-bottom: 2px solid #222;
            }
            QTabBar::tab {
                background-color: #1a1a1a;
                color: #888;
                border: 1px solid #282828;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 20px;
                min-width: 120px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:hover {
                background-color: #242424;
                color: #eee;
            }
            QTabBar::tab:selected {
                background-color: #0e0e0e;
                color: #ff9800;
                border: 1px solid #ff9800;
                border-bottom: 2px solid #0e0e0e;
            }
        """)
        self.tab_widget.tabCloseRequested.connect(self.on_tab_close_requested)
        self.setCentralWidget(self.tab_widget)

        # Tab 0: Cockpit WebView
        self.web_view = QWebEngineView(self)
        self.web_page = CockpitWebPage(self, self.web_view)
        self.web_view.setPage(self.web_page)
        
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        
        self.tab_widget.addTab(self.web_view, "Cockpit")
        self.web_view.setUrl(QUrl("http://127.0.0.1:8000/"))
        
        # Disable close button on Cockpit Tab
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

        # Midi Engine & Actions
        self.midi_manager = MidiManager(self.midi_callback, on_config_change=self.on_midi_config_change)
        
        self.action_handler = ActionHandler()
        self.action_handler.set_profile_manager(self.profile_manager)
        self.action_handler.set_midi_manager(self.midi_manager)
        self.action_handler.register_listener(self.on_data_received)
        self.action_handler.start_monitoring()

        # Context Monitor (Focus tracking)
        self.context_monitor = ContextMonitor(self.profile_manager, self.action_handler, self.on_context_change)
        self.context_monitor.start()

        # System Tray setup
        self.setup_tray()

        # Start Engine (Delayed)
        self.after(1000, self.start_engine)

    def start_engine(self):
        try:
            mode = self.settings.get("connection_mode", "MIDO")
            target = ""
            if mode == "BLE":
                target = self.settings.get("midi_device_name_ble", "")
            else:
                target = self.settings.get("midi_device_name_usb", "")

            self.settings["midi_device_name"] = target
            print(f"[ENGINE] Starting Mode={mode}, Target={target}")
            self.midi_manager.switch_mode(mode, target)
        except Exception as e:
            print(f"[ENGINE] Startup Error: {e}")

    def on_context_change(self, profile):
        """Callback from ContextMonitor when focused application changes."""
        if not profile: return

        def _update():
            prof_name = profile.get("name") if profile else "None"
            if self.current_profile and self.current_profile.get("name") == prof_name:
                return

            print(f"[CONTEXT] Auto-Switch Profile: {prof_name}")
            self.current_profile = profile
            
            # Sync active device definition in server.py
            device_def = self.device_manager.get_definition_for_port(self.settings.get("midi_device_name"))
            if not device_def:
                device_def = DEFAULT_AIRSTEP_DEF
            
            # Expose to fastapi app state
            from server import app as fastapi_app
            fastapi_app.state.active_device_def = device_def

        self.after(0, _update)

    def on_midi_config_change(self, new_ports):
        self.settings["midi_output_names"] = new_ports
        self.after(0, lambda: self.save_all(silent=True))

    def save_all(self, silent=False):
        # Save profiles configuration (handled by profile_manager automatically on edits)
        pass

    # -------------------------------------------------------------
    # MIDI PIPELINE & WEBSOCKET BROADCASTING
    # -------------------------------------------------------------
    def midi_callback(self, msg):
        """Callback principal du moteur MIDI"""
        if not msg: return
        
        if msg.type == 'control_change':
            cc = msg.control
            val = msg.value
            chan = msg.channel + 1
            
            # 1. Action Handler execution
            if self.action_handler:
                print(f"[MIDI IN] Physical Event: CC {cc}, Val {val}, Chan {chan}")
                self.action_handler.execute(cc, val, chan, self.profiles, self.manual_override_profile, midi_manager=self.midi_manager)

            # 2. Real-time WebSocket Broadcast
            try:
                from server import broadcast_sync
                broadcast_sync(json.dumps({
                    "type": "midi_in",
                    "cc": cc,
                    "value": val,
                    "channel": chan
                }))
            except Exception as e:
                print(f"[WS BROADCAST] Error: {e}")

    def on_data_received(self, cc=None, value=None, channel=None):
        """Action handler feedback trigger (lights, flashes)."""
        if cc is not None:
            # Mirror flash event inside native Remote Control window if open
            if self.remote_win and self.remote_win.isVisible():
                self.remote_win.flash_button(cc)

            # Mirror to cockpit WebSocket clients as well
            try:
                from server import broadcast_sync
                broadcast_sync(json.dumps({
                    "type": "midi_in",
                    "cc": cc,
                    "value": value or 127,
                    "channel": channel or 1
                }))
            except Exception as e:
                pass

    # -------------------------------------------------------------
    # BACKWARD COMPATIBILITY TKINTER WRAPPERS
    # -------------------------------------------------------------
    def after(self, ms, callback):
        """Standard Tkinter-like delayed task runner using QTimer."""
        QTimer.singleShot(ms, callback)

    def withdraw(self):
        self.hide()

    def deiconify(self):
        self.showNormal()
        self.activateWindow()

    def lift(self):
        self.raise_()

    def focus_force(self):
        self.activateWindow()

    def mainloop(self):
        """Transparently start the QApplication event loop."""
        sys.exit(self.qt_app.exec())

    # -------------------------------------------------------------
    # SYSTEM TRAY & WINDOW LIFECYCLE
    # -------------------------------------------------------------
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(ICON_PNG_PATH):
            self.tray_icon.setIcon(QIcon(ICON_PNG_PATH))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
        tray_menu = QMenu()
        
        show_action = QAction("Ouvrir le Cockpit", self)
        show_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(show_action)
        
        remote_action = QAction("Afficher la Télécommande", self)
        remote_action.triggered.connect(self.toggle_remote_control)
        tray_menu.addAction(remote_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quitter Airstep Studio", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_activated)

    def show_main_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_window()

    def closeEvent(self, event):
        """Minimize to tray instead of closing on X button."""
        event.ignore()
        self.hide()

    def quit_app(self):
        print("Arrêt de l'application...")
        if self.context_monitor:
            self.context_monitor.stop()
        if self.action_handler:
            self.action_handler.stop_monitoring()
        self.tray_icon.hide()
        QApplication.quit()
        sys.exit(0)

    # -------------------------------------------------------------
    # REMOTE CONTROL WIDGET MANAGER
    # -------------------------------------------------------------
    def open_remote_control(self):
        if not self.remote_win:
            self.remote_win = RemoteControlWindow(self)
        self.remote_win.show()
        self.remote_win.raise_()

    def toggle_remote_control(self):
        if not self.remote_win:
            self.open_remote_control()
        else:
            if self.remote_win.isVisible():
                self.remote_win.hide()
            else:
                self.remote_win.show()
                self.remote_win.raise_()

    def load_external_url(self, url):
        url_str = url.toString()
        
        # Check if we already have this URL open in an active tab
        for i in range(1, self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            web_view = widget.findChild(QWebEngineView)
            if web_view and web_view.url().toString() == url_str:
                self.tab_widget.setCurrentIndex(i)
                return

        # Clean title for display
        display_title = url_str
        if "songsterr.com" in url_str:
            display_title = "Songsterr"
            # Try to extract song name from Songsterr URL
            parts = url_str.split("/")
            if len(parts) > 0:
                slug = parts[-1]
                slug = slug.replace("-tab", "").split("-s")[0]
                display_title = "Tab: " + slug.replace("-", " ").title()
        elif "ultimate-guitar.com" in url_str:
            display_title = "Ultimate Guitar"
        elif "youtube.com" in url_str or "youtu.be" in url_str:
            display_title = "YouTube Video"

        # Create tab container widget
        tab_container = QWidget(self)
        tab_layout = QVBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # External WebView (completely isolated, loads as a top-level page)
        web_view = QWebEngineView(self)
        ext_settings = web_view.settings()
        ext_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        ext_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        ext_settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        
        tab_layout.addWidget(web_view)

        # Add new tab
        new_index = self.tab_widget.addTab(tab_container, display_title)
        web_view.setUrl(url)
        self.tab_widget.setCurrentIndex(new_index)

        # Ensure Cockpit tab close button remains hidden
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

    def on_tab_close_requested(self, index):
        if index == 0:
            return # Never close the Cockpit!

        widget = self.tab_widget.widget(index)
        # Find child QWebEngineView inside to properly stop any audio/video playing on close
        web_view = widget.findChild(QWebEngineView)
        if web_view:
            web_view.setUrl(QUrl("about:blank"))
            web_view.deleteLater()
            
        self.tab_widget.removeTab(index)
        widget.deleteLater()
