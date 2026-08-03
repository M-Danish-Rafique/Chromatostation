# method_manager.py
import json
from datetime import datetime

class MethodManager:
    @staticmethod
    def save_method(data, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_method(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)