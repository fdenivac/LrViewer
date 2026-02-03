"""
some common utilities
"""

import os
import winreg


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
