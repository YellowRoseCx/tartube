import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from mainapp import _

class SchedulingTab:
    def __init__(self, sys_pref_win):
        self.sys_pref_win = sys_pref_win

    def setup(self):
        tab, grid = self.sys_pref_win.add_notebook_tab(_('Sche_duling'), 3)
        inner_notebook = self.sys_pref_win.add_inner_notebook(grid)
        self.sys_pref_win.setup_scheduling_start_tab(inner_notebook)
        self.sys_pref_win.setup_scheduling_stop_tab(inner_notebook)
