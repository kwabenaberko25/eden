import os
from eden.config import ConfigManager, Environment

os.environ["EDEN_ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret"

manager = ConfigManager()
manager.reset()
config = manager.load()

print(f"ENV: {config.env}")
print(f"SECRET_KEY: {config.secret_key}")
print(f"LEN: {len(config.secret_key)}")
