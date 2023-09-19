
import sys
import json
import os.path
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------------------------
# Configuration - app configuration storage
# ------------------------------------------------------------------------------

class Configuration:
    """
    Application configuration store and persistency.
    Default is storage is „browse.config” file in current directory.
    """

    def __init__(self, path="./browse.config"):
        """
        Load configuration from file. By default configuration
        is stored in `browse.config` file in current directory.
        """
        self.path = Path(path)
        self._config = dict()
        if os.path.isfile(path):
            with open(path, "r") as read_file:
                self._config = json.load(read_file)

    def save(self, backup=False):
        """
        Save all configuration data to disk.
        """
        if backup:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            p = self.path
            p.rename(Path(p.parent, f"{p.stem}_{timestamp}{p.suffix}"))
        with open(self.path, "w") as write_file:
            json.dump(self._config, write_file, indent=2)

    def get_history(self):
        if 'history' in self._config:
            return self._config['history']
        else:
            return None

    def get_view_history(self, path):
        if 'history' in self._config:
            return next((x for x in self._config["history"] if x['file_name'] == path),
                        None)        

    def update_history(self, view_dictionary):
        if 'history' not in self._config:
            self._config['history'] = [view_dictionary, ]
        else:
            history = self._config["history"]
            history = [x for x in history if x['file_name'] != view_dictionary['file_name']]
            history.insert(0, view_dictionary)
            self._config["history"] = history
        self.save()

    def get_session(self):
        if 'session' in self._config:
            return self._config['session']
        else:
            return None

    def update_session(self, app):
        self._config['session'] = app.get_session()
        if 'history' not in self._config:
            self._config['history'] = []
        history = self._config["history"]
        for view in app.views + [app.view]:
            data = view.config_dictionary()
            history = [x for x in history if x['file_name'] != data['file_name']]
            history.insert(0, data)
        self._config["history"] = history
        self.save(backup=True)
