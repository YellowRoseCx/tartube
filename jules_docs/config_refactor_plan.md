# Refactoring Plan: `tartube/config.py`

## Overview
`config.py` is approximately 36,000 lines long. Surprisingly, despite its name, it does not primarily handle configuration data loading/saving (which seems to be handled elsewhere, potentially in `mainapp.py` or a database). Instead, this file contains the UI classes for all the complex configuration/preferences windows and edit dialogs.

The file consists of 11 very large classes, mostly inheriting from `GenericConfigWin`, `GenericEditWin`, or `GenericPrefWin`. `SystemPrefWin` starts at line 20584 and goes to the end of the file (making it over 15,000 lines long).

## Refactoring Recommendations

The structure here is much cleaner than `mainwin.py` because it's already divided into distinct classes, they are just massive because of the sheer number of preferences and settings available in Tartube.

### 1. Extract Base Classes (`tartube/preferences/base.py`)
- **Action:** Create a new directory, e.g., `tartube/preferences/` or `tartube/config_ui/`.
- **Action:** Move the base classes `GenericConfigWin`, `GenericEditWin`, and `GenericPrefWin` into a shared base module (e.g., `tartube/preferences/base.py`).

### 2. Extract Editor Window Classes (`tartube/preferences/editors/`)
The classes `CustomDLEditWin`, `OptionsEditWin`, `FFmpegOptionsEditWin`, `VideoEditWin`, `ChannelPlaylistEditWin`, `FolderEditWin`, and `ScheduledEditWin` are self-contained property windows for different entities.
- **Action:** Extract each of these classes into their own file within an `editors` sub-package.
    - `tartube/preferences/editors/custom_dl.py`
    - `tartube/preferences/editors/options.py`
    - `tartube/preferences/editors/ffmpeg.py`
    - `tartube/preferences/editors/video.py`
    - `tartube/preferences/editors/channel_playlist.py`
    - `tartube/preferences/editors/folder.py`
    - `tartube/preferences/editors/scheduled.py`

### 3. Refactor `SystemPrefWin` (`tartube/preferences/system_prefs.py`)
At 15,000+ lines, `SystemPrefWin` is the largest window in this file. It likely handles the main "Preferences" dialog, which likely has many tabs/notebook pages.
- **Action:** Move `SystemPrefWin` to its own file `tartube/preferences/system_prefs.py`.
- **Action (Deep Refactor):** A 15,000 line preferences window usually means that the UI construction for every single tab in a `Gtk.Notebook` is stuffed into one `__init__` or `setup_ui` method. Break down the UI creation by moving the construction of each tab's contents into separate methods or separate classes (e.g., `GeneralTab`, `DownloadTab`, `NetworkTab`, `AppearanceTab`). This will greatly improve readability.

## Execution Strategy
This refactoring is primarily about file splitting and namespace management.
1. Create the target directory structure (`tartube/preferences/`).
2. Move the base classes.
3. Move the editor classes one by one, ensuring the imports are fixed.
4. Move `SystemPrefWin`.
5. Finally, tackle the internal complexity of `SystemPrefWin` by componentizing its tabs/sections.
