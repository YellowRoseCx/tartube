import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from mainapp import _

class WindowsTab:
    def __init__(self, sys_pref_win):
        self.sys_pref_win = sys_pref_win

    def setup(self):
        tab, grid = self.sys_pref_win.add_notebook_tab(_('_Windows'), 2)
        inner_notebook = self.sys_pref_win.add_inner_notebook(grid)
        self.sys_pref_win.setup_windows_main_window_tab(inner_notebook)
        self.sys_pref_win.setup_windows_colours_tab(inner_notebook)
        self.sys_pref_win.setup_windows_videos_tab(inner_notebook)
        self.sys_pref_win.setup_windows_websites_tab(inner_notebook)
        self.sys_pref_win.setup_windows_drag_tab(inner_notebook)
        self.sys_pref_win.setup_windows_dialogues_tab(inner_notebook)
        self.sys_pref_win.setup_windows_errors_warnings_tab(inner_notebook)
        self.sys_pref_win.setup_windows_system_tray_tab(inner_notebook)
