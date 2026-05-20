import os
from utils import get_data_dir

data_dir = get_data_dir()
filepath = os.path.join(data_dir, "userscripts.json")
print("DATADIR:", data_dir)
print("FILEPATH:", filepath)
print("EXISTS:", os.path.exists(filepath))
if os.path.exists(filepath):
    print("SIZE:", os.path.getsize(filepath))
