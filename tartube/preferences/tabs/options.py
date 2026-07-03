import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from mainapp import _

class OptionsTab:
    def __init__(self, sys_pref_win):
        self.sys_pref_win = sys_pref_win

    def setup(self):
        tab, grid = self.sys_pref_win.add_notebook_tab(_('O_ptions'), 6)
        inner_notebook = self.sys_pref_win.add_inner_notebook(grid)
        self.sys_pref_win.setup_options_dl_prefs_tab(inner_notebook)
        self.sys_pref_win.setup_options_dl_list_tab(inner_notebook)
        self.sys_pref_win.setup_options_ffmpeg_list_tab(inner_notebook)
