"""
some common utilities
"""

import os
import re
import logging
import winreg

import pluginlib


def seconds_tostring(seconds, **kwargs):
    """
    convert seconds to string
    format returned :
        [H:]MM:SS[.pp]
    kwargs :
        fract : control decimals number
    """
    stime = []
    seconds = float(seconds)
    if seconds // 3600 > 0:
        stime.append(f"{int(seconds // 3600)}:")
    stime.append(f"{int((seconds // 60) % 60):02}:")
    stime.append(f"{int(seconds % 60):02}")
    if kwargs.get("fract", 0):
        fmt = f"%.{kwargs.get('fract', 0)}f"
        fract = fmt % (seconds % 1)
        fract = fract[1:]
        stime.append(fract)
    return "".join(stime)


def smart_unit(value, unit):
    """convert number in smart form : KB, MB, GB, TB"""
    if value is None:
        return f"- K{unit}"
    if isinstance(value, str):
        value = int(value)
    if value > 1000 * 1000 * 1000 * 1000:
        return f"{(value / (1000 * 1000 * 1000 * 1000.0)):.2f} T{unit}"
    if value > 1000 * 1000 * 1000:
        return f"{(value / (1000 * 1000 * 1000.0)):.2f} G{unit}"
    if value > 1000 * 1000:
        return f"{(value / (1000 * 1000.0)):.2f} M{unit}"
    if value > 1000:
        return f"{(value / (1000.0)):.2f} K{unit}"


def get_download_path():
    """return standard download folder"""
    if os.name == "nt":
        sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        return os.path.join(os.path.expanduser("~"), "downloads")


def get_all_loggers(project_path: str) -> set[str]:
    """
    Get all logger names used in the project.

    Args:
        project_path (str): The path to the project root directory.

    Returns:
        set[str]: A set of logger names.
    """
    if not os.path.isdir(project_path):
        project_path, _ = os.path.split(project_path)
    logger_names = set()
    pattern = re.compile(r"logging.getLogger\(([^)]+)\)")

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    matches = pattern.findall(content)
                    for match in matches:
                        match = match.strip()
                        if match.startswith('"') or match.startswith("'"):
                            match = match[1:-1]
                        if match == "__name__":
                            module_path = (
                                os.path.relpath(file_path, project_path)
                                .replace(".py", "")
                                .replace(os.path.sep, ".")
                            )
                            logger_names.add(module_path)
    return logger_names


def set_log_level(handler: logging.Handler, level_str: str):
    """set logging level"""
    try:
        # can be a number
        level = int(level_str)
        handler.setLevel(level)
        return
    except ValueError:
        pass
    try:
        handler.setLevel(logging.getLevelNamesMapping()[level_str.upper()])
    except KeyError:
        handler.setLevel(logging.INFO)


class ModuleAllowListFilter(logging.Filter):
    """Only allows records from modules in a predefined list."""

    def __init__(self, allowed_modules, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_modules = allowed_modules

    def filter(self, record):
        """filter log based on module name and level"""
        # check logger name
        module = record.name
        if module not in self.allowed_modules:
            return False
        # check level
        level_str = self.allowed_modules[module]
        level_num = getattr(logging, level_str.upper(), logging.INFO)
        return record.levelno >= level_num


def set_log_filter(handler: logging.Handler, modules: str):
    """
    set logging filter on handler

    :param handler: logging handler
    :param modules: comma-separated list of modules and levels, e.g. 'module1:INFO,module2:DEBUG'
    """
    modules_log = {}
    for part in modules.split(","):
        if ":" in part:
            module, level = part.split(":", 1)
            modules_log[module.strip()] = level.strip().upper()
        else:
            module = part.strip()
            modules_log[module] = "INFO"

    handler.addFilter(ModuleAllowListFilter(modules_log))


def avail_plugins_thumbsource():
    """
    get infos on available thumbnail source plugins

    return list of tuple (name, description)
    """
    avail = []
    loader = pluginlib.PluginLoader(modules=["plugins.thumbsource"])
    plugins = loader.plugins[list(loader.plugins.keys())[0]]
    for plugin_name, plugin_class in plugins.items():
        avail.append((plugin_name, plugin_class.description))
    return avail


class FifoList:
    """
    FIFO list with a fixed maximum size
      When the list reaches its maximum size, adding a new element will remove the oldest item.
      If the item already exists in the list, it will be moved to the head of the list
    """

    def __init__(self, max_size: int, move_existing=False):
        self.max_size = max_size
        self.move_existing = move_existing
        self._data = []

    def append(self, item):
        """append element"""
        if self.move_existing:
            if item in self._data:
                self._data.remove(item)
                self._data.insert(0, item)
                return
        if len(self._data) >= self.max_size:
            self._data.pop(0)
        self._data.append(item)

    def exists(self, item):
        """return True if item is in the list"""
        return item in self._data

    def clear(self):
        """
        Remove all items from the list.
        """
        self._data.clear()
