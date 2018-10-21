import os
import json

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ConfigManager:

    _CFG_FILE = "config.json"
    _cfg = dict()

    def __init__(self, config_file=None):
        if config_file:
            ConfigManager._CFG_FILE = config_file

    # Watch for config file changes
    @staticmethod
    def _watch_changes():
        observer = Observer()

        file = ConfigManager._CFG_FILE
        method = ConfigManager._read_cfg
        change_handler = ChangeHandler(file, method)

        observer.schedule(change_handler, ".", recursive=True)
        observer.start()

    @staticmethod
    def _read_cfg():
        if os.path.isfile(ConfigManager._CFG_FILE):
            with open(ConfigManager._CFG_FILE) as config_file:
                ConfigManager._cfg = json.load(config_file)
        else:
            cfg_file = ConfigManager._CFG_FILE
            exit(f"ERROR: No configuration file '{cfg_file}' found")

    @staticmethod
    def _write_cfg():
        if os.path.isfile(ConfigManager._CFG_FILE):
            with open(ConfigManager._CFG_FILE, "w") as config_file:
                json.dump(ConfigManager._cfg, config_file, indent=4)
        else:
            cfg_file = ConfigManager._CFG_FILE
            exit(f"ERROR: No configuration file '{cfg_file}' found")

    @staticmethod
    def get(key):
        if not ConfigManager._cfg:
            ConfigManager._read_cfg()
            ConfigManager._watch_changes()

        return ConfigManager._cfg[key] if key in ConfigManager._cfg else None


class ChangeHandler(FileSystemEventHandler):
    file = None
    method = None

    def __init__(self, file, method):
        type(self).file = file
        type(self).method = method

    @staticmethod
    def on_modified(event):
        if os.path.basename(event.src_path).endswith(ChangeHandler.file):
            ChangeHandler.method()
