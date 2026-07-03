import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from mainapp import _

class GeneralTab:
    def __init__(self, sys_pref_win):
        self.sys_pref_win = sys_pref_win

    def setup(self):
        tab, grid = self.sys_pref_win.add_notebook_tab(_('_General'), 0)
        inner_notebook = self.sys_pref_win.add_inner_notebook(grid)
        self.setup_general_application_tab(inner_notebook)
        if not self.sys_pref_win.app_obj.simple_prefs_flag:
            self.setup_general_modules_tab(inner_notebook)

    def setup_general_application_tab(self, inner_notebook):
        self.sys_pref_win.setup_general_application_tab(inner_notebook)

    def setup_general_modules_tab(self, inner_notebook):
        self.sys_pref_win.setup_general_modules_tab(inner_notebook)
