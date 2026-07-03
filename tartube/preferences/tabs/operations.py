import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from mainapp import _

class OperationsTab:
    def __init__(self, sys_pref_win):
        self.sys_pref_win = sys_pref_win

    def setup(self):
        tab, grid = self.sys_pref_win.add_notebook_tab(_('O_perations'), 4)
        inner_notebook = self.sys_pref_win.add_inner_notebook(grid)
        self.sys_pref_win.operations_inner_notebook = inner_notebook
        self.sys_pref_win.setup_operations_downloads_tab(inner_notebook)
        self.sys_pref_win.setup_operations_stop_tab(inner_notebook)
        self.sys_pref_win.setup_operations_limits_tab(inner_notebook)
        self.sys_pref_win.setup_operations_livestreams_tab(inner_notebook)
        self.sys_pref_win.setup_operations_actions_tab(inner_notebook)
        self.sys_pref_win.setup_operations_archive_tab(inner_notebook)
        self.sys_pref_win.setup_operations_ignore_tab(inner_notebook)
        self.sys_pref_win.setup_operations_slices_tab(inner_notebook)
        self.sys_pref_win.setup_operations_custom_dl_tab(inner_notebook)
        self.sys_pref_win.setup_operations_clips_tab(inner_notebook)
        self.sys_pref_win.setup_operations_missing_tab(inner_notebook)
        self.sys_pref_win.setup_operations_proxies_tab(inner_notebook)
        self.sys_pref_win.setup_operations_mirrors_tab(inner_notebook)
        self.sys_pref_win.setup_operations_prefs_tab(inner_notebook)
