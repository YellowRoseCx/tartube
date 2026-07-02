# Refactoring Plan: `tartube/mainapp.py`

## Overview
`mainapp.py` is 30,000 lines long and contains a single class: `TartubeApp`. This class inherits from `Gtk.Application` and represents the absolute core of the program. It acts as the central hub connecting the UI, the database, the downloader threads, and the application's configuration.

The file is almost entirely composed of methods attached to `TartubeApp`. There are hundreds of methods handling everything from database integrity checks (`check_integrity_db`) to GTK menu action handlers (`on_menu_add_channel`), and getter/setter boilerplate for configuration (`set_ytdl_path`, `set_allow_ytdl_archive_mode`).

## Refactoring Recommendations

Because `TartubeApp` acts as the central router for the application, breaking it apart requires extracting groups of related methods into separate managers or controllers that the main app can instantiate and delegate to.

### 1. Extract Database Management (`tartube/core/database.py`)
`TartubeApp` is heavily involved in database lifecycle management.
- **Action:** Extract methods like `load_db`, `save_db`, `switch_db`, `update_db`, `check_integrity_db`, `fix_integrity_db`, `export_from_db`, and `import_into_db`.
- **Action:** Create a `DatabaseManager` class in `tartube/core/database.py` that is instantiated by `TartubeApp`.
- **Action:** Update references in `TartubeApp` to call `self.db_manager.load_db()` instead of handling it directly.

### 2. Extract Menu and Action Handlers (`tartube/core/actions.py`)
There are dozens of `on_menu_*` methods (e.g., `on_menu_import_yt`, `on_menu_quit`, `on_menu_test_ytdl`) which handle the business logic when a user clicks a menu item.
- **Action:** Create an `ActionController` or `MenuHandler` class.
- **Action:** Move the `on_menu_*` functions to this controller. The controller will likely need a reference to the `TartubeApp` instance or specific managers (like the download manager or database manager) to execute the actions.

### 3. Extract Configuration/State Getters and Setters (`tartube/core/state.py` or `config_manager.py`)
A huge portion of this file appears to be basic getters and setters (e.g., `set_ytdl_fork`, `set_ytdlp_filter_options_flag`, etc.). This suggests the application state/configuration is tightly coupled to the application class itself.
- **Action:** Extract these properties into a dedicated `AppConfig` or `AppState` data class or configuration manager.
- **Action:** Modify `TartubeApp` to delegate these calls to the configuration manager, or better yet, refactor the calling code to access the configuration manager directly, bypassing `TartubeApp` entirely.

### 4. Extract Application Lifecycle and OS Integration (`tartube/core/lifecycle.py`)
Methods related to startup, shutdown, system error handling (`system_error`, `system_warning`), auto-detecting paths, and checking external dependencies should be grouped.
- **Action:** Move dependency checking (`check_external`, `auto_detect_paths`) to an `EnvironmentManager` or a setup module.

## Execution Strategy
Refactoring `mainapp.py` is the highest risk operation because it touches every part of the system.
1. **Identify the Seams:** Start by identifying completely independent blocks of methods (like the import/export logic).
2. **Extract Managers:** Create the `DatabaseManager` and move database lifecycle methods. Ensure `TartubeApp` instantiates it in `__init__`.
3. **Move Action Handlers:** Extract the UI action callbacks to a separate controller.
4. **Decouple Configuration:** Shift the mass of getter/setter methods into a dedicated configuration object.
5. **Iterative Testing:** Because this file handles application state, each extraction must be paired with extensive manual testing (or automated tests if they exist) to ensure the application still boots and core functions work.
