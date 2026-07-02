# Refactoring Plan: `tartube/mainwin.py`

## Overview
`mainwin.py` is an incredibly large file, currently sitting at over 42,000 lines of code. It contains the primary `MainWin` class (which is roughly 25,000 lines on its own), representing the main application window, along with numerous catalogue classes and roughly 40 GTK dialog classes.

This file is a classic example of a "God object" where the main window manages everything from low-level UI events to business logic, data presentation, and managing various dialogs.

## Refactoring Recommendations

To make this manageable, `mainwin.py` should be broken down into several smaller modules.

### 1. Extract Dialog Classes (`tartube/dialogs/`)
Lines 31090 to the end of the file contain almost 40 distinct GTK Dialog classes (`AddBulkDialogue`, `AddChannelDialogue`, `ExportDialogue`, etc.).
- **Action:** Create a new directory named `tartube/dialogs/`.
- **Action:** Move each dialog class into its own module within this directory (e.g., `tartube/dialogs/add_bulk.py`, `tartube/dialogs/add_channel.py`, `tartube/dialogs/export.py`).
- **Action:** Create a `tartube/dialogs/__init__.py` to expose these dialogs cleanly. This alone will remove over 11,000 lines from `mainwin.py`.

### 2. Extract UI Component Classes (`tartube/ui/`)
Lines 25061 to 31089 define classes that handle UI components that are not the main window itself, specifically the Catalogue display components (`SimpleCatalogueItem`, `ComplexCatalogueItem`, `GridCatalogueItem`, `CatalogueRow`, `CatalogueGridBox`), `DropZoneBox`, `StatusIcon`, and `MultiDragDropTreeView`.
- **Action:** Create a new directory named `tartube/ui/` (or similar).
- **Action:** Extract the catalogue classes into `tartube/ui/catalogue_items.py`.
- **Action:** Extract `DropZoneBox` into `tartube/ui/dropzone.py`.
- **Action:** Extract `StatusIcon` into `tartube/ui/status_icon.py`.
- **Action:** Extract `MultiDragDropTreeView` into `tartube/ui/drag_drop.py`.

### 3. Refactor `MainWin` Class (Lines 69 - 25060)
The `MainWin` class itself needs significant refactoring. At 25,000 lines, it handles too many responsibilities.
- **Action: Separate UI Construction from Logic.** The `__init__` method and associated UI building methods (setting up grids, lists, notebooks, menus) should be separated from event handling. Consider creating a `MainWindowUI` builder class or separating out the menu building logic (`tartube/ui/main_menu.py`) and layout logic.
- **Action: Extract Action Handlers.** The class likely contains hundreds of methods for handling button clicks, menu selections, and signals (e.g., `on_button_clicked`, `on_menu_item_selected`). Move these handlers out to controller classes or command patterns.
- **Action: Extract Data Formatting/Presentation.** If `MainWin` prepares data for GTK TreeViews/ListStores, this logic should be moved to a separate ViewModel or Presentation layer.
- **Action: Extract System Tray / External integration.** Logic handling system tray icons, drag-and-drop from the OS, or opening external players should be delegated to specialized manager classes.

## Execution Strategy
1. **Low Hanging Fruit:** Begin by extracting all the dialog classes. This is highly mechanical and low-risk, provided imports are updated in `mainwin.py`.
2. **UI Components:** Extract the catalogue and custom tree view classes next.
3. **MainWin Deconstruction:** Finally, begin dismantling the `MainWin` class. Start by moving the UI setup code into helper modules or a builder class, then systematically extract signal handlers to controller modules.
