import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from mainapp import _

class FilesTab:
    def __init__(self, sys_pref_win):
        self.sys_pref_win = sys_pref_win

    def setup(self):
        tab, grid = self.sys_pref_win.add_notebook_tab(_('_Files'), 1)
        inner_notebook = self.sys_pref_win.add_inner_notebook(grid)
        self.sys_pref_win.files_inner_notebook = inner_notebook
        self.sys_pref_win.setup_files_filesystem_tab(inner_notebook)
        self.sys_pref_win.setup_files_write_move_tab(inner_notebook)
        self.sys_pref_win.setup_files_paths_tab(inner_notebook)
        self.sys_pref_win.setup_files_names_tab(inner_notebook)
        self.sys_pref_win.setup_files_urls_tab(inner_notebook)
        self.sys_pref_win.setup_files_videos_tab(inner_notebook)
        self.sys_pref_win.setup_files_temp_folders_tab(inner_notebook)
        self.sys_pref_win.setup_files_delete_tab(inner_notebook)
        self.sys_pref_win.setup_files_override_tab(inner_notebook)
        self.sys_pref_win.setup_files_keep_tab(inner_notebook)
        self.sys_pref_win.setup_files_database_tab(inner_notebook)
        self.sys_pref_win.setup_files_config_tab(inner_notebook)
        self.sys_pref_win.setup_files_backups_tab(inner_notebook)
        self.sys_pref_win.setup_files_history_tab(inner_notebook)
        self.sys_pref_win.setup_files_statistics_tab(inner_notebook)
        self.sys_pref_win.setup_files_cookies_tab(inner_notebook)
        self.sys_pref_win.setup_files_shortcuts_tab(inner_notebook)
        self.sys_pref_win.setup_files_device_tab(inner_notebook)
        self.sys_pref_win.setup_files_update_tab(inner_notebook)
