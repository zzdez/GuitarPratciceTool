import os
import json
import base64
import dotenv
from utils import get_app_dir

# Cryptographic helper functions (XOR + Base64) for robust lightweight encryption
def _xor_crypt(data: str, key: str = "GuitarPracticeToolSecretKey_789!#@$%") -> str:
    key_bytes = key.encode('utf-8')
    data_bytes = data.encode('utf-8')
    result = bytearray()
    for i in range(len(data_bytes)):
        result.append(data_bytes[i] ^ key_bytes[i % len(key_bytes)])
    return base64.b64encode(result).decode('utf-8')

def _xor_decrypt(encrypted_base64: str, key: str = "GuitarPracticeToolSecretKey_789!#@$%") -> str:
    try:
        data_bytes = base64.b64decode(encrypted_base64.encode('utf-8'))
        key_bytes = key.encode('utf-8')
        result = bytearray()
        for i in range(len(data_bytes)):
            result.append(data_bytes[i] ^ key_bytes[i % len(key_bytes)])
        return result.decode('utf-8')
    except Exception:
        return ""

class ConfigManager:
    def __init__(self, config_file="config.json", secrets_file="secrets.bin"):
        self.config_file = os.path.join(get_app_dir(), config_file)
        self.secrets_file = os.path.join(get_app_dir(), secrets_file)
        self.config_data = {}
        self.secrets_data = {}
        self._load_config()
        self._load_secrets()
        
        # Ensure internal Media directories exist at startup
        from utils import get_internal_media_dirs
        get_internal_media_dirs()

    def _load_config(self):
        """Loads config.json into memory if it exists. Creates it if missing."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except Exception as e:
                print(f"Error loading {self.config_file}: {e}")
                self.config_data = {"settings": {}}
        else:
            self.config_data = {"settings": {}}
            self._save_config()

    def _load_secrets(self):
        """Loads and decrypts secrets.bin. If missing, attempts to migrate from .env."""
        # 1. If secrets.bin exists, load and decrypt
        if os.path.exists(self.secrets_file):
            try:
                with open(self.secrets_file, "r", encoding="utf-8") as f:
                    encrypted_content = f.read().strip()
                if encrypted_content:
                    decrypted_content = _xor_decrypt(encrypted_content)
                    if decrypted_content:
                        self.secrets_data = json.loads(decrypted_content)
                    else:
                        self.secrets_data = {}
            except Exception as e:
                print(f"Error loading decrypted secrets: {e}")
                self.secrets_data = {}
        else:
            self.secrets_data = {}

        # 2. Check for migration from .env (Only if secrets.bin was missing or empty)
        env_path = os.path.join(get_app_dir(), ".env")
        migrated = False
        if os.path.exists(env_path):
            try:
                # Load temporary to migrate
                dotenv.load_dotenv(env_path)
                keys_to_migrate = ["YOUTUBE_API_KEY", "GETSONGBPM_API_KEY", "GETSONGBPM_KEY", "GETSONG_API_KEY", "GETSONGKEY_API_KEY"]
                for key in keys_to_migrate:
                    val = os.environ.get(key) or os.environ.get(key.lower())
                    if val and key not in self.secrets_data:
                        self.secrets_data[key] = val
                        migrated = True
            except Exception as e:
                print(f"Error during .env migration: {e}")

        # 3. Save to secrets.bin if we migrated
        if migrated:
            self._save_secrets()
            # Clean sensitive API keys from .env to prevent double storage and plain text
            self._clean_env_keys(env_path)
            
        # 4. Expose active secrets in memory (os.environ) so that other sub-modules
        # can still access them transparently via environment variables
        for key, value in self.secrets_data.items():
            os.environ[key] = str(value)

    def _clean_env_keys(self, env_path):
        """Cleans sensitive API keys from .env to keep it secure."""
        if not os.path.exists(env_path):
            return
        try:
            # We will rewrite the .env file without keys containing "API_KEY"
            lines = []
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            new_lines = []
            keys_to_remove = ["YOUTUBE_API_KEY", "GETSONGBPM_API_KEY", "GETSONGBPM_KEY", "GETSONG_API_KEY", "GETSONGKEY_API_KEY"]
            for line in lines:
                should_keep = True
                for k in keys_to_remove:
                    if line.strip().startswith(k) or line.strip().startswith(k.lower()):
                        should_keep = False
                        break
                if should_keep:
                    new_lines.append(line)
            
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Error cleaning env keys: {e}")

    def _save_secrets(self):
        """Encrypts and saves secrets to secrets.bin."""
        try:
            serialized = json.dumps(self.secrets_data, indent=4)
            encrypted = _xor_crypt(serialized)
            with open(self.secrets_file, "w", encoding="utf-8") as f:
                f.write(encrypted)
        except Exception as e:
            print(f"Error saving secrets: {e}")

    def get(self, key, default=None):
        """
        Retrieves a configuration value with priority:
        1. Encrypted Secrets (secrets.bin / memory secrets) for API keys
        2. Environment Variable (Upper Case)
        3. config.json (exact key)
        4. Default value
        """
        env_key = key.upper()
        # 1. Encrypted Secrets Priority
        if env_key in self.secrets_data:
            return self.secrets_data[env_key]
        if key in self.secrets_data:
            return self.secrets_data[key]

        # 2. Environment Variable (Highest Priority for other keys)
        if os.environ.get(env_key) is not None:
            return os.environ.get(env_key)

        # SPECIFIC LOGIC: Internal Media folders (Prioritized & Merged)
        if key == "media_folders":
            from utils import get_internal_media_dirs, to_portable_path
            internal_dirs = get_internal_media_dirs() 
            
            # Get existing from config
            saved_dirs = []
            if "settings" in self.config_data and "media_folders" in self.config_data["settings"]:
                saved_dirs = self.config_data["settings"]["media_folders"]
            elif "media_folders" in self.config_data:
                saved_dirs = self.config_data["media_folders"]
            
            # Merge and prioritize internal (as portable paths)
            final_dirs = [to_portable_path(d) for d in internal_dirs]
            for d in saved_dirs:
                if d not in final_dirs:
                    final_dirs.append(d)
            return final_dirs

        # JSON config backup
        if "settings" in self.config_data and key in self.config_data["settings"]:
            return self.config_data["settings"][key]

        if key in self.config_data:
            return self.config_data[key]
            
        # Specific Default for language
        if key == "language":
            return "fr"

        # 4. Default
        return default

    def set(self, key, value):
        """
        Sets a value in config.json (persisted) or secrets.bin (if it's an API Key or secret).
        """
        env_key = key.upper()
        if "API_KEY" in env_key or "SECRET" in env_key or "KEY" in env_key:
            # Save into encrypted secrets
            self.secrets_data[env_key] = str(value)
            self._save_secrets()
            # Update OS environ so it's immediately available without restart
            os.environ[env_key] = str(value)
            return
            
        # Normal configuration save
        if "settings" not in self.config_data:
            self.config_data["settings"] = {}

        self.config_data["settings"][key] = value
        self._save_config()

    def _save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

