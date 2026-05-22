import abc
import threading
import time
import datetime
import asyncio
import multiprocessing
import queue
import mido

# Try importing Bleak
try:
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False

from midi_scanner import scan_loop
import os
from utils import get_app_dir
from i18n import _

class MidiProvider(abc.ABC):
    def __init__(self, device_name, callback):
        self.target_name = device_name
        self.callback = callback
        self.is_connected = False
        self.last_error = None
        self.scanning_enabled = True
        self._stop_event = threading.Event()

    def log(self, message):
        # logging disabled to save disk space
        pass

    @abc.abstractmethod
    def start(self): pass

    @abc.abstractmethod
    def stop(self): pass

    def set_scanning(self, enabled):
        self.scanning_enabled = enabled
        self.log(f"Auto-Scan {'enabled' if enabled else 'disabled'}")

    def force_rescan(self):
        """Optional method to force a hardware scan. Override if needed."""
        self.log("Force rescan triggered (Base: No-op)")

    @abc.abstractmethod
    def get_ports(self): return []

    def is_running(self):
        return not self._stop_event.is_set()

# ==========================================
# 1. MIDO PROVIDER (Legacy/USB)
# ==========================================
class MidoProvider(MidiProvider):
    def __init__(self, device_name, callback):
        super().__init__(device_name, callback)
        self.input_port = None
        self.thread = None
        self.scanner_process = None
        self.scan_queue = None
        self.last_known_ports = []

    def _internal_callback(self, msg):
        if self.callback: self.callback(msg)

    def start(self):
        self.log("Starting MidoProvider...")
        # Security: Stop previously running threads if any (should typically be handled by manager)
        self.stop() 
        self._stop_event.clear()

        # Subprocess Scanner
        self.scan_queue = multiprocessing.Queue()
        self.scanner_process = multiprocessing.Process(target=scan_loop, args=(self.scan_queue,), daemon=True)
        self.scanner_process.start()

        self.thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self.thread.start()
        self.log("MidoProvider Threads Started.")

    def stop(self):
        self.log("Stopping MidoProvider...")
        self._stop_event.set()
        
        # 1. Stop Scanner Process
        if self.scanner_process:
            self.scanner_process.terminate()
            self.scanner_process.join(timeout=1.0)
            self.scanner_process = None
        
        # 2. Wait for Monitor Thread
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                self.log("WARNING: Monitor Thread did not unset gracefully.")
        
        # 3. Close Port
        if self.input_port:
            try: 
                self.input_port.close()
                self.log("Mido Port Closed.")
            except: pass
            self.input_port = None
        
        # 4. Force OS Release
        time.sleep(0.2)
        self.is_connected = False
        self.log("MidoProvider Stopped.")

    def force_rescan(self):
        self.log("Forcing Rescan...")
        self.last_known_ports = []

    def get_ports(self):
        return self.last_known_ports

    def _monitor_connection(self):
        self.log(f"Monitor Loop Started. Target: '{self.target_name}'")
        while not self._stop_event.is_set():
            # Update ports
            if self.scan_queue:
                try:
                    while not self.scan_queue.empty():
                        ports_list = self.scan_queue.get_nowait()
                                  
                        if ports_list != self.last_known_ports:
                            self.log(f"Scanner Update: {ports_list}")
                        self.last_known_ports = ports_list
                except: pass

            if self.is_connected:
                time.sleep(1.0)
                continue

            if not self.scanning_enabled:
                time.sleep(1.0)
                continue

            try:
                available_ports = self.last_known_ports
                target_port = None
                
                # 1. Exact Match
                if self.target_name in available_ports:
                    target_port = self.target_name
                else:
                    import re
                    # 2. Smart Index Match (e.g. "FS1-WL 1" fits "FS1-WL 2")
                    # Strip trailing digits and whitespace from target
                    base_target = re.sub(r'\s*\d+$', '', self.target_name).strip()
                    
                    if base_target:
                        for p in available_ports:
                            base_p = re.sub(r'\s*\d+$', '', p).strip()
                            if base_target.lower() == base_p.lower():
                                target_port = p
                                self.log(f"Smart Match: '{self.target_name}' resolved to '{p}'")
                                break
                    
                    # 3. Partial Match Fallback
                    if not target_port:
                        target_port = next((p for p in available_ports if self.target_name in p), None)

                if target_port:
                    self.log(f"Found: '{target_port}' (Subprocess View)")
                    try:
                        # --- CROSS-PROCESS PORT TRANSLATION ---
                        # Windows WinMM enumerates devices differently per-process.
                        # The subprocess scanner might see 'FS1-WL 2', while the main process sees 'FS1-WL 1'.
                        # We must map the subprocess name to the exact main process name before opening!
                        actual_port = target_port
                        main_process_ports = mido.get_input_names()
                        
                        if target_port not in main_process_ports:
                            self.log(f"Mapping '{target_port}' against Main Process: {main_process_ports}")
                            import re
                            base_target2 = re.sub(r'\s*\d+$', '', target_port).strip()
                            for mp in main_process_ports:
                                if re.sub(r'\s*\d+$', '', mp).strip().lower() == base_target2.lower():
                                    actual_port = mp
                                    self.log(f"Translated to -> '{actual_port}'")
                                    break
                                    
                        self.input_port = mido.open_input(actual_port, callback=self._internal_callback)
                        self.is_connected = True
                        self.last_error = None
                        self.log("Connected (Mido)!")
                    except Exception as ex:
                        self.log(f"Connection Error: {ex}")
                        self.last_error = str(ex)
            except Exception as e:
                self.log(f"Loop Error: {e}")

            time.sleep(1.0)

# ==========================================
# 2. BLEAK PROVIDER (Bluetooth Direct)
# ==========================================
class BleakProvider(MidiProvider):
    # Candidate Characteristics for MIDI Data (Notify)
    CANDIDATE_CHARS = [
        "7772e5db-3868-4112-a1a9-f2669d106bf3", # Standard BLE MIDI
        "77711512-ccc0-4cd0-97b7-4a06dc85ca9e", # XSonic Proprietary
        "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Nordic UART TX
    ]

    def __init__(self, device_name, callback):
        super().__init__(device_name, callback)
        self.client = None
        self.thread = None
        self.discovered_devices = []
        self.force_reset_scanner = False

    def force_rescan(self):
        self.log("Forcing Rescan...")
        self.discovered_devices = []
        self.force_reset_scanner = True

    def start(self):
        self.log(f"Starting BleakProvider... (Available={BLEAK_AVAILABLE})")
        if not BLEAK_AVAILABLE:
            self.last_error = _("gui.msg_error_bleak_missing", default="Bleak (lib) missing")
            self.log("ERROR: Bleak not available.")
            return
        
        self.stop() # Ensure clean state
        self._stop_event.clear()
        
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()
        self.log("Bleak Thread launched.")

    def stop(self):
        self.log("Stopping BLE Engine...")
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
             self.thread.join(timeout=3.0)
             if self.thread.is_alive():
                 self.log("Warning: BLE Thread did not stop gracefully.")
        self.is_connected = False
        self.log("BLE Engine Stopped.")

    def get_ports(self):
        ports = [d.name for d in self.discovered_devices if d.name]
        # Si le périphérique est déjà connecté en BLE, il n'émet plus de trames d'advertising actives
        # et n'apparaîtrait plus dans le scan passif de découvrabilité. On l'injecte donc impérativement.
        if self.is_connected and self.target_name and self.target_name not in ports:
            ports.append(self.target_name)
        return ports

    def _run_async_loop(self):
        self.log("Async Loop Thread Entering...")
        try:
            if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(self._main_loop())
        except Exception as e:
            self.log(f"Async Loop CRASH: {e}")

    async def _main_loop(self):
        self.log("Bleak Engine Started")
        scanner = BleakScanner()
        consecutive_adapter_errors = 0
        force_scan_iteration = False

        while not self._stop_event.is_set():
            if self.force_reset_scanner:
                self.log("Re-initializing BleakScanner...")
                scanner = BleakScanner()
                self.force_reset_scanner = False
                force_scan_iteration = True

            if self.is_connected and not force_scan_iteration:
                consecutive_adapter_errors = 0
                if self.client and self.client.is_connected:
                    await asyncio.sleep(1.0)
                    continue
                else:
                    self.log("Disconnected")
                    self.is_connected = False

            # Scanning Logic
            if not self.scanning_enabled and not force_scan_iteration:
                await asyncio.sleep(1.0)
                continue

            try:
                # Scan
                if force_scan_iteration:
                     await asyncio.sleep(0.1)
                else:
                     await asyncio.sleep(2.0)
                
                # Check stop event before long operation
                if self._stop_event.is_set(): break

                devices = await scanner.discover(timeout=3.0)
                self.discovered_devices = devices
                
                # DIAGNOSTIC LOG
                found_names = [d.name for d in devices if d.name]
                if found_names:
                    self.log(f"BLE Scan Results: {found_names} (Looking for: '{self.target_name}')")
                else:
                    self.log(f"BLE Scan: No devices found.")

                consecutive_adapter_errors = 0
                force_scan_iteration = False

                target_device = None
                for d in devices:
                    if d.name and self.target_name.lower() in d.name.lower():
                         target_device = d
                         break

                if target_device and not self.is_connected:
                    self.log(f"Connecting BLE: {target_device.name}...")
                    self.client = BleakClient(target_device.address)
                    await self.client.connect()

                    if self.client.is_connected:
                        self.log("BLE Connected. Finding MIDI Characteristic...")
                        found_char = None
                        services_map = {c.uuid: c for s in self.client.services for c in s.characteristics}

                        for candidate in self.CANDIDATE_CHARS:
                            if candidate in services_map:
                                char = services_map[candidate]
                                if "notify" in char.properties:
                                    found_char = candidate
                                    break

                        if found_char:
                            await self.client.start_notify(found_char, self._on_notify)
                            self.is_connected = True
                            self.last_error = None
                            self.log("Connected (BLE) & Subscribed!")
                        else:
                            # Fallback logic simplified for brevity but functional
                            self.log("No known MIDI char. Trying connection only.")
                            self.is_connected = True

            except Exception as e:
                self.log(f"BLE Loop Error: {e}")
                if "No Bluetooth adapter found" in str(e):
                    consecutive_adapter_errors += 1
                    if consecutive_adapter_errors >= 3:
                         self.log("CRITICAL: Adapter Failure. Stopping.")
                         break
                    await asyncio.sleep(5.0)

            await asyncio.sleep(1.0)

        # Cleanup async
        if self.client:
            try: await self.client.disconnect()
            except: pass
        self.log("Async Loop Exit.")

    def _on_notify(self, sender, data):
        # Improved BLE MIDI Parser (Pattern Matching)
        try:
            bytes_list = list(data)
            i = 0
            while i < len(bytes_list):
                b = bytes_list[i]
                if (b & 0xF0) in [0x80, 0x90, 0xB0, 0xE0]:
                    if i + 2 < len(bytes_list):
                        d1 = bytes_list[i+1]
                        d2 = bytes_list[i+2]
                        if d1 < 0x80 and d2 < 0x80:
                            msg = mido.Message.from_bytes([b, d1, d2])
                            if self.callback: self.callback(msg)
                            i += 3
                            continue
                elif (b & 0xF0) in [0xC0, 0xD0]:
                    if i + 1 < len(bytes_list):
                        d1 = bytes_list[i+1]
                        if d1 < 0x80:
                            msg = mido.Message.from_bytes([b, d1])
                            if self.callback: self.callback(msg)
                            i += 2
                            continue
                i += 1
        except: pass

class MidiManager:
    def __init__(self, callback, on_config_change=None):
        self.callback = callback
        self.on_config_change = on_config_change
        self.current_provider = None
        self.current_mode = None
        self.active_providers = []  # Liste des providers physiques actifs en simultane
        
        # Output ports state
        self._active_output_ports = []
        self._target_output_names = []
        
        # V73: Watchdog for auto-reconnection
        self._stop_event = threading.Event()
        self._watchdog_thread = threading.Thread(target=self._output_watchdog, daemon=True)
        self._watchdog_thread.start()
    
    def log(self, msg):
        # logging disabled to save disk space
        pass

    def _output_watchdog(self):
        """Periodically checks if target output ports are connected."""
        while not self._stop_event.is_set():
            if self._target_output_names:
                # Check if any target is missing from active ports
                active_names = [p[0] for p in self._active_output_ports]
                
                # Check targets that are NOT currently active
                need_refresh = False
                for target in self._target_output_names:
                    if target not in active_names:
                        need_refresh = True
                        break
                
                if need_refresh:
                    available = self.get_available_outputs()
                    self.log(f"[WATCHDOG] Connection drift detected. Scanning...")
                    
                    old_targets = list(self._target_output_names)
                    new_resolved = self.set_output_ports(self._target_output_names)
                    
                    # V75: CRITICAL - Check if targets were updated due to fuzzy matching
                    if self._target_output_names != old_targets:
                        print(f"[WATCHDOG] Persistent Auto-Healing: Targets updated to {self._target_output_names}")
                        if self.on_config_change:
                            self.on_config_change(self._target_output_names)
            
            time.sleep(5.0)

    def switch_composite(self, physical_devices):
        """
        Démarrage simultané de plusieurs providers physiques.
        physical_devices: list of dict, ex: [{"type": "BLE", "name": "AIRSTEP"}, {"type": "USB", "name": "FS1-WL"}]
        """
        print(f"[MIDI] Commutation Composite: {physical_devices}")
        
        # 1. Arrêter proprement tous les anciens providers actifs
        for provider in self.active_providers:
            print(f"[MIDI] Arrêt du provider: {provider.__class__.__name__} ({provider.target_name})")
            try:
                provider.stop()
            except Exception as e:
                print(f"[MIDI] Erreur lors de l'arrêt du provider: {e}")
        
        self.active_providers = []
        self.current_provider = None
        
        # 2. Instancier les nouveaux providers correspondants
        for dev in physical_devices:
            dev_type = dev.get("type")
            dev_name = dev.get("name")
            if not dev_type or not dev_name or dev_name in ("None", "Virtuel", "Virtual", ""):
                continue
                
            print(f"[MIDI] Instanciation du provider Composite: Type={dev_type}, Nom={dev_name}")
            if dev_type == "BLE":
                provider = BleakProvider(dev_name, self.callback)
            else:
                provider = MidoProvider(dev_name, self.callback)
                
            self.active_providers.append(provider)
            
            # Définir le premier comme current_provider pour la compatibilité ascendante
            if not self.current_provider:
                self.current_provider = provider
        
        # 3. Démarrer tous les providers actifs
        for provider in self.active_providers:
            try:
                provider.start()
                print(f"[MIDI] Provider démarré pour '{provider.target_name}'")
            except Exception as e:
                print(f"[MIDI] Erreur de démarrage pour '{provider.target_name}': {e}")

    def switch_mode(self, mode, device_name):
        """
        Radical switch: Kill old, start new.
        Persists callback. Encapsulated in switch_composite for unification.
        """
        self.log(f"Switching Mode to {mode} / Target: {device_name}")
        self.current_mode = mode
        
        is_virtual_or_none = (
            mode in (None, "None", "Virtuel", "Virtual") or 
            device_name in (None, "None", "Virtuel", "Virtual", "")
        )
        
        if is_virtual_or_none:
            self.switch_composite([])
        else:
            self.switch_composite([{"type": mode, "name": device_name}])

    def get_ports(self):
        ports = []
        for provider in self.active_providers:
            try:
                ports.extend(provider.get_ports())
            except: pass
        return list(set(ports))

    def set_scanning(self, enabled):
        for provider in self.active_providers:
            try:
                provider.set_scanning(enabled)
            except: pass

    def force_rescan(self):
        for provider in self.active_providers:
            try:
                provider.force_rescan()
            except: pass

    @property
    def is_connected(self):
        if not self.active_providers:
            return False
        return any(provider.is_connected for provider in self.active_providers)

    @property
    def active_device_name(self):
        """Returns the target names of all active providers"""
        if not self.active_providers:
            return None
        connected_names = [p.target_name for p in self.active_providers if p.is_connected]
        if connected_names:
            return ", ".join(connected_names)
        # Fallback aux noms cibles configurés s'ils ne sont pas encore connectés
        return ", ".join([p.target_name for p in self.active_providers])

    # --- Output Management (Instance Methods) ---
    
    def get_available_outputs(self):
        try:
            return mido.get_output_names()
        except:
            return []

    def set_output_ports(self, port_names):
        if not isinstance(port_names, list):
            port_names = [port_names] if port_names else []

        available = self.get_available_outputs()
        self._target_output_names = list(port_names) # Work on a copy
        resolved_ports = []
        
        import re
        def clean_name(n):
            # Remove parenthesis, MIDIOUT prefixes, and trailing digits/spaces
            return re.sub(r'\(.*?\)|MIDIOUT\d*|\d+', '', n).strip().lower()

        new_targets = []
        for name in self._target_output_names:
            if not name: continue
            
            actual_name = name
            found = False
            
            # 1. Exact Match
            if name in available:
                actual_name = name
                found = True
            
            # 2. Extreme Fuzzy Match (The "Soul" match)
            if not found:
                base_target = clean_name(name)
                if base_target and len(base_target) > 3:
                    for p in available:
                        if base_target in clean_name(p):
                            actual_name = p
                            found = True
                            print(f"[MIDI OUT] Auto-healed '{name}' -> '{p}'")
                            break
            
            # 3. Index Match fallback
            if not found:
                base_target_simple = re.sub(r'\s*\d+$', '', name).strip()
                if base_target_simple:
                    for p in available:
                        if base_target_simple.lower() in p.lower():
                            actual_name = p
                            found = True
                            print(f"[MIDI OUT] Index-healed '{name}' -> '{p}'")
                            break
            
            if actual_name not in new_targets:
                new_targets.append(actual_name)
            
            if found and actual_name not in resolved_ports:
                resolved_ports.append(actual_name)

        # Update the targets list with potentially new names
        self._target_output_names = new_targets

        # Close existing
        for name, port in self._active_output_ports:
            try: port.close()
            except: pass
        self._active_output_ports = []

        for name in resolved_ports:
            try:
                out = mido.open_output(name)
                self._active_output_ports.append((name, out))
                self.log(f"Connected output: '{name}'")
            except Exception as e:
                self.log(f"Could not open output '{name}': {e}")
                
        return resolved_ports

    def send_raw(self, msg):
        """Broadcasts any mido.Message to all active output ports."""
        if not self._active_output_ports: 
            # V73: Zero-latency recovery. If no ports but targets exist, try connecting NOW.
            if self._target_output_names:
                print("[MIDI OUT] No ports active. Attempting emergency recovery...")
                self.set_output_ports(self._target_output_names)
            if not self._active_output_ports: return

        dead_ports = []
        for name, port in self._active_output_ports:
            try:
                port.send(msg)
                print(f"[MIDI OUT] Sent to '{name}': {msg}")
            except Exception as e:
                print(f"[MIDI OUT] Failed '{name}': {e}")
                dead_ports.append(name)
        
        # Cleanup dead ports so watchdog can restart them
        if dead_ports:
            self._active_output_ports = [p for p in self._active_output_ports if p[0] not in dead_ports]

    def send_message(self, channel, cc, value):
        ch = max(0, min(15, int(channel) - 1))
        msg = mido.Message('control_change', channel=ch, control=int(cc), value=int(value))
        self.send_raw(msg)
    
    def get_ports_status(self):
        available = self.get_available_outputs()
        status_list = []
        
        # Helper to match "soul" of names
        import re
        def clean(n):
            return re.sub(r'\(.*?\)|MIDIOUT\d*|\d+', '', n).strip().lower()

        # Build list of all names to consider
        all_names = set(available) | set(self._target_output_names)
        
        # Pre-clean target names for faster fuzzy matching
        clean_targets = [clean(t) for t in self._target_output_names if clean(t)]

        for name in sorted(list(all_names)):
            # 1. Direct match
            is_configured = name in self._target_output_names
            
            # 2. Fuzzy match (if not direct)
            if not is_configured:
                c_name = clean(name)
                if c_name:
                    for ct in clean_targets:
                        if ct in c_name or c_name in ct:
                            is_configured = True
                            break

            is_connected = any(p[0] == name for p in self._active_output_ports)
            is_available = name in available
            
            status_list.append({
                "name": name,
                "selected": is_configured,
                "connected": is_connected,
                "available": is_available
            })
        return status_list
