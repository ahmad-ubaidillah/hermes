"""Top-level re-exports from core.utils for backward compatibility.

Also re-exports the json and yaml modules so that test patches like
patch("utils.json.dump", ...) resolve correctly.
"""

import json
import yaml

from core.utils import atomic_json_write, atomic_yaml_write

__all__ = ["atomic_json_write", "atomic_yaml_write", "json", "yaml"]
