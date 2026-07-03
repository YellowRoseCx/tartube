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
from tartube.preferences.base import GenericConfigWin, GenericEditWin, GenericPrefWin


class OptionsEditWin(GenericEditWin):

    """Python class for an 'edit window' to modify values in an
    options.OptionsManager object.

    Args:

        app_obj (mainapp.TartubeApp): The main application object

        edit_obj (options.OptionsManager): The object whose attributes will be
            edited in this window

        init_mode (str or None): If specified, a tab is automatically selected;
            one of the values specified in the comments to self.select_tab()

    """


    # Standard class methods


    def __init__(self, app_obj, edit_obj, init_mode=None):

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options window starts here.' \
            + ' In the menu, click Edit > General download options...'
        )

        Gtk.Window.__init__(self, title=_('Download options'))

        if self.is_duplicate(app_obj, edit_obj, init_mode):
            return

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # The options.OptionManager object being edited
        self.edit_obj = edit_obj


        # IV list - Gtk widgets
        # ---------------------
        self.grid = None                        # Gtk.Grid
        self.notebook = None                    # Gtk.Notebook
        self.reset_button = None                # Gtk.Button
        self.apply_button = None                # Gtk.Button
        self.ok_button = None                   # Gtk.Button
        self.cancel_button = None               # Gtk.Button
        # The 'embed_subs' option appears in two different places
        self.embed_checkbutton = None           # Gtk.CheckButton
        self.embed_checkbutton2 = None          # Gtk.CheckButton
        # The Gtk.ListStore containing the user's preferred video/audio formats
        #   (which must be redrawn when self.apply_changes() is called)
        self.formats_liststore = None           # Gtk.ListStore
        # The Gtk.CheckButton specifying whether obsolete formats should be
        #   hidden in that list
        self.formats_checkbutton = None         # Gtk.CheckButton

        # IV list - other
        # ---------------
        # Size (in pixels) of gaps between edit window widgets
        self.spacing_size = self.app_obj.default_spacing_size
        # Flag set to True if all four buttons ('Reset', 'Apply', 'Cancel' and
        #   'OK') are required, or False if just the 'OK' button is required
        self.multi_button_flag = True

        # When the user changes a value, it is not applied to self.edit_obj
        #   immediately; instead, it is stored temporarily in this dictionary
        # If the user clicks the 'OK' or 'Apply' buttons at the bottom of the
        #   window, the changes are applied to self.edit_obj
        # If the user clicks the 'Reset' or 'Cancel' buttons, the dictionary
        #   is emptied and the changes are lost
        # In this edit window, the key-value pairs directly correspond to those
        #   in options.OptionsManager.options_dict, rather than corresponding
        #   directly to attributes in the options.OptionsManager object
        # Because of that, we use our own .apply_changes() and .retrieve_val()
        #   functions, rather than relying on the generic functions
        # Key-value pairs are added to this dictionary whenever the user
        #   makes a change (so if no changes are made when the window is
        #   closed, the dictionary will still be empty)
        self.edit_dict = {}

        # IVs used to keep track of widget changes in the 'Files' tab
        # Flag set to to False when that tab's output template widgets are
        #   desensitised, True when sensitised
        self.template_flag = False
        # A list of Gtk widgets to (de)sensitise in when the flag changes
        self.template_widget_list = []

        # Code
        # ----

        # Set up the edit window
        self.setup()

        # Automatically open a particular tab, if required
        self.select_tab(init_mode)


    # Public class methods


    def is_duplicate(self, app_obj, edit_obj, init_mode):

        """Called by self.__init__.

        Don't open this edit window, if another with the same .edit_obj is
        already open.

        If 'init_mode' is specified, switch the visible tab in the existing
        preference window (if any).

        Args:

            app_obj (mainapp.TartubeApp): The main application object

            edit_obj (options.OptionsManager): The object whose attributes will
                be edited in this window

            init_mode (str or None): One of the values specified in the
                comments to self.select_tab()

        Return values:

            True if a duplicate is found, False if not

        """

        for config_win_obj in app_obj.main_win_obj.config_win_list:

            if isinstance(config_win_obj, GenericEditWin) \
            and config_win_obj.edit_obj == edit_obj:

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


#   def setup_button_strip():   # Inherited from GenericEditWin


#   def setup_gap():            # Inherited from GenericConfigWin


    def select_tab(self, init_mode=None):

        """Called by self.__init__().

        On startup, automatically open a particular tab, if required.

        Args:

            init_mode (str or None): If specified:
                - 'formats' - media formats
                - 'subs' - subtitles
                - (any other value is ignored)

        """

        if init_mode is not None:

            if init_mode == 'formats':
                self.select_formats_tab()
            elif init_mode == 'subs':
                self.select_subs_tab()


    def select_formats_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the media format options are
        displayed.
        """

        # Opens tab: self.setup_formats_preferred_tab()
        self.notebook.set_current_page(3)


    def select_subs_tab(self):

        """Can be called by anything.

        Makes the visible tab the one on which the subtitle options are
        displayed.
        """

        # Opens tab: self.setup_subtitles_options_tab()
        self.notebook.set_current_page(5)


    # (Non-widget functions)


    def apply_changes(self):

        """Called by self.on_button_ok_clicked() and
        self.on_button_apply_clicked().

        Any changes the user has made are temporarily stored in self.edit_dict.
        Apply to those changes to the object being edited.

        In this edit window we apply changes to self.edit_obj.options_dict
        (rather than to self.edit_obj's attributes directly, as in the generic
        function.)
        """

        # Apply any changes the user has made
        for key in self.edit_dict.keys():

            if key in self.edit_obj.options_dict:
                self.edit_obj.options_dict[key] = self.edit_dict[key]

        # The name can also be updated, if it has been changed (but it the
        #   entry was blank, keep the old name)
        if 'name' in self.edit_dict \
        and self.edit_dict['name'] != '':
            self.edit_obj.name = self.edit_dict['name']
        # The description can also be updated, even if it is blank
        if 'descrip' in self.edit_dict:
            self.edit_obj.descrip = self.edit_dict['descrip']

        # The changes can now be cleared
        self.edit_dict = {}

        # The user can specify multiple video/audio formats. If a mixture of
        #   both is specified, then video formats must be listed before audio
        #   formats (or youtube-dl won't download them all)
        # Tell the options.OptionManager object to rearrange them, if
        #   necessary
        self.edit_obj.rearrange_formats()
        # ...then redraw the textview in the Formats tab
        self.formats_tab_redraw_list()

        # Update the associated mainwin.DropZoneBox in the main window's
        #   Drag and Drop tab
        if self.edit_obj.uid in self.app_obj.classic_dropzone_list:
            dropzone_obj \
            = self.app_obj.main_win_obj.drag_drop_dict[self.edit_obj.uid]
            dropzone_obj.update_widgets()


    def retrieve_val(self, name, default=None):

        """Can be called by anything.

        Any changes the user has made are temporarily stored in self.edit_dict.

        In the generic function, each key corresponds to an attribute in the
        object being edited, self.edit_obj. In this window, it corresponds to a
        key in self.edit_obj.options_dict.

        If 'name' exists as a key in that dictionary, retrieve the
        corresponding value and return it. Otherwise, the user hasn't yet
        modified the value, so retrieve directly from the attribute in the
        object being edited.

        Args:

            name (str): The name of the attribute in the object being edited

        Return values:

            The original or modified value of that attribute

        """

        if name in self.edit_dict:

            return self.edit_dict[name]

        elif name == 'uid' \
        or name == 'name' \
        or name == 'descrip' \
        or name == 'dbid_list':

            return getattr(self.edit_obj, name)

        elif name in self.edit_obj.options_dict:

            value = self.edit_obj.options_dict[name]
            if type(value) is list or type(value) is dict:
                return value.copy()
            else:
                return value

        elif default is not None:

            return default

        else:

            return self.app_obj.system_error(
                404,
                'Unrecognised property name \'' + name + '\'',
            )


    def add_tooltip(self, text, widget=None, widget2=None, widget3=None, \
    widget4=None, widget5=None):

        """Called by various tabs, to show the equivalent youtube-dl switches
        for each Tartube download option.

        Adds the tooltip 'text' to any specified widgets (maximum four).

        Args:

            text (str): The text to use in the tooltip

            widget, widget2, widget3, widget4, widget5 (widget or None): Any
                Gtk widget for which we can call .set_tooltip_text()

        """

        if widget is not None:
            widget.set_tooltip_text(text)
        if widget2 is not None:
            widget2.set_tooltip_text(text)
        if widget3 is not None:
            widget3.set_tooltip_text(text)
        if widget4 is not None:
            widget4.set_tooltip_text(text)
        if widget5 is not None:
            widget5.set_tooltip_text(text)


    # (Setup tabs)


    def setup_tabs(self):

        """Called by self.setup(), .on_button_apply_clicked() and
        .on_button_reset_clicked().

        Sets up the tabs for this edit window.
        """

        self.setup_name_tab()
        self.setup_downloads_tab()
        self.setup_files_tab()
        self.setup_formats_tab()
        if not self.app_obj.simple_options_flag:
            self.setup_post_process_tab()
        else:
            self.setup_convert_tab()
        self.setup_subtitles_tab()
        if not self.app_obj.simple_options_flag:
            self.setup_advanced_tab()


    def setup_name_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Name' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Name'
        )

        tab, grid = self.add_notebook_tab(_('_Name'))
        grid_width = 3

        label = self.add_label(grid,
            _('Name for these download options'),
            0, 0, 1, 1,
        )

        entry = self.add_entry(grid,
            'name',
            1, 0, 1, 1,
        )
        entry.set_hexpand(True)

        entry2 = self.add_entry(grid,
            None,
            2, 0, 1, 1,
        )
        entry2.set_text('#' + str(self.edit_obj.uid))
        entry2.set_hexpand(False)
        entry2.set_max_length(8)

        label2 = self.add_label(grid,
            _('Description'),
            0, 1, 1, 1,
        )

        entry3 = self.add_entry(grid,
            'descrip',
            1, 1, 2, 1,
        )
        entry3.set_hexpand(True)

        label3 = self.add_label(grid,
            _('Download options applied to'),
            0, 2, 1, 1,
        )

        entry4 = self.add_entry(grid,
            None,
            1, 2, 2, 1,
        )
        entry4.set_editable(False)

        if self.edit_obj == self.app_obj.general_options_obj:
            entry4.set_text(_('All channels, playlists and folders'))
        elif self.edit_obj == self.app_obj.classic_options_obj:
            entry4.set_text(_('Downloads in the Classic Mode tab'))
        elif self.edit_obj.dbid_list:
            entry4.set_text(self.get_options_applied_text(self.edit_obj))
        else:
            entry4.set_text(_('These options are not applied to anything'))

        if self.app_obj.simple_options_flag:

            label4 = self.add_label(grid,
                _(
                'Additional download options, e.g. --write-subs (do not use' \
                + ' -o or --output)',
                ),
                0, 3, grid_width, 1,
            )

        else:

            label4 = self.add_label(grid,
                _('Additional download options'),
                0, 3, 1, 1,
            )

            if os.name == 'nt':

                checkbutton = self.add_checkbutton(grid,
                    _(
                    'Use ONLY these options (Tartube adds the output folder)',
                    ),
                    None,
                    1, 3, 2, 1,
                )
                # (Signal connect appears below)

            else:

                checkbutton = self.add_checkbutton(grid,
                    _(
                    'Use ONLY these options (Tartube adds the output' \
                    + ' directory)',
                    ),
                    None,
                    1, 3, 2, 1,
                )
                # (Signal connect appears below)

            checkbutton.set_active(self.retrieve_val('direct_cmd_flag'))

            checkbutton2 = self.add_checkbutton(grid,
                _('If URLs are specified below, use only those URLs'),
                'direct_url_flag',
                1, 4, 2, 1,
            )

            # (Signal connects from above)
            checkbutton.connect(
                'toggled',
                self.on_direct_cmd_toggled,
                checkbutton2,
            )

        textview, textbuffer = self.add_textview(grid,
            'extra_cmd_string',
            0, 5, grid_width, 1,
        )
        self.add_tooltip(
            _(
                'Arguments containing special shell characters' \
                + '(+ - & < > = ? * ! : ; \\ / and brackets) should be' \
                + ' enclosed within quotes, e.g. -f "(137/136)"',
            ),
            label4,
            textview,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 6, grid_width, 1)

        if self.app_obj.simple_options_flag:
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
        if not self.app_obj.simple_options_flag:
            button.set_label(_('Hide advanced download options'))
        else:
            button.set_label(_('Show advanced download options'))
        button.set_hexpand(True)
        button.connect('clicked', self.on_simple_options_clicked)

        frame2 = self.add_pixbuf(grid2,
            'copy_large',
            0, 1, 1, 1,
        )
        frame2.set_hexpand(False)

        button2 = Gtk.Button(
            _('Import general download options into this window'),
        )
        grid2.attach(button2, 1, 1, 1, 1)
        button2.set_hexpand(True)
        button2.connect('clicked', self.on_clone_options_clicked)
        if self.edit_obj == self.app_obj.general_options_obj:
            # No point cloning the General Options Manager onto itself
            button2.set_sensitive(False)

        frame3 = self.add_pixbuf(grid2,
            'warning_large',
            0, 2, 1, 1,
        )
        frame3.set_hexpand(False)

        button3 = Gtk.Button(
            _('Completely reset all download options to their default values'),
        )
        grid2.attach(button3, 1, 2, 1, 1)
        button3.set_hexpand(True)
        button3.connect('clicked', self.on_reset_options_clicked)


    def setup_downloads_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Downloads' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads'
        )

        # Simple options only
        if self.app_obj.simple_options_flag:

            tab, grid = self.add_notebook_tab(_('_Downloads'))

            row_count = self.downloads_age_widgets(grid, 0)
            row_count = self.downloads_size_limit_widgets(grid, row_count)
            row_count = self.downloads_date_widgets(grid, row_count)
            row_count = self.downloads_views_widgets(grid, row_count)

        # All options
        else:

            # Add this tab...
            tab, grid = self.add_notebook_tab(_('_Downloads'), 0)

            # ...and an inner notebook...
            inner_notebook = self.add_inner_notebook(grid)

            # ...with its own tabs
            self.setup_downloads_general_tab(inner_notebook)
            self.setup_downloads_videos_tab(inner_notebook)
            self.setup_downloads_live_tab(inner_notebook)
            self.setup_downloads_playlists_tab(inner_notebook)
            self.setup_downloads_limits_tab(inner_notebook)
            self.setup_downloads_comments_tab(inner_notebook)
            self.setup_downloads_extractor_tab(inner_notebook)
            self.setup_downloads_filtering_tab(inner_notebook)
            self.setup_downloads_external_tab(inner_notebook)


    def setup_downloads_general_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'General' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > General' \
            + ' (to make hidden tabs visible, click the \'Show advanced' \
            + ' download options\' button in the Name tab)'
        )

        tab, grid = self.add_inner_notebook_tab('_General', inner_notebook)

        # General download options
        self.add_label(grid,
            '<u>' + _('General download options') + '</u>',
            0, 0, 1, 1,
        )

        row_count = 1
        row_count = self.downloads_general_widgets(grid, row_count)

        # General download options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('General download options') + '</u>' + self.ytdlp_only(),
            0, (row_count + 1), 2, 1,
        )

        label = self.add_label(grid,
            _(
                'Number of fragments of a DASH/HLS video to download' \
                + ' concurrently',
            ),
            0, (row_count + 2), 1, 1
        )

        spinbutton = self.add_spinbutton(grid,
            1, None, 1,
            'concurrent_fragments',
            1, (row_count + 2), 1, 1
        )
        self.add_tooltip('-N, --concurrent-fragments N', label, spinbutton)

        label2 = self.add_label(grid,
            _(
                'Minimum download rate (bytes/sec) below which throttling' \
                + ' is assumed',
            ),
            0, (row_count + 3), 1, 1
        )

        spinbutton2 = self.add_spinbutton(grid,
            0, None, 100,
            'throttled_rate',
            1, (row_count + 3), 1, 1
        )
        self.add_tooltip('--throttled-rate RATE', label2, spinbutton2)


    def setup_downloads_videos_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'Videos' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Videos'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Videos'),
            inner_notebook,
        )
        grid_width = 2

        # Video selection options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Video selection options') + '</u>' + self.ytdlp_only(),
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Stop download process when encountering a file in the archive'),
            'break_on_existing',
            0, 1, grid_width, 1,
        )
        self.add_tooltip('--break-on-existing', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _(
                'Stop download process when encountering a file that has' \
                + ' been filtered out',
            ),
            'break_on_reject',
            0, 2, grid_width, 1,
        )
        self.add_tooltip('--break-on-reject', checkbutton2)

        label = self.add_label(grid,
            _('Number of failures allowed before rest of playlist is skipped'),
            0, 3, 1, 1
        )

        spinbutton = self.add_spinbutton(grid,
            0, None, 1,
            'skip_playlist_after_errors',
            1, 3, 1, 1
        )
        self.add_tooltip('--skip-playlist-after-errors N', label, spinbutton)

        # Verbosity and simulation options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Verbosity and simulation options') + '</u>' \
            + self.ytdlp_only(),
            0, 4, grid_width, 1,
        )

        checkbutton3 = self.add_checkbutton(grid,
            _(
                'Ignore \'No video formats\' error (useful for extracting' \
                + ' metadata from unavailable videos)',
            ),
            'ignore_no_formats_error',
            0, 5, grid_width, 1,
        )
        self.add_tooltip('--ignore-no-formats-error', checkbutton3)

        checkbutton4 = self.add_checkbutton(grid,
            _(
                'Force download archive entries to be written as long as' \
                + ' no errors occur',
            ),
            'force_write_archive',
            0, 6, grid_width, 1,
        )
        self.add_tooltip('--force-write-archive', checkbutton4)

        # Video/audio merge options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Video/audio merge options') + '</u>' \
            + self.ytdlp_only(),
            0, 7, grid_width, 1,
        )

        checkbutton5 = self.add_checkbutton(grid,
            _('Allow multiple video streams to be merged into a single file'),
            'video_multistreams',
            0, 8, grid_width, 1,
        )
        self.add_tooltip('--video-multistreams', checkbutton5)

        checkbutton6 = self.add_checkbutton(grid,
            _('Allow multiple audio streams to be merged into a single file'),
            'audio_multistreams',
            0, 9, grid_width, 1,
        )
        self.add_tooltip('--audio-multistreams', checkbutton6)


    def setup_downloads_live_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'Live' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Live'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Live'),
            inner_notebook,
        )
        grid_width = 2

        # Livestream options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Livestream options') + '</u>' + self.ytdlp_only(),
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Download livestreams from start (experimental, YouTube only)'),
            'live_from_start',
            0, 1, grid_width, 1,
        )
        self.add_tooltip('--live-from-start', checkbutton)

        label = self.add_label(grid,
            _('Minimum seconds to wait for scheduled streams'),
            0, 2, 1, 1
        )

        spinbutton = self.add_spinbutton(grid,
            0, None, 1,
            'wait_for_video_min',
            1, 2, 1, 1
        )
        self.add_tooltip('--wait-for-video MIN', label, spinbutton)


    def setup_downloads_playlists_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'Playlists' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Playlists'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Playlists'),
            inner_notebook,
        )

        row_count = self.downloads_playlist_widgets(grid, 0)


    def setup_downloads_limits_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'Limits' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Limits'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('L_imits'),
            inner_notebook,
        )

        row_count = self.downloads_age_widgets(grid, 0)
        row_count = self.downloads_size_limit_widgets(grid, row_count)
        row_count = self.downloads_date_widgets(grid, row_count)
        row_count = self.downloads_views_widgets(grid, row_count)


    def setup_downloads_comments_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'Comments' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Comments'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Comments'),
            inner_notebook,
        )

        # Video comments (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Video comments') + '</u>' + self.ytdlp_only(),
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('When checking videos, store comments in the metadata file'),
            None,
            0, 1, 1, 1,
        )
        # (Signal connect appears below)
        checkbutton.set_active(self.retrieve_val('check_fetch_comments', False))
        self.add_tooltip('--write-comments', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('When downloading videos, store comments in the metadata file'),
            None,
            0, 2, 1, 1,
        )
        # (Signal connect appears below)
        checkbutton2.set_active(self.retrieve_val('dl_fetch_comments', False))
        self.add_tooltip('--write-comments', checkbutton2)

        self.add_label(grid,
            '<i>' + _('Warning: fetching comments will increase the download' \
            + ' time, perhaps by a lot!') + '</i>',
            0, 3, 1, 1,
        )

        checkbutton3 = self.add_checkbutton(grid,
            _('Also store comments in the Tartube database'),
            'store_comments_in_db',
            0, 4, 1, 1,
        )
        if not checkbutton.get_active() \
        and not checkbutton2.get_active():
            checkbutton3.set_sensitive(False)

        # (Signal connects from above)
        checkbutton.connect(
            'toggled',
            self.on_check_fetch_comments_button_toggled,
            checkbutton3,
        )
        checkbutton2.connect(
            'toggled',
            self.on_dl_comment_fetch_button_toggled,
            checkbutton3,
        )

        self.add_label(grid,
            '<i>' + _(
                'Warning: storing comments will increase the size of' \
                + ' Tartube\'s datbase, perhaps by a lot!',
            ) + '</i>',
            0, 5, 1, 1,
        )


    def setup_downloads_extractor_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'Extractor' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Extractor'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Extractor'),
            inner_notebook,
        )
        grid_width = 2

        # Extractor options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Extractor options') + '</u>' + self.ytdlp_only(),
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            'Number of retries for known extractor errors',
            0, 1, 1, 1,
        )

        combo_list = [
            '', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'infinite',
        ]

        combo = self.add_combo(grid,
            combo_list,
            'extractor_retries',
            1, 1, 1, 1
        )
        combo.set_hexpand(True)
        self.add_tooltip('--extractor-retries RETRIES', label, combo)

        checkbutton = self.add_checkbutton(grid,
            _('Do not process dynamic DASH manifests'),
            'no_allow_dynamic_mpd',
            0, 2, grid_width, 1,
        )
        self.add_tooltip('--no-allow-dynamic-mpd', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _(
                'Split HLS playlists to different formats at discontinuities' \
                + ' such as ad breaks',
            ),
            'hls_split_discontinuity',
            0, 3, grid_width, 1,
        )
        self.add_tooltip('--hls-split-discontinuity', checkbutton2)

        # Extractor arguments
        self.add_label(grid,
            '<u>' + _('Extractor arguments') + '</u>',
            0, 4, grid_width, 1,
        )

        label2 = self.add_label(grid,
            '<i>' + _('One argument per line, e.g.') \
            + '</i> youtube:skip=dash,hls;player_client=android',
            0, 5, grid_width, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            'extractor_args_list',
            0, 6, grid_width, 1,
        )
        self.add_tooltip('--extractor-args KEY:ARGS', label2, textview)


    def setup_downloads_filtering_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'Filtering' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Filtering'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Filtering'),
            inner_notebook,
        )

        row_count = self.downloads_filtering_widgets(grid, 0)


    def setup_downloads_external_tab(self, inner_notebook):

        """Called by self.setup_downloads_tab().

        Sets up the 'External' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > External'
        )

        tab, grid = self.add_inner_notebook_tab(_('E_xternal'), inner_notebook)

        row_count = self.downloads_external_widgets(grid, 0)


    def setup_files_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Files' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files'
        )

        # Add this tab...
        tab, grid = self.add_notebook_tab(_('_Files'), 0)

        # ...and an inner notebook...
        inner_notebook = self.add_inner_notebook(grid)

        # ...with its own tabs
        self.setup_files_names_tab(inner_notebook)
        if not self.app_obj.simple_options_flag:
            self.setup_files_override_tab(inner_notebook)
            self.setup_files_paths_tab(inner_notebook)
        self.setup_files_filesystem_tab(inner_notebook)
        self.setup_files_cookies_tab(inner_notebook)
        if not self.app_obj.simple_options_flag:
            self.setup_files_shortcuts_tab(inner_notebook)
        self.setup_files_write_move_tab(inner_notebook)
        self.setup_files_keep_tab(inner_notebook)


    def setup_files_names_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'File names' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files > File names'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('File _names'),
            inner_notebook,
        )
        grid_width = 2

        # File name options
        self.add_label(grid,
            '<u>' + _('File name options') + '</u>',
            0, 0, 2, 1,
        )

        label = self.add_label(grid,
            _('Format for video file names'),
            0, 1, 1, 1,
        )
        label.set_hexpand(False)

        store = Gtk.ListStore(int, str)
        num_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
        for num in num_list:
            store.append( [num, formats.FILE_OUTPUT_NAME_DICT[num]] )

        current_format = self.edit_obj.options_dict['output_format']
        current_template = formats.FILE_OUTPUT_CONVERT_DICT[current_format]
        if current_template is None:
            current_template = self.edit_obj.options_dict['output_template']

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, 0, 2, 1, 1)
        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, "text", 1)
        combo.set_entry_text_column(1)
        combo.set_active(num_list.index(current_format))
        combo.set_hexpand(False)
        # (Signal connect appears below)
        self.add_tooltip('-o, --output TEMPLATE', combo)

        label2 = self.add_label(grid,
            _('File output template'),
            1, 1, 1, 1,
        )
        label2.set_hexpand(True)

        entry = self.add_entry(grid,
            None,
            1, 2, 1, 1,
        )
        entry.set_text(current_template)
        entry.set_hexpand(True)
        # (Signal connect appears below)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

        # Add widgets to a list, so we can sensitise them when a custom
        #   template is selected, and desensitise them the rest of the time
        self.template_widget_list = [entry]

        self.add_label(grid2,
            _('Add to template:'),
            0, 0, 1, 1,
        )

        master_list = [
            _('Video properties'),
            [
                'id',               _('Video ID'),
                'title',            _('Video title'),
                'display_id',       _('Alternative video ID'),
                'alt_title',        _('Secondary video title'),
                'url',              _('Video URL'),
                'ext',              _('Video filename extension'),
                'license',          _('Video licence'),
                'age_limit',        _('Age restriction (years)'),
                'is_live',          _('Is a livestream'),
                'video_autonumber', _('Autonumber videos'),
                'playlist_autonumber',
                                    _('Autonumber videos (playlists)'),
            ],
            _('Creator/uploader'),
            [
                'uploader',         _('Full name of video uploader'),
                'uploader_id',      _('Uploader ID'),
                'creator',          _('Nickname/ID of video uploader'),
                'channel',          _('Channel name'),
                'channel_id',       _('Channel ID'),
                'playlist',         _('Playlist name'),
                'playlist_id',      _('Playlist ID'),
                'playlist_index',   _('Video index in playlist'),
            ],
            _('Date/time/location'),
            [
                'release_date',     _('Release date (YYYYMMDD)'),
                'release_date_custom',
                                    _('Release date (custom format)'),
                'timestamp',        _('Release time (UNIX timestamp)'),
                'timestamp_custom', _('Release time (custom format)'),
                'upload_date',      _('Upload date (YYYYMMDD)'),
                'upload_date_custom',
                                    _('Upload date (custom format)'),
                'duration',         _('Video length (seconds)'),
                'duration_custom',  _('Video length (custom format)'),
                'location',         _('Filming location'),
            ],
            _('Time format'),
            [],
            _('Video format'),
            [
                'format',           _('Video format'),
                'format_id',        _('Video format code'),
                'width',            _('Video width'),
                'height',           _('Video height'),
                'resolution',       _('Video resolution'),
                'fps',              _('Video frame rate'),
                'tbr',              _('Average video/audio bitrate (KiB/s)'),
                'vbr',              _('Average video bitrate (KiB/s)'),
                'abr',              _('Average audio bitrate (KiB/s)'),
            ],
            _('Ratings/comments'),
            [
                'view_count',       _('Number of views'),
                'like_count',       _('Number of positive ratings'),
                'dislike_count',    _('Number of negative ratings'),
                'average_rating',   _('Average rating'),
                'repost_count',     _('Number of reposts'),
                'comment_count',    _('Number of comments'),
            ],
        ]

        # (Create the entry and its button first, so they are available to the
        #   callbacks)
        entry2 = Gtk.Entry()
        entry2.set_hexpand(True)

        button = Gtk.Button(_('Reset'))
        button.set_sensitive(False)
        # (Signal connect appears below)

        row_num = -1
        while master_list:

            row_num += 1

            this_title = master_list.pop(0)
            this_store_list = master_list.pop(0)

            self.add_label(grid2,
                this_title,
                1, row_num, 1, 1,
            )

            if this_title == _('Time format'):

                grid2.attach(entry2, 2, row_num, 1, 1)
                grid2.attach(button, 3, row_num, 1, 1)

                self.template_widget_list.append(entry2)
                self.template_widget_list.append(button)

            else:

                this_store = Gtk.ListStore(str)
                # (The dictionary is used by
                #   self.on_file_tab_add_button_clicked() to translate the
                #   visible string into the string youtube-dl uses)
                this_store_dict = {}
                while this_store_list:
                    item = this_store_list.pop(0)
                    mod_item = this_store_list.pop(0)

                    this_store_dict[mod_item] = item
                    this_store.append( [mod_item] )

                this_combo = Gtk.ComboBox.new_with_model(this_store)
                grid2.attach(this_combo, 2, row_num, 1, 1)
                this_renderer_text = Gtk.CellRendererText()
                this_combo.pack_start(this_renderer_text, True)
                this_combo.add_attribute(this_renderer_text, "text", 0)
                this_combo.set_entry_text_column(0)
                this_combo.set_active(0)

                this_button = Gtk.Button(_('Add'))
                grid2.attach(this_button, 3, row_num, 1, 1)
                this_button.connect(
                    'clicked',
                    self.on_file_tab_add_button_clicked,
                    entry,
                    entry2,
                    this_combo,
                    this_store_dict,
                )

                self.template_widget_list.append(this_combo)
                self.template_widget_list.append(this_button)

            if this_title == _('Date/time/location'):

                # (Signal connects from above)
                this_combo.connect(
                    'changed',
                    self.on_date_time_combo_changed,
                    entry2,
                    button,
                    this_store_dict,
                )

                button.connect(
                    'clicked',
                    self.on_file_tab_reset_button_clicked,
                    entry2,
                    this_combo,
                    this_store_dict,
                )

        # (Signal connects from above)
        combo.connect(
            'changed',
            self.on_file_tab_main_combo_changed,
            entry,
            entry2,
            button,
        )
        entry.connect('changed', self.on_file_tab_main_entry_changed)

        # (De)sensitise widgets in self.template_widget_list
        if current_format == 0:
            self.file_tab_sensitise_widgets(True)
        else:
            self.file_tab_sensitise_widgets(False)


    def setup_files_override_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Override' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files > Override'
        )


        tab, grid = self.add_inner_notebook_tab(
            _('_Override'),
            inner_notebook,
        )
        grid_width = 4

        # List of output filename templates (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('List of output filename templates') + '</u>' \
            + self.ytdlp_only(),
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'Overrides the output template in the \'File names\' tab',
            ) + '</i>',
            0, 1, grid_width, 1,
        )

        # (GenericConfigWin.add_treeview() doesn't support multiple columns, so
        #   we'll do everything ourselves)
        frame = Gtk.Frame()
        grid.attach(frame, 0, 2, grid_width, 1)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_headers_visible(True)

        for i, column_title in enumerate([ _('Type'), _('Template') ]):

            renderer_text = Gtk.CellRendererText()
            column_text = Gtk.TreeViewColumn(
                column_title,
                renderer_text,
                text=i,
            )
            treeview.append_column(column_text)
            column_text.set_resizable(True)

        liststore = Gtk.ListStore(str, str)
        treeview.set_model(liststore)

        # Initialise the list
        self.setup_files_override_tab_update_treeview(liststore)

        # Add editing buttons
        label = self.add_label(grid,
            _('Output type'),
            0, 3, 1, 1,
        )

        combo_list = formats.YTDLP_OUTPUT_TYPE_LIST.copy()
        combo = self.add_combo(grid,
            combo_list,
            None,
            1, 3, 1, 1,
        )
        combo.set_active(0)

        label2 = self.add_label(grid,
            _('Output template'),
            0, 4, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            1, 4, (grid_width - 1), 1,
        )

        button = Gtk.Button()
        grid.attach(button, 0, 5, 1, 1)
        button.set_label(_('Add'))
        button.connect(
            'clicked',
            self.on_ytdlp_output_add_button_clicked,
            liststore,
            combo,
            entry,
        )

        button2 = Gtk.Button()
        grid.attach(button2, 1, 5, 1, 1)
        button2.set_label(_('Delete'))
        button2.connect(
            'clicked',
            self.on_ytdlp_output_delete_button_clicked,
            treeview,
        )

        button3 = Gtk.Button()
        grid.attach(button3, 3, 5, 1, 1)
        button3.set_label(_('Refresh list'))
        button3.connect(
            'clicked',
            self.on_ytdlp_output_refresnh_button_clicked,
            treeview,
        )


    def setup_files_override_tab_update_treeview(self, liststore):

        """Can be called by anything.

        Fills or updates the treeview.

        Args:

            liststore (Gtk.ListStore): The treeview's model

        """

        liststore.clear()

        for item in self.retrieve_val('output_format_list'):

            # (Each 'item' is in the form TYPES:TEMPLATE)
            match = re.search(r'^([^\:]+)\:(.*)', item)
            if match:
                liststore.append([ match.groups()[0], match.groups()[1] ])


    def setup_files_paths_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Paths' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files > Paths'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Paths'),
            inner_notebook,
        )
        grid_width = 5

        # List of output paths (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('List of output paths') + '</u>' + self.ytdlp_only(),
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

        for i, column_title in enumerate([ _('Type'), _('Path') ]):

            renderer_text = Gtk.CellRendererText()
            column_text = Gtk.TreeViewColumn(
                column_title,
                renderer_text,
                text=i,
            )
            treeview.append_column(column_text)
            column_text.set_resizable(True)

        liststore = Gtk.ListStore(str, str)
        treeview.set_model(liststore)

        # Initialise the list
        self.setup_files_paths_tab_update_treeview(liststore)

        # Add editing buttons
        label = self.add_label(grid,
            _('Output type'),
            0, 2, 1, 1,
        )

        combo_list = formats.YTDLP_OUTPUT_TYPE_LIST.copy()
        combo_list.insert(0, 'home')
        combo_list.insert(1, 'temp')
        combo = self.add_combo(grid,
            combo_list,
            None,
            1, 2, 1, 1,
        )
        combo.set_active(0)

        label2 = self.add_label(grid,
            _('Output path'),
            0, 3, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            1, 3, (grid_width - 2), 1,
        )
        entry.set_editable(False)

        button = Gtk.Button()
        grid.attach(button, 4, 3, 1, 1)
        button.set_label(_('Set'))
        button.connect(
            'clicked',
            self.on_ytdlp_paths_set_button_clicked,
            entry,
        )

        button2 = Gtk.Button()
        grid.attach(button2, 0, 4, 1, 1)
        button2.set_label(_('Add'))
        button2.connect(
            'clicked',
            self.on_ytdlp_paths_add_button_clicked,
            liststore,
            combo,
            entry,
        )

        button3 = Gtk.Button()
        grid.attach(button3, 1, 4, 1, 1)
        button3.set_label(_('Delete'))
        button3.connect(
            'clicked',
            self.on_ytdlp_paths_delete_button_clicked,
            treeview,
        )

        button4 = Gtk.Button()
        grid.attach(button4, 3, 4, 2, 1)
        button4.set_label(_('Refresh list'))
        button4.connect(
            'clicked',
            self.on_ytdlp_paths_refresh_button_clicked,
            treeview,
        )


    def setup_files_paths_tab_update_treeview(self, liststore):

        """Can be called by anything.

        Fills or updates the treeview.

        Args:

            liststore (Gtk.ListStore): The treeview's model

        """

        liststore.clear()

        for item in self.retrieve_val('output_path_list'):

            # (Each 'item' is in the form TYPES:PATH)
            match = re.search(r'^([^\:]+)\:(.*)', item)
            if match:
                liststore.append([ match.groups()[0], match.groups()[1] ])


    def setup_files_filesystem_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Filesystem' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files > Filesystem'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Filesystem'),
            inner_notebook,
        )
        grid_width = 2

        # Filesystem options
        self.add_label(grid,
            '<u>' + _('Filesystem options') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Restrict filenames to ASCII characters'),
            'restrict_filenames',
            0, 1, grid_width, 1,
        )
        self.add_tooltip('--restrict-filenames', checkbutton)

        if not self.app_obj.simple_options_flag:

            checkbutton2 = self.add_checkbutton(grid,
                _('Don\'t use the server\'s file modification time'),
                'nomtime',
                0, 2, grid_width, 1,
            )
            self.add_tooltip('--no-mtime', checkbutton2)

        checkbutton3 = self.add_checkbutton(grid,
            _('Download all videos into this folder'),
            None,
            0, 3, 1, 1,
        )
        # (Signal connect appears below)

        # (Currently, only three fixed folders are elligible for this mode, so
        #   we'll just add them individually)
        store = Gtk.ListStore(GdkPixbuf.Pixbuf, int, str)
        # (Guard against mainapp.TartubeApp.debug_open_options_win_flag being
        #   set...)
        count = 0
        if self.app_obj.fixed_misc_folder:
            store.append([
                self.app_obj.main_win_obj.pixbuf_dict['folder_green_small'],
                self.app_obj.fixed_misc_folder.dbid,
                self.app_obj.fixed_misc_folder.name,
            ])
            misc_index = count
            count += 1

        if self.app_obj.fixed_clips_folder:
            store.append([
                self.app_obj.main_win_obj.pixbuf_dict['folder_green_small'],
                self.app_obj.fixed_clips_folder.dbid,
                self.app_obj.fixed_clips_folder.name,
            ])
            clips_index = count
            count += 1

        if self.app_obj.fixed_temp_folder:
            store.append([
                self.app_obj.main_win_obj.pixbuf_dict['folder_blue_small'],
                self.app_obj.fixed_temp_folder.dbid,
                self.app_obj.fixed_temp_folder.name,
            ])
            temp_index = count
            count += 1

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, 1, 3, 1, 1)

        renderer_pixbuf = Gtk.CellRendererPixbuf()
        combo.pack_start(renderer_pixbuf, False)
        combo.add_attribute(renderer_pixbuf, 'pixbuf', 0)

        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 2)

        combo.set_entry_text_column(0)
        combo.set_hexpand(True)
        # (Signal connect appears below)

        # (Acceptable values are 'temp', 'misc', 'clips'
        current_override = self.edit_obj.options_dict['use_fixed_folder']
        if current_override is None:
            checkbutton3.set_active(False)
            combo.set_sensitive(False)
            combo.set_active(0)

        else:
            checkbutton3.set_active(True)
            combo.set_sensitive(True)
            if current_override == 'temp':
                combo.set_active(temp_index)
            elif current_override == 'misc':
                combo.set_active(misc_index)
            elif current_override == 'clips':
                combo.set_active(clips_index)
            else:
                # Default to the 'Unsorted Videos' folder
                combo.set_active(misc_index)

        # (Signal connects from above)
        checkbutton3.connect('toggled', self.on_fixed_folder_toggled, combo)
        combo.connect('changed', self.on_fixed_folder_changed)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 4, grid_width, 1)

        # Filesystem options (yt-dlp only)
        self.add_label(grid2,
            '<u>' + _('Filesystem options') + '</u>' + self.ytdlp_only(),
            0, 0, grid_width, 1,
        )

        checkbutton4 = self.add_checkbutton(grid2,
            _('Force filenames to be MS Windows compatible'),
            'windows_filenames',
            0, 1, grid_width, 1,
        )
        self.add_tooltip('--windows-filenames', checkbutton4)

        label = self.add_label(grid2,
            _(
                'Limit filename length (excluding extension) to this' \
                + ' many characters',
            ),
            0, 2, 1, 1
        )

        spinbutton = self.add_spinbutton(grid2,
            0, None, 1,
            'trim_filenames',
            1, 2, 1, 1
        )
        self.add_tooltip('--trim-filenames', label, spinbutton)

        if os.name != 'nt':
            msg = _(
                'WARNING: The filename length includes the length of the' \
                + ' folder name!',
            )
        else:
            msg = _(
                'WARNING: The filename length includes the length of the' \
                + ' directory name!',
            )

        self.add_label(grid2,
            '<i>' + msg + '</i>',
            0, 3, grid_width, 1,
        )

        if not self.app_obj.simple_options_flag:

            checkbutton5 = self.add_checkbutton(grid2,
                _('Do not overwrite any files'),
                'no_overwrites',
                0, 4, grid_width, 1,
            )
            self.add_tooltip('--no-overwrites', checkbutton5)

            checkbutton6 = self.add_checkbutton(grid2,
                _(
                    'Overwrite all video and metadata files (includes' \
                    + ' \'--no-continue\')',
                ),
                'force_overwrites',
                0, 5, grid_width, 1,
            )
            self.add_tooltip('--force-overwrites', checkbutton6)

            checkbutton7 = self.add_checkbutton(grid2,
                _('Write playlist metadata in addition to video metadata'),
                'write_playlist_metafiles',
                0, 6, grid_width, 1,
            )
            self.add_tooltip('--write-playlist-metafiles', checkbutton7)

            checkbutton8 = self.add_checkbutton(grid2,
                _(
                    'Write all fields, including private fields, to the' \
                    + ' .info.json file',
                ),
                'no_clean_info_json',
                0, 7, grid_width, 1,
            )
            self.add_tooltip('--no-clean-infojson', checkbutton8)


    def setup_files_cookies_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Cookies' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files > Cookies'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Cookies'),
            inner_notebook,
        )
        grid_width = 3

        # Cookies options
        self.add_label(grid,
            '<u>' + _('Cookies options') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Path to the downloader\'s cookie jar file'),
            0, 1, 1, 1,
        )

        set_button = Gtk.Button(_('Set'))
        grid.attach(set_button, 1, 1, 1, 1)
        # (Signal connect appears below)

        reset_button = Gtk.Button(_('Reset'))
        grid.attach(reset_button, 2, 1, 1, 1)
        # (Signal connect appears below)

        entry = self.add_entry(grid,
            None,
            0, 2, grid_width, 1,
        )
        entry.set_editable(False)
        self.add_tooltip('--cookies FILE', label, entry)

        init_path = self.retrieve_val('cookies_path')
        if init_path == '':

            entry.set_text(
                os.path.abspath(
                    os.path.join(
                        self.app_obj.data_dir,
                        self.app_obj.cookie_file_name,
                    ),
                ),
            )

        else:

            entry.set_text(init_path)

        # (Signal connects from above)
        set_button.connect(
            'clicked',
            self.on_cookies_set_button_clicked,
            entry,
        )
        reset_button.connect(
            'clicked',
            self.on_cookies_reset_button_clicked,
            entry,
        )

        if not self.app_obj.simple_options_flag:

            # (To avoid messing up the neat format of the rows above, add a
            #   secondary grid, and put the next set of widgets inside it)
            grid2 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

            # Cookie options (yt-dlp only)
            self.add_label(grid2,
                '<u>' + _('Cookie options') + '</u>' + self.ytdlp_only(),
                0, 0, 1, 1,
            )

            checkbutton = self.add_checkbutton(grid2,
                _('Do not read/dump cookies from/to the cookiejar file'),
                'no_cookies',
                0, 1, 1, 1,
            )
            self.add_tooltip('--no-cookies', checkbutton)

            checkbutton2 = self.add_checkbutton(grid2,
                _('Do not load cookies from browser'),
                'no_cookies_from_browser',
                0, 2, 1, 1,
            )
            self.add_tooltip('--no-cookies-from-browser', checkbutton2)

            # (To avoid messing up the neat format of the rows above, add a
            #   secondary grid, and put the next set of widgets inside it)
            grid3 = self.add_secondary_grid(grid, 0, 4, grid_width, 1)

            label2 = self.add_label(grid3,
                _('Retrieve cookies from browser'),
                0, 0, 1, 1
            )
            label2.set_hexpand(False)

            entry2 = self.add_entry(grid3,
                None,
                1, 0, 1, 1,
            )
            entry2.set_hexpand(True)
            entry2.set_editable(False)
            entry2.set_text(self.retrieve_val('cookies_from_browser'))

            # (To avoid messing up the neat format of the rows above, add a
            #   secondary grid, and put the next set of widgets inside it)
            grid4 = self.add_secondary_grid(grid, 0, 5, grid_width, 1)

            self.add_label(grid4,
                _('Browser'),
                0, 0, 1, 1
            )

            combo_list = [
                '', 'brave', 'chrome', 'chromium', 'edge', 'firefox', 'opera',
                'safari', 'vivaldi',
            ]
            combo = self.add_combo(grid4,
                combo_list,
                None,
                1, 0, 1, 1
            )
            combo.set_active(0)
            combo.set_hexpand(True)
            # (Signal connect appears below)

            self.add_label(grid4,
                _('Chromium keyring'),
                2, 0, 1, 1
            )

            combo_list2 = ['', 'basictext', 'gnomekeyring', 'kwallet']
            combo2 = self.add_combo(grid4,
                combo_list2,
                None,
                3, 0, 1, 1
            )
            combo2.set_active(0)
            combo2.set_hexpand(True)
            # (Signal connect appears below)

            # (To avoid messing up the neat format of the rows above, add a
            #   secondary grid, and put the next set of widgets inside it)
            grid5 = self.add_secondary_grid(grid, 0, 6, grid_width, 1)

            label3 = self.add_label(grid5,
                _('Browser profile name (optional)'),
                0, 0, 1, 1
            )
            label3.set_hexpand(False)

            entry3 = self.add_entry(grid5,
                None,
                1, 0, 3, 1,
            )
            entry3.set_hexpand(True)
            # (Signal connect appears below)

            label4 = self.add_label(grid5,
                _('Browser profile path (optional)'),
                0, 1, 1, 1
            )
            label4.set_hexpand(False)

            entry4 = self.add_entry(grid5,
                None,
                1, 1, 1, 1,
            )
            entry4.set_hexpand(True)
            entry4.set_editable(False)

            set_button = Gtk.Button(_('Set'))
            grid5.attach(set_button, 2, 1, 1, 1)
            # (Signal connect appears below)

            reset_button = Gtk.Button(_('Reset'))
            grid5.attach(reset_button, 3, 1, 1, 1)
            # (Signal connect appears below)

            self.add_tooltip(
                '--cookies-from-browser BROWSER[+KEYRING][:PROFILE]',
                entry2,
                combo,
                combo2,
                entry3,
                entry4,
            )

            # Set the initial values for those widgets, retrieving them from
            #   the 'cookies_from_browser' download option
            match = re.search(
                r'^([^+:]+)(\+[^+:]+)?(\:.*)?',
                self.retrieve_val('cookies_from_browser'),
            )
            if match:
                browser = match.groups()[0]
                keyring = match.groups()[1]
                profile = match.groups()[2]

                if browser != '':

                    for i in range(len(combo_list)):
                        if combo_list[i] == browser:
                            combo.set_active(i)
                            break

                    if keyring != '' and keyring is not None:

                        # (Remove initial +/: characters)
                        keyring = keyring[1:]

                        for i in range(len(combo_list2)):
                            if combo_list2[i] == keyring:
                                combo2.set_active(i)
                                break

                    if profile != '' and profile is not None:

                        # (Remove initial +/: characters)
                        profile = profile[1:]

                        # This might be a profile name, or a profile path.
                        #   Assume it's a name unless the path exists
                        if not os.path.isfile(profile):
                            entry3.set_text(profile)
                        else:
                            entry4.set_text(profile)

            # (Signal connects from above)
            combo.connect(
                'changed',
                self.setup_files_cookies_tab_update,
                checkbutton2,
                entry2,
                combo,
                combo2,
                entry3,
                entry4,
            )
            combo2.connect(
                'changed',
                self.setup_files_cookies_tab_update,
                checkbutton2,
                entry2,
                combo,
                combo2,
                entry3,
                entry4,
            )
            entry3.connect(
                'changed',
                self.on_cookies_ytdlp_entry_changed,
                entry2,
                combo,
                combo2,
                entry3,
                entry4,
            )
            set_button.connect(
                'clicked',
                self.on_cookies_ytdlp_set_button_clicked,
                entry2,
                combo,
                combo2,
                entry3,
                entry4,
            )
            reset_button.connect(
                'clicked',
                self.on_cookies_ytdlp_reset_button_clicked,
                entry2,
                combo,
                combo2,
                entry3,
                entry4,
            )


    def setup_files_cookies_tab_update(self, widget, checkbutton, entry,
    combo, combo2, entry2, entry3):

        """Called by self.setup_files_cookies_tab() to set the
        'cookies_from_browser' download option, updating several widgets.

        Also called by several callbacks.

        Args:

            widget (Gtk.Entry or Gtk.Combo): Ignored

            checkbutton (Gtk.CheckButton): The 'Do not load cookies from
                browser' checkbutton

            entry (Gtk.Entry): The entry box displaying the download option

            combo, combo2, entry2, entry3 (Gtk.Combo, Gtk.Entry): Widgets whose
                settings are combined to set the 'cookies_from_browser'
                download option

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        browser = model[tree_iter][0]

        if browser == '' and combo2.get_active() != 0:

            # Special case: reset the other two widgets, which causes further
            #   calls to this function, in which the download option is updated
            entry.set_text('')
            combo2.set_active(0)
            return

        # Otherwise, set the new value of 'cookies_from_browser' now
        tree_iter2 = combo2.get_active_iter()
        model2 = combo2.get_model()
        keyring = model2[tree_iter2][0]

        profile_name = entry2.get_text()
        profile_path = entry3.get_text()

        value = browser
        if keyring != '':
            value += '+' + keyring

        if profile_name != '':
            value += ':' + profile_name
        elif profile_path != '':
            value += ':' + profile_path

        self.edit_dict['cookies_from_browser'] = value
        entry.set_text(value)

        # (To avoid confusion, reset the 'Do not load cookies from browser'
        #   checkbutton; the user can re-enable it, if they want)
        checkbutton.set_active(False)


    def setup_files_shortcuts_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Shortcuts' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files > Shortcuts'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Shortcuts'),
            inner_notebook,
        )

        # Internet shortcut options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Internet shortcut options') + '</u>' \
            + self.ytdlp_only(),
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Write an internet shortcut file (.url, .webloc or .desktop)'),
            'write_link',
            0, 1, 1, 1,
        )
        self.add_tooltip('--write-link', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('Write a Windows internet shortcut file (.url)'),
            'write_url_link',
            0, 2, 1, 1,
        )
        self.add_tooltip('--write-url-link', checkbutton2)

        checkbutton3 = self.add_checkbutton(grid,
            _('Write a macOS inernet shortcut file (.webloc)'),
            'write_webloc_link',
            0, 3, 1, 1,
        )
        self.add_tooltip('--write-webloc-link', checkbutton3)

        checkbutton4 = self.add_checkbutton(grid,
            _('Write a Linux internet shortcut file (.desktop)'),
            'write_desktop_link',
            0, 4, 1, 1,
        )
        self.add_tooltip('--write-desktop-link', checkbutton4)


    def setup_files_write_move_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Write/move' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files > Write/move'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Write/move'),
            inner_notebook,
        )
        grid_width = 2

        # File write options
        self.add_label(grid,
            '<u>' + _('File write options') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Write video\'s description to a .description file'),
            'write_description',
            0, 1, grid_width, 1,
        )
        self.add_tooltip('--write-description', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('Write video\'s metadata to an .info.json file'),
            'write_info',
            0, 2, grid_width, 1,
        )
        self.add_tooltip('--write-info-json', checkbutton2)

        checkbutton3 = self.add_checkbutton(grid,
            _(
            'Write video\'s annotations to an .annotations.xml file',
            ),
            'write_annotations',
            0, 3, grid_width, 1,
        )
        self.add_tooltip('--write-annotations', checkbutton3)

        self.add_label(grid,
            '<i>' + _(
            'Annotations are not downloaded when checking videos/channels/' \
            + 'playlists/folders'
            ) + '</i>',
            1, 4, 1, 1,
        )

        checkbutton4 = self.add_checkbutton(grid,
            _('Write the video\'s thumbnail to the same folder'),
            'write_thumbnail',
            0, 5, grid_width, 1,
        )
        self.add_tooltip('--write-thumbnail', checkbutton4)

        # File move options
        self.add_label(grid,
            '<u>' + _('File move options') + '</u>',
            0, 6, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _('Move video\'s description file into a sub-folder'),
            'move_description',
            0, 7, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _('Write video\'s metadata file into a sub-folder'),
            'move_info',
            0, 8, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _('Write video\'s annotations file into a sub-folder'),
            'move_annotations',
            0, 9, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _('Write the video\'s thumbnail into a sub-folder'),
            'move_thumbnail',
            0, 10, grid_width, 1,
        )


    def setup_files_keep_tab(self, inner_notebook):

        """Called by self.setup_files_tab().

        Sets up the 'Keep' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Files > Keep'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Keep'),
            inner_notebook,
        )

        # Options during real (not simulated) downloads
        self.add_label(grid,
            '<u>' + _('Options during real (not simulated) downloads') \
            + '</u>',
            0, 0, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Keep the description file after the download has finished'),
            'keep_description',
            0, 1, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Keep the metadata file after the download has finished'),
            'keep_info',
            0, 2, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Keep the annotations file after the download has finished'),
            'keep_annotations',
            0, 3, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Keep the thumbnail file after the download has finished'),
            'keep_thumbnail',
            0, 4, 1, 1,
        )

        # Options during simulated (not real) downloads
        self.add_label(grid,
            '<u>' + _('Options during simulated (not real) downloads') \
            + '</u>',
            0, 5, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Keep the description file after the download has finished'),
            'sim_keep_description',
            0, 6, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Keep the metadata file after the download has finished'),
            'sim_keep_info',
            0, 7, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Keep the annotations file after the download has finished'),
            'sim_keep_annotations',
            0, 8, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Keep the thumbnail file after the download has finished'),
            'sim_keep_thumbnail',
            0, 9, 1, 1,
        )


    def setup_formats_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Formats' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Formats'
        )

        # Add this tab...
        tab, grid = self.add_notebook_tab(_('F_ormats'), 0)

        # When advanced download options are visible, use an inner tab;
        #   otherwise display the same content in the main tab
        if self.app_obj.simple_options_flag:

            self.setup_formats_tab_add_grid(grid)

        else:

            # ...and an inner notebook...
            inner_notebook = self.add_inner_notebook(grid)

            # ...with its own tabs
            self.setup_formats_preferred_tab(inner_notebook)
            self.setup_formats_advanced_tab(inner_notebook)


    def setup_formats_preferred_tab(self, inner_notebook):

        """Called by self.setup_formats_tab().

        Sets up the 'Preferred' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        tab, grid = self.add_inner_notebook_tab(
            _('_Preferred'),
            inner_notebook,
        )

        self.setup_formats_tab_add_grid(grid)


    def setup_formats_tab_add_grid(self, grid):

        """Called by self.setup_formats_tab() and
         .setup_formats_preferred_tab().

        Adds widgets to the specified grid.

        Args:

            grid (Gtk.Grid): The main grid for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Formats > Preferred'
        )

        # (Force both treeviews to take half the available width)
        grid.set_column_homogeneous(True)
        grid_width = 4

        # Preferred format options
        self.add_label(grid,
            '<u>' + _('Preferred format options') + '</u>',
            0, 0, grid_width, 1,
        )

        if self.app_obj.simple_options_flag:

            # Newbies frequently get confused by this tab, so add an
            #   explanatory warning

            hbox = Gtk.HBox()
            grid.attach(hbox, 0, 1, grid_width, 1)

            frame = Gtk.Frame()
            hbox.pack_start(frame, False, False, 0)
            frame.set_hexpand(False)

            hbox2 = Gtk.HBox()
            frame.add(hbox2)
            hbox2.set_border_width(self.spacing_size)

            image = Gtk.Image()
            hbox2.pack_start(image, False, False, 0)
            image.set_from_pixbuf(
                self.app_obj.main_win_obj.pixbuf_dict['attention_large'],
            )

            frame2 = Gtk.Frame()
            hbox.pack_start(frame2, True, True, self.spacing_size)
            frame2.set_hexpand(True)

            vbox = Gtk.VBox()
            frame2.add(vbox)
            vbox.set_border_width(self.spacing_size)

            label = Gtk.Label()
            vbox.pack_start(label, True, True, 0)
            label.set_markup(
                '<b>' + _(
                    'If your preferred formats are not available, the' \
                    + ' download will fail!',
                ) + '</b>',
            )

            label2 = Gtk.Label()
            vbox.pack_start(label2, True, True, 0)
            label2.set_markup(
                '<b>' + _(
                    'If you want a specific format, install FFmpeg and use' \
                    + ' the Convert tab!',
                ) + '</b>',
            )

        # Left column
        self.add_label(grid,
            _('Recognised video/audio formats'),
            0, 2, 2, 1,
        )

        treeview, liststore = self.add_treeview(grid,
            0, 3, 2, 1,
        )
        self.setup_formats_tab_update_list(liststore)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 4, 2, 1)

        button = Gtk.Button(_('Add format') + ' >>>')
        grid2.attach(button, 0, 0, 1, 1)
        button.set_hexpand(True)
        # (Signal connect appears below)

        button2 = Gtk.Button()
        grid2.attach(button2, 1, 0, 1, 1)
        button2.set_hexpand(False)
        button2.set_image(
            Gtk.Image.new_from_pixbuf(
                self.app_obj.main_win_obj.pixbuf_dict['keyboard_small'],
            ),
        )
        button2.set_tooltip_text(_('Type extractor code directly'))
        # (Signal connect appears below)

        self.formats_checkbutton = self.add_checkbutton(grid,
            _('Hide obsolete YouTube formats'),
            None,
            0, 5, 2, 1,
        )
        if self.app_obj.hide_obsolete_formats_flag:
            self.formats_checkbutton.set_active(True)
        self.formats_checkbutton.connect(
            'toggled',
            self.on_obsolete_format_checkbutton_toggled,
            liststore,
        )

        # Right column
        self.add_label(grid,
            _('List of preferred formats'),
            2, 2, 2, 1,
        )

        treeview2, self.formats_liststore = self.add_treeview(grid,
            2, 3, 2, 1,
        )
        self.add_tooltip('-f, --format FORMAT', treeview, treeview2)

        # There are multiple possible format options, any or all of which might
        #   be set
        self.formats_tab_redraw_list()

        button3 = Gtk.Button('<<< ' + _('Remove format'))
        grid.attach(button3, 2, 4, 2, 1)
        # (Signal connect appears below)

        button4 = Gtk.Button('^ ' + _('Move up'))
        grid.attach(button4, 2, 5, 1, 1)
        # (Signal connect appears below)

        button5 = Gtk.Button('v ' + _('Move down'))
        grid.attach(button5, 3, 5, 1, 1)
        # (Signal connect appears below)

        # (Signal connects from above)
        # 'Add format'
        button.connect(
            'clicked',
            self.on_formats_tab_add_clicked,
            button3,
            button4,
            button5,
            treeview,
        )
        # 'Type extractor code directly'
        button2.connect(
            'clicked',
            self.on_formats_tab_type_clicked,
            button3,
            button4,
            button5,
            treeview,
        )
        # 'Remove format'
        button3.connect(
            'clicked',
            self.on_formats_tab_remove_clicked,
            button,
            button2,
            button4,
            button5,
            treeview2,
        )
        # 'Move up'
        button4.connect(
            'clicked',
            self.on_formats_tab_up_clicked,
            treeview2,
        )
        # 'Move down'
        button5.connect(
            'clicked',
            self.on_formats_tab_down_clicked,
            treeview2,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid3 = self.add_secondary_grid(grid, 0, 6, grid_width, 1)

        # Desensitise buttons, as appropriate
        format_count = self.formats_tab_count_formats()
        if format_count == 0:
            button3.set_sensitive(False)
            button4.set_sensitive(False)
            button5.set_sensitive(False)

        label3 = self.add_label(grid3,
            _(
            'If a merge is required after post-processing, output to this' \
            + ' format:',
            ),
            0, 0, 1, 1,
        )

        combo_list = ['', 'flv', 'mkv', 'mp4', 'ogg', 'webm']
        combo = self.add_combo(grid3,
            combo_list,
            None,
            1, 0, 1, 1,
        )
        combo.set_active(
            combo_list.index(self.retrieve_val('merge_output_format')),
        )
        combo.set_hexpand(True)
        combo.connect('changed', self.on_formats_tab_combo_changed)
        self.add_tooltip('--merge-output-format FORMAT', label3, combo)


    def setup_formats_tab_update_list(self, liststore):

        """Called by self.setup_formats_tab_add_grid(), etc.

        Updates the (full) list of formats on the left-hand side.

        Args:

            liststore (Gtk.ListStore): The liststore to update

        """

        liststore.clear()

        for key in formats.VIDEO_OPTION_LIST:

            value = formats.VIDEO_OPTION_DICT[key]

            if not self.app_obj.hide_obsolete_formats_flag or \
            not formats.VIDEO_OPTION_OBSOLETE_DICT[value]:
                liststore.append([key])


    def setup_formats_advanced_tab(self, inner_notebook):

        """Called by self.setup_formats_tab().

        Sets up the 'Advanced' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Formats > Advanced'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Advanced'),
            inner_notebook,
        )
        grid_width = 2
        extra_row = 0

        # Multiple format options
        self.add_label(grid,
            '<u>' + _('Multiple format options') + '</u>',
            0, 0, grid_width, 1,
        )

        if self.app_obj.allow_ytdl_archive_flag:

            extra_row = 1
            self.add_label(grid,
                '<i>' + _(
                    'Multiple formats will not be downloaded, because an' \
                    + ' archive file will be created'
                ) + '\n' + _(
                    'The archive file can be disabled in the System' \
                    ' Preferences window',
                ) + '</i>',
                0, 1, grid_width, 1,
            )

        radiobutton = self.add_radiobutton(grid,
            None,
            _(
            'For each video, download the first available format from the' \
            + ' preferred list',
            ),
            None,
            None,
            0, (1 + extra_row), grid_width, 1,
        )
        if self.retrieve_val('video_format_mode') == 'single':
            radiobutton.set_active(True)
        # (Signal connect appears below)

        radiobutton2 = self.add_radiobutton(grid,
            radiobutton,
            _(
            'For each video, combine the first video and first audio format' \
            + ' from the preferred list',
            ),
            None,
            None,
            0, (2 + extra_row), grid_width, 1,
        )
        if self.retrieve_val('video_format_mode') == 'combine':
            radiobutton2.set_active(True)
        # (Signal connect appears below)

        radiobutton3 = self.add_radiobutton(grid,
            radiobutton2,
            _(
            'For each video, download all available formats from the' \
            + ' preferred list',
            ),
            None,
            None,
            0, (3 + extra_row), grid_width, 1,
        )
        if self.retrieve_val('video_format_mode') == 'multiple':
            radiobutton3.set_active(True)
        # (Signal connect appears below)

        radiobutton4 = self.add_radiobutton(grid,
            radiobutton2,
            _('Download all available formats for all videos'),
            None,
            None,
            0, (4 + extra_row), grid_width, 1,
        )
        if self.retrieve_val('video_format_mode') == 'all':
            radiobutton4.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        radiobutton.connect(
            'toggled',
            self.on_video_format_mode_toggled,
            'single',
        )
        radiobutton2.connect(
            'toggled',
            self.on_video_format_mode_toggled,
            'combine',
        )
        radiobutton3.connect(
            'toggled',
            self.on_video_format_mode_toggled,
            'multiple',
        )
        radiobutton4.connect(
            'toggled',
            self.on_video_format_mode_toggled,
            'all',
        )

        # Other format options
        self.add_label(grid,
            '<u>' + _('Other format options') + '</u>',
            0, (5 + extra_row), grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Prefer free video formats, unless one is specified above'),
            'prefer_free_formats',
            0, (6 + extra_row), grid_width, 1,
        )
        self.add_tooltip('--prefer-free-formats', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('Do not download DASH-related data for YouTube videos'),
            'yt_skip_dash',
            0, (7 + extra_row), grid_width, 1,
        )
        self.add_tooltip('--youtube-skip-dash-manifest', checkbutton2)

        # Other format options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Other format options') + '</u>' \
            + self.ytdlp_only(),
            0, (8 + extra_row), grid_width, 1,
        )

        checkbutton3 = self.add_checkbutton(grid,
            _(
                'Check formats selected are actually downloadable' \
                + ' (Experimental)',
            ),
            'check_formats',
            0, (9 + extra_row), grid_width, 1,
        )
        self.add_tooltip('--check-formats', checkbutton3)

        checkbutton4 = self.add_checkbutton(grid,
            _(
                'Allow unplayable formats to be listed and downloaded (also' \
                + ' disables post-processing)',
            ),
            'allow_unplayable_formats',
            0, (10 + extra_row), grid_width, 1,
        )
        self.add_tooltip('--allow-unplayable-formats', checkbutton4)


    def setup_convert_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Convert' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Convert'
        )

        tab, grid = self.add_notebook_tab(_('_Convert'))
        grid_width = 4

        # Convert to video
        self.add_label(grid,
            '<u>' + _('Convert to video') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Convert downloaded video to another format'),
            0, 1, 2, 1,
        )

        combo_list = ['', 'avi', 'flv', 'mkv', 'mp4', 'ogg', 'webm']
        combo = self.add_combo(grid,
            combo_list,
            'recode_video',
            2, 1, 2, 1,
        )
        self.add_tooltip('--recode-video FORMAT', label, combo)

        # Convert to audio
        self.add_label(grid,
            '<u>' + _('Convert to audio') + '</u>',
            0, 2, grid_width, 1,
        )

        # (The MS Windows installer includes FFmpeg)
        text = _(
            'Download each video, extract the sound, and then discard the' \
            + ' original video',
        )
        if os.name != 'nt':
            text += '\n' + _(
                '(requires that FFmpeg or AVConv is installed on your system)'
            )

        checkbutton = self.add_checkbutton(grid,
            text,
            'extract_audio',
            0, 3, grid_width, 1,
        )
        self.add_tooltip('-x, --extract-audio', checkbutton)

        label = self.add_label(grid,
            _('Use this audio format:') + ' ',
            0, 4, 1, 1,
        )
        label.set_hexpand(False)

        combo_list = formats.AUDIO_FORMAT_LIST.copy()
        combo_list.insert(0, '')
        combo = self.add_combo(grid,
            combo_list,
            'audio_format',
            1, 4, 1, 1,
        )
        combo.set_hexpand(True)
        self.add_tooltip('--audio-format FORMAT', label, combo)

        label2 = self.add_label(grid,
            _('Use this audio quality:') + ' ',
            2, 4, 1, 1,
        )
        label2.set_hexpand(False)

        combo2_list = [
            [_('High'), '0'],
            [_('Medium'), '5'],
            [_('Low'), '9'],
        ]

        combo2 = self.add_combo_with_data(grid,
            combo2_list,
            'audio_quality',
            3, 4, 1, 1,
        )
        combo2.set_hexpand(True)
        self.add_tooltip('--audio-quality QUALITY', label2, combo2)


    def setup_post_process_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Post-processing' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Post-processing'
        )

        # Add this tab...
        tab, grid = self.add_notebook_tab(_('_Post-processing'), 0)

        # ...and an inner notebook...
        inner_notebook = self.add_inner_notebook(grid)

        # ...with its own tabs
        self.setup_post_process_general_tab(inner_notebook)
        self.setup_post_process_ytdlp_tab(inner_notebook)


    def setup_post_process_general_tab(self, inner_notebook):

        """Called by self.setup_post_process_tab().

        Sets up the 'General' inner notebook tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Post-processing > General'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_General'),
            inner_notebook,
        )
        grid_width = 2
        grid.set_column_homogeneous(True)

        # Post-processing options
        self.add_label(grid,
            '<u>' + _('Post-processing options') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _(
            'Post-process video files to convert them to audio-only files',
            ),
            'extract_audio',
            0, 1, grid_width, 1,
        )
        self.add_tooltip('-x, --extract-audio', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('Prefer AVConv over FFmpeg'),
            'prefer_avconv',
            0, 2, 1, 1,
        )
        if os.name == 'nt':
            checkbutton2.set_sensitive(False)
        self.add_tooltip('-prefer-avconv', checkbutton2)

        checkbutton3 = self.add_checkbutton(grid,
            _('Prefer FFmpeg over AVConv (default)'),
            'prefer_ffmpeg',
            1, 2, 1, 1,
        )
        if os.name == 'nt':
            checkbutton3.set_sensitive(False)
        self.add_tooltip('--prefer-ffmpeg', checkbutton3)

        label = self.add_label(grid,
            _('Audio format of the post-processed file'),
            0, 3, 1, 1,
        )

        combo_list = formats.AUDIO_FORMAT_LIST.copy()
        combo_list.insert(0, '')
        combo = self.add_combo(grid,
            combo_list,
            'audio_format',
            1, 3, 1, 1,
        )
        self.add_tooltip('--audio-format FORMAT', label, combo)

        label2 = self.add_label(grid,
            _('Audio quality of the post-processed file'),
            0, 4, 1, 1,
        )

        combo2_list = [
            [_('High VBR'), '0'],
            [_('Medium VBR'), '5'],
            [_('Low VBR'), '9'],
            [_('320 kb/s'), '320k'],
            [_('256 kb/s'), '256k'],
            [_('192 kb/s'), '192k'],
            [_('128 kb/s'), '128k'],
            [_('96 kb/s'), '96k'],
        ]

        combo2 = self.add_combo_with_data(grid,
            combo2_list,
            'audio_quality',
            1, 4, 1, 1,
        )
        self.add_tooltip('--audio-quality QUALITY', label2, combo2)

        label3 = self.add_label(grid,
            _('Encode video to another format, if necessary'),
            0, 5, 1, 1,
        )

        combo_list3 = ['', 'avi', 'flv', 'mkv', 'mp4', 'ogg', 'webm']
        combo3 = self.add_combo(grid,
            combo_list3,
            'recode_video',
            1, 5, 1, 1,
        )
        self.add_tooltip('--recode-video FORMAT', label3, combo3)

        label4 = self.add_label(grid,
            _('Arguments to pass to post-processor'),
            0, 6, 1, 1,
        )

        entry = self.add_entry(grid,
            'pp_args',
            1, 6, 1, 1,
        )
        self.add_tooltip('--postprocessor-args ARGS', label4, entry)

        checkbutton4 = self.add_checkbutton(grid,
            _('Keep original file after processing it'),
            'keep_video',
            0, 7, 1, 1,
        )
        self.add_tooltip('-k, --keep-video', checkbutton4)

        # (This option can also be modified in the Post-process tab)
        self.embed_checkbutton = self.add_checkbutton(grid,
            _('Merge subtitles file with video (.mp4 only)'),
            None,
            1, 7, 1, 1,
        )
        self.embed_checkbutton.set_active(self.retrieve_val('embed_subs'))
        self.embed_checkbutton.connect(
            'toggled',
            self.on_embed_checkbutton_toggled,
        )
        self.add_tooltip('--embed-subs', self.embed_checkbutton)

        checkbutton5 = self.add_checkbutton(grid,
            _('Embed thumbnail in audio file as cover art'),
            'embed_thumbnail',
            0, 8, 1, 1,
        )
        self.add_tooltip('--embed-thumbnail', checkbutton5)

        checkbutton6 = self.add_checkbutton(grid,
            _('Write metadata to the video file'),
            'add_metadata',
            1, 8, 1, 1,
        )
        self.add_tooltip('--add-metadata', checkbutton6)

        label5 = self.add_label(grid,
            _('Automatically correct known faults of the file'),
            0, 9, 1, 1,
        )

        combo_list4 = [
            ['', ''],
            [_('Do nothing'), 'never'],
            [_('Warn, but do nothing'), 'warn'],
            [_('Fix if possible, otherwise warn'), 'detect_or_warn'],
        ]
        combo4 = self.add_combo_with_data(grid,
            combo_list4,
            'fixup_policy',
            1, 9, 1, 1,
        )
        self.add_tooltip('--fixup POLICY', combo4)


    def setup_post_process_ytdlp_tab(self, inner_notebook):

        """Called by self.setup_post_process_tab().

        Sets up the 'yt-dlp' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Post-processing > yt-dlp'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_yt-dlp'),
            inner_notebook,
        )
        grid_width = 2

        # Post-processing options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Post-processing options') + '</u>' + self.ytdlp_only(),
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Remux video into another container if necessary'),
            0, 1, 1, 1
        )

        combo_list = [
            '', 'mp4', 'mkv', 'flv', 'webm', 'mov', 'avi',
            'mp3', 'mka', 'm4a', 'ogg', 'opus',
        ]

        combo = self.add_combo(grid,
            combo_list,
            'remux_video',
            1, 1, 1, 1
        )
        combo.set_hexpand(True)
        self.add_tooltip('--remux-video FORMAT', label, combo)

        checkbutton = self.add_checkbutton(grid,
            _(
                'Embed metadata including chapter markers (if supported by' \
                + ' format)',
            ),
            'embed_metadata',
            0, 2, grid_width, 1,
        )
        self.add_tooltip('--embed-metadata', checkbutton)

        label2 = self.add_label(grid,
            _('Convert thumbnails to another format'),
            0, 3, 1, 1
        )

        combo_list2 = ['', 'jpg', 'png']
        combo2 = self.add_combo(grid,
            combo_list2,
            'convert_thumbnails',
            1, 3, 1, 1
        )
        combo2.set_hexpand(True)
        self.add_tooltip('--convert-thumbnails FORMAT', label2, combo2)

        checkbutton2 = self.add_checkbutton(grid,
            _(
                'Split video into multiple files based on internal chapters',
            ),
            'split_chapters',
            0, 4, grid_width, 1,
        )
        self.add_tooltip('--split-chapters', checkbutton2)

        self.add_label(grid,
            '<i>' + _(
                'N.B. The \'chapter\' prefix can be used in the \'Output\'' \
                + ' and \'Paths\' tabs',
            ) + '</i>',
            0, 5, grid_width, 1
        )


    def setup_subtitles_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Subtitles' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Subtitles'
        )

        # Add this tab...
        tab, grid = self.add_notebook_tab(_('_Subtitles'), 0)

        # ...and an inner notebook...
        inner_notebook = self.add_inner_notebook(grid)

        # ...with its own tabs
        self.setup_subtitles_options_tab(inner_notebook)
        self.setup_subtitles_more_options_tab(inner_notebook)


    def setup_subtitles_options_tab(self, inner_notebook):

        """Called by self.setup_subtitles_tab().

        Sets up the 'Options' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Subtitles > Options'
        )

        tab, grid = self.add_inner_notebook_tab(_('_Options'), inner_notebook)

        # Subtitles options
        self.add_label(grid,
            '<u>' + _('Subtitles options') + '</u>',
            0, 0, 2, 1,
        )

        radiobutton = self.add_radiobutton(grid,
            None,
            _('Don\'t download the subtitles file'),
            None,
            None,
            0, 1, 2, 1,
        )
        if self.retrieve_val('write_subs') is False:
            radiobutton.set_active(True)
        # (Signal connect appears below)

        radiobutton2 = self.add_radiobutton(grid,
            radiobutton,
            _('Download the automatic subtitles file (YouTube only)'),
            None,
            None,
            0, 2, 2, 1,
        )
        if self.retrieve_val('write_subs') is True \
        and self.retrieve_val('write_auto_subs') is True:
            radiobutton2.set_active(True)
        # (Signal connect appears below)
        self.add_tooltip('--write-sub, --write-auto-sub', radiobutton2)

        radiobutton3 = self.add_radiobutton(grid,
            radiobutton2,
            _('Download all available subtitle files'),
            None,
            None,
            0, 3, 2, 1,
        )
        if self.retrieve_val('write_subs') is True \
        and self.retrieve_val('write_all_subs') is True:
            radiobutton3.set_active(True)
        # (Signal connect appears below)
        self.add_tooltip('--write-sub, -all-subs', radiobutton3)

        radiobutton4 = self.add_radiobutton(grid,
            radiobutton3,
            _('Download subtitle file for these languages:'),
            None,
            None,
            0, 4, 2, 1,
        )
        if self.retrieve_val('write_subs') is True \
        and self.retrieve_val('write_auto_subs') is False \
        and self.retrieve_val('write_all_subs') is False:
            radiobutton4.set_active(True)
        # (Signal connect appears below)
        self.add_tooltip('--write-sub', radiobutton4)

        treeview, liststore = self.add_treeview(grid,
            0, 5, 1, 1,
        )

        for language in formats.LANGUAGE_CODE_LIST:
            liststore.append([
                language + ' [' + formats.LANGUAGE_CODE_DICT[language] + ']',
            ])

        # We need a reverse dictionary for quick lookup
        rev_dict = {}
        for key in formats.LANGUAGE_CODE_DICT:
            val = formats.LANGUAGE_CODE_DICT[key]
            rev_dict[val] = key

        button = Gtk.Button(_('Add language') + ' >>>')
        grid.attach(button, 0, 6, 1, 1)
        # (Signal connect appears below)

        treeview2, liststore2 = self.add_treeview(grid,
            1, 5, 1, 1,
        )
        lang_list = self.retrieve_val('subs_lang_list')
        # The option stores values from formats.LANGUAGE_CODE_DICT, e.g. 'en',
        #   'live_chat'. Convert them to the corresponding values, e.g.
        #   'English'
        for lang_code in lang_list:
            liststore2.append([
                rev_dict[lang_code] + ' [' + lang_code + ']',
            ])

        self.add_tooltip('--sub-lang LANGS', treeview, treeview2)

        button2 = Gtk.Button('<<< ' + _('Remove language'))
        grid.attach(button2, 1, 6, 1, 1)
        # (Signal connect appears below)

        # Desensitise the buttons, if the matching radiobutton isn't active
        if not radiobutton4.get_active():
            button.set_sensitive(False)
            button2.set_sensitive(False)

        # (Signal connects from above)
        button.connect(
            'clicked',
            self.on_subtitles_tab_add_clicked,
            treeview,
            liststore2,
            rev_dict,
        )
        button2.connect(
            'clicked',
            self.on_subtitles_tab_remove_clicked,
            treeview2,
            liststore2,
            rev_dict,
        )
        radiobutton.connect(
            'toggled',
            self.on_subtitles_toggled,
            button, button2,
            'write_subs',
        )
        radiobutton2.connect(
            'toggled',
            self.on_subtitles_toggled,
            button, button2,
            'write_auto_subs',
        )
        radiobutton3.connect(
            'toggled',
            self.on_subtitles_toggled,
            button, button2,
            'write_all_subs',
        )
        radiobutton4.connect(
            'toggled',
            self.on_subtitles_toggled,
            button, button2,
            'subs_lang',
        )


    def setup_subtitles_more_options_tab(self, inner_notebook):

        """Called by self.setup_subtitles_tab().

        Sets up the 'More options' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Subtitles > More options'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_More options'),
            inner_notebook,
        )

        # Subtitle format options
        self.add_label(grid,
            '<u>' + _('Subtitle format options') + '</u>',
            0, 0, 1, 1,
        )

        label = self.add_label(grid,
            _(
            'Preferred subtitle format(s), e.g. \'srt\', \'vtt\',' \
            + ' \'srt/ass/vtt/lrc/best\'',
            ),
            0, 1, 1, 1,
        )

        entry = self.add_entry(grid,
            'subs_format',
            0, 2, 1, 1,
        )
        self.add_tooltip('--sub-format FORMAT', label, entry)

        # Post-processing options
        self.add_label(grid,
            '<u>' + _('Post-processing options') + '</u>',
            0, 3, 1, 1,
        )

        self.add_label(grid,
            '<i>' + _('Applies to .mp4 videos only; requires FFmpeg/AVConv') \
            + '</i>',
            0, 4, 1, 1,
        )

        # (This option can also be modified in the Post-process tab)
        self.embed_checkbutton2 = self.add_checkbutton(grid,
            _('During post-processing, merge subtitles file with video'),
            None,
            0, 5, 1, 1,
        )
        self.embed_checkbutton2.set_active(self.retrieve_val('embed_subs'))
        self.embed_checkbutton2.connect(
            'toggled',
            self.on_embed_checkbutton_toggled,
        )
        self.add_tooltip('--embed-subs', self.embed_checkbutton2)


    def setup_advanced_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Advanced' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Advanced'
        )

        # Add this tab...
        tab, grid = self.add_notebook_tab(_('_Advanced'), 0)

        # ...and an inner notebook...
        inner_notebook = self.add_inner_notebook(grid)

        # ...with its own tabs
        self.setup_advanced_configuration_tab(inner_notebook)
        self.setup_advanced_authentication_tab(inner_notebook)
        self.setup_advanced_netrc_tab(inner_notebook)
        self.setup_advanced_network_tab(inner_notebook)
        self.setup_advanced_georestrict_tab(inner_notebook)
        self.setup_advanced_workaround_tab(inner_notebook)
        self.setup_advanced_fetch_tab(inner_notebook)


    def setup_advanced_configuration_tab(self, inner_notebook):

        """Called by self.setup_advanced_tab().

        Sets up the 'Configuration' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Advanced > Configurations'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Configurations'),
            inner_notebook,
        )
        grid_width = 3

        # Configuration file options
        self.add_label(grid,
            '<u>' + _('Configuration file options') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_checkbutton(grid,
            _('Use the downloader\'s configuration file'),
            'downloader_config',
            0, 1, grid_width, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            None,
            0, 2, grid_width, 1,
        )

        label = self.add_label(grid,
            _('File loaded from:'),
            0, 3, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid,
            None,
            1, 3, 1, 1,
        )
        entry.set_hexpand(True)

        msg = _('Save file')
        button = Gtk.Button(msg)
        grid.attach(button, 2, 3, 1, 1)
        button.get_child().set_width_chars(len(msg) + 6)
        # (Signal connect appears below)

        # (If the downloader's configuration file exists, load it and update
        #   the textview/entry)
        dl_config_path = ttutils.get_dl_config_path(self.app_obj)
        if os.path.isfile(dl_config_path):

            line_list = []

            try:
                with open(dl_config_path) as fh:
                    line_list = fh.readlines()

            except:
                pass

            textbuffer.set_text(str.join('', line_list))
            entry.set_text(dl_config_path)

        # (Signal connect from above)
        button.connect(
            'clicked',
            self.on_dl_config_button_clicked,
            entry,
            textbuffer,
            dl_config_path,
        )


    def setup_advanced_authentication_tab(self, inner_notebook):

        """Called by self.setup_advanced_tab().

        Sets up the 'Authentication' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Advanced > Authentication'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Authentication'),
            inner_notebook,
        )
        grid_width = 2

        # Authentication options
        self.add_label(grid,
            '<u>' + _('Authentication options') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Username with which to log in'),
            0, 1, 1, 1,
        )

        entry = self.add_entry(grid,
            'username',
            1, 1, 1, 1,
        )
        self.add_tooltip('-u, --username USERNAME', label, entry)

        label2 = self.add_label(grid,
            _('Password with which to log in'),
            0, 2, 1, 1,
        )

        entry2 = self.add_entry(grid,
            'password',
            1, 2, 1, 1,
        )
        self.add_tooltip('-p, --password PASSWORD', label2, entry2)

        label3 = self.add_label(grid,
            _('Password required for this URL'),
            0, 3, 1, 1,
        )

        entry3 = self.add_entry(grid,
            'video_password',
            1, 3, 1, 1,
        )
        self.add_tooltip('--video-password PASSWORD', label3, entry3)

        label4 = self.add_label(grid,
            _('Two-factor authentication code'),
            0, 4, 1, 1,
        )

        entry4 = self.add_entry(grid,
            'two_factor',
            1, 4, 1, 1,
        )
        self.add_tooltip('-2, --twofactor TWOFACTOR', label4, entry4)

        label5 = self.add_label(grid,
            _(
                'Adobe Pass multiple-system operator (TV provider)' \
                + ' identifier',
            ),
            0, 5, 1, 1
        )

        entry5 = self.add_entry(grid,
            'ap_mso',
            1, 5, 1, 1,
        )
        self.add_tooltip('--ap-mso MSO', label5, entry5)

        label6 = self.add_label(grid,
            _(' Adobe Pass multiple-system operator account login'),
            0, 6, 1, 1
        )

        entry6 = self.add_entry(grid,
            'ap_username',
            1, 6, 1, 1,
        )
        self.add_tooltip('--ap-username USERNAME', label6, entry6)

        label7 = self.add_label(grid,
            _('Adobe Pass multiple-system operator account password'),
            0, 7, 1, 1
        )

        entry7 = self.add_entry(grid,
            'ap_password',
            1, 7, 1, 1,
        )
        self.add_tooltip('--ap-password PASSWORD', label7, entry7)

        self.add_youtube_warning(grid, 0, 8, 2, 1)


    def setup_advanced_netrc_tab(self, inner_notebook):

        """Called by self.setup_advanced_tab().

        Sets up the '.netrc' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Advanced > .netrc'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('._netrc'),
            inner_notebook,
        )
        grid_width = 3

        # .netrc options
        self.add_label(grid,
            '<u>' + _('.netrc options') + '</u>',
            0, 0, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Use .netrc authentication data'),
            'net_rc',
            0, 1, grid_width, 1,
        )
        self.add_tooltip('-n, --netrc', checkbutton)

        textview, textbuffer = self.add_textview(grid,
            None,
            0, 2, grid_width, 1,
        )

        label = self.add_label(grid,
            _('File loaded from:'),
            0, 3, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid,
            None,
            1, 3, 1, 1,
        )
        entry.set_hexpand(True)

        msg = _('Save file')
        button = Gtk.Button(msg)
        grid.attach(button, 2, 3, 1, 1)
        button.get_child().set_width_chars(len(msg) + 6)
        # (Signal connect appears below)

        # (If the .netrc file exists, load it and update the textview/entry)
        netrc_path = os.path.abspath(
            os.path.join(
                os.path.expanduser('~'),
                '.netrc',
            ),
        )
        if os.path.isfile(netrc_path):

            line_list = []

            try:
                with open(netrc_path) as fh:
                    line_list = fh.readlines()

            except:
                pass

            textbuffer.set_text(str.join('', line_list))
            entry.set_text(netrc_path)

        self.add_youtube_warning(grid, 0, 4, grid_width, 1)

        # (Signal connect from above)
        button.connect(
            'clicked',
            self.on_netrc_button_clicked,
            entry,
            textbuffer,
            netrc_path,
        )


    def setup_advanced_network_tab(self, inner_notebook):

        """Called by self.setup_advanced_tab().

        Sets up the 'Network' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Advanced > Network'
        )

        tab, grid = self.add_inner_notebook_tab(_('N_etwork'), inner_notebook)
        grid_width = 2

        # Network options
        self.add_label(grid,
            '<u>' + _('Network options') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _(
            'Use this HTTP/HTTPS proxy (if set, overrides the proxies in' \
            + ' Tartube\'s preferences window)',
            ),
            0, 1, grid_width, 1,
        )

        entry = self.add_entry(grid,
            'proxy',
            0, 2, grid_width, 1,
        )
        self.add_tooltip('--proxy URL', label, entry)

        label2 = self.add_label(grid,
            _('Time to wait for socket connection, before giving up'),
            0, 3, 1, 1,
        )

        entry2 = self.add_entry(grid,
            'socket_timeout',
            1, 3, 1, 1,
        )
        self.add_tooltip('--socket-timeout SECONDS', label2, entry2)

        label3 = self.add_label(grid,
            _('Bind with this Client-side IP address'),
            0, 4, 1, 1,
        )

        entry3 = self.add_entry(grid,
            'source_address',
            1, 4, 1, 1,
        )
        self.add_tooltip('--source-address IP', label3, entry3)

        checkbutton = self.add_checkbutton(grid,
            _('Connect using IPv4 only'),
            'force_ipv4',
            0, 5, grid_width, 1,
        )
        self.add_tooltip('-4, --force-ipv4', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('Connect using IPv6 only'),
            'force_ipv6',
            0, 6, grid_width, 1,
        )
        self.add_tooltip('-6, --force-ipv6', checkbutton2)


    def setup_advanced_georestrict_tab(self, inner_notebook):

        """Called by self.setup_advanced_tab().

        Sets up the 'Geo-restriction' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Advanced > Geo-restriction'
        )

        tab, grid = self.add_inner_notebook_tab(
            _('_Geo-restriction'),
            inner_notebook,
        )
        grid_width = 2

        # Geo-restriction options
        self.add_label(grid,
            '<u>' + _('Geo-restriction options') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Use this proxy to verify IP address'),
            0, 1, 1, 1,
        )

        entry = self.add_entry(grid,
            'geo_verification_proxy',
            1, 1, 1, 1,
        )
        self.add_tooltip('--geo-verification-proxy URL', label, entry)

        checkbutton = self.add_checkbutton(grid,
            _('Bypass using fake X-Forwarded-For HTTP header'),
            'geo_bypass',
            0, 2, 1, 1,
        )
        self.add_tooltip('--geo-bypass', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('Don\'t bypass using fake HTTP header'),
            'no_geo_bypass',
            1, 2, 1, 1,
        )
        self.add_tooltip('--no-geo-bypass', checkbutton2)

        label2 = self.add_label(grid,
            _('Bypass geo-restriction with ISO 3166-2 country code'),
            0, 3, 1, 1,
        )

        entry2 = self.add_entry(grid,
            'geo_bypass_country',
            1, 3, 1, 1,
        )
        self.add_tooltip('--geo-bypass-country CODE', label2, entry2)

        label3 = self.add_label(grid,
            _('Bypass with explicit IP block in CIDR notation'),
            0, 4, 1, 1,
        )

        entry3 = self.add_entry(grid,
            'geo_bypass_ip_block',
            1, 4, 1, 1,
        )
        self.add_tooltip('--geo-bypass-ip-block IP_BLOCK', label3, entry3)


    def setup_advanced_workaround_tab(self, inner_notebook):

        """Called by self.setup_advanced_tab().

        Sets up the 'Workaround' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Advanced > Workaround'
        )

        tab, grid = self.add_inner_notebook_tab('_Workaround', inner_notebook)
        grid_width = 2

        # Workaround options
        self.add_label(grid,
            '<u>' + _('Workaround options') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Custom user agent'),
            0, 1, 1, 1,
        )

        entry = self.add_entry(grid,
            'user_agent',
            1, 1, 1, 1,
        )
        self.add_tooltip('--user-agent UA', label, entry)

        label2 = self.add_label(grid,
            _('Custom referer if video access has restricted domain'),
            0, 2, 1, 1,
        )

        entry2 = self.add_entry(grid,
            'referer',
            1, 2, 1, 1,
        )
        self.add_tooltip('--referer URL', label2, entry2)

        label3 = self.add_label(grid,
            _('Minimum seconds to sleep before each download'),
            0, 3, 1, 1,
        )

        spinbutton = self.add_spinbutton(grid,
            0, 3600, 1,
            None,
            1, 3, 1, 1
        )
        spinbutton.set_value(self.edit_obj.options_dict['min_sleep_interval'])
        # (Signal connect appears below)
        self.add_tooltip('--sleep-interval SECONDS', label3, spinbutton)

        label4 = self.add_label(grid,
            _('Maximum seconds to sleep before each download'),
            0, 4, 1, 1,
        )

        spinbutton2 = self.add_spinbutton(grid,
            0, 3600, 1,
            'max_sleep_interval',
            1, 4, 1, 1
        )
        if self.edit_obj.options_dict['min_sleep_interval'] == 0:
            spinbutton2.set_sensitive(False)
        self.add_tooltip('--max-sleep-interval SECONDS', label4, spinbutton2)

        # (Signal connect from above)
        spinbutton.connect(
            'value-changed',
            self.on_sleep_button_changed,
            spinbutton2,
        )

        label5 = self.add_label(grid,
            _('Force this encoding (experimental)'),
            0, 5, 1, 1,
        )

        entry3 = self.add_entry(grid,
            'force_encoding',
            1, 5, 1, 1,
        )
        self.add_tooltip('--encoding ENCODING', label5, entry3)

        checkbutton = self.add_checkbutton(grid,
            _('Suppress HTTPS certificate validation'),
            'no_check_certificate',
            0, 6, grid_width, 1,
        )
        self.add_tooltip('--no-check-certificate', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _(
            'Use an unencrypted connection to retrieve information about' \
            + ' videos (YouTube only)',
            ),
            'prefer_insecure',
            0, 7, grid_width, 1,
        )
        self.add_tooltip('--prefer-insecure', checkbutton2)

        # Workaround options (yt-dlp only)
        self.add_label(grid,
            '<u>' + _('Workaround options') + '</u>' + self.ytdlp_only(),
            0, 8, grid_width, 1,
        )

        label = self.add_label(grid,
            _(
                'Number of seconds to sleep between requests during data' \
                + ' extraction',
            ),
            0, 9, 1, 1
        )

        spinbutton3 = self.add_spinbutton(grid,
            0, None, 1,
            'sleep_requests',
            1, 9, 1, 1
        )
        self.add_tooltip('--sleep-requests SECONDS', label, spinbutton3)

        label2 = self.add_label(grid,
            _(
                'Number of seconds to sleep before each download (or minimum' \
                + ' time)',
            ),
            0, 10, 1, 1
        )

        spinbutton4 = self.add_spinbutton(grid,
            0, None, 1,
            'sleep_subtitles',
            1, 10, 1, 1
        )
        self.add_tooltip('--sleep-subtitles SECONDS', label2, spinbutton4)


    def setup_advanced_fetch_tab(self, inner_notebook):

        """Called by self.setup_advanced_tab().

        Sets up the 'Fetcg' inner notebook tab.

        Args:

            inner_notebook (Gtk.Notebook): The container for this tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Advanced > Fetch'
        )

        tab, grid = self.add_inner_notebook_tab('_Fetch', inner_notebook)

        # Fetch options
        self.add_label(grid,
            '<u>' + _('Fetch options') + '</u>',
            0, 0, 1, 1,
        )

        label = self.add_label(grid,
            _(
                'Additional download options when fetching list of video' \
                + ' formats',
            ),
            0, 1, 1, 1,
        )

        label2 = self.add_label(grid,
            '<i>' + _('e.g. --cookies COOKIEPATH') + '</i>',
            0, 2, 1, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            'fetch_formats_cmd_string',
            0, 3, 1, 1,
        )

        label3 = self.add_label(grid,
            _(
                'Additional download options when fetching list of video' \
                + ' subtitles',
            ),
            0, 4, 1, 1,
        )

        label4 = self.add_label(grid,
            '<i>' + _('e.g. --cookies COOKIEPATH') + '</i>',
            0, 5, 1, 1,
        )

        textview2, textbuffe2r = self.add_textview(grid,
            'fetch_subtitles_cmd_string',
            0, 6, 1, 1,
        )

        tooltip = _(
            'Arguments containing special shell characters' \
            + '(+ - & < > = ? * ! : ; \\ / and brackets) should be' \
            + ' enclosed within quotes, e.g. -f "(137/136)"',
        )
        self.add_tooltip(tooltip, label, label2, textview)
        self.add_tooltip(tooltip, label3, label4, textview2)


    # (Tab support functions - general)


    def file_tab_sensitise_widgets(self, flag):

        """Called by self.setup_files_names_tab() and
        self.on_file_tab_combo_changed().

        Sensitises or desensitises a list of widgets in response to the user's
        interactions with widgets on that tab.

        Also resets comboboxes to show their first items.

        Args:

            flag (bool): True to sensitise the widgets, False to desensitise
                them

        """

        self.template_flag = flag
        for widget in self.template_widget_list:

            widget.set_sensitive(flag)

            # All combos in this tab (except for the one in the top-left
            #   corner, which is not in self.template_widget_list) must be
            #   reset to show their first item
            if isinstance(widget, Gtk.ComboBox):
                widget.set_active(0)


    def file_tab_update_time_format(self, value, entry, button):

        """Called by self.on_date_time_combo_changed() and
        .on_file_tab_reset_button_clicked().

        Updates the contents of the 'Time format' entry box, and (de)sensitises
        widgets.

        Args:

            value (str): A component used in youtube-dl's output template

            entry (Gtk.Entry): A widget to update

            button (Gtk.Button): Another widget to update

        """

        if value == 'release_date_custom' \
        or value == 'upload_date_custom':

            entry.set_text('%Y-%m-%d')
            entry.set_sensitive(True)
            button.set_sensitive(True)

        elif value == 'timestamp_custom' \
        or value == 'duration_custom':

            entry.set_text('%H-%M-%S')
            entry.set_sensitive(True)
            button.set_sensitive(True)

        else:

            entry.set_text('')
            entry.set_sensitive(False)
            button.set_sensitive(False)


    def formats_tab_count_formats(self):

        """Called by several parts of self.setup_formats_tab().

        Counts the number of video/audio formats that are set.

        Return values:

            An integer in the range 0-3

        """

        format_list = self.retrieve_val('video_format_list')

        return len(format_list)


    def formats_tab_redraw_list(self):

        """Called by self.setup_formats_tab() and then again by
        self.apply_changes().

        Update the Gtk.ListStore containing the user's preferred video/audio
        formats.
        """

        # Empty the treeview
        self.formats_liststore.clear()

        # (Need to reverse formats.VIDEO_OPTION_DICT for quick lookup)
        rev_dict = {}
        for key in formats.VIDEO_OPTION_DICT:
            rev_dict[formats.VIDEO_OPTION_DICT[key]] = key

        # Refill the treeview
        format_list = self.retrieve_val('video_format_list')
        for item in format_list:

            if item in rev_dict:
                self.formats_liststore.append([rev_dict[item]])
            else:
                # Non-standard format, not specified by
                #   formats.VIDEO_OPTION_DICT
                self.formats_liststore.append([item])


    # (Tab support functions - Downloads tab)


    def downloads_age_widgets(self, grid, row_count):

        """Called by various parts of the Downloads tabs."""

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Limits'
        )

        # Video age options
        self.add_label(grid,
            '<u>' + _('Video age options') + '</u>',
            0, row_count, 1, 1,
        )

        label = self.add_label(grid,
            _('Download videos suitable for this age'),
            0, (row_count + 1), 1, 1,
        )

        entry = self.add_entry(grid,
            'age_limit',
            1, (row_count + 1), 1, 1,
        )
        self.add_tooltip('--age-limit YEARS', label, entry)

        return row_count + 2


    def downloads_date_widgets(self, grid, row_count):

        """Called by various parts of the Downloads tabs."""

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Limits'
        )

        grid_width = 3

        # Video date options
        self.add_label(grid,
            '<u>' + _('Video date options') + '</u>',
            0, row_count, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Only videos uploaded on this date'),
            0, (row_count + 1), (grid_width - 2), 1,
        )

        entry = self.add_entry(grid,
            'date',
            (grid_width - 2), (row_count + 1), 1, 1,
        )
        entry.set_editable(False)

        button = Gtk.Button(_('Set'))
        grid.attach(button, (grid_width - 1), (row_count + 1), 1, 1)
        button.connect(
            'clicked',
            self.on_button_set_date_clicked,
            entry,
            'date',
        )
        self.add_tooltip('--date DATE', label, entry, button)

        label2 = self.add_label(grid,
            _('Only videos uploaded before this date'),
            0, (row_count + 2), (grid_width - 2), 1,
        )

        entry2 = self.add_entry(grid,
            'date_before',
            (grid_width - 2), (row_count + 2), 1, 1,
        )
        entry2.set_editable(False)

        button2 = Gtk.Button(_('Set'))
        grid.attach(button2, (grid_width - 1), (row_count + 2), 1, 1)
        button2.connect(
            'clicked',
            self.on_button_set_date_clicked,
            entry2,
            'date_before',
        )
        self.add_tooltip('--datebefore DATE', label2, entry2, button2)

        label3 = self.add_label(grid,
            _('Only videos uploaded after this date'),
            0, (row_count + 3), (grid_width - 2), 1,
        )

        entry3 = self.add_entry(grid,
            'date_after',
            (grid_width - 2), (row_count + 3), 1, 1,
        )
        entry3.set_editable(False)

        button3 = Gtk.Button(_('Set'))
        grid.attach(button3, (grid_width - 1), (row_count + 3), 1, 1)
        button3.connect(
            'clicked',
            self.on_button_set_date_clicked,
            entry3,
            'date_after',
        )
        self.add_tooltip('--dateafter DATE', label3, entry3, button3)

        return row_count + 4


    def downloads_external_widgets(self, grid, row_count):

        """Called by various parts of the Downloads tabs."""

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > External'
        )

        grid_width = 2

        # External downloader options
        self.add_label(grid,
            '<u>' + _('External downloader options') + '</u>',
            0, row_count, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Use this external downloader'),
            0, (row_count + 1), 1, 1,
        )

        ext_list = [
            '', 'aria2c', 'avconv', 'axel', 'curl', 'ffmpeg', 'httpie',
            'wget',
        ]

        combo = self.add_combo(grid,
            ext_list,
            'external_downloader',
            1, (row_count + 1), 1, 1,
        )
        combo.set_hexpand(True)
        self.add_tooltip('--external-downloader COMMAND', label, combo)

        label2 = self.add_label(grid,
            _('Arguments to pass to external downloader'),
            0, (row_count + 2), grid_width, 1,
        )

        entry = self.add_entry(grid,
            'external_arg_string',
            0, (row_count + 3), grid_width, 1,
        )
        self.add_tooltip('--external-downloader-args ARGS', label2, entry)

        return row_count + 4


    def downloads_filtering_widgets(self, grid, row_count):

        """Called by various parts of the Downloads tabs."""

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Filtering'
        )

        grid_width = 3

        # Video filtering options
        self.add_label(grid,
            '<u>' + _('Video filtering options') + '</u>',
            0, row_count, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Download only matching titles (regex or caseless substring)'),
            0, (row_count + 1), grid_width, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            'match_title_list',
            0, (row_count + 2), grid_width, 1,
        )
        self.add_tooltip('--match-title REGEX', label, textview)

        label2 = self.add_label(grid,
            _(
            'Don\'t download only matching titles (regex or caseless' \
            + ' substring)',
            ),
            0, (row_count + 3), grid_width, 1,
        )

        textview2, textbuffer2 = self.add_textview(grid,
            'reject_title_list',
            0, (row_count + 4), grid_width, 1,
        )
        self.add_tooltip('--reject-title REGEX', label2, textview2)

        label3 = self.add_label(grid,
            _('Generic video filter, for example:') + ' like_count > 100',
            0, (row_count + 5), grid_width, 1,
        )

        entry = self.add_entry(grid,
            'match_filter',
            0, (row_count + 6), grid_width, 1,
        )
        self.add_tooltip('--match-filter FILTER', label3, entry)

        return row_count + 7


    def downloads_general_widgets(self, grid, row_count):

        """Called by various parts of the Downloads tabs."""

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > General'
        )

        grid_width = 3

        checkbutton = self.add_checkbutton(grid,
            _('Prefer HLS (HTTP Live Streaming)'),
            'native_hls',
            0, row_count, grid_width, 1,
        )
        self.add_tooltip('--hls-prefer-native', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('Prefer FFMpeg over native HLS downloader'),
            'hls_prefer_ffmpeg',
            0, (row_count + 1), grid_width, 1,
        )
        self.add_tooltip('--hls-prefer-ffmpeg', checkbutton2)

        checkbutton3 = self.add_checkbutton(grid,
            _('Include advertisements (experimental feature)'),
            'include_ads',
            0, (row_count + 2), grid_width, 1,
        )
        self.add_tooltip('--include-ads', checkbutton3)

        checkbutton4 = self.add_checkbutton(grid,
            _('Ignore errors and continue the download operation'),
            'ignore_errors',
            0, (row_count + 3), grid_width, 1,
        )
        self.add_tooltip('-i, --ignore-errors', checkbutton4)

        checkbutton5 = self.add_checkbutton(grid,
            _('Abort video download if fragments are unavailable'),
            'abort_on_unavailable_fragment',
            0, (row_count + 4), grid_width, 1,
        )
        self.add_tooltip('--abort-on-unavailable-fragment', checkbutton5)

        label = self.add_label(grid,
            _('Number of retries'),
            0, (row_count + 5), 1, 1,
        )

        spinbutton = self.add_spinbutton(grid,
            1, 99, 1,
            'retries',
            1, (row_count + 5), 1, 1,
        )
        self.add_tooltip('-R, --retries RETRIES', label, spinbutton)

        return row_count + 6


    def downloads_playlist_widgets(self, grid, row_count):

        """Called by various parts of the Downloads tabs."""

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Playlists'
        )

        grid_width = 2

        # Playlist options
        self.add_label(grid,
            '<u>' + _('Playlist options') + '</u>',
            0, row_count, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'Channels and playlists are handled in the same way, so' \
                + ' these options can be used with both',
            ) + '</i>',
            0, (row_count + 1), grid_width, 1,
        )

        label = self.add_label(grid,
            _('Start downloading playlist from index'),
            0, (row_count + 2), 1, 1,
           )

        spinbutton = self.add_spinbutton(grid,
            1, None, 1,
            'playlist_start',
            1, (row_count + 2), 1, 1,
        )
        self.add_tooltip('--playlist-start NUMBER', label, spinbutton)

        label2 = self.add_label(grid,
            _('Stop downloading playlist at index'),
            0, (row_count + 3), 1, 1,
        )

        spinbutton2 = self.add_spinbutton(grid,
            0, None, 1,
            'playlist_end',
            1, (row_count + 3), 1, 1,
        )
        self.add_tooltip('--playlist-end NUMBER', label2, spinbutton2)

        label3 = self.add_label(grid,
            _('Download playlist range, in form START:STOP:STEP'),
            0, (row_count + 4), 1, 1,
        )

        entry = self.add_entry(grid,
            'playlist_items',
            1, (row_count + 4), 1, 1,
        )
        entry.set_hexpand(True)
        self.add_tooltip('--playlist-items ITEM_SPEC', label3, entry)

        label4 = self.add_label(grid,
            _('Abort operation after downloading this many videos'),
            0, (row_count + 5), 1, 1,
        )

        spinbutton3 = self.add_spinbutton(grid,
            0, None, 1,
            'max_downloads',
            1, (row_count + 5), 1, 1,
        )
        self.add_tooltip('--max-downloads NUMBER', label4, spinbutton3)

        checkbutton = self.add_checkbutton(grid,
            _('Abort downloading the playlist if an error occurs'),
            'abort_on_error',
            0, (row_count + 6), grid_width, 1,
        )
        self.add_tooltip('--abort-on-error', checkbutton)

        checkbutton2 = self.add_checkbutton(grid,
            _('Download playlist in reverse order'),
            'playlist_reverse',
            0, (row_count + 7), grid_width, 1,
        )
        self.add_tooltip('--playlist-reverse', checkbutton2)

        checkbutton3 = self.add_checkbutton(grid,
            _('Download playlist in random order'),
            'playlist_random',
            0, (row_count + 8), grid_width, 1,
        )
        self.add_tooltip('--playlist-random', checkbutton3)

        return row_count + 8


    def downloads_size_limit_widgets(self, grid, row_count):

        """Called by various parts of the Downloads tabs."""

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Limits'
        )

        grid_width = 3

        # Video size limit options
        self.add_label(grid,
            '<u>' + _('Video size limit options') + '</u>',
            0, row_count, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Minimum file size for video downloads'),
            0, (row_count + 1), (grid_width - 2), 1,
        )

        spinbutton = self.add_spinbutton(grid,
            0, None, 1,
            'min_filesize',
               (grid_width - 2), (row_count + 1), 1, 1,
        )

        combo = self.add_combo_with_data(grid,
            formats.FILE_SIZE_UNIT_LIST,
            'min_filesize_unit',
            (grid_width - 1), (row_count + 1), 1, 1,
        )
        self.add_tooltip('--min-filesize SIZE', label, spinbutton, combo)

        label2 = self.add_label(grid,
            _('Maximum file size for video downloads'),
            0, (row_count + 2), (grid_width - 2), 1,
        )

        spinbutton2 = self.add_spinbutton(grid,
            0, None, 1,
            'max_filesize',
            (grid_width - 2), (row_count + 2), 1, 1,
        )

        combo2 = self.add_combo_with_data(grid,
            formats.FILE_SIZE_UNIT_LIST,
            'max_filesize_unit',
            (grid_width - 1), (row_count + 2), 1, 1,
        )
        self.add_tooltip('--max-filesize SIZE', label2, spinbutton2, combo2)

        return row_count + 3


    def downloads_views_widgets(self, grid, row_count):

        """Called by various parts of the Downloads tabs."""

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Download options > Downloads > Limits'
        )

        grid_width = 3

        # Video views options
        self.add_label(grid,
            '<u>' + _('Video views options') + '</u>',
            0, row_count, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Minimum number of views'),
            0, (row_count + 1), (grid_width - 2), 1,
        )

        spinbutton = self.add_spinbutton(grid,
            0, None, 1,
            'min_views',
            (grid_width - 2), (row_count + 1), 1, 1,
        )
        self.add_tooltip('--min-views COUNT', label, spinbutton)

        label2 = self.add_label(grid,
            _('Maximum number of views'),
            0, (row_count + 2), (grid_width - 2), 1,
        )

        spinbutton2 = self.add_spinbutton(grid,
            0, None, 1,
            'max_views',
            (grid_width - 2), (row_count + 2), 1, 1,
        )
        self.add_tooltip('--max-views COUNT', label2, spinbutton2)

        # (This improves layout a little)
        if not self.app_obj.simple_options_flag:
            spinbutton.set_hexpand(True)
            spinbutton2.set_hexpand(True)

        return row_count + 3


    # Callback class methods


    def on_button_set_date_clicked(self, button, entry, prop):

        """Called by callback in self.downloads_date_widgets().

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

            prop (str): The attribute in self.edit_dict to modify

        """

        # Prompt the user for a new calendar date
        dialogue_win = mainwin.CalendarDialogue(
            self,
            self.retrieve_val(prop),
        )

        response = dialogue_win.run()

        # Retrieve user choices from the dialogue window, before destroying it
        if response == Gtk.ResponseType.OK:
            date_tuple = dialogue_win.calendar.get_date()

        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK and date_tuple:

            year = str(date_tuple[0])           # e.g. 2011
            month = str(date_tuple[1] + 1)      # Values in range 0-11
            day = str(date_tuple[2])            # Values in range 1-31

            entry.set_text(
                year.zfill(4) + month.zfill(2) + day.zfill(2)
            )

        else:

            entry.set_text('')


    def on_check_fetch_comments_button_toggled(self, checkbutton, \
    checkbutton2):

        """Called by callback in self.setup_downloads_comments_tab().

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to update

        """

        if checkbutton.get_active():
            self.edit_dict['check_fetch_comments'] = True
            checkbutton2.set_sensitive(True)

        else:
            self.edit_dict['check_fetch_comments'] = False
            if not self.retrieve_val('dl_fetch_comments', False):
                checkbutton2.set_active(False)
                checkbutton2.set_sensitive(False)


    def on_clone_options_clicked(self, button):

        """Called by callback in self.setup_name_tab().

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Name'
        )

        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _(
            'This procedure cannot be reversed. Are you sure you want to' \
            + ' continue?',
            ),
            'question',
            'yes-no',
            self,           # Parent window is this window
            {
                'yes': 'clone_download_options_from_window',
                'data': [self, self.edit_obj],
            },
        )


    def on_cookies_set_button_clicked(self, button, entry):

        """Called by callback in self.setup_files_cookies_tab().

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Files > Cookies'
        )

        # Prompt the user for a new file
        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Select the cookie jar file'),
            self,
            'open',
        )

        cookie_path = self.retrieve_val('cookies_path')

        if cookie_path == '':
            cookie_dir = self.app_obj.data_dir
        else:
            cookie_dir, cookie_file = os.path.split(cookie_path)

        dialogue_win.set_current_folder(cookie_dir)

        # Get the user's response
        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()
        if response == Gtk.ResponseType.OK:

            self.edit_dict['cookies_path'] = new_path
            entry.set_text(new_path)


    def on_cookies_reset_button_clicked(self, button, entry):

        """Called by callback in self.setup_files_cookies_tab().

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

        """

        self.edit_dict['cookies_path'] = ''
        entry.set_text(
            os.path.abspath(
                os.path.join(
                    self.app_obj.data_dir,
                    self.app_obj.cookie_file_name,
                ),
            ),
        )


    def on_cookies_ytdlp_entry_changed(self, widget, entry, combo, \
    combo2, entry2, entry3):

        """Called by callback in self.setup_files_cookies_tab().

        Args:

            widget (Gtk.Entry): The widget modified (ignored)

            entry (Gtk.Entry): The entry box displaying the download option

            combo, combo2, entry2, entry3 (Gtk.Combo, Gtk.Entry): Widgets whose
                settings are combined to set the 'cookies_from_browser'
                download option

        """

        # (The other entry also specifies the profile; at least one of them
        #   must be empty)
        if entry2.get_text() != '':
            entry3.set_text('')

        # Update the download option, and display it in 'entry'
        self.setup_files_cookies_tab_update(
            None,
            entry,
            combo,
            combo2,
            entry2,
            entry3,
        )


    def on_cookies_ytdlp_reset_button_clicked(self, button, entry, combo, \
    combo2, entry2, entry3):

        """Called by callback in self.setup_files_cookies_tab().

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): The entry box displaying the download option

            combo, combo2, entry2, entry3 (Gtk.Combo, Gtk.Entry): Widgets whose
                settings are combined to set the 'cookies_from_browser'
                download option

        """

        entry3.set_text('')

        # Update the download option, and display it in 'entry'
        self.setup_files_cookies_tab_update(
            None,
            entry,
            combo,
            combo2,
            entry2,
            entry3,
        )


    def on_cookies_ytdlp_set_button_clicked(self, button, entry, combo, \
    combo2, entry2, entry3):

        """Called by callback in self.setup_files_cookies_tab().

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): The entry box displaying the download option

            combo, combo2, entry2, entry3 (Gtk.Combo, Gtk.Entry): Widgets whose
                settings are combined to set the 'cookies_from_browser'
                download option

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Files > Cookies'
        )

        # Prompt the user for a new file
        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Select the browser profile'),
            self,
            'open',
        )

        # Get the user's response
        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = dialogue_win.get_filename()

        dialogue_win.destroy()
        if response == Gtk.ResponseType.OK:
            entry3.set_text(new_path)

            # (The other entry also specifies the profile; at least one of them
            #   must be empty)
            if new_path != '':
                entry2.set_text('')

        # Update the download option, and display it in 'entry'
        self.setup_files_cookies_tab_update(
            None,
            entry,
            combo,
            combo2,
            entry2,
            entry3,
        )


    def on_date_time_combo_changed(self, combo, entry, button, trans_dict):

        """Called by callback in self.setup_files_filesystem_tab().

        The 'Date/time/location' combo sets or resets the entry just beneath
        it, every time the user selects a new combo item.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            entry (Gtk.Entry): Another widget to update

            button (Gtk.Button): Another widget to update

            trans_dict (dict): Converts a translated string into the string
                used by youtube-dl

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        value = trans_dict[model[tree_iter][0]]

        self.file_tab_update_time_format(value, entry, button)


    def on_direct_cmd_toggled(self, checkbutton, checkbutton2):

        """Called by callback in self.setup_name_tab().

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to modify

        """

        if not checkbutton.get_active():
            self.edit_dict['direct_cmd_flag'] = False
            checkbutton2.set_active(False)
            checkbutton2.set_sensitive(False)

        else:

            self.edit_dict['direct_cmd_flag'] = True
            checkbutton2.set_sensitive(True)


    def on_dl_comment_fetch_button_toggled(self, checkbutton, checkbutton2):

        """Called by callback in self.setup_downloads_comments_tab().

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            checkbutton2 (Gtk.CheckButton): Another widget to update

        """

        if checkbutton.get_active():
            self.edit_dict['dl_fetch_comments'] = True
            checkbutton2.set_sensitive(True)

        else:
            self.edit_dict['dl_fetch_comments'] = False
            if not self.retrieve_val('check_fetch_comments', False):
                checkbutton2.set_active(False)
                checkbutton2.set_sensitive(False)



    def on_dl_config_button_clicked(self, button, entry, textbuffer, \
    dl_config_path):

        """Called by callback in self.setup_advanced_configuration_tab().

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to modify

            textbuffer (Gtk.TextBuffer): Buffer for the textview containing
                the text to be saved

            dl_config_path (str): FUll path to the downloader's configuration
                file

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Advanced > Configurations'
        )

        # Save the file
        try:

            dir_path = os.path.dirname(dl_config_path)
            if not os.path.isdir(dir_path):
                self.app_obj.make_directory(dir_path)

            fh = open(dl_config_path, 'w')
            fh.write(
                textbuffer.get_text(
                    textbuffer.get_start_iter(),
                    textbuffer.get_end_iter(),
                    # Don't include hidden characters
                    False,
                ),
            )
            fh.close()

        except:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Could not save the downloader\'s configuration file'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        entry.set_text(dl_config_path)

        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _('Downloader\'s configuration file saved'),
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_embed_checkbutton_toggled(self, checkbutton):

        """Called by callback in self.setup_post_process_tab() or
        setup_subtitles_more_options_tab().

        The 'embed_subs' option appears in both the Formats and Subtitles tabs.
        When one widget is modified, we need to set the other widgets to match
        without starting an infinite loop of signal connects.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        prop = 'embed_subs'

        if checkbutton == self.embed_checkbutton2 \
        and self.embed_checkbutton is None:

            # An easy case; the Formats tab isn't visible, so there is only one
            #   widget to think about
            if not checkbutton.get_active():
                self.edit_dict[prop] = False
            else:
                self.edit_dict[prop] = True

        else:

            # We get around the infinite loop problem by setting the other
            #   checkbutton, if it's in the opposite state to this checkbutton
            flag = checkbutton.get_active()

            if checkbutton == self.embed_checkbutton:

                if self.embed_checkbutton2.get_active() != flag:
                    self.embed_checkbutton2.set_active(flag)
                elif not checkbutton.get_active():
                    self.edit_dict[prop] = False
                else:
                    self.edit_dict[prop] = True

            else:

                if self.embed_checkbutton.get_active() != flag:
                    self.embed_checkbutton.set_active(flag)
                elif not checkbutton.get_active():
                    self.edit_dict[prop] = False
                else:
                    self.edit_dict[prop] = True


    def on_fixed_folder_changed(self, combo):

        """Called by callback in self.setup_files_filesystem_tab().

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        dbid = model[tree_iter][1]
        if dbid == self.app_obj.fixed_temp_folder.dbid:
            self.edit_dict['use_fixed_folder'] = 'temp'
        elif dbid == self.app_obj.fixed_misc_folder.dbid:
            self.edit_dict['use_fixed_folder'] = 'misc'
        elif dbid == self.app_obj.fixed_clips_folder.dbid:
            self.edit_dict['use_fixed_folder'] = 'clips'
        else:
            # Failsafe
            self.edit_dict['use_fixed_folder'] = None


    def on_fixed_folder_toggled(self, checkbutton, combo):

        """Called by callback in self.setup_files_filesystem_tab().

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            combo (Gtk.ComboBox): Another widget to be modified by this
                function

        """

        if not checkbutton.get_active():
            self.edit_dict['use_fixed_folder'] = None
            combo.set_sensitive(False)

        else:

            tree_iter = combo.get_active_iter()
            model = combo.get_model()
            dbid = model[tree_iter][1]
            if dbid == self.app_obj.fixed_temp_folder.dbid:
                self.edit_dict['use_fixed_folder'] = 'temp'
            elif dbid == self.app_obj.fixed_misc_folder.dbid:
                self.edit_dict['use_fixed_folder'] = 'misc'
            elif dbid == self.app_obj.fixed_clips_folder.dbid:
                self.edit_dict['use_fixed_folder'] = 'clips'
            else:
                # Failsafe
                self.edit_dict['use_fixed_folder'] = None

            combo.set_sensitive(True)


    def on_file_tab_add_button_clicked(self, button, entry, entry2, combo, \
    trans_dict):

        """Called by callback in self.setup_files_names_tab().

        Args:

            button (Gtk.Button): The widget clicked

            entry, entry2 (Gtk.Entry): Other widgets to be modified by this
                function

            combo (Gtk.ComboBox): Another widget to be modified by this
                function

            trans_dict (dict): Converts a translated string into the string
                used by youtube-dl

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        value = trans_dict[model[tree_iter][0]]

        # The new component should be inserted at the end of the filename, and
        #   before the file extension (if possible)
        output_template = file_name = self.retrieve_val('output_template')
        file_ext = ''
        if value != 'ext' and output_template:

            match = re.search(r'(.*)(\.\%\(ext\)s)\s*$', output_template)
            if match:

                file_name = match.groups()[0]
                file_ext = match.groups()[1]

        if not output_template or output_template[-1] == os.sep:
            prefix = ''
        elif value == 'ext':
            prefix = '.'
        else:
            prefix = '-'

        # e.g. to generate '(upload_date>%Y-%m-%d)s'
        time_format = entry2.get_text()
        if time_format != '':

            if value == 'release_date_custom':
                value = 'release_date>' + time_format
            elif value == 'upload_date_custom':
                value = 'upload_date>' + time_format
            elif value == 'timestamp_custom':
                value = 'timestamp>' + time_format
            elif value == 'duration_custom':
                value = 'duration>' + time_format

        if value == 'video_autonumber':
            formatted = '{0}%({1})3d'.format(prefix, value)
        else:
            formatted = '{0}%({1})s'.format(prefix, value)

        # (Setting the entry updates self.edit_dict)
        if value == 'ext':
            entry.set_text(file_name + file_ext + formatted)
        else:
            entry.set_text(file_name + formatted + file_ext)


    def on_file_tab_reset_button_clicked(self, button, entry, combo, \
    trans_dict):

        """Called by callback in self.setup_files_names_tab().

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to be modified by this function

            combo (Gtk.ComboBox): Another widget to be modified by this
                function

            trans_dict (dict): Converts a translated string into the string
                used by youtube-dl

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        value = trans_dict[model[tree_iter][0]]

        self.file_tab_update_time_format(value, entry, button)


    def on_file_tab_main_combo_changed(self, combo, entry, entry2, button):

        """Called by callback in self.setup_files_names_tab().

        Args:

            combo (Gtk.ComboBox): The widget clicked

            entry, entry2 (Gtk.Entry): Other widgets to be modified

            button (Gtk.Button): Another widget to be modified

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        row_id, name = model[tree_iter][:2]

        self.edit_dict['output_format'] = row_id

        # The custom template is associated with the index 0
        if row_id == 0:

            self.file_tab_sensitise_widgets(True)
            # (The call to that function sensitises the 'Time format' widgets,
            #   but they must be desensitised when a custom format is not
            #   selected)
            entry2.set_sensitive(False)
            button.set_sensitive(False)

            entry.set_text(self.retrieve_val('output_template'))

        else:

            self.file_tab_sensitise_widgets(False)
            entry.set_text(formats.FILE_OUTPUT_CONVERT_DICT[row_id])


    def on_file_tab_main_entry_changed(self, entry):

        """Called by callback in self.setup_files_names_tab().

        Args:

            entry (Gtk.Entry): The widget clicked

        """

        # Only set 'output_template' when option 3 is selected, which is when
        #   the entry is sensitised
        if self.template_flag:
            self.edit_dict['output_template'] = entry.get_text()


    def on_formats_tab_add_clicked(self, add_button, remove_button, \
    up_button, down_button, treeview):

        """Called by callback in self.setup_formats_tab_add_grid().

        Args:

            add_button (Gtk.Button): The widget clicked

            remove_button, up_button, down_button (Gtk.Button): Other widgets
                to be modified by this function

            treeview (Gtk.TreeView): The treeview on the left side of the tab

        """

        selection = treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:

            # Nothing selected
            return

        else:

            name = model[tree_iter][0]
            # Convert string e.g. 'mp4 [360p]' to the extractor code e.g. '18'
            extract_code = formats.VIDEO_OPTION_DICT[name]

        # Update the option
        format_list = self.retrieve_val('video_format_list')
        if extract_code in format_list:
            return
        else:
            format_list.append(extract_code)
            self.edit_dict['video_format_list'] = format_list

        # Update the other treeview, adding the format to it (and don't modify
        #   this treeview)
        self.formats_liststore.append([name])

        # Update other widgets, as required
        remove_button.set_sensitive(True)
        up_button.set_sensitive(True)
        down_button.set_sensitive(True)


    def on_formats_tab_combo_changed(self, combo):

        """Called by callback in self.setup_formats_tab_add_grid().

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Formats > Preferred'
        )

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        val = model[tree_iter][0]

        self.edit_dict['merge_output_format'] = val

        # For some reason, this youtube-dl download option doesn't work if the
        #   specified format (e.g. 'mp4') isn't also specified in the list of
        #   preferred formats
        # Warn the user about that, where appropriate
        format_list = self.retrieve_val('video_format_list')
        if val != '' and not val in format_list:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _(
                'This option won\'t work unless the format is also added to' \
                + ' the list of preferred formats above',
                ),
                'warning',
                'ok',
                self,           # Parent window is this window
            )


    def on_formats_tab_down_clicked(self, down_button, treeview):

        """Called by callback in self.setup_formats_tab_add_grid().

        Args:

            down_button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): Another widget to be modified by this
                function

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            # Nothing selected
            return

        else:

            this_iter = model.get_iter(path_list[0])
            name = model[this_iter][0]
            # Convert string e.g. 'mp4 [360p]' to the extractor code e.g. '18',
            #   unless it's a non-standard extractor code
            if name in formats.VIDEO_OPTION_DICT:
                extract_code = formats.VIDEO_OPTION_DICT[name]
            else:
                extract_code = name

        # Update the option
        format_list = self.retrieve_val('video_format_list')
        if extract_code in format_list:

            index = format_list.index(extract_code)
            if index < (len(format_list) - 1):
                format_list.remove(extract_code)
                format_list.insert((index + 1), extract_code)

                self.edit_dict['video_format_list'] = format_list

                # Update the other treeview
                this_path = path_list[0]
                next_path = this_path[0]+1
                model.move_after(
                    model.get_iter(this_path),
                    model.get_iter(next_path),
                )


    def on_formats_tab_remove_clicked(self, remove_button, add_button, \
    type_button, up_button, down_button, other_treeview):

        """Called by callback in self.setup_formats_tab_add_grid().

        Args:

            remove_button (Gtk.Button): The widget clicked

            add_button, type_button, up_button, down_button (Gtk.Button): Other
                widgets to be modified by this function

            other_treeview (Gtk.TreeView): The treeview on the right side of
                the tab

        """

        selection = other_treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:

            # Nothing selected
            return

        else:

            name = model[tree_iter][0]
            # Convert string e.g. 'mp4 [360p]' to the extractor code e.g. '18',
            #   unless it's a non-standard extractor code
            if name in formats.VIDEO_OPTION_DICT:
                extract_code = formats.VIDEO_OPTION_DICT[name]
            else:
                extract_code = name

        # Update the option
        format_list = self.retrieve_val('video_format_list')
        if extract_code in format_list:
            format_list.remove(extract_code)

            self.edit_dict['video_format_list'] = format_list

            # Update the right-hand side treeview
            model.remove(tree_iter)

            # Update other widgets, as required
            add_button.set_sensitive(True)
            type_button.set_sensitive(True)
            if not format_list:

                # No formats left to remove
                remove_button.set_sensitive(False)
                up_button.set_sensitive(False)
                down_button.set_sensitive(False)


    def on_formats_tab_type_clicked(self, type_button, remove_button, \
    up_button, down_button, treeview):

        """Called by callback in self.setup_formats_tab_add_grid().

        Args:

            type_button (Gtk.Button): The widget clicked

            remove_button, up_button, down_button (Gtk.Button): Other widgets
                to be modified by this function

            treeview (Gtk.TreeView): The treeview on the left side of the tab

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Formats > Preferred > Type extractor code' \
            + ' directly',
        )

        # Prompt the user to type an extractor code directly
        dialogue_win = mainwin.ExtractorCodeDialogue(self)
        response = dialogue_win.run()

        # Retrieve user choices from the dialogue window, before destroying it
        if response == Gtk.ResponseType.OK:
            extract_code = dialogue_win.extract_code

        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK and extract_code is not None:

            # Update the option (code copied from
            #   self.on_formats_tab_add_clicked() above)
            format_list = self.retrieve_val('video_format_list')
            if extract_code in format_list:
                return
            else:
                format_list.append(extract_code)
                self.edit_dict['video_format_list'] = format_list

            # Update the other treeview, adding the specified format to it (but
            #   don't modify this treeview)
            add_flag = False
            for name in formats.VIDEO_OPTION_DICT.keys():
                if formats.VIDEO_OPTION_DICT[name] == extract_code:
                    self.formats_liststore.append([name])
                    add_flag = True
                    break

            if not add_flag:
                # Non-standard format, with no entry in
                #   formats.VIDEO_OPTION_DICT
                self.formats_liststore.append([extract_code])

            # Update other widgets, as required
            remove_button.set_sensitive(True)
            up_button.set_sensitive(True)
            down_button.set_sensitive(True)


    def on_formats_tab_up_clicked(self, up_button, treeview):

        """Called by callback in self.setup_formats_tab_add_grid().

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): Another widget to be modified by this
                function

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            # Nothing selected
            return

        else:

            this_iter = model.get_iter(path_list[0])
            name = model[this_iter][0]
            # Convert string e.g. 'mp4 [360p]' to the extractor code e.g. '18',
            #   unless it's a non-standard extractor code
            if name in formats.VIDEO_OPTION_DICT:
                extract_code = formats.VIDEO_OPTION_DICT[name]
            else:
                extract_code = name

        # Update the option
        format_list = self.retrieve_val('video_format_list')
        if extract_code in format_list:

            index = format_list.index(extract_code)
            if index > 0:
                format_list.remove(extract_code)
                format_list.insert((index - 1), extract_code)

                self.edit_dict['video_format_list'] = format_list

                # Update the other treeview
                this_path = path_list[0]
                prev_path = this_path[0]-1
                model.move_before(
                    model.get_iter(this_path),
                    model.get_iter(prev_path),
                )


    def on_netrc_button_clicked(self, button, entry, textbuffer, netrc_path):

        """Called by callback in self.setup_advanced_netrc_tab().

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to modify

            textbuffer (Gtk.TextBuffer): Buffer for the textview containing
                the text to be saved

            netrc_path (str): FUll path to the .netrc file

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Advanced > .netrc'
        )

        if not os.path.isfile(netrc_path):
            new_flag = True
        else:
            new_flag = False

        # Save the file
        try:
            fh = open(netrc_path, 'w')
            fh.write(
                textbuffer.get_text(
                    textbuffer.get_start_iter(),
                    textbuffer.get_end_iter(),
                    # Don't include hidden characters
                    False,
                ),
            )
            fh.close()

        except:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Could not save the .netrc file'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        if new_flag:

            # For a newly-created file, set read/write permissions, as
            #   described in the youtube-dl documentation
            os.chmod(netrc_path, stat.S_IREAD | stat.S_IWRITE)

        entry.set_text(netrc_path)

        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _('.netrc file saved'),
            'info',
            'ok',
            self,           # Parent window is this window
        )


    def on_obsolete_format_checkbutton_toggled(self, checkbutton, liststore):

        """Called by callback in self.setup_formats_tab_add_grid().

        Toggles the display of obsolete YouTube formats in the tab's list.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            liststore (Gtk.ListStore): The widget to update

        """

        self.app_obj.set_hide_obsolete_formats_flag(checkbutton.get_active())
        self.setup_formats_tab_update_list(liststore)

        # Also update any other OptionsEditWin windows that are currently open
        for config_win_obj in self.app_obj.main_win_obj.config_win_list:

            if isinstance(config_win_obj, OptionsEditWin) \
            and config_win_obj.edit_obj != self.edit_obj \
            and config_win_obj.formats_checkbutton.get_active \
            != self.app_obj.hide_obsolete_formats_flag:
                config_win_obj.formats_checkbutton.set_active(
                    self.app_obj.hide_obsolete_formats_flag,
                )


    def on_reset_options_clicked(self, button):

        """Called by callback in self.setup_name_tab().

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Name'
        )

        self.app_obj.dialogue_manager_obj.show_msg_dialogue(
            _(
            'This procedure cannot be reversed. Are you sure you want to' \
            + ' continue?',
            ),
            'question',
            'yes-no',
            self,           # Parent window is this window
            {
                'yes': 'reset_download_options',
                # (Reset this edit window, if the user clicks 'yes')
                'data': [self],
            },
        )


    def on_simple_options_clicked(self, button):

        """Called by callback in self.setup_general_tab().

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Name'
        )

        if not self.app_obj.simple_options_flag:

            self.app_obj.set_simple_options_flag(True)

            if not self.edit_dict:
                # User has not changed any options, so redraw the window to
                #   show the same options.OptionsManager object
                self.reset_with_new_edit_obj(self.edit_obj)

            else:
                # User has already changed some options. We don't want to lose
                #   them, so wait for the window to close and be re-opened,
                #   before switching between simple/advanced options
                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _(
                    'Fewer download options will be visible when you click' \
                    + ' the \'Apply\' or \'Reset\' buttons (or when you' \
                    + ' close and then re-open the window)',
                    ),
                    'info',
                    'ok',
                    self,           # Parent window is this window
                )

                button.set_label(
                    _('Show advanced download options (when window re-opens)'),
                )

        else:

            self.app_obj.set_simple_options_flag(False)

            if not self.edit_dict:
                self.reset_with_new_edit_obj(self.edit_obj)

            else:
                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _(
                    'More download options will be visible when you click' \
                    + ' the \'Apply\' or \'Reset\' buttons (or when you' \
                    + ' close and then re-open the window)',
                    ),
                    'info',
                    'ok',
                    self,           # Parent window is this window
                )

                button.set_label(
                    _('Hide advanced download options (when window re-opens)'),
                )


    def on_sleep_button_changed(self, spinbutton, spinbutton2):

        """Called by callback in self.setup_advanced_workaround_tab().

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

            spinbutton2 (Gtk.SpinButton2): Another widget to update

        """

        value = int(spinbutton.get_value())

        self.edit_dict['min_sleep_interval'] = value
        if value == 0:
            spinbutton2.set_value(0)
            spinbutton2.set_sensitive(False)
        else:
            spinbutton2.set_sensitive(True)


    def on_subtitles_tab_add_clicked(self, button, treeview, other_liststore,
    rev_dict):

        """Called by callback in self.setup_subtitles_options_tab().

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview on the left side of the tab

            other_liststore (Gtk.ListStore): The liststore belonging to the
                treeview on the right side of the tab

            rev_dict (dict): A reversed formats.LANGUAGE_CODE_DICT

        """

        selection = treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:

            # Nothing selected
            return

        name = model[tree_iter][0]
        # From a string in the form 'English [en]', remove the language code to
        #    get a key in formats.LANGUAGE_CODE_DICT, e.g. 'English'
        match = re.search(r'^(.*)\s\[', name)
        if match:

            lang_name = match.groups()[0]
            if lang_name in formats.LANGUAGE_CODE_DICT:

                lang_code = formats.LANGUAGE_CODE_DICT[lang_name]

                # Retrieve the existing list of languages
                lang_code_list = self.retrieve_val('subs_lang_list')
                if not lang_code in lang_code_list:

                    lang_code_list.append(lang_code)

                # Sort by language name, not by language code
                lang_list = []
                mod_code_list = []
                for this_code in lang_code_list:
                    lang_list.append(rev_dict[this_code])

                lang_list.sort()
                for this_lang in lang_list:
                    mod_code_list.append(formats.LANGUAGE_CODE_DICT[this_lang])

                # Update the option...
                self.edit_dict['subs_lang_list'] = mod_code_list
                # ...and the treeview
                other_liststore.clear()
                for this_lang in lang_list:
                    other_liststore.append([
                        this_lang + ' [' \
                        + formats.LANGUAGE_CODE_DICT[this_lang] + ']',
                    ])


    def on_subtitles_tab_remove_clicked(self, button, other_treeview,
    other_liststore, rev_dict):

        """Called by callback in self.setup_subtitles_options_tab().

        Args:

            button (Gtk.Button): The widget clicked

            other_treeview (Gtk.TreeView): The treeview on the right side of
                the tab

            other_liststore (Gtk.ListStore): The liststore belonging to that
                treeview

            rev_dict (dict): A reversed formats.LANGUAGE_CODE_DICT

        """

        selection = other_treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:

            # Nothing selected
            return

        name = model[tree_iter][0]
        # From a string in the form 'English [en]', remove the language name to
        #   get a value in formats.LANGUAGE_CODE_DICT, e.g. 'en'
        match = re.search(r'^.*\s\[(.*)\]', name)
        if match:

            lang_code = match.groups()[0]

            # Retrieve the existing list of languages
            lang_code_list = self.retrieve_val('subs_lang_list')
            if lang_code in lang_code_list:

                lang_code_list.remove(lang_code)

            # Sort by language name, not by language code
            lang_list = []
            mod_code_list = []
            for this_code in lang_code_list:
                lang_list.append(rev_dict[this_code])

            lang_list.sort()
            for this_lang in lang_list:
                mod_code_list.append(formats.LANGUAGE_CODE_DICT[this_lang])

            # Update the option...
            self.edit_dict['subs_lang_list'] = mod_code_list
            # ...and the treeview
            other_liststore.clear()
            for this_lang in lang_list:
                other_liststore.append([
                    this_lang + ' [' \
                    + formats.LANGUAGE_CODE_DICT[this_lang] + ']',
                ])


    def on_subtitles_toggled(self, radiobutton, button, button2, prop):

        """Called by callback in self.setup_subtitles_options_tab().

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            button, button2 (Gtk.Button): Other widgets to be modified by this
                function

            prop (str): The attribute in self.edit_dict to modify

        """

        if radiobutton.get_active():

            if prop == 'write_subs':
                self.edit_dict['write_subs'] = False
                self.edit_dict['write_auto_subs'] = False
                self.edit_dict['write_all_subs'] = False
                button.set_sensitive(False)
                button2.set_sensitive(False)

            elif prop == 'write_auto_subs':
                self.edit_dict['write_subs'] = True
                self.edit_dict['write_auto_subs'] = True
                self.edit_dict['write_all_subs'] = False
                button.set_sensitive(False)
                button2.set_sensitive(False)

            elif prop == 'write_all_subs':
                self.edit_dict['write_subs'] = True
                self.edit_dict['write_auto_subs'] = False
                self.edit_dict['write_all_subs'] = True
                button.set_sensitive(False)
                button2.set_sensitive(False)

            elif prop == 'subs_lang':
                self.edit_dict['write_subs'] = True
                self.edit_dict['write_auto_subs'] = False
                self.edit_dict['write_all_subs'] = False
                button.set_sensitive(True)
                button2.set_sensitive(True)


    def on_video_format_mode_toggled(self, radiobutton, value):

        """Called by callback in self.setup_formats_advanced_tab().

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            prop (str): The attribute in self.edit_dict to modify

        """

        if radiobutton.get_active():
            self.edit_dict['video_format_mode'] = value


    def on_ytdlp_output_add_button_clicked(self, button, liststore, combo, \
    entry):

        """Called from callback in self.setup_files_override_tab().

        Adds a template to the 'output_format_list' option.

        Args:

            button (Gtk.Button): The widget clicked

            liststore (Gtk.ListStore): The treeview's model

            combo (Gtk.ComboBox): Widget providing the output type

            entry (Gtk.Entry): Widget providiing the output template

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        output_type = model[tree_iter][0]

        output_template = entry.get_text()
        if output_template == '':
            return

        # Items in the list are in the form TYPES:TEMPLATE
        # However, every item should have a uniquE TYPES component. If an item
        #   with a TYPES component matching 'output_type' already exists,
        #   overwrite it. Otherwise, add a new item to the end of the list
        output_format_list = self.retrieve_val('output_format_list')
        mod_list = []
        match_flag = False

        for item in output_format_list:

            match = re.search(r'^([^\:]+)\:', item)
            if match:
                this_output_type = match.groups()[0]

                if this_output_type == output_type:
                    mod_list.append(output_type + ':' + output_template)
                    match_flag = True

                else:
                    mod_list.append(item)

        if not match_flag:
            mod_list.append(output_type + ':' + output_template)

        # Update the option
        self.edit_dict['output_format_list'] = mod_list
        # Update the treeview
        self.setup_files_override_tab_update_treeview(liststore)


    def on_ytdlp_output_delete_button_clicked(self, button, treeview):

        """Called from a callback in self.setup_files_override_tab().

        Deletes the selected template to the 'output_format_list' option.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeVies): The treeview displaying the template list

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:
            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:
            return

        # Items in the list are in the form TYPES:TEMPLATE
        output_type = model[this_iter][0]
        output_template = model[this_iter][1]
        item = output_type + ':' + output_template
        # Walk the list, and delete the first matching group
        output_format_list = self.retrieve_val('output_format_list')
        mod_list = []
        match_flag = False

        for this_item in output_format_list:

            if not match_flag and this_item == item:
                match_flag = True   # Delete this one
            else:
                mod_list.append(this_item)

        # Update the option
        self.edit_dict['output_format_list'] = mod_list
        # Update the treeview
        self.setup_files_override_tab_update_treeview(treeview.get_model())


    def on_ytdlp_output_refresnh_button_clicked(self, button, treeview):

        """Called from a callback in self.setup_files_override_tab().

        Refreshes the treeview.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeVies): The treeview displaying the template list

        """

        # Update the treeview
        self.setup_files_override_tab_update_treeview(treeview.get_model())


    def on_ytdlp_paths_add_button_clicked(self, button, liststore, combo, \
    entry):

        """Called from callback in self.setup_files_paths_tab().

        Adds a path to the 'output_path_list' option.

        Args:

            button (Gtk.Button): The widget clicked

            liststore (Gtk.ListStore): The treeview's model

            combo (Gtk.ComboBox): Widget providing the output type

            entry (Gtk.Entry): Widget providiing the output path

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        output_type = model[tree_iter][0]

        output_path = entry.get_text()
        if output_path == '':
            return

        # Items in the list are in the form TYPES:PATH
        # However, every item should have a uniquE TYPES component. If an item
        #   with a TYPES component matching 'output_type' already exists,
        #   overwrite it. Otherwise, add a new item to the end of the list
        output_path_list = self.retrieve_val('output_path_list')
        mod_list = []
        match_flag = False

        for item in output_path_list:

            match = re.search(r'^([^\:]+)\:', item)
            if match:
                this_output_type = match.groups()[0]

                if this_output_type == output_type:
                    mod_list.append(output_type + ':' + output_path)
                    match_flag = True

                else:
                    mod_list.append(item)

        if not match_flag:
            mod_list.append(output_type + ':' + output_path)

        # Update the option
        self.edit_dict['output_path_list'] = mod_list
        # Update the treeview
        self.setup_files_paths_tab_update_treeview(liststore)


    def on_ytdlp_paths_delete_button_clicked(self, button, treeview):

        """Called from a callback in self.setup_files_paths_tab().

        Deletes the selected path to the 'output_path_list' option.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeVies): The treeview displaying the path list

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:
            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:
            return

        # Items in the list are in the form TYPES:PATH
        output_type = model[this_iter][0]
        output_path = model[this_iter][1]
        item = output_type + ':' + output_path
        # Walk the list, and delete the first matching group
        output_path_list = self.retrieve_val('output_path_list')
        mod_list = []
        match_flag = False

        for this_item in output_path_list:

            if not match_flag and this_item == item:
                match_flag = True   # Delete this one
            else:
                mod_list.append(this_item)

        # Update the option
        self.edit_dict['output_path_list'] = mod_list
        # Update the treeview
        self.setup_files_paths_tab_update_treeview(treeview.get_model())


    def on_ytdlp_paths_refresh_button_clicked(self, button, treeview):

        """Called from a callback in self.setup_files_paths_tab().

        Refreshes the treeview.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeVies): The treeview displaying the path list

        """

        # Update the treeview
        self.setup_files_paths_tab_update_treeview(treeview.get_model())


    def on_ytdlp_paths_set_button_clicked(self, button, entry):

        """Called from a callback in self.setup_files_paths_tab().

        Opens a file chooser dialogue to set the contents of the entry box.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to update

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Download options > Files > Paths'
        )

        # Prompt the user for a new file
        if os.name == 'nt':
            msg = _('Select the output folder')
        else:
            msg = _('Select the output directory')

        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            msg,
            self,
            'folder',
        )

        current_dir = entry.get_text()
        if current_dir:
            dialogue_win.set_current_folder(current_dir)

        response = dialogue_win.run()
        output_dir = dialogue_win.get_filename()
        dialogue_win.destroy()

        if response == Gtk.ResponseType.OK and output_dir != '':

            entry.set_text(output_dir)
