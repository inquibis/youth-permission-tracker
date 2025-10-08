from dotenv import dotenv_values, load_dotenv
import os

class EnvManager:
    def __init__(self, filename=".env"):
        self.filename = filename
        # Make sure file exists
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                f.write("")

    def get(self, key:str, default_value=None)->str:
        """Read a value from .env (returns default if not found)."""
        config = dotenv_values(self.filename)
        return config.get(key, default_value)

    def set(self, key:str, value:str)->str:
        """Update value if key exists, otherwise append it."""
        lines = []
        found = False
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        lines.append(f"{key}={value}\n")
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append(f"{key}={value}\n")

        with open(self.filename, "w") as f:
            f.writelines(lines)

    def load(self, override=True)->None:
        """Load values into os.environ"""
        load_dotenv(self.filename, override=override)

    def all(self)->dict:
        """Return all key-value pairs as a dict"""
        return dotenv_values(self.filename)