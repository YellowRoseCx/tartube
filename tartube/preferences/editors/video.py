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


class VideoEditWin(GenericEditWin):

    """Python class for an 'edit window' to modify values in a media.Video
    object.

    Args:

        app_obj (mainapp.TartubeApp): The main application object

        edit_obj (media.Video): The object whose attributes will be edited in
            this window

    """


    # Standard class methods


    def __init__(self, app_obj, edit_obj):

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Video properties window starts here.' \
            + ' In the main window, in the Videos tab, right-click a video' \
            + ' and select Show video > Properties...'
        )

        Gtk.Window.__init__(self, title=_('Video properties'))

        if self.is_duplicate(app_obj, edit_obj):
            return

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # The media.Video object being edited
        self.edit_obj = edit_obj


        # IV list - Gtk widgets
        # ---------------------
        self.grid = None                        # Gtk.Grid
        self.notebook = None                    # Gtk.Notebook
        self.reset_button = None                # Gtk.Button
        self.apply_button = None                # Gtk.Button
        self.ok_button = None                   # Gtk.Button
        self.cancel_button = None               # Gtk.Button
        # (Non-standard widgets)
        self.apply_options_button = None        # Gtk.Button
        self.edit_options_button = None         # Gtk.Button
        self.remove_options_button = None       # Gtk.Button
        # (Widgets used in the Timestamps tab)
        self.timestamp_liststore = None         # Gtk.ListStore
        # (Widgets used in the Slices tab)
        self.slice_liststore = None             # Gtk.ListStore
        # (Widgets used in the Comments tab)
        self.comment_scrolled = None            # Gtk.ScrolledWindow
        self.comment_treeview = None            # Gtk.TreeView
        self.comment_liststore = None           # Gtk.ListStore
        self.comment_listbox = None             # Gtk.ListBox
        self.filter_entry = None                # Gtk.Entry
        self.filter_togglebutton = None         # Gtk.ToggleButon
        self.filter_author_checkbutton = None   # Gtk.CheckButton
        self.filter_comment_checkbutton = None  # Gtk.CheckButton
        self.filter_uploader_checkbutton = None # Gtk.CheckButton
        self.filter_apply_button = None         # Gtk.ToolButton
        self.filter_cancel_button = None        # Gtk.ToolButton


        # IV list - other
        # ---------------
        # Size (in pixels) of gaps between edit window widgets
        self.spacing_size = self.app_obj.default_spacing_size
        # Flag set to True if all four buttons ('Reset', 'Apply', 'Cancel' and
        #   'OK') are required, or False if just the 'OK' button is required
        self.multi_button_flag = False

        # When the user changes a value, it is not applied to self.edit_obj
        #   immediately; instead, it is stored temporarily in this dictionary
        # If the user clicks the 'OK' or 'Apply' buttons at the bottom of the
        #   window, the changes are applied to self.edit_obj
        # If the user clicks the 'Reset' or 'Cancel' buttons, the dictionary
        #   is emptied and the changes are lost
        # The key-value pairs in the dictionary correspond directly to the
        #   names of attributes, and their values in self.edit_obj
        # Key-value pairs are added to this dictionary whenever the user makes
        #   a change (so if no changes are made when the window is closed, the
        #   dictionary will still be empty)
        self.edit_dict = {}

        # String identifying the media type
        self.media_type = 'video'


        # Code
        # ----

        # Set up the edit window
        self.setup()


    # Public class methods


#   def is_duplicate():         # Inherited from GenericConfigWin


#   def setup():                # Inherited from GenericConfigWin


#   def setup_grid():           # Inherited from GenericConfigWin


#   def setup_notebook():       # Inherited from GenericConfigWin


#   def add_notebook_tab():     # Inherited from GenericConfigWin


#   def setup_button_strip():   # Inherited from GenericEditWin


#   def setup_gap():            # Inherited from GenericConfigWin


    # (Non-widget functions)


    def apply_changes(self):

        """Called by self.on_button_ok_clicked() and
        self.on_button_apply_clicked().

        Any changes the user has made are temporarily stored in self.edit_dict.
        Apply to those changes to the object being edited.
        """

        # Apply any changes the user has made
        for key in self.edit_dict.keys():
            setattr(self.edit_obj, key, self.edit_dict[key])

        # The changes can now be cleared
        self.edit_dict = {}

        # Redraw this media.Video in the Video Catalogue, if it's visible
        GObject.timeout_add(
            0,
            self.app_obj.main_win_obj.video_catalogue_update_video,
            self.edit_obj,
        )


#   def retrieve_val():         # Inherited from GenericConfigWin


    # (Setup tabs)


    def setup_tabs(self):

        """Called by self.setup(), .on_button_apply_clicked() and
        .on_button_reset_clicked().

        Sets up the tabs for this edit window.
        """

        self.setup_general_tab()
        self.setup_download_options_tab()
        self.setup_livestream_tab()
        self.setup_descrip_tab()
        self.setup_timestamps_tab()
        self.setup_slices_tab()
        self.setup_comments_tab()
        self.setup_errors_warnings_tab()


    def setup_general_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'General' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Video properties > General'
        )

        tab, grid = self.add_notebook_tab(_('_General'))
        grid_width = 3

        # General properties
        self.add_label(grid,
            '<u>' + _('General properties') + '</u>',
            0, 0, grid_width, 1,
        )

        # The first sets of widgets are shared by multiple edit windows
        self.add_container_properties(grid)
        self.add_source_properties(grid)

        label = self.add_label(grid,
            _('File'),
            0, 6, 1, 1,
        )
        label.set_hexpand(False)

        frame = self.add_image(grid,
            self.app_obj.main_win_obj.icon_dict['stock_file'],
            1, 6, 1, 1,
        )
        # (The frame looks cramped without this. The icon itself is 16x16)
        frame.set_size_request(
            16 + (self.spacing_size * 2),
            -1,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 2, 6, 1, 1)

        entry = self.add_entry(grid2,
            None,
            0, 0, 1, 1,
        )
        entry.set_editable(False)
        if self.edit_obj.file_name:
            entry.set_text(self.edit_obj.get_actual_path(self.app_obj))

        if not self.app_obj.show_custom_icons_flag:
            button = Gtk.Button.new_from_icon_name(
                Gtk.STOCK_FILE,
                Gtk.IconSize.BUTTON,
            )
        else:
            button = Gtk.Button.new()
            button.set_image(
                Gtk.Image.new_from_pixbuf(
                    self.app_obj.main_win_obj.pixbuf_dict['stock_add'],
                ),
            )

        grid2.attach(button, 1, 0, 1, 1)
        button.set_tooltip_text(_('Set the file (if this is the wrong one)'))
        if self.edit_obj.parent_obj.name \
        in self.app_obj.container_unavailable_dict:
            button.set_sensitive(False)
        # (Signal connect appears below)

        # (Back to the main grid)
        label2 = self.add_label(grid,
            _('Metadata file'),
            0, 7, 2, 1,
        )
        label2.set_hexpand(False)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid3 = self.add_secondary_grid(grid, 2, 7, 1, 1)

        entry2 = self.add_entry(grid3,
            None,
            0, 0, 1, 1,
        )
        entry2.set_editable(False)

        metadata_path = None
        if self.retrieve_val('file_name') is not None:
            metadata_path = self.edit_obj.get_actual_path_by_ext(
                self.app_obj,
                '.info.json',
            )
            if metadata_path:
                entry2.set_text(metadata_path)

        if not self.app_obj.show_custom_icons_flag:
            button2 = Gtk.Button.new_from_icon_name(
                Gtk.STOCK_FILE,
                Gtk.IconSize.BUTTON,
            )
        else:
            button2 = Gtk.Button.new()
            button2.set_image(
                Gtk.Image.new_from_pixbuf(
                    self.app_obj.main_win_obj.pixbuf_dict['stock_file'],
                ),
            )

        grid3.attach(button2, 1, 0, 1, 1)
        button2.set_tooltip_text(
            _('Update database using the video\'s metadata file'),
        )
        if not metadata_path:
            button2.set_sensitive(False)
        # (Signal connect appears below)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid4 = self.add_secondary_grid(grid, 0, 8, grid_width, 1)

        checkbutton = self.add_checkbutton(grid4,
            _('Video downloaded'),
            'dl_flag',
            0, 0, 1, 1,
        )
        checkbutton.set_sensitive(False)

        checkbutton2 = self.add_checkbutton(grid4,
            _('Video unwatched'),
            'new_flag',
            1, 0, 1, 1,
        )
        checkbutton2.set_sensitive(False)

        checkbutton3 = self.add_checkbutton(grid4,
            _('Video has been split from an original'),
            'split_flag',
            0, 1, 2, 1,
        )
        checkbutton3.set_sensitive(False)

        checkbutton4 = self.add_checkbutton(grid4,
            _('Video is archived'),
            'archive_flag',
            0, 2, 1, 1,
        )
        checkbutton4.set_sensitive(False)

        checkbutton5 = self.add_checkbutton(grid4,
            _('Video is bookmarked'),
            'bookmark_flag',
            1, 2, 1, 1,
        )
        checkbutton5.set_sensitive(False)

        checkbutton6 = self.add_checkbutton(grid4,
            _('Video is favourite'),
            'fav_flag',
            0, 3, 1, 1,
        )
        checkbutton6.set_sensitive(False)

        checkbutton7 = self.add_checkbutton(grid4,
            _('Video is in waiting list'),
            'waiting_flag',
            1, 3, 1, 1,
        )
        checkbutton7.set_sensitive(False)

        checkbutton8 = self.add_checkbutton(grid4,
            _('Video is blocked/censored/age-restricted'),
            'block_flag',
            0, 4, 2, 1,
        )
        checkbutton8.set_sensitive(False)

        checkbutton9 = self.add_checkbutton(grid4,
            _('Always simulate download of this video'),
            'dl_sim_flag',
            0, 5, 2, 1,
        )
        checkbutton9.set_sensitive(False)

        label3 = self.add_label(grid4,
            _('Video ID'),
            2, 0, 1, 1,
        )
        label3.set_hexpand(False)

        entry3 = self.add_entry(grid4,
            None,
            3, 0, 1, 1,
        )
        entry3.set_editable(False)
        if self.edit_obj.vid is not None:
            entry3.set_text(self.edit_obj.vid)

        label4 = self.add_label(grid4,
            _('Duration'),
            2, 1, 1, 1,
        )
        label4.set_hexpand(False)

        entry4 = self.add_entry(grid4,
            None,
            3, 1, 1, 1,
        )
        entry4.set_editable(False)
        if self.edit_obj.duration is not None:
            entry4.set_text(
                ttutils.convert_seconds_to_string(self.edit_obj.duration),
            )

        label5 = self.add_label(grid4,
            _('File size'),
            2, 2, 1, 1,
        )
        label5.set_hexpand(False)

        entry5 = self.add_entry(grid4,
            None,
            3, 2, 1, 1,
        )
        entry5.set_editable(False)
        if self.edit_obj.file_size is not None:
            entry5.set_text(self.edit_obj.get_file_size_string())

        label6 = self.add_label(grid4,
            _('Upload time'),
            2, 3, 1, 1,
        )
        label6.set_hexpand(False)

        entry6 = self.add_entry(grid4,
            None,
            3, 3, 1, 1,
        )
        entry6.set_editable(False)
        if self.edit_obj.upload_time is not None:
            entry6.set_text(self.edit_obj.get_upload_time_string())

        label7 = self.add_label(grid4,
            _('Receive time'),
            2, 4, 1, 1,
        )
        label7.set_hexpand(False)

        entry7 = self.add_entry(grid4,
            None,
            3, 4, 1, 1,
        )
        entry7.set_editable(False)
        if self.edit_obj.receive_time is not None:
            entry7.set_text(self.edit_obj.get_receive_time_string())

        label8 = self.add_label(grid4,
            _('Subtitles'),
            2, 5, 1, 1,
        )
        label8.set_hexpand(False)

        entry8 = self.add_entry(grid4,
            None,
            3, 5, 1, 1,
        )
        entry8.set_editable(False)
        entry8.set_text(' '.join(self.edit_obj.subs_list))

        # (Signal connect from above)
        button.connect('clicked', self.on_file_button_clicked)
        button2.connect('clicked', self.on_metadata_button_clicked)


#   def setup_download_options_tab():   # Inherited from GenericConfigWin


    def setup_livestream_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Livestream' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Video properties > Live'
        )

        tab, grid = self.add_notebook_tab(_('_Live'))
        grid_width = 2

        # Livestream properties
        self.add_label(grid,
            '<u>' + _('Livestream properties') + '</u>',
            0, 0, grid_width, 1,
        )

        label = self.add_label(grid,
            _('Livestream status'),
            0, 1, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid,
            None,
            1, 1, 1, 1,
        )
        entry.set_editable(False)
        if self.edit_obj.live_mode == 1:
            entry.set_text(_('Waiting to start'))
        elif self.edit_obj.live_mode == 2:
            entry.set_text(_('Livestream has started'))
        elif self.edit_obj.was_live_flag:
            entry.set_text(_('Livestream has finished'))
        else:
            entry.set_text(_('Not a livestream'))

        label2 = self.add_label(grid,
            _('Livestream message'),
            0, 2, 1, 1,
        )
        label2.set_hexpand(False)

        entry2 = self.add_entry(grid,
            None,
            1, 2, 1, 1,
        )
        entry2.set_text(self.edit_obj.live_msg)
        entry2.set_editable(False)

        checkbutton = Gtk.CheckButton()
        grid.attach(checkbutton, 0, 3, grid_width, 1)
        checkbutton.set_label(
            _('Video is pre-recorded'),
        )
        if self.edit_obj.live_debut_flag:
            checkbutton.set_active(True)
        checkbutton.set_sensitive(False)

        if self.edit_obj.live_mode and not (
            self.edit_obj.parent_obj.dbid \
            in self.app_obj.container_unavailable_dict
        ):
            # Livestream actions
            self.add_label(grid,
                '<u>' + _('Livestream actions') + '</u>',
                0, 4, grid_width, 1,
            )

            checkbutton2 = Gtk.CheckButton()
            grid.attach(checkbutton2, 0, 5, grid_width, 1)
            checkbutton2.set_label(
                _('When the livestream starts, show a desktop notification'),
            )
            if self.edit_obj.dbid in self.app_obj.media_reg_auto_notify_dict:
                checkbutton2.set_active(True)
            checkbutton2.set_sensitive(False)

            checkbutton3 = Gtk.CheckButton()
            grid.attach(checkbutton3, 0, 6, grid_width, 1)
            checkbutton3.set_label(
                _('When the livestream starts, play an alarm'),
            )
            if self.edit_obj.dbid in self.app_obj.media_reg_auto_alarm_dict:
                checkbutton3.set_active(True)
            checkbutton3.set_sensitive(False)

            checkbutton4 = Gtk.CheckButton()
            grid.attach(checkbutton4, 0, 7, grid_width, 1)
            checkbutton4.set_label(
                _(
                'When the livestream starts, open it in the system\'s web' \
                + ' browser',
                ),
            )
            if self.edit_obj.dbid in self.app_obj.media_reg_auto_open_dict:
                checkbutton4.set_active(True)
            checkbutton4.set_sensitive(False)

            checkbutton5 = Gtk.CheckButton()
            grid.attach(checkbutton5, 0, 8, grid_width, 1)
            checkbutton5.set_label(
                _(
                'When the livestream starts, begin downloading it immediately',
                ),
            )
            if self.edit_obj.dbid in self.app_obj.media_reg_auto_dl_start_dict:
                checkbutton5.set_active(True)
            checkbutton5.set_sensitive(False)

            checkbutton6 = Gtk.CheckButton()
            grid.attach(checkbutton6, 0, 9, grid_width, 1)
            checkbutton6.set_label(
                _(
                'When a livestream stops, download it (overwriting any' \
                + ' earlier file)',
                ),
            )
            if self.edit_obj.dbid in self.app_obj.media_reg_auto_dl_stop_dict:
                checkbutton6.set_active(True)
            checkbutton6.set_sensitive(False)


    def setup_descrip_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Description' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Video properties > Description'
        )

        tab, grid = self.add_notebook_tab(_('_Description'))
        grid_width = 2

        # Video description
        self.add_label(grid,
            '<u>' + _('Video description') + '</u>',
            0, 0, grid_width, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            'descrip',
            0, 1, grid_width, 1,
        )
        textview.set_editable(False)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_can_focus(False)

        button = Gtk.Button.new_with_label(
            _('Update from the description file, and set the line length to:'),
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
            None,
            1, 2, 1, 1,
        )
        spinbutton.set_value(self.app_obj.main_win_obj.descrip_line_max_len)

        button2 = Gtk.Button.new_with_label(
            _('Clear the description (does not modify the file)'),
        )
        grid.attach(button2, 0, 3, grid_width, 1)
        # (Signal connect appears below)

        # (Signal connects from above)
        button.connect(
            'clicked',
            self.on_load_descrip_button_clicked,
            spinbutton,
            textbuffer,
        )

        button2.connect(
            'clicked',
            self.on_clear_descrip_button_clicked,
            textbuffer,
        )


    def setup_timestamps_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Timestamps' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Video properties > Timestamps'
        )

        tab, grid = self.add_notebook_tab(_('_Timestamps'))
        grid_width = 4

        # Timestamps
        self.add_label(grid,
            '<u>' + _('Timestamps') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'Timestamps can be used to download or create video clips',
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

        for i, column_title in enumerate(
            [ _('Start'), _('Stop'), _('Clip title') ],
        ):
            renderer_text = Gtk.CellRendererText()
            column_text = Gtk.TreeViewColumn(
                column_title,
                renderer_text,
                text=i,
            )
            treeview.append_column(column_text)
            column_text.set_resizable(True)

        self.timestamp_liststore = Gtk.ListStore(str, str, str)
        treeview.set_model(self.timestamp_liststore)

        # Initialise the list
        self.setup_timestamps_tab_update_treeview()

        # Strip of widgets at the bottom
        label = self.add_label(grid,
            _('Start timestamp (e.g. 15:29)'),
            0, 3, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid,
            None,
            1, 3, 1, 1,
        )
        entry.set_width_chars(12)
        entry.set_hexpand(False)

        label2 = self.add_label(grid,
            _('Stop timestamp (optional)'),
            2, 3, 1, 1,
        )
        label2.set_hexpand(False)

        entry2 = self.add_entry(grid,
            None,
            3, 3, 1, 1,
        )
        entry2.set_width_chars(12)
        entry2.set_hexpand(False)

        label3 = self.add_label(grid,
            _('Clip title (optional)'),
            0, 4, 1, 1,
        )
        label3.set_hexpand(False)

        entry3 = self.add_entry(grid,
            None,
            1, 4, 3, 1,
        )
        entry3.set_hexpand(True)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 5, grid_width, 1)

        button = Gtk.Button(_('Add timestamp'))
        grid2.attach(button, 0, 0, 1, 1)
        button.set_hexpand(True)
        button.connect(
            'clicked',
            self.on_add_stamp_button_clicked,
            entry,
            entry2,
            entry3,
        )

        button2 = Gtk.Button(_('Delete timestamp'))
        grid2.attach(button2, 1, 0, 1, 1)
        button2.set_hexpand(True)
        button2.connect(
            'clicked',
            self.on_delete_stamp_button_clicked,
            treeview,
        )

        button3 = Gtk.Button(_('Clip preferences'))
        grid2.attach(button3, 2, 0, 1, 1)
        button3.set_hexpand(True)
        button3.connect(
            'clicked',
            self.on_clip_prefs_clicked,
        )

        button4 = Gtk.Button(_('Clear list'))
        grid2.attach(button4, 3, 0, 1, 1)
        button4.set_hexpand(True)
        button4.connect(
            'clicked',
            self.on_clear_stamp_button_clicked,
        )

        button5 = Gtk.Button(_('Reset list using copied text'))
        grid2.attach(button5, 0, 1, 2, 1)
        button5.set_hexpand(True)
        button5.connect(
            'clicked',
            self.on_copy_stamp_button_clicked,
        )

        button6 = Gtk.Button(_('Reset list using video description'))
        grid2.attach(button6, 2, 1, 2, 1)
        button6.set_hexpand(True)
        button6.connect(
            'clicked',
            self.on_extract_stamp_button_clicked,
        )


    def setup_timestamps_tab_update_treeview(self):

        """ Called by self.setup_timestamps_tab().

        Fills or updates the treeview.
        """

        self.timestamp_liststore.clear()

        # Add each timestamp/title to the treeview, one row at a time
        for mini_list in self.edit_obj.stamp_list:

            start_stamp = mini_list[0]

            if mini_list[1] is None:
                stop_stamp = ''
            else:
                stop_stamp = mini_list[1]

            if mini_list[2] is None:
                clip_title = ''
            else:
                clip_title = mini_list[2]

            self.timestamp_liststore.append(
                [ start_stamp, stop_stamp, clip_title ],
            )


    def setup_slices_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Slices' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Video properties > Slices'
        )

        tab, grid = self.add_notebook_tab(_('_Slices'))
        grid_width = 4

        # Video slices
        self.add_label(grid,
            '<u>' + _('Video slices') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'SponsorBlock provides a list of slices that can be' \
                + ' removed from a video',
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

        for i, column_title in enumerate(
            [ _('Category'), _('Action type'), _('Start'), _('Stop') ],
        ):
            renderer_text = Gtk.CellRendererText()
            column_text = Gtk.TreeViewColumn(
                column_title,
                renderer_text,
                text=i,
            )
            treeview.append_column(column_text)
            column_text.set_resizable(True)

        self.slice_liststore = Gtk.ListStore(str, str, str, str)
        treeview.set_model(self.slice_liststore)

        # Initialise the list
        self.setup_slices_tab_update_treeview()

        # Strip of widgets at the bottom
        self.add_label(grid,
            _('Category'),
            0, 3, 1, 1
        )

        combo = self.add_combo(grid,
            formats.SPONSORBLOCK_CATEGORY_LIST,
            None,
            1, 3, 1, 1,
        )
        combo.set_active(0)

        self.add_label(grid,
            _('Action type'),
            2, 3, 1, 1
        )

        combo2 = self.add_combo(grid,
            formats.SPONSORBLOCK_ACTION_LIST,
            None,
            3, 3, 1, 1,
        )
        combo2.set_active(0)

        label = self.add_label(grid,
            _('Start (timestamp or seconds)'),
            0, 4, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid,
            None,
            1, 4, 1, 1,
        )
        entry.set_hexpand(False)

        label2 = self.add_label(grid,
            _('Stop (optional)'),
            2, 4, 1, 1,
        )
        label2.set_hexpand(False)

        entry2 = self.add_entry(grid,
            None,
            3, 4, 1, 1,
        )
        entry2.set_hexpand(False)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 5, grid_width, 1)

        button = Gtk.Button(_('Add slice'))
        grid2.attach(button, 0, 0, 1, 1)
        button.set_hexpand(True)
        button.connect(
            'clicked',
            self.on_add_slice_button_clicked,
            combo,
            combo2,
            entry,
            entry2,
        )

        button2 = Gtk.Button(_('Delete slice'))
        grid2.attach(button2, 1, 0, 1, 1)
        button2.set_hexpand(True)
        button2.connect(
            'clicked',
            self.on_delete_slice_button_clicked,
            treeview,
        )

        button3 = Gtk.Button(_('SponsorBlock settings'))
        grid2.attach(button3, 2, 0, 1, 1)
        button3.set_hexpand(True)
        button3.connect(
            'clicked',
            self.on_block_prefs_clicked,
        )

        button4 = Gtk.Button(_('Clear list'))
        grid2.attach(button4, 3, 0, 1, 1)
        button4.set_hexpand(True)
        button4.connect(
            'clicked',
            self.on_clear_slice_button_clicked,
        )

        button5 = Gtk.Button(_('Contact SponsorBlock to reset list'))
        grid2.attach(button5, 2, 1, 2, 1)
        button5.set_hexpand(True)
        button5.connect(
            'clicked',
            self.on_contact_sblock_clicked,
        )


    def setup_slices_tab_update_treeview(self):

        """ Called by self.setup_slices_tab().

        Fills or updates the treeview.
        """

        self.slice_liststore.clear()

        # Add each slice to the treeview, one row at a time
        for mini_dict in self.edit_obj.slice_list:

            if 'category' in mini_dict:
                category = mini_dict['category']
            else:
                category = 'n/a'

            if 'action' in mini_dict:
                action = mini_dict['action']
            else:
                action = 'n/a'

            if 'start_time' in mini_dict:
                start_time = mini_dict['start_time']
            else:
                start_time = 'n/a'

            if 'stop_time' in mini_dict \
            and mini_dict['stop_time'] is not None:
                stop_time = mini_dict['stop_time']
            else:
                stop_time = 'n/a'

            self.slice_liststore.append(
                [ category, action, str(start_time), str(stop_time) ],
            )


    def setup_comments_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Comments' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Video properties > Comments'
        )

        tab, grid = self.add_notebook_tab(_('_Comments'))
        grid_width = 3

        # Comments (yt-dlp only)
        label = self.add_label(grid,
            '<u>' + _('Comments') + '</u>' + self.ytdlp_only(),
            0, 0, 1, 1,
        )
        label.set_hexpand(True)

        label2 = self.add_label(grid,
            _('Total comments:'),
            1, 0, 1, 1,
        )
        label2.set_hexpand(False)

        entry = self.add_entry(grid,
            None,
            2, 0, 1, 1,
        )
        entry.set_hexpand(False)
        entry.set_max_width_chars(8)
        entry.set_text(str(len(self.edit_obj.comment_list)))

        frame = Gtk.Frame()
        grid.attach(frame, 0, 1, grid_width, 1)

        self.comment_scrolled = Gtk.ScrolledWindow()
        frame.add(self.comment_scrolled)
        self.comment_scrolled.set_vexpand(True)
        self.comment_scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC,
        )

        # For a flat list, use a Gtk.TreeView. For a formmated list, use a
        #   Gtk.ListBox
        if not self.app_obj.comment_show_formatted_flag:
            self.setup_comments_tab_add_treeview()
        else:
            self.setup_comments_tab_add_listbox()

        # (The list is initialised below)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 2, grid_width, 1)

        # Editing widgets
        checkbutton = self.add_checkbutton(grid2,
            _('Show formatted list'),
            None,
            0, 0, 1, 1,
        )
        checkbutton.set_hexpand(False)
        if self.app_obj.comment_show_formatted_flag:
            checkbutton.set_active(True)
        checkbutton.connect('toggled', self.on_format_checkbutton_toggled)

        radiobutton = self.add_radiobutton(grid2,
            None,
            _('Show comment times as text'),
            None,
            None,
            1, 0, 1, 1,
        )
        radiobutton.set_hexpand(False)
        # (Signal connect appears below)

        radiobutton2 = self.add_radiobutton(grid2,
            radiobutton,
            _('Show comment timestamps'),
            None,
            None,
            2, 0, 1, 1,
        )
        radiobutton2.set_hexpand(False)
        if not self.app_obj.comment_show_text_time_flag:
            radiobutton2.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        radiobutton.connect(
            'toggled',
            self.on_time_radiobutton_toggled,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid3 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

        label3 = self.add_label(grid3,
            _('Filter'),
            0, 0, 1, 1,
        )
        label3.set_hexpand(False)

        self.filter_entry = self.add_entry(grid3,
            None,
            1, 0, 1, 1,
        )
        self.filter_entry.set_hexpand(False)
        self.filter_entry.set_tooltip_text(_('Enter search text'))
        self.filter_entry.set_width_chars(16)

        self.filter_togglebutton = Gtk.ToggleButton.new_with_label(_('Regex'))
        grid3.attach(self.filter_togglebutton, 2, 0, 1, 1)

        self.filter_author_checkbutton = self.add_checkbutton(grid3,
            _('Author'),
            None,
            3, 0, 1, 1,
        )
        self.filter_author_checkbutton.set_hexpand(False)

        self.filter_comment_checkbutton = self.add_checkbutton(grid3,
            _('Comment'),
            None,
            4, 0, 1, 1,
        )
        self.filter_comment_checkbutton.set_hexpand(False)
        self.filter_comment_checkbutton.set_active(True)

        self.filter_uploader_checkbutton = self.add_checkbutton(grid3,
            _('Uploader'),
            None,
            5, 0, 1, 1,
        )
        self.filter_uploader_checkbutton.set_hexpand(False)

        if not self.app_obj.show_custom_icons_flag:
            self.filter_apply_button = Gtk.ToolButton.new_from_stock(
                Gtk.STOCK_FIND,
            )
        else:
            self.filter_apply_button = Gtk.ToolButton.new()
            self.filter_apply_button.set_icon_widget(
                Gtk.Image.new_from_pixbuf(
                    self.app_obj.main_win_obj.pixbuf_dict['stock_find'],
                ),
            )
        grid3.attach(self.filter_apply_button, 6, 0, 1, 1)
        self.filter_apply_button.connect(
            'clicked',
            self.on_apply_filter_button_clicked,
        )

        if not self.app_obj.show_custom_icons_flag:
            self.filter_cancel_button = Gtk.ToolButton.new_from_stock(
                Gtk.STOCK_CANCEL,
            )
        else:
            self.filter_cancel_button = Gtk.ToolButton.new()
            self.filter_cancel_button.set_icon_widget(
                Gtk.Image.new_from_pixbuf(
                    self.app_obj.main_win_obj.pixbuf_dict['stock_cancel'],
                ),
            )
        grid3.attach(self.filter_cancel_button, 7, 0, 1, 1)
        self.filter_cancel_button.set_sensitive(False)
        self.filter_cancel_button.connect(
            'clicked',
            self.on_cancel_filter_button_clicked,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid4 = self.add_secondary_grid(grid, 0, 4, grid_width, 1)

        button = Gtk.Button.new_with_label(
            _('Update from the metadata file'),
        )
        grid4.attach(button, 0, 0, 1, 1)
        button.set_hexpand(True)
        button.connect(
            'clicked',
            self.on_load_comments_button_clicked,
        )
        # (The call to .check_actual_path_by_ext() requires a value of
        #   media.Video.file_name that is not None)
        if self.edit_obj.file_name is None \
        or self.edit_obj.file_ext is None:
            button.set_sensitive(False)
        else:
            json_path = self.edit_obj.check_actual_path_by_ext(
                self.app_obj,
                '.info.json',
            )
            if json_path is None:
                button.set_sensitive(False)

        button2 = Gtk.Button.new_with_label(
            _('Clear comments (does not modify the file)'),
        )
        grid4.attach(button2, 1, 0, 1, 1)
        button2.set_hexpand(True)
        button2.connect(
            'clicked',
            self.on_clear_comments_button_clicked,
        )

        # Initialise the list
        self.setup_comments_tab_update_list()


    def setup_comments_tab_add_treeview(self):

        """Called by self.setup_comments_tab().

        For a flat list, we use a Gtk.TreeView.
        """

        # (This treeview replaces the old treeview or Gtk.ListBox)
        self.setup_comments_tab_remove_child()

        self.comment_treeview = Gtk.TreeView()
        self.comment_scrolled.add(self.comment_treeview)
        self.comment_treeview.set_headers_visible(True)

        for i, column_title in enumerate(
            [
                _('Time'), _('Author'), _('Comment'), _('Likes'),
                _('Favourite'), _('Uploader'), '',
            ],
        ):
            if i < 4:
                renderer_text = Gtk.CellRendererText()
                column_text = Gtk.TreeViewColumn(
                    column_title,
                    renderer_text,
                    text=i,
                )
                self.comment_treeview.append_column(column_text)
                column_text.set_resizable(True)
                # (Employ a twin strategy to cope with spam: split long values
                #   into multiple lines, and limit the (default) column size)
                if i == 1:
                    column_text.set_min_width(100)
                    column_text.set_max_width(200)
                elif i == 2:
                    column_text.set_min_width(100)
                else:
                    column_text.set_min_width(50)
            elif i < 6:
                renderer_toggle = Gtk.CellRendererToggle()
                column_toggle = Gtk.TreeViewColumn(
                    column_title,
                    renderer_toggle,
                    active=i,
                )
                self.comment_treeview.append_column(column_toggle)
                column_toggle.set_resizable(False)
                column_toggle.set_min_width(50)
            else:
                # (Prevent the 'Uploader' column expanding to fill available
                #   space, especially when the window is maximised)
                renderer_text = Gtk.CellRendererText()
                column_text = Gtk.TreeViewColumn(
                    column_title,
                    renderer_text,
                    text=i,
                )
                self.comment_treeview.append_column(column_text)
                column_text.set_resizable(False)

        self.comment_liststore = Gtk.ListStore(
            str, str, str, str, bool, bool,
        )
        self.comment_treeview.set_model(self.comment_liststore)


    def setup_comments_tab_add_listbox(self):

        """Called by self.setup_comments_tab().

        For a formatted list, we use a Gtk.ListBox.
        """

        # (This listbox replaces the old treeview or Gtk.ListBox)
        self.setup_comments_tab_remove_child()

        self.comment_listbox = Gtk.ListBox()
        self.comment_scrolled.add(self.comment_listbox)
        self.comment_listbox.set_can_focus(False)
        self.comment_listbox.set_vexpand(True)


    def setup_comments_tab_remove_child(self):

        """Called by self.setup_comments_tab_add_treeview() and
        self.setup_comments_tab_add_listbox().

        Removes the containing Gtk.Frame's textview or listbox, before adding
        a new child widget.
        """

        if self.comment_treeview is not None:
            self.comment_scrolled.remove(self.comment_treeview)
            self.comment_treeview = None
            self.comment_liststore = None
        elif self.comment_listbox is not None:
            self.comment_scrolled.remove(self.comment_listbox)
            self.comment_listbox = None


    def setup_comments_tab_update_list(self):

        """Can be called by anything.

        Fills or updates either the treeview or the listbox, whichever is
        visible at the moment.
        """

        if self.comment_treeview is not None:
            self.setup_comments_tab_update_treeview()
        else:
            self.setup_comments_tab_update_listbox()

        # (The Gtk.ListBox won't appear filled without this line)
        self.show_all()


    def setup_comments_tab_update_treeview(self):

        """ Called by self.setup_comments_tab().

        Fills or updates the treeview.
        """

        self.comment_liststore.clear()

        shorter = 30
        longer = 80

        # Set up filtering
        filter_dict = {
            'search_text': self.filter_entry.get_text(),
            'lower_text': self.filter_entry.get_text().lower(),
            'regex_flag': self.filter_togglebutton.get_active(),
            'author_flag': self.filter_author_checkbutton.get_active(),
            'comment_flag': self.filter_comment_checkbutton.get_active(),
            'uploader_flag': self.filter_uploader_checkbutton.get_active(),
        }

        # Add each comment to the treeview, one row at a time
        # (Employ a twin strategy to cope with spam: split long values into
        #   multiple lines, and limit the (default) column size)
        longest = 0
        for mini_dict in self.edit_obj.comment_list:

            if not self.setup_comments_tab_check_filter(
                mini_dict,
                filter_dict,
            ):
                continue

            # (The keys 'id' and 'text' are compulsory)
            if not self.app_obj.comment_show_text_time_flag \
            and 'timestamp' in mini_dict:
                ts = datetime.datetime.fromtimestamp(mini_dict['timestamp'])
                ts.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
                time = ts.strftime('%Y-%m-%d %H:%M:%S')

            elif self.app_obj.comment_show_text_time_flag \
            and 'time' in mini_dict:
                time = mini_dict['time']

            else:
                time = 'n/a'

            if 'author' in mini_dict:
                author = mini_dict['author']
            else:
                author = 'n/a'

            if 'likes' in mini_dict:
                likes = mini_dict['likes']
            else:
                likes = '0'

            if 'fav_flag' in mini_dict:
                fav_flag = mini_dict['fav_flag']
            else:
                fav_flag = False

            if 'ul_flag' in mini_dict:
                ul_flag = mini_dict['ul_flag']
            else:
                ul_flag = False

            self.comment_liststore.append([
                time,
                ttutils.shorten_string(author, shorter),
                ttutils.tidy_up_long_string(mini_dict['text'], longer),
                str(likes),
                fav_flag,
                ul_flag,
            ])


    def setup_comments_tab_update_listbox(self):

        """ Called by self.setup_comments_tab().

        Fills or updates the listbox.
        """

        for child in self.comment_listbox.get_children():
            self.comment_listbox.remove(child)

        shorter = 30
        longer = 80
        # Import the main window (for convenience)
        main_win_obj = self.app_obj.main_win_obj

        # The media.Video object's .comment_list is a flat list. Compile a
        #   dictionary, so we can find each commment's parents
        check_dict = {}
        for mini_dict in self.edit_obj.comment_list:
            check_dict[mini_dict['id']] = mini_dict

        # Set up filtering
        filter_dict = {
            'search_text': self.filter_entry.get_text(),
            'lower_text': self.filter_entry.get_text().lower(),
            'regex_flag': self.filter_togglebutton.get_active(),
            'author_flag': self.filter_author_checkbutton.get_active(),
            'comment_flag': self.filter_comment_checkbutton.get_active(),
            'uploader_flag': self.filter_uploader_checkbutton.get_active(),
        }

        # Add each comment to the listbox, one row at a time
        for mini_dict in self.edit_obj.comment_list:

            if not self.setup_comments_tab_check_filter(
                mini_dict,
                filter_dict,
            ):
                continue

            row = Gtk.ListBoxRow()

            hbox = Gtk.HBox()
            row.add(hbox)
            # (self.spacing_size is a little too big)
            hbox.set_border_width(3)

            # Indent the comment, depending on how many parents this comment
            #   has
            # The indentation is applied by adding a Gtk.Label of the right
            #   length, up to a sensible maximum
            # (Don't indent comments when the filter is applied)
            if not self.filter_cancel_button.get_sensitive():
                count = 0
                this_dict = mini_dict
                while count <= 8 and this_dict['parent'] is not None:
                    this_dict = check_dict[this_dict['parent']]
                    count += 1

                if count:
                    label = Gtk.Label.new()
                    hbox.pack_start(label, False, False, 0)
                    label.set_text('        ' * count)

            box = Gtk.Box()
            hbox.add(box)

            vbox = Gtk.VBox()
            box.add(vbox)

            hbox2 = Gtk.HBox()
            vbox.pack_start(hbox2, False, False, 0)

            if 'ul_flag' in mini_dict and mini_dict['ul_flag'] is True:
                image = Gtk.Image.new_from_pixbuf(
                    main_win_obj.pixbuf_dict['uploader_small'],
                )
                hbox2.pack_start(image, False, False, 0)

            if 'author' in mini_dict:
                msg = '<b>' \
                + html.escape(
                    ttutils.shorten_string(mini_dict['author'], shorter),
                    quote=False,
                ) + '</b>'
            else:
                msg = '<b>Anonymous</b>'

            if not self.app_obj.comment_show_text_time_flag \
            and 'timestamp' in mini_dict:
                ts = datetime.datetime.fromtimestamp(mini_dict['timestamp'])
                ts.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
                time = ts.strftime('%Y-%m-%d %H:%M:%S')

            elif self.app_obj.comment_show_text_time_flag \
            and 'time' in mini_dict:
                time = mini_dict['time']

            else:
                time = 'Unknown time'

            msg += ' <i>' + time + '</i>'

            label2 = Gtk.Label()
            hbox2.pack_start(label2, False, False, 0)
            label2.set_markup(msg)
            label2.set_alignment(0, 0.5)

            if 'likes' in mini_dict and mini_dict['likes'] != 0:
                image = Gtk.Image.new_from_pixbuf(
                    main_win_obj.pixbuf_dict['likes_small'],
                )
                hbox2.pack_start(image, False, False, self.spacing_size)

                label3 = Gtk.Label()
                hbox2.pack_start(label3, False, False, 0)
                label3.set_text(str(mini_dict['likes']))
                label3.set_alignment(0, 0.5)

            if 'fav_flag' in mini_dict and mini_dict['fav_flag'] is True:
                image = Gtk.Image.new_from_pixbuf(
                    main_win_obj.pixbuf_dict['favourite_small'],
                )
                hbox2.pack_start(image, False, False, self.spacing_size)

            hbox3 = Gtk.HBox()
            vbox.pack_start(hbox3, False, False, 0)

            label4 = Gtk.Label()
            hbox3.pack_start(label4, False, False, 0)
            label4.set_text(
                html.escape(
                    ttutils.tidy_up_long_string(mini_dict['text'], longer),
                    quote=False
                    ,
                ),
            )
            label4.set_alignment(0, 0.5)

            self.comment_listbox.add(row)


    def setup_comments_tab_check_filter(self, comment_dict, filter_dict):

        """Called by self.setup_comments_tab_update_treeview() and
        self.setup_comments_tab_update_listbox().

        Checks each comment against the filter, if it is active.

        Args:

            comment_dict (dict): An item in media.Video.comment_list,
                supplying details about a single comment associated with this
                window's video

            filter_dict (dict): Summary of the state of widgets on this tab,
                supplying the keys 'search_text', 'lower_text', 'regex_flag',
                'author_flag', 'comment_flag', 'uploader_flag'

        Return values:

            True to display the comment, False to filter it out

        """

        comment = comment_dict['text']

        if not filter_dict['regex_flag']:

            if (
                filter_dict['author_flag'] \
                and comment_dict['author'].lower().find(
                    filter_dict['lower_text']
                ) > -1
            ) or (
                filter_dict['comment_flag'] \
                and comment_dict['text'].lower().find(
                    filter_dict['lower_text']
                ) > -1
            ) or (
                filter_dict['uploader_flag'] \
                and comment_dict['ul_flag']
            ):
                return True

        else:

            if (
                filter_dict['author_flag'] \
                and re.search(
                    filter_dict['search_text'],
                    comment_dict['author'],
                    re.IGNORECASE,
                )
            ) or (
                filter_dict['comment_flag'] \
                and re.search(
                    filter_dict['search_text'],
                    comment_dict['text'],
                    re.IGNORECASE
                )
            ) or (
                filter_dict['uploader_flag'] \
                and comment_dict['ul_flag']
            ):
                return True

        # No match
        return False


    def setup_errors_warnings_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Errors / Warnings' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Video properties > Errors / Warnings'
        )

        tab, grid = self.add_notebook_tab(_('_Errors / Warnings'))

        # Errors / Warnings
        self.add_label(grid,
            '<u>' + _('Errors / Warnings') + '</u>',
            0, 0, 1, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'Error messages produced the last time this video was' \
                + ' checked/downloaded',
            ) + '</i>',
            0, 1, 1, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            'error_list',
            0, 2, 1, 1,
        )
        textview.set_editable(False)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_can_focus(False)

        self.add_label(grid,
            '<i>' + _(
                'Warning messages produced the last time this video was' \
                + ' checked/downloaded',
            ) + '</i>',
            0, 3, 1, 1,
        )

        textview2, textbuffer2 = self.add_textview(grid,
            'warning_list',
            0, 4, 1, 1,
        )
        textview2.set_editable(False)
        textview2.set_wrap_mode(Gtk.WrapMode.WORD)
        textview2.set_can_focus(False)


    # Callback class methods


#   def on_button_apply_options_clicked():  # Inherited from GenericConfigWin


#   def on_button_edit_options_clicked():   # Inherited from GenericConfigWin


#   def on_button_remove_options_clicked(): # Inherited from GenericConfigWin


    def on_add_slice_button_clicked(self, button, combo, combo2, entry, \
    entry2):

        """Called from a callback in self.setup_slicess_tab().

        Adds a new slice to the video's slice list.

        Args:

            button (Gtk.Button): The widget clicked

            combo, combo2 (Gtk.Entry): Other widgets to modify

            entry, entry2 (Gtk.Entry): Other widgets to modify

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Video properties > Slices'
        )

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        category = model[tree_iter][0]

        tree_iter2 = combo2.get_active_iter()
        model2 = combo2.get_model()
        action_type = model2[tree_iter2][0]

        start_time = ttutils.strip_whitespace(entry.get_text())
        stop_time = ttutils.strip_whitespace(entry2.get_text())

        start_time = float(
            ttutils.timestamp_convert_to_seconds(self.app_obj, start_time),
        )

        if stop_time == '':
            stop_time = None
        else:
            stop_time = float(
                ttutils.timestamp_convert_to_seconds(self.app_obj, stop_time),
            )

        # Do nothing if specified timestamps aren't valid
        try:
            ignore = float(start_time)
            if stop_time is not None:
                ignore = float(stop_time)

        except:
            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Invalid start/stop times'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        if stop_time is not None and stop_time <= start_time:
            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Invalid start/stop times'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        # Compile the mini-dictionary in the format returned by SponsorBlock
        mini_dict = {
            'category': category,
            'action': action_type,
            'start_time': start_time,
            'stop_time': stop_time,
            'duration': 0,
        }

        # Add it to the list
        slice_list = self.retrieve_val('slice_list')
        slice_list.append(mini_dict)

        # (The called function will sort the list)
        self.edit_obj.set_slices(slice_list)

        # (Show changes, and empty entry boxes)
        self.setup_slices_tab_update_treeview()
        entry.set_text('')
        entry2.set_text('')


    def on_add_stamp_button_clicked(self, button, entry, entry2, entry3):

        """Called from a callback in self.setup_timestamps_tab().

        Adds a new timestamp to video's timestamp list, optionally with a
        clip title.

        Args:

            button (Gtk.Button): The widget clicked

            entry, entry2, entry3 (Gtk.Entry): Other widgets to modify

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Video properties > Timestamps'
        )

        start_stamp = ttutils.strip_whitespace(entry.get_text())
        stop_stamp = ttutils.strip_whitespace(entry2.get_text())
        clip_title = ttutils.strip_whitespace(entry3.get_text())

        # (Values are stored as None, rather than empty strings)
        if stop_stamp == '':
            stop_stamp = None

        if clip_title == '':
            clip_title = None

        # Do nothing if specified timestamps aren't valid ('stop_stamp' is
        #   optional)
        regex = '^' + self.app_obj.timestamp_regex + '$'
        if re.search(regex, start_stamp) \
        and (stop_stamp is None or re.search(regex, stop_stamp)) \
        and ttutils.timestamp_compare(self.app_obj, start_stamp, stop_stamp):

            # Add leading zeroes to the minutes and seconds components, so
            #   that .stamp_list gets sorted correctly (and doesn't look
            #   weird)
            start_stamp = ttutils.timestamp_format(self.app_obj, start_stamp)
            if stop_stamp is not None:
                stop_stamp = ttutils.timestamp_format(self.app_obj, stop_stamp)

            # Timestamps stored in groups of three, in the form
            #   (start_stamp, stop_stamp, clip_title)
            # If a group with the same 'start_stamp' timestamp already exists,
            #   don't replace it; allow duplicates (as the user may actually
            #   want that)
            stamp_list = self.retrieve_val('stamp_list')
            stamp_list.append([ start_stamp, stop_stamp, clip_title ])

            # (The called function will sort the list)
            self.edit_obj.set_timestamps(stamp_list)

            # (Show changes, and empty entry boxes. The 'stop' timestamp, if
            #   specified, becomes the 'start' timestamp for the next group)
            self.setup_timestamps_tab_update_treeview()

            if stop_stamp is None:
                entry.set_text('')
            else:
                entry.set_text(
                    ttutils.timestamp_add_second(self.app_obj, stop_stamp),
                )

            entry2.set_text('')
            entry3.set_text('')

        else:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Invalid timestamp(s)'),
                'error',
                'ok',
                self,           # Parent window is this window
            )


    def on_apply_filter_button_clicked(self, button):

        """Called from a callback in self.setup_comments_tab().

        Filters the list of comments to those matching the search text.

        Args:

            button (Gtk.Button): The widget clicked

        """

        if not self.filter_author_checkbutton.get_active() \
        and not self.filter_comment_checkbutton.get_active() \
        and not self.filter_uploader_checkbutton.get_active():
            self.filter_entry.set_text('')
            self.filter_cancel_button.set_sensitive(False)
        elif self.filter_entry.get_text() == '':
            self.filter_cancel_button.set_sensitive(False)
        else:
            self.filter_cancel_button.set_sensitive(True)

        self.setup_comments_tab_update_list()


    def on_block_prefs_clicked(self, button):

        """Called from a callback in self.setup_slices_tab().

        Opens the preferences window to show (Sponsor)Block settings.

        Args:

            button (Gtk.Button): The widget clicked

        """

        SystemPrefWin(self.app_obj, 'slices')


    def on_cancel_filter_button_clicked(self, button):

        """Called from a callback in self.setup_comments_tab().

        Cancels the filter for comments.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.filter_entry.set_text('')
        self.filter_cancel_button.set_sensitive(False)
        self.setup_comments_tab_update_list()


    def on_clear_comments_button_clicked(self, button):

        """Called from a callback in self.setup_descrip_tab().

        Clears the video's .comment_list IV (but doesn't modify the
        .info.json file itself).

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.edit_obj.reset_comments()
        self.setup_comments_tab_update_list()


    def on_clear_descrip_button_clicked(self, button, textbuffer):

        """Called from a callback in self.setup_descrip_tab().

        Clears the video's .descrip IV (but doesn't modify the .description
        file itself).

        Args:

            button (Gtk.Button): The widget clicked

            textbuffer (Gtk.TextBuffer): The textview's textbuffer

        """

        self.edit_obj.reset_video_descrip()
        textbuffer.set_text('')


    def on_clear_slice_button_clicked(self, button):

        """Called from a callback in self.setup_slices_tab().

        Empties the video's slice list.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.edit_obj.reset_slices()
        self.setup_slices_tab_update_treeview()


    def on_clear_stamp_button_clicked(self, button):

        """Called from a callback in self.setup_timestamps_tab().

        Empties the video's timestamp list.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.edit_obj.reset_timestamps()
        self.setup_timestamps_tab_update_treeview()


    def on_clip_prefs_clicked(self, button):

        """Called from a callback in self.setup_timestamps_tab().

        Opens the preferences window to show clip settings.

        Args:

            button (Gtk.Button): The widget clicked

        """

        SystemPrefWin(self.app_obj, 'clips')


    def on_contact_sblock_clicked(self, button):

        """Called from a callback in self.setup_slices_tab().

        Contacts SponsorBlock to reset the video's slice list.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ttutils.fetch_slice_data(
            self.app_obj,
            self.edit_obj,
        )

        self.setup_slices_tab_update_treeview()


    def on_copy_stamp_button_clicked(self, button):

        """Called from a callback in self.setup_timestamps_tab().

        Updates the video's timestamp list using text the user has copied and
        pasted into a dialogue window.

        Args:

            button (Gtk.Button): The widget clicked

        """

        # Open the dialogue window
        dialogue_win = mainwin.AddStampDialogue(
            self,
            self.app_obj.main_win_obj,
        )
        response = dialogue_win.run()

        # Retrieve user choices from the dialogue window
        if response == Gtk.ResponseType.OK:

            text = dialogue_win.textbuffer.get_text(
                dialogue_win.textbuffer.get_start_iter(),
                dialogue_win.textbuffer.get_end_iter(),
                # Don't include hidden characters
                False,
            )

            # (Do not modify the existing list of timestampes, if no text was
            #   added to the dialogue window)
            if text != '':
                self.edit_obj.extract_timestamps_from_descrip(
                    self.app_obj,
                    text,
                )

                self.setup_timestamps_tab_update_treeview()

        # ...before destroying the dialogue window
        dialogue_win.destroy()


    def on_delete_slice_button_clicked(self, button, treeview):

        """Called from a callback in self.setup_slices_tab().

        Deletes the selected slice from the video's slice list.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeVies): The treeview displaying the slice list

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:

            return

        category = model[this_iter][0]
        action_type = model[this_iter][1]
        start_time = float(model[this_iter][2])
        stop_time = float(model[this_iter][3])

        # Slices are stored as a list of mini-dictionaries, in the form
        #   described by self.on_add_slice_button_clicked()
        # Walk the list, and delete the first matching mini-dictionary
        slice_list = self.retrieve_val('slice_list')
        mod_list = []
        match_flag = False

        for mini_dict in slice_list:

            if not match_flag \
            and mini_dict['category'] == category \
            and mini_dict['action'] == action_type \
            and mini_dict['start_time'] == start_time \
            and mini_dict['stop_time'] == stop_time:
                match_flag = True   # Delete this one
            else:
                mod_list.append(mini_dict)

        # (The called function will sort the list)
        self.edit_obj.set_slices(mod_list)

        # (Show changes)
        self.setup_slices_tab_update_treeview()


    def on_delete_stamp_button_clicked(self, button, treeview):

        """Called from a callback in self.setup_timestamps_tab().

        Deletes the selected timestamp(s) from the video's timestamp list.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeVies): The treeview displaying the timestamp list

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:
            return

        start_stamp = model[this_iter][0]
        stop_stamp = model[this_iter][1]
        clip_title = model[this_iter][2]

        # Timestamps stored in groups of three, in the form
        #   (start_stamp, stop_stamp, clip_title)
        # Walk the list, and delete the first matchng group
        stamp_list = self.retrieve_val('stamp_list')
        mod_list = []
        match_flag = False

        for mini_list in stamp_list:

            if not match_flag \
            and mini_list[0] == start_stamp \
            and (mini_list[1] is None or mini_list[1] == stop_stamp) \
            and (mini_list[2] is None or mini_list[2] == clip_title):
                match_flag = True   # Delete this one
            else:
                mod_list.append(mini_list)

        # (The called function will sort the list)
        self.edit_obj.set_timestamps(mod_list)

        # (Show changes)
        self.setup_timestamps_tab_update_treeview()


    def on_extract_stamp_button_clicked(self, button):

        """Called from a callback in self.setup_timestamps_tab().

        Updates the video's timestamp list from its description, then displays
        that list in the treeview.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.edit_obj.extract_timestamps_from_descrip(self.app_obj)
        self.setup_timestamps_tab_update_treeview()


    def on_file_button_clicked(self, button):

        """Called from a callback in self.setup_general_tab().

        Prompts the user to choose a new video/audio file. If a valid one is
        selected, update the media.Video object to use it

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Video properties > General'
        )

        # Prompt the user for a new file
        dialogue_win = self.app_obj.dialogue_manager_obj.show_file_chooser(
            _('Select the correct video/audio file'),
            self,
            'open',
        )

        if self.edit_obj.file_name is not None:
            old_path = self.edit_obj.get_actual_path(self.app_obj)
            old_dir, old_name = os.path.split(old_path)
            dialogue_win.set_current_folder(old_dir)

        # Get the user's response
        response = dialogue_win.run()
        if response == Gtk.ResponseType.OK:
            new_path = os.path.abspath(dialogue_win.get_filename())

        dialogue_win.destroy()
        if response == Gtk.ResponseType.OK:

            # The user must not set a video that's in a different directory
            file_dir, file_name = os.path.split(new_path)
            parent_obj = self.edit_obj.parent_obj
            if file_dir != parent_obj.get_actual_dir(self.app_obj) \
            and file_dir != parent_obj.get_default_dir(self.app_obj):

                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _(
                    'The replacement video/audio file must be in the same' \
                    + ' channel, playlist or folder',
                    ),
                    'error',
                    'ok',
                    self,           # Parent window is this window
                 )

                return

            # The new file must be in a recognised video/audio format
            file_name, file_ext = os.path.splitext(new_path)
            short_ext = file_ext[1:]

            if not short_ext in formats.VIDEO_FORMAT_LIST \
            and not short_ext in formats.AUDIO_FORMAT_LIST:

                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _('You must select a valid video/audio file'),
                    'error',
                    'ok',
                    self,           # Parent window is this window
                )

                return

            # Set the new file path
            self.edit_obj.set_file_from_path(new_path)

            # Extract video statistics from the metadata file
            self.app_obj.update_video_from_json(self.edit_obj)

            # Set the new file's size, duration, and so on. The True argument
            #   instructs the function to override existing values
            if self.edit_obj.dl_flag:
                self.app_obj.update_video_from_filesystem(
                    self.edit_obj,
                    new_path,
                    True,
                )

            # If the video exists, then we can mark it as downloaded
            if not self.edit_obj.dl_flag:
                self.app_obj.mark_video_downloaded(self.edit_obj, True)

            # Redraw the video in the Video Catalogue straight away
            GObject.timeout_add(
                0,
                self.app_obj.main_win_obj.video_catalogue_update_video,
                self.edit_obj,
            )

            # Reset this window by abusing the generic code
            self.reset_with_new_edit_obj(self.edit_obj)


    def on_format_checkbutton_toggled(self, checkbutton):

        """Called from callback in self.setup_comments_tab().

        Updates the mainapp.TartubeApp IV, and redraws the treeview.

        Args:

            checkbutton (Gtk.CheckButton): The clicked widget

        """

        if not checkbutton.get_active():
            self.app_obj.set_comment_show_formatted_flag(False)
            self.setup_comments_tab_add_treeview()
        else:
            self.app_obj.set_comment_show_formatted_flag(True)
            self.setup_comments_tab_add_listbox()

        self.setup_comments_tab_update_list()
        self.show_all()


    def on_load_comments_button_clicked(self, button):

        """Called from a callback in self.setup_comments_tab().

        Updates the video's comments from its .info.json file.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.app_obj.update_video_from_json(self.edit_obj, 'comments')
        self.setup_comments_tab_update_list()


    def on_load_descrip_button_clicked(self, button, spinbutton, textbuffer):

        """Called from a callback in self.setup_descrip_tab().

        Updates the video's description from its .description file.

        Args:

            button (Gtk.Button): The widget clicked

            spinbutton (Gtk.SpinButton): Widget setting the maximum line
                length

            textbuffer (Gtk.TextBuffer): The textview's textbuffer

        """

        self.edit_obj.read_video_descrip(
            self.app_obj,
            int(spinbutton.get_value()),
        )

        textbuffer.set_text(self.edit_obj.descrip)


    def on_metadata_button_clicked(self, button):

        """Called from a callback in self.setup_general_tab().

        Prompts the user to choose a new metadata file. If a valid one is
        selected, update the media.Video object to use it

        Args:

            button (Gtk.Button): The widget clicked

        """

        metadata_path = self.edit_obj.get_actual_path_by_ext(
            self.app_obj,
            '.info.json',
        )
        if metadata_path is not None:

            # Extract video statistics from the metadata file
            self.app_obj.update_video_from_json(self.edit_obj)

            # Set the new file's size, duration, and so on. The True argument
            #   instructs the function to override existing values
            if self.edit_obj.dl_flag:
                self.app_obj.update_video_from_filesystem(
                    self.edit_obj,
                    self.edit_obj.get_actual_path(self.app_obj),
                    True,
                )

            # Redraw the video in the Video Catalogue straight away
            GObject.timeout_add(
                0,
                self.app_obj.main_win_obj.video_catalogue_update_video,
                self.edit_obj,
            )

            # Reset this window by abusing the generic code
            self.reset_with_new_edit_obj(self.edit_obj)


    def on_time_radiobutton_toggled(self, radiobutton):

        """Called from callback in self.setup_comments_tab().

        Updates the mainapp.TartubeApp IV, and redraws the treeview.

        Args:

            radiobutton (Gtk.RadioButton): The clicked widget

        """

        if radiobutton.get_active():
            self.app_obj.set_comment_show_text_time_flag(True)
        else:
            self.app_obj.set_comment_show_text_time_flag(False)

        self.setup_comments_tab_update_list()
