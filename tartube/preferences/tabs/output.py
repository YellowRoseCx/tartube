import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from mainapp import _

class OutputTab:
    def __init__(self, sys_pref_win):
        self.sys_pref_win = sys_pref_win

    def setup(self):
        tab, grid = self.sys_pref_win.add_notebook_tab(_('O_utput'), 7)
        inner_notebook = self.sys_pref_win.add_inner_notebook(grid)
        self.sys_pref_win.setup_output_outputtab_tab(inner_notebook)
        self.sys_pref_win.setup_output_log_tab(inner_notebook)
        self.sys_pref_win.setup_output_terminal_tab(inner_notebook)
        self.sys_pref_win.setup_output_general_tab(inner_notebook)
