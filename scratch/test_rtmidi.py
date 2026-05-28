import rtmidi

print("--- RTMIDI APIS ---")
apis = rtmidi.get_compiled_api()
for api in apis:
    print(f"API compiled: {api} ({rtmidi.get_api_name(api)})")

# Test listing inputs for each compiled API
for api in apis:
    print(f"\n--- Ports pour l'API: {rtmidi.get_api_name(api)} ---")
    try:
        midi_in = rtmidi.MidiIn(rtmidi_api=api)
        ports = midi_in.get_ports()
        print("Ports:", ports)
    except Exception as e:
        print("Erreur:", e)
