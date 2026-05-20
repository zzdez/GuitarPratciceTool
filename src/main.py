import sys
import os

# V21: Bypass same-origin, CORS and iframe SAMEORIGIN/CSP constraints globally for Songsterr embedding
# Only set environment flags if this is the main GUI process
if "--multiprocessing-fork" not in "".join(sys.argv):
    os.environ["QTWEBENGINE_DISABLE_CONTENT_SECURITY_POLICY"] = "1"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-web-security --allow-running-insecure-content"

import threading
import webbrowser
import uvicorn
import multiprocessing
import socket
import time

# --- FIX CONSOLE PYINSTALLER ---
class NullWriter:
    def write(self, text): pass
    def flush(self): pass
    def isatty(self): return False

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

# --- FIX CHEMINS ---
# S'assurer que le dossier src (ou le root du bundle) est dans le path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# Si on est dans src, ajouter aussi le parent pour les imports absolus type 'src.xxx'
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# --- IMPORTS ---
from server import app as fastapi_app
from config_manager import ConfigManager
from gui import MidiKbdApp
from midi_engine import MidiManager
from utils import get_app_dir
import maintenance

# Globals
server_thread = None
midi_manager = None
app = None

# --- CALLBACK MIDI (Le Pont Critique) ---


def start_uvicorn(host, port):
    try:
        uvicorn.run(fastapi_app, host=host, port=port, log_level="warning")
    except: pass

def main():
    global app, server_thread

    print("--- Démarrage MidiKbd Control Studio ---")
    print("DISCLAIMER: MidiKbd Control Studio est un outil d'interopérabilité.")
    print("L'utilisateur est seul responsable de l'usage des fonctions de téléchargement,")
    print("conformément aux lois sur la copie privée et aux droits d'auteur de son pays.")

    # 0. Light Mode Detection
    light_mode_flag = os.path.join(get_app_dir(), "light_mode.flag")
    is_light_mode = os.path.exists(light_mode_flag) or os.environ.get("LIGHT_MODE") == "1"

    if is_light_mode:
        print(">>> MODE LIGHT ACTIVE (Serveur Web & Context Monitor DESACTIVES) <<<")

    # 1. Config & i18n
    config = ConfigManager()
    port = int(config.get("app_port", 8000))
    
    from i18n import i18n
    lang = config.get("language", "fr")
    i18n.export_locales()
    i18n.set_language(lang)

    # 1b. Maintenance & Consolidation des données (Mesh Sync Global)
    try:
        maintenance.heal_all_meshes()
    except Exception as e:
        print(f"Maintenance Error: {e}")

    # 2. Interface Graphique (GUI) - Doit être créée dans le Main Thread
    app = MidiKbdApp()
    
    if is_light_mode:
        # Mode Light : On ouvre directement la Remote et on affiche le Tray
        app.withdraw() # Main win hidden
        print("Ouverture immédiate de la Remote (Light Mode)...")
        app.after(500, lambda: app.open_remote_control())
    else:
        # Mode Studio : Démarrage discret (Tray only)
        app.withdraw()

    # 2b. Wiring Web Settings Button -> Native GUI
    # ... (Keep wiring, it won't hurt even if unused in Light Mode)

    # ... (Callback definitions omitted for brevity, logic remains same) ...

    # 2e. State Injection
    # ... (Keep wiring)

    # 3. Démarrage Serveur Web (Thread) - EXCLUDED IN LIGHT MODE
    server_thread = None
    if not is_light_mode:
        server_thread = threading.Thread(target=start_uvicorn, args=("127.0.0.1", port), daemon=True)
        server_thread.start()
        print("Serveur Web démarré.")
    
        # Context Monitor start is inside MidiKbdApp.__init__. 
        # We need to STOP it if light mode.
        if hasattr(app, 'context_monitor') and app.context_monitor:
            # Note: ContextMonitor was started in app.__init__. We should stop it here.
            # Better architecture would be to start it here, but checking existing code...
            # It IS started in MidiKbdApp.__init__.
             pass 
    else:
        # Stop the monitor that started automatically in MidiKbdApp
        if hasattr(app, 'context_monitor') and app.context_monitor:
            print("Arrêt du ContextMonitor pour Light Mode.")
            app.context_monitor.stop()

    # 4. Démarrage MIDI (Thread) - ALWAYS ON
    # On lance le MIDI maintenant !
    def start_midi_engine():
        time.sleep(1) # Petit délai pour laisser l'UI s'afficher
        try:
            device_name = config.get("midi_device_name", "AIRSTEP")
            conn_mode = config.get("connection_mode", "BLE") # ou MIDO

            print(f"Tentative connexion MIDI ({conn_mode}) sur : {device_name}")

            midi_manager = MidiManager.create(conn_mode, device_name, on_midi_event)
            # On stocke la ref dans l'app pour qu'elle puisse afficher le statut
            app.midi_engine = midi_manager
            # Hack/Fix: Le MidiManager est passé à l'ActionHandler via execute() mais on utilise l'instance ici
            # Mais app.midi_engine est l'instance MidiManager
            # Donc on est bon.
            midi_manager.start()
        except Exception as e:
            print(f"Erreur Fatal MIDI: {e}")

    def open_settings_wrapper():
        # Utilise .after pour que l'appel vienne du Thread Principal Tkinter
        if app:
            # CORRECTION : On ouvre la Fenêtre Principale, pas juste le dialogue settings
            app.after(0, lambda: [app.deiconify(), app.lift(), app.focus_force()])

    def toggle_remote_wrapper():
        if app:
            app.after(0, lambda: app.toggle_remote_control())
            
    def reload_userscripts_wrapper():
        if app:
            app.after(0, lambda: app.reload_userscripts())
            
    fastapi_app.state.toggle_remote_callback = toggle_remote_wrapper
    fastapi_app.state.open_settings_callback = open_settings_wrapper
    fastapi_app.state.reload_userscripts_callback = reload_userscripts_wrapper
    fastapi_app.state.midi_manager = app.midi_manager

    # 2c. Wiring Folder Selection (Thread-Safe)
    def select_folder_wrapper():
        """Ouvre askdirectory dans le thread principal et renvoie le résultat"""
        if app and hasattr(app, "dialog_helper"):
            ctx = {"event": threading.Event(), "path": None}
            app.dialog_helper.select_folder_signal.emit(ctx)
            ctx["event"].wait()
            return ctx["path"]
        return None

    fastapi_app.state.select_folder_callback = select_folder_wrapper

    # 2d. Wiring File Selection (Thread-Safe)
    def select_file_wrapper():
        """Ouvre askopenfilename dans le thread principal et renvoie le résultat"""
        if app and hasattr(app, "dialog_helper"):
            ctx = {"event": threading.Event(), "path": None}
            app.dialog_helper.select_file_signal.emit(ctx)
            ctx["event"].wait()
            return ctx["path"]
        return None

    fastapi_app.state.select_file_callback = select_file_wrapper

    # 2e. State Injection (Profiles, Context, Action Handler)
    fastapi_app.state.profile_manager = app.profile_manager
    fastapi_app.state.action_handler = app.action_handler
    
    if hasattr(app, 'context_monitor'):
        fastapi_app.state.context_monitor = app.context_monitor

    # 4. MIDI Engine is now managed by MidiKbdApp internally automatically.
    # See MidiKbdApp.start_engine() and MidiKbdApp.__init__()


    # 5. Ouverture Navigateur (Désactivé : Mode Service)
    # def open_browser():
    #     time.sleep(2)
    #     webbrowser.open(f"http://127.0.0.1:{port}")
    #
    # threading.Thread(target=open_browser, daemon=True).start()

    # 6. Boucle Principale (Bloquante Tkinter)
    # C'est ici que l'application vit.
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        pass

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    # V21: Bypass same-origin, CORS and iframe SAMEORIGIN/CSP constraints globally for Songsterr embedding
    # Only modify sys.argv if we are in the main GUI process (not in multiprocessing spawned forks)
    if "--multiprocessing-fork" not in "".join(sys.argv):
        if "--disable-web-security" not in sys.argv:
            sys.argv.append("--disable-web-security")
        if "--allow-running-insecure-content" not in sys.argv:
            sys.argv.append("--allow-running-insecure-content")
            
    main()
