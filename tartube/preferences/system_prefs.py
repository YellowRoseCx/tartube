# Import Gtk modules
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Gdk, GdkPixbuf

# Import other modules
import datetime
import html
import json
import os
import pickle
import re
import stat
import sys
import urllib.parse

# Import our modules
import __main__
import downloads
import formats
import mainapp
import mainwin
import media
import platform
import ttutils
from mainapp import _

# Import matplotlib stuff
if mainapp.HAVE_MATPLOTLIB_FLAG:
    from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
    from matplotlib.figure import Figure
    from matplotlib.ticker import MaxNLocator

# Import base classes
from tartube.preferences.tabs import (
    GeneralTab, FilesTab, WindowsTab, SchedulingTab,
    OperationsTab, DownloaderTab, OptionsTab, OutputTab
)

from tartube.preferences.base import GenericPrefWin


class SystemPrefWin(GenericPrefWin):

    """Python class for a 'preference window' to modify various system
    settings.

    Args:

        app_obj (mainapp.TartubeApp): The main application object

        init_mode (str or None): If specified, a tab is automatically selected;
            one of the values specified in the comments to self.select_tab()

    """


    # Standard class methods


    def __init__(self, app_obj, init_mode=None):

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences window starts here.' \
            + ' In the menu, click Edit > System preferences...'
        )

        Gtk.Window.__init__(self, title=_('System preferences'))

        if self.is_duplicate(app_obj, init_mode):
            return

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj


        # IV list - Gtk widgets
        # ---------------------
        self.grid = None                        # Gtk.Grid
        self.notebook = None                    # Gtk.Notebook
        self.files_inner_notebook = None        # Gtk.Notebook
        self.operations_inner_notebook = None   # Gtk.Notebook
        self.downloader_inner_notebook = None   # Gtk.Notebook
        self.ok_button = None                   # Gtk.Button
        # (IVs used to handle widget changes in the 'General' tab)
        self.radiobutton = None                 # Gtk.RadioButton
        self.radiobutton2 = None                # Gtk.RadioButton
        self.radiobutton3 = None                # Gtk.RadioButton
        self.radiobutton4 = None                # Gtk.RadioButton
        self.radiobutton5 = None                # Gtk.RadioButton
        self.spinbutton = None                  # Gtk.SpinButton
        self.spinbutton2 = None                 # Gtk.SpinButton
        self.spinbutton3 = None                 # Gtk.SpinButton
        self.spinbutton4 = None                 # Gtk.SpinButton
        # (IVs used to handle widget changes in the 'Files' tab)
        self.entry = None                       # Gtk.Entry
        self.entry2 = None                      # Gtk.Entry
        self.url_liststore = None               # Gtk.ListStore
        # (IVs used to handle widget changes in the 'Custom' tab)
        self.custom_liststore = None            # Gtk.ListStore
        # (IVs used to handle widget changes in the 'Livestream' tab)
        self.livestream_radiobutton = None      # Gtk.RadioButton
        self.livestream_radiobutton2 = None     # Gtk.RadioButton
        self.livestream_radiobutton3 = None     # Gtk.RadioButton
        self.livestream_radiobutton4 = None     # Gtk.RadioButton
        self.livestream_radiobutton5 = None     # Gtk.RadioButton
        # (IVs used to hanle widget changes in the 'Forks' tab)
        self.forks_radiobutton = None           # Gtk.RadioButton
        self.forks_radiobutton2 = None          # Gtk.RadioButton
        self.forks_radiobutton3 = None          # Gtk.RadioButton
        self.forks_entry = None                 # Gtk.RadioButton
        # (IVs used to hanle widget changes in the 'File paths' tab)
        self.filepaths_combo = None             # Gkt.ComboBox
        # (IVs used to handle widget changes in the 'Downloaders' tab)
        self.path_liststore = None              # Gtk.ListStore
        self.cmd_liststore = None               # Gtk.ListStore
        # (IVs used to handle widget changes in the 'Scheduling' tab)
        self.schedule_liststore = None          # Gtk.ListStore
        # (IVs used to handle widget changes in the 'Options' tab)
        self.options_liststore = None           # Gtk.ListStore
        self.ffmpeg_liststore = None            # Gtk.ListStore
        # (IVs used to open the window at a particular tab)
        self.filesinner_notebook = None         # Gtk.Notebook
        self.operations_inner_notebook = None   # Gtk.Notebook


        # IV list - other
        # ---------------
        # Size (in pixels) of gaps between preference window widgets
        self.spacing_size = self.app_obj.default_spacing_size

        # Code
        # ----

        # Set up the preference window
        self.setup()

        # Automatically open a particular tab, if required
        self.select_tab(init_mode)


    # Public class methods


    def is_duplicate(self, app_obj, init_mode=None):

        """Called by self.__init__.

        Don't open this preference window, if another preference window of the
        same class is already open.

        If 'init_mode' is specified, switch the visible tab in the existing
        preference window (if any).

        Args:

            app_obj (mainapp.TartubeApp): The main application object

            init_mode (str or None): One of the values specified in the
                comments to self.select_tab()

        Return values:

            True if a duplicate is found, False if not

        """

        for config_win_obj in app_obj.main_win_obj.config_win_list:

            if type(self) == type(config_win_obj):

                # Duplicate found. Make it prominent...
                config_win_obj.present()
                # ...and switch to a particular tab, if required
                config_win_obj.select_tab(init_mode)

                return True

        # Not a duplicate
        return False


#   def setup():                # Inherited from GenericConfigWin


#   def setup_grid():           # Inherited from GenericConfigWin


#   def setup_notebook():       # Inherited from GenericConfigWin


#   def add_notebook_tab():     # Inherited from GenericConfigWin


#   def setup_button_strip():   # Inherited from GenericPrefWin


#   def setup_gap():            # Inherited from GenericConfigWin


    def select_tab(self, init_mode=None):

        """Called by self.__init__().

        On startup, automatically open a particular tab, if required.

        Args:

            init_mode (str or None): If specified:
                - 'clips' - video clip preferences
                - 'custom_dl' - custom download preferences
                - 'db' - options for switching the Tartube database
                - 'downloads' - Download operation preferences
                - 'forks' - youtube-dl forks,
                - 'live' - livestream options
                - 'options' - the list of download options
                - 'paths' - youtube-dl paths,
                - 'slices' - video slice preferences
                - (any other value is ignored)

        """

        if init_mode is not None:

            if init_mode == 'clips':
                self.select_clips_tab()
            elif init_mode == 'custom_dl':
                self.select_custom_dl_tab()
            elif init_mode == 'db':
                self.select_switch_db_tab()
            elif init_mode == 'downloads':
                self.select_downloads_tab()
            elif init_mode == 'forks':
                self.select_forks_tab()
            elif init_mode == 'live':
                self.select_livestream_tab()
            elif init_mode == 'options':
                self.select_options_tab()
            elif init_mode == 'paths':
                self.select_paths_tab()
            elif init_mode == 'slices':
                self.select_slices_tab()


    def select_clips_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the video clip preferences are
        displayed.
        """

        # Opens tab: self.setup_operations_clips_tab()
        if not self.app_obj.simple_prefs_flag:
            self.notebook.set_current_page(4)
            self.operations_inner_notebook.set_current_page(8)
        else:
            self.notebook.set_current_page(4)
            self.operations_inner_notebook.set_current_page(7)


    def select_custom_dl_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the custom download preferences
        are displayed.
        """

        # Opens tab: self.setup_operations_custom_dl_tab()
        self.notebook.set_current_page(4)
        self.operations_inner_notebook.set_current_page(4)


    def select_switch_db_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the user can set Tartube's
        data directory (which contains the Tartube database file).
        """

        # Opens tab: self.setup_files_database_tab()
        if not self.app_obj.simple_prefs_flag:
            self.notebook.set_current_page(1)
            self.files_inner_notebook.set_current_page(2)
        else:
            self.notebook.set_current_page(1)
            self.files_inner_notebook.set_current_page(0)


    def select_downloads_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the custom download preferences
        are displayed.
        """

        # Opens tab: self.setup_operations_downloads_tab()
        self.notebook.set_current_page(4)
        self.operations_inner_notebook.set_current_page(2)


    def select_forks_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the user can set youtube-dl
        forks.
        """

        # Opens tab: self.setup_downloader_forks_tab()
        self.notebook.set_current_page(5)
        self.downloader_inner_notebook.set_current_page(0)


    def select_livestream_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the user can set livestream
        options.
        """

        # Opens tab: self.setup_operations_livestreams_tab()
        if not self.app_obj.simple_prefs_flag:
            self.notebook.set_current_page(4)
            self.operations_inner_notebook.set_current_page(6)
        else:
            self.notebook.set_current_page(4)
            self.operations_inner_notebook.set_current_page(5)


    def select_options_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the list of download options is
        displayed.
        """

        # Opens tab: self.setup_options_dl_list_tab()
        self.notebook.set_current_page(6)


    def select_paths_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the user can set youtube-dl
        paths.
        """

        # Opens tab: self.setup_downloader_paths_tab()
        self.notebook.set_current_page(5)
        self.downloader_inner_notebook.set_current_page(1)


    def select_slices_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the video slice preferences are
        displayed.
        """

        # Opens tab: self.setup_operations_slices_tab()
        if not self.app_obj.simple_prefs_flag:
            self.notebook.set_current_page(4)
            self.operations_inner_notebook.set_current_page(9)
        else:
            self.notebook.set_current_page(4)
            self.operations_inner_notebook.set_current_page(8)


    # (Setup tabs)


    def setup_tabs(self):

        """Called by self.setup(), .on_button_apply_clicked() and
        .on_button_reset_clicked().

        Sets up the tabs for this preference window.
        """

        GeneralTab(self).setup()
        FilesTab(self).setup()
        WindowsTab(self).setup()
        SchedulingTab(self).setup()
        OperationsTab(self).setup()
        DownloaderTab(self).setup()
        OptionsTab(self).setup()
        OutputTab(self).setup()



    def setup_general_application_tab(self, inner_notebook):

        """Called by self.setup_general_tab().

        Sets up the 'Application' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > General > Application'
        )

        # Import the main window (for convenience)
        main_win_obj = self.app_obj.main_win_obj

        tab, grid = self.add_inner_notebook_tab(
            _('_Application'),
            inner_notebook,
        )
        grid_width = 3

        # Application details
        self.add_label(grid,
            '<u>' + _('Application details') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Version'),
            0, 1, 1, 1,
        )
        label.set_hexpand(False)

        self.entry = self.add_entry(grid,
            __main__.__version__,
            False,
            1, 1, 1, 1,
        )

        self.entry = self.add_entry(grid,
            __main__.__date__,
            False,
            2, 1, 1, 1,
        )

        label = self.add_label(grid,
            _('Locale override'),
            0, 2, 1, 1,
        )
        label.set_hexpand(False)

        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        store.append(
            [
                self.app_obj.main_win_obj.pixbuf_dict['slice_small'],
                _('Use your system locale'),
                ''
            ]
        )

        # (This list is for a second combo, using the same list as the one
        #   above, but not clickable by the user)
        label2 = self.add_label(grid,
            _('Current locale'),
            0, 3, 1, 1,
        )
        label2.set_hexpand(False)

        store2 = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        store2.append(
            [
                self.app_obj.main_win_obj.pixbuf_dict['slice_small'],
                _('Unrecognised locale'),
                ''
            ]
        )

        for this_locale in formats.LOCALE_LIST:

            # (Some locales are in format "en_GB", some in format "fr")
            if not 'flag_' + this_locale in \
            self.app_obj.main_win_obj.pixbuf_dict:
                flag_locale = this_locale[:2]
            else:
                flag_locale = this_locale

            pixbuf = \
            self.app_obj.main_win_obj.pixbuf_dict['flag_' + flag_locale]

            store.append(
                [ pixbuf, formats.LOCALE_DICT[this_locale], this_locale ],
            )
            store2.append(
                [ pixbuf, formats.LOCALE_DICT[this_locale], this_locale ],
            )

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, 1, 2, 1, 1)
        combo.set_hexpand(False)

        renderer_pixbuf = Gtk.CellRendererPixbuf()
        combo.pack_start(renderer_pixbuf, False)
        combo.add_attribute(renderer_pixbuf, 'pixbuf', 0)

        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 1)

        if self.app_obj.override_locale is None:
            combo.set_active(0)
        else:
            combo.set_active(
                formats.LOCALE_LIST.index(self.app_obj.override_locale) + 1
            )
        combo.connect('changed', self.on_locale_combo_changed, grid)

        combo2 = Gtk.ComboBox.new_with_model(store2)
        grid.attach(combo2, 1, 3, 1, 1)
        combo2.set_hexpand(False)
        combo2.set_sensitive(False)

        renderer_pixbuf = Gtk.CellRendererPixbuf()
        combo2.pack_start(renderer_pixbuf, False)
        combo2.add_attribute(renderer_pixbuf, 'pixbuf', 0)

        renderer_text = Gtk.CellRendererText()
        combo2.pack_start(renderer_text, True)
        combo2.add_attribute(renderer_text, 'text', 1)

        if self.app_obj.current_locale is None:
            combo2.set_active(0)

        elif self.app_obj.current_locale in formats.LOCALE_LIST:
            combo2.set_active(
                formats.LOCALE_LIST.index(self.app_obj.current_locale) + 1
            )

        else:

            # (Some locales are in format "en_GB", some in format "fr")
            alt_locale = self.app_obj.current_locale[:2]
            if alt_locale in formats.LOCALE_LIST:
                combo2.set_active(
                    formats.LOCALE_LIST.index(alt_locale) + 1
                )

            else:
                combo2.set_active(0)

        # N.B. The call to self.on_locale_combo_changed() can create another
        #   secondary grid at 0, 4

        # Preferences mode
        self.add_label(grid,
            '<u>' + _('Preferences mode') + '</u>',
            0, 5, grid_width, 1,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 6, grid_width, 1)

        if self.app_obj.simple_prefs_flag:
            frame = self.add_pixbuf(grid2,
                'hand_right_large',
                0, 0, 1, 1,
            )
            frame.set_hexpand(False)
            frame.set_size_request(75, -1)

        else:
            frame = self.add_pixbuf(grid2,
                'hand_left_large',
                0, 0, 1, 1,
            )
            frame.set_hexpand(False)
            frame.set_size_request(75, -1)

        button = Gtk.Button()
        grid2.attach(button, 1, 0, 1, 1)
        if not self.app_obj.simple_prefs_flag:
            button.set_label(_('Hide advanced preferences'))
        else:
            button.set_label(_('Show advanced preferences'))
        button.set_hexpand(True)
        button.connect('clicked', self.on_simple_prefs_clicked)


    def setup_general_modules_tab(self, inner_notebook):

        """Called by self.setup_general_tab().

        Sets up the 'Modules' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > General > Modules'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Modules'), inner_notebook)
        grid_width = 2

        # Module availability
        self.add_label(grid,
            '<u>' + _('Module availability') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _(
            'feedparser module is available (required for detecting' \
            + ' livestreams)',
            ),
            mainapp.HAVE_FEEDPARSER_FLAG,
            False,                      # Can't be toggled by user
            0, 1, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _('matplotlib module is available (draws graphs)'),
            mainapp.HAVE_MATPLOTLIB_FLAG,
            False,                      # Can't be toggled by user
            0, 2, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _(
            'moviepy module is available (finds the length of videos, if' \
            + ' unknown)',
            ),
            mainapp.HAVE_MOVIEPY_FLAG,
            False,                      # Can't be toggled by user
            0, 3, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _(
            'playsound3 module is available (sound an alarm when a' \
            + ' livestream starts)',
            ),
            mainapp.HAVE_PLAYSOUND_FLAG,
            False,                      # Can't be toggled by user
            0, 4, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _(
            'XDG module is available (saves the config file in the standard' \
            + ' location)',
            ),
            mainapp.HAVE_XDG_FLAG,
            False,                      # Can't be toggled by user
            0, 5, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _(
            'Notify module is available (shows desktop notifications; Linux/' \
            + '*BSD only)',
            ),
            mainapp.HAVE_NOTIFY_FLAG,
            False,                      # Can't be toggled by user
            0, 6, grid_width, 1,
        )

        # Module preferences
        self.add_label(grid,
            '<u>' + _('Module preferences') + '</u>',
            0, 7, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'Use \'moviepy\' module to get a video\'s duration, if not known'
            + ' (may be slow)',
            ),
            self.app_obj.use_module_moviepy_flag,
            True,                   # Can be toggled by user
            0, 8, grid_width, 1,
        )
        checkbutton.connect('toggled', self.on_moviepy_button_toggled)
        if not mainapp.HAVE_MOVIEPY_FLAG:
            checkbutton.set_sensitive(False)

        self.add_label(grid,
            _('Timeout applied when moviepy checks a video file'),
            0, 9, 1, 1,
        )

        spinbutton = self.add_spinbutton(grid,
            0,
            60,
            1,                  # Step
            self.app_obj.refresh_moviepy_timeout,
            1, 9, 1, 1,
        )
        spinbutton.connect(
            'value-changed',
            self.on_moviepy_timeout_spinbutton_changed,
        )


    def setup_files_device_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Device' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Device'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Device'), inner_notebook)
        grid_width = 3

        # Device preferences
        self.add_label(grid,
            '<u>' + _('Device preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            _('Size of device'),
            0, 3, 1, 1,
        )

        self.entry = self.add_entry(grid,
            str(ttutils.disk_get_total_space(self.app_obj.data_dir)),
            False,
            1, 3, 1, 1,
        )
        self.entry.set_sensitive(False)

        self.add_label(grid,
            'GiB',
            2, 3, 1, 1,
        )

        self.add_label(grid,
            _('Free space on device'),
            0, 4, 1, 1,
        )

        self.entry2 = self.add_entry(grid,
            str(ttutils.disk_get_free_space(self.app_obj.data_dir)),
            False,
            1, 4, 1, 1,
        )
        self.entry2.set_sensitive(False)

        self.add_label(grid,
            'GiB',
            2, 4, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
                'Before checking/downloading videos, warn user if disk space' \
                + ' is less than',
            ),
            self.app_obj.disk_space_warn_flag,
            True,                   # Can be toggled by user
            0, 5, grid_width, 1,
        )
        # (Signal connect appears below)

        spinbutton = self.add_spinbutton(grid,
            0, None,
            self.app_obj.disk_space_increment,
            self.app_obj.disk_space_warn_limit,
            1, 6, 1, 1,
        )
        if not self.app_obj.disk_space_warn_flag:
            spinbutton.set_sensitive(False)
        # (Signal connect appears below)

        self.add_label(grid,
            'GiB',
            2, 6, 1, 1,
        )

        checkbutton2 = self.add_checkbutton(grid,
            _('Halt downloads if disk space is less than'),
            self.app_obj.disk_space_stop_flag,
            True,                   # Can be toggled by user
            0, 7, 1, 1,
        )
        # (Signal connect appears below)

        spinbutton2 = self.add_spinbutton(grid,
            0, None,
            self.app_obj.disk_space_increment,
            self.app_obj.disk_space_stop_limit,
            1, 7, 1, 1,
        )
        if not self.app_obj.disk_space_stop_flag:
            spinbutton2.set_sensitive(False)
        # (Signal connect appears below)

        self.add_label(grid,
            'GiB',
            2, 7, 1, 1,
        )

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_disk_warn_button_toggled,
            spinbutton,
        )
        spinbutton.connect(
            'value-changed',
            self.on_disk_warn_spinbutton_changed,
        )
        checkbutton2.connect(
            'toggled',
            self.on_disk_stop_button_toggled,
            spinbutton2,
        )
        spinbutton2.connect(
            'value-changed',
            self.on_disk_stop_spinbutton_changed,
        )


    def setup_files_config_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Config' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Config'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Config'), inner_notebook)

        # Configuration preferences
        self.add_label(grid,
            '<u>' + _('Configuration preferences') + '</u>',
            0, 0, 1, 1,
        )

        self.add_label(grid,
            _('Tartube configuration file loaded from'),
            0, 1, 1, 1,
        )

        entry = self.add_entry(grid,
            self.app_obj.get_config_path(),
            False,
            0, 2, 1, 1,
        )
        entry.set_sensitive(False)

        self.add_label(grid,
            _('Default location for Tartube configuration'),
            0, 3, 1, 1,
        )

        entry2 = self.add_entry(grid,
            self.app_obj.config_file_xdg_path,
            False,
            0, 4, 1, 1,
        )
        entry2.set_sensitive(False)

        self.add_label(grid,
            _('Alternative location for Tartube configuration'),
            0, 5, 1, 1,
        )

        entry3 = self.add_entry(grid,
            self.app_obj.config_file_path,
            False,
            0, 6, 1, 1,
        )
        entry3.set_sensitive(False)


    def setup_files_database_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Database' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Database'
        )

        tab, grid = self.add_inner_notebook_tab(_('D_atabase'), inner_notebook)
        grid_width = 2

        # Database preferences
        self.add_label(grid,
            '<u>' + _('Database preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Current data folder'),
            0, 1, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid,
            self.app_obj.data_dir,
            False,
            1, 1, 1, 1,
        )
        entry.set_sensitive(False)

        label2 = self.add_label(grid,
            _('Current database'),
            0, 2, 1, 1,
        )
        label2.set_hexpand(False)

        entry2 = self.add_entry(grid,
            os.path.abspath(
                os.path.join(
                    self.app_obj.data_dir, self.app_obj.db_file_name,
                ),
            ),
            False,
            1, 2, 1, 1,
        )
        entry2.set_sensitive(False)

        label3 = self.add_label(grid,
            _('Recent data folders'),
            0, 3, 1, 1,
        )
        label3.set_hexpand(False)

        treeview, liststore = self.add_treeview(grid,
            1, 3, 1, 1,
        )
        treeview.set_vexpand(False)
        for item in self.app_obj.data_dir_alt_list:
            liststore.append([item])

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 4, grid_width, 1)

        button = Gtk.Button(_('Add new database'))
        grid2.attach(button, 0, 0, 1, 1)
        button.set_tooltip_text(_('Change to a different data folder'))
        button.set_hexpand(True)
        button.connect(
            'clicked',
            self.on_data_dir_change_button_clicked,
        )

        button2 = Gtk.Button(_('Check and repair database'))
        grid2.attach(button2, 1, 0, 2, 1)
        button2.set_tooltip_text(
            _('Check for inconsistencies, and repair them'),
        )
        button2.set_hexpand(True)
        button2.connect('clicked', self.on_data_check_button_clicked)

        button3 = Gtk.Button(_('Dump database to JSON'))
        grid2.attach(button3, 3, 0, 2, 1)
        button3.set_tooltip_text(
            _('Convert databases to JSON, even when Tartube can\'t load them'),
        )
        button3.set_hexpand(True)
        button3.connect('clicked', self.on_dump_db_button_clicked, treeview)

        button4 = Gtk.Button(_('Switch to this database'))
        grid2.attach(button4, 0, 1, 1, 1)
        button4.set_tooltip_text(_('Switch to the selected data folder'))
        button4.set_hexpand(True)
        button4.set_sensitive(False)
        button4.connect(
            'clicked',
            self.on_data_dir_switch_button_clicked,
            button,
            treeview,
        )

        button5 = Gtk.Button(_('Forget'))
        grid2.attach(button5, 1, 1, 1, 1)
        button5.set_tooltip_text(
            _('Remove the selected data folder from the list'),
        )
        button5.set_hexpand(True)
        button5.set_sensitive(False)
        button5.connect(
            'clicked',
            self.on_data_dir_forget_button_clicked,
            treeview,
        )

        button6 = Gtk.Button(_('Forget all'))
        grid2.attach(button6, 2, 1, 1, 1)
        button6.set_tooltip_text(
            _('Forget every folder in this list (except the current one)'),
        )
        button6.set_hexpand(True)
        if len(self.app_obj.data_dir_alt_list) <= 1:
            button6.set_sensitive(False)
        button6.connect(
            'clicked',
            self.on_data_dir_forget_all_button_clicked,
            treeview,
        )

        button7 = Gtk.Button(_('Move up'))
        grid2.attach(button7, 3, 1, 1, 1)
        button7.set_tooltip_text(
            _('Move the selected folder up the list'),
        )
        button7.set_hexpand(True)
        button7.set_sensitive(False)
        # (Signal connect appears below)

        button8 = Gtk.Button(_('Move down'))
        grid2.attach(button8, 4, 1, 1, 1)
        button8.set_tooltip_text(
            _('Move the selected folder down the list'),
        )
        button8.set_hexpand(True)
        button8.set_sensitive(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        button7.connect(
            'clicked',
            self.on_data_dir_move_up_button_clicked,
            treeview,
            liststore,
            button8,
        )
        button8.connect(
            'clicked',
            self.on_data_dir_move_down_button_clicked,
            treeview,
            liststore,
            button7,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid3 = self.add_secondary_grid(grid, 0, 5, grid_width, 1)

        checkbutton = self.add_checkbutton(grid3,
            _(
            'On startup, load the first database on the list (not the most' \
            + ' recently-use one)',
            ),
            self.app_obj.data_dir_use_first_flag,
            True,               # Can be toggled by user
            0, 0, 2, 1,
        )
        checkbutton.connect('toggled', self.on_use_first_button_toggled)

        checkbutton2 = self.add_checkbutton(grid3,
            _('If one database is in use, try to load others'),
            self.app_obj.data_dir_use_list_flag,
            True,               # Can be toggled by user
            0, 1, 1, 1,
        )
        checkbutton2.connect('toggled', self.on_use_list_button_toggled)

        checkbutton3 = self.add_checkbutton(grid3,
            _('New databases are added to this list'),
            self.app_obj.data_dir_add_from_list_flag,
            True,               # Can be toggled by user
            1, 1, 1, 1,
        )
        checkbutton3.connect('toggled', self.on_add_from_list_button_toggled)

        # Everything must be desensitised, if load/save is disabled
        if self.app_obj.disable_load_save_flag:
            button.set_sensitive(False)
            button2.set_sensitive(False)
            button3.set_sensitive(False)
            button4.set_sensitive(False)
            button5.set_sensitive(False)
            button6.set_sensitive(False)
            button7.set_sensitive(False)
            button8.set_sensitive(False)
            checkbutton.set_sensitive(False)
            checkbutton2.set_sensitive(False)
            checkbutton3.set_sensitive(False)

        # (More signal connects from above)
        treeview.connect(
            'cursor-changed',
            self.on_data_dir_cursor_changed,
            button4,    # Switch
            button5,    # Forget
            button6,    # Forget all
            button7,    # Move up
            button8,    # Move down
        )


    def setup_files_backups_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Backups' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Backups'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Backups'), inner_notebook)
        grid_width = 3

        # Backup preferences
        self.add_label(grid,
            '<u>' + _('Backup preferences') + '</u>',
            0, 0, grid_width, 1,
        )
        self.add_label(grid,
            '<i>' + _(
                'When saving the database, Tartube makes a backup copy of' \
                + ' its database file',
            ) + '</i>',
            0, 1, grid_width, 1,
        )

        radiobutton = self.add_radiobutton(grid,
            None,
            _('Delete the backup as soon as the database has been saved'),
            0, 2, grid_width, 1,
        )
        # (Signal connect appears below)

        radiobutton2 = self.add_radiobutton(grid,
            radiobutton,
            _('Keep the backup file, replacing any previous backup file'),
            0, 3, grid_width, 1,
        )
        if self.app_obj.db_backup_mode == 'single':
            radiobutton2.set_active(True)
        # (Signal connect appears below)

        radiobutton3 = self.add_radiobutton(grid,
            radiobutton2,
            _('Make a new backup file once per day'),
            0, 4, grid_width, 1,
        )
        if self.app_obj.db_backup_mode == 'daily':
            radiobutton3.set_active(True)
        # (Signal connect appears below)

        radiobutton4 = self.add_radiobutton(grid,
            radiobutton3,
            _('Make a new backup file every time the database is saved'),
            0, 5, grid_width, 1,
        )
        if self.app_obj.db_backup_mode == 'always':
            radiobutton4.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        radiobutton.connect(
            'toggled',
            self.on_backup_button_toggled,
            'default',
        )
        radiobutton2.connect(
            'toggled',
            self.on_backup_button_toggled,
            'single',
        )
        radiobutton3.connect(
            'toggled',
            self.on_backup_button_toggled,
            'daily',
        )
        radiobutton4.connect(
            'toggled',
            self.on_backup_button_toggled,
            'always',
        )

        if not self.app_obj.simple_prefs_flag:

            # Export preferences
            self.add_label(grid,
                '<u>' + _('Export preferences') + '</u>',
                0, 6, grid_width, 1,
            )

            label = self.add_label(grid,
                _('Separator used in CSV exports'),
                0, 7, 1, 1,
            )
            label.set_hexpand(False)

            # (At the moment, Tartube only offers two choices of CSV separator)
            combo = self.add_combo(grid,
                ['|', ','],
                self.app_obj.export_csv_separator,
                1, 7, 1, 1,
            )
            combo.set_hexpand(False)
            combo.connect('changed', self.on_separator_combo_changed)

            # (Empty label for spacing)
            label = self.add_label(grid,
                '',
                2, 1, 1, 1,
            )
            label.set_hexpand(True)


    def setup_files_videos_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Videos' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Videos'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Videos'),
            inner_notebook,
        )
        grid_width = 3

        # Video matching preferences
        self.add_label(grid,
            '<u>' + _('Video matching preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            _('When matching videos on the filesystem:'),
            0, 1, grid_width, 1,
        )

        self.radiobutton3 = self.add_radiobutton(grid,
            None,
            _('The video names must match exactly'),
            0, 2, 1, 1,
        )
        # (Signal connect appears below)

        self.radiobutton4 = self.add_radiobutton(grid,
            self.radiobutton3,
            _('The first # characters must match exactly'),
            0, 3, 1, 1,
        )
        # (Signal connect appears below)

        self.spinbutton3 = self.add_spinbutton(grid,
            1, 999, 1, self.app_obj.match_first_chars,
            1, 3, 2, 1,
        )
        # (Signal connect appears below)

        self.radiobutton5 = self.add_radiobutton(grid,
            self.radiobutton4,
            _(
            'Ignore the last # characters; the remaining name must match' \
            + ' exactly',
            ),
            0, 4, 1, 1,
        )
        # (Signal connect appears below)

        self.spinbutton4 = self.add_spinbutton(grid,
            1, 999, 1, self.app_obj.match_ignore_chars,
            1, 4, 2, 1,
        )
        # (Signal connect appears below)

        # (Widgets are sensitised/desensitised, based on the radiobutton)
        if self.app_obj.match_method == 'exact_match':
            self.spinbutton3.set_sensitive(False)
            self.spinbutton4.set_sensitive(False)
        elif self.app_obj.match_method == 'match_first':
            self.radiobutton4.set_active(True)
            self.spinbutton4.set_sensitive(False)
        else:
            self.radiobutton5.set_active(True)
            self.spinbutton3.set_sensitive(False)

        # (Signal connects from above)
        self.radiobutton3.connect('toggled', self.on_match_button_toggled)
        self.radiobutton4.connect('toggled', self.on_match_button_toggled)
        self.radiobutton5.connect('toggled', self.on_match_button_toggled)
        self.spinbutton3.connect(
            'value-changed',
            self.on_match_spinbutton_changed,
        )
        self.spinbutton4.connect(
            'value-changed',
            self.on_match_spinbutton_changed,
        )

        self.add_label(grid,
            '<u>' + _('Video matching recommended preferences') + '</u>',
            0, 5, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
                'Check the video\'s original name and the downloaded file' \
                + ' name',
            ),
            self.app_obj.match_nickname_flag,
            True,               # Can be toggled by user
            0, 6, grid_width, 1,
        )
        checkbutton.set_hexpand(False)
        checkbutton.connect('toggled', self.on_match_nickname_button_toggled)

        self.add_label(grid,
            '<i>' + _(
                'N.B. If disabled, custom file templates will interfere' \
                + ' with video matching'
            ) + '</i>',
            0, 7, grid_width, 1,
        )


    def setup_files_delete_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Delete' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Delete'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('D_elete'),
            inner_notebook,
        )
        grid_width = 12

        # Automatic video deletion/removal preferences
        self.add_label(grid,
            '<u>' + _('Automatic video deletion/removal preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'Deleted videos are re-downloaded without an archive file.' \
                + ' See the Operations > Archive tab',
            ) + '</i>',
            0, 1, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Automatically delete downloaded videos'),
            self.app_obj.auto_delete_flag,
            True,               # Can be toggled by user
            0, 2, 6, 1,
        )
        # (Signal connect appears below)

        self.spinbutton = self.add_spinbutton(grid,
            0, 999, 1, self.app_obj.auto_delete_days,
            6, 2, 3, 1,
        )
        if not self.app_obj.auto_delete_flag:
            self.spinbutton.set_sensitive(False)
        # (Signal connect appears below)

        combo_list = [
            [ _('days since download'), 'download' ],
            [ _('days since upload'), 'upload' ],
        ]

        combo = self.add_combo_with_data(grid,
            combo_list,
            None,
            9, 2, 3, 1,
        )
        if self.app_obj.auto_delete_type_flag:
            combo.set_active(1)
        if not self.app_obj.auto_delete_flag:
            combo.set_sensitive(False)

        checkbutton2 = self.add_checkbutton(grid,
            _('Only downloaded videos from the database'),
            self.app_obj.auto_remove_flag,
            True,               # Can be toggled by user
            0, 3, 6, 1,
        )
        # (Signal connect appears below)

        self.spinbutton2 = self.add_spinbutton(grid,
            0, 999, 1, self.app_obj.auto_remove_days,
            6, 3, 3, 1,
        )
        if not self.app_obj.auto_remove_flag:
            self.spinbutton2.set_sensitive(False)
        # (Signal connect appears below)

        combo2 = self.add_combo_with_data(grid,
            combo_list,
            None,
            9, 3, 3, 1,
        )
        if self.app_obj.auto_remove_type_flag:
            combo2.set_active(1)
        if not self.app_obj.auto_remove_flag:
            combo2.set_sensitive(False)

        checkbutton3 = self.add_checkbutton(grid,
            _('Only delete/remove videos which have been watched'),
            self.app_obj.auto_delete_watched_flag,
            True,               # Can be toggled by user
            0, 4, grid_width, 1,
        )
        # (Signal connect appears below)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 5, grid_width, 1)

        self.add_label(grid2,
            _('Delete/remove files:'),
            0, 0, 2, 1,
        )

        self.radiobutton = self.add_radiobutton(grid2,
            None,
            _('When the database is loaded'),
            2, 0, 5, 1,
        )
        # (Signal connect appears below)

        self.radiobutton2 = self.add_radiobutton(grid2,
            self.radiobutton,
            _('After every download operation'),
            7, 0, 5, 1,
        )
        if self.app_obj.auto_delete_asap_flag:
            self.radiobutton2.set_active(True)

        if not self.app_obj.auto_delete_flag \
        and not self.app_obj.auto_remove_flag:
            checkbutton3.set_sensitive(False)
            self.radiobutton.set_sensitive(False)
            self.radiobutton2.set_sensitive(False)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_auto_delete_videos_button_toggled,
            self.spinbutton,
            combo,
            checkbutton2,
            checkbutton3,
            self.radiobutton,
            self.radiobutton2,
        )
        self.spinbutton.connect(
            'value-changed',
            self.on_auto_delete_videos_spinbutton_changed,
        )
        combo.connect('changed', self.on_auto_delete_type_combo_changed)
        checkbutton2.connect(
            'toggled',
            self.on_auto_remove_videos_button_toggled,
            self.spinbutton2,
            combo2,
            checkbutton,
            checkbutton3,
            self.radiobutton,
            self.radiobutton2,
        )
        self.spinbutton2.connect(
            'value-changed',
            self.on_auto_remove_videos_spinbutton_changed,
        )
        combo2.connect('changed', self.on_auto_remove_type_combo_changed)
        checkbutton3.connect('toggled', self.on_delete_watched_button_toggled)
        self.radiobutton.connect('toggled', self.on_delete_asap_button_toggled)

        # Manual video deletion/removal preferences
        self.add_label(grid,
            '<u>' + _('Manual video deletion/removal preferences') + '</u>',
            0, 6, grid_width, 1,
        )

        checkbutton4 = self.add_checkbutton(grid,
            _('Show dialogue window before removing video(s)'),
            self.app_obj.show_delete_video_dialogue_flag,
            True,               # Can be toggled by user
            0, 7, grid_width, 1,
        )
        checkbutton4.connect(
            'toggled',
            self.on_show_delete_video_button_toggled,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _('When removing videos, remove all files from the filesystem'),
            self.app_obj.delete_video_files_flag,
            True,               # Can be toggled by user
            0, 8, grid_width, 1,
        )
        checkbutton5.connect(
            'toggled',
            self.on_remove_video_file_button_toggled,
        )

        checkbutton6 = self.add_checkbutton(grid,
            _(
                'Show dialogue window before removing channels/playlists' \
                + '/folders',
            ),
            self.app_obj.show_delete_container_dialogue_flag,
            True,               # Can be toggled by user
            0, 9, grid_width, 1,
        )
        checkbutton6.connect(
            'toggled',
            self.on_show_delete_container_button_toggled,
        )

        checkbutton7 = self.add_checkbutton(grid,
            _(
                'When removing containers, remove all files from the' \
                + ' filesystem',
            ),
            self.app_obj.delete_container_files_flag,
            True,               # Can be toggled by user
            0, 10, grid_width, 1,
        )
        checkbutton7.connect(
            'toggled',
            self.on_remove_container_file_button_toggled,
        )


    def setup_files_update_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Update' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Update'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Update'),
            inner_notebook,
        )
        grid_width = 2

        # Update video descriptions
        self.add_label(grid,
            '<u>' + _('Update video descriptions') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' \
            + _(
                'These procedures might take a long time on a large database',
            ) \
            + '</i>',
            0, 1, grid_width, 1,
        )

        button = Gtk.Button.new_with_label(
            _('Update from description files, and set the line lengths to:'),
        )
        grid.attach(button, 0, 2, 1, 1)
        # (Signal connect appears below)

        min_value = self.app_obj.main_win_obj.medium_string_max_len
        max_value = self.app_obj.main_win_obj.descrip_line_max_len
        if max_value < min_value:
            max_value = min_value

        spinbutton = self.add_spinbutton(grid,
            min_value,
            max_value,
            1,
            self.app_obj.main_win_obj.descrip_line_max_len,
            1, 2, 1, 1,
        )

        button2 = Gtk.Button.new_with_label(
            _('Clear descriptions (does not modify the description files)'),
        )
        grid.attach(button2, 0, 3, grid_width, 1)
        # (Signal connect appears below)

        # (Signal connects from above)
        button.connect(
            'clicked',
            self.on_load_descrips_button_clicked,
            spinbutton,
        )

        button2.connect(
            'clicked',
            self.on_clear_descrips_button_clicked,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 4, grid_width, 1)

        # Video timestamps
        self.add_label(grid2,
            '<u>' + _('Video timestamps') + '</u>',
            0, 4, grid_width, 1,
        )

        button3 = Gtk.Button(_('Extract timestamps for all videos'))
        grid2.attach(button3, 0, 5, 1, 1)
        button3.set_hexpand(False)
        button3.connect(
            'clicked',
            self.on_extract_stamps_button_clicked,
        )

        button4 = Gtk.Button(_('Remove timestamps from all videos'))
        grid2.attach(button4, 1, 5, 1, 1)
        button4.set_hexpand(False)
        button4.connect(
            'clicked',
            self.on_remove_stamps_button_clicked,
        )

        # Video comments
        self.add_label(grid2,
            '<u>' + _('Video comments') + '</u>',
            0, 6, grid_width, 1,
        )

        button5 = Gtk.Button(_('Extract comments for all videos'))
        grid2.attach(button5, 0, 7, 1, 1)
        button5.set_hexpand(False)
        button5.connect(
            'clicked',
            self.on_extract_comments_button_clicked,
        )

        button6 = Gtk.Button(_('Remove comments from all videos'))
        grid2.attach(button6, 1, 7, 1, 1)
        button6.set_hexpand(False)
        button6.connect(
            'clicked',
            self.on_remove_comments_button_clicked,
        )

        self.add_label(grid,
            '<i>' + _(
                'Comments are extracted from each video\'s metadata file,' \
                + ' so this procedure may take a long time',
            ) + '</i>',
            0, 8, grid_width, 1,
        )


    def setup_files_urls_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'URLs' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > URLs'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('U_RLs'),
            inner_notebook,
        )
        grid_width = 2

        # Update channel/playlist URLs
        self.add_label(grid,
            '<u>' + _('Update channel/playlist URLs') + '</u>',
            0, 0, (grid_width - 1), 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Confirm every change'),
            self.app_obj.url_change_confirm_flag,
            True,               # Can be toggled by user
            (grid_width - 1), 0, 1, 1,
        )
        checkbutton.set_hexpand(False)
        checkbutton.connect(
            'toggled',
            self.on_confirm_url_button_toggled,
        )

        # (GenericConfigWin.add_treeview() doesn't support multiple columns, so
        #   we'll do everything ourselves)
        frame = Gtk.Frame()
        grid.attach(frame, 0, 1, grid_width, 1)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_headers_visible(True)
        # (Allow multiple selection)
        treeview.set_can_focus(True)
        selection = treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        for i, column_title in enumerate(
            [ 'hide', '', _('Name'), _('URL') ],
        ):
            if i == 1:
                renderer_pixbuf = Gtk.CellRendererPixbuf()
                column_pixbuf = Gtk.TreeViewColumn(
                    column_title,
                    renderer_pixbuf,
                    pixbuf=i,
                )
                treeview.append_column(column_pixbuf)
                column_pixbuf.set_resizable(False)
            else:
                renderer_text = Gtk.CellRendererText()
                column_text = Gtk.TreeViewColumn(
                    column_title,
                    renderer_text,
                    text=i,
                )
                treeview.append_column(column_text)
                column_text.set_resizable(True)
                if i == 0:
                    column_text.set_visible(False)
                elif i == 2:
                    renderer_text.set_property('editable', True)
                    renderer_text.connect(
                        'edited',
                        self.on_container_name_edited,
                        treeview,
                        checkbutton,
                    )
                elif i == 3:
                    renderer_text.set_property('editable', True)
                    renderer_text.connect(
                        'edited',
                        self.on_container_url_edited,
                        treeview,
                        checkbutton,
                    )

        self.url_liststore = Gtk.ListStore(
            int, GdkPixbuf.Pixbuf, str, str,
        )
        treeview.set_model(self.url_liststore)

        # Initialise the list
        self.setup_files_urls_tab_update_treeview()

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 2, grid_width, 1)

        # Strip of widgets beneath the list
        self.add_label(grid2,
            _('Pattern'),
            0, 0, 1, 1,
        )

        entry = self.add_entry(grid2,
            None,
            True,
            1, 0, 1, 1,
        )

        self.add_label(grid2,
            _('Substitution'),
            2, 0, 1, 1,
        )

        entry2 = self.add_entry(grid2,
            None,
            True,
            3, 0, 1, 1,
        )

        checkbutton2 = self.add_checkbutton(grid2,
            _('This pattern is a regex'),
            self.app_obj.url_change_regex_flag,
            True,               # Can be toggled by user
            0, 1, 2, 1,
        )
        checkbutton2.set_hexpand(False)
        checkbutton2.connect(
            'toggled',
            self.on_url_regex_button_toggled,
        )

        button = Gtk.Button(
            _('Search and replace text in the selected URLs'),
        )
        grid2.attach(button, 2, 1, 2, 1)
        button.set_hexpand(True)
        button.connect(
            'clicked',
            self.on_container_url_multiple_edited,
            entry,
            entry2,
            treeview,
        )

        button2 = Gtk.Button()
        grid2.attach(button2, 2, 2, 1, 1)
        button2.set_hexpand(True)
        button2.set_label(_('Open URLs'))
        button2.connect(
            'clicked',
            self.on_open_url_clicked,
            treeview,
        )

        button3 = Gtk.Button()
        grid2.attach(button3, 3, 2, 1, 1)
        button3.set_hexpand(True)
        button3.set_label(_('Refresh list'))
        button3.connect(
            'clicked',
            self.setup_files_urls_tab_update_treeview,
        )


    def setup_files_urls_tab_update_treeview(self, button=None):

        """ Called by self.setup_files_urls_tab().

        Fills or updates the treeview.

        Args:

            button (Gtk.Button): The widget clicked (if applicable)

        """

        self.url_liststore.clear()

        # Prepare a sorted list of channels/playlists to display in the
        #   treeview
        obj_list = []
        for media_data_obj in self.app_obj.container_reg_dict.values():

            if isinstance(media_data_obj, media.Channel) \
            or isinstance(media_data_obj, media.Playlist):
                obj_list.append(media_data_obj)

        obj_list.sort(key=lambda x: x.name.lower())

        # Add each channel/playlist to the treeview, one row at a time
        for media_data_obj in obj_list:
            self.setup_files_urls_tab_add_row(media_data_obj)


    def setup_files_urls_tab_add_row(self, media_data_obj):

        """Called by self.setup_scheduling_start_tab_update_treeview() and
        .on_scheduled_add_button_clicked().

        Adds a row to the treeview.

        Args:

            media_data_obj (media.Channel, media.Playlist): The media data
                object to display on this row

        """

        if isinstance(media_data_obj, media.Channel):
            pixbuf = self.app_obj.main_win_obj.pixbuf_dict['channel_small']
        else:
            pixbuf = self.app_obj.main_win_obj.pixbuf_dict['playlist_small']

        row_list = []
        row_list.append(media_data_obj.dbid)
        row_list.append(pixbuf)
        row_list.append(media_data_obj.name)
        row_list.append(media_data_obj.source)

        self.url_liststore.append(row_list)


    def setup_files_temp_folders_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Temporary folders' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Temporary'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Temporary'),
            inner_notebook,
        )

        # Temporary folder preferences
        self.add_label(grid,
            '<u>' + _('Temporary folder preferences') + '</u>',
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Empty temporary folders when Tartube shuts down'),
            self.app_obj.delete_on_shutdown_flag,
            True,               # Can be toggled by user
            0, 1, 1, 1,
        )
        # (Signal connect appears below)

        self.add_label(grid,
            '<i>' + _(
                '(N.B. Temporary folders are always emptied when Tartube' \
                + ' starts up)',
            ) + '</i>',
            0, 2, 1, 1,
        )

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Open temporary folders (on the desktop) when Tartube shuts down',
            ),
            self.app_obj.open_temp_on_desktop_flag,
            True,               # Can be toggled by user
            0, 3, 1, 1,
        )
        checkbutton2.connect('toggled', self.on_open_desktop_button_toggled)
        if self.app_obj.delete_on_shutdown_flag:
            checkbutton2.set_sensitive(False)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_delete_shutdown_button_toggled,
            checkbutton2,
        )


    def setup_files_statistics_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Statistics' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > Statistics'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Statistics'),
            inner_notebook,
        )
        grid_width = 4

        # Statistics
        self.add_label(grid,
            '<u>' + _('Statistics') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            _('The Tartube database contains:'),
            0, 1, grid_width, 1,
        )

        self.add_label(grid,
            _('Videos'),
            0, 2, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            False,
            1, 2, 1, 1,
        )

        self.add_label(grid,
            _('Downloaded'),
            0, 3, 1, 1,
        )

        entry2 = self.add_entry(grid,
            None,
            False,
            1, 3, 1, 1,
        )

        self.add_label(grid,
            _('Other'),
            0, 4, 1, 1,
        )

        entry3 = self.add_entry(grid,
            None,
            False,
            1, 4, 1, 1,
        )

        self.add_label(grid,
            _('Channels'),
            2, 2, 1, 1,
        )

        entry4 = self.add_entry(grid,
            None,
            False,
            3, 2, 1, 1,
        )

        self.add_label(grid,
            _('Playlists'),
            2, 3, 1, 1,
        )

        entry5 = self.add_entry(grid,
            None,
            False,
            3, 3, 1, 1,
        )

        self.add_label(grid,
            _('Custom folders'),
            2, 4, 1, 1,
        )

        entry6 = self.add_entry(grid,
            None,
            False,
            3, 4, 1, 1,
        )

        # Initialise the entries. Commented out so that the preference window
        #   will still appear quickly for enormous databases
#        self.setup_files_statistics_tab_recalculate(
#            entry,
#            entry2,
#            entry3,
#            entry4,
#            entry5,
#            entry6,
#        )

        button = Gtk.Button()
        grid.attach(button, 3, 5, 1, 1)
        button.set_label(_('Calculate'))
        button.connect(
            'clicked',
            self.on_recalculate_stats_button_clicked,
            entry,
            entry2,
            entry3,
            entry4,
            entry5,
            entry6,
        )


    def setup_files_statistics_tab_recalculate(self, entry, entry2, entry3,
    entry4, entry5, entry6):

        """Called by self.setup_files_statistics_tab and
        .on_recalculate_stats_button_clicked().

        Args:

            entry, entry2, entry3, entry4, entry5, entry6 (Gtk.Entry): The
                entry boxes to update

        """

        video_count = 0
        dl_count = 0
        not_dl_count = 0
        channel_count = 0
        playlist_count = 0
        folder_count = 0

        # Get number of videos, channels, playlists and sub-folders, and also
        #   downloaded/not downloaded videos
        # Ignore fixed (system) folders
        for media_data_obj in self.app_obj.media_reg_dict.values():

            if isinstance(media_data_obj, media.Video):

                video_count += 1

                if media_data_obj.dl_flag:
                    dl_count += 1
                else:
                    not_dl_count += 1

            elif isinstance(media_data_obj, media.Channel):

                channel_count += 1

            elif isinstance(media_data_obj, media.Playlist):

                playlist_count += 1

            elif isinstance(media_data_obj, media.Folder) \
            and not media_data_obj.fixed_flag:

                folder_count += 1

        entry.set_text(str(video_count))
        entry2.set_text(str(dl_count))
        entry3.set_text(str(not_dl_count))
        entry4.set_text(str(channel_count))
        entry5.set_text(str(playlist_count))
        entry6.set_text(str(folder_count))


    def setup_files_history_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'History' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Files > History'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_History'),
            inner_notebook,
        )
        grid_width = 6

        # Download history
        self.add_label(grid,
            '<u>' + _('Download history') + '</u>',
            0, 0, grid_width, 1,
        )

        # Add combos to customise the graph
        combo, combo2, combo3, combo4, combo5 = self.add_combos_for_graphs(
            grid,
            1,
        )

        # Add a button which, when clicked, draws the graph using the
        #   customisation options specified by the combos
        button = Gtk.Button()
        grid.attach(button, 5, 1, 1, 1)
        button.set_label(_('Draw'))
        # (Signal connect appears below)

        # Add a box, inside which we draw graphs
        hbox = Gtk.HBox()
        grid.attach(hbox, 0, 2, grid_width, 1)
        hbox.set_hexpand(True)
        hbox.set_vexpand(True)

        # (Signal connects from above)
        button.connect(
            'clicked', self.on_button_draw_graph_clicked,
            hbox,
            combo,
            combo2,
            combo3,
            combo4,
            combo5,
        )


    def setup_windows_main_window_tab(self, inner_notebook):

        """Called by self.setup_windows_tab().

        Sets up the 'Main Window' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Windows > Main Window'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Main window'),
            inner_notebook,
        )
        grid_width = 3

        # Main window preferences
        self.add_label(grid,
            '<u>' + _('Main window preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Remember size of the main window'),
            self.app_obj.main_win_save_size_flag,
            True,                   # Can be toggled by user
            0, 1, 1, 1,
        )
        # (Signal connect appears below)

        checkbutton2 = self.add_checkbutton(grid,
            _('Remember slider positions'),
            self.app_obj.main_win_save_slider_flag,
            True,                   # Can be toggled by user
            1, 1, 1, 1,
        )
        checkbutton2.connect('toggled', self.on_remember_slider_button_toggled)
        if not self.app_obj.main_win_save_size_flag:
            checkbutton2.set_sensitive(False)

        button = Gtk.Button(_('Reset both'))
        grid.attach(button, 2, 1, 1, 1)
        button.set_hexpand(True)
        button.connect(
            'clicked',
            self.on_reset_size_clicked,
        )

        # (Signal connect from above)
        checkbutton.connect(
            'toggled',
            self.on_remember_size_button_toggled,
            checkbutton2,
        )

        checkbutton3 = self.add_checkbutton(grid,
            _('Don\'t show the main window toolbar'),
            self.app_obj.toolbar_hide_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        # (Signal connect appears below)

        if not self.app_obj.simple_prefs_flag:

            checkbutton4 = self.add_checkbutton(grid,
                _('Don\'t show labels in the main window toolbar'),
                self.app_obj.toolbar_squeeze_flag,
                True,                   # Can be toggled by user
                1, 2, 2, 1,
            )
            checkbutton4.connect('toggled', self.on_squeeze_button_toggled)
            if self.app_obj.toolbar_hide_flag:
                checkbutton4.set_sensitive(False)

            # (Signal connect from above)
            checkbutton3.connect(
                'toggled',
                self.on_hide_toolbar_button_toggled,
                checkbutton4,
            )

        else:
            checkbutton3.connect(
                'toggled',
                self.on_hide_toolbar_button_toggled,
                None,
            )

        checkbutton5 = self.add_checkbutton(grid,
            _(
            'Replace stock icons with custom icons (in case stock icons' \
            + ' are not visible)',
            ),
            self.app_obj.show_custom_icons_flag,
            True,                   # Can be toggled by user
            0, 3, grid_width, 1,
        )
        checkbutton5.connect('toggled', self.on_show_custom_icons_toggled)

        if not self.app_obj.simple_prefs_flag:

            checkbutton6 = self.add_checkbutton(grid,
                _('Show tooltips for videos, channels, playlists and folders'),
                self.app_obj.show_tooltips_flag,
                True,                   # Can be toggled by user
                0, 4, grid_width, 1,
            )
            # (Signal connect appears below)

            checkbutton7 = self.add_checkbutton(grid,
                _(
                    'Show errors/warnings in tooltips (but not in the Videos' \
                    + ' tab)',
                ),
                self.app_obj.show_tooltips_extra_flag,
                True,                   # Can be toggled by user
                0, 5, grid_width, 1,
            )
            checkbutton7.connect(
                'toggled',
                self.on_show_tooltips_extra_toggled,
            )
            if not self.app_obj.show_tooltips_flag:
                checkbutton7.set_sensitive(False)

            # (Signal connect from above)
            checkbutton6.connect(
                'toggled',
                self.on_show_tooltips_toggled,
                checkbutton7,
            )

        checkbutton8 = self.add_checkbutton(grid,
            _(
            'Disable the download buttons in the toolbar and the Videos tab',
            ),
            self.app_obj.disable_dl_all_flag,
            True,                   # Can be toggled by user
            0, 6, grid_width, 1,
        )
        checkbutton8.connect('toggled', self.on_disable_dl_all_toggled)

        checkbutton9 = self.add_checkbutton(grid,
            _(
            'In the Progress tab, hide finished downloads',
            ),
            self.app_obj.progress_list_hide_flag,
            True,                   # Can be toggled by user
            0, 7, 1, 1,
        )
        checkbutton9.connect('toggled', self.on_hide_button_toggled)

        checkbutton10 = self.add_checkbutton(grid,
            _('Show downloads in reverse order'),
            self.app_obj.results_list_reverse_flag,
            True,                   # Can be toggled by user
            1, 7, 2, 1,
        )
        checkbutton10.connect('toggled', self.on_reverse_button_toggled)

        checkbutton11 = self.add_checkbutton(grid,
            _(
                'In the Progress/Classic Mode tabs, remember the width of' \
                + ' (some) columns',
            ),
            self.app_obj.progress_list_remember_width_flag,
            True,                   # Can be toggled by user
            0, 8, grid_width, 1,
        )
        checkbutton11.connect('toggled', self.on_remember_width_button_toggled)

        checkbutton12 = self.add_checkbutton(grid,
            _('When Tartube starts, automatically open the Classic Mode tab'),
            self.app_obj.show_classic_tab_on_startup_flag,
            True,               # Can be toggled by user
            0, 9, grid_width, 1,
        )
        checkbutton12.connect(
            'toggled',
            self.on_show_classic_mode_button_toggled,
        )
        if __main__.__pkg_no_download_flag__:
            checkbutton12.set_sensitive(False)

        if not self.app_obj.simple_prefs_flag:

            checkbutton13 = self.add_checkbutton(grid,
                _(
                'In the Classic Mode tab, when adding URLs, remove' \
                + ' duplicates rather than retaining them',
                ),
                self.app_obj.classic_duplicate_remove_flag,
                True,                   # Can be toggled by user
                0, 10, grid_width, 1,
            )
            checkbutton13.connect(
                'toggled',
                self.on_remove_duplicate_button_toggled,
            )

            checkbutton14 = self.add_checkbutton(grid,
                _(
                'In the Errors/Warnings tab, don\'t reset the tab title when' \
                + ' it is clicked',
                ),
                self.app_obj.system_msg_keep_totals_flag,
                True,                   # Can be toggled by user
                0, 11, grid_width, 1,
            )
            checkbutton14.connect(
                'toggled',
                self.on_system_keep_button_toggled,
            )


    def setup_windows_videos_tab(self, inner_notebook):

        """Called by self.setup_windows_tab().

        Sets up the 'Tabs' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Windows > Videos'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Videos'), inner_notebook)
        grid_width = 2

        # Video Index (left side of the Videos tab)
        self.add_label(grid,
            '<u>' + _('Video Index (left side of the Videos tab)') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Show a \'Custom download all\' button'),
            self.app_obj.show_custom_dl_button_flag,
            True,                   # Can be toggled by user
            0, 1, grid_width, 1,
        )
        checkbutton.connect('toggled', self.on_show_custom_dl_button_toggled)

        if not self.app_obj.simple_prefs_flag:

            checkbutton2 = self.add_checkbutton(grid,
                _('While checking/downloading videos, show free disk space'),
                self.app_obj.show_free_space_flag,
                True,                   # Can be toggled by user
                0, 2, grid_width, 1,
            )
            checkbutton2.connect(
                'toggled',
                self.on_show_free_space_button_toggled,
            )

            checkbutton3 = self.add_checkbutton(grid,
                _('Allow each row to be marked for checking/downloading'),
                self.app_obj.show_marker_in_index_flag,
                True,                   # Can be toggled by user
                0, 3, grid_width, 1,
            )
            checkbutton3.connect(
                'toggled',
                self.on_show_selector_button_toggled,
            )

            checkbutton4 = self.add_checkbutton(grid,
                _('Show smaller icons'),
                self.app_obj.show_small_icons_in_index_flag,
                True,                   # Can be toggled by user
                0, 4, grid_width, 1,
            )
            checkbutton4.connect('toggled', self.on_show_small_icons_toggled)

            checkbutton5 = self.add_checkbutton(grid,
                _(
                'Show detailed statistics about the videos in each channel' \
                + ' / playlist / folder',
                ),
                self.app_obj.complex_index_flag,
                True,               # Can be toggled by user
                0, 5, grid_width, 1,
            )
            checkbutton5.connect('toggled', self.on_complex_button_toggled)

        checkbutton6 = self.add_checkbutton(grid,
            _(
            'After clicking on a folder, automatically expand/collapse the' \
            + ' tree around it',
            ),
            self.app_obj.auto_expand_video_index_flag,
            True,                   # Can be toggled by user
            0, 6, grid_width, 1,
        )
        # (Signal connect appears below)

        checkbutton7 = self.add_checkbutton(grid,
            _(
            'Expand the whole tree, not just the level beneath the clicked' \
            + ' folder',
            ),
            self.app_obj.full_expand_video_index_flag,
            True,                   # Can be toggled by user
            0, 7, grid_width, 1,
        )
        if not self.app_obj.auto_expand_video_index_flag:
            checkbutton7.set_sensitive(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        checkbutton6.connect(
            'toggled',
            self.on_expand_tree_toggled,
            checkbutton7,
        )
        checkbutton7.connect('toggled', self.on_expand_full_tree_toggled)

        # Video Catalogue (right side of the Videos tab)
        self.add_label(grid,
            '<u>' + _('Video Catalogue (right side of the Videos tab)') \
            + '</u>',
            0, 8, grid_width, 1,
        )

        checkbutton8 = self.add_checkbutton(grid,
            _('Show \'today\' and \'yesterday\' as the date, when possible'),
            self.app_obj.show_pretty_dates_flag,
            True,                   # Can be toggled by user
            0, 9, grid_width, 1,
        )
        checkbutton8.connect('toggled', self.on_pretty_date_button_toggled)

        checkbutton9 = self.add_checkbutton(grid,
            _('Show livestreams with a different background colour'),
            self.app_obj.livestream_use_colour_flag,
            True,                   # Can be toggled by user
            0, 10, grid_width, 1,
        )
        # (Signal connect appears below)

        checkbutton10 = self.add_checkbutton(grid,
            _('Use same background colours for livestream and debut videos'),
            self.app_obj.livestream_simple_colour_flag,
            True,                   # Can be toggled by user
            0, 11, grid_width, 1,
        )
        if not self.app_obj.livestream_use_colour_flag:
            checkbutton10.set_sensitive(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        checkbutton9.connect(
            'toggled',
            self.on_livestream_colour_button_toggled,
            checkbutton10,
        )
        checkbutton10.connect(
            'toggled',
            self.on_livestream_simple_button_toggled,
        )

        if not self.app_obj.simple_prefs_flag:

            checkbutton11 = self.add_checkbutton(grid,
                _('Channel and playlist names are clickable (grid mode only)'),
                self.app_obj.catalogue_clickable_container_flag,
                True,                   # Can be toggled by user
                0, 12, grid_width, 1,
            )
            checkbutton11.connect('toggled', self.on_clickable_button_toggled)

        checkbutton12 = self.add_checkbutton(grid,
            _('Show nicknames (not video file names)'),
            self.app_obj.catalogue_show_nickname_flag,
            True,                   # Can be toggled by user
            0, 13, grid_width, 1,
        )
        checkbutton12.connect('toggled', self.on_nickname_button_toggled)


    def setup_windows_drag_tab(self, inner_notebook):

        """Called by self.setup_windows_tab().

        Sets up the 'Drag' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Windows > Drag'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Drag'), inner_notebook)

        # Drag and drop preferences
        self.add_label(grid,
            '<u>' + _('Drag and drop preferences') + '</u>',
            0, 0, 1, 1,
        )

        self.add_label(grid,
            '<i>' + _(
            'When dragging and dropping videos to an external application...',
            ) + '</i>',
            0, 1, 2, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Transfer the video\'s full file path'),
            self.app_obj.drag_video_path_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton.connect('toggled', self.on_drag_path_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _('Transfer the video\'s source URL'),
            self.app_obj.drag_video_source_flag,
            True,                   # Can be toggled by user
            0, 3, 1, 1,
        )
        checkbutton2.connect('toggled', self.on_drag_source_button_toggled)

        checkbutton3 = self.add_checkbutton(grid,
            _('Transfer the video\'s name'),
            self.app_obj.drag_video_name_flag,
            True,                   # Can be toggled by user
            0, 4, 1, 1,
        )
        checkbutton3.connect('toggled', self.on_drag_name_button_toggled)

        checkbutton4 = self.add_checkbutton(grid,
            _('Transfer error/warning messages'),
            self.app_obj.drag_video_msg_flag,
            True,                   # Can be toggled by user
            1, 2, 1, 1,
        )
        checkbutton4.connect('toggled', self.on_drag_msg_button_toggled)

        checkbutton5 = self.add_checkbutton(grid,
            _('Transfer the thumbnail\'s full file path'),
            self.app_obj.drag_thumb_path_flag,
            True,                   # Can be toggled by user
            1, 3, 1, 1,
        )
        checkbutton5.connect('toggled', self.on_drag_thumb_button_toggled)

        checkbutton6 = self.add_checkbutton(grid,
            _('Add a text separator before each item'),
            self.app_obj.drag_video_separator_flag,
            True,                   # Can be toggled by user
            1, 4, 1, 1,
        )
        checkbutton6.connect('toggled', self.on_drag_separator_button_toggled)

        self.add_label(grid,
            '<i>' + _(
            'When dragging and dropping messages from the Errors/Warnings' \
            + ' tab to an external application...',
            ) + '</i>',
            0, 5, 2, 1,
        )

        checkbutton7 = self.add_checkbutton(grid,
            _('Transfer the video/channel/playlist file path'),
            self.app_obj.drag_error_path_flag,
            True,                   # Can be toggled by user
            0, 6, 1, 1,
        )
        checkbutton7.connect('toggled', self.on_drag_error_path_button_toggled)

        checkbutton8 = self.add_checkbutton(grid,
            _('Transfer the video/channel/playlist URL'),
            self.app_obj.drag_error_source_flag,
            True,                   # Can be toggled by user
            0, 7, 1, 1,
        )
        checkbutton8.connect(
            'toggled',
            self.on_drag_error_source_button_toggled,
        )

        checkbutton9 = self.add_checkbutton(grid,
            _('Transfer the video/channel/playlist name'),
            self.app_obj.drag_error_name_flag,
            True,                   # Can be toggled by user
            0, 8, 1, 1,
        )
        checkbutton9.connect(
            'toggled',
            self.on_drag_error_name_button_toggled,
        )

        checkbutton10 = self.add_checkbutton(grid,
            _('Transfer error/warning messages'),
            self.app_obj.drag_error_msg_flag,
            True,                   # Can be toggled by user
            1, 6, 1, 1,
        )
        checkbutton10.connect(
            'toggled',
            self.on_drag_error_msg_button_toggled,
        )

        checkbutton11 = self.add_checkbutton(grid,
            _('Add a text separator before each item'),
            self.app_obj.drag_error_separator_flag,
            True,                   # Can be toggled by user
            1, 7, 1, 1,
        )
        checkbutton11.connect(
            'toggled',
            self.on_drag_error_separator_button_toggled,
        )


    def setup_windows_system_tray_tab(self, inner_notebook):

        """Called by self.setup_windows_tab().

        Sets up the 'System tray' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Windows > Tray'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Tray'),
            inner_notebook,
        )

        # System tray preferences
        self.add_label(grid,
            '<u>' + _('System tray preferences') + '</u>',
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Show Tartube in the system tray'),
            self.app_obj.show_status_icon_flag,
            True,               # Can be toggled by user
            0, 1, 1, 1,
        )
        checkbutton.set_hexpand(False)
        # (Signal connect appears below)

        checkbutton2 = self.add_checkbutton(grid,
            _('Start Tartube in the system tray'),
            self.app_obj.open_in_tray_flag,
            True,               # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton2.set_hexpand(False)
        # (Signal connect appears below)
        if not self.app_obj.show_status_icon_flag:
            checkbutton2.set_sensitive(False)

        checkbutton3 = self.add_checkbutton(grid,
            _('Close to the tray, rather than closing the application'),
            self.app_obj.close_to_tray_flag,
            True,               # Can be toggled by user
            0, 3, 1, 1,
        )
        checkbutton3.set_hexpand(False)
        # (Signal connect appears below)
        if not self.app_obj.show_status_icon_flag:
            checkbutton3.set_sensitive(False)

        checkbutton4 = self.add_checkbutton(grid,
            _(
            'After closing to the tray, restore the window\'s position' \
            + ' (does not work on Wayland)',
            ),
            self.app_obj.restore_posn_from_tray_flag,
            True,               # Can be toggled by user
            0, 4, 1, 1,
        )
        checkbutton4.set_hexpand(False)
        # (Signal connect appears below)
        if not self.app_obj.show_status_icon_flag \
        or not self.app_obj.close_to_tray_flag:
            checkbutton4.set_sensitive(False)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_show_status_icon_toggled,
            checkbutton2,
            checkbutton3,
            checkbutton4,
        )
        checkbutton2.connect('toggled', self.on_open_in_tray_toggled)
        checkbutton3.connect(
            'toggled',
            self.on_close_to_tray_toggled,
            checkbutton4,
        )
        checkbutton4.connect('toggled', self.on_restore_from_tray_toggled)


    def setup_windows_dialogues_tab(self, inner_notebook):

        """Called by self.setup_windows_tab().

        Sets up the 'Dialogues' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Windows > Dialogues'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('D_ialogues'),
            inner_notebook,
        )

        # Add media preferences
        self.add_label(grid,
            '<u>' + _('Add media preferences') + '</u>',
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('When adding channels/playlists, keep the dialogue window open'),
            self.app_obj.dialogue_keep_open_flag,
            True,               # Can be toggled by user
            0, 1, 1, 1,
        )
        checkbutton.set_hexpand(False)
        # (Signal connect appears below)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'When the dialogue window opens, add URLs from the system' \
            + ' clipboard',
            ),
            self.app_obj.dialogue_copy_clipboard_flag,
            True,               # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton2.set_hexpand(False)
        checkbutton2.connect('toggled', self.on_clipboard_button_toggled)
        if self.app_obj.dialogue_keep_open_flag:
            checkbutton2.set_sensitive(False)

        # (Signal connect from above)
        checkbutton.connect(
            'toggled',
            self.on_keep_open_button_toggled,
            checkbutton2,
        )

        checkbutton3 = self.add_checkbutton(grid,
            _(
            'When adding YouTube channels, remind the user to copy the' \
            + ' correct URL',
            ),
            self.app_obj.dialogue_yt_remind_flag,
            True,               # Can be toggled by user
            0, 3, 1, 1,
        )
        checkbutton3.set_hexpand(False)
        checkbutton3.connect('toggled', self.on_yt_remind_button_toggled)

        # Move media preferences
        self.add_label(grid,
            '<u>' + _('Move media preferences') + '</u>',
            0, 4, 1, 1,
        )

        checkbutton4 = self.add_checkbutton(grid,
            _(
            'Prompt the user before moving channels/playlists/folders in' \
            + ' the Video Index',
            ),
            self.app_obj.dialogue_move_container_flag,
            True,               # Can be toggled by user
            0, 5, 1, 1,
        )
        checkbutton4.set_hexpand(False)
        checkbutton4.connect('toggled', self.on_move_container_button_toggled)

        checkbutton5 = self.add_checkbutton(grid,
            _('Prompt the user before moving videos in the Video Index'),
            self.app_obj.dialogue_move_video_flag,
            True,               # Can be toggled by user
            0, 6, 1, 1,
        )
        checkbutton5.set_hexpand(False)
        checkbutton5.connect('toggled', self.on_move_video_button_toggled)

        checkbutton6 = self.add_checkbutton(grid,
            _(
                'After moving, switch to the destination in the Video' \
                + ' Catalogue',
            ),
            self.app_obj.dialogue_move_select_flag,
            True,               # Can be toggled by user
            0, 7, 1, 1,
        )
        checkbutton6.set_hexpand(False)
        checkbutton6.connect('toggled', self.on_move_select_button_toggled)

        # Debugging preferences
        self.add_label(grid,
            '<u>' + _('Debugging preferences') + '</u>',
            0, 8, 1, 1,
        )

        checkbutton7 = self.add_checkbutton(grid,
            _(
            'Temporarily disable message dialogue windows (display messages' \
            + ' in terminal instead)',
            ),
            self.app_obj.dialogue_disable_msg_flag,
            True,               # Can be toggled by user
            0, 9, 1, 1,
        )
        checkbutton7.set_hexpand(False)
        checkbutton7.connect('toggled', self.on_dialogue_disable_toggled)

        self.add_label(grid,
            '<i>' + _(
            'N.B. Tartube shows a dialogue window after checking or' \
            + ' downloading videos',
            ) + '</i>',
            0, 10, 1, 1,
        )

        self.add_label(grid,
            '<i>' + _(
            'That dialogue window can be disabled in the Operations >' \
            + ' Actions tab',
            ) + '</i>',
            0, 11, 1, 1,
        )


    def setup_windows_colours_tab(self, inner_notebook):

        """Called by self.setup_windows_tab().

        Sets up the 'Colours' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Windows > Colours'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Colours'),
            inner_notebook,
        )
        grid_width = 5

        # Video catalogue colour preferences
        self.add_label(grid,
            '<u>' + _('Video catalogue colour preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        self.setup_windows_colours_tab_add_row(grid,
            1,
            # Key in mainapp.TartubeApp.custom_bg_table
            'live_wait',
            _('Waiting livestreams'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            2,
            'live_now',
            _('Broadcasting livestreams'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            3,
            'debut_wait',
            _('Waiting debut videos'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            4,
            'debut_now',
            _('Broadcasting debut videos'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            5,
            'select',
            _('Selected videos'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            6,
            'select_wait',
            _('Selected waiting videos'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            7,
            'select_live',
            _('Selected broadcasting videos'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            8,
            'drag_drop_notify',
            _('Drag and Drop notification'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            9,
            'drag_drop_odd',
            _('Drag and Drop background 1'),
        )

        self.setup_windows_colours_tab_add_row(grid,
            10,
            'drag_drop_even',
            _('Drag and Drop background 2'),
        )


    def setup_windows_colours_tab_add_row(self, grid, row_num, key, descrip):

        """Called by self.setup_windows_colours_tab_add_row().

        Sets up a single row of widgets corresponding to a single key in
        mainapp.TartubeApp.custom_bg_table.

        Args:

            grid (Gtk.Grid): The grid on which widgets are attached

            row_num (int): Coordinates on the grid on which these widgets are
                place

            key (str): A key in mainapp.TartubeApp.custom_bg_table

            descrip (str): The label to use for this row

        """

        label = self.add_label(grid,
            descrip,
            0, row_num, 1, 1,
        )
        label.set_hexpand(False)

        label2 = self.add_label(grid,
            '<i>' + _('Custom colour:') + '</i>',
            1, row_num, 1, 1,
        )
        label2.set_hexpand(False)

        colorbutton = Gtk.ColorButton.new()
        grid.attach(colorbutton, 2, row_num, 1, 1)
        colorbutton.connect(
            'color-set',
            self.on_custom_colour_button_clicked,
            key,
        )

        mini_list = self.app_obj.custom_bg_table[key]
        custom_rgba_obj = Gdk.RGBA(
            mini_list[0],
            mini_list[1],
            mini_list[2],
            mini_list[3],
        )
        colorbutton.set_rgba(custom_rgba_obj)

        label3 = self.add_label(grid,
            '<i>' + _('Default colour:') + '</i>',
            3, row_num, 1, 1,
        )
        label3.set_hexpand(False)

        colorbutton2 = Gtk.ColorButton.new()
        grid.attach(colorbutton2, 4, row_num, 1, 1)
        colorbutton2.connect(
            'button-press-event',
            self.on_default_colour_button_clicked,
            colorbutton,
            key,
        )

        mini_list2 = self.app_obj.default_bg_table[key]
        default_rgba_obj = Gdk.RGBA(
            mini_list2[0],
            mini_list2[1],
            mini_list2[2],
            mini_list[3],
        )
        colorbutton2.set_rgba(default_rgba_obj)


    def setup_windows_errors_warnings_tab(self, inner_notebook):

        """Called by self.setup_windows_tab().

        Sets up the 'Errors/Warnings' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Windows >' \
            + ' Errors/Warnings'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Errors/Warnings'),
            inner_notebook,
        )

        # Errors/Warnings tab preferences
        self.add_label(grid,
            '<u>' + _('Errors/Warnings tab preferences') + '</u>',
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Show Tartube errors'),
            self.app_obj.system_error_show_flag,
            True,                   # Can be toggled by user
            0, 1, 1, 1,
        )
        checkbutton.connect('toggled', self.on_system_error_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _('Show Tartube warnings'),
            self.app_obj.system_warning_show_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton2.connect('toggled', self.on_system_warning_button_toggled)

        checkbutton3 = self.add_checkbutton(grid,
            _('Show operation errors'),
            self.app_obj.operation_error_show_flag,
            True,                   # Can be toggled by user
            0, 3, 1, 1,
        )
        checkbutton3.connect(
            'toggled',
            self.on_operation_error_button_toggled,
        )

        checkbutton4 = self.add_checkbutton(grid,
            _('Show operation warnings'),
            self.app_obj.operation_warning_show_flag,
            True,                   # Can be toggled by user
            0, 4, 1, 1,
        )
        checkbutton4.connect(
            'toggled',
            self.on_operation_warning_button_toggled,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _('Show dates'),
            self.app_obj.system_msg_show_date_flag,
            True,                   # Can be toggled by user
            0, 5, 1, 1,
        )
        checkbutton5.connect(
            'toggled',
            self.on_system_date_button_toggled,
        )

        checkbutton6 = self.add_checkbutton(grid,
            _('Show channel/playlist/folder names'),
            self.app_obj.system_msg_show_container_flag,
            True,                   # Can be toggled by user
            0, 6, 1, 1,
        )
        checkbutton6.connect(
            'toggled',
            self.on_system_container_button_toggled,
        )

        checkbutton7 = self.add_checkbutton(grid,
            _('Show video names'),
            self.app_obj.system_msg_show_video_flag,
            True,                   # Can be toggled by user
            0, 7, 1, 1,
        )
        checkbutton7.connect(
            'toggled',
            self.on_system_video_button_toggled,
        )

        checkbutton8 = self.add_checkbutton(grid,
            _('Show full messages'),
            self.app_obj.system_msg_show_multi_line_flag,
            True,                   # Can be toggled by user
            0, 8, 1, 1,
        )
        checkbutton8.connect(
            'toggled',
            self.on_system_multi_line_button_toggled,
        )


    def setup_windows_websites_tab(self, inner_notebook):

        """Called by self.setup_windows_tab().

        Sets up the 'Websites' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Windows > Websites'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Websites'),
            inner_notebook,
        )
        grid_width = 2

        # YouTube error/warning preferences
        self.add_label(grid,
            '<u>' + _('YouTube error/warning preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Ignore YouTube copyright errors'),
            self.app_obj.ignore_yt_copyright_flag,
            True,                   # Can be toggled by user
            0, 1, 1, 1,
        )
        checkbutton.connect('toggled', self.on_copyright_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _('Ignore YouTube age-restriction errors'),
            self.app_obj.ignore_yt_age_restrict_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton2.connect('toggled', self.on_age_restrict_button_toggled)

        checkbutton3 = self.add_checkbutton(grid,
            _('Ignore YouTube deletion by uploader errors'),
            self.app_obj.ignore_yt_uploader_deleted_flag,
            True,                   # Can be toggled by user
            1, 1, 1, 1,
        )
        checkbutton3.connect('toggled', self.on_uploader_button_toggled)

        checkbutton4 = self.add_checkbutton(grid,
            _('Ignore YouTube payment errors'),
            self.app_obj.ignore_yt_payment_flag,
            True,                   # Can be toggled by user
            1, 2, 1, 1,
        )
        checkbutton4.connect('toggled', self.on_payment_button_toggled)

        # General preferences
        self.add_label(grid,
            '<u>' + _('General preferences') + '</u>',
            0, 4, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'Ignore any errors/warnings which match lines in this list' \
                + ' (applies to all websites)',
            ) + '</i>',
            0, 5, grid_width, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            self.app_obj.ignore_custom_msg_list,
            0, 6, grid_width, 1
        )
        # (Signal connect appears below)

        radiobutton = self.add_radiobutton(grid,
            None,
            _('These are ordinary strings'),
            0, 7, 1, 1,
        )
        # (Signal connect appears below)

        radiobutton2 = self.add_radiobutton(grid,
            radiobutton,
            _('These are regular expressions (regexes)'),
            1, 7, 1, 1,
        )
        if self.app_obj.ignore_custom_regex_flag:
            radiobutton2.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        textbuffer.connect('changed', self.on_custom_textview_changed)
        radiobutton.connect(
            'toggled',
            self.on_regex_button_toggled,
            False,
        )
        radiobutton2.connect(
            'toggled',
            self.on_regex_button_toggled,
            True,
        )


    def setup_scheduling_start_tab(self, inner_notebook):

        """Called by self.setup_scheduling_tab().

        Sets up the 'Start' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Scheduling > Start'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Start'), inner_notebook)
        grid_width = 5

        # Scheduled download preferences
        self.add_label(grid,
            '<u>' + _('Scheduled download preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        # (GenericConfigWin.add_treeview() doesn't support multiple columns, so
        #   we'll do everything ourselves)
        frame = Gtk.Frame()
        grid.attach(frame, 0, 1, grid_width, 1)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_headers_visible(True)

        for i, column_title in enumerate(
            [
                _('Name'), _('Download'), _('Start mode'), _('Time'),
                _('Priority'), _('Whole'), _('Shutdown'), _('D/L All'),
                _('Join mode'),
            ]
        ):
            if i >= 4 and i <= 7:
                renderer_toggle = Gtk.CellRendererToggle()
                column_toggle = Gtk.TreeViewColumn(
                    column_title,
                    renderer_toggle,
                    active=i,
                )
                treeview.append_column(column_toggle)
                column_toggle.set_resizable(False)
            else:
                renderer_text = Gtk.CellRendererText()
                column_text = Gtk.TreeViewColumn(
                    column_title,
                    renderer_text,
                    text=i,
                )
                treeview.append_column(column_text)
                column_text.set_resizable(True)

        self.schedule_liststore = Gtk.ListStore(
            str, str, str, str, bool, bool, bool, bool, str,
        )
        treeview.set_model(self.schedule_liststore)

        # Initialise the list
        self.setup_scheduling_start_tab_update_treeview()

        # Add editing widgets
        label = self.add_label(grid,
            _('Scheduled download name'),
            0, 2, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid,
            None,
            True,
            1, 2, (grid_width - 2), 1,
        )

        button = Gtk.Button()
        grid.attach(button, (grid_width - 1), 2, 1, 1)
        button.set_label(_('Add'))
        button.connect(
            'clicked',
            self.on_scheduled_add_button_clicked,
            entry,
        )

        button2 = Gtk.Button()
        grid.attach(button2, 1, 3, 1, 1)
        button2.set_label(_('Edit'))
        button2.connect(
            'clicked',
            self.on_scheduled_edit_button_clicked,
            treeview,
        )

        button3 = Gtk.Button()
        grid.attach(button3, 2, 3, 1, 1)
        button3.set_label(_('Move up'))
        button3.connect(
            'clicked',
            self.on_scheduled_move_up_button_clicked,
            treeview,
        )

        button4 = Gtk.Button()
        grid.attach(button4, 3, 3, 1, 1)
        button4.set_label(_('Move down'))
        button4.connect(
            'clicked',
            self.on_scheduled_move_down_button_clicked,
            treeview,
        )

        button5 = Gtk.Button()
        grid.attach(button5, 4, 3, 1, 1)
        button5.set_label(_('Delete'))
        button5.connect(
            'clicked',
            self.on_scheduled_delete_button_clicked,
            treeview,
        )


    def setup_scheduling_start_tab_update_treeview(self):

        """ Called by self.setup_scheduling_start_tab() and
        mainapp.TartubeApp.del_scheduled_list().

        Fills or updates the treeview.
        """

        self.schedule_liststore.clear()

        for scheduled_obj in self.app_obj.scheduled_list:
            self.setup_scheduling_start_tab_add_row(scheduled_obj)


    def setup_scheduling_start_tab_add_row(self, scheduled_obj):

        """Called by self.setup_scheduling_start_tab_update_treeview() and
        .on_scheduled_add_button_clicked().

        Adds a row to the treeview.

        Args:

            scheduled_obj (media.Scheduled) - The scheduled download object to
                display on this row

        """

        row_list = []

        row_list.append(scheduled_obj.name)

        if scheduled_obj.dl_mode == 'sim':
            row_list.append(_('Check'))
        elif scheduled_obj.dl_mode == 'real':
            row_list.append(_('Download'))
        else:
            row_list.append(_('Custom'))

        row_list.append(scheduled_obj.start_mode)

        if scheduled_obj.start_mode != 'timetable':

            row_list.append(
                str(scheduled_obj.wait_value) + ' ' + scheduled_obj.wait_unit
            )

        elif scheduled_obj.timetable_list:

            # (Show the first day/time combination only)
            mini_list = scheduled_obj.timetable_list[0]
            row_list.append(
                formats.SPECIFIED_DAYS_DICT[mini_list[0]] + ' ' + mini_list[1],
            )

        else:

            row_list.append('')

        row_list.append(scheduled_obj.exclusive_flag)
        row_list.append(scheduled_obj.ignore_limits_flag)
        row_list.append(scheduled_obj.shutdown_flag)
        row_list.append(scheduled_obj.all_flag)
        row_list.append(scheduled_obj.join_mode)

        self.schedule_liststore.append(row_list)


    def setup_scheduling_stop_tab(self, inner_notebook):

        """Called by self.setup_scheduling_tab().

        Sets up the 'Stop' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Scheduling > Stop'
        )

        tab, grid = self.add_inner_notebook_tab(_('S_top'), inner_notebook)
        grid_width = 3

        # Scheduled stop preferences
        self.add_label(grid,
            '<u>' + _('Scheduled stop preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
            'N.B. Each scheduled download also has its own \'stop\' settings' \
            + ' which override these settings',
            ) + '</i>',
            0, 1, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Stop all download operations after this much time'),
            self.app_obj.autostop_time_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        # (Signal connect appears below)

        spinbutton = self.add_spinbutton(grid,
            1, None, 1, self.app_obj.autostop_time_value,
            1, 2, 1, 1,
        )
        if not self.app_obj.autostop_time_flag:
            spinbutton.set_sensitive(False)

        store = Gtk.ListStore(str, str)
        for string in formats.TIME_METRIC_LIST:
            store.append( [string, formats.TIME_METRIC_TRANS_DICT[string]] )

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, 2, 2, 1, 1)

        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 1)
        combo.set_entry_text_column(1)
        combo.set_active(
            formats.TIME_METRIC_LIST.index(
                self.app_obj.autostop_time_unit,
            )
        )
        if not self.app_obj.autostop_time_flag:
            combo.set_sensitive(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_autostop_time_button_toggled,
            spinbutton,
            combo,
        )
        spinbutton.connect(
            'value-changed',
            self.on_autostop_time_spinbutton_changed,
        )
        combo.connect('changed', self.on_autostop_time_combo_changed)

        checkbutton2 = self.add_checkbutton(grid,
            _('Stop all download operations after this many videos'),
            self.app_obj.autostop_videos_flag,
            True,                   # Can be toggled by user
            0, 3, 1, 1,
        )
        # (Signal connect appears below)

        spinbutton2 = self.add_spinbutton(grid,
            1, None, 1, self.app_obj.autostop_videos_value,
            1, 3, 1, 1,
        )
        if not self.app_obj.autostop_videos_flag:
            spinbutton2.set_sensitive(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        checkbutton2.connect(
            'toggled',
            self.on_autostop_videos_button_toggled,
            spinbutton2,
        )
        spinbutton2.connect(
            'value-changed',
            self.on_autostop_videos_spinbutton_changed,
        )

        checkbutton3 = self.add_checkbutton(grid,
            _('Stop all download operations after this much disk space'),
            self.app_obj.autostop_size_flag,
            True,                   # Can be toggled by user
            0, 4, 1, 1,
        )
        # (Signal connect appears below)

        spinbutton3 = self.add_spinbutton(grid,
            1, None, 1, self.app_obj.autostop_size_value,
            1, 4, 1, 1,
        )
        if not self.app_obj.autostop_size_flag:
            spinbutton3.set_sensitive(False)

        combo3 = self.add_combo(grid,
            formats.FILESIZE_METRIC_LIST,
            None,
            2, 4, 1, 1,
        )
        combo3.set_active(
            formats.FILESIZE_METRIC_LIST.index(
                self.app_obj.autostop_size_unit,
            )
        )
        if not self.app_obj.autostop_size_flag:
            combo3.set_sensitive(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        checkbutton3.connect(
            'toggled',
            self.on_autostop_size_button_toggled,
            spinbutton3,
            combo3,
        )
        spinbutton3.connect(
            'value-changed',
            self.on_autostop_size_spinbutton_changed,
        )
        combo3.connect('changed', self.on_autostop_size_combo_changed)

        self.add_label(grid,
            '<i>' + _(
                'N.B. Disk space is estimated. This setting does not apply' \
                + ' to simulated downloads',
            ) + '</i>',
            0, 5, grid_width, 1,
        )


    def setup_operations_limits_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Limits' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Limits'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Limits'),
            inner_notebook,
        )
        grid_width = 3

        # Performance limits
        self.add_label(grid,
            '<u>' + _('Performance limits') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _('Limits are applied when you start downloading a' \
            + ' video/channel/playlist') + '</i>',
            0, 1, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Limit simultaneous downloads to'),
            self.app_obj.num_worker_apply_flag,
            True,               # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton.set_hexpand(False)
        checkbutton.connect('toggled', self.on_worker_button_toggled)

        spinbutton = self.add_spinbutton(grid,
            self.app_obj.num_worker_min,
            self.app_obj.num_worker_max,
            1,                  # Step
            self.app_obj.num_worker_default,
            1, 2, 1, 1,
        )
        spinbutton.connect('value-changed', self.on_worker_spinbutton_changed)

        checkbutton2 = self.add_checkbutton(grid,
            _('Limit download speed to'),
            self.app_obj.bandwidth_apply_flag,
            True,               # Can be toggled by user
            0, 3, 1, 1,
        )
        checkbutton2.set_hexpand(False)
        checkbutton2.connect('toggled', self.on_bandwidth_button_toggled)

        spinbutton2 = self.add_spinbutton(grid,
            self.app_obj.bandwidth_min,
            self.app_obj.bandwidth_max,
            1,                  # Step
            self.app_obj.bandwidth_default,
            1, 3, 1, 1,
        )
        spinbutton2.connect(
            'value-changed',
            self.on_bandwidth_spinbutton_changed,
        )

        self.add_label(grid,
            'KiB/s',
            2, 3, 1, 1,
        )

        checkbutton3 = self.add_checkbutton(grid,
            _('Overriding video format options, limit video resolution to'),
            self.app_obj.video_res_apply_flag,
            True,               # Can be toggled by user
            0, 4, 1, 1,
        )
        checkbutton3.set_hexpand(False)
        checkbutton3.connect('toggled', self.on_video_res_button_toggled)

        combo = self.add_combo(grid,
            formats.VIDEO_RESOLUTION_LIST,
            None,
            1, 4, 1, 1,
        )
        combo.set_active(
            formats.VIDEO_RESOLUTION_LIST.index(
                self.app_obj.video_res_default,
            )
        )
        combo.connect('changed', self.on_video_res_combo_changed)

        # Alternative performance limits
        self.add_label(grid,
            '<u>' + _('Alternative performance limits') + '</u>',
            0, 5, grid_width, 1,
        )

        checkbutton4 = self.add_checkbutton(grid,
            _('Limit simultaneous downloads to'),
            self.app_obj.alt_num_worker_apply_flag,
            True,               # Can be toggled by user
            0, 6, 1, 1,
        )
        checkbutton4.set_hexpand(False)
        checkbutton4.connect('toggled', self.on_worker_button_toggled, True)

        spinbutton3 = self.add_spinbutton(grid,
            self.app_obj.num_worker_min,
            self.app_obj.num_worker_max,
            1,                  # Step
            self.app_obj.alt_num_worker,
            1, 6, 1, 1,
        )
        spinbutton3.connect(
            'value-changed',
            self.on_worker_spinbutton_changed,
            True,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _('Limit download speed to'),
            self.app_obj.alt_bandwidth_apply_flag,
            True,               # Can be toggled by user
            0, 7, 1, 1,
        )
        checkbutton5.set_hexpand(False)
        checkbutton5.connect('toggled', self.on_bandwidth_button_toggled, True)

        spinbutton4 = self.add_spinbutton(grid,
            self.app_obj.bandwidth_min,
            self.app_obj.bandwidth_max,
            1,                  # Step
            self.app_obj.alt_bandwidth,
            1, 7, 1, 1,
        )
        spinbutton4.connect(
            'value-changed',
            self.on_bandwidth_spinbutton_changed,
            True,
        )

        self.add_label(grid,
            'KiB/s',
            2, 7, 1, 1,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 8, (grid_width - 1), 1)

        label = self.add_label(grid2,
            _('Alternative limits apply between') + '   ',
            0, 0, 1, 1,
        )

        # (Hours in format '00' to '23')
        start_time = self.app_obj.alt_start_time
        stop_time = self.app_obj.alt_stop_time

        hour_list = []
        for h in range(24):
            hour_list.append('{:02d}'.format(h))

        # (Minutes in format '00', '05', 10' .. '55')
        minute_list = []
        for n in range(12):
            minute_list.append('{:02d}'.format(n*5))

        combo2 = self.add_combo(grid2,
            hour_list,
            None,
            1, 0, 1, 1,
        )
        combo2.set_active(hour_list.index(start_time[0:2]))
        combo2.connect('changed', self.on_alt_time_combo_changed, 'start_hour')

        label2 = self.add_label(grid2,
            ' : ',
            2, 0, 1, 1,
        )
        label2.set_hexpand(False)

        combo3 = self.add_combo(grid2,
            minute_list,
            None,
            3, 0, 1, 1,
        )
        combo3.set_active(minute_list.index(start_time[3:5]))
        combo3.connect('changed', self.on_alt_time_combo_changed, 'start_min')

        label3 = self.add_label(grid2,
            '   ' + _('and') + '   ',
            4, 0, 1, 1,
        )
        label3.set_hexpand(False)

        combo4 = self.add_combo(grid2,
            hour_list,
            None,
            5, 0, 1, 1,
        )
        combo4.set_active(hour_list.index(stop_time[0:2]))
        combo4.connect('changed', self.on_alt_time_combo_changed, 'stop_hour')

        label4 = self.add_label(grid2,
            ' : ',
            6, 0, 1, 1,
        )
        label4.set_hexpand(False)

        combo5 = self.add_combo(grid2,
            minute_list,
            None,
            7, 0, 1, 1,
        )
        combo5.set_active(minute_list.index(stop_time[3:5]))
        combo5.connect('changed', self.on_alt_time_combo_changed, 'stop_min')

        label5 = self.add_label(grid2,
            _('On days') + '   ',
            0, 1, 1, 1,
        )

        combo6_list = []
        for s in formats.SPECIFIED_DAYS_LIST:
            combo6_list.append( [formats.SPECIFIED_DAYS_DICT[s], s] )

        combo6 = self.add_combo_with_data(grid2,
            combo6_list,
            None,
            1, 1, 7, 1,
        )
        combo6.set_hexpand(False)
        combo6.set_active(
            formats.SPECIFIED_DAYS_LIST.index(self.app_obj.alt_day_string),
        )
        combo6.connect('changed', self.on_alt_days_combo_changed)


    def setup_operations_stop_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Stop' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Stop'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Stop'),
            inner_notebook,
        )
        grid_width = 2

        # Time-saving settings
        self.add_label(grid,
            '<u>' + _('Time-saving settings') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'Stop checking/downloading a channel/playlist when it finds' \
            + ' videos you already have',
            ),
            self.app_obj.operation_limit_flag,
            True,               # Can be toggled by user
            0, 1, grid_width, 1,
        )
        checkbutton.set_hexpand(False)
        # (Signal connect appears below)

        self.add_label(grid,
            _('Stop after this many videos (when checking)'),
            0, 2, 1, 1,
        )

        entry = self.add_entry(grid,
            self.app_obj.operation_check_limit,
            True,
            1, 2, 1, 1,
        )
        entry.set_width_chars(4)
        if not self.app_obj.operation_limit_flag:
            entry.set_sensitive(False)
        # (Signal connect appears below)

        self.add_label(grid,
            _('Stop after this many videos (when downloading)'),
            0, 3, 1, 1,
        )

        entry2 = self.add_entry(grid,
            self.app_obj.operation_download_limit,
            True,
            1, 3, 1, 1,
        )
        entry2.set_width_chars(4)
        if not self.app_obj.operation_limit_flag:
            entry2.set_sensitive(False)
        # (Signal connect appears below)

        checkbutton2 = self.add_checkbutton(grid,
            _('Include videos filtered by upload date, views or age limit'),
            self.app_obj.operation_limit_include_out_of_range_flag,
            True,               # Can be toggled by user
            0, 4, grid_width, 1,
        )
        checkbutton2.set_hexpand(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_limit_button_toggled,
            entry,
            entry2,
            checkbutton2,
        )
        entry.connect('changed', self.on_check_limit_changed)
        entry2.connect('changed', self.on_dl_limit_changed)
        checkbutton2.connect('toggled', self.on_limit_range_button_toggled)


    def setup_operations_downloads_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Downloads' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Downloads'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Downloads'),
            inner_notebook,
        )
        grid_width = 2

        # Download operation preferences
        self.add_label(grid,
            '<u>' + _('Download operation preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'Automatically update downloader before every download operation',
            ),
            self.app_obj.operation_auto_update_flag,
            True,                   # Can be toggled by user
            0, 1, grid_width, 1,
        )
        checkbutton.connect('toggled', self.on_auto_update_button_toggled)
        if __main__.__pkg_strict_install_flag__:
            checkbutton.set_sensitive(False)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Automatically save files at the end of all operations',
            ),
            self.app_obj.operation_save_flag,
            True,                   # Can be toggled by user
            0, 2, grid_width, 1,
        )
        checkbutton2.connect('toggled', self.on_save_button_toggled)

        if not self.app_obj.simple_prefs_flag:

            checkbutton3 = self.add_checkbutton(grid,
                _(
                'For simulated downloads, don\'t check a video in a folder' \
                + ' more than once',
                ),
                self.app_obj.operation_sim_shortcut_flag,
                True,                   # Can be toggled by user
                0, 3, grid_width, 1,
            )
            checkbutton3.connect(
                'toggled',
                self.on_operation_sim_button_toggled,
            )

            checkbutton4 = self.add_checkbutton(grid,
                _(
                'If a download stalls, restart it after this many minutes',
                ),
                self.app_obj.operation_auto_restart_flag,
                True,                   # Can be toggled by user
                0, 4, 1, 1,
            )
            # (Signal connect appears below)

            spinbutton = self.add_spinbutton(grid,
                1,
                None,
                1,                     # Step
                self.app_obj.operation_auto_restart_time,
                1, 4, 1, 1,
            )
            # (Signal connect appears below)
            if not self.app_obj.operation_auto_restart_flag:
                spinbutton.set_sensitive(False)

            self.add_label(grid,
                '     ' \
                + _(
                'Maximum restarts after a stalled download (0 for no maximum)',
                ),
                0, 5, 1, 1,
            )

            spinbutton2 = self.add_spinbutton(grid,
                0,
                None,
                1,                     # Step
                self.app_obj.operation_auto_restart_max,
                1, 5, 1, 1,
            )
            # (Signal connect appears below)
            if not self.app_obj.operation_auto_restart_flag:
                spinbutton2.set_sensitive(False)

            # (Signal connects from above)
            checkbutton4.connect(
                'toggled',
                self.on_auto_restart_button_toggled,
                spinbutton,
                spinbutton2,
            )
            spinbutton.connect(
                'value-changed',
                self.on_auto_restart_time_spinbutton_changed,
            )
            spinbutton2.connect(
                'value-changed',
                self.on_auto_restart_max_spinbutton_changed,
            )

            checkbutton5 = self.add_checkbutton(grid,
                _('Apply a timeout (in minutes) when checking a video'),
                self.app_obj.apply_json_timeout_flag,
                True,                   # Can be toggled by user
                0, 6, grid_width, 1,
            )
            # (Signal connect appears below)

            # (To avoid messing up the neat format of the rows above, add a
            #   secondary grid, and put the next set of widgets inside it)
            grid2 = self.add_secondary_grid(grid, 0, 7, grid_width, 1)

            label = self.add_label(grid2,
                _('Without comments'),
                0, 0, 1, 1,
            )

            spinbutton3 = self.add_spinbutton(grid2,
                1,
                None,
                1,                     # Step
                self.app_obj.json_timeout_no_comments_time,
                1, 0, 1, 1,
            )
            # (Signal connect appears below)
            if not self.app_obj.apply_json_timeout_flag:
                spinbutton3.set_sensitive(False)

            label2 = self.add_label(grid2,
                _('With comments'),
                2, 0, 1, 1,
            )

            spinbutton4 = self.add_spinbutton(grid2,
                1,
                None,
                1,                     # Step
                self.app_obj.json_timeout_with_comments_time,
                3, 0, 1, 1,
            )
            # (Signal connect appears below)
            if not self.app_obj.apply_json_timeout_flag:
                spinbutton4.set_sensitive(False)

            # (Signal connects from above)
            checkbutton5.connect(
                'toggled',
                self.on_json_button_toggled,
                spinbutton3,
                spinbutton4,
            )
            spinbutton3.connect(
                'value-changed',
                self.on_timeout_no_comments_spinbutton_changed,
            )
            spinbutton4.connect(
                'value-changed',
                self.on_timeout_with_comments_spinbutton_changed,
            )

            checkbutton6 = self.add_checkbutton(grid,
                _(
                'Assign anonymous error/warning messages to the most' \
                + ' probable video',
                ),
                self.app_obj.auto_assign_errors_warnings_flag,
                True,                   # Can be toggled by user
                0, 8, grid_width, 1,
            )
            checkbutton6.connect('toggled', self.on_auto_assign_button_toggled)

        checkbutton7 = self.add_checkbutton(grid,
            _(
            'Add censored, age-restricted and other blocked videos to the' \
            + ' database',
            ),
            self.app_obj.add_blocked_videos_flag,
            True,                   # Can be toggled by user
            0, 9, grid_width, 1,
        )
        checkbutton7.connect('toggled', self.on_add_blocked_button_toggled)

        if not self.app_obj.simple_prefs_flag:

            checkbutton8 = self.add_checkbutton(grid,
                _(
                'Extract playlist IDs from each video, and store them in the' \
                + ' parent channel/playlist',
                ),
                self.app_obj.store_playlist_id_flag,
                True,                   # Can be toggled by user
                0, 10, grid_width, 1,
            )
            checkbutton8.connect('toggled', self.on_store_playlist_id_toggled)

            checkbutton9 = self.add_checkbutton(grid,
                _(
                'Convert .webp thumbnails into .jpg thumbnails (using' \
                + '  FFmpeg) after downloading them',
                ),
                self.app_obj.ffmpeg_convert_webp_flag,
                True,                   # Can be toggled by user
                0, 11, grid_width, 1,
            )
            # (Signal connect appears below)

            checkbutton10 = self.add_checkbutton(grid,
                _(
                    '...but don\'t delete the original thumbnails (enable' \
                    + ' before embedding thumbnails in videos)',
                ),
                self.app_obj.ffmpeg_retain_webp_flag,
                True,                   # Can be toggled by user
                0, 12, grid_width, 1,
            )
            if not self.app_obj.ffmpeg_convert_webp_flag:
                checkbutton.set_sensitive(False)
            checkbutton10.connect(
                'toggled',
                self.on_ffmpeg_retain_flag_toggled,
            )

            # (Signal connects from above)
            checkbutton9.connect(
                'toggled',
                self.on_ffmpeg_convert_flag_toggled,
                checkbutton10,
            )


    def setup_operations_ignore_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Ignore' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Ignore'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Ignore'),
            inner_notebook,
        )
        grid_width = 2

        # Ignore downloader errors/warnings
        self.add_label(grid,
            '<u>' + _('Ignore downloader errors/warnings') + '</u>',
            0, 0, grid_width, 1,
        )

        ignore_me = _(
            'TRANSLATOR\'S NOTE: These error messages are always in English',
        )

        checkbutton = self.add_checkbutton(grid,
            _('Ignore \'Child process exited with non-zero code\' errors'),
            self.app_obj.ignore_child_process_exit_flag,
            True,                   # Can be toggled by user
            0, 1, grid_width, 1,
        )
        checkbutton.connect('toggled', self.on_child_process_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Ignore \'Unable to download video data\' and \'Unable to' \
            + ' extract video data\' errors',
            ),
            self.app_obj.ignore_http_404_error_flag,
            True,                   # Can be toggled by user
            0, 2, grid_width, 1,
        )
        checkbutton2.connect('toggled', self.on_http_404_button_toggled)

        checkbutton3 = self.add_checkbutton(grid,
            _('Ignore \'Did not get any data blocks\' errors'),
            self.app_obj.ignore_data_block_error_flag,
            True,                   # Can be toggled by user
            0, 3, grid_width, 1,
        )
        checkbutton3.connect('toggled', self.on_data_block_button_toggled)

        checkbutton4 = self.add_checkbutton(grid,
            _(
            'Ignore \'Requested formats are incompatible for merge\' warnings',
            ),
            self.app_obj.ignore_merge_warning_flag,
            True,                   # Can be toggled by user
            0, 4, grid_width, 1,
        )
        checkbutton4.connect('toggled', self.on_merge_button_toggled)

        checkbutton5 = self.add_checkbutton(grid,
            _('Ignore \'No video formats found\' errors'),
            self.app_obj.ignore_missing_format_error_flag,
            True,                   # Can be toggled by user
            0, 5, grid_width, 1,
        )
        checkbutton5.connect('toggled', self.on_missing_format_button_toggled)

        checkbutton6 = self.add_checkbutton(grid,
            _('Ignore \'There are no annotations to write\' warnings'),
            self.app_obj.ignore_no_annotations_flag,
            True,                   # Can be toggled by user
            0, 6, grid_width, 1,
        )
        checkbutton6.connect('toggled', self.on_no_annotations_button_toggled)

        checkbutton7 = self.add_checkbutton(grid,
            _('Ignore \'Video doesn\'t have subtitles\' warnings'),
            self.app_obj.ignore_no_subtitles_flag,
            True,                   # Can be toggled by user
            0, 7, grid_width, 1,
        )
        checkbutton7.connect('toggled', self.on_no_subtitles_button_toggled)

        checkbutton8 = self.add_checkbutton(grid,
            _('Ignore \'A channel/user page was given\' warnings'),
            self.app_obj.ignore_page_given_flag,
            True,                   # Can be toggled by user
            0, 8, grid_width, 1,
        )
        checkbutton8.connect('toggled', self.on_page_given_button_toggled)

        checkbutton9 = self.add_checkbutton(grid,
            _('Ignore \'There\'s no playlist description to write\' warnings'),
            self.app_obj.ignore_no_descrip_flag,
            True,                   # Can be toggled by user
            0, 9, grid_width, 1,
        )
        checkbutton9.connect('toggled', self.on_no_descrip_button_toggled)

        checkbutton10 = self.add_checkbutton(grid,
            _(
            'Ignore \'Unable to download video thumbnail: HTTP Error 404:' \
            + ' Not Found\' warnings',
            ),
            self.app_obj.ignore_thumb_404_flag,
            True,                   # Can be toggled by user
            0, 10, grid_width, 1,
        )
        checkbutton10.connect('toggled', self.on_thumb_404_button_toggled)

        checkbutton11 = self.add_checkbutton(grid,
            _(
            'Ignore \'The channel is not currently live\' warnings on Twitch',
            ),
            self.app_obj.ignore_twitch_not_live_flag,
            True,                   # Can be toggled by user
            0, 11, grid_width, 1,
        )
        checkbutton11.connect('toggled', self.on_twitch_live_button_toggled)


    def setup_operations_custom_dl_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Custom' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Custom'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Custom'), inner_notebook)
        grid_width = 4

        # Custom downloads
        self.add_label(grid,
            '<u>' + _('Custom downloads') + '</u>',
            0, 0, grid_width, 1,
        )

        # (GenericConfigWin.add_treeview() doesn't support multiple columns, so
        #   we'll do everything ourselves)
        frame = Gtk.Frame()
        grid.attach(frame, 0, 1, grid_width, 1)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_headers_visible(True)

        # (The final column is deliberately empty, so that the previous column
        #   doesn't expand to fill the whole available area)
        for i, column_title in enumerate(
            [ '#', _('Name'), _('Default'), _('Classic Mode'), '']
        ):
            if i == 2 or i == 3:
                renderer_toggle = Gtk.CellRendererToggle()
                column_toggle = Gtk.TreeViewColumn(
                    column_title,
                    renderer_toggle,
                    active=i,
                )
                treeview.append_column(column_toggle)
                column_toggle.set_resizable(False)
            else:
                renderer_text = Gtk.CellRendererText()
                column_text = Gtk.TreeViewColumn(
                    column_title,
                    renderer_text,
                    text=i,
                )
                treeview.append_column(column_text)
                column_text.set_resizable(True)

        self.custom_liststore = Gtk.ListStore(int, str, bool, bool, str)
        treeview.set_model(self.custom_liststore)

        # Initialise the list
        self.setup_operations_custom_dl_tab_update_treeview()

        # Add editing buttons
        self.add_label(grid,
            'Name',
            0, 2, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            True,
            1, 2, 1, 1,
        )

        button = Gtk.Button()
        grid.attach(button, 2, 2, 1, 1)
        button.set_label(_('Add'))
        button.connect(
            'clicked',
            self.on_custom_dl_add_button_clicked,
            entry,
        )

        button2 = Gtk.Button()
        grid.attach(button2, 3, 2, 1, 1)
        button2.set_label(_('Import'))
        button2.connect(
            'clicked',
            self.on_custom_dl_import_button_clicked,
            entry,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

        button3 = Gtk.Button()
        grid2.attach(button3, 0, 0, 1, 1)
        button3.set_label(_('Edit'))
        button3.connect(
            'clicked',
            self.on_custom_dl_edit_button_clicked,
            treeview,
        )

        button4 = Gtk.Button()
        grid2.attach(button4, 1, 0, 1, 1)
        button4.set_label(_('Export'))
        button4.connect(
            'clicked',
            self.on_custom_dl_export_button_clicked,
            treeview,
        )

        button5 = Gtk.Button()
        grid2.attach(button5, 2, 0, 1, 1)
        button5.set_label(_('Clone'))
        button5.connect(
            'clicked',
            self.on_custom_dl_clone_button_clicked,
            treeview,
        )

        button6 = Gtk.Button()
        grid2.attach(button6, 3, 0, 1, 1)
        button6.set_label(_('Use in Classic Mode tab'))
        button6.connect(
            'clicked',
            self.on_custom_dl_use_classic_button_clicked,
            treeview,
        )

        button7 = Gtk.Button()
        grid2.attach(button7, 4, 0, 1, 1)
        button7.set_label(_('Delete'))
        button7.connect(
            'clicked',
            self.on_custom_dl_delete_button_clicked,
            treeview,
        )

        # (Use an empty label for spacing)
        label = self.add_label(grid2,
            '',
            5, 0, 1, 1,
        )
        label.set_hexpand(True)

        button8 = Gtk.Button()
        grid2.attach(button8, 6, 0, 1, 1)
        button8.set_label(_('Refresh list'))
        button8.connect(
            'clicked',
            self.setup_operations_custom_dl_tab_update_treeview,
        )


    def setup_operations_custom_dl_tab_update_treeview(self):

        """Can be called by anything.

        Fills or updates the treeview.

        """

        self.custom_liststore.clear()

        for uid in sorted(self.app_obj.custom_dl_reg_dict):
            self.setup_operations_custom_dl_tab_add_row(
                self.app_obj.custom_dl_reg_dict[uid],
            )


    def setup_operations_custom_dl_tab_add_row(self, custom_dl_obj):

        """Can be called by anything.

        Adds a row to the treeview.

        Args:

            custom_dl_obj (downloads.CustomDLManager): The custom download
                manager object to display on this row

        """

        row_list = []

        row_list.append(custom_dl_obj.uid)
        row_list.append(
            ttutils.tidy_up_long_string(
                custom_dl_obj.name,
                self.app_obj.main_win_obj.short_string_max_len,
            ),
        )

        if self.app_obj.general_custom_dl_obj \
        and self.app_obj.general_custom_dl_obj == custom_dl_obj:
            row_list.append(True)
        else:
            row_list.append(False)

        if self.app_obj.classic_custom_dl_obj \
        and self.app_obj.classic_custom_dl_obj == custom_dl_obj:
            row_list.append(True)
        else:
            row_list.append(False)

        # (The final column is deliberately empty, so that the previous column
        #   doesn't expand to fill the whole available area)
        row_list.append('')

        self.custom_liststore.append(row_list)


    def setup_operations_archive_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Archive' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Archive'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Archive'),
            inner_notebook,
        )

        grid_width = 4

        # Archive file preferences
        self.add_label(grid,
            '<u>' + _('Archive file preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'Allow downloader to create its own archive file (so deleted' \
            + ' videos are not re-downloaded)',
            ),
            self.app_obj.allow_ytdl_archive_flag,
            True,                   # Can be toggled by user
            0, 1, grid_width, 1,
        )
        # (Signal connect appears below)

        # (Empty label for spacing)
        label = self.add_label(grid,
            '     ',
            0, 2, 1, 1,
        )
        label.set_hexpand(False)

        radiobutton = self.add_radiobutton(grid,
            None,
            _(
            'Store the archive file in the same location as the video',
            ),
            1, 2, (grid_width - 1), 1,
        )
        # (Signal connect appears below)

        self.add_label(grid,
            '<i>' + _(
                'N.B. Archive files are never stored in system folders like' \
                + ' \'Unsorted Videos\'',
            ) + '</i>',
            1, 3, (grid_width - 1), 1,
        )

        radiobutton2 = self.add_radiobutton(grid,
            radiobutton,
            _(
            'Store the archive file in Tartube\'s data directory',
            ),
            1, 4, (grid_width - 1), 1,
        )
        if self.app_obj.allow_ytdl_archive_mode == 'top':
            radiobutton2.set_active(True)
        # (Signal connect appears below)

        radiobutton3 = self.add_radiobutton(grid,
            radiobutton2,
            _(
            'Store the archive file at this location:',
            ),
            1, 5, (grid_width - 1), 1,
        )
        if self.app_obj.allow_ytdl_archive_mode == 'custom':
            radiobutton3.set_active(True)
        # (Signal connect appears below)

        entry = self.add_entry(grid,
            None,
            True,
            1, 6, 1, 1,
        )
        if self.app_obj.allow_ytdl_archive_path != None:
            entry.set_text(self.app_obj.allow_ytdl_archive_path)
        entry.set_hexpand(True)
        entry.set_editable(False)

        button = Gtk.Button(_('Set'))
        grid.attach(button, 2, 6, 1, 1)
        # (Signal connect appears below)

        button2 = Gtk.Button(_('Reset'))
        grid.attach(button2, 3, 6, 1, 1)
        # (Signal connect appears below)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Update the archive file when videos are moved into a database' \
            + ' folder (YouTube only)',
            ),
            self.app_obj.update_ytdl_archive_on_move_flag,
            True,                   # Can be toggled by user
            0, 7, grid_width, 1,
        )
        checkbutton2.connect('toggled', self.on_archive_update_toggled)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_archive_button_toggled,
            checkbutton2,
            radiobutton,
            radiobutton2,
            radiobutton3,
            button,
            button2,
        )
        radiobutton.connect(
            'toggled',
            self.on_archive_radiobutton_toggled,
            radiobutton,
            radiobutton2,
            radiobutton3,
            entry,
            button,
            button2,
        )
        radiobutton2.connect(
            'toggled',
            self.on_archive_radiobutton_toggled,
            radiobutton,
            radiobutton2,
            radiobutton3,
            entry,
            button,
            button2,
        )
        radiobutton3.connect(
            'toggled',
            self.on_archive_radiobutton_toggled,
            radiobutton,
            radiobutton2,
            radiobutton3,
            entry,
            button,
            button2,
        )
        button.connect('clicked', self.on_set_archive_button_clicked, entry)
        button2.connect('clicked', self.on_reset_archive_button_clicked, entry)

        if not self.app_obj.allow_ytdl_archive_flag:
            radiobutton.set_sensitive(False)
            radiobutton2.set_sensitive(False)
            radiobutton3.set_sensitive(False)
        if not self.app_obj.allow_ytdl_archive_flag \
        or self.app_obj.allow_ytdl_archive_mode != 'custom':
            button.set_sensitive(False)
            button2.set_sensitive(False)

        # Classic Mode tab preferences
        self.add_label(grid,
            '<u>' + _('Classic Mode tab preferences') + '</u>',
            0, 8, grid_width, 1,
        )

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Create an archive file when downloading from the Classic Mode' \
            + ' tab',
            ),
            self.app_obj.classic_ytdl_archive_flag,
            True,                   # Can be toggled by user
            0, 9, grid_width, 1,
        )
        checkbutton2.connect('toggled', self.on_archive_classic_button_toggled)

        self.add_label(grid,
            '<i>' + _(
                'This setting should only be enabled when downloading' \
                + ' channels and playlists',
            ) + '</i>',
            0, 10, grid_width, 1,
        )


    def setup_operations_livestreams_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Streams' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Livestreams'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('Li_vestreams'),
            inner_notebook,
        )
        grid_width = 2

        # Livestream preferences (compatible websites only)
        self.add_label(grid,
            '<u>' + _(
                'Livestream preferences (compatible websites only)',
            ) + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Do not check/download any livestream [yt-dlp only]'),
            self.app_obj.block_livestreams_flag,
            True,                   # Can be toggled by user
            0, 1, 1, 1,
        )
        checkbutton.connect(
            'toggled',
            self.on_block_livestreams_button_toggled,
        )

        checkbutton2 = self.add_checkbutton(grid,
            _('Detect livestreams announced within this many days'),
            self.app_obj.enable_livestreams_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        # (Signal connect appears below)
        spinbutton = self.add_spinbutton(grid,
            0, None, 1, self.app_obj.livestream_max_days,
            1, 2, 1, 1,
        )
        if not self.app_obj.enable_livestreams_flag:
            spinbutton.set_sensitive(False)
        # (Signal connect appears below)

        checkbutton3 = self.add_checkbutton(grid,
            _('How often to check the status of livestreams (in minutes)'),
            self.app_obj.scheduled_livestream_flag,
            True,                   # Can be toggled by user
            0, 3, 1, 1,
        )
        if not self.app_obj.enable_livestreams_flag:
            checkbutton3.set_sensitive(False)
        # (Signal connect appears below)

        spinbutton2 = self.add_spinbutton(grid,
            1, None, 1, self.app_obj.scheduled_livestream_wait_mins,
            1, 3, 1, 1,
        )
        if not self.app_obj.enable_livestreams_flag \
        or not self.app_obj.scheduled_livestream_flag:
            spinbutton2.set_sensitive(False)
        # (Signal connect appears below)

        checkbutton4 = self.add_checkbutton(grid,
            _('Check more frequently when a livestream is due to start'),
            self.app_obj.scheduled_livestream_extra_flag,
            True,                   # Can be toggled by user
            0, 4, grid_width, 1,
        )
        if not self.app_obj.enable_livestreams_flag \
        or not self.app_obj.scheduled_livestream_flag:
            checkbutton4.set_sensitive(False)
        checkbutton4.connect(
            'toggled',
            self.on_extra_livestreams_button_toggled,
        )

        # (Signal connects from above)
        checkbutton2.connect(
            'toggled',
            self.on_enable_livestreams_button_toggled,
            checkbutton3,
            checkbutton4,
            spinbutton,
            spinbutton2,
        )

        spinbutton.connect(
            'value-changed',
            self.on_livestream_max_days_spinbutton_changed,
        )

        checkbutton3.connect(
            'toggled',
            self.on_scheduled_livestreams_button_toggled,
            checkbutton4,
            spinbutton2,
        )

        spinbutton2.connect(
            'value-changed',
            self.on_scheduled_livestreams_spinbutton_changed,
        )

        # Broadcast preferences (compatible websites only)
        self.add_label(grid,
            '<u>' + _(
                'Broadcasting livestream preferences (compatible websites' \
                + ' only)',
            ) + '</u>',
            0, 5, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'These settings apply when downloading videos individually,' \
                + ' for example with a custom download',
            ) + '</i>',
            0, 6, grid_width, 1,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 7, grid_width, 1)

        label = self.add_label(grid2,
            _('Download using:'),
            0, 0, 1, 1,
        )
        label.set_hexpand(False)

        self.livestream_radiobutton = self.add_radiobutton(grid2,
            None,
            '',
            1, 0, 1, 1,
        )
        self.livestream_radiobutton.set_hexpand(False)
        # (Signal connect appears below)

        self.livestream_radiobutton2 = self.add_radiobutton(grid2,
            self.livestream_radiobutton,
            _('.m3u manifest'),
            2, 0, 1, 1,
        )
        self.livestream_radiobutton2.set_hexpand(False)
        if self.app_obj.livestream_dl_mode == 'default_m3u':
            self.livestream_radiobutton2.set_active(True)
        # (Signal connect appears below)

        self.livestream_radiobutton3 = self.add_radiobutton(grid2,
            self.livestream_radiobutton2,
            'streamlink',
            3, 0, 1, 1,
        )
        self.livestream_radiobutton3.set_hexpand(False)
        if self.app_obj.livestream_dl_mode == 'streamlink':
            self.livestream_radiobutton3.set_active(True)
        # (Signal connect appears below)

        # (Set labels for those widgets, and replace them every time the
        #   downloader changes)
        self.setup_operations_livestreams_tab_update()

        # (Signal connects from above)
        self.livestream_radiobutton.connect(
            'toggled',
            self.on_livestream_mode_button_toggled,
            'default',
        )
        self.livestream_radiobutton2.connect(
            'toggled',
            self.on_livestream_mode_button_toggled,
            'default_m3u',
        )
        self.livestream_radiobutton3.connect(
            'toggled',
            self.on_livestream_mode_button_toggled,
            'streamlink',
        )

        if not self.app_obj.simple_prefs_flag:

            # (To avoid messing up the neat format of the rows above, add a
            #   secondary grid, and put the next set of widgets inside it)
            grid3 = self.add_secondary_grid(grid, 0, 8, grid_width, 1)

            self.livestream_radiobutton4 = self.add_radiobutton(grid3,
                None,
                _('Replace a partially-downloaded livestream'),
                1, 0, 1, 1,
            )
            self.livestream_radiobutton4.set_hexpand(False)

            self.livestream_radiobutton5 = self.add_radiobutton(grid3,
                self.livestream_radiobutton4,
                _('Resume a partially-downloaded livestream'),
                2, 0, 1, 1,
            )
            self.livestream_radiobutton5.set_hexpand(False)
            if not self.app_obj.livestream_replace_flag:
                self.livestream_radiobutton5.set_active(True)
            if self.app_obj.livestream_dl_mode == 'streamlink':
                self.livestream_radiobutton5.set_sensitive(False)
            # (Signal connect appears below)

            # (Signal connects from above)
            self.livestream_radiobutton4.connect(
                'toggled',
                self.on_livestream_replace_button_toggled,
            )

            # (More widgets)
            checkbutton5 = self.add_checkbutton(grid,
                _(
                'Bypass usual limits on simultaneous downloads, so that' \
                + ' all livestreams can be downloaded',
                ),
                self.app_obj.num_worker_bypass_flag,
                True,                   # Can be toggled by user
                0, 9, grid_width, 1,
            )
            checkbutton5.connect(
                'toggled',
                self.on_worker_bypass_button_toggled,
            )

            self.add_label(grid,
                _('Timeout after this many minutes of inactivity'),
                0, 10, 1, 1,
            )

            spinbutton3 = self.add_spinbutton(grid,
                1, None, 0.2,
                self.app_obj.livestream_dl_timeout,
                1, 10, 1, 1,
            )
            spinbutton3.connect(
                'value-changed',
                self.on_livestream_timeout_spinbutton_changed,
            )

            checkbutton6 = self.add_checkbutton(grid,
                _(
                'When the livestream download is stopped manually, mark the' \
                + ' video as downloaded',
                ),
                self.app_obj.livestream_stop_is_final_flag,
                True,                   # Can be toggled by user
                0, 11, grid_width, 1,
            )
            checkbutton6.connect(
                'toggled',
                self.on_livestream_stop_button_toggled,
            )

            checkbutton7 = self.add_checkbutton(grid,
                _(
                'Check a video before the livestream download (ensures' \
                + ' metadata is downloaded)',
                ),
                self.app_obj.livestream_force_check_flag,
                True,                   # Can be toggled by user
                0, 12, grid_width, 1,
            )
            checkbutton7.connect(
                'toggled',
                self.on_livestream_force_check_button_toggled,
            )

            self.add_label(grid,
                '   <i>' + _(
                    'N.B. This setting is ignored in the Classic Mode tab',
                ) + '</i>',
                0, 13, grid_width, 1,
            )


    def setup_operations_livestreams_tab_update(self):

        """Called initially by self.setup_operations_livestreams_tab, and
        subsequently by self.update_ytdl_combos().

        Updates labels in that tab to show the current downloader.
        """

        downloader = self.app_obj.get_downloader()

        self.livestream_radiobutton.set_label(
            downloader + ' (' + _('not recommended') + ')',
        )


    def setup_operations_actions_tab(self, inner_notebook):

        """Called by self.setup_scheduling_tab().

        Sets up the 'Actions' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Actions'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('Ac_tions'),
            inner_notebook,
        )
        grid_width = 3

        # Livestream actions (can be toggled for individual videos)
        self.add_label(grid,
            '<u>' + _(
                'Livestream actions (can be toggled for individual videos)',
            ) + '</u>',
            0, 0, grid_width, 1,
        )

        # Currently disabled on MS Windows
        if os.name == 'nt':
            string = ' ' + _('(currently disabled on MS Windows)')
        else:
            string = ''

        checkbutton = self.add_checkbutton(grid,
            _('When a livestream starts, show a desktop notification') \
            + string,
            self.app_obj.livestream_auto_notify_flag,
            True,                   # Can be toggled by user
            0, 1, grid_width, 1,
        )
        checkbutton.connect(
            'toggled',
            self.on_livestream_auto_notify_button_toggled,
        )
        if os.name == 'nt':
            checkbutton.set_sensitive(False)

        checkbutton2 = self.add_checkbutton(grid,
            _('When a livestream starts, sound an alarm'),
            self.app_obj.livestream_auto_alarm_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        if not mainapp.HAVE_PLAYSOUND_FLAG \
        or self.app_obj.sound_dir is None \
        or not self.app_obj.sound_list:
            checkbutton2.set_sensitive(False)
        checkbutton2.connect(
            'toggled',
            self.on_livestream_auto_alarm_button_toggled,
        )

        combo = self.add_combo(grid,
            self.app_obj.sound_list,
            self.app_obj.sound_custom,
            1, 2, 1, 1,
        )
        combo.connect('changed', self.on_sound_custom_changed)
        if not mainapp.HAVE_PLAYSOUND_FLAG \
        or self.app_obj.sound_dir is None \
        or not self.app_obj.sound_list:
            combo.set_visible(False)

        button = Gtk.Button(_('Test'))
        grid.attach(button, 2, 2, 1, 1)
        button.set_tooltip_text(_('Plays the selected sound effect'))
        button.connect('clicked', self.on_test_sound_clicked, combo)
        if not mainapp.HAVE_PLAYSOUND_FLAG \
        or self.app_obj.sound_dir is None \
        or not self.app_obj.sound_list:
            button.set_sensitive(False)

        checkbutton3 = self.add_checkbutton(grid,
            _(
            'When a livestream starts, open it in the system\'s web browser',
            ),
            self.app_obj.livestream_auto_open_flag,
            True,                   # Can be toggled by user
            0, 3, grid_width, 1,
        )
        checkbutton3.connect(
            'toggled',
            self.on_livestream_auto_open_button_toggled,
        )

        checkbutton4 = self.add_checkbutton(grid,
            _('When a livestream starts, begin downloading it immediately'),
            self.app_obj.livestream_auto_dl_start_flag,
            True,                   # Can be toggled by user
            0, 4, grid_width, 1,
        )
        checkbutton4.connect(
            'toggled',
            self.on_livestream_auto_dl_start_button_toggled,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _(
            'When a livestream stops, download it (overwriting any earlier' \
            + ' file)',
            ),
            self.app_obj.livestream_auto_dl_stop_flag,
            True,                   # Can be toggled by user
            0, 5, grid_width, 1,
        )
        checkbutton5.connect(
            'toggled',
            self.on_livestream_auto_dl_stop_button_toggled,
        )

        if not self.app_obj.simple_prefs_flag:

            # Desktop notification preferences
            self.add_label(grid,
                '<u>' + _('Desktop notification preferences') + '</u>',
                0, 6, 1, 1,
            )

            radiobutton = self.add_radiobutton(grid,
                None,
                _('Show a dialogue window at the end of an operation'),
                0, 7, 1, 1,
            )
            # (Signal connect appears below)

            if platform.system() != 'Windows' \
            and platform.system() != 'Darwin':
                text = 'Show a desktop notification at the end of an operation'
            else:
                text = 'Show a desktop notification (Linux/*BSD only)'

            radiobutton2 = self.add_radiobutton(grid,
                radiobutton,
                _(text),
                0, 8, 1, 1,
            )
            if self.app_obj.operation_dialogue_mode == 'desktop':
                radiobutton2.set_active(True)
            if platform.system() == 'Windows' or platform.system() == 'Darwin':
                radiobutton2.set_sensitive(False)
            # (Signal connect appears below)

            radiobutton3 = self.add_radiobutton(grid,
                radiobutton2,
                _('Don\'t notify the user at the end of an operation'),
                0, 9, 1, 1,
            )
            if self.app_obj.operation_dialogue_mode == 'default':
                radiobutton3.set_active(True)
            # (Signal connect appears below)

            # (Signal connects from above)
            radiobutton.connect(
                'toggled',
                self.on_dialogue_button_toggled,
                'dialogue',
            )
            radiobutton2.connect(
                'toggled',
                self.on_dialogue_button_toggled,
                'desktop',
            )
            radiobutton3.connect(
                'toggled',
                self.on_dialogue_button_toggled,
                'default',
            )


    def setup_operations_clips_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Clips' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Clips'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('Cli_ps'),
            inner_notebook,
        )
        grid_width = 2

        # Timestamps
        self.add_label(grid,
            '<u>' + _('Timestamps') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'When a video is checked/downloaded, automatically extract' \
            + ' timestamps from its metadata file',
            ),
            self.app_obj.video_timestamps_extract_json_flag,
            True,                   # Can be toggled by user
            0, 1, grid_width, 1,
        )
        checkbutton.connect('toggled', self.on_extract_json_flag_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'When a video is checked/downloaded, automatically extract' \
            + ' timestamps from its description',
            ),
            self.app_obj.video_timestamps_extract_descrip_flag,
            True,                   # Can be toggled by user
            0, 2, grid_width, 1,
        )
        checkbutton2.connect('toggled', self.on_extract_descrip_flag_toggled)

        if not self.app_obj.simple_prefs_flag:

            checkbutton3 = self.add_checkbutton(grid,
                _('If timestamps have already been extracted, replace them'),
                self.app_obj.video_timestamps_replace_flag,
                True,                   # Can be toggled by user
                0, 3, grid_width, 1,
            )
            checkbutton3.connect(
                'toggled',
                self.on_replace_stamps_flag_toggled,
            )

            checkbutton4 = self.add_checkbutton(grid,
                _(
                'If no timestamps have been extracted, try again before' \
                + ' splitting a video',
                ),
                self.app_obj.video_timestamps_re_extract_flag,
                True,                   # Can be toggled by user
                0, 4, grid_width, 1,
            )
            checkbutton4.connect(
                'toggled',
                self.on_reextract_stamps_flag_toggled,
            )

        # Video clips (requires FFmpeg)
        self.add_label(grid,
            '<u>' + _('Video clips (requires FFmpeg or yt-dlp)') + '</u>',
            0, 5, grid_width, 1,
        )

        # (N.B. This setting can be more conveniently changed in
        #   mainwin.PrepareClipDialogue)
        if not self.app_obj.simple_prefs_flag:

            radiobutton = self.add_radiobutton(grid,
                None,
                _('Download video clips using FFmpeg'),
                0, 6, 1, 1,
            )
            # (Signal connect appears below)

            radiobutton2 = self.add_radiobutton(grid,
                radiobutton,
                _('Download video clips using yt-dlp'),
                1, 6, 1, 1,
            )
            if self.app_obj.video_timestamps_dl_mode == 'downloader':
                radiobutton2.set_active(True)

            # (Signal connects from above)
            radiobutton.connect(
                'toggled',
                self.on_clips_dl_mode_button_toggled,
            )

        self.add_label(grid,
            _('Format of video clip filenames'),
            0, 7, 1, 1,
        )

        combo_list = [
            _('Number'), 'num',
            _('Clip Title'), 'clip',
            _('Number + Clip Title'), 'num_clip',
            _('Clip Title + Number'), 'clip_num',
            _('Original Title'), 'orig',
            _('Original Title + Number'), 'orig_num',
            _('Original Title + Clip Title'), 'orig_clip',
            _('Original Title + Number + Clip Title'), 'orig_num_clip',
            _('Original Title + Clip Title + Number'), 'orig_clip_num',
        ]

        store = Gtk.ListStore(str, str)
        count = -1
        line_num = 0
        while combo_list:

            count += 1
            descrip = combo_list.pop(0)
            mode = combo_list.pop(0)
            if mode == self.app_obj.split_video_name_mode:
                line_num = count

            store.append([ descrip, mode])

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, 1, 7, 1, 1)
        combo.set_hexpand(True)

        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 0)
        combo.set_active(line_num)
        combo.connect('changed', self.on_split_mode_combo_changed)

        self.add_label(grid,
            _('Generic title for video clips'),
            0, 8, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            True,
            1, 8, 1, 1,
        )
        entry.set_text(self.app_obj.split_video_custom_title)
        entry.connect(
            'changed',
            self.on_custom_title_changed,
        )

        radiobutton3 = self.add_radiobutton(grid,
            None,
            _('Move clips to the Video Clips folder'),
            0, 9, 1, 1,
        )
        # (Signal connect appears below)

        radiobutton4 = self.add_radiobutton(grid,
            radiobutton3,
            _('Keep clips with their original video'),
            1, 9, 1, 1,
        )
        if not self.app_obj.split_video_clips_dir_flag:
            radiobutton4.set_active(True)

        # (Signal connects from above)
        radiobutton3.connect(
            'toggled',
            self.on_clips_dir_button_toggled,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _('...but place new files inside a sub-directory'),
            self.app_obj.split_video_subdir_flag,
            True,                   # Can be toggled by user
            0, 10, grid_width, 1,
        )
        checkbutton5.connect(
            'toggled',
            self.on_split_subdir_flag_toggled,
        )

        checkbutton6 = self.add_checkbutton(grid,
            _('Add new files to Tartube\'s database'),
            self.app_obj.split_video_add_db_flag,
            True,                   # Can be toggled by user
            0, 11, 1, 1,
        )
        checkbutton6.connect(
            'toggled',
            self.on_add_db_flag_toggled,
        )

        checkbutton7 = self.add_checkbutton(grid,
            _('Use the original video\'s thumbnail'),
            self.app_obj.split_video_copy_thumb_flag,
            True,                   # Can be toggled by user
            1, 11, 1, 1,
        )
        checkbutton7.connect('toggled', self.on_copy_thumb_flag_toggled)

        if not self.app_obj.simple_prefs_flag:

            checkbutton8 = self.add_checkbutton(grid,
                _(
                    'Force keyframes at cuts (slower, but fewer video' \
                    + ' artefacts before and after each cut)',
                ),
                self.app_obj.split_video_force_keyframe_flag,
                True,                   # Can be toggled by user
                0, 12, grid_width, 1,
            )
            checkbutton8.connect(
                'toggled',
                self.on_split_keyframe_flag_toggled,
            )

        if os.name == 'nt':
            msg = _('After splitting a video, open the destination folder')
        else:
            msg = _('After splitting a video, open the destination directory')

        checkbutton9 = self.add_checkbutton(grid,
            msg,
            self.app_obj.split_video_auto_open_flag,
            True,                   # Can be toggled by user
            0, 13, grid_width, 1,
        )
        checkbutton9.connect('toggled', self.on_auto_open_flag_toggled)

        checkbutton10 = self.add_checkbutton(grid,
            _(
            'After splitting a video, delete the original (ignored for' \
            + ' videos in channels/playlists)',
            ),
            self.app_obj.split_video_auto_delete_flag,
            True,                   # Can be toggled by user
            0, 14, grid_width, 1,
        )
        checkbutton10.connect('toggled', self.on_auto_delete_flag_toggled)


    def setup_operations_slices_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Slices' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Slices'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('Slic_es'),
            inner_notebook,
        )
        grid_width = 1

        # Video slices (requires FFmpeg)
        self.add_label(grid,
            '<u>' + _('Video slices (requires FFmpeg)') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'While checking/downloading videos, check each video against' \
            + ' the SponsorBlock server',
            ),
            self.app_obj.sblock_fetch_flag,
            True,               # Can be toggled by user
            0, 1, grid_width, 1,
        )
        checkbutton.connect('toggled', self.on_sblock_fetch_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'When contacting the server, obfuscate each video\'s ID' \
            + ' (recommended)',
            ),
            self.app_obj.sblock_obfuscate_flag,
            True,               # Can be toggled by user
            0, 2, grid_width, 1,
        )
        checkbutton2.connect(
            'toggled',
            self.on_sblock_obfuscate_button_toggled,
        )

        if not self.app_obj.simple_prefs_flag:

            checkbutton3 = self.add_checkbutton(grid,
                _(
                'If slices have already been extracted, replace the old list',
                ),
                self.app_obj.sblock_replace_flag,
                True,               # Can be toggled by user
                0, 3, grid_width, 1,
            )
            checkbutton3.connect(
                'toggled',
                self.on_sblock_replace_button_toggled,
            )

            checkbutton4 = self.add_checkbutton(grid,
                _(
                'If slices have been extracted, contact the server again' \
                + ' before removing more slices from the video',
                ),
                self.app_obj.sblock_re_extract_flag,
                True,               # Can be toggled by user
                0, 4, grid_width, 1,
            )
            checkbutton4.connect(
                'toggled',
                self.on_sblock_re_extract_button_toggled,
            )

            checkbutton5 = self.add_checkbutton(grid,
                _(
                'Force keyframes at cuts (slower, but fewer video artefacts' \
                + ' before and after each cut)',
                ),
                self.app_obj.slice_video_force_keyframe_flag,
                True,               # Can be toggled by user
                0, 5, grid_width, 1,
            )
            checkbutton5.connect(
                'toggled',
                self.on_slice_keyframe_flag_toggled,
            )

            checkbutton6 = self.add_checkbutton(grid,
                _(
                'After removing slices from a video, reset all timestamp and' \
                + ' slice data (recommended)',
                ),
                self.app_obj.slice_video_cleanup_flag,
                True,               # Can be toggled by user
                0, 6, grid_width, 1,
            )
            checkbutton6.connect(
                'toggled',
                self.on_slice_cleanup_button_toggled,
            )


    def setup_operations_mirrors_tab(self, inner_notebook):

        """Called by self.setup_scheduling_tab().

        Sets up the 'Mirrors' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Mirrors'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Mirrors'),
            inner_notebook,
        )
        grid_width = 2

        # Invidious mirror
        self.add_label(grid,
            '<u>' + _('Invidious mirror') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            _(
                'To find an updated list of Invidious mirrors, use any' \
                + ' search engine!',
            ),
            0, 1, grid_width, 1,
        )

        entry = self.add_entry(grid,
            self.app_obj.custom_invidious_mirror,
            True,
            0, 2, 1, 1,
        )
        entry.connect('changed', self.on_invidious_mirror_changed)

        button = Gtk.Button(_('Reset'))
        grid.attach(button, 1, 2, 1, 1)
        button.set_tooltip_text(_('Use the default Invidious mirror'))
        button.set_hexpand(False)
        button.connect('clicked', self.on_reset_invidious_clicked, entry)

        msg = _('Type the exact text that replaces www.youtube.com e.g.')
        msg = re.sub('www.youtube.com', '   <b>www.youtube.com</b>   ', msg)

        self.add_label(grid,
            '<i>' + msg + '   <b>' + self.app_obj.default_invidious_mirror \
            + '</b></i>',
            0, 3, grid_width, 1,
        )

        # SponsorBlock API mirror
        self.add_label(grid,
            '<u>' + _('SponsorBlock API mirror') + '</u>',
            0, 4, grid_width, 1,
        )

        entry2 = self.add_entry(grid,
            self.app_obj.custom_sblock_mirror,
            True,
            0, 5, 1, 1,
        )
        entry2.connect('changed', self.on_sblock_mirror_changed)

        button2 = Gtk.Button(_('Reset'))
        grid.attach(button2, 1, 5, 1, 1)
        button2.set_tooltip_text(_('Use the default SponsorBlock URL'))
        button2.connect('clicked', self.on_reset_sblock_clicked, entry2)


    def setup_operations_proxies_tab(self, inner_notebook):

        """Called by self.setup_scheduling_tab().

        Sets up the 'Proxies' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Proxies'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('P_roxies'),
            inner_notebook,
        )

        # Proxies
        self.add_label(grid,
            '<u>' + _('Proxies') + '</u>',
            0, 0, 1, 1,
        )

        self.add_label(grid,
            '<i>' \
            + _(
            'During a download operation, Tartube will cycle betwween the' \
            + ' proxies in this list',
            ) + '</i>',
            0, 1, 1, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            self.app_obj.dl_proxy_list,
            0, 2, 1, 1
        )
        textbuffer.connect('changed', self.on_proxy_textview_changed)


    def setup_operations_prefs_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Preferences' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Preferences'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('Pre_ferences'),
            inner_notebook,
        )
        grid_width = 3

        # URL flexibility preferences
        self.add_label(grid,
            '<u>' + _('URL flexibility preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        radiobutton = self.add_radiobutton(grid,
            None,
            _(
            'If a video\'s URL represents a channel/playlist, not a video,' \
            + ' don\'t download it',
            ),
            0, 1, grid_width, 1,
        )
        # (Signal connect appears below)

        radiobutton2 = self.add_radiobutton(grid,
            radiobutton,
            _('...or, download multiple videos into the containing folder'),
            0, 2, grid_width, 1,
        )
        if self.app_obj.operation_convert_mode == 'multi':
            radiobutton2.set_active(True)
        # (Signal connect appears below)

        radiobutton3 = self.add_radiobutton(grid,
            radiobutton2,
            _(
            '...or, create a new channel, and download the videos into that',
            ),
            0, 3, grid_width, 1,
        )
        if self.app_obj.operation_convert_mode == 'channel':
            radiobutton3.set_active(True)
        # (Signal connect appears below)

        radiobutton4 = self.add_radiobutton(grid,
            radiobutton3,
            _(
            '...or, create a new playlist, and download the videos into that',
            ),
            0, 4, grid_width, 1,
        )
        if self.app_obj.operation_convert_mode == 'playlist':
            radiobutton4.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        radiobutton.connect(
            'toggled',
            self.on_convert_from_button_toggled,
            'disable',
        )
        radiobutton2.connect(
            'toggled',
            self.on_convert_from_button_toggled,
            'multi',
        )
        radiobutton3.connect(
            'toggled',
            self.on_convert_from_button_toggled,
            'channel',
        )
        radiobutton4.connect(
            'toggled',
            self.on_convert_from_button_toggled,
            'playlist',
        )

        # Missing video preferences
        self.add_label(grid,
            '<u>' + _('Missing video preferences') + '</u>',
            0, 5, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'Add videos which have been removed from a channel/playlist to' \
            + ' the Missing Videos folder',
            ),
            self.app_obj.track_missing_videos_flag,
            True,                   # Can be toggled by user
            0, 6, grid_width, 1,
        )
        # (Signal connect appears below)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Only add videos that were uploaded within this many days',
            ),
            self.app_obj.track_missing_time_flag,
            True,                   # Can be toggled by user
            0, 7, 1, 1,
        )
        if not self.app_obj.track_missing_videos_flag:
            checkbutton2.set_sensitive(False)
        # (Signal connect appears below)

        spinbutton = self.add_spinbutton(grid,
            0,
            365,
            1,                  # Step
            self.app_obj.track_missing_time_days,
            1, 7, 2, 1,
        )
        spinbutton.set_hexpand(True)
        if not self.app_obj.track_missing_videos_flag \
        or not self.app_obj.track_missing_time_flag:
            spinbutton.set_sensitive(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_missing_videos_button_toggled,
            checkbutton2,
            spinbutton,
        )
        checkbutton2.connect(
            'toggled',
            self.on_missing_time_button_toggled,
            spinbutton,
        )
        spinbutton.connect(
            'value-changed',
            self.on_missing_time_spinbutton_changed,
        )


    def setup_operations_missing_tab(self, inner_notebook):

        """Called by self.setup_operations_tab().

        Sets up the 'Missing' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Operations > Missing'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('Missi_ng'),
            inner_notebook,
        )
        grid_width = 3

        # Missing video preferences
        self.add_label(grid,
            '<u>' + _('Missing video preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'Add videos which have been removed from a channel/playlist to' \
            + ' the Missing Videos folder',
            ),
            self.app_obj.track_missing_videos_flag,
            True,                   # Can be toggled by user
            0, 1, grid_width, 1,
        )
        # (Signal connect appears below)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Only add videos that were uploaded within this many days',
            ),
            self.app_obj.track_missing_time_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        if not self.app_obj.track_missing_videos_flag:
            checkbutton2.set_sensitive(False)
        # (Signal connect appears below)

        spinbutton = self.add_spinbutton(grid,
            0,
            365,
            1,                  # Step
            self.app_obj.track_missing_time_days,
            1, 2, 2, 1,
        )
        spinbutton.set_hexpand(True)
        if not self.app_obj.track_missing_videos_flag \
        or not self.app_obj.track_missing_time_flag:
            spinbutton.set_sensitive(False)
        # (Signal connect appears below)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_missing_videos_button_toggled,
            checkbutton2,
            spinbutton,
        )
        checkbutton2.connect(
            'toggled',
            self.on_missing_time_button_toggled,
            spinbutton,
        )
        spinbutton.connect(
            'value-changed',
            self.on_missing_time_spinbutton_changed,
        )


    def setup_downloader_forks_tab(self, inner_notebook):

        """Called by self.setup_downloader_tab().

        Sets up the 'Forks' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Downloaders > Forks'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Forks'),
            inner_notebook,
        )

        # Forks of youtube-dl
        self.add_label(grid,
            '<u>' + _('Forks of youtube-dl') + '</u>',
            0, 0, 1, 1,
        )

        # yt-dlp. Use an event box so the downloader can be selected by
        #   clicking anywhere in the frame
        event_box = Gtk.EventBox()
        grid.attach(event_box, 0, 1, 1, 1)
        # (Signal connect appears below)

        frame = Gtk.Frame()
        event_box.add(frame)
        frame.set_border_width(self.spacing_size)

        grid2 = Gtk.Grid()
        frame.add(grid2)
        grid2.set_border_width(self.spacing_size)

        self.add_label(grid2,
            ttutils.tidy_up_long_string(
                '<b>yt-dlp</b>: <i>' \
                + self.app_obj.ytdl_fork_descrip_dict['yt-dlp'] \
                + '</i>',
            ),
            0, 0, 2, 1,
        )

        self.forks_radiobutton = self.add_radiobutton(grid2,
            None,
            '   ' + _('Use yt-dlp'),
            0, 1, 1, 1,
        )
        # (Signal connect appears below)

        checkbutton = self.add_checkbutton(grid2,
            _('Install without dependencies') + '\n' \
            + _('(recommended on MS Windows)'),
            self.app_obj.ytdl_fork_no_dependency_flag,
            True,                   # Can be toggled by user
            1, 1, 1, 1,
        )
        # (Signal connect appears below)

        checkbutton2 = self.add_checkbutton(grid2,
            _('Install nightly build') + '\n' \
            + _('(experimental, PIP installs only)'),
            self.app_obj.ytdl_fork_nightly_flag,
            True,                   # Can be toggled by user
            2, 1, 1, 1,
        )
        # (Signal connect appears below)

        # youtube-dl
        event_box2 = Gtk.EventBox()
        grid.attach(event_box2, 0, 2, 1, 1)
        # (Signal connect appears below)

        frame2 = Gtk.Frame()
        event_box2.add(frame2)
        frame2.set_border_width(self.spacing_size)

        grid3 = Gtk.Grid()
        frame2.add(grid3)
        grid3.set_border_width(self.spacing_size)

        self.add_label(grid3,
            ttutils.tidy_up_long_string(
                '<b>youtube-dl</b>: <i>' \
                + self.app_obj.ytdl_fork_descrip_dict['youtube-dl'] \
                + '</i>',
            ),
            0, 0, 1, 1,
        )

        self.forks_radiobutton2 = self.add_radiobutton(grid3,
            self.forks_radiobutton,
            '   ' + _('Use youtube-dl'),
            0, 1, 1, 1,
        )
        # (Signal connect appears below)

        # Any other fork
        event_box3 = Gtk.EventBox()
        grid.attach(event_box3, 0, 3, 1, 1)
        # (Signal connect appears below)

        frame3 = Gtk.Frame()
        event_box3.add(frame3)
        frame3.set_border_width(self.spacing_size)

        grid4 = Gtk.Grid()
        frame3.add(grid4)
        grid4.set_border_width(self.spacing_size)
        grid4.set_row_spacing(self.spacing_size)

        self.add_label(grid4,
            '<i>' + ttutils.tidy_up_long_string(
                '<b>' + _('Other forks') + ':</b> ' \
                + self.app_obj.ytdl_fork_descrip_dict['custom'],
            ) + '</i>',
            0, 0, 2, 1,
        )

        self.forks_radiobutton3 = self.add_radiobutton(grid4,
            self.forks_radiobutton2,
            '   ' + _('Use this fork (e.g. youtube-dlc):'),
            0, 1, 1, 1,
        )
        # (Signal connect appears below)
        self.forks_radiobutton3.set_hexpand(False)

        self.forks_entry = self.add_entry(grid4,
            None,
            True,
            1, 1, 1, 1,
        )
        self.forks_entry.set_sensitive(True)
        self.forks_entry.set_max_length(32)
        self.forks_entry.set_hexpand(False)
        self.forks_entry.set_icon_from_stock(
            Gtk.EntryIconPosition.PRIMARY,
            'gtk-yes',
        )
        # (Signal connect appears below)

        # Set widgets' initial states
        if self.app_obj.ytdl_fork is None \
        or self.app_obj.ytdl_fork == 'youtube-dl':
            self.forks_radiobutton2.set_active(True)
            checkbutton.set_sensitive(False)
            checkbutton2.set_sensitive(False)
            self.forks_entry.set_sensitive(False)
        elif self.app_obj.ytdl_fork == 'yt-dlp':
            self.forks_radiobutton.set_active(True)
            checkbutton.set_sensitive(True)
            checkbutton2.set_sensitive(True)
            self.forks_entry.set_sensitive(False)
        else:
            self.forks_radiobutton3.set_active(True)
            if self.app_obj.ytdl_fork is not None:
                self.forks_entry.set_text(self.app_obj.ytdl_fork)
            else:
                self.forks_entry.set_text('')
            checkbutton.set_sensitive(False)
            checkbutton2.set_sensitive(False)
            self.forks_entry.set_sensitive(True)

        # (Signal connects from above)
        event_box.connect(
            'button-press-event',
            self.on_ytdl_fork_frame_clicked,
            self.forks_radiobutton,
        )
        event_box2.connect(
            'button-press-event',
            self.on_ytdl_fork_frame_clicked,
            self.forks_radiobutton2,
        )
        event_box3.connect(
            'button-press-event',
            self.on_ytdl_fork_frame_clicked,
            self.forks_radiobutton3,
        )
        self.forks_radiobutton.connect(
            'toggled',
            self.on_ytdl_fork_button_toggled,
            checkbutton,
            checkbutton2,
            'yt-dlp',
        )
        checkbutton.connect('toggled', self.on_ytdlp_install_button_toggled)
        checkbutton2.connect('toggled', self.on_ytdlp_nightly_button_toggled)
        self.forks_radiobutton2.connect(
            'toggled',
            self.on_ytdl_fork_button_toggled,
            checkbutton,
            checkbutton2,
            'youtube-dl',
        )
        self.forks_radiobutton3.connect(
            'toggled',
            self.on_ytdl_fork_button_toggled,
            checkbutton,
            checkbutton2,
        )
        self.forks_entry.connect('changed', self.on_ytdl_fork_changed)

        # Bottom section (always sensitised)
        checkbutton3 = self.add_checkbutton(grid,
            _(
                'When using other downloaders, filter out yt-dlp download' \
                + ' options',
            ),
            self.app_obj.ytdlp_filter_options_flag,
            True,                   # Can be toggled by user
            0, 4, 1, 1,
        )
        checkbutton3.connect('toggled', self.on_filter_options_button_toggled)


    def setup_downloader_paths_tab(self, inner_notebook):

        """Called by self.setup_downloader_tab().

        Sets up the 'File Paths' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Downloaders > File paths'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('File _paths'),
            inner_notebook,
        )
        grid_width = 3

        # Downloader file paths
        self.add_label(grid,
            '<u>' + _('Downloader file paths') + '</u>',
            0, 0, grid_width, 1,
        )

        # youtube-dl file paths
        self.add_label(grid,
            _('Path to the executable'),
            0, 1, 1, 1,
        )

        combo_list = [
            [
                _('Use default path') + ' (' + self.app_obj.ytdl_path_default \
                + ')',
                self.app_obj.ytdl_path_default,
            ],
        ]

        if os.name != 'nt':

            combo_list.append(
                [
                    _('Use local path') + ' (' + self.app_obj.ytdl_bin + ')',
                    self.app_obj.ytdl_bin,
                ],
            )

        if os.name == 'nt':
            msg = _('Use custom path (not recommended on MS Windows)')
        else:
            msg = _('Use custom path')
        combo_list.append(
            [
                msg,
                None,       # Set by the callback
            ],
        )

        if os.name != 'nt':

            combo_list.append(
                [
                    _('Use PyPI path') + ' (' + self.app_obj.ytdl_path_pypi \
                    + ')',
                    self.app_obj.ytdl_path_pypi,
                ],
            )

        self.path_liststore = Gtk.ListStore(str, str)
        for mini_list in combo_list:
            self.path_liststore.append( [ mini_list[0], mini_list[1] ] )

        self.filepaths_combo = Gtk.ComboBox.new_with_model(self.path_liststore)
        grid.attach(self.filepaths_combo, 1, 1, (grid_width - 1), 1)
        renderer_text = Gtk.CellRendererText()
        self.filepaths_combo.pack_start(renderer_text, True)
        self.filepaths_combo.add_attribute(renderer_text, 'text', 0)
        self.filepaths_combo.set_entry_text_column(0)
        # (Signal connect appears below)

        entry = self.add_entry(grid,
            None,
            False,
            1, 2, 1, 1,
        )

        button = Gtk.Button(_('Set'))
        grid.attach(button, 2, 2, 1, 1)
        # (Signal connect appears below)

        # Set up those widgets
        if os.name == 'nt':

            if self.app_obj.ytdl_path_custom_flag:
                self.filepaths_combo.set_active(1)
            else:
                self.filepaths_combo.set_active(0)

        else:

            if self.app_obj.ytdl_path_custom_flag:
                self.filepaths_combo.set_active(2)
            elif self.app_obj.ytdl_path == self.app_obj.ytdl_path_default:
                self.filepaths_combo.set_active(0)
            elif self.app_obj.ytdl_path == self.app_obj.ytdl_path_pypi:
                self.filepaths_combo.set_active(3)
            else:
                self.filepaths_combo.set_active(1)

        if self.app_obj.ytdl_path_custom_flag:

            # (If this window is loaded due to
            #   mainapp.TartubeApp.debug_open_pref_win_flag, this value will be
            #   None)
            if self.app_obj.ytdl_path:
                entry.set_text(self.app_obj.ytdl_path)

        else:
            button.set_sensitive(False)

        # Now set up the next combo
        if not __main__.__pkg_strict_install_flag__:

            self.add_label(grid,
                _('Command for update operations'),
                0, 3, 1, 1,
            )

            self.cmd_liststore = Gtk.ListStore(str, str)
            for item in self.app_obj.ytdl_update_list:
                self.cmd_liststore.append(
                    [item, formats.YTDL_UPDATE_DICT[item]]
                )

            combo2 = Gtk.ComboBox.new_with_model(self.cmd_liststore)
            grid.attach(combo2, 1, 3, (grid_width - 1), 1)

            renderer_text = Gtk.CellRendererText()
            combo2.pack_start(renderer_text, True)
            combo2.add_attribute(renderer_text, 'text', 1)
            combo2.set_entry_text_column(1)

            combo2.set_active(
                self.app_obj.ytdl_update_list.index(
                    self.app_obj.ytdl_update_current,
                ),
            )
            if __main__.__pkg_strict_install_flag__:
                combo2.set_sensitive(False)
            # (Signal connect appears below)

            # Update the combos, so that the youtube-dl fork, rather than
            #   youtube-dl itself, is visible (if applicable)
            self.update_ytdl_combos()

        # (Signal connects from above)
        self.filepaths_combo.connect(
            'changed',
            self.on_ytdl_path_combo_changed,
            entry,
            button,
        )
        button.connect('clicked', self.on_ytdl_path_button_clicked, entry)

        if not __main__.__pkg_strict_install_flag__:
            combo2.connect('changed', self.on_update_combo_changed)


    def setup_downloader_js_runtime_tab(self, inner_notebook):

        """Called by self.setup_downloader_tab().

        Sets up the 'JavaScript' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Downloaders' \
            + ' > JavaScript'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('JavaScript'),
            inner_notebook,
        )
        grid_width = 4

        # JavaScript runtime paths
        self.add_label(grid,
            '<u>' + _('JavaScript runtime paths') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'Use a JavaScript runtime during all video downloads (recommended)'
            ),
            self.app_obj.js_runtime_flag,
            True,                   # Can be toggled by user
            0, 1, grid_width, 1,
        )
        # (Signal connect appears below)

        self.add_label(grid,
            'Select runtime',
            0, 2, 1, 1,
        )

        combo_list = [
            [_('deno (recommended)'), 'deno'],
            [_('node.js (not available by default)'), 'node'],
            [_('bun (not available by default)'), 'bun'],
            [_('QuickJS (not available by default)'), 'quickjs'],
        ]
        liststore = Gtk.ListStore(str, str)
        for mini_list in combo_list:
            liststore.append( [ mini_list[0], mini_list[1] ] )

        combo = Gtk.ComboBox.new_with_model(liststore)
        grid.attach(combo, 1, 2, (grid_width - 1), 1)
        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 0)
        combo.set_entry_text_column(0)
        combo.set_active(
            self.app_obj.js_runtime_list.index(
                self.app_obj.js_runtime_choice,
            ),
        )
        if not self.app_obj.js_runtime_flag:
            combo.set_sensitive(False)
        # (Signal connect appears below)

        self.add_label(grid,
            'Path to the executable',
            0, 3, 1, 1,
        )

        button = Gtk.Button(_('Set'))
        grid.attach(button, 2, 3, 1, 1)
        if not self.app_obj.js_runtime_flag:
            button.set_sensitive(False)
        # (Signal connect appears below)

        button2 = Gtk.Button(_('Reset'))
        grid.attach(button2, 3, 3, 1, 1)
        if not self.app_obj.js_runtime_flag:
            button2.set_sensitive(False)
        # (Signal connect appears below)

        entry = self.add_entry(grid,
            self.app_obj.ffmpeg_path,
            False,
            0, 4, grid_width, 1,
        )
        entry.set_sensitive(False)
        entry.set_editable(False)
        entry.set_hexpand(True)
        self.setup_downloader_js_runtime_tab_update_entry(entry)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_js_runtime_button_toggled,
            combo,
            entry,
            button,
            button2,
        )
        combo.connect('changed', self.on_js_runtime_combo_changed, entry)
        button.connect(
            'clicked',
            self.on_set_js_runtime_button_clicked,
            entry
        )
        button2.connect(
            'clicked',
            self.on_reset_js_runtime_button_clicked,
            entry
        )


    def setup_downloader_js_runtime_tab_update_entry(self, entry):

        """Called by self.setup_downloader_js_runtime_tab().

        Updates the entry displaying the path to the JS runtime.

        Args:

            entry (Gtk.Entry): The widget to update

        """

        val = self.app_obj.js_runtime_choice
        if self.app_obj.js_runtime_path:
            val += ':' + self.app_obj.js_runtime_path

        entry.set_text(val)


    def setup_downloader_ffmpeg_tab(self, inner_notebook):

        """Called by self.setup_downloader_tab().

        Sets up the 'FFmpeg / AVConv' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Downloaders' \
            + ' > FFmpeg / AVConv'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('FF_mpeg / AVConv'),
            inner_notebook,
        )
        grid_width = 4

        # Post-processor file paths
        self.add_label(grid,
            '<u>' + _('Post-processor file paths') + '</u>',
            0, 0, grid_width, 1,
        )
        self.add_label(grid,
            '<i>' + _(
            'You only need to set these paths if Tartube cannot find' \
            + ' FFmpeg / AVConv automatically'
            ) + '</i>',
            0, 1, grid_width, 1,
        )

        self.add_label(grid,
            _('Path to the FFmpeg executable'),
            0, 2, 1, 1,
        )

        button = Gtk.Button(_('Set'))
        grid.attach(button, 1, 2, 1, 1)
        # (Signal connect appears below)

        button2 = Gtk.Button(_('Reset'))
        grid.attach(button2, 2, 2, 1, 1)
        # (Signal connect appears below)

        button3 = Gtk.Button(_('Use default path'))
        grid.attach(button3, 3, 2, 1, 1)
        # (Signal connect appears below)

        entry = self.add_entry(grid,
            self.app_obj.ffmpeg_path,
            False,
            0, 3, grid_width, 1,
        )
        entry.set_sensitive(False)
        entry.set_editable(False)
        entry.set_hexpand(True)

        if os.name == 'nt':
            entry.set_sensitive(False)
            button.set_sensitive(False)

        # (Signal connects from above)
        button.connect('clicked', self.on_set_ffmpeg_button_clicked, entry)
        button2.connect('clicked', self.on_reset_ffmpeg_button_clicked, entry)
        button3.connect(
            'clicked',
            self.on_default_ffmpeg_button_clicked, entry,
        )

        self.add_label(grid,
            _('Path to the AVConv executable'),
            0, 4, 1, 1,
        )

        button4 = Gtk.Button(_('Set'))
        grid.attach(button4, 1, 4, 1, 1)
        # (Signal connect appears below)

        button5 = Gtk.Button(_('Reset'))
        grid.attach(button5, 2, 4, 1, 1)
        # (Signal connect appears below)

        button6 = Gtk.Button(_('Use default path'))
        grid.attach(button6, 3, 4, 1, 1)
        # (Signal connect appears below)

        entry2 = self.add_entry(grid,
            self.app_obj.ffmpeg_path,
            False,
            0, 5, grid_width, 1,
        )
        entry2.set_sensitive(False)
        entry2.set_editable(False)
        entry2.set_hexpand(True)

        if os.name == 'nt':
            entry2.set_sensitive(False)
            entry2.set_text(_('Not supported on MS Windows'))
            button4.set_sensitive(False)
            button5.set_sensitive(False)
            button6.set_sensitive(False)

        # (Signal connects from above)
        button4.connect('clicked', self.on_set_avconv_button_clicked, entry2)
        button5.connect('clicked', self.on_reset_avconv_button_clicked, entry2)
        button6.connect(
            'clicked',
            self.on_default_avconv_button_clicked,
            entry2,
        )


    def setup_downloader_streamlink_tab(self, inner_notebook):

        """Called by self.setup_downloader_tab().

        Sets up the 'streamlink' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Downloaders > streamlink'
        )
        ignore_me = _(
            'TRANSLATOR\'S NOTE: \'streamlink\' is the name of a Python' \
            + ' module'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_streamlink'),
            inner_notebook,
        )
        grid_width = 3

        # streamlink file path
        self.add_label(grid,
            '<u>' + _('streamlink file path') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            _('Path to the streamlink executable'),
            0, 1, 1, 1,
        )

        button = Gtk.Button(_('Set'))
        grid.attach(button, 1, 1, 1, 1)
        # (Signal connect appears below)

        button2 = Gtk.Button(_('Reset'))
        grid.attach(button2, 2, 1, 1, 1)
        # (Signal connect appears below)

        entry = self.add_entry(grid,
            self.app_obj.streamlink_path,
            False,
            0, 2, grid_width, 1,
        )
        entry.set_sensitive(False)
        entry.set_editable(False)
        entry.set_hexpand(True)

        if os.name == 'nt':
            entry.set_sensitive(False)
            entry.set_text(_('Install from main menu'))
            button.set_sensitive(False)
            button2.set_sensitive(False)

        # (Signal connects from above)
        button.connect(
            'clicked',
            self.on_set_streamlink_button_clicked,
            entry,
        )
        button2.connect(
            'clicked',
            self.on_reset_streamlink_button_clicked,
            entry,
        )


    def setup_options_dl_list_tab(self, inner_notebook):

        """Called by self.setup_options_tab().

        Sets up the 'Download options' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Options' \
            + ' > Download options'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Download options'),
            inner_notebook,
        )
        grid_width = 4

        # List of download options
        self.add_label(grid,
            '<u>' + _('List of download options') + '</u>',
            0, 0, grid_width, 1,
        )

        # (GenericConfigWin.add_treeview() doesn't support multiple columns, so
        #   we'll do everything ourselves)
        frame = Gtk.Frame()
        grid.attach(frame, 0, 1, grid_width, 1)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_headers_visible(True)

        for i, column_title in enumerate(
            [
                '#', _('Name'), _('Videos tab'), _('Classic Mode'),
                _('Dropzone'), _('Applied to media'),
            ]
        ):
            if i >= 2 and i <= 4:
                renderer_toggle = Gtk.CellRendererToggle()
                column_toggle = Gtk.TreeViewColumn(
                    column_title,
                    renderer_toggle,
                    active=i,
                )
                treeview.append_column(column_toggle)
                column_toggle.set_resizable(False)
            else:
                renderer_text = Gtk.CellRendererText()
                column_text = Gtk.TreeViewColumn(
                    column_title,
                    renderer_text,
                    text=i,
                )
                treeview.append_column(column_text)
                column_text.set_resizable(True)

        self.options_liststore = Gtk.ListStore(int, str, bool, bool, bool, str)
        treeview.set_model(self.options_liststore)

        # Initialise the list
        self.setup_options_dl_list_tab_update_treeview()

        # Add editing buttons
        self.add_label(grid,
            'Manager name',
            0, 2, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            True,
            1, 2, 1, 1,
        )

        button = Gtk.Button()
        grid.attach(button, 2, 2, 1, 1)
        button.set_label(_('Add'))
        button.connect(
            'clicked',
            self.on_options_add_button_clicked,
            entry,
        )

        button2 = Gtk.Button()
        grid.attach(button2, 3, 2, 1, 1)
        button2.set_label(_('Import'))
        button2.connect(
            'clicked',
            self.on_options_import_button_clicked,
            entry,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

        button3 = Gtk.Button()
        grid2.attach(button3, 0, 0, 1, 1)
        button3.set_label(_('Edit'))
        button3.connect(
            'clicked',
            self.on_options_edit_button_clicked,
            treeview,
        )

        button4 = Gtk.Button()
        grid2.attach(button4, 1, 0, 1, 1)
        button4.set_label(_('Export'))
        button4.connect(
            'clicked',
            self.on_options_export_button_clicked,
            treeview,
        )

        button5 = Gtk.Button()
        grid2.attach(button5, 2, 0, 1, 1)
        button5.set_label(_('Clone'))
        button5.connect(
            'clicked',
            self.on_options_clone_button_clicked,
            treeview,
        )

        button6 = Gtk.Button()
        grid2.attach(button6, 3, 0, 1, 1)
        button6.set_label(_('Use in Classic Mode tab'))
        button6.connect(
            'clicked',
            self.on_options_use_classic_button_clicked,
            treeview,
        )

        button7 = Gtk.Button()
        grid2.attach(button7, 4, 0, 1, 1)
        button7.set_label(_('Delete'))
        button7.connect(
            'clicked',
            self.on_options_delete_button_clicked,
            treeview,
        )

        # (Use an empty label for spacing)
        label = self.add_label(grid2,
            '',
            5, 0, 1, 1,
        )
        label.set_hexpand(True)

        button8 = Gtk.Button()
        grid2.attach(button8, 6, 0, 1, 1)
        button8.set_label(_('Refresh list'))
        button8.connect(
            'clicked',
            self.setup_options_dl_list_tab_update_treeview,
        )


    def setup_options_dl_list_tab_update_treeview(self, button=None):

        """Can be called by anything.

        Fills or updates the treeview.
        """

        self.options_liststore.clear()

        for uid in sorted(self.app_obj.options_reg_dict):
            self.setup_options_dl_list_tab_add_row(
                self.app_obj.options_reg_dict[uid],
            )


    def setup_options_dl_list_tab_add_row(self, options_obj):

        """Can be called by anything.

        Adds a row to the treeview.

        Args:

            options_obj (options.OptionsManager) - The options manager object
                to display on this row

        """

        row_list = []

        row_list.append(options_obj.uid)
        row_list.append(
            ttutils.tidy_up_long_string(
                options_obj.name,
                self.app_obj.main_win_obj.short_string_max_len,
            ),
        )

        if self.app_obj.general_options_obj \
        and self.app_obj.general_options_obj == options_obj:
            row_list.append(True)
        else:
            row_list.append(False)

        if self.app_obj.classic_options_obj \
        and self.app_obj.classic_options_obj == options_obj:
            row_list.append(True)
        else:
            row_list.append(False)

        if options_obj.uid in self.app_obj.classic_dropzone_list:
            row_list.append(True)
        else:
            row_list.append(False)

        if not options_obj.dbid_list:
            row_list.append('')
        else:
            row_list.append(self.get_options_applied_text(options_obj))

        self.options_liststore.append(row_list)


    def setup_options_dl_prefs_tab(self, inner_notebook):

        """Called by self.setup_downloader_tab().

        Sets up the 'Preferences' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Options > Preferences'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Preferences'),
            inner_notebook,
        )
        grid_width = 2

        # Download options preferences
        self.add_label(grid,
            '<u>' + _('Download options preferences') + '</u>',
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'When applying download options to something, clone the general' \
            + ' download options',
            ),
            self.app_obj.auto_clone_options_flag,
            True,                   # Can be toggled by user
            0, 1, 1, 1,
        )
        checkbutton.connect('toggled', self.on_auto_clone_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'After downloading a video, destroy its download options',
            ),
            self.app_obj.auto_delete_options_flag,
            True,                   # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton2.connect('toggled', self.on_auto_delete_button_toggled)


    def setup_options_ffmpeg_list_tab(self, inner_notebook):

        """Called by self.setup_options_tab().

        Sets up the 'FFmpeg options' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Options > FFmpeg options'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_FFmpeg options'),
            inner_notebook,
        )
        grid_width = 4

        # List of FFmpeg options managers
        self.add_label(grid,
            '<u>' + _('List of FFmpeg options managers') + '</u>',
            0, 0, grid_width, 1,
        )

        # (GenericConfigWin.add_treeview() doesn't support multiple columns, so
        #   we'll do everything ourselves)
        frame = Gtk.Frame()
        grid.attach(frame, 0, 1, grid_width, 1)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_headers_visible(True)

        # (Fourth column is empty, to keep the 3rd column at a minimum width)
        for i, column_title in enumerate(
            [ '#', _('Name'), _('Current'), '' ]
        ):
            if i == 2:
                renderer_toggle = Gtk.CellRendererToggle()
                column_toggle = Gtk.TreeViewColumn(
                    column_title,
                    renderer_toggle,
                    active=i,
                )
                treeview.append_column(column_toggle)
                column_toggle.set_resizable(False)
            else:
                renderer_text = Gtk.CellRendererText()
                column_text = Gtk.TreeViewColumn(
                    column_title,
                    renderer_text,
                    text=i,
                )
                treeview.append_column(column_text)
                column_text.set_resizable(True)

        self.ffmpeg_liststore = Gtk.ListStore(int, str, bool, str)
        treeview.set_model(self.ffmpeg_liststore)

        # Initialise the list
        self.setup_options_ffmpeg_list_tab_update_treeview()

        # Add editing buttons
        self.add_label(grid,
            'Manager name',
            0, 2, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            True,
            1, 2, 1, 1,
        )

        button = Gtk.Button()
        grid.attach(button, 2, 2, 1, 1)
        button.set_label(_('Add'))
        button.connect(
            'clicked',
            self.on_ffmpeg_add_button_clicked,
            entry,
        )

        button2 = Gtk.Button()
        grid.attach(button2, 3, 2, 1, 1)
        button2.set_label(_('Import'))
        button2.connect(
            'clicked',
            self.on_ffmpeg_import_button_clicked,
            entry,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

        button3 = Gtk.Button()
        grid2.attach(button3, 0, 0, 1, 1)
        button3.set_label(_('Edit'))
        button3.connect(
            'clicked',
            self.on_ffmpeg_edit_button_clicked,
            treeview,
        )

        button4 = Gtk.Button()
        grid2.attach(button4, 1, 0, 1, 1)
        button4.set_label(_('Export'))
        button4.connect(
            'clicked',
            self.on_ffmpeg_export_button_clicked,
            treeview,
        )

        button5 = Gtk.Button()
        grid2.attach(button5, 2, 0, 1, 1)
        button5.set_label(_('Clone'))
        button5.connect(
            'clicked',
            self.on_ffmpeg_clone_button_clicked,
            treeview,
        )

        button6 = Gtk.Button()
        grid2.attach(button6, 3, 0, 1, 1)
        button6.set_label(_('Use these options'))
        button6.connect(
            'clicked',
            self.on_ffmpeg_use_button_clicked,
            treeview,
        )

        button7 = Gtk.Button()
        grid2.attach(button7, 4, 0, 1, 1)
        button7.set_label(_('Delete'))
        button7.connect(
            'clicked',
            self.on_ffmpeg_delete_button_clicked,
            treeview,
        )

        # (Use an empty label for spacing)
        label = self.add_label(grid2,
            '',
            5, 0, 1, 1,
        )
        label.set_hexpand(True)

        button8 = Gtk.Button()
        grid2.attach(button8, 6, 0, 1, 1)
        button8.set_label(_('Refresh list'))
        button8.connect(
            'clicked',
            self.setup_options_ffmpeg_list_tab_update_treeview,
        )


    def setup_options_ffmpeg_list_tab_update_treeview(self):

        """Can be called by anything.

        Fills or updates the treeview.
        """

        self.ffmpeg_liststore.clear()

        for uid in sorted(self.app_obj.ffmpeg_reg_dict):
            self.setup_options_ffmpeg_list_tab_add_row(
                self.app_obj.ffmpeg_reg_dict[uid],
            )


    def setup_options_ffmpeg_list_tab_add_row(self, options_obj):

        """Can be called by anything.

        Adds a row to the treeview.

        Args:

            options_obj (ffmpeg_tartube.FFmpegOptionsManager): The FFmpeg
                options manager object to display on this row

        """

        row_list = []

        row_list.append(options_obj.uid)
        row_list.append(
            ttutils.tidy_up_long_string(
                options_obj.name,
                self.app_obj.main_win_obj.short_string_max_len,
            ),
        )

        if self.app_obj.ffmpeg_options_obj \
        and self.app_obj.ffmpeg_options_obj == options_obj:
            row_list.append(True)
        else:
            row_list.append(False)

        # (Fourth column is empty, to keep the 3rd column at a minimum width)
        row_list.append('')

        self.ffmpeg_liststore.append(row_list)


    def setup_output_general_tab(self, inner_notebook):

        """Called by self.setup_output_tab().

        Sets up the 'General' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Output > General'
        )

        tab, grid = self.add_inner_notebook_tab(_('_General'), inner_notebook)

        # General preferences (applies to both the Output tab, terminal window
        #   and downloader log)
        self.add_label(grid,
            '<u>' + _('General preferences') + '</u>',
            0, 0, 1, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'Applies to Output tab, terminal window and downloader log',
            ) + '</i>',
            0, 1, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Downloader writes verbose output (youtube-dl debugging mode)'),
            self.app_obj.ytdl_write_verbose_flag,
            True,               # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton.set_hexpand(False)
        checkbutton.connect('toggled', self.on_ytdl_verbose_button_toggled)


    def setup_output_outputtab_tab(self, inner_notebook):

        """Called by self.setup_output_tab().

        Sets up the 'Output tab' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Output > Output tab'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Output tab'),
            inner_notebook,
        )
        grid_width = 2

        # Output tab preferences
        self.add_label(grid,
            '<u>' + _('Output tab preferences') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Display downloader system commands in the Output tab'),
            self.app_obj.ytdl_output_system_cmd_flag,
            True,               # Can be toggled by user
            0, 1, grid_width, 1,
        )
        checkbutton.set_hexpand(False)
        checkbutton.connect('toggled', self.on_output_system_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Display general output (from downloader\'s STDOUT) in the' \
            + ' Output tab',
            ),
            self.app_obj.ytdl_output_stdout_flag,
            True,               # Can be toggled by user
            0, 2, grid_width, 1,
        )
        checkbutton2.set_hexpand(False)
        # (Signal connect appears below)

        checkbutton3 = self.add_checkbutton(grid,
            _('...but don\'t write each video\'s JSON data'),
            self.app_obj.ytdl_output_ignore_json_flag,
            True,               # Can be toggled by user
            0, 3, grid_width, 1,
        )
        checkbutton3.set_hexpand(False)
        checkbutton3.connect('toggled', self.on_output_json_button_toggled)
        if not self.app_obj.ytdl_output_stdout_flag:
            checkbutton3.set_sensitive(False)

        checkbutton4 = self.add_checkbutton(grid,
            _('...but don\'t write each video\'s download progress'),
            self.app_obj.ytdl_output_ignore_progress_flag,
            True,               # Can be toggled by user
            0, 4, grid_width, 1,
        )
        checkbutton4.set_hexpand(False)
        checkbutton4.connect('toggled', self.on_output_progress_button_toggled)
        if not self.app_obj.ytdl_output_stdout_flag:
            checkbutton4.set_sensitive(False)

        # (Signal connect from above)
        checkbutton2.connect(
            'toggled',
            self.on_output_stdout_button_toggled,
            checkbutton3,
            checkbutton4,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _(
            'Display errors/warnings (from downloader\'s STDERR) in the' \
            + ' Output tab',
            ),
            self.app_obj.ytdl_output_stderr_flag,
            True,               # Can be toggled by user
            0, 5, grid_width, 1,
        )
        checkbutton5.set_hexpand(False)
        checkbutton5.connect('toggled', self.on_output_stderr_button_toggled)

        # N.B. I didn't actually implement a check for MS Windows, so this
        #   setting will still be visible on Linux (where users are likely
        #   seeing a monospace font for all operations anyway)
        checkbutton6 = self.add_checkbutton(grid,
            _('Disable monospace fonts in the Output tab (MS Windows only)'),
            self.app_obj.disable_monospaced_output_flag,
            True,               # Can be toggled by user
            0, 6, 1, 1,
        )
        checkbutton6.set_hexpand(False)
        checkbutton6.connect(
            'toggled',
            self.on_disable_monospaced_button_toggled
        )

        checkbutton7 = self.add_checkbutton(grid,
            _('Limit the size of Output tab pages to'),
            self.app_obj.output_size_apply_flag,
            True,               # Can be toggled by user
            0, 7, 1, 1,
        )
        checkbutton7.set_hexpand(False)
        checkbutton7.connect('toggled', self.on_output_size_button_toggled)

        spinbutton = self.add_spinbutton(grid,
            self.app_obj.output_size_min,
            self.app_obj.output_size_max,
            1,                  # Step
            self.app_obj.output_size_default,
            1, 7, 1, 1,
        )
        spinbutton.connect(
            'value-changed',
            self.on_output_size_spinbutton_changed,
        )

        if not self.app_obj.simple_prefs_flag:

            checkbutton8 = self.add_checkbutton(grid,
                _(
                    'Empty pages in the Output tab at the start of every' \
                    + ' operation',
                ),
                self.app_obj.ytdl_output_start_empty_flag,
                True,               # Can be toggled by user
                0, 8, grid_width, 1,
            )
            checkbutton8.set_hexpand(False)
            checkbutton8.connect(
                'toggled',
                self.on_output_empty_button_toggled,
            )

            checkbutton9 = self.add_checkbutton(grid,
                _(
                'Show a summary of active threads (changes are applied when' \
                + ' Tartube restarts)',
                ),
                self.app_obj.ytdl_output_show_summary_flag,
                True,               # Can be toggled by user
                0, 9, grid_width, 1,
            )
            checkbutton9.set_hexpand(False)
            checkbutton9.connect(
                'toggled',
                self.on_output_summary_button_toggled,
            )

            checkbutton10 = self.add_checkbutton(grid,
                _(
                'During update/info operations, automatically switch to the' \
                + ' Output tab',
                ),
                self.app_obj.auto_switch_output_flag,
                True,                   # Can be toggled by user
                0, 10, grid_width, 1,
            )
            checkbutton10.connect(
                'toggled',
                self.on_auto_switch_button_toggled,
            )

            checkbutton11 = self.add_checkbutton(grid,
                _(
                'During a refresh operation, show all matching videos in the' \
                + ' Output tab',
                ),
                self.app_obj.refresh_output_videos_flag,
                True,               # Can be toggled by user
                0, 11, grid_width, 1,
            )
            checkbutton11.set_hexpand(False)
            # (Signal connect appears below)

            checkbutton12 = self.add_checkbutton(grid,
                _('...also show all non-matching videos'),
                self.app_obj.refresh_output_verbose_flag,
                True,               # Can be toggled by user
                0, 12, grid_width, 1,
            )
            checkbutton12.set_hexpand(False)
            checkbutton12.connect(
                'toggled',
                self.on_refresh_verbose_button_toggled,
            )
            if not self.app_obj.refresh_output_videos_flag:
                checkbutton11.set_sensitive(False)

            # (Signal connect from above)
            checkbutton11.connect(
                'toggled',
                self.on_refresh_videos_button_toggled,
                checkbutton12,
            )


    def setup_output_terminal_tab(self, inner_notebook):

        """Called by self.setup_output_tab().

        Sets up the 'Terminal window' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Output > Terminal window'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Terminal window'),
            inner_notebook,
        )

        # Terminal window preferences
        self.add_label(grid,
            '<u>' + _('Terminal window preferences') + '</u>',
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Write downloader system commands to the terminal window'),
            self.app_obj.ytdl_write_system_cmd_flag,
            True,               # Can be toggled by user
            0, 1, 1, 1,
        )
        checkbutton.set_hexpand(False)
        checkbutton.connect('toggled', self.on_terminal_system_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Write general output (from downloader\'s STDOUT) to the' \
            + ' terminal window',
            ),
            self.app_obj.ytdl_write_stdout_flag,
            True,               # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton2.set_hexpand(False)
        # (Signal connect appears below)

        checkbutton3 = self.add_checkbutton(grid,
            _('...but don\'t write each video\'s JSON data'),
            self.app_obj.ytdl_write_ignore_json_flag,
            True,               # Can be toggled by user
            0, 3, 1, 1,
        )
        checkbutton3.set_hexpand(False)
        checkbutton3.connect('toggled', self.on_terminal_json_button_toggled)
        if not self.app_obj.ytdl_write_stdout_flag:
            checkbutton3.set_sensitive(False)

        checkbutton4 = self.add_checkbutton(grid,
            _('...but don\'t write each video\'s download progress'),
            self.app_obj.ytdl_write_ignore_progress_flag,
            True,               # Can be toggled by user
            0, 4, 1, 1,
        )
        checkbutton4.set_hexpand(False)
        checkbutton4.connect(
            'toggled',
            self.on_terminal_progress_button_toggled,
        )
        if not self.app_obj.ytdl_write_stdout_flag:
            checkbutton4.set_sensitive(False)

        # (Signal connect from above)
        checkbutton2.connect(
            'toggled',
            self.on_terminal_stdout_button_toggled,
            checkbutton3,
            checkbutton4,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _(
            'Write errors/warnings (from downloader\'s STDERR) to the' \
            + ' terminal window',
            ),
            self.app_obj.ytdl_write_stderr_flag,
            True,               # Can be toggled by user
            0, 5, 1, 1,
        )
        checkbutton5.set_hexpand(False)
        checkbutton5.connect(
            'toggled',
            self.on_terminal_stderr_button_toggled,
        )


    def setup_output_log_tab(self, inner_notebook):

        """Called by self.setup_output_tab().

        Sets up the 'Log' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Output > Log'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Downloader log'),
            inner_notebook,
        )

        # Downloader log preferences
        self.add_label(grid,
            '<u>' + _('Downloader log preferences') + '</u>',
            0, 0, 1, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'If enabled, the file \'{0}\' is written to Tartube\'s' \
                + ' data folder',
            ).format(self.app_obj.ytdl_log_name) + '</i>',
            0, 1, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Write downloader system commands to the log'),
            self.app_obj.ytdl_log_system_cmd_flag,
            True,               # Can be toggled by user
            0, 2, 1, 1,
        )
        checkbutton.set_hexpand(False)
        checkbutton.connect('toggled', self.on_log_system_button_toggled)

        checkbutton2 = self.add_checkbutton(grid,
            _('Write general output (from downloader\'s STDOUT) to the log'),
            self.app_obj.ytdl_log_stdout_flag,
            True,               # Can be toggled by user
            0, 3, 1, 1,
        )
        checkbutton2.set_hexpand(False)
        # (Signal connect appears below)

        checkbutton3 = self.add_checkbutton(grid,
            _('...but don\'t write each video\'s JSON data'),
            self.app_obj.ytdl_log_ignore_json_flag,
            True,               # Can be toggled by user
            0, 4, 1, 1,
        )
        checkbutton3.set_hexpand(False)
        checkbutton3.connect('toggled', self.on_log_json_button_toggled)
        if not self.app_obj.ytdl_log_stdout_flag:
            checkbutton3.set_sensitive(False)

        checkbutton4 = self.add_checkbutton(grid,
            _('...but don\'t write each video\'s download progress'),
            self.app_obj.ytdl_log_ignore_progress_flag,
            True,               # Can be toggled by user
            0, 5, 1, 1,
        )
        checkbutton4.set_hexpand(False)
        checkbutton4.connect(
            'toggled',
            self.on_log_progress_button_toggled,
        )
        if not self.app_obj.ytdl_log_stdout_flag:
            checkbutton4.set_sensitive(False)

        # (Signal connect from above)
        checkbutton2.connect(
            'toggled',
            self.on_log_stdout_button_toggled,
            checkbutton3,
            checkbutton4,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _('Write errors/warnings (from downloader\'s STDERR) to the log'),
            self.app_obj.ytdl_log_stderr_flag,
            True,               # Can be toggled by user
            0, 6, 1, 1,
        )
        checkbutton5.set_hexpand(False)
        checkbutton5.connect(
            'toggled',
            self.on_log_stderr_button_toggled,
        )


    # Callback class methods


    def on_add_blocked_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables adding blocked videos to the database.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.add_blocked_videos_flag:
            self.app_obj.set_add_blocked_videos_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.add_blocked_videos_flag:
            self.app_obj.set_add_blocked_videos_flag(False)


    def on_add_db_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables adding split files to Tartube's database.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.split_video_add_db_flag:
            self.app_obj.set_split_video_add_db_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.split_video_add_db_flag:
            self.app_obj.set_split_video_add_db_flag(False)


    def on_add_from_list_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_database_tab().

        Enables/disables automatic adding of new Tartube data directories to
        the list of recent directories.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.data_dir_add_from_list_flag:
            self.app_obj.set_data_dir_add_from_list_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.data_dir_add_from_list_flag:
            self.app_obj.set_data_dir_add_from_list_flag(False)


    def on_age_restrict_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_websites_tab().

        Enables/disables ignoring of YouTube age-restriction error messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_yt_age_restrict_flag:
            self.app_obj.set_ignore_yt_age_restrict_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_yt_age_restrict_flag:
            self.app_obj.set_ignore_yt_age_restrict_flag(False)


    def on_alt_time_combo_changed(self, combo, type_str):

        """Called from a callback in self.setup_operations_limits_tab().

        Sets the hours or minutes portion of the start or stop time for
        alternative performance limits.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            type_str (str): 'start_hour', 'start_min', 'stop_hour', 'stop_min'

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        value = model[tree_iter][0]

        if type_str == 'start_hour' or type_str == 'start_min':

            if type_str == 'start_hour':
                start_time = value + self.app_obj.alt_start_time[2:5]
            else:
                start_time = self.app_obj.alt_start_time[0:3] + value

            self.app_obj.set_alt_start_time(start_time)

        elif type_str == 'stop_hour' or type_str == 'stop_min':

            if type_str == 'stop_hour':
                stop_time = value + self.app_obj.alt_stop_time[2:5]
            else:
                stop_time = self.app_obj.alt_stop_time[0:3] + value

            self.app_obj.set_alt_stop_time(stop_time)


    def on_alt_days_combo_changed(self, combo):

        """Called from a callback in self.setup_operations_limits_tab().

        Sets the day(s) on which alternative performance limits apply.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            type_str (str): One of the values in formats.SPECIFIED_DAYS_LIST,
                e.g. 'every_day'

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.app_obj.set_alt_day_string(model[tree_iter][1])


    def on_archive_button_toggled(self, checkbutton, checkbutton2, radiobutton,
    radiobutton2, radiobutton3, button, button2):

        """Called from callback in self.setup_operations_archive_tab().

        Enables/disables creation of youtube-dl's archive file,
        ytdl-archive.txt.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Other widgets to modify

            radiobutton, radiobutton2, radiobutton3 (Gtk.RadioButton): Other
                widgets to modify

            button, button2 (Gtk.Button): Other widgets to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.allow_ytdl_archive_flag:
            self.app_obj.set_allow_ytdl_archive_flag(True)
            radiobutton.set_sensitive(True)
            radiobutton2.set_sensitive(True)
            radiobutton3.set_sensitive(True)
            if self.app_obj.allow_ytdl_archive_mode == 'custom':
                button.set_sensitive(True)
                button2.set_sensitive(True)
            else:
                button.set_sensitive(False)
                button2.set_sensitive(False)
            checkbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.allow_ytdl_archive_flag:
            self.app_obj.set_allow_ytdl_archive_flag(False)
            radiobutton.set_sensitive(False)
            radiobutton2.set_sensitive(False)
            radiobutton3.set_sensitive(False)
            button.set_sensitive(False)
            button2.set_sensitive(False)
            checkbutton2.set_sensitive(False)
            checkbutton2.set_active(False)


    def on_archive_classic_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_archive_tab().

        Enables/disables creation of youtube-dl's archive file,
        ytdl-archive.txt, when downloading from the Classic Mode tab. Toggling
        the corresponding Gtk.ToggleButton in the Classic Mode tab sets the IV
        (and makes sure the two buttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj

        other_flag = main_win_obj.classic_archive_button.get_active()
        if (checkbutton.get_active() and not other_flag):
            main_win_obj.classic_archive_button.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.classic_archive_button.set_active(False)


    def on_archive_radiobutton_toggled(self, widget, radiobutton, \
    radiobutton2, radiobutton3, entry, button, button2):

        """Called from callback in self.setup_operations_archive_tab().

        Enables/disables creation of youtube-dl's archive file,
        ytdl-archive.txt.

        Args:

            widget (Gtk.RadioButton): The widget clicked

            radiobutton, radiobutton2, radiobutton3 (Gtk.RadioButton): Other
                widgets to check

            entry (Gtk.Entry): A widget to modify

            button, button2 (Gtk.Button): Other widgets to modify

        """

        if radiobutton.get_active():
            self.app_obj.set_allow_ytdl_archive_mode('default')
            entry.set_text('')
            self.app_obj.set_allow_ytdl_archive_path(None)
            button.set_sensitive(False)
            button2.set_sensitive(False)

        elif radiobutton2.get_active():
            self.app_obj.set_allow_ytdl_archive_mode('top')
            entry.set_text('')
            self.app_obj.set_allow_ytdl_archive_path(None)
            button.set_sensitive(False)
            button2.set_sensitive(False)

        elif radiobutton3.get_active():
            self.app_obj.set_allow_ytdl_archive_mode('custom')
            button.set_sensitive(True)
            button2.set_sensitive(True)


    def on_archive_update_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_archive_tab().

        Enables/disables updating the youtube-dl archive file, when a video is
        moved into a media.Folder.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.update_ytdl_archive_on_move_flag:
            self.app_obj.set_update_ytdl_archive_on_move_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.update_ytdl_archive_on_move_flag:
            self.app_obj.set_update_ytdl_archive_on_move_flag(False)


    def on_auto_assign_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables auto-assigning anonymous youtube-dl error/warning
        messages to the most probable video.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.auto_assign_errors_warnings_flag:
            self.app_obj.set_auto_assign_errors_warnings_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.auto_assign_errors_warnings_flag:
            self.app_obj.set_auto_assign_errors_warnings_flag(False)


    def on_auto_clone_button_toggled(self, checkbutton):

        """Called from callback in self.setup_options_prefs().

        Enables/disables auto-cloning of the General Options Manager.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.auto_clone_options_flag:
            self.app_obj.set_auto_clone_options_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.auto_clone_options_flag:
            self.app_obj.set_auto_clone_options_flag(False)


    def on_auto_delete_button_toggled(self, checkbutton):

        """Called from callback in self.setup_options_prefs().

        Enables/disables auto-deleting of download options applied to a
        media.Video, after it has been downloaded.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.auto_delete_options_flag:
            self.app_obj.set_auto_delete_options_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.auto_delete_options_flag:
            self.app_obj.set_auto_delete_options_flag(False)


    def on_auto_delete_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables auto-deleting the original video after splitting it
        into smaller pieces.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.split_video_auto_delete_flag:
            self.app_obj.set_split_video_auto_delete_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.split_video_auto_delete_flag:
            self.app_obj.set_split_video_auto_delete_flag(False)


    def on_auto_delete_type_combo_changed(self, combo):

        """Called from a callback in self.setup_files_delete_tab().

        Sets whether auto-deletion applies to videos downloaded or uploaded
        after a certain time.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()

        if model[tree_iter][1] == 'upload':
            self.app_obj.set_auto_delete_type_flag(True)
        else:
            self.app_obj.set_auto_delete_type_flag(False)


    def on_auto_delete_videos_button_toggled(self, checkbutton, combo,
    spinbutton, checkbutton2, checkbutton3, radiobutton, radiobutton2):

        """Called from callback in self.setup_files_delete_tab().

        Enables/disables automatic deletion of downloaded videos.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): A widget to be (de)sensitised

            combo (Gtk.ComboBox): Other widgets to be (de)sensitised

            checkbutton2, checkbutton3 (Gtk.CheckButton): Other widgets to be
                (de)sensitised

            radiobutton, radiobutton2 (Gtk.RadioButton): Other widgets to be
                (de)sensitised

        """

        if checkbutton.get_active() \
        and not self.app_obj.auto_delete_flag:
            self.app_obj.set_auto_delete_flag(True)
            spinbutton.set_sensitive(True)
            combo.set_sensitive(True)
            checkbutton3.set_sensitive(True)
            radiobutton.set_sensitive(True)
            radiobutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.auto_delete_flag:
            self.app_obj.set_auto_delete_flag(False)
            spinbutton.set_sensitive(False)
            combo.set_sensitive(False)
            if checkbutton2.get_active():
                checkbutton3.set_sensitive(True)
                radiobutton.set_sensitive(True)
                radiobutton2.set_sensitive(True)
            else:
                checkbutton3.set_active(False)
                checkbutton3.set_sensitive(False)
                radiobutton.set_active(True)
                radiobutton.set_sensitive(False)
                radiobutton2.set_sensitive(False)


    def on_auto_delete_videos_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_files_delete_tab().

        Sets the number of days after which downloaded videos should be
        deleted.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_auto_delete_days(spinbutton.get_value())


    def on_auto_remove_videos_button_toggled(self, checkbutton, combo,
    spinbutton, checkbutton2, checkbutton3, radiobutton, radiobutton2):

        """Called from callback in self.setup_files_delete_tab().

        Enables/disables automatic removal of downloaded videos.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): A widget to be (de)sensitised

            combo (Gtk.ComboBox): Other widgets to be (de)sensitised

            checkbutton2, checkbutton3 (Gtk.CheckButton): Other widgets to be
                (de)sensitised

            radiobutton, radiobutton2 (Gtk.RadioButton): Other widgets to be
                (de)sensitised

        """

        if checkbutton.get_active() \
        and not self.app_obj.auto_remove_flag:
            self.app_obj.set_auto_remove_flag(True)
            spinbutton.set_sensitive(True)
            combo.set_sensitive(True)
            checkbutton3.set_sensitive(True)
            radiobutton.set_sensitive(True)
            radiobutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.auto_remove_flag:
            self.app_obj.set_auto_remove_flag(False)
            spinbutton.set_sensitive(False)
            combo.set_sensitive(False)
            if checkbutton2.get_active():
                checkbutton3.set_sensitive(True)
                radiobutton.set_sensitive(True)
                radiobutton2.set_sensitive(True)
            else:
                checkbutton3.set_active(False)
                checkbutton3.set_sensitive(False)
                radiobutton.set_active(True)
                radiobutton.set_sensitive(False)
                radiobutton2.set_sensitive(False)


    def on_auto_remove_videos_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_files_delete_tab().

        Sets the number of days after which downloaded videos should be
        removed.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_auto_remove_days(spinbutton.get_value())


    def on_auto_open_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables auto-opening the destination directory after splitting
        a video.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.split_video_auto_open_flag:
            self.app_obj.set_split_video_auto_open_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.split_video_auto_open_flag:
            self.app_obj.set_split_video_auto_open_flag(False)


    def on_auto_remove_type_combo_changed(self, combo):

        """Called from a callback in self.setup_files_delete_tab().

        Sets whether auto-removal applies to videos downloaded or uploaded
        after a certain time.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()

        if model[tree_iter][1] == 'upload':
            self.app_obj.set_auto_remove_type_flag(True)
        else:
            self.app_obj.set_auto_remove_type_flag(False)


    def on_auto_restart_button_toggled(self, checkbutton, spinbutton,
    spinbutton2):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables restarting a stalled download operation.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton, spinbutton2 (Gtk.SpinButton): Other widgets to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.operation_auto_restart_flag:
            self.app_obj.set_operation_auto_restart_flag(True)
            spinbutton.set_sensitive(True)
            spinbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.operation_auto_restart_flag:
            self.app_obj.set_operation_auto_restart_flag(False)
            spinbutton.set_sensitive(False)
            spinbutton2.set_sensitive(False)


    def on_auto_restart_max_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Sets the maximum number of restarts after a stalled download.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_operation_auto_restart_max(spinbutton.get_value())


    def on_auto_restart_time_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Sets the time after which a stalled download job is restarted.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_operation_auto_restart_time(spinbutton.get_value())


    def on_auto_switch_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables automatically switching to the Output tab when an
        update operation starts.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.auto_switch_output_flag:
            self.app_obj.set_auto_switch_output_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.auto_switch_output_flag:
            self.app_obj.set_auto_switch_output_flag(False)


    def on_auto_update_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables automatic update operation before every download
        operation.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.operation_auto_update_flag:
            self.app_obj.set_operation_auto_update_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.operation_auto_update_flag:
            self.app_obj.set_operation_auto_update_flag(False)


    def on_autostop_size_button_toggled(self, checkbutton, spinbutton, combo):

        """Called from callback in self.setup_scheduling_stop_tab().

        Enables/disables auto-stopping a download operation after a certain
        amount of disk space.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): Another widget to modify

            combo (Gtk.ComboBox): Another widget to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.autostop_size_flag:
            self.app_obj.set_autostop_size_flag(True)
            spinbutton.set_sensitive(True)
            combo.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.autostop_size_flag:
            self.app_obj.set_autostop_size_flag(False)
            spinbutton.set_sensitive(False)
            combo.set_sensitive(False)


    def on_autostop_size_combo_changed(self, combo):

        """Called from a callback in self.setup_scheduling_stop_tab().

        Sets the disk space unit at which a download operation is auto-stopped.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.app_obj.set_autostop_size_unit(model[tree_iter][0])


    def on_autostop_size_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_scheduling_stop_tab().

        Sets the disk space value at which a download operation is
        auto-stopped.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_autostop_size_value(spinbutton.get_value())


    def on_autostop_time_button_toggled(self, checkbutton, spinbutton, combo):

        """Called from callback in self.setup_scheduling_stop_tab().

        Enables/disables auto-stopping a download operation after a certain
        time.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): Another widget to modify

            combo (Gtk.ComboBox): Another widget to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.autostop_time_flag:
            self.app_obj.set_autostop_time_flag(True)
            spinbutton.set_sensitive(True)
            combo.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.autostop_time_flag:
            self.app_obj.set_autostop_time_flag(False)
            spinbutton.set_sensitive(False)
            combo.set_sensitive(False)


    def on_autostop_time_combo_changed(self, combo):

        """Called from a callback in self.setup_scheduling_stop_tab().

        Sets the time unit at which a download operation is auto-stopped.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.app_obj.set_autostop_time_unit(model[tree_iter][0])


    def on_autostop_time_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_scheduling_stop_tab().

        Sets the time value at which a download operation is auto-stopped.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_autostop_time_value(spinbutton.get_value())


    def on_autostop_videos_button_toggled(self, checkbutton, spinbutton):

        """Called from callback in self.setup_scheduling_stop_tab().

        Enables/disables auto-stopping a download operation after a certain
        number of videos.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): Another widget to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.autostop_videos_flag:
            self.app_obj.set_autostop_videos_flag(True)
            spinbutton.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.autostop_videos_flag:
            self.app_obj.set_autostop_videos_flag(False)
            spinbutton.set_sensitive(False)


    def on_autostop_videos_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_scheduling_stop_tab().

        Sets the number of videos at which a download operation is
        auto-stopped.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_autostop_videos_value(spinbutton.get_value())


    def on_backup_button_toggled(self, radiobutton, value):

        """Called from callback in self.setup_files_backups_tab().

        Updates IVs in the main application.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            value (str): The new value of the IV

        """

        if radiobutton.get_active():
            self.app_obj.set_db_backup_mode(value)


    def on_bandwidth_button_toggled(self, checkbutton, alt_flag=False):

        """Called from callback in self.setup_operations_limits_tab().

        Enables/disables the download speed limit. Toggling the corresponding
        Gtk.CheckButton in the Progress tab sets the IV (and makes sure the two
        checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            alt_flag (bool): If True, the alternative limit is toggled

        """

        main_win_obj = self.app_obj.main_win_obj

        if not alt_flag:

            other_flag = main_win_obj.bandwidth_checkbutton.get_active()

            if (checkbutton.get_active() and not other_flag):
                main_win_obj.bandwidth_checkbutton.set_active(True)
            elif (not checkbutton.get_active() and other_flag):
                main_win_obj.bandwidth_checkbutton.set_active(False)

        else:

            # Alternative limits. There is no second widget to toggle
            if checkbutton.get_active() \
            and not self.app_obj.alt_bandwidth_apply_flag:
                self.app_obj.set_alt_bandwidth_apply_flag(True)
            elif not checkbutton.get_active() \
            and self.app_obj.alt_bandwidth_apply_flag:
                self.app_obj.set_alt_bandwidth_apply_flag(False)


    def on_bandwidth_spinbutton_changed(self, spinbutton, alt_flag=False):

        """Called from callback in self.setup_operations_limits_tab().

        Sets the simultaneous download limit. Setting the value of the
        corresponding Gtk.SpinButton in the Progress tab sets the IV (and
        makes sure the two spinbuttons have the same value).

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

            alt_flag (bool): If True, the alternative limit is set

        """

        if not alt_flag:

            self.app_obj.main_win_obj.bandwidth_spinbutton.set_value(
                spinbutton.get_value(),
            )

        else:

            # Alternative limits. There is no second widget to toggle
            self.app_obj.set_alt_bandwidth(int(spinbutton.get_value()))


    def on_block_livestreams_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Enables/disables checking/downloading livestreams by yt-dlp

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.block_livestreams_flag:
            self.app_obj.set_block_livestreams_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.block_livestreams_flag:
            self.app_obj.set_block_livestreams_flag(False)


    def on_check_limit_changed(self, entry):

        """Called from callback in self.setup_operations_block_tab().

        Sets the limit at which a download operation will stop checking a
        channel or playlist.

        Args:

            entry (Gtk.Entry): The widget changed

        """

        text = entry.get_text()
        if text.isdigit() and int(text) >= 0:
            self.app_obj.set_operation_check_limit(int(text))


    def on_clickable_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables clickable channel/playlist names in the Video
        Catalogue.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.catalogue_clickable_container_flag:
            self.app_obj.set_catalogue_clickable_container_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.catalogue_clickable_container_flag:
            self.app_obj.set_catalogue_clickable_container_flag(False)


    def on_child_process_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of child process exit error messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_child_process_exit_flag:
            self.app_obj.set_ignore_child_process_exit_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_child_process_exit_flag:
            self.app_obj.set_ignore_child_process_exit_flag(False)


    def on_clear_descrips_button_clicked(self, button):

        """Called from a callback in self.setup_files_update_tab().

        For every video in the database, clears the description (but doesn't
        modify the description file itself).

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Update'
        )

        video_count = 0
        update_count = 0

        for media_data_obj in self.app_obj.media_reg_dict.values():

            if isinstance(media_data_obj, media.Video):

                video_count += 1

                if media_data_obj.descrip is not None \
                and media_data_obj.descrip != '':
                    update_count += 1

                media_data_obj.reset_video_descrip()

        # Confirm the result
        msg = _('Total videos:') + ' ' + str(video_count) + '\n\n' \
        + _('Videos updated:') + ' ' + str(update_count)

        self.app_obj.dialogue_manager_obj.show_simple_msg_dialogue(
            msg,
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_clipboard_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_dialogues_tab().

        Enables/disables copying from the system clipboard in various dialogue
        windows.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.dialogue_copy_clipboard_flag:
            self.app_obj.set_dialogue_copy_clipboard_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.dialogue_copy_clipboard_flag:
            self.app_obj.set_dialogue_copy_clipboard_flag(False)


    def on_clips_dir_button_toggled(self, radiobutton):

        """Called from callback in self.setup_operations_clips_tab().

        Toggles between moving clips to the Video Clips folder.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if radiobutton.get_active():
            self.app_obj.set_split_video_clips_dir_flag(True)
        else:
            self.app_obj.set_split_video_clips_dir_flag(False)


    def on_clips_dl_mode_button_toggled(self, radiobutton):

        """Called from callback in self.setup_operations_clips_tab().

        Toggles between download clips with FFmpeg and yt-dlp.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if radiobutton.get_active():
            self.app_obj.set_video_timestamps_dl_mode('ffmpeg')
        else:
            self.app_obj.set_video_timestamps_dl_mode('downloader')


    def on_close_to_tray_toggled(self, checkbutton, checkbutton2):

        """Called from a callback in self.setup_windows_system_tray_tab().

        Enables/disables closing to the system tray, rather than closing the
        application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.close_to_tray_flag:
            self.app_obj.set_close_to_tray_flag(True)
            checkbutton2.set_sensitive(True)
        elif not checkbutton.get_active() \
        and self.app_obj.close_to_tray_flag:
            self.app_obj.set_close_to_tray_flag(False)
            checkbutton2.set_active(False)
            checkbutton2.set_sensitive(False)


    def on_complex_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_videos_tab().

        Switches between simple/complex views in the Video Index.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        redraw_flag = False
        if checkbutton.get_active() and not self.app_obj.complex_index_flag:
            self.app_obj.set_complex_index_flag(True)
            redraw_flag = True
        elif not checkbutton.get_active() and self.app_obj.complex_index_flag:
            self.app_obj.set_complex_index_flag(False)
            redraw_flag = True

        if redraw_flag:
            # Redraw the Video Index and the Video Catalogue (since nothing in
            #   the Video Index will be selected)
            self.app_obj.main_win_obj.video_index_catalogue_reset()


    def on_confirm_url_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_urls_tab().

        Enables/disables prompting user for confirmation before modifying a
        URL.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.url_change_confirm_flag:
            self.app_obj.set_url_change_confirm_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.url_change_confirm_flag:
            self.app_obj.set_url_change_confirm_flag(False)


    def on_container_name_edited(self, widget, path, text, treeview, \
    checkbutton):

        """Called from callback in self.setup_files_urls_tab().

        Updates the name of a channel/playlist, prompting the user for
        confirmation first, if required.

        Args:

            widget (Gtk.CellRendererText): The widget clicked

            path (int): Path to the treeview line that was edited

            text (str): The new contents of the cell

            treeview (Gtk.TreeView): The parent treeview

            checkbutton (Gtk.CheckButton): If active, prompt the user before
                updating URLs

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > URLs'
        )

        # Check the entered text is a valid name
        if text == '' \
        or re.search(r'^\s*$', text) \
        or not self.app_obj.check_container_name_is_legal(text):

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('The name \'{0}\' is not allowed').format(text),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        # Get the dbid for the selected line's channel/playlist
        model = treeview.get_model()
        tree_iter = model.get_iter(path)
        if tree_iter is not None:

            dbid = model[tree_iter][0]
            media_data_obj = self.app_obj.media_reg_dict[dbid]

            if media_data_obj.name == text:
                # No change
                return

            # Check that the parent folder doesn't already have a container
            #   with the same name
            if (
                media_data_obj.parent_obj is not None \
                and self.app_obj.find_duplicate_name_in_container(
                    media_data_obj.parent_obj,
                    text,
                )
            ) or (
                media_data_obj.parent_obj is None \
                and self.app_obj.find_duplicate_name_in_container(None, text)
            ):
                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _(
                        'There is already a channel, playlist or folder' \
                        + ' called \'{0}\'',
                    ).format(text),
                    'error',
                    'ok',
                    self,           # Parent window is this window
                )

                return

            if not checkbutton.get_active():

                # Rename without confirmation
                if self.app_obj.rename_container_silently(
                    media_data_obj,
                    text,
                ):
                    model[tree_iter][3] = text

            else:

                # Seek confirmation before renaming
                if isinstance(media_data_obj, media.Channel):
                    msg = _('Are you sure you want to rename this channel?')
                elif isinstance(media_data_obj, media.Playlist):
                    msg = _('Are you sure you want to rename this playlist?')
                elif isinstance(media_data_obj, media.Folder):
                    msg = _('Are you sure you want to rename this folder?')

                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    msg,
                    'question',
                    'yes-no',
                    self,           # Parent window is this window
                    {
                        'yes': 'update_container_name',
                        'data': [model, tree_iter, media_data_obj, text],
                    },
                )


    def on_container_url_edited(self, widget, path, text, treeview, \
    checkbutton):

        """Called from callback in self.setup_files_urls_tab().

        Updates the URL for a channel/playlist, prompting the user for
        confirmation first, if required.

        Args:

            widget (Gtk.CellRendererText): The widget clicked

            path (int): Path to the treeview line that was edited

            text (str): The new contents of the cell

            treeview (Gtk.TreeView): The parent treeview

            checkbutton (Gtk.CheckButton): If active, prompt the user before
                updating URLs

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > URLs'
        )

        # Check the entered text is a valid URL
        if not ttutils.check_url(text):
            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('That is not a valid URL'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        # Get the dbid for the selected line's channel/playlist
        model = treeview.get_model()
        tree_iter = model.get_iter(path)
        if tree_iter is not None:

            dbid = model[tree_iter][0]
            media_data_obj = self.app_obj.media_reg_dict[dbid]

            if not checkbutton.get_active():
                media_data_obj.set_source(text)
                model[tree_iter][3] = text

            else:

                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _('Are you sure you want to update the URL?'),
                    'question',
                    'yes-no',
                    self,           # Parent window is this window
                    {
                        'yes': 'update_container_url',
                        'data': [model, tree_iter, media_data_obj, text],
                    },
                )


    def on_container_url_multiple_edited(self, button, entry, entry2, \
    treeview):

        """Called from callback in self.setup_files_urls_tab().

        Search and replace in the source URLs of the selected channels/
        playlists.

        Args:

            button (Gtk.Button): The widget clicked

            entry, entry2 (Gtk.Entry): Widgets containing the search/replace
                text

            treeview (Gtk.TreeView): The parent treeview

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + 'System preferences > Files > URLs'
        )

        # Check the pattern (in 'entry') is valid ('entry2' can contain any
        #   text, including no text at all)
        pattern = entry.get_text()
        subst = entry2.get_text()

        if not self.app_obj.url_change_regex_flag:

            if pattern == '':
                return

        else:

            try:
                re.compile(pattern)

            except re.error():
                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _('The regex is invalid'),
                    'error',
                    'ok',
                    self,           # Parent window is this window
                )

                return

        # Get the media data objects for each selected line
        media_list = []
        mod_path_list = []

        selection = treeview.get_selection()
        this_tuple = selection.get_selected_rows()
        # (Confusingly, first item in the tuple is the Gtk.ListStore)
        model = this_tuple[0]
        for path in this_tuple[1]:

            tree_iter = model.get_iter(path)
            if tree_iter is not None:

                dbid = model[tree_iter][0]
                if dbid in self.app_obj.media_reg_dict:

                    media_data_obj = self.app_obj.media_reg_dict[dbid]
                    if media_data_obj.source is not None:
                        media_list.append(media_data_obj)
                        mod_path_list.append(path)

        if not media_list:
            # Nothing selected (or channels/playlists removed)
            return

        # Get confirmation, before proceeding
        if not self.app_obj.url_change_confirm_flag:

            self.app_obj.update_container_url_multiple(
                [
                    self,
                    model,
                    mod_path_list,
                    media_list,
                    pattern,
                    subst,
                ],
            )

        else:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Are you sure you want to update these URLs?'),
                'question',
                'yes-no',
                self,           # Parent window is this window
                {
                    'yes': 'update_container_url_multiple',
                    'data': \
                    [
                        self,
                        model,
                        mod_path_list,
                        media_list,
                        pattern,
                        subst,
                    ],
                },
            )


    def on_convert_from_button_toggled(self, radiobutton, mode):

        """Called from callback in self.setup_operations_prefs_tab().

        Set what happens when downloading a media.Video object whose URL
        represents a channel/playlist.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            mode (str): The new value for the IV: 'disable', 'multi',
                'channel' or 'playlist'

        """

        if radiobutton.get_active():
            self.app_obj.set_operation_convert_mode(mode)


    def on_copy_thumb_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables copying the original video's thumbnail after splitting
        a video.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.split_video_copy_thumb_flag:
            self.app_obj.set_split_video_copy_thumb_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.split_video_copy_thumb_flag:
            self.app_obj.set_split_video_copy_thumb_flag(False)


    def on_copyright_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_websites_tab().

        Enables/disables ignoring of YouTube copyright errors messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_yt_copyright_flag:
            self.app_obj.set_ignore_yt_copyright_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_yt_copyright_flag:
            self.app_obj.set_ignore_yt_copyright_flag(False)


    def on_custom_colour_button_clicked(self, colorbutton, key):

        """Called by self.setup_windows_colours_tab_add_row()

        After the colour selection dialogue has closed, update the custom
        background colour used in the Video Catalogue.

        Args:

            colorbutton (Gtk.ColorButton): The widget clicked

            key (str): One of the keys in mainapp.TartubeApp.custom_bg_table

        """

        rgba_obj = colorbutton.get_color()

        # Update IVs. Insert a standard value for alpha, so the user doesn't
        #   have to think about it
        self.app_obj.set_custom_bg(
            key,
            (rgba_obj.red / 65536),
            (rgba_obj.green / 65536),
            (rgba_obj.blue / 65536),
            0.20,
        )

        # Update the custom colour button to show the colour with its true
        #   alpha value
        mini_list = self.app_obj.custom_bg_table[key]
        custom_rgba_obj = Gdk.RGBA(
            mini_list[0],
            mini_list[1],
            mini_list[2],
            mini_list[3],
        )
        colorbutton.set_rgba(custom_rgba_obj)

        # Update the Video Catalogue to show the new colour
        if self.app_obj.main_win_obj.video_index_current_dbid is not None:
            self.app_obj.main_win_obj.video_catalogue_redraw_all(
                self.app_obj.main_win_obj.video_index_current_dbid,
            )


    def on_custom_dl_add_button_clicked(self, button, entry):

        """Called from callback in self.setup_operations_custom_dl_tab().

        Adds a new downloads.CustomDLManager object.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Widget providiing a name for the new object

        """

        name = entry.get_text()
        if name == '':
            return

        new_obj = self.app_obj.create_custom_dl_manager(name)

        # Update the treeview
        self.setup_operations_custom_dl_tab_update_treeview()
        # Empty the entry box
        entry.set_text('')

        # All other widgets for creating an custom download manager object open
        #   its edit window, so we'll do the same here
        CustomDLEditWin(self.app_obj, new_obj)


    def on_custom_dl_clone_button_clicked(self, button, treeview):

        """Called from callback in self.setup_operations_custom_dl_tab().

        Clones the selected downloads.CustomDLManager object.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.custom_dl_reg_dict:

                    new_obj = self.app_obj.clone_custom_dl_manager(
                        self.app_obj.custom_dl_reg_dict[uid],
                    )

                    # Open an edit window, so the user can set the cloned
                    #   object's name
                    CustomDLEditWin(self.app_obj, new_obj)


    def on_custom_dl_delete_button_clicked(self, button, treeview):

        """Called from callback in self.setup_operations_custom_dl_tab().

        Deletes the selected downloads.CustomDLManager object, if allowed.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Operations > Custom'
        )

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:

            return

        uid = model[this_iter][0]
        if not uid in self.app_obj.custom_dl_reg_dict:
            return

        custom_dl_obj = self.app_obj.custom_dl_reg_dict[uid]
        if self.app_obj.general_custom_dl_obj \
        and self.app_obj.general_custom_dl_obj == custom_dl_obj:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('The default custom download manager cannot be deleted'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        # Prompt for confirmation
        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _('Are you sure you want to delete this custom download manager?'),
            'question',
            'yes-no',
            self,           # Parent window is this window
            {
                'yes': 'delete_custom_dl_manager',
                # Specified manager
                'data': custom_dl_obj,
            },
        )


    def on_custom_dl_edit_button_clicked(self, button, treeview):

        """Called from callback in self.setup_operations_custom_dl_tab().

        Opens an edit window for the selected downloads.CustomDLManager object.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.custom_dl_reg_dict:

                    CustomDLEditWin(
                        self.app_obj,
                        self.app_obj.custom_dl_reg_dict[uid],
                    )


    def on_custom_dl_export_button_clicked(self, button, treeview):

        """Called from callback in self.setup_operations_custom_dl_tab().

        Exports the selected downloads.CustomDLManager object to a JSON file.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.custom_dl_reg_dict:

                    self.app_obj.export_custom_dl_manager(
                        self.app_obj.custom_dl_reg_dict[uid],
                    )


    def on_custom_dl_import_button_clicked(self, button, entry):

        """Called from callback in self.setup_operations_custom_dl_tab().

        Imports a JSON file and creates a new downloads.CustomDLManager for it.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Widget providiing a name for the new object.
                If the entry is empty, then the name specified by the JSON file
                itself is used

        """

        self.app_obj.import_custom_dl_manager(entry.get_text())

        # Update the treeview
        self.setup_operations_custom_dl_tab_update_treeview()
        # Empty the entry box
        entry.set_text('')


    def on_custom_dl_use_classic_button_clicked(self, button, treeview):

        """Called from callback in self.setup_operations_custom_dl_tab().

        Applies the selected downloads.CustomDLManager object to the Classic
        Mode tab.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.custom_dl_reg_dict:

                    custom_dl_obj = self.app_obj.custom_dl_reg_dict[uid]

                    # If this is already the custom download manager for the
                    #   Classic Mode tab, then remove it (but don't delete the
                    #   object itself)
                    if self.app_obj.classic_custom_dl_obj \
                    and self.app_obj.classic_custom_dl_obj == custom_dl_obj:

                        self.app_obj.disapply_classic_custom_dl_manager()

                    else:

                        self.app_obj.apply_classic_custom_dl_manager(
                            self.app_obj.custom_dl_reg_dict[uid],
                        )

        # Update the treeview
        self.setup_operations_custom_dl_tab_update_treeview()


    def on_custom_textview_changed(self, textbuffer):

        """Called from callback in self.setup_windows_websites_tab().

        Sets the custom of list of ignorable error messages.

        Args:

            textbuffer (Gtk.TextBuffer): The buffer belonging to the textview
                whose contents has been modified

        """

        text = textbuffer.get_text(
            textbuffer.get_start_iter(),
            textbuffer.get_end_iter(),
            # Don't include hidden characters
            False,
        )

        # Filter out empty lines
        line_list = text.splitlines()
        mod_list = []
        for line in line_list:
            if re.search(r'\S', line):
                mod_list.append(line)

        # Apply the changes
        self.app_obj.set_ignore_custom_msg_list(mod_list)


    def on_custom_title_changed(self, entry):

        """Called from callback in self.setup_operations_clips_tab().

        Sets the custom title for split videos.

        Args:

            entry (Gtk.Entry): The widget clicked

        """

        text = entry.get_text()
        if text == '':
            self.app_obj.set_split_video_custom_title(
                self.app_obj.split_video_generic_title,
            )
        else:
            self.app_obj.set_split_video_custom_title(text)

        entry.set_text(self.app_obj.split_video_custom_title)


    def on_data_block_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of data block error messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_data_block_error_flag:
            self.app_obj.set_ignore_data_block_error_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_data_block_error_flag:
            self.app_obj.set_ignore_data_block_error_flag(False)


    def on_data_check_button_clicked(self, button):

        """Called from callback in self.setup_files_database_tab().

        Checks the Tartube database for inconsistencies, and fixes them.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.app_obj.check_integrity_db(
            False,      # Don't run silently; prompt the user before repairing
            self,       # This window, not the main window, is the parent
        )


    def on_data_dir_change_button_clicked(self, button):

        """Called from callback in self.setup_files_database_tab().

        Opens a window in which the user can select Tartube's data directoy.
        If the user actually selects it, call the main application to take
        action.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Database'
        )

        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Please select Tartube\'s data folder'),
            self,
            'folder',
        )

        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK:

            dialogue_manager_obj = self.app_obj.dialogue_manager_obj

            # In the past, I accidentally created a new database directory
            #   just inside an existing one, rather than switching to the
            #   existing one
            # If no database file exists, prompt the user to create a new one
            db_path = os.path.abspath(
                os.path.join(new_path, self.app_obj.db_file_name),
            )

            if not os.path.isfile(db_path):

                dialogue_manager_obj.show_msg_dialogue(
                    _(
                        'Are you sure you want to create a new database at' \
                        + ' this location?',
                    ) + '\n\n' + new_path,
                    'question',
                    'yes-no',
                    self,           # Parent window is this window
                    {
                        'yes': 'switch_db',
                        'data': [new_path, self],
                    },
                )

            else:

                # Database file already exists, so try to load it now
                self.try_switch_db(new_path, button)


    def on_data_dir_cursor_changed(self, treeview, button2, button3, button4,
    button5, button6):

        """Called by self.setup_files_database_tab().

        When a data directory in the list is selected, (de)sensitise buttons
        in response.

        Args:

            treeview (Gtk.TreeView): The widget in which a line was selected.

            button2, button3, button4, button5, button6 (Gtk.Button): Other
                widgets to be modified

        """

        selection = treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is not None and not self.app_obj.disable_load_save_flag:

            data_dir = model[tree_iter][0]

            if data_dir != self.app_obj.data_dir:
                button2.set_sensitive(True)
                button3.set_sensitive(True)
            else:
                button2.set_sensitive(False)
                button3.set_sensitive(False)

            posn = self.app_obj.data_dir_alt_list.index(data_dir)
            if posn > 0:
                button5.set_sensitive(True)
            else:
                button5.set_sensitive(False)

            if posn < (len(self.app_obj.data_dir_alt_list) - 1):
                button6.set_sensitive(True)
            else:
                button6.set_sensitive(False)

        else:

            button2.set_sensitive(False)
            button3.set_sensitive(False)
            button5.set_sensitive(False)
            button6.set_sensitive(False)

        if len(self.app_obj.data_dir_alt_list) <= 1 \
        or self.app_obj.disable_load_save_flag:
            button4.set_sensitive(False)
        else:
            button4.set_sensitive(True)


    def on_data_dir_forget_button_clicked(self, button, treeview):

        """Called from callback in self.setup_files_database_tab().

        Removes the selected the data directory from the list of alternative
        data directories.

        Args:

            button (Gtk.Button): The widget that was clicked

            treeview (Gtk.TreeView): The widget in which a line was selected.

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Database'
        )

        selection = treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:

            # Nothing selected
            return

        else:

            data_dir = model[tree_iter][0]

        # Should not be possible to click the button, when the current
        #   directory is selected, but we'll check anyway
        if data_dir == self.app_obj.data_dir:
            return

        # Prompt the user for confirmation. If the user confirms, this window
        #   is reset to update the treeview
        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _('Are you sure you want to forget this database?'),
            'question',
            'yes-no',
            self,           # Parent window is this window
            {
                'yes': 'forget_db',
                'data': [data_dir, self],
            },
        )


    def on_data_dir_forget_all_button_clicked(self, button, treeview):

        """Called from callback in self.setup_files_database_tab().

        Removes all data directories from the list of alternatives, except for
        the current one.

        Args:

            button (Gtk.Button): The widget that was clicked

            treeview (Gtk.TreeView): The widget in which a line was selected.

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Database'
        )

        # Should not be possible to click the button, when the list contains
        #   no alternatives but the current one, but we'll check anyway
        if len(self.app_obj.data_dir_alt_list) <= 1:
            return

        # Prompt the user for confirmation. If the user confirms, this window
        #   is reset to update the treeview
        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _(
            'Are you sure you want to forget all databases except the' \
            + ' current one?',
            ),
            'question',
            'yes-no',
            self,           # Parent window is this window
            {
                'yes': 'forget_all_db',
                'data': self,
            },
        )


    def on_data_dir_move_down_button_clicked(self, button, treeview, \
    liststore, button2):

        """Called from callback in self.setup_files_database_tab().

        Moves the selected data directory down one position in the list of
        alternative data directories.

        Args:

            button (Gtk.Button): The widget that was clicked (the down button)

            treeview (Gtk.TreeView): The widget in which a line was selected

            liststore (Gtk.ListStore): The treeview's liststore

            button2 (Gtk.Button): The up button

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            # Nothing selected
            return

        # (Keeping track of the first/last selected items helps us to
        #   (de)sensitise buttons, in a moment)
        first_item = None
        last_item = None

        path_list.reverse()

        for path in path_list:

            this_iter = model.get_iter(path)
            last_item = model[this_iter][0]
            if first_item is None:
                first_item = model[this_iter][0]

            if model.iter_next(this_iter):

                liststore.move_after(
                    this_iter,
                    model.iter_next(this_iter),
                )

            else:

                # If the first item won't move up, then successive items will
                #   be moved above this one (which is not what we want)
                break

        # Update the IV
        dir_list = []
        for row in liststore:
            dir_list.append(row[0])

        self.app_obj.set_data_dir_alt_list(dir_list)

        # (De)sensitise the button(s), if required
        if dir_list.index(first_item) == 0:
            button2.set_sensitive(False)
        else:
            button2.set_sensitive(True)

        if dir_list.index(last_item) == (len(dir_list) - 1):
            button.set_sensitive(False)
        else:
            button.set_sensitive(True)


    def on_data_dir_move_up_button_clicked(self, button, treeview, liststore,
    button2):

        """Called from callback in self.setup_files_database_tab().

        Moves the selected data directory up one position in the list of
        alternative data directories.

        Args:

            button (Gtk.Button): The widget that was clicked (the up button)

            treeview (Gtk.TreeView): The widget in which a line was selected

            liststore (Gtk.ListStore): The treeview's liststore

            button2 (Gtk.Button): The down button

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            # Nothing selected
            return

        # (Keeping track of the first/last selected items helps us to
        #   (de)sensitise buttons, in a moment)
        first_item = None
        last_item = None

        # Move the selected items up
        for path in path_list:

            this_iter = model.get_iter(path)
            last_item = model[this_iter][0]
            if first_item is None:
                first_item = model[this_iter][0]

            if model.iter_previous(this_iter):

                liststore.move_before(
                    this_iter,
                    model.iter_previous(this_iter),
                )

            else:

                # If the first item won't move up, then successive items will
                #   be moved above this one (which is not what we want)
                break

        # Update the IV
        dir_list = []
        for row in liststore:
            dir_list.append(row[0])

        self.app_obj.set_data_dir_alt_list(dir_list)

        # (De)sensitise the button(s), if required
        if dir_list.index(first_item) == 0:
            button.set_sensitive(False)
        else:
            button.set_sensitive(True)

        if dir_list.index(last_item) == (len(dir_list) - 1):
            button2.set_sensitive(False)
        else:
            button2.set_sensitive(True)


    def on_data_dir_switch_button_clicked(self, button, button2, treeview):

        """Called from callback in self.setup_files_database_tab().

        Changes the Tartube data directory to the one selected in the
        textview.

        Args:

            button (Gtk.Button): The widget clicked

            button2 (Gtk.Button): Another button to be possibly desensitised

            treeview (Gtk.TreeView): A widget in which one file path is
                selected (maybe)

            entry, entry2 (Gtk.Entry): Other widgets to be modified

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Database'
        )

        selection = treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:

            # Nothing selected
            return

        else:

            data_dir = model[tree_iter][0]

        # Should not be possible to click the button, when the current
        #   directory is selected, but we'll check anyway
        if data_dir == self.app_obj.data_dir:
            return

        # If no database file exists, prompt the user to create a new one
        db_path = os.path.abspath(
            os.path.join(data_dir, self.app_obj.db_file_name),
        )

        if not os.path.isfile(db_path):

            self.app_obj.dialogue_manager_obj.show_simple_msg_dialogue(
                _(
                    'No database exists at this location:',
                ) + '\n\n' + data_dir + '\n\n' + _(
                    'Do you want to create a new one?',
                ),
                'question',
                'yes-no',
                self,           # Parent window is this window
                {
                    'yes': 'switch_db',
                    'data': [data_dir, self],
                },
            )

        else:

            # Database file already exists, so try to load it now
            self.try_switch_db(data_dir, button2)


    def on_delete_asap_button_toggled(self, radiobutton):

        """Called from callback in self.setup_files_delete_tab().

        Enables/disables automatic deletion/removal of videos after every
        download operation.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if not radiobutton.get_active() \
        and not self.app_obj.auto_delete_asap_flag:
            self.app_obj.set_auto_delete_asap_flag(True)
        elif radiobutton.get_active() \
        and self.app_obj.auto_delete_asap_flag:
            self.app_obj.set_auto_delete_asap_flag(False)


    def on_default_avconv_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_ffmpeg_tab().

        Sets the path to the avconv binary to the default path.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        self.app_obj.set_avconv_path(self.app_obj.default_avconv_path)
        entry.set_text(self.app_obj.avconv_path)


    def on_default_colour_button_clicked(self, colorbutton, event_button, \
    colorbutton2, key):

        """Called by self.setup_windows_colours_tab_add_row()

        After clicking the default colour button, don't allow the usual
        colour selection dialogue to open. Instead, update the button showing
        the custom colour.

        Args:

            colorbutton (Gtk.ColorButton): The widget clicked

            event_button (Gdk.EventButton): Ignored

            colorbutton2 (Gtk.ColorButton): Another widget to u pdate

            key (str): One of the keys in mainapp.TartubeApp.custom_bg_table

        """

        # Update IVs
        self.app_obj.reset_custom_bg(key)

        # Update the custom colour button
        mini_list = self.app_obj.custom_bg_table[key]
        custom_rgba_obj = Gdk.RGBA(
            mini_list[0],
            mini_list[1],
            mini_list[2],
            mini_list[3],
        )
        colorbutton2.set_rgba(custom_rgba_obj)

        # Update the Video Catalogue to show the new colour
        if self.app_obj.main_win_obj.video_index_current_dbid is not None:
            self.app_obj.main_win_obj.video_catalogue_redraw_all(
                self.app_obj.main_win_obj.video_index_current_dbid,
            )

        # Return True so the colour selection dialogue is not opened
        return True


    def on_default_ffmpeg_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_ffmpeg_tab().

        Sets the path to the ffmpeg binary to the default path.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        self.app_obj.set_ffmpeg_path(self.app_obj.default_ffmpeg_path)
        entry.set_text(self.app_obj.ffmpeg_path)


    def on_delete_shutdown_button_toggled(self, checkbutton, checkbutton2):

        """Called from callback in self.setup_files_temp_folders_tab().

        Enables/disables emptying temporary folders when Tartube shuts down.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to be modified

        """

        if checkbutton.get_active() \
        and not self.app_obj.delete_on_shutdown_flag:
            self.app_obj.set_delete_on_shutdown_flag(True)
            checkbutton2.set_sensitive(False)

        elif not checkbutton.get_active() \
        and self.app_obj.delete_on_shutdown_flag:
            self.app_obj.set_delete_on_shutdown_flag(False)
            checkbutton2.set_sensitive(True)


    def on_delete_watched_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_delete_tab().

        Enables/disables automatic deletion/removal of videos, but only those
        that have been watched.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.auto_delete_watched_flag:
            self.app_obj.set_auto_delete_watched_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.auto_delete_watched_flag:
            self.app_obj.set_auto_delete_watched_flag(False)


    def on_dialogue_button_toggled(self, radiobutton, mode):

        """Called from callback in self.setup_operations_actions_tab().

        Sets whether a desktop notification, dialogue window or neither should
        be shown to the user at the end of a download/update/refresh/info/tidy
        operation.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            mode (str): The new value for the IV: 'default', 'desktop' or
                'dialogue'

        """

        if radiobutton.get_active():
            self.app_obj.set_operation_dialogue_mode(mode)


    def on_dialogue_disable_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_dialogues_tab().

        Enables/disables message dialogue windows (for testing purposes).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.dialogue_disable_msg_flag:
            self.app_obj.set_dialogue_disable_msg_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.dialogue_disable_msg_flag:
            self.app_obj.set_dialogue_disable_msg_flag(False)


    def on_disable_dl_all_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables the 'Download all' buttons in the main window toolbar
        and in the Videos tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.disable_dl_all_flag:
            self.app_obj.set_disable_dl_all_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.disable_dl_all_flag:
            self.app_obj.set_disable_dl_all_flag(False)


    def on_disable_monospaced_button_toggled(self, checkbutton):

        """Called from callback in self.setup_output_outputtab_tab().

        Enables/disables monospace fonts in the Output tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.disable_monospaced_output_flag:
            self.app_obj.set_disable_monospaced_output_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.disable_monospaced_output_flag:
            self.app_obj.set_disable_monospaced_output_flag(False)


    def on_disk_stop_button_toggled(self, checkbutton, spinbutton):

        """Called from a callback in self.setup_files_device_tab().

        Enables/disables halting a download operation when the system is
        running out of disk space.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.CheckButton): Another widget to be (de)sensitised

        """

        if checkbutton.get_active() \
        and not self.app_obj.disk_space_stop_flag:
            self.app_obj.set_disk_space_stop_flag(True)
            spinbutton.set_sensitive(True)
        elif not checkbutton.get_active() \
        and self.app_obj.disk_space_stop_flag:
            self.app_obj.set_disk_space_stop_flag(False)
            spinbutton.set_sensitive(False)


    def on_disk_stop_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_files_device_tab().

        Sets the amount of free disk space below which download operations
        will be halted.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_disk_space_stop_limit(spinbutton.get_value())


    def on_disk_warn_button_toggled(self, checkbutton, spinbutton):

        """Called from a callback in self.setup_files_device_tab().

        Enables/disables warnings when the system is running out of disk space.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.CheckButton): Another widget to be (de)sensitised

        """

        if checkbutton.get_active() \
        and not self.app_obj.disk_space_warn_flag:
            self.app_obj.set_disk_space_warn_flag(True)
            spinbutton.set_sensitive(True)
        elif not checkbutton.get_active() \
        and self.app_obj.disk_space_warn_flag:
            self.app_obj.set_disk_space_warn_flag(False)
            spinbutton.set_sensitive(False)


    def on_disk_warn_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_files_device_tab().

        Sets the amount of free disk space below which a warning will be
        issued.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_disk_space_warn_limit(spinbutton.get_value())


    def on_dl_limit_changed(self, entry):

        """Called from callback in self.setup_operations_block_tab().

        Sets the limit at which a download operation will stop downloading a
        channel or playlist.

        Args:

            entry (Gtk.Entry): The widget changed

        """

        text = entry.get_text()
        if text.isdigit() and int(text) >= 0:
            self.app_obj.set_operation_download_limit(int(text))


    def on_drag_error_msg_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the error/warning message when dragging
        and dropping from the Errors/Warnings tab to an external application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_error_msg_flag:
            self.app_obj.set_drag_error_msg_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_error_msg_flag:
            self.app_obj.set_drag_error_msg_flag(False)


    def on_drag_error_name_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the video/channel/playlist name when
        dragging and dropping from the Errors/Warnings tab to an external
        application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_error_name_flag:
            self.app_obj.set_drag_error_name_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_error_name_flag:
            self.app_obj.set_drag_error_name_flag(False)


    def on_drag_error_path_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the video/channel/playlist path when
        dragging and dropping from the Errors/Warnings tab to an external
        application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_error_path_flag:
            self.app_obj.set_drag_error_path_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_error_path_flag:
            self.app_obj.set_drag_error_path_flag(False)


    def on_drag_error_separator_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables adding a separator before each video/channel/playlsit
        when dragging and dropping from the Errors/Warnings tab to an external
        application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_error_separator_flag:
            self.app_obj.set_drag_error_separator_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_error_separator_flag:
            self.app_obj.set_drag_error_separator_flag(False)


    def on_drag_error_source_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the video/channel/playlist URL when
        dragging and dropping from the Errors/Warnings tab to an external
        application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_error_source_flag:
            self.app_obj.set_drag_error_source_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_error_source_flag:
            self.app_obj.set_drag_error_source_flag(False)


    def on_drag_msg_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring of any errors/warnings associated with
        the video when dragging and dropping to an external application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_video_msg_flag:
            self.app_obj.set_drag_video_msg_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_video_msg_flag:
            self.app_obj.set_drag_video_msg_flag(False)


    def on_drag_name_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the video's name when dragging and
        dropping to an external application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_video_name_flag:
            self.app_obj.set_drag_video_name_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_video_name_flag:
            self.app_obj.set_drag_video_name_flag(False)


    def on_drag_name_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the video's name when dragging and
        dropping to an external application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_video_name_flag:
            self.app_obj.set_drag_video_name_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_video_name_flag:
            self.app_obj.set_drag_video_name_flag(False)


    def on_drag_path_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the video's path when dragging and
        dropping to an external application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_video_path_flag:
            self.app_obj.set_drag_video_path_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_video_path_flag:
            self.app_obj.set_drag_video_path_flag(False)


    def on_drag_separator_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables adding a separator before each video, when dragging
        video data into an external application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_video_separator_flag:
            self.app_obj.set_drag_video_separator_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_video_separator_flag:
            self.app_obj.set_drag_video_separator_flag(False)


    def on_drag_source_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the video's source URL when dragging and
        dropping to an external application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_video_source_flag:
            self.app_obj.set_drag_video_source_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_video_source_flag:
            self.app_obj.set_drag_video_source_flag(False)


    def on_drag_thumb_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_drag_tab().

        Enables/disables transferring the video thumbnail's path when dragging
        and dropping to an external application.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.drag_thumb_path_flag:
            self.app_obj.set_drag_thumb_path_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.drag_thumb_path_flag:
            self.app_obj.set_drag_thumb_path_flag(False)


    def on_dump_db_button_clicked(self, button, treeview):

        """Called from callback in self.setup_files_database_tab().

        Prompts the user to select a database, then dumps it to JSON.

        The code is here, rather than in mainapp.TartubeApp, so that dialogue
        windows can use this preferences window as the parent.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview showing recent data folders

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Database'
        )

        # Prompt the user to select a database file
        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Select a Tartube database file'),
            self,
            'open',
        )

        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            db_path = dialogue_win.get_filename()

        dialogue_win.destroy()

        if response != Gtk.ResponseType.OK or not db_path:
            return

        # Try to load it, ignoring any lockfiles that might be in place
        try:
            fh = open(db_path, 'rb')
            load_dict = pickle.load(fh)
            fh.close()

        except:
            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('This file is not loadable (might be corrupted)'),
                'error',
                'ok',
                self,
            )

            return

        if not 'container_reg_dict' in load_dict \
        or not 'media_reg_dict' in load_dict:
            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('This file does is not compatible with Tartube'),
                'error',
                'ok',
                self,
            )

            return

        elif len(load_dict['container_reg_dict']) == 0:
            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('This file was loaded, but is empty'),
                'error',
                'ok',
                self,
            )

            return

        # Prepare a dictionary in the same form exported by
        #   mainapp.TartubeApp.export_from_db()
        container_reg_dict = load_dict['container_reg_dict']
        local = ttutils.get_local_time()
        db_dict = {}
        count = 0

        for dbid in self.app_obj.container_reg_dict.keys():

            if not dbid in load_dict['media_reg_dict']:
                continue

            media_data_obj = load_dict['media_reg_dict'][dbid]
            # (Don't export folders; just export channels/playlists as a flat
            #   dictionary)
            if isinstance(media_data_obj, media.Channel) \
            or isinstance(media_data_obj, media.Playlist):

                count += 1
                mini_dict = {
                    'dbid': count,
                    'vid': None,
                    'name': media_data_obj.name,
                    'nickname': media_data_obj.nickname,
                    'file': None,
                    'source': media_data_obj.source,
                    'db_dict': {},
                }

                if isinstance(media_data_obj, media.Channel):
                    mini_dict['type'] = 'channel'
                else:
                    mini_dict['type'] = 'playlist'

                db_dict[count] = mini_dict

        export_dict = {
            # Metadata
            'script_name': __main__.__packagename__,
            'script_version': __main__.__version__,
            'save_date': str(local.strftime('%d %b %Y')),
            'save_time': str(local.strftime('%H:%M:%S')),
            'file_type': 'db_export',
            # Data
            'db_dict': db_dict,
        }

        # Try to save the export file
        export_path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.realpath(db_path)),
                self.app_obj.export_json_file_name,
            ),
        )

        try:
            with open(export_path, 'w') as outfile:
                json.dump(export_dict, outfile, indent=4)

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Database export file saved to:') \
                + '\n\n' + export_path,
                'info',
                'ok',
                self,
            )

        except Exception as e:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Failed to save the database export file:') \
                + '\n\n' + str(e),
                'error',
                'ok',
                self,
            )


    def on_enable_livestreams_button_toggled(self, checkbutton, checkbutton2,
    checkbutton3, spinbutton, spinbutton2):

        """Called from callback in self.setup_operations_livestreams_tab().

        Enables/disables livestream detection.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2, checkbutton3 (Gtk.CheckButton): Other widgets to
                sensitise/desensitise, according to the new value of the flag

            spinbutton, spinbutton2 (Gtk.SpinButton): Another widget to
                sensitise/desensitise, according to the new value of the flag

        """

        if checkbutton.get_active() \
        and not self.app_obj.enable_livestreams_flag:
            self.app_obj.set_enable_livestreams_flag(True)
            checkbutton2.set_sensitive(True)
            checkbutton3.set_sensitive(True)
            spinbutton.set_sensitive(True)
            spinbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.enable_livestreams_flag:
            self.app_obj.set_enable_livestreams_flag(False)
            checkbutton2.set_active(False)
            checkbutton2.set_sensitive(False)
            checkbutton3.set_active(False)
            checkbutton3.set_sensitive(False)
            spinbutton.set_sensitive(False)
            spinbutton2.set_sensitive(False)


    def on_expand_tree_toggled(self, checkbutton, checkbutton2):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables auto-expansion of the Video Index after a folder is
        selected (clicked).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget that must be
                modified

        """

        if checkbutton.get_active() \
        and not self.app_obj.auto_expand_video_index_flag:
            self.app_obj.set_auto_expand_video_index_flag(True)
            checkbutton2.set_sensitive(True)
        elif not checkbutton.get_active() \
        and self.app_obj.auto_expand_video_index_flag:
            self.app_obj.set_auto_expand_video_index_flag(False)
            checkbutton2.set_sensitive(False)


    def on_expand_full_tree_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables full auto-expansion of the Video Index after a folder
        is selected (clicked).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.full_expand_video_index_flag:
            self.app_obj.set_full_expand_video_index_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.full_expand_video_index_flag:
            self.app_obj.set_full_expand_video_index_flag(False)


    def on_extra_livestreams_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Enables/disables performing more frequent livestream operations when a
        livestream is due to start.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.scheduled_livestream_extra_flag:
            self.app_obj.set_scheduled_livestream_extra_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.scheduled_livestream_extra_flag:
            self.app_obj.set_scheduled_livestream_extra_flag(False)


    def on_extract_comments_button_clicked(self, button):

        """Called from callback in self.setup_files_update_tab().

        Extracts timestamps from the description of every video in the
        database.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Update'
        )

        video_count = 0
        attempt_count = 0
        success_count = 0

        for media_data_obj in self.app_obj.media_reg_dict.values():

            if isinstance(media_data_obj, media.Video):

                video_count += 1

                if not media_data_obj.comment_list:

                    attempt_count += 1
                    self.app_obj.update_video_from_json(
                        media_data_obj,
                        'comments',
                    )

                    if media_data_obj.comment_list:
                        success_count += 1

        # Redraw the Video Catalogue, at its current page
        main_win_obj = self.app_obj.main_win_obj
        main_win_obj.video_catalogue_redraw_all(
            main_win_obj.video_index_current_dbid,
            main_win_obj.catalogue_toolbar_current_page,
        )

        # Confirm the result
        msg = _('Total videos:') + ' ' + str(video_count) + '\n\n' \
        + _('Videos checked:') + ' ' + str(attempt_count) + '\n' \
        + _('Videos updated:') + ' ' + str(success_count)

        self.app_obj.dialogue_manager_obj.show_simple_msg_dialogue(
            msg,
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_extract_stamps_button_clicked(self, button):

        """Called from callback in self.setup_files_update_tab().

        Extracts timestamps from the description of every video in the
        database.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Update'
        )

        video_count = 0
        attempt_count = 0
        success_count = 0

        for media_data_obj in self.app_obj.media_reg_dict.values():

            if isinstance(media_data_obj, media.Video):

                video_count += 1

                if not media_data_obj.stamp_list \
                and media_data_obj.descrip is not None \
                and media_data_obj.descrip != '':

                    attempt_count += 1

                    media_data_obj.extract_timestamps_from_descrip(
                        self.app_obj,
                    )

                    if media_data_obj.stamp_list:

                        success_count += 1

        # Redraw the Video Catalogue, at its current page
        main_win_obj = self.app_obj.main_win_obj
        main_win_obj.video_catalogue_redraw_all(
            main_win_obj.video_index_current_dbid,
            main_win_obj.catalogue_toolbar_current_page,
        )

        # Confirm the result
        msg = _('Total videos:') + ' ' + str(video_count) + '\n\n' \
        + _('Videos checked:') + ' ' + str(attempt_count) + '\n' \
        + _('Videos updated:') + ' ' + str(success_count)

        self.app_obj.dialogue_manager_obj.show_simple_msg_dialogue(
            msg,
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_extract_descrip_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables automatically extracting timestamps from the video's
        description file.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.video_timestamps_extract_descrip_flag:
            self.app_obj.set_video_timestamps_extract_descrip_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.video_timestamps_extract_descrip_flag:
            self.app_obj.set_video_timestamps_extract_descrip_flag(False)


    def on_extract_json_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables automatically extracting timestamps from the video's
        metadata file.


        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.video_timestamps_extract_json_flag:
            self.app_obj.set_video_timestamps_extract_json_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.video_timestamps_extract_json_flag:
            self.app_obj.set_video_timestamps_extract_json_flag(False)


    def on_ffmpeg_add_button_clicked(self, button, entry):

        """Called from callback in self.setup_options_ffmpeg_list_tab().

        Adds a new ffmpeg_tartube.FFmpegOptionsManager object.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Widget providiing a name for the new object

        """

        name = entry.get_text()
        if name == '':
            return

        new_obj = self.app_obj.create_ffmpeg_options(name)

        # Update the treeview
        self.setup_options_ffmpeg_list_tab_update_treeview()
        # Empty the entry box
        entry.set_text('')

        # All other widgets for creating an options manager object open its
        #   edit window, so we'll do the same here
        FFmpegOptionsEditWin(self.app_obj, new_obj)


    def on_ffmpeg_clone_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_ffmpeg_list_tab().

        Clones the selected ffmpeg_tartube.FFmpegOptionsManager object.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.ffmpeg_reg_dict:

                    new_obj = self.app_obj.clone_ffmpeg_options(
                        self.app_obj.ffmpeg_reg_dict[uid],
                    )

                    # Open an edit window, so the user can set the cloned
                    #   object's name
                    FFmpegOptionsEditWin(self.app_obj, new_obj)


    def on_ffmpeg_convert_flag_toggled(self, checkbutton, checkbutton2):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables conversion of .webp thumbnails into .jpg thumbnails.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to be updated

        """

        if checkbutton.get_active() \
        and not self.app_obj.ffmpeg_convert_webp_flag:
            self.app_obj.set_ffmpeg_convert_webp_flag(True)
            checkbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.ffmpeg_convert_webp_flag:
            self.app_obj.set_ffmpeg_convert_webp_flag(False)
            checkbutton2.set_active(False)
            checkbutton2.set_sensitive(False)


    def on_ffmpeg_delete_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_ffmpeg_list_tab().

        Deletes the selected ffmpeg_tartube.FFmpegOptionsManager object, if
        allowed.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Options > FFmpeg options'
        )

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:

            return

        uid = model[this_iter][0]
        if not uid in self.app_obj.ffmpeg_reg_dict:
            return

        options_obj = self.app_obj.ffmpeg_reg_dict[uid]
        if self.app_obj.ffmpeg_options_obj \
        and self.app_obj.ffmpeg_options_obj == options_obj:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('The current options manager cannot be deleted'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        # Prompt for confirmation
        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _('Are you sure you want to delete this options manager?'),
            'question',
            'yes-no',
            self,           # Parent window is this window
            {
                'yes': 'delete_ffmpeg_options',
                # Specified options
                'data': options_obj,
            },
        )


    def on_ffmpeg_edit_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_ffmpeg_list_tab().

        Opens an edit window for the selected
        ffmpeg_tartube.FFmpegOptionsManager.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.ffmpeg_reg_dict:

                    FFmpegOptionsEditWin(
                        self.app_obj,
                        self.app_obj.ffmpeg_reg_dict[uid],
                    )


    def on_ffmpeg_export_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_ffmpeg_list_tab().

        Exports the selected ffmpeg_tartube.FFmpegOptionsManager object to a
        JSON file.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.ffmpeg_reg_dict:

                    self.app_obj.export_ffmpeg_options(
                        self.app_obj.ffmpeg_reg_dict[uid],
                    )


    def on_ffmpeg_import_button_clicked(self, button, entry):

        """Called from callback in self.setup_options_ffmpeg_list_tab().

        Imports a JSON file and creates a new
        ffmpeg_tartube.FFmpegOptionsManager for it.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Widget providiing a name for the new object.
                If the entry is empty, then the name specified by the JSON file
                itself is used

        """

        self.app_obj.import_ffmpeg_options(entry.get_text())

        # Update the treeview
        self.setup_options_ffmpeg_list_tab_update_treeview()
        # Empty the entry box
        entry.set_text('')


    def on_ffmpeg_retain_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables conversion of .webp thumbnails into .jpg thumbnails.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ffmpeg_retain_webp_flag:
            self.app_obj.set_ffmpeg_retain_webp_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ffmpeg_retain_webp_flag:
            self.app_obj.set_ffmpeg_retain_webp_flag(False)


    def on_ffmpeg_use_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_ffmpeg_list_tab().

        Sets the selected ffmpeg_tartube.FFmpegOptionsManager object as the
        current one.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.ffmpeg_reg_dict:

                    self.app_obj.set_ffmpeg_options_obj(
                        self.app_obj.ffmpeg_reg_dict[uid],
                    )

        # Update the treeview
        self.setup_options_ffmpeg_list_tab_update_treeview()


    def on_filter_options_button_toggled(self, checkbutton):

        """Called from callback in self.setup_downloader_forks_tab().

        Sets the flag to filter out yt-dlp options, when using a fork.

        Args:

            checkbutton (Gtk.Checkbutton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdlp_filter_options_flag:
            self.app_obj.set_ytdlp_filter_options_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdlp_filter_options_flag:
            self.app_obj.set_ytdlp_filter_options_flag(False)


    def on_hide_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables hiding finishe media data objects in the Progress
        List.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag = main_win_obj.hide_finished_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.hide_finished_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.hide_finished_checkbutton.set_active(False)


    def on_hide_toolbar_button_toggled(self, checkbutton, checkbutton2):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables hiding the main window's main toolbar.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another checkbutton to modify
                (if it exists)

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Windows > Main Window'
        )

        if checkbutton.get_active() \
        and not self.app_obj.toolbar_hide_flag:
            self.app_obj.set_toolbar_hide_flag(True)

            if not self.app_obj.simple_prefs_flag:
                checkbutton2.set_sensitive(False)

        elif not checkbutton.get_active() \
        and self.app_obj.toolbar_hide_flag:
            self.app_obj.set_toolbar_hide_flag(False)

            if not self.app_obj.simple_prefs_flag:
                checkbutton2.set_sensitive(True)

        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _('The new setting will be applied when Tartube restarts'),
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_http_404_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of HTTP 404 error messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_http_404_error_flag:
            self.app_obj.set_ignore_http_404_error_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_http_404_error_flag:
            self.app_obj.set_ignore_http_404_error_flag(False)


    def on_invidious_mirror_changed(self, entry):

        """Called from callback in self.on_invidious_mirror_changed().

        Sets the Invidious mirror to use.

        Args:

            entry (Gtk.Entry): The widget changed

        """

        self.app_obj.set_custom_invidious_mirror(entry.get_text())


    def on_js_runtime_button_toggled(
        self, checkbutton, combo, entry, button, button2,
    ):
        """Called from callback in self.setup_downloader_javascript_tab().

        Enables/disables use of a JS runtime/engine during downloads.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            combo (Gtk.ComboBox): Another widget to be updated

            entry (Gtk.Entry): Another widget to be updated

            button, button2 (Gtk.Button): Other widgets to be updated

        """

        if checkbutton.get_active() \
        and not self.app_obj.js_runtime_flag:

            self.app_obj.set_js_runtime_flag(True)
            combo.set_sensitive(True)
            combo.set_active(0)
            button.set_sensitive(True)
            button2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.js_runtime_flag:
            self.app_obj.set_js_runtime_flag(False)
            combo.set_active(0)
            combo.set_sensitive(False)
            button.set_sensitive(False)
            button2.set_sensitive(False)

        self.setup_downloader_js_runtime_tab_update_entry(entry)


    def on_js_runtime_combo_changed(self, combo, entry):

        """Called from a callback in self.setup_downloader_js_runtime_tab().

        Extracts the value visible in the combobox, converts it into another
        value, and uses that value to update the main application's IV.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            entry (Gtk.Entry): Another widget to update

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        choice = model[tree_iter][1]

        self.app_obj.set_js_runtime_choice(choice)
        self.setup_downloader_js_runtime_tab_update_entry(entry)


    def on_json_button_toggled(self, checkbutton, spinbutton, spinbutton2):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables applying a timeout when fetching a video's JSON data.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton, spinbutton2 (Gtk.SpinButton): Other widgets to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.apply_json_timeout_flag:
            self.app_obj.set_apply_json_timeout_flag(True)
            spinbutton.set_sensitive(True)
            spinbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.apply_json_timeout_flag:
            self.app_obj.set_apply_json_timeout_flag(False)
            spinbutton.set_sensitive(False)
            spinbutton2.set_sensitive(False)


    def on_keep_open_button_toggled(self, checkbutton, checkbutton2):

        """Called from a callback in self.setup_windows_dialogues_tab().

        Enables/disables keeping the dialogue window open when adding channels/
        playlists/folders.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another checkbutton to sensitise/
                desensitise, according to the new value of the flag

        """

        if checkbutton.get_active() \
        and not self.app_obj.dialogue_keep_open_flag:
            self.app_obj.set_dialogue_keep_open_flag(True)
            checkbutton2.set_sensitive(False)

        elif not checkbutton.get_active() \
        and self.app_obj.dialogue_keep_open_flag:
            self.app_obj.set_dialogue_keep_open_flag(False)
            checkbutton2.set_sensitive(True)


    def on_limit_button_toggled(
        self, checkbutton, entry, entry2, checkbutton2
    ):
        """Called from callback in self.setup_operations_block_tab().

        Sets the limit at which a download operation will stop downloading a
        channel or playlist.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            entry, entry2 (Gtk.Entry): The entry boxes which must be
                sensitised/desensitised, according to the new setting of the IV

            checkbutton2 (Gtk.CheckButton): Another widget to be updated

        """

        if checkbutton.get_active() and not self.app_obj.operation_limit_flag:
            self.app_obj.set_operation_limit_flag(True)
            entry.set_sensitive(True)
            entry2.set_sensitive(True)
            checkbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.operation_limit_flag:
            self.app_obj.set_operation_limit_flag(False)
            entry.set_sensitive(False)
            entry2.set_sensitive(False)
            checkbutton2.set_active(False)
            checkbutton2.set_sensitive(False)


    def on_limit_range_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_block_tab().

        Counts youtube-dl 'date is not in range' messages towards the download
        limit for a channel or playlist.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.operation_limit_include_out_of_range_flag:
            self.app_obj.set_operation_limit_include_out_of_range_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.operation_limit_include_out_of_range_flag:
            self.app_obj.set_operation_limit_include_out_of_range_flag(False)


    def on_livestream_auto_alarm_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_actions_tab().

        Enables/disables sounding an alarm when a livestream starts.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_auto_alarm_flag:
            self.app_obj.set_livestream_auto_alarm_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.livestream_auto_alarm_flag:
            self.app_obj.set_livestream_auto_alarm_flag(False)


    def on_livestream_auto_dl_start_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_actions_tab().

        Enables/disables downloading a livestream as soon as it starts.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_auto_dl_start_flag:
            self.app_obj.set_livestream_auto_dl_start_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.livestream_auto_dl_start_flag:
            self.app_obj.set_livestream_auto_dl_start_flag(False)


    def on_livestream_auto_dl_stop_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_actions_tab().

        Enables/disables downloading a livestream as soon as it stops.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_auto_dl_stop_flag:
            self.app_obj.set_livestream_auto_dl_stop_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.livestream_auto_dl_stop_flag:
            self.app_obj.set_livestream_auto_dl_stop_flag(False)


    def on_livestream_auto_notify_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_actions_tab().

        Enables/disables desktop notifications when a livestream starts.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_auto_notify_flag:
            self.app_obj.set_livestream_auto_notify_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.livestream_auto_notify_flag:
            self.app_obj.set_livestream_auto_notify_flag(False)


    def on_livestream_auto_open_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_actions_tab().

        Enables/disables opening a livestream in the system's web browser when
        it starts.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_auto_open_flag:
            self.app_obj.set_livestream_auto_open_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.livestream_auto_open_flag:
            self.app_obj.set_livestream_auto_open_flag(False)


    def on_livestream_colour_button_toggled(self, checkbutton, checkbutton2):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables coloured backgrounds for livestream videos in the
        Video Catalogue.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_use_colour_flag:
            self.app_obj.set_livestream_use_colour_flag(True)
            checkbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.livestream_use_colour_flag:
            self.app_obj.set_livestream_use_colour_flag(False)
            checkbutton2.set_sensitive(False)

        # Redraw the Video Catalogue, at its current page, to update the
        #   backgrounds
        main_win_obj = self.app_obj.main_win_obj
        main_win_obj.video_catalogue_redraw_all(
            main_win_obj.video_index_current_dbid,
            main_win_obj.catalogue_toolbar_current_page,
        )


    def on_livestream_force_check_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Enables/disables force check of a video, before downloading it as a
        livestream.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_force_check_flag:
            self.app_obj.set_livestream_force_check_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.livestream_force_check_flag:
            self.app_obj.set_livestream_force_check_flag(False)


    def on_livestream_max_days_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Sets the time (in days) at which Tartube stops looking for livestreams.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_livestream_max_days(
            spinbutton.get_value(),
        )


    def on_livestream_mode_button_toggled(self, radiobutton, value):

        """Called from callback in self.setup_operations_livestreams_tab().

        Sets the livestream download mode.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            radiobutton2, radiobutton3 (Gtk.RadioButton): Other widgets to
                modify

            value (str): The new value of the IV

        """

        if radiobutton.get_active():
            self.app_obj.set_livestream_dl_mode(value)

            if not self.app_obj.simple_prefs_flag:

                if self.app_obj.livestream_dl_mode == 'streamlink':
                    self.livestream_radiobutton4.set_active(True)
                    self.livestream_radiobutton5.set_sensitive(False)
                else:
                    self.livestream_radiobutton5.set_sensitive(True)


    def on_livestream_replace_button_toggled(self, radiobutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Enables/disables replacing a previously-downloaded livestream.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if radiobutton.get_active():
            self.app_obj.set_livestream_replace_flag(True)
        else:
            self.app_obj.set_livestream_replace_flag(False)


    def on_livestream_simple_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables using the same background colour for livestream and
        debut videos.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_simple_colour_flag:
            self.app_obj.set_livestream_simple_colour_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.livestream_simple_colour_flag:
            self.app_obj.set_livestream_simple_colour_flag(False)

        # Redraw the Video Catalogue, at its current page, to update the
        #   backgrounds
        main_win_obj = self.app_obj.main_win_obj
        main_win_obj.video_catalogue_redraw_all(
            main_win_obj.video_index_current_dbid,
            main_win_obj.catalogue_toolbar_current_page,
        )


    def on_livestream_stop_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Enables/disables marking a stopped livestream as downloaded.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.livestream_stop_is_final_flag:
            self.app_obj.set_livestream_stop_is_final_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.livestream_stop_is_final_flag:
            self.app_obj.set_livestream_stop_is_final_flag(False)


    def on_livestream_timeout_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Sets the timeout (in minutes) for livestream downloads.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_livestream_dl_timeout(
            spinbutton.get_value(),
        )


    def on_load_descrips_button_clicked(self, button, spinbutton):

        """Called from a callback in self.setup_files_update_tab().

        For every video in the database, updates the description from the
        .description file.

        Args:

            button (Gtk.Button): The widget clicked

            spinbutton (Gtk.SpinButton): Widget setting the maximum line
                length

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Update'
        )

        video_count = 0
        update_count = 0

        for media_data_obj in self.app_obj.media_reg_dict.values():

            if isinstance(media_data_obj, media.Video):

                video_count += 1

                old_descrip = media_data_obj.descrip

                media_data_obj.read_video_descrip(
                    self.app_obj,
                    int(spinbutton.get_value()),
                )

                if old_descrip != media_data_obj.descrip:
                    update_count += 1

        # Confirm the result
        msg = _('Total videos:') + ' ' + str(video_count) + '\n\n' \
        + _('Videos updated:') + ' ' + str(update_count)

        self.app_obj.dialogue_manager_obj.show_simple_msg_dialogue(
            msg,
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_locale_combo_changed(self, combo, grid):

        """Called from a callback in self.setup_general_language_tab().

        Sets the override locale for Tartube.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            grid (Gtk.Grid): The grid on which this tab's widgets are
                arranged

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > General > Application'
        )

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        locale = model[tree_iter][2]

        if locale == '':
            self.app_obj.reset_override_local()
        else:
            self.app_obj.set_override_local(locale)

        # Add some more widgets to tell the user to restart Tartube
        # As the user might not know the language, show an icon as well as
        #   some text
        # Use an extra grid to avoid messing up the layout of widgets above
        grid2 = self.add_secondary_grid(grid, 0, 4, 3, 1)
        grid2.set_border_width(self.spacing_size * 2)

        frame = self.add_image(grid2,
            self.app_obj.main_win_obj.icon_dict['warning_large'],
            0, 0, 1, 1,
        )
        # (The frame looks cramped without this. The icon itself is 32x32)
        frame.set_size_request(
            32 + (self.spacing_size * 2),
            32 + (self.spacing_size * 2),
        )

        self.add_label(grid2,
            '<i>' + _(
                'The new setting will be applied when Tartube restarts',
            ) + '</i>',
            1, 0, 1, 1,
        )

        self.show_all()


    def on_log_json_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_log_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the
        downloader log.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_log_ignore_json_flag:
            self.app_obj.set_ytdl_log_ignore_json_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_log_ignore_json_flag:
            self.app_obj.set_ytdl_log_ignore_json_flag(False)


    def on_log_progress_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_log_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the
        downloader log.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_log_ignore_progress_flag:
            self.app_obj.set_ytdl_log_ignore_progress_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_log_ignore_progress_flag:
            self.app_obj.set_ytdl_log_ignore_progress_flag(False)


    def on_log_stderr_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_log_tab().

        Enables/disables writing output from youtube-dl's STDERR to the
        downloader log.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_log_stderr_flag:
            self.app_obj.set_ytdl_log_stderr_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_log_stderr_flag:
            self.app_obj.set_ytdl_log_stderr_flag(False)


    def on_log_stdout_button_toggled(self, checkbutton, checkbutton2, \
    checkbutton3):

        """Called from a callback in self.setup_output_log_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the
        downloader log.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2, checkbutton3 (Gtk.CheckButton): Additional
                checkbuttons to sensitise/desensitise, according to the new
                value of the flag

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_log_stdout_flag:
            self.app_obj.set_ytdl_log_stdout_flag(True)
            checkbutton2.set_sensitive(True)
            checkbutton3.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_log_stdout_flag:
            self.app_obj.set_ytdl_log_stdout_flag(False)
            checkbutton2.set_sensitive(False)
            checkbutton3.set_sensitive(False)


    def on_log_system_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_log_tab().

        Enables/disables writing youtube-dl system commands to the downloader
        log.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_log_system_cmd_flag:
            self.app_obj.set_ytdl_log_system_cmd_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_log_system_cmd_flag:
            self.app_obj.set_ytdl_log_system_cmd_flag(False)


    def on_match_button_toggled(self, radiobutton):

        """Called from callback in self.setup_files_video_deletion_tab().

        Updates IVs in the main application and sensities/desensities widgets.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        default_val = self.app_obj.match_default_chars

        if radiobutton.get_active():

            if radiobutton == self.radiobutton3:
                self.app_obj.set_match_method('exact_match')
                # (Changing the contents of the widgets automatically updates
                #   mainapp.TartubeApp IVs)
                self.spinbutton3.set_value(default_val)
                self.spinbutton3.set_sensitive(False)
                self.spinbutton4.set_value(default_val)
                self.spinbutton4.set_sensitive(False)

            elif radiobutton == self.radiobutton4:
                self.app_obj.set_match_method('match_first')
                self.spinbutton3.set_sensitive(True)
                self.spinbutton4.set_value(default_val)
                self.spinbutton4.set_sensitive(False)

            else:
                self.app_obj.set_match_method('ignore_last')
                self.spinbutton3.set_value(default_val)
                self.spinbutton3.set_sensitive(False)
                self.spinbutton4.set_sensitive(True)


    def on_match_nickname_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_videos_tab().

        Enables/disables matching against both media.Video.name and
        media.Video.nickname.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to be modified

        """

        if checkbutton.get_active() \
        and not self.app_obj.match_nickname_flag:
            self.app_obj.set_match_nickname_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.match_nickname_flag:
            self.app_obj.set_match_nickname_flag(False)


    def on_match_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_files_video_deletion_tab().

        Updates IVs in the main application and sensities/desensities widgets.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        if spinbutton == self.spinbutton3:
            self.app_obj.set_match_first_chars(spinbutton.get_value())
        else:
            self.app_obj.set_match_ignore_chars(spinbutton.get_value())


    def on_merge_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of 'Requested formats are incompatible for
        merge and will be merged into mkv' warning messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_merge_warning_flag:
            self.app_obj.set_ignore_merge_warning_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_merge_warning_flag:
            self.app_obj.set_ignore_merge_warning_flag(False)


    def on_missing_format_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of missing format error messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_missing_format_error_flag:
            self.app_obj.set_ignore_missing_format_error_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_missing_format_error_flag:
            self.app_obj.set_ignore_missing_format_error_flag(False)


    def on_missing_time_button_toggled(self, checkbutton, spinbutton):

        """Called from callback in self.setup_operations_prefs_tab().

        Enables/disables a time limit when tracking videos missing from a
        channel/playlist.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): Another widget to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.track_missing_time_flag:

            self.app_obj.set_track_missing_time_flag(True)
            spinbutton.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.track_missing_time_flag:
            self.app_obj.set_track_missing_time_flag(False)
            spinbutton.set_sensitive(False)


    def on_missing_time_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_operations_prefs_tab().

        Sets a time limit when tracking videos missing from a channel/playlist.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_track_missing_time_days(
            spinbutton.get_value(),
        )


    def on_missing_videos_button_toggled(self, checkbutton, checkbutton2, \
    spinbutton):

        """Called from callback in self.setup_operations_prefs_tab().

        Enables/disables tracking videos missing from a channel/playlist.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to modify

            spinbutton (Gtk.SpinButton): Another widget to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.track_missing_videos_flag:

            self.app_obj.set_track_missing_videos_flag(True)
            checkbutton2.set_sensitive(True)
            if self.app_obj.track_missing_time_flag:
                spinbutton.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.track_missing_videos_flag:
            checkbutton2.set_active(False)
            self.app_obj.set_track_missing_videos_flag(False)
            checkbutton2.set_sensitive(False)
            spinbutton.set_sensitive(False)


    def on_move_container_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_dialogues_tab().

        Enables/disables prompting the user before moving channels/playlists/
        folders in the Video Index.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.dialogue_move_container_flag:
            self.app_obj.set_dialogue_move_container_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.dialogue_move_container_flag:
            self.app_obj.set_dialogue_move_container_flag(False)


    def on_move_select_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_dialogues_tab().

        Enables/disables selecting a channel/playlist/folder, after media has
        been moved into it.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.dialogue_move_select_flag:
            self.app_obj.set_dialogue_move_select_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.dialogue_move_select_flag:
            self.app_obj.set_dialogue_move_select_flag(False)


    def on_move_video_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_dialogues_tab().

        Enables/disables prompting the user before moving videos in the Video
        Index.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.dialogue_move_video_flag:
            self.app_obj.set_dialogue_move_video_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.dialogue_move_video_flag:
            self.app_obj.set_dialogue_move_video_flag(False)


    def on_moviepy_button_toggled(self, checkbutton):

        """Called from callback in self.setup_general_modules_tab().

        Enables/disables use of the moviepy.editor module.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.use_module_moviepy_flag:
            self.app_obj.set_use_module_moviepy_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.use_module_moviepy_flag:
            self.app_obj.set_use_module_moviepy_flag(False)


    def on_moviepy_timeout_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_general_modules_tab().

        Sets the timeout to apply to threads using the moviepy module.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_refresh_moviepy_timeout(
            spinbutton.get_value(),
        )


    def on_nickname_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables showing video nicknames in the Video Catalogue.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.catalogue_show_nickname_flag:
            self.app_obj.set_catalogue_show_nickname_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.catalogue_show_nickname_flag:
            self.app_obj.set_catalogue_show_nickname_flag(False)


    def on_no_annotations_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of the 'no annotations' warning messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_no_annotations_flag:
            self.app_obj.set_ignore_no_annotations_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_no_annotations_flag:
            self.app_obj.set_ignore_no_annotations_flag(False)


    def on_no_subtitles_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of the 'no subtitles' warning messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_no_subtitles_flag:
            self.app_obj.set_ignore_no_subtitles_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_no_subtitles_flag:
            self.app_obj.set_ignore_no_subtitles_flag(False)


    def on_no_descrip_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of the 'no playlist description to write'
        warning messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_no_descrip_flag:
            self.app_obj.set_ignore_no_descrip_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_no_descrip_flag:
            self.app_obj.set_ignore_no_descrip_flag(False)


    def on_open_desktop_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_temp_folders_tab().

        Enables/disables opening temporary folders on the desktop when Tartube
        shuts down.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.open_temp_on_desktop_flag:
            self.app_obj.set_open_temp_on_desktop_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.open_temp_on_desktop_flag:
            self.app_obj.set_open_temp_on_desktop_flag(False)


    def on_open_in_tray_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_system_tray_tab().

        Enables/disables opening Tartube in the system tray.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.open_in_tray_flag:
            self.app_obj.set_open_in_tray_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.open_in_tray_flag:
            self.app_obj.set_open_in_tray_flag(False)


    def on_open_url_clicked(self, button, treeview):

        """Called from a callback in self.setup_files_urls_tab().

        Opens the URL in the selected line.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The parent treeview

        """

        # Get the media data objects for each selected line
        selection = treeview.get_selection()
        this_tuple = selection.get_selected_rows()
        # (Confusingly, first item in the tuple is the Gtk.ListStore)
        model = this_tuple[0]
        for path in this_tuple[1]:

            tree_iter = model.get_iter(path)
            if tree_iter is not None:

                dbid = model[tree_iter][0]
                if dbid in self.app_obj.media_reg_dict:

                    media_data_obj = self.app_obj.media_reg_dict[dbid]
                    if media_data_obj.source is not None:

                        ttutils.open_file(self.app_obj, media_data_obj.source)


    def on_operation_error_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_errors_warnings_tab().

        Enables/disables operation errors in the 'Errors/Warnings' tab.
        Toggling the corresponding Gtk.CheckButton in the Errors/Warnings tab
        sets the IV (and makes sure the two checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag = main_win_obj.show_operation_error_checkbutton.get_active()

        main_win_obj = self.app_obj.main_win_obj
        if (checkbutton.get_active() and not other_flag):
            main_win_obj.show_operation_error_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.show_operation_error_checkbutton.set_active(False)


    def on_operation_sim_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables ignoring already-checked videos whose parent is a
        media.Folder, if the videos have already been checked.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.operation_sim_shortcut_flag:
            self.app_obj.set_operation_sim_shortcut_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.operation_sim_shortcut_flag:
            self.app_obj.set_operation_sim_shortcut_flag(False)


    def on_operation_warning_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_errors_warnings_tab().

        Enables/disables operation warnings in the 'Errors/Warnings' tab.
        Toggling the corresponding Gtk.CheckButton in the Errors/Warnings tab
        sets the IV (and makes sure the two checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag \
        = main_win_obj.show_operation_warning_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.show_operation_warning_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.show_operation_warning_checkbutton.set_active(False)


    def on_options_add_button_clicked(self, button, entry):

        """Called from callback in self.setup_options_dl_list_tab().

        Adds a new options.OptionsManager object.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Widget providiing a name for the new object

        """

        name = entry.get_text()
        if name == '':
            return

        new_obj = self.app_obj.create_download_options(name)

        # If required, clone download options from the General Options Manager
        #   into the new object
        if self.app_obj.auto_clone_options_flag:
            new_obj.clone_options(self.app_obj.general_options_obj)

        # On the assumption that objects created here will be applied (mostly)
        #   in the Classic Mode tab, disable downloading the description,
        #   annotations (etc) files
        new_obj.set_classic_mode_options()

        # Update the treeview
        self.setup_options_dl_list_tab_update_treeview()
        # Empty the entry box
        entry.set_text('')

        # All other widgets for creating an options manager object open its
        #   edit window, so we'll do the same here
        OptionsEditWin(self.app_obj, new_obj)


    def on_options_clone_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_dl_list_tab().

        Clones the selected options.OptionsManager object.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.options_reg_dict:

                    new_obj = self.app_obj.clone_download_options(
                        self.app_obj.options_reg_dict[uid],
                    )

                    # Open an edit window, so the user can set the cloned
                    #   object's name
                    OptionsEditWin(self.app_obj, new_obj)


    def on_options_delete_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_dl_list_tab().

        Deletes the selected options.OptionsManager object, if allowed.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Options > Download options'
        )

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:

            return

        uid = model[this_iter][0]
        if not uid in self.app_obj.options_reg_dict:
            return

        options_obj = self.app_obj.options_reg_dict[uid]
        if self.app_obj.general_options_obj \
        and self.app_obj.general_options_obj == options_obj:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('The default options manager cannot be deleted'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        # Prompt for confirmation
        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _('Are you sure you want to delete this options manager?'),
            'question',
            'yes-no',
            self,           # Parent window is this window
            {
                'yes': 'delete_download_options',
                # Specified options
                'data': options_obj,
            },
        )


    def on_options_edit_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_dl_list_tab().

        Opens an edit window for the selected options.OptionsManager object.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.options_reg_dict:

                    OptionsEditWin(
                        self.app_obj,
                        self.app_obj.options_reg_dict[uid],
                    )


    def on_options_export_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_dl_list_tab().

        Exports the selected options.OptionsManager object to a JSON file.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.options_reg_dict:

                    self.app_obj.export_download_options(
                        self.app_obj.options_reg_dict[uid],
                    )


    def on_options_import_button_clicked(self, button, entry):

        """Called from callback in self.setup_options_dl_list_tab().

        Imports a JSON file and creates a new options.OptionsManager for it.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Widget providiing a name for the new object.
                If the entry is empty, then the name specified by the JSON file
                itself is used

        """

        self.app_obj.import_download_options(entry.get_text())

        # Update the treeview
        self.setup_options_dl_list_tab_update_treeview()
        # Empty the entry box
        entry.set_text('')


    def on_options_use_classic_button_clicked(self, button, treeview):

        """Called from callback in self.setup_options_dl_list_tab().

        Applies the selected options.OptionsManager object to the Classic Mode
        tab.

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if path_list:

            # (Multiple selection is not enabled)
            this_iter = model.get_iter(path_list[0])
            if this_iter is not None:

                uid = model[this_iter][0]
                if uid in self.app_obj.options_reg_dict:

                    options_obj = self.app_obj.options_reg_dict[uid]

                    # If this is already the options manager for the Classic
                    #   Mode tab, then remove it (but don't delete the object
                    #   itself)
                    if self.app_obj.classic_options_obj \
                    and self.app_obj.classic_options_obj == options_obj:

                        self.app_obj.remove_classic_download_options()

                    else:

                        self.app_obj.apply_classic_download_options(
                            self.app_obj.options_reg_dict[uid],
                        )

        # Update the treeview
        self.setup_options_dl_list_tab_update_treeview()


    def on_output_empty_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables emptying pages in the Output tab at the start of every
        operation.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_output_start_empty_flag:
            self.app_obj.set_ytdl_output_start_empty_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_output_start_empty_flag:
            self.app_obj.set_ytdl_output_start_empty_flag(False)


    def on_output_json_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the Output
        tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_output_ignore_json_flag:
            self.app_obj.set_ytdl_output_ignore_json_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_output_ignore_json_flag:
            self.app_obj.set_ytdl_output_ignore_json_flag(False)


    def on_output_progress_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the Output
        tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_output_ignore_progress_flag:
            self.app_obj.set_ytdl_output_ignore_progress_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_output_ignore_progress_flag:
            self.app_obj.set_ytdl_output_ignore_progress_flag(False)


    def on_output_stderr_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables writing output from youtube-dl's STDERR to the Output
        tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_output_stderr_flag:
            self.app_obj.set_ytdl_output_stderr_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_output_stderr_flag:
            self.app_obj.set_ytdl_output_stderr_flag(False)


    def on_output_stdout_button_toggled(self, checkbutton, checkbutton2, \
    checkbutton3):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the Output
        tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2, checkbutton3 (Gtk.CheckButton): Additional
                checkbuttons to sensitise/desensitise, according to the new
                value of the flag

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_output_stdout_flag:
            self.app_obj.set_ytdl_output_stdout_flag(True)
            checkbutton2.set_sensitive(True)
            checkbutton3.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_output_stdout_flag:
            self.app_obj.set_ytdl_output_stdout_flag(False)
            checkbutton2.set_sensitive(False)
            checkbutton3.set_sensitive(False)


    def on_output_summary_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables displaying a summary page in the Output tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_output_show_summary_flag:
            self.app_obj.set_ytdl_output_show_summary_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_output_show_summary_flag:
            self.app_obj.set_ytdl_output_show_summary_flag(False)


    def on_output_size_button_toggled(self, checkbutton):

        """Called from callback in self.setup_output_outputtab_tab().

        Enables/disables applying a maximum size to the Output tab pages.
        Toggling the corresponding Gtk.CheckButton in the Output tab sets the
        IV (and makes sure the two checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        other_flag \
        = self.app_obj.main_win_obj.output_size_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            self.app_obj.main_win_obj.output_size_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            self.app_obj.main_win_obj.output_size_checkbutton.set_active(False)


    def on_output_size_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_output_outputtab_tab().

        Sets the maximum size of the Output tab pages. Setting the value of the
        corresponding Gtk.SpinButton in the Output tab sets the IV (and
        makes sure the two spinbuttons have the same value).

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.main_win_obj.output_size_spinbutton.set_value(
            spinbutton.get_value(),
        )


    def on_output_system_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables writing youtube-dl system commands to the Output tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_output_system_cmd_flag:
            self.app_obj.set_ytdl_output_system_cmd_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_output_system_cmd_flag:
            self.app_obj.set_ytdl_output_system_cmd_flag(False)


    def on_page_given_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of the 'a channel/user page was given'
        warning messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_page_given_flag:
            self.app_obj.set_ignore_page_given_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_page_given_flag:
            self.app_obj.set_ignore_page_given_flag(False)


    def on_payment_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_websites_tab().

        Enables/disables ignoring of payment required error messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_yt_payment_flag:
            self.app_obj.set_ignore_yt_payment_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_yt_payment_flag:
            self.app_obj.set_ignore_yt_payment_flag(False)


    def on_pretty_date_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables 'today' and 'yesterday' rather than a numerical date
        in the Videos tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_pretty_dates_flag:
            self.app_obj.set_show_pretty_dates_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_pretty_dates_flag:
            self.app_obj.set_show_pretty_dates_flag(False)


    def on_proxy_textview_changed(self, textbuffer):

        """Called from callback in self.setup_operations_proxies_tab().

        Sets the list of proxies.

        Args:

            textbuffer (Gtk.TextBuffer): The buffer belonging to the textview
                whose contents has been modified

        """

        text = textbuffer.get_text(
            textbuffer.get_start_iter(),
            textbuffer.get_end_iter(),
            # Don't include hidden characters
            False,
        )

        # Filter out empty lines
        line_list = text.splitlines()
        mod_list = []
        for line in line_list:
            if re.search(r'\S', line):
                mod_list.append(line)

        # Apply the changes
        self.app_obj.set_dl_proxy_list(mod_list)


    def on_recalculate_stats_button_clicked(self, button, entry, entry2,
    entry3, entry4, entry5, entry6):

        """Called from callback in self.setup_files_statistics_tab().

        Recalculates the number of media data objects in the Tartube database,
        and updates the entry boxes.

        Args:

            button (Gtk.Button): The widget clicked

            entry, entry2, entry3, entry4, entry5, entry6 (Gtk.Entry): The
                entry boxes to update

        """

        self.setup_files_statistics_tab_recalculate(
            entry,
            entry2,
            entry3,
            entry4,
            entry5,
            entry6,
        )


    def on_reextract_stamps_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables re-extracting timestamps just before splitting a
        video.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.video_timestamps_re_extract_flag:
            self.app_obj.set_video_timestamps_re_extract_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.video_timestamps_re_extract_flag:
            self.app_obj.set_video_timestamps_re_extract_flag(False)


    def on_refresh_verbose_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables displaying non-matching videos in the Output tab
        during a refresh operation.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.refresh_output_verbose_flag:
            self.app_obj.set_refresh_output_verbose_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.refresh_output_verbose_flag:
            self.app_obj.set_refresh_output_verbose_flag(False)


    def on_refresh_videos_button_toggled(self, checkbutton, checkbutton2):

        """Called from a callback in self.setup_output_outputtab_tab().

        Enables/disables displaying matching videos in the Output tab during a
        refresh operation.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): A different checkbutton to
                sensitise/desensitise, according to the new value of the flag

        """

        if checkbutton.get_active() \
        and not self.app_obj.refresh_output_videos_flag:
            self.app_obj.set_refresh_output_videos_flag(True)
            checkbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.refresh_output_videos_flag:
            self.app_obj.set_refresh_output_videos_flag(False)
            checkbutton2.set_sensitive(False)


    def on_regex_button_toggled(self, radiobutton, flag):

        """Called from callback in self.setup_windows_websites_tab().

        Sets whether mainapp.TartubeApp.ignore_custom_msg_list contains
        ordinary strings or regexes.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            flag (bool): False for ordinary strings, True for regexes

        """

        if radiobutton.get_active():
            self.app_obj.set_ignore_custom_regex_flag(flag)


    def on_remember_size_button_toggled(self, checkbutton, checkbutton2):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables remembering the size of the main window.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to be modified

        """

        if checkbutton.get_active() \
        and not self.app_obj.main_win_save_size_flag:
            self.app_obj.set_main_win_save_size_flag(True)
            checkbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.main_win_save_size_flag:
            self.app_obj.set_main_win_save_size_flag(False)
            checkbutton2.set_sensitive(False)
            checkbutton2.set_active(False)


    def on_remember_slider_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables remembering the position of sliders in the main
        window.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.main_win_save_slider_flag:
            self.app_obj.set_main_win_save_slider_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.main_win_save_slider_flag:
            self.app_obj.set_main_win_save_slider_flag(False)


    def on_remember_width_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_main_window_tab().

        Enables/disables remembering the width of some columns in the Progress
        and Classic Mode tabs.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.progress_list_remember_width_flag:
            self.app_obj.set_progress_list_remember_width_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.progress_list_remember_width_flag:
            self.app_obj.set_progress_list_remember_width_flag(False)


    def on_remove_comments_button_clicked(self, button):

        """Called from callback in self.setup_files_update_tab().

        Clears comments from every video in the database.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Update'
        )

        video_count = 0
        success_count = 0

        for media_data_obj in self.app_obj.media_reg_dict.values():

            if isinstance(media_data_obj, media.Video):

                video_count += 1
                if media_data_obj.comment_list:

                    success_count += 1
                    media_data_obj.reset_comments()


        # Redraw the Video Catalogue, at its current page
        main_win_obj = self.app_obj.main_win_obj
        main_win_obj.video_catalogue_redraw_all(
            main_win_obj.video_index_current_dbid,
            main_win_obj.catalogue_toolbar_current_page,
        )

        # Confirm the result
        msg = _('Total videos:') + ' ' + str(video_count) + '\n\n' \
        + _('Videos updated:') + ' ' + str(success_count)

        self.app_obj.dialogue_manager_obj.show_simple_msg_dialogue(
            msg,
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_remove_container_file_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_delete_tab().

        Enables/disables removing all files from the filesystem when deleting
        containers manually.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.delete_container_files_flag:
            self.app_obj.set_delete_container_files_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.delete_container_files_flag:
            self.app_obj.set_delete_container_files_flag(False)


    def on_remove_duplicate_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables removeing duplicate URLs from the Classic Mode tab,
        after the 'Add URLs' button is clicked.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.classic_duplicate_remove_flag:
            self.app_obj.set_classic_duplicate_remove_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.classic_duplicate_remove_flag:
            self.app_obj.set_classic_duplicate_remove_flag(False)


    def on_remove_stamps_button_clicked(self, button):

        """Called from callback in self.setup_files_update_tab().

        Clears timestamps from every video in the database.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Update'
        )

        video_count = 0
        success_count = 0

        for media_data_obj in self.app_obj.media_reg_dict.values():

            if isinstance(media_data_obj, media.Video):

                video_count += 1
                if media_data_obj.stamp_list:

                    success_count += 1
                    media_data_obj.reset_timestamps()


        # Redraw the Video Catalogue, at its current page
        main_win_obj = self.app_obj.main_win_obj
        main_win_obj.video_catalogue_redraw_all(
            main_win_obj.video_index_current_dbid,
            main_win_obj.catalogue_toolbar_current_page,
        )

        # Confirm the result
        msg = _('Total videos:') + ' ' + str(video_count) + '\n\n' \
        + _('Videos updated:') + ' ' + str(success_count)

        self.app_obj.dialogue_manager_obj.show_simple_msg_dialogue(
            msg,
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_remove_video_file_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_delete_tab().

        Enables/disables removing all files from the filesystem when deleting
        videos manually.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.delete_video_files_flag:
            self.app_obj.set_delete_video_files_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.delete_video_files_flag:
            self.app_obj.set_delete_video_files_flag(False)


    def on_replace_stamps_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables replacing timestamps.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.video_timestamps_replace_flag:
            self.app_obj.set_video_timestamps_replace_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.video_timestamps_replace_flag:
            self.app_obj.set_video_timestamps_replace_flag(False)


    def on_reset_archive_button_clicked(self, button, entry):

        """Called from callback in self.setup_operations_archive_tab().

        Resets the path to the youtube-dl archive file.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        self.app_obj.set_allow_ytdl_archive_path(None)
        entry.set_text('')


    def on_reset_avconv_button_clicked(self, button, entry):

        """Called from callback in self.setup_ytdl_avconv_tab().

        Resets the path to the avconv binary.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        self.app_obj.set_avconv_path(None)
        entry.set_text('')


    def on_reset_ffmpeg_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_ffmpeg_tab().

        Resets the path to the FFmpeg binary.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        self.app_obj.set_ffmpeg_path(None)
        entry.set_text('')


    def on_reset_js_runtime_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_js_runtime_tab().

        Resets the path to the JS runtime binary.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        self.app_obj.set_js_runtime_path(None)
        self.setup_downloader_js_runtime_tab_update_entry(entry)


    def on_reset_invidious_clicked(self, button, entry):

        """Called from callback in self.setup_operations_mirrors_tab().

        Resets the Invidious mirror

        Args:

            entry (Gtk.Entry): The widget changed

            entry (Gtk.Entry): Another widget to update

        """

        self.app_obj.reset_custom_invidious_mirror()
        entry.set_text(self.app_obj.custom_invidious_mirror)


    def on_reset_sblock_clicked(self, button, entry):

        """Called from callback in self.setup_operations_mirrors_tab().

        Resets the URL of the SponsorBlock API.

        Args:

            button (Gtk.Button): The widget that was clicked

            entry (Gtk.Entry): Another widget to update

        """

        self.app_obj.reset_custom_sblock_mirror()
        entry.set_text(self.app_obj.custom_sblock_mirror)


    def on_reset_size_clicked(self, button):

        """Called from a callback in self.setup_windows_main_window_tab().

        Resets the main window to its default size, and repositions sliders to
        their default positions.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.app_obj.main_win_obj.resize_self(
            self.app_obj.main_win_width,
            self.app_obj.main_win_height,
        )

        self.app_obj.main_win_obj.reset_sliders()

        # Because of Gtk issues, the slider's position must be reset twice, the
        #   second time by mainapp.TartubeApp.script_fast_timer_callback()
        self.app_obj.set_main_win_slider_reset_flag(True)


    def on_reset_streamlink_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_streamlink_tab().

        Resets the path to the streamlink binary.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        self.app_obj.set_streamlink_path(None)
        entry.set_text('')


    def on_restore_from_tray_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_system_tray_tab().

        Enables/disables restoring the window's position after closing it to
        the system tray.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.restore_posn_from_tray_flag:
            self.app_obj.set_restore_posn_from_tray_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.restore_posn_from_tray_flag:
            self.app_obj.set_restore_posn_from_tray_flag(False)


    def on_reverse_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables display of videos in the Results List in the reverse
        order.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag = main_win_obj.reverse_results_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.reverse_results_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.reverse_results_checkbutton.set_active(False)


    def on_save_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables automatic saving of files at the end of a download/
        update/refresh/info/tidy operation.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() and not self.app_obj.operation_save_flag:
            self.app_obj.set_operation_save_flag(True)
        elif not checkbutton.get_active() and self.app_obj.operation_save_flag:
            self.app_obj.set_operation_save_flag(False)


    def on_sblock_fetch_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_slices_tab().

        Enables/disables contacting the SponsorBlock server.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.sblock_fetch_flag:
            self.app_obj.set_sblock_fetch_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.sblock_fetch_flag:
            self.app_obj.set_sblock_fetch_flag(False)


    def on_sblock_obfuscate_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_slices_tab().

        Enables/disables obfuscating video IDs in requests to the SponsorBlock
        server.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.sblock_obfuscate_flag:
            self.app_obj.set_sblock_obfuscate_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.sblock_obfuscate_flag:
            self.app_obj.set_sblock_obfuscate_flag(False)


    def on_sblock_replace_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_slices_tab().

        Enables/disables replacing any previous set of video slices.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.sblock_replace_flag:
            self.app_obj.set_sblock_replace_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.sblock_replace_flag:
            self.app_obj.set_sblock_replace_flag(False)


    def on_sblock_re_extract_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_slices_tab().

        Enables/disables re-extracting SponsorBlock before removing slices
        from a video.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.sblock_re_extract_flag:
            self.app_obj.set_sblock_re_extract_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.sblock_re_extract_flag:
            self.app_obj.set_sblock_re_extract_flag(False)


    def on_slice_cleanup_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_slices_tab().

        Enables/disables clearing timestamp/slice data from a video, after it
        has had its video slices removed.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.slice_video_cleanup_flag:
            self.app_obj.set_slice_video_cleanup_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.slice_video_cleanup_flag:
            self.app_obj.set_slice_video_cleanup_flag(False)


    def on_sblock_mirror_changed(self, entry):

        """Called from callback in self.setup_operations_mirrors_tab().

        Sets the SponsorBlock API mirror to use.

        Args:

            entry (Gtk.Entry): The widget changed

        """

        self.app_obj.set_custom_sblock_mirror(entry.get_text())


    def on_scheduled_add_button_clicked(self, button, entry):

        """Called from callback in self.setup_scheduling_start_tab().

        Adds a new media.Scheduled object, adds it to the treeview, and opens
        an edit window for it.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): An entry containing the new object's name

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Scheduling > Start'
        )

        # Check the specified name is valid
        name = entry.get_text()
        if name == '':
            return

        for this_obj in self.app_obj.scheduled_list:
            if this_obj.name == name:

                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _('There is already a scheduled download with that name'),
                    'error',
                    'ok',
                    self,           # Parent window is this window
                )

                return

        # Create a new scheduled download object
        new_obj = media.Scheduled(name, 'real', 'repeat')
        self.app_obj.add_scheduled_list(new_obj)

        # Add it to the treeview
        self.setup_scheduling_start_tab_add_row(new_obj)
        # Open an edit window for it
        ScheduledEditWin(self.app_obj, new_obj)
        # Reset the entry
        entry.set_text('')


    def on_scheduled_delete_button_clicked(self, button, treeview):

        """Called from callback in self.setup_scheduling_start_tab().

        Prompts the user, and then deletes the selected media.Scheduled object.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview with a selected line

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Scheduling > Start'
        )

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        for path in path_list:

            this_iter = model.get_iter(path)
            name = model[this_iter][0]

            for scheduled_obj in self.app_obj.scheduled_list:
                if scheduled_obj.name == name:

                    # Prompt the user
                    self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                        _(
                        'Are you sure you want to delete this scheduled' \
                        + ' download?',
                        ),
                        'question',
                        'yes-no',
                        self,           # Parent window is this window
                        {
                            'yes': 'del_scheduled_list',
                            'data': [scheduled_obj, self],
                        },
                    )


    def on_scheduled_edit_button_clicked(self, button, treeview):

        """Called from callback in self.setup_scheduling_start_tab().

        Opens an edit window for the selected media.Scheduled object.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview with a selected line

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        for path in path_list:

            this_iter = model.get_iter(path)
            name = model[this_iter][0]

            for scheduled_obj in self.app_obj.scheduled_list:
                if scheduled_obj.name == name:
                    ScheduledEditWin(self.app_obj, scheduled_obj)
                    break


    def on_scheduled_move_down_button_clicked(self, button, treeview):

        """Called from callback in self.setup_scheduling_start_tab().

        Moves the selected media.Scheduled object down one position in the
        list.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview with a selected line

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        for path in path_list:

            this_iter = model.get_iter(path)
            if model.iter_next(this_iter):

                name = model[this_iter][0]
                self.app_obj.move_scheduled_list(name, True)

                model.move_after(
                    this_iter,
                    model.iter_next(this_iter),
                )


    def on_scheduled_move_up_button_clicked(self, button, treeview):

        """Called from callback in self.setup_scheduling_start_tab().

        Moves the selected media.Scheduled object up one position in the list.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview with a selected line

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        for path in path_list:

            this_iter = model.get_iter(path)
            if this_iter is not None:

                name = model[this_iter][0]
                self.app_obj.move_scheduled_list(name, False)

                model.move_before(
                    this_iter,
                    model.iter_previous(this_iter),
                )


    def on_scheduled_livestreams_button_toggled(self, checkbutton,
    checkbutton2, spinbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Enables starting the livestream task periodically to check videos
        marked as livestreams.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to sensitise/
                desensitise, according to the new value of the flag

            spinbutton (Gtk.SpinButton): Another widget to sensitise/
                desensitise, according to the new value of the flag

        """

        if checkbutton.get_active() \
        and not self.app_obj.scheduled_livestream_flag:
            self.app_obj.set_scheduled_livestream_flag(True)
            spinbutton.set_sensitive(True)
            checkbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.scheduled_livestream_flag:
            self.app_obj.set_scheduled_livestream_flag(False)
            spinbutton.set_sensitive(False)
            checkbutton2.set_sensitive(False)
            checkbutton2.set_active(False)


    def on_scheduled_livestreams_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Sets the time (in minutes) between scheduled livestream operations.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_scheduled_livestream_wait_mins(
            spinbutton.get_value(),
        )


    def on_separator_combo_changed(self, combo):

        """Called from a callback in self.setup_files_backups_tab().

        Sets the CSV export separator.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.app_obj.set_export_csv_separator(model[tree_iter][0])


    def on_set_archive_button_clicked(self, button, entry):

        """Called from callback in self.setup_operations_archive_tab().

        Opens a window in which the user can select the path to the directory
        in which the youtube-dl archive file should be stored.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Operations > Archive'
        )

        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Select the location of the archive file'),
            self,
            'folder',
        )

        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK and new_path:

            self.app_obj.set_allow_ytdl_archive_path(new_path)
            entry.set_text(self.app_obj.allow_ytdl_archive_path)


    def on_set_avconv_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_ffmpeg_tab().

        Opens a window in which the user can select the avconv binary, if it is
        installed (and if the user wants it).

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Downloaders > FFmpeg / AVConv'
        )

        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Please select the AVConv executable'),
            self,
            'open',
        )

        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK and new_path:

            self.app_obj.set_avconv_path(new_path)
            entry.set_text(self.app_obj.avconv_path)


    def on_set_ffmpeg_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_ffmpeg_tab().

        Opens a window in which the user can select the FFmpeg binary, if it is
        installed (and if the user wants it).

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Downloaders > FFmpeg / AVConv'
        )

        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Please select the FFmpeg executable'),
            self,
            'open',
        )

        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK and new_path:

            self.app_obj.set_ffmpeg_path(new_path)
            entry.set_text(self.app_obj.ffmpeg_path)


    def on_set_js_runtime_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_js_runtime_tab().

        Opens a window in which the user can select the JS runtime binary, if
        it is installed (and if the user wants it).

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Downloaders > JavaScript'
        )

        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Please select the JavaScript runtime'),
            self,
            'open',
        )

        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK:

            self.app_obj.set_js_runtime_path(new_path)
            self.setup_downloader_js_runtime_tab_update_entry(entry)


    def on_set_streamlink_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_streamlink_tab().

        Opens a window in which the user can select the streamlink binary, if
        it is installed (and if the user wants it).

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Downloaders > streamlink'
        )

        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Please select the streamlink executable'),
            self,
            'open',
        )

        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK and new_path:

            self.app_obj.set_streamlink_path(new_path)
            entry.set_text(self.app_obj.streamlink_path)


    def on_show_classic_mode_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_main_window_tab().

        Enables/disables automatically opening the Classic Mode tab on startup.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_classic_tab_on_startup_flag:
            self.app_obj.set_show_classic_tab_on_startup_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_classic_tab_on_startup_flag:
            self.app_obj.set_show_classic_tab_on_startup_flag(False)


    def on_show_custom_dl_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables showing the 'Custom download all' button in the Videos
        tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_custom_dl_button_flag:
            self.app_obj.set_show_custom_dl_button_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_custom_dl_button_flag:
            self.app_obj.set_show_custom_dl_button_flag(False)

        # Abuse the main window code to either show or hide the button
        self.app_obj.main_win_obj.hide_progress_bar(True)


    def on_show_custom_icons_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables replacing stock icons with custom icons.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Windows > Main Window'
        )

        if checkbutton.get_active() \
        and not self.app_obj.show_custom_icons_flag:
            self.app_obj.set_show_custom_icons_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_custom_icons_flag:
            self.app_obj.set_show_custom_icons_flag(False)

        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _('The new setting will be applied when Tartube restarts'),
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_show_delete_container_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_delete_tab().

        Enables/disables prompting the user before deleting containers.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_delete_container_dialogue_flag:
            self.app_obj.set_show_delete_container_dialogue_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_delete_container_dialogue_flag:
            self.app_obj.set_show_delete_container_dialogue_flag(False)


    def on_show_delete_video_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_delete_tab().

        Enables/disables prompting the user before deleting videos.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_delete_video_dialogue_flag:
            self.app_obj.set_show_delete_video_dialogue_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_delete_video_dialogue_flag:
            self.app_obj.set_show_delete_video_dialogue_flag(False)


    def on_show_free_space_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables showing free disk space in the Videos tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_free_space_flag:
            self.app_obj.set_show_free_space_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_free_space_flag:
            self.app_obj.set_show_free_space_flag(False)


    def on_show_selector_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables showing the selector button in each row of the Video
        Index.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_marker_in_index_flag:
            self.app_obj.set_show_marker_in_index_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_marker_in_index_flag:
            self.app_obj.set_show_marker_in_index_flag(False)


    def on_show_small_icons_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables smaller icons in the Video Index.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_small_icons_in_index_flag:
            self.app_obj.set_show_small_icons_in_index_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_small_icons_in_index_flag:
            self.app_obj.set_show_small_icons_in_index_flag(False)


    def on_show_status_icon_toggled(self, checkbutton, checkbutton2,
    checkbutton3, checkbutton4):

        """Called from a callback in self.setup_windows_system_tray_tab().

        Shows/hides the status icon in the system tray.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2, checkbutton3, checkbutton4 (Gtk.CheckButton): Other
                widgets to modify

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_status_icon_flag:
            self.app_obj.set_show_status_icon_flag(True)
            checkbutton2.set_sensitive(True)
            checkbutton3.set_sensitive(True)
            if self.app_obj.close_to_tray_flag:
                checkbutton4.set_sensitive(True)
            else:
                checkbutton4.set_sensitive(False)

        elif not checkbutton.get_active() \
        and self.app_obj.show_status_icon_flag:
            self.app_obj.set_show_status_icon_flag(False)
            checkbutton2.set_active(False)
            checkbutton2.set_sensitive(False)
            checkbutton3.set_active(False)
            checkbutton3.set_sensitive(False)
            checkbutton4.set_active(False)
            checkbutton4.set_sensitive(False)


    def on_show_tooltips_toggled(self, checkbutton, checkbutton2):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables tooltips for videos/channels/playlists/folders.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to be modified

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_tooltips_flag:
            self.app_obj.set_show_tooltips_flag(True)
            checkbutton2.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.show_tooltips_flag:
            self.app_obj.set_show_tooltips_flag(False)
            checkbutton2.set_sensitive(False)
            checkbutton2.set_active(False)


    def on_show_tooltips_extra_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_videos_tab().

        Enables/disables errors/warnings in tooltips.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.show_tooltips_extra_flag:
            self.app_obj.set_show_tooltips_extra_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.show_tooltips_extra_flag:
            self.app_obj.set_show_tooltips_extra_flag(False)


    def on_simple_prefs_clicked(self, button):

        """Called by callback in self.setup_general_application_tab().

        Args:

            button (Gtk.Button): The widget clicked

        """

        if not self.app_obj.simple_prefs_flag:
            self.app_obj.set_simple_prefs_flag(True)
        else:
            self.app_obj.set_simple_prefs_flag(False)

        self.reset_window()


    def on_slice_keyframe_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_slices_tab().

        Enables/disables forced keyframes at cuts, when removing slices from
        videos.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.slice_video_force_keyframe_flag:
            self.app_obj.set_slice_video_force_keyframe_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.slice_video_force_keyframe_flag:
            self.app_obj.set_slice_video_force_keyframe_flag(False)


    def on_sound_custom_changed(self, combo):

        """Called from callback in self.setup_operations_actions_tab().

        Sets the user's preferred sound effect for livestream alarms.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.app_obj.set_sound_custom(model[tree_iter][0])


    def on_split_keyframe_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables forced keyframes at cuts, when splitting videos into
        clips.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.split_video_force_keyframe_flag:
            self.app_obj.set_split_video_force_keyframe_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.split_video_force_keyframe_flag:
            self.app_obj.set_split_video_force_keyframe_flag(False)


    def on_split_mode_combo_changed(self, combo):

        """Called from a callback in self.setup_operations_clips_tab().

        Sets the mode for naming split video files.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.app_obj.set_split_video_name_mode(model[tree_iter][1])


    def on_split_subdir_flag_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_clips_tab().

        Enables/disables moving split files into a sub-directory.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.split_video_subdir_flag:
            self.app_obj.set_split_video_subdir_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.split_video_subdir_flag:
            self.app_obj.set_split_video_subdir_flag(False)


    def on_squeeze_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables labels in the main window's main toolbar.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.toolbar_squeeze_flag:
            self.app_obj.set_toolbar_squeeze_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.toolbar_squeeze_flag:
            self.app_obj.set_toolbar_squeeze_flag(False)


    def on_store_playlist_id_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Enables/disables storing video's playlist IDs in the parent channel/
        playlist.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.store_playlist_id_flag:
            self.app_obj.set_store_playlist_id_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.store_playlist_id_flag:
            self.app_obj.set_store_playlist_id_flag(False)


    def on_system_container_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_errors_warnings_tab().

        Enables/disables showing container names in the Errors/Warnings tab.
        Toggling the corresponding Gtk.CheckButton in the Errors/Warnings tab
        sets the IV (and makes sure the two checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag \
        = main_win_obj.show_system_container_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.show_system_container_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.show_system_container_checkbutton.set_active(False)


    def on_system_date_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_errors_warnings_tab().

        Enables/disables showing dates (as well as times) in the Errors/
        Warnings tab. Toggling the corresponding Gtk.CheckButton in the Errors/
        Warnings tab sets the IV (and makes sure the two checkbuttons have the
        same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag \
        = main_win_obj.show_system_date_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.show_system_date_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.show_system_date_checkbutton.set_active(False)


    def on_system_multi_line_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_errors_warnings_tab().

        Enables/disables showing full error/warning messages in the Errors/
        Warnings tab. Toggling the corresponding Gtk.CheckButton in the Errors/
        Warnings tab sets the IV (and makes sure the two checkbuttons have the
        same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag \
        = main_win_obj.show_system_multi_line_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.show_system_multi_line_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.show_system_multi_line_checkbutton.set_active(False)


    def on_system_video_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_errors_warnings_tab().

        Enables/disables showing video names in the Errors/Warnings tab.
        Toggling the corresponding Gtk.CheckButton in the Errors/Warnings tab
        sets the IV (and makes sure the two checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag \
        = main_win_obj.show_system_video_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.show_system_video_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.show_system_video_checkbutton.set_active(False)


    def on_system_error_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_errors_warnings_tab().

        Enables/disables system errors in the 'Errors/Warnings' tab. Toggling
        the corresponding Gtk.CheckButton in the Errors/Warnings tab sets the
        IV (and makes sure the two checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag = main_win_obj.show_system_error_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.show_system_error_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.show_system_error_checkbutton.set_active(False)


    def on_system_keep_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_main_window_tab().

        Enables/disables keeping the total number of system messages in the tab
        label until the clear button is explicitly clicked.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.system_msg_keep_totals_flag:
            self.app_obj.set_system_msg_keep_totals_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.system_msg_keep_totals_flag:
            self.app_obj.set_system_msg_keep_totals_flag(False)


    def on_system_warning_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_errors_warnings_tab().

        Enables/disables system warnings in the 'Errors/Warnings' tab. Toggling
        the corresponding Gtk.CheckButton in the Errors/Warnings tab sets the
        IV (and makes sure the two checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        main_win_obj = self.app_obj.main_win_obj
        other_flag = main_win_obj.show_system_warning_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            main_win_obj.show_system_warning_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            main_win_obj.show_system_warning_checkbutton.set_active(False)


    def on_terminal_json_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_terminal_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the
        terminal.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_write_ignore_json_flag:
            self.app_obj.set_ytdl_write_ignore_json_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_write_ignore_json_flag:
            self.app_obj.set_ytdl_write_ignore_json_flag(False)


    def on_terminal_progress_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_terminal_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the
        terminal.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_write_ignore_progress_flag:
            self.app_obj.set_ytdl_write_ignore_progress_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_write_ignore_progress_flag:
            self.app_obj.set_ytdl_write_ignore_progress_flag(False)


    def on_terminal_stderr_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_terminal_tab().

        Enables/disables writing output from youtube-dl's STDERR to the
        terminal.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_write_stderr_flag:
            self.app_obj.set_ytdl_write_stderr_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_write_stderr_flag:
            self.app_obj.set_ytdl_write_stderr_flag(False)


    def on_terminal_stdout_button_toggled(self, checkbutton, checkbutton2, \
    checkbutton3):

        """Called from a callback in self.setup_output_terminal_tab().

        Enables/disables writing output from youtube-dl's STDOUT to the
        terminal.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2, checkbutton3 (Gtk.CheckButton): Additional
                checkbuttons to sensitise/desensitise, according to the new
                value of the flag

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_write_stdout_flag:
            self.app_obj.set_ytdl_write_stdout_flag(True)
            checkbutton2.set_sensitive(True)
            checkbutton3.set_sensitive(True)

        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_write_stdout_flag:
            self.app_obj.set_ytdl_write_stdout_flag(False)
            checkbutton2.set_sensitive(False)
            checkbutton3.set_sensitive(False)


    def on_terminal_system_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_terminal_tab().

        Enables/disables writing youtube-dl system commands to the terminal.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_write_system_cmd_flag:
            self.app_obj.set_ytdl_write_system_cmd_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_write_system_cmd_flag:
            self.app_obj.set_ytdl_write_system_cmd_flag(False)


    def on_test_sound_clicked(self, button, combo):

        """Called from callback in self.setup_operations_actions_tab().

        Plays the sound effect selected in the combobox.

        Args:

            button (Gtk.Button): The widget that was clicked

            combo (Gtk.ComboBox): The widget in which a sound effect is
                selected

        """

        self.app_obj.play_sound()


    def on_thumb_404_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of the 'Unable to download video thumbnail'
        warning messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_thumb_404_flag:
            self.app_obj.set_ignore_thumb_404_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_thumb_404_flag:
            self.app_obj.set_ignore_thumb_404_flag(False)


    def on_timeout_no_comments_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Sets the JSON timeout when not fetching comments.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_json_timeout_no_comments_time(spinbutton.get_value())


    def on_timeout_with_comments_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_operations_downloads_tab().

        Sets the JSON timeout when fetching comments.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.app_obj.set_json_timeout_with_comments_time(
            spinbutton.get_value(),
        )


    def on_twitch_live_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_ignore_tab().

        Enables/disables ignoring of the Twitch 'this channel is not live'
        error messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_twitch_not_live_flag:
            self.app_obj.set_ignore_twitch_not_live_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_twitch_not_live_flag:
            self.app_obj.set_ignore_twitch_not_live_flag(False)


    def on_update_combo_changed(self, combo):

        """Called from a callback in self.setup_downloader_paths_tab().

        Extracts the value visible in the combobox, converts it into another
        value, and uses that value to update the main application's IV.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.app_obj.set_ytdl_update_current(model[tree_iter][0])


    def on_uploader_button_toggled(self, checkbutton):

        """Called from callback in self.setup_windows_websites_tab().

        Enables/disables ignoring of deletion by uploader error messages.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ignore_yt_uploader_deleted_flag:
            self.app_obj.set_ignore_yt_uploader_deleted_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ignore_yt_uploader_deleted_flag:
            self.app_obj.set_ignore_yt_uploader_deleted_flag(False)


    def on_url_regex_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_urls_tab().

        Enables/disables treating the pattern as a regex, when searching/
        replacing URLs.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.url_change_regex_flag:
            self.app_obj.set_url_change_regex_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.url_change_regex_flag:
            self.app_obj.set_url_change_regex_flag(False)


    def on_use_first_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_database_tab().

        Enables/disables automatic loading of the first database file in the
        list.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.data_dir_use_first_flag:
            self.app_obj.set_data_dir_use_first_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.data_dir_use_first_flag:
            self.app_obj.set_data_dir_use_first_flag(False)


    def on_use_list_button_toggled(self, checkbutton):

        """Called from callback in self.setup_files_database_tab().

        Enables/disables automatic loading of an alternative database file, if
        the default one is locked.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.data_dir_use_list_flag:
            self.app_obj.set_data_dir_use_list_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.data_dir_use_list_flag:
            self.app_obj.set_data_dir_use_list_flag(False)


    def on_video_res_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_limits_tab().

        Enables/disables the video resolution limit. Toggling the corresponding
        Gtk.CheckButton in the Progress tab sets the IV (and makes sure the two
        checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        other_flag \
        = self.app_obj.main_win_obj.video_res_checkbutton.get_active()

        if (checkbutton.get_active() and not other_flag):
            self.app_obj.main_win_obj.video_res_checkbutton.set_active(True)
        elif (not checkbutton.get_active() and other_flag):
            self.app_obj.main_win_obj.video_res_checkbutton.set_active(False)


    def on_video_res_combo_changed(self, combo):

        """Called from a callback in self.setup_operations_limits_tab().

        Extracts the value visible in the combobox, converts it into another
        value, and uses that value to update the main application's IV.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.app_obj.set_video_res_default(model[tree_iter][0])


    def on_worker_button_toggled(self, checkbutton, alt_flag=False):

        """Called from callback in self.setup_operations_limits_tab().

        Enables/disables the simultaneous download limit. Toggling the
        corresponding Gtk.CheckButton in the Progress tab sets the IV (and
        makes sure the two checkbuttons have the same status).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            alt_flag (bool): If True, the alternative limit is toggled

        """

        main_win_obj = self.app_obj.main_win_obj

        if not alt_flag:

            other_flag = main_win_obj.num_worker_checkbutton.get_active()

            if (checkbutton.get_active() and not other_flag):
                main_win_obj.num_worker_checkbutton.set_active(True)
            elif (not checkbutton.get_active() and other_flag):
                main_win_obj.num_worker_checkbutton.set_active(False)

        else:

            # Alternative limits. There is no second widget to toggle
            if checkbutton.get_active() \
            and not self.app_obj.alt_num_worker_apply_flag:
                self.app_obj.set_alt_num_worker_apply_flag(True)
            elif not checkbutton.get_active() \
            and self.app_obj.alt_num_worker_apply_flag:
                self.app_obj.set_alt_num_worker_apply_flag(False)


    def on_worker_bypass_button_toggled(self, checkbutton):

        """Called from callback in self.setup_operations_livestreams_tab().

        Enables/disables bypassing the maximum simultaneous downloads limit
        when downloading broadcasting livestreams.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.num_worker_bypass_flag:
            self.app_obj.set_num_worker_bypass_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.num_worker_bypass_flag:
            self.app_obj.set_num_worker_bypass_flag(False)


    def on_worker_spinbutton_changed(self, spinbutton, alt_flag=False):

        """Called from callback in self.setup_operations_limits_tab().

        Sets the simultaneous download limit. Setting the value of the
        corresponding Gtk.SpinButton in the Progress tab sets the IV (and
        makes sure the two spinbuttons have the same value).

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

            alt_flag (bool): If True, the alternative limit is set

        """

        if not alt_flag:

            self.app_obj.main_win_obj.num_worker_spinbutton.set_value(
                spinbutton.get_value(),
            )

        else:

            # Alternative limits. There is no second widget to toggle
            self.app_obj.set_alt_num_worker(int(spinbutton.get_value()))


    def on_yt_remind_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_windows_dialogues_tab().

        Enables/disables reminding the user about the correct URL when adding
        YouTube channels.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.dialogue_yt_remind_flag:
            self.app_obj.set_dialogue_yt_remind_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.dialogue_yt_remind_flag:
            self.app_obj.set_dialogue_yt_remind_flag(False)


    def on_ytdl_fork_button_toggled(self, radiobutton, checkbutton, \
    checkbutton2, fork_type=None):

        """Called from callback in self.setup_downloader_forks_tab().

        Sets the youtube-dl fork to be used. See also
        self.on_ytdl_fork_changed().

        Args:

            radiobutton (Gtk.Radiobutton): The widget clicked

            checkbutton, checkbutton2 (Gtk.CheckButton): Other widgets to be
                updated

            fork_type (str): 'yt-dlp', 'youtube-dl', or None for any other fork

        """

        if radiobutton.get_active():

            if fork_type is None:

                fork_name = self.forks_entry.get_text()
                # (If the 'other fork' option is selected, but nothing is
                #   entered in the entry box, use youtube-dl as the downloader)
                if fork_name == '':
                    self.app_obj.set_ytdl_fork(None)
                else:
                    self.app_obj.set_ytdl_fork(fork_name)

                checkbutton.set_sensitive(False)
                checkbutton2.set_sensitive(False)
                self.forks_entry.set_sensitive(True)

            elif fork_type == 'youtube-dl':

                fork_name = fork_type
                self.app_obj.set_ytdl_fork(None)
                checkbutton.set_sensitive(False)
                checkbutton2.set_sensitive(False)
                self.forks_entry.set_text('')
                self.forks_entry.set_sensitive(False)

            elif fork_type == 'yt-dlp':

                fork_name = fork_type
                self.app_obj.set_ytdl_fork(fork_type)
                checkbutton.set_sensitive(True)
                checkbutton2.set_sensitive(True)
                self.forks_entry.set_text('')
                self.forks_entry.set_sensitive(False)

            # If the user has set a custom path to the youtube-dl executable
            #   that does not match 'fork_type', then the path must be reset
            if self.app_obj.ytdl_path_custom_flag:

                directory, fullname = os.path.split(self.app_obj.ytdl_path)
                filename, extension = os.path.splitext(fullname)
                if filename != fork_name:
                    self.filepaths_combo.set_active(0)


        self.update_ytdl_combos()


    def on_ytdl_fork_changed(self, entry):

        """Called from callback in self.setup_downloader_forks_tab().

        Sets the youtube-dl fork to be used. See also
        self.on_ytdl_fork_button_toggled().

        Args:

            entry (Gtk.Entry): The widget changed

        """

        if self.forks_radiobutton3.get_active():

            text = ttutils.strip_whitespace(entry.get_text())
            if text == '':

                self.app_obj.set_ytdl_fork(None)
                entry.set_icon_from_stock(
                    Gtk.EntryIconPosition.PRIMARY,
                    'gtk-yes',
                )

            else:

                # Git 466 - prevent the user from adding an absolute path;
                #   the value we're expecting is omething like 'youtube-dlc'
                if re.search(r'[^\w\-]', text):

                    entry.set_icon_from_stock(
                        Gtk.EntryIconPosition.PRIMARY,
                        'gtk-no',
                    )

                else:

                    self.app_obj.set_ytdl_fork(text)
                    entry.set_icon_from_stock(
                        Gtk.EntryIconPosition.PRIMARY,
                        'gtk-yes',
                    )

            self.update_ytdl_combos()


    def on_ytdl_fork_frame_clicked(self, event_box, event_button, radiobutton):

        """Called from a callback in self.setup_downloader_forks_tab().

        Enables/disables selecting a downloader by clicking anywhere in its
        containing frame.

        Args:

            event_box (Gtk.EventBox): Ignored

            event_button (Gdk.EventButton): Ignored

            radiobutton (Gtk.RadioButton): The radiobutton inside the clicked
                frame, which should be made active

        """

        if not radiobutton.get_active():
            radiobutton.set_active(True)


    def on_ytdl_path_button_clicked(self, button, entry):

        """Called from callback in self.setup_downloader_paths_tab().

        Sets a custom path to the youtube-dl executable.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to update

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Downloaders > File paths'
        )

        # Prompt the user for the new youtube-dl executable
        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Select the youtube-dl-compatible executable'),
            self,
            'open',
        )

        # (When the user first selects 'Use custom path', using the combobox,
        #   the default youtube-dl path continues to be used until they have
        #   specified a new path)
        if self.app_obj.ytdl_path != self.app_obj.ytdl_path_default:
            dialogue_win.set_current_folder(self.app_obj.ytdl_path)

        # Get the user's response
        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()
        if response == Gtk.ResponseType.OK:

            # Update the name of the fork to match the path
            directory, fullname = os.path.split(new_path)
            filename, extension = os.path.splitext(fullname)
            self.app_obj.set_ytdl_fork(filename)

            # Update widgets in the calling ('File paths') tab
            entry.set_text(new_path)
            # Update widgets in the 'Forks' tab
            if filename == 'youtube-dl':
                self.forks_radiobutton.set_active(True)
            elif filename == 'yt-dlp':
                self.forks_radiobutton2.set_active(True)
            else:
                self.forks_radiobutton3.set_active(True)
                self.forks_entry.set_text(filename)

            # Update the path to the executable (this must be done last,
            #   otherwise widget updates will override each other)
            self.app_obj.set_ytdl_path(new_path)
            self.app_obj.ytdl_update_dict['ytdl_update_custom_path'] \
            = ['python3', self.app_obj.ytdl_path, '-U']


    def on_ytdl_path_combo_changed(self, combo, entry, button):

        """Called from a callback in self.setup_downloader_paths_tab().

        Extracts the value visible in the combobox, converts it into another
        value, and uses that value to update the main application's IV.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            entry (Gtk.Entry): Another entry to check

            button (Gtk.Button): Another widget to modify

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        ytdl_path = model[tree_iter][1]

        if ytdl_path is not None:

            self.app_obj.set_ytdl_path(ytdl_path)
            self.app_obj.set_ytdl_path_custom_flag(False)
            entry.set_text('')
            button.set_sensitive(False)

        else:

            # Custom youtube-dl path, set by the entry/button
            # Until the user has selected their own executable, use the default
            #   one
            self.app_obj.set_ytdl_path(self.app_obj.ytdl_path_default)
            self.app_obj.ytdl_update_dict['ytdl_update_custom_path'] \
            = ['python3', self.app_obj.ytdl_path, '-U']
            self.app_obj.set_ytdl_path_custom_flag(True)

            entry.set_text(self.app_obj.ytdl_path)
            button.set_sensitive(True)


    def on_ytdl_verbose_button_toggled(self, checkbutton):

        """Called from a callback in self.setup_output_general_tab().

        Enables/disables writing verbose output (youtube-dl debugging mode).

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_write_verbose_flag:
            self.app_obj.set_ytdl_write_verbose_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_write_verbose_flag:
            self.app_obj.set_ytdl_write_verbose_flag(False)


    def on_ytdlp_install_button_toggled(self, checkbutton):

        """Called from callback in self.setup_downloader_forks_tab().

        Sets the flag to install yt-dlp with or without dependencies.

        Args:

            checkbutton (Gtk.Checkbutton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_fork_no_dependency_flag:
            self.app_obj.set_ytdl_fork_no_dependency_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_fork_no_dependency_flag:
            self.app_obj.set_ytdl_fork_no_dependency_flag(False)


    def on_ytdlp_nightly_button_toggled(self, checkbutton):

        """Called from callback in self.setup_downloader_forks_tab().

        Sets the flag to install nightly builds of yt-dlp.

        Args:

            checkbutton (Gtk.Checkbutton): The widget clicked

        """

        if checkbutton.get_active() \
        and not self.app_obj.ytdl_fork_nightly_flag:
            self.app_obj.set_ytdl_fork_nightly_flag(True)
        elif not checkbutton.get_active() \
        and self.app_obj.ytdl_fork_nightly_flag:
            self.app_obj.set_ytdl_fork_nightly_flag(False)


    # (Callback support functions)


    def try_switch_db(self, data_dir, button):

        """Called by self.on_data_dir_change_button_clicked() and
        .on_data_dir_switch_button_clicked().

        Having confirmed that a database directory specified by the user
        actually exists, attempt to load the database file inside it.

        Args:

            data_dir (str): The full path to the data directory

            button (Gtk.Button): A button to be possibly desensitised

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' System preferences > Files > Database'
        )

        dialogue_manager_obj = self.app_obj.dialogue_manager_obj

        # Database file already exists, so try to load it now
        if not self.app_obj.switch_db([data_dir, self]):

            # Load failed, and the user chose to shut down Tartube
            if self.app_obj.disable_load_save_lock_flag:

                return self.app_obj.stop()

            # Load failed for any other reason
            elif self.app_obj.disable_load_save_flag:

                button.set_sensitive(False)

                if not self.app_obj.disable_load_save_lock_flag:

                    if self.app_obj.disable_load_save_msg is not None:

                        dialogue_win = dialogue_manager_obj.show_msg_dialogue(
                            self.app_obj.disable_load_save_msg,
                            'error',
                            'ok',
                            self,           # Parent window is this window
                        )

                    else:

                        dialogue_win = dialogue_manager_obj.show_msg_dialogue(
                            _('Database file not loaded'),
                            'error',
                            'ok',
                            self,           # Parent window is this window
                        )

                # When load/save is disabled, this preference window can't be
                #   opened
                # Therefore, if load/save has just been disabled, close this
                #   window after the dialogue window closes
                dialogue_win.set_modal(True)
                dialogue_win.run()
                dialogue_win.destroy()
                if self.app_obj.disable_load_save_flag:
                    self.destroy()

            # Load not attempted
            else:

                dialogue_win = dialogue_manager_obj.show_msg_dialogue(
                    _('Did not try to load the database file'),
                    'error',
                    'ok',
                    self,           # Parent window is this window
                )

        else:

            # Load succeeded. Redraw the preference window, opening it at the
            #   same tab
            self.reset_window()
            self.select_switch_db_tab()

            if self.app_obj.disable_load_save_msg is not None:

                dialogue_manager_obj.show_msg_dialogue(
                    self.app_obj.disable_load_save_msg,
                    'info',
                    'ok',
                    self,           # Parent window is this window
                )

            else:

                dialogue_manager_obj.show_msg_dialogue(
                    _('Database file loaded'),
                    'info',
                    'ok',
                    self,           # Parent window is this window
                )


    def update_ytdl_combos(self):

        """Called initially by self.setup_downloader_paths_tab(), then by
        self.on_ytdl_fork_changed().

        Updates the contents of the two comboboxes in the tab, so that the
        youtube-dl fork is visible, rather than yotube-dl itself (if
        applicable).

        Also updates labels in the Operations > Livestreams tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: System preferences > Downloaders > Forks'
        )

        fork = standard = 'youtube-dl'
        if self.app_obj.ytdl_fork is not None:
            fork = self.app_obj.ytdl_fork

        ytdl_path_default = re.sub(
            standard,
            fork,
            self.app_obj.ytdl_path_default,
        )

        # First combo: Path to the youtube-dl executable
        self.path_liststore.set(
            self.path_liststore.get_iter(Gtk.TreePath(0)),
            0,
            _('Use default path') + ' (' + ytdl_path_default + ')',
        )

        ytdl_bin = re.sub(
            standard,
            fork,
            self.app_obj.ytdl_bin,
        )

        if os.name != 'nt':

            self.path_liststore.set(
                self.path_liststore.get_iter(Gtk.TreePath(1)),
                0,
                _('Use local path') + ' (' + ytdl_bin + ')',
            )

            ytdl_path_pypi = re.sub(
                standard,
                fork,
                self.app_obj.ytdl_path_pypi,
            )

            self.path_liststore.set(
                self.path_liststore.get_iter(Gtk.TreePath(3)),
                0,
                _('Use PyPI path') + ' (' + ytdl_path_pypi + ')',
            )

        # Second combo: Command for update operations (not always visible)
        if not __main__.__pkg_strict_install_flag__:

            count = -1
            for item in self.app_obj.ytdl_update_list:

                count += 1
                descrip = re.sub(
                    standard, fork, formats.YTDL_UPDATE_DICT[item]
                )
                self.cmd_liststore.set(
                    self.cmd_liststore.get_iter(Gtk.TreePath(count)),
                    1,
                    descrip,
                )

        # Update labels in the Operations > Livestreams tab
        self.setup_operations_livestreams_tab_update()
