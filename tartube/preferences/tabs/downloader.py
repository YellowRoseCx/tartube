import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from mainapp import _

class DownloaderTab:
    def __init__(self, sys_pref_win):
        self.sys_pref_win = sys_pref_win

    def setup(self):
        tab, grid = self.sys_pref_win.add_notebook_tab(_('D_ownloader'), 5)
        inner_notebook = self.sys_pref_win.add_inner_notebook(grid)
        self.sys_pref_win.downloader_inner_notebook = inner_notebook
        self.sys_pref_win.setup_downloader_forks_tab(inner_notebook)
        self.sys_pref_win.setup_downloader_paths_tab(inner_notebook)
        self.sys_pref_win.setup_downloader_ffmpeg_tab(inner_notebook)
        self.sys_pref_win.setup_downloader_streamlink_tab(inner_notebook)
        self.sys_pref_win.setup_downloader_js_runtime_tab(inner_notebook)
