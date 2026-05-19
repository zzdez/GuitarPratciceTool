import json
import os

new_keys = {
    "lbl_midi_hardware": "Matériel & Connexion MIDI",
    "lbl_connection_mode": "Mode de Connexion",
    "lbl_midi_device_name": "Nom du Périphérique",
    "lbl_midi_outputs": "Routage des Sorties MIDI (Multi-Output)",
    "lbl_profile_management": "Gestion des Profils & Mappings",
    "lbl_select_profile": "Sélectionner le Profil",
    "lbl_rules_autoswitch": "Règles d'Auto-Switch (Focalisation)",
    "lbl_target_process": "Processus Cible",
    "lbl_window_title_regex": "Titre Fenêtre (Filter/Regex)",
    "lbl_master_vol_sys": "Volume Master Système (OS)",
    "btn_new_profile": "+ Nouveau",
    "btn_duplicate_profile": "Dupliquer",
    "btn_delete_profile": "Supprimer",
    "lbl_mappings_list": "Liste des Mappings (Boutons Physiques)",
    "btn_add_mapping": "+ Ajouter un Mapping",
    "col_mapping_name": "Nom",
    "col_mapping_midi": "Entrée MIDI",
    "col_mapping_action": "Action Exécutée",
    "col_mapping_opts": "Options",
    "modal_mapping_title_add": "Ajouter un Mapping MIDI",
    "modal_mapping_title_edit": "Modifier le Mapping MIDI",
    "lbl_mapping_desc": "Description du Bouton / Action",
    "lbl_mapping_midi_cc": "MIDI CC (Numéro)",
    "lbl_mapping_midi_ch": "Canal MIDI (1-16)",
    "lbl_mapping_action_type": "Type d'Action",
    "lbl_mapping_action_val": "Valeur / Raccourci Clavier",
    "btn_rec_key": "REC Clavier",
    "hint_rec_key": "Appuyez sur une touche..."
}

new_keys_en = {
    "lbl_midi_hardware": "MIDI Hardware & Connection",
    "lbl_connection_mode": "Connection Mode",
    "lbl_midi_device_name": "Device Name",
    "lbl_midi_outputs": "MIDI Output Routing (Multi-Output)",
    "lbl_profile_management": "Profiles & Mappings Management",
    "lbl_select_profile": "Select Profile",
    "lbl_rules_autoswitch": "Auto-Switch Rules (Focusing)",
    "lbl_target_process": "Target Process",
    "lbl_window_title_regex": "Window Title (Filter/Regex)",
    "lbl_master_vol_sys": "Master System Volume (OS)",
    "btn_new_profile": "+ New",
    "btn_duplicate_profile": "Duplicate",
    "btn_delete_profile": "Delete",
    "lbl_mappings_list": "Mappings List (Physical Buttons)",
    "btn_add_mapping": "+ Add Mapping",
    "col_mapping_name": "Name",
    "col_mapping_midi": "MIDI Input",
    "col_mapping_action": "Executed Action",
    "col_mapping_opts": "Options",
    "modal_mapping_title_add": "Add MIDI Mapping",
    "modal_mapping_title_edit": "Edit MIDI Mapping",
    "lbl_mapping_desc": "Button / Action Description",
    "lbl_mapping_midi_cc": "MIDI CC (Number)",
    "lbl_mapping_midi_ch": "MIDI Channel (1-16)",
    "lbl_mapping_action_type": "Action Type",
    "lbl_mapping_action_val": "Value / Keyboard Shortcut",
    "btn_rec_key": "REC Key",
    "hint_rec_key": "Press any key..."
}

# Update French
fr_path = os.path.join("locales", "fr.json")
if os.path.exists(fr_path):
    with open(fr_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "web" in data:
        data["web"].update(new_keys)
    with open(fr_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("French locales updated!")

# Update English
en_path = os.path.join("locales", "en.json")
if os.path.exists(en_path):
    with open(en_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "web" in data:
        data["web"].update(new_keys_en)
    with open(en_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("English locales updated!")
