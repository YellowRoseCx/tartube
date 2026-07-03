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


class CustomDLEditWin(GenericEditWin):

    """Python class for an 'edit window' to modify values in a
    downloads.CustomDLManager object.

    Args:

        app_obj (mainapp.TartubeApp): The main application object

        edit_obj (downloads.CustomDLManager): The object whose attributes will
            be edited in this window

    """


    # Standard class methods


    def __init__(self, app_obj, edit_obj):

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Custom downloads window starts here.' \
            + ' In the menu, click Edit > System preferences...' \
            + ' > Operations > Custom > Edit'
        )

        Gtk.Window.__init__(self, title=_('Custom download settings'))

        if self.is_duplicate(app_obj, edit_obj):
            return

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # The downloads.CustomDLManager object being edited
        self.edit_obj = edit_obj


        # IV list - Gtk widgets
        # ---------------------
        self.grid = None                        # Gtk.Grid
        self.notebook = None                    # Gtk.Notebook
        self.reset_button = None                # Gtk.Button
        self.apply_button = None                # Gtk.Button
        self.ok_button = None                   # Gtk.Button
        self.cancel_button = None               # Gtk.Button
        # (From self.setup_name_tab)
        self.button = None                      # Gtk.Button
        self.button2 = None                     # Gtk.Button
        self.checkbutton = None                 # Gtk.CheckButton
        self.checkbutton2 = None                # Gtk.CheckButton
        # (From self.setup_subtitles_tab)
        self.checkbutton3 = None                # Gtk.CheckButton
        self.checkbutton4 = None                # Gtk.CheckButton
        self.treeview = None                    # Gtk.TreeView
        self.liststore = None                   # Gtk.ListStore
        self.button3 = None                     # Gtk.Button
        self.treeview2 = None                   # Gtk.TreeView
        self.liststore2 = None                  # Gtk.ListStore
        self.button4 = None                     # Gtk.Button
        # (From self.setup_clips_tab)
        self.checkbutton5 = None                # Gtk.CheckButton
        # (From self.setup_slices_tab)
        self.checkbutton6 = None                # Gtk.CheckButton
        self.liststore3 = None                  # Gtk.ListStore
        self.button5 = None                     # Gkt.Button
        self.button6 = None                     # Gkt.Button
        # (From self.setup_delay_tab)
        self.checkbutton7 = None                # Gtk.CheckButton
        self.spinbutton = None                  # Gtk.SpinButton
        self.spinbutton2 = None                 # Gtk.SpinButton
        # (From self.setup_mirrors_tab)
        self.radiobutton = None                 # Gtk.RadioButton
        self.radiobutton2 = None                # Gtk.RadioButton
        self.radiobutton3 = None                # Gtk.RadioButton
        self.radiobutton4 = None                # Gtk.RadioButton
        # (From self.setup_livestreams_tab)
        self.checkbutton8 = None                # Gtk.CheckButton
        self.checkbutton9 = None                # Gtk.CheckButton
        self.checkbutton10 = None               # Gtk.CheckButton
        self.checkbutton11 = None               # Gtk.CheckButton


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
        self.edit_dict = {}


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

        # Import the main window (for convenience)
        main_win_obj = self.app_obj.main_win_obj

        # Apply any changes the user has made
        for key in self.edit_dict.keys():
            setattr(self.edit_obj, key, self.edit_dict[key])


        # If 'divert_mode' has changed, the Video Catalogue must be redrawn
        if 'divert_mode' in self.edit_dict \
        and self.app_obj.catalogue_mode_type != 'simple' \
        and main_win_obj.video_index_current_dbid is not None:

            main_win_obj.video_catalogue_redraw_all(
                main_win_obj.video_index_current_dbid,
                main_win_obj.catalogue_toolbar_current_page,
            )

        # The changes can now be cleared
        self.edit_dict = {}


#   def retrieve_val():         # Inherited from GenericConfigWin


    # (Setup tabs)


    def setup_tabs(self):

        """Called by self.setup(), .on_button_apply_clicked() and
        .on_button_reset_clicked().

        Sets up the tabs for this edit window.
        """

        self.setup_name_tab()
        self.setup_subtitles_tab()
        self.setup_clips_tab()
        self.setup_slices_tab()
        self.setup_delay_tab()
        self.setup_mirrors_tab()
        self.setup_livestreams_tab()

        # Unusual step - signal connects go here, after all widgets have been
        #   created

        # (From self.setup_name_tab)
        self.button.connect('clicked', self.on_clone_settings_clicked)
        self.button2.connect('clicked', self.on_reset_settings_clicked)
        self.checkbutton.connect(
            'toggled',
            self.on_dl_by_video_button_toggled,
        )
        self.checkbutton2.connect(
            'toggled',
            self.on_dl_precede_button_toggled,
        )

        # (From self.setup_subtitles_tab)
        self.checkbutton3.connect(
            'toggled',
            self.on_dl_if_subs_button_toggled,
        )
        self.button3.connect('clicked', self.on_add_language_clicked)
        self.button4.connect('clicked', self.on_remove_language_clicked)

        # (From self.setup_clips_tab)
        self.checkbutton5.connect(
            'toggled',
            self.on_split_button_toggled,
        )

        # (From self.setup_slices_tab)
        self.checkbutton6.connect(
            'toggled',
            self.on_slice_button_toggled,
        )
        self.button5.connect('clicked', self.on_select_all_button_clicked)
        self.button6.connect('clicked', self.on_unselect_all_button_clicked)

        # (From self.setup_delay_tab)
        self.checkbutton7.connect(
            'toggled',
            self.on_delay_button_toggled,
        )
        self.spinbutton.connect(
            'value-changed',
            self.on_delay_spinbutton_changed,
        )

        # (From self.setup_mirrors_tab)
        self.radiobutton.connect(
            'toggled',
            self.on_divert_button_toggled,
        )
        self.radiobutton2.connect(
            'toggled',
            self.on_divert_button_toggled,
        )
        self.radiobutton3.connect(
            'toggled',
            self.on_divert_button_toggled,
        )
        self.radiobutton4.connect(
            'toggled',
            self.on_divert_button_toggled,
        )

        # (From self.setup_livestreams_tab)
        self.checkbutton8.connect(
            'toggled',
            self.on_ignore_live_button_toggled,
        )
        self.checkbutton9.connect(
            'toggled',
            self.on_ignore_old_live_button_toggled,
        )
        self.checkbutton10.connect(
            'toggled',
            self.on_dl_if_live_button_toggled,
        )
        self.checkbutton11.connect(
            'toggled',
            self.on_dl_if_old_live_button_toggled,
        )


    def setup_name_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Name' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Custom downloads > Name'
        )

        tab, grid = self.add_notebook_tab(_('_Name'))
        grid_width = 4

        label = self.add_label(grid,
            _('Name'),
            0, 0, 2, 1,
        )

        entry = self.add_entry(grid,
            'name',
            2, 0, 1, 1,
        )
        entry.set_hexpand(True)

        entry2 = self.add_entry(grid,
            None,
            3, 0, 1, 1,
        )
        entry2.set_text('#' + str(self.edit_obj.uid))
        entry2.set_hexpand(False)

        label2 = self.add_label(grid,
            _('Usage'),
            0, 1, 2, 1,
        )

        entry3 = self.add_entry(grid,
            None,
            2, 1, 2, 1,
        )
        entry3.set_editable(False)

        if self.edit_obj == self.app_obj.general_custom_dl_obj:
            entry3.set_text(
                _('Applies everywhere except the Classic Mode tab'),
            )
        elif self.edit_obj == self.app_obj.classic_custom_dl_obj:
            entry3.set_text(_('Applies to the Classic Mode tab'))
        else:
            entry3.set_text(_('Applies when selected'))

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 2, grid_width, 1)
        grid_width2 = 3
        grid2.set_vexpand(True)

        # (Empty label for spacing)
        label3 = Gtk.Label()
        grid2.attach(label3, 0, 0, grid_width2, 1)
        label3.set_hexpand(True)

        # (Frame containing text)
        frame = Gtk.Frame()
        grid2.attach(frame, 1, 1, 1, 1)
        frame.set_hexpand(False)

        grid3 = Gtk.Grid()
        frame.add(grid3)
        grid3.set_border_width(self.spacing_size * 2)
        grid3.set_column_spacing(self.spacing_size)
        grid3.set_row_spacing(self.spacing_size)
        grid3.set_hexpand(False)

        self.add_label(grid3,
            '<b>' + _('HINT') + '</b>: ' + _('Enable these settings first!'),
            0, 0, 1, 1,
        )

        self.checkbutton = self.add_checkbutton(grid3,
            _('Download each video independently of its channel or playlist'),
            None,
            0, 1, 1, 1,
        )
        self.checkbutton.set_active(self.edit_obj.dl_by_video_flag)

        self.checkbutton2 = self.add_checkbutton(grid3,
            _(
                'Check channels/playlists/folders before each custom' \
                + ' download (recommended)',
            ),
            None,
            0, 2, 1, 1,
        )
        self.checkbutton2.set_active(self.edit_obj.dl_precede_flag)
        if not self.edit_obj.dl_by_video_flag \
        or (
            self.app_obj.classic_custom_dl_obj is not None \
            and self.app_obj.classic_custom_dl_obj == self.edit_obj
        ):
            self.checkbutton2.set_sensitive(False)

        # (Frame containing text)
        frame2 = Gtk.Frame()
        grid2.attach(frame2, 1, 2, 1, 1)
        frame.set_hexpand(False)

        grid4 = Gtk.Grid()
        frame2.add(grid4)
        grid4.set_border_width(self.spacing_size * 2)
        grid4.set_column_spacing(self.spacing_size)
        grid4.set_row_spacing(self.spacing_size)
        grid4.set_hexpand(False)

        self.add_label(grid4,
            '<b>' + _('HINT') + '</b>: ' + _(
                'The <b>Check all</b> and <b>Download all</b> buttons will' \
                + ' not start a custom download!',
            ),
            0, 0, 1, 1,
        )
        self.add_label(grid4,
            _(
                'Use the main menu, or right-click a video, channel,' \
                + ' playlist or folder!',
            ),
            0, 1, 1, 1,
        )

        # (Strips of widgets at the bottom of the primary grid)
        frame3 = self.add_pixbuf(grid,
            'copy_large',
            0, 3, 1, 1,
        )
        frame3.set_hexpand(False)

        self.button = Gtk.Button(
            _(
                'Import settings from the general custom download into this' \
                + ' window',
            ),
        )
        grid.attach(self.button, 1, 3, (grid_width - 1), 1)
        self.button.set_hexpand(True)
        if self.edit_obj == self.app_obj.general_custom_dl_obj:
            # No point cloning the General Custom Download Manager onto itself
            self.button.set_sensitive(False)

        frame4 = self.add_pixbuf(grid,
            'warning_large',
            0, 4, 1, 1,
        )
        frame4.set_hexpand(False)

        self.button2 = Gtk.Button(
            _('Completely reset all settings to their default values'),
        )
        grid.attach(self.button2, 1, 4, (grid_width - 1), 1)
        self.button2.set_hexpand(True)


    def setup_subtitles_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Subtitles' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Custom downloads > Subtitles'
        )

        tab, grid = self.add_notebook_tab(_('_Subtitles'))
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(False)
        grid_width = 2

        if not self.edit_obj.dl_by_video_flag \
        or not self.edit_obj.dl_precede_flag:
            desens_flag = True
        else:
            desens_flag = False

        # Subtitles settings
        self.add_label(grid,
            '<u>' + _('Subtitles settings') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'Note: this tab downloads videos. To download subtitles, use' \
                + ' the download options windows',
            ) + '</i>',
            0, 1, grid_width, 1,
        )

        self.checkbutton3 = self.add_checkbutton(grid,
            _('Only download videos with available subtitles'),
            None,
            0, 2, grid_width, 1,
        )
        self.checkbutton3.set_active(self.edit_obj.dl_if_subs_flag)
        if desens_flag:
            self.checkbutton3.set_sensitive(False)

        self.checkbutton4 = self.add_checkbutton(grid,
            _(
            'During the custom download, don\'t add videos without subtitles' \
            + ' to the database at all',
            ),
            'ignore_if_no_subs_flag',
            0, 3, grid_width, 1,
        )
        self.checkbutton4.set_active(self.edit_obj.ignore_if_no_subs_flag)
        if desens_flag or not self.edit_obj.dl_if_subs_flag:
            self.checkbutton4.set_sensitive(False)

        self.add_label(grid,
            _(
            'Require subtitles in these languages (leave empty to download' \
            + ' videos with any subtitles):',
            ),
            0, 4, grid_width, 1,
        )

        self.treeview, self.liststore = self.add_treeview(grid,
            0, 5, 1, 1)
        self.treeview.set_vexpand(True)

        for language in formats.LANGUAGE_CODE_LIST:
            self.liststore.append([
                language + ' [' + formats.LANGUAGE_CODE_DICT[language] + ']',
            ])

        self.button3 = Gtk.Button(_('Add language') + ' >>>')
        grid.attach(self.button3, 0, 6, 1, 1)
        if desens_flag or not self.edit_obj.dl_if_subs_flag:
            self.button3.set_sensitive(False)

        self.treeview2, self.liststore2 = self.add_treeview(grid,
            1, 5, 1, 1)
        self.treeview2.set_vexpand(True)

        # Initialise the right-hand treeview
        self.setup_subtitles_tab_redraw_list()

        self.button4 = Gtk.Button('<<< ' + _('Remove language'))
        grid.attach(self.button4, 1, 6, 1, 1)
        if desens_flag or not self.edit_obj.dl_if_subs_flag:
            self.button4.set_sensitive(False)


    def setup_subtitles_tab_redraw_list(self):

        """Called by self.setup_subtitles_tab() and then again by
        self.on_add_languages_clicked() and .on_remove_languages_clicked().

        Update the Gtk.ListStore containing the user's preferred video/audio
        formats.
        """

        # Empty the treeview
        self.liststore2.clear()

        # (Need to reverse formats.LANGUAGE_CODE_DICT for quick lookup)
        rev_dict = {}
        for key in formats.LANGUAGE_CODE_DICT:
            rev_dict[formats.LANGUAGE_CODE_DICT[key]] = key

        # Refill the treeview
        lang_list = self.retrieve_val('dl_if_subs_list')
        for lang_code in lang_list:
            self.liststore2.append([
                rev_dict[lang_code] + ' [' + lang_code + ']',
            ])


    def setup_clips_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Clips' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Custom downloads > Clips'
        )

        tab, grid = self.add_notebook_tab(_('_Clips'))

        # Clip settings
        self.add_label(grid,
            '<u>' + _('Clip settings') + '</u>',
            0, 0, 1, 1,
        )

        self.checkbutton5 = self.add_checkbutton(grid,
            _(
                'Split videos into video clips using timestamps (requires' \
                + ' FFmpeg)',
            ),
            None,
            0, 1, 1, 1,
        )
        self.checkbutton5.set_active(self.edit_obj.split_flag)
        if not self.edit_obj.dl_by_video_flag:
            self.checkbutton5.set_sensitive(False)


    def setup_slices_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Slices' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Custom downloads > Slices'
        )

        tab, grid = self.add_notebook_tab(_('S_lices'))
        grid_width = 2

        # Slice settings
        self.add_label(grid,
            '<u>' + _('Slice settings') + '</u>',
            0, 0, grid_width, 1,
        )

        self.checkbutton6 = self.add_checkbutton(grid,
            _(
                'Remove slices from the video using SponsorBlock data' \
                + ' (requires FFmpeg)'),
            None,
            0, 1, grid_width, 1,
        )
        self.checkbutton6.set_active(self.edit_obj.slice_flag)
        if not self.edit_obj.dl_by_video_flag \
        or self.edit_obj.split_flag:
            self.checkbutton6.set_sensitive(False)

        # (GenericConfigWin.add_treeview() doesn't support multiple columns, so
        #   we'll do everything ourselves)
        frame = Gtk.Frame()
        grid.attach(frame, 0, 2, 1, 8)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_headers_visible(True)

        for i, column_title in enumerate(
            [ _('Remove'), _('Type'), ]
        ):
            if i == 0:
                renderer_toggle = Gtk.CellRendererToggle()
                column_toggle = Gtk.TreeViewColumn(
                    column_title,
                    renderer_toggle,
                    active=i,
                )
                treeview.append_column(column_toggle)
                column_toggle.set_resizable(False)
                renderer_toggle.set_sensitive(True)
                renderer_toggle.set_activatable(True)
                renderer_toggle.connect(
                    'toggled',
                    self.on_treeview_button_toggled,
                )
            else:
                renderer_text = Gtk.CellRendererText()
                column_text = Gtk.TreeViewColumn(
                    column_title,
                    renderer_text,
                    text=i,
                )
                treeview.append_column(column_text)
                column_text.set_resizable(True)

        self.liststore3 = Gtk.ListStore(bool, str)
        treeview.set_model(self.liststore3)

        # Initialise the list
        self.setup_slices_tab_update_treeview()

        # Editing buttons
        self.button5 = Gtk.Button(_('Remove all'))
        grid.attach(self.button5, 1, 2, 1, 1)
        self.button5.set_hexpand(True)
        if not self.edit_obj.slice_flag:
            self.button5.set_sensitive(False)

        self.button6 = Gtk.Button(_('Remove none'))
        grid.attach(self.button6, 1, 3, 1, 1)
        self.button6.set_hexpand(True)
        if not self.edit_obj.slice_flag:
            self.button6.set_sensitive(False)

        # (Empty labels for aesthetics)
        for i in range(8):
            self.add_label(grid,
                '',
                1, (4 + i), 1, 1,
            )


    def setup_slices_tab_update_treeview(self):

        """ Called by self.setup_downloads_tab.

        Fills or updates the treeview.
        """

        self.liststore3.clear()

        slice_dict = self.retrieve_val('slice_dict')
        for category in formats.SPONSORBLOCK_CATEGORY_LIST:

            row_list = []
            if slice_dict[category]:
                row_list.append(True)
            else:
                row_list.append(False)

            row_list.append(category)

            self.liststore3.append(row_list)


    def setup_delay_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Delays' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Custom downloads > Delay'
        )

        tab, grid = self.add_notebook_tab(_('_Delays'))
        grid_width = 2

        # Download delay settings
        self.add_label(grid,
            '<u>' + _('Download delay settings') + '</u>',
            0, 0, grid_width, 1,
        )

        self.checkbutton7 = self.add_checkbutton(grid,
            _('Apply a delay after each video/channel/playlist is downloaded'),
            None,
            0, 1, grid_width, 1,
        )
        self.checkbutton7.set_active(self.edit_obj.delay_flag)

        self.add_label(grid,
            _('Maximum delay to apply (in minutes)'),
            0, 2, 1, 1,
        )

        self.spinbutton = self.add_spinbutton(grid,
            0.2,
            None,
            0.2,                    # Step
            'delay_max',
            1, 2, 1, 1,
        )
        if not self.edit_obj.delay_flag:
            self.spinbutton.set_sensitive(False)

        self.add_label(grid,
            _(
            'Minimum delay to apply (in minutes; randomises the actual delay)'
            ),
            0, 3, 1, 1,
        )

        self.spinbutton2 = self.add_spinbutton(grid,
            0,
            None,
            0.2,                    # Step
            'delay_min',
            1, 3, 1, 1,
        )
        if not self.edit_obj.delay_flag:
            self.spinbutton2.set_sensitive(False)


    def setup_mirrors_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Mirrors' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Custom downloads > Mirrors'
        )

        tab, grid = self.add_notebook_tab(_('_Mirrors'))
        grid_width = 2

        # Mirror settings
        self.add_label(grid,
            '<u>' + _('Mirror settings') + '</u>',
            0, 0, grid_width, 1,
        )

        self.radiobutton = self.add_radiobutton(grid,
            None,
            _('Obtain a YouTube video from the original website'),
            None,
            None,
            0, 1, grid_width, 1,
        )

        self.radiobutton2 = self.add_radiobutton(grid,
            self.radiobutton,
            _('Obtain the video from HookTube rather than YouTube'),
            None,
            None,
            0, 2, grid_width, 1,
        )
        if self.edit_obj.divert_mode == 'hooktube':
            self.radiobutton2.set_active(True)

        self.radiobutton3 = self.add_radiobutton(grid,
            self.radiobutton2,
            _('Obtain the video from Invidious rather than YouTube'),
            None,
            None,
            0, 3, grid_width, 1,
        )
        if self.edit_obj.divert_mode == 'invidious':
            self.radiobutton3.set_active(True)

        self.radiobutton4 = self.add_radiobutton(grid,
            self.radiobutton3,
            _('Obtain the video from this YouTube front-end:'),
            None,
            None,
            0, 4, 1, 1,
        )
        if self.edit_obj.divert_mode == 'other':
            self.radiobutton4.set_active(True)

        self.entry = self.add_entry(grid,
            'divert_website',
            1, 4, 1, 1,
        )
        self.entry.set_hexpand(True)
        if not self.edit_obj.divert_mode == 'other':
            self.entry.set_sensitive(False)

        msg = _('Type the exact text that replaces www.youtube.com e.g.')
        msg = re.sub('www.youtube.com', '   <b>www.youtube.com</b>   ', msg)

        self.add_label(grid,
            '<i>' + msg + '   <b>hooktube.com</b></i>',
            0, 6, grid_width, 1,
        )

        if not self.edit_obj.dl_by_video_flag:
            self.radiobutton.set_sensitive(False)
            self.radiobutton2.set_sensitive(False)
            self.radiobutton3.set_sensitive(False)
            self.radiobutton4.set_sensitive(False)
            self.entry.set_sensitive(False)


    def setup_livestreams_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Livestreams' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Custom downloads > Livestreams'
        )

        tab, grid = self.add_notebook_tab(_('L_ivestreams'))

        # Livestream settings
        self.add_label(grid,
            '<u>' + _('Livestream settings') + '</u>',
            0, 0, 1, 1,
        )

        self.checkbutton8 = self.add_checkbutton(grid,
            _('Don\'t download broadcasting livestreams'),
            None,
            0, 1, 1, 1,
        )
        self.checkbutton8.set_active(self.edit_obj.ignore_stream_flag)
        if not self.edit_obj.dl_by_video_flag:
            self.checkbutton8.set_sensitive(False)

        self.checkbutton9 = self.add_checkbutton(grid,
            _('Don\'t download finished livestreams'),
            None,
            0, 2, 1, 1,
        )
        self.checkbutton9.set_active(self.edit_obj.ignore_old_stream_flag)
        if not self.edit_obj.dl_by_video_flag:
            self.checkbutton9.set_sensitive(False)

        self.checkbutton10 = self.add_checkbutton(grid,
            _('Only download broadcasting livestreams'),
            None,
            0, 3, 1, 1,
        )
        self.checkbutton10.set_active(self.edit_obj.ignore_stream_flag)
        if not self.edit_obj.dl_by_video_flag:
            self.checkbutton10.set_sensitive(False)

        self.checkbutton11 = self.add_checkbutton(grid,
            _('Only download finished livestreams'),
            None,
            0, 4, 1, 1,
        )
        self.checkbutton11.set_active(self.edit_obj.ignore_old_stream_flag)
        if not self.edit_obj.dl_by_video_flag:
            self.checkbutton11.set_sensitive(False)


    # Callback class methods


    def on_add_language_clicked(self, button):

        """Called by callback in self.setup_tabs().

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = self.treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:

            # Nothing selected
            return

        name = model[tree_iter][0]
        # From a string in the form 'English [en]', remove the language code to
        #    get a key in formats.LANGUAGE_CODE_DICT, e.g. 'English'
        match = re.search(r'^(.*)\s\[', name)
        if match:

            language = match.groups()[0]
            if language in formats.LANGUAGE_CODE_DICT:

                lang_code = formats.LANGUAGE_CODE_DICT[language]
                new_list = self.retrieve_val('dl_if_subs_list')
                # (Don't add duplicates)
                if lang_code not in new_list:

                    new_list.append(lang_code)

                    self.edit_dict['dl_if_subs_list'] = new_list

                    # Update the treeview
                    self.setup_subtitles_tab_redraw_list()


    def on_clone_settings_clicked(self, button):

        """Called by callback in self.setup_tabs().

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Custom downloads > Name'
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
                'yes': 'clone_custom_dl_manager_from_window',
                'data': [self, self.edit_obj],
            },
        )


    def on_delay_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables delays between downloads of individual media data
        objects.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['delay_flag'] = True

            self.spinbutton.set_sensitive(True)
            self.spinbutton2.set_sensitive(True)

        else:

            self.edit_dict['delay_flag'] = False

            self.spinbutton.set_sensitive(False)
            self.spinbutton2.set_sensitive(False)


    def on_delay_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_tabs().

        Updates both delay spinbutton widgets, as well as setting the IV.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        value = spinbutton.get_value()
        self.edit_dict['delay_max'] = value
        self.spinbutton2.set_range(0, value)


    def on_divert_button_toggled(self, radiobutton):

        """Called from callback in self.setup_tabs().

        Sets the YouTube mirror from which downloads are obtained.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if self.radiobutton.get_active():
            self.edit_dict['divert_mode'] = 'default'
        elif self.radiobutton2.get_active():
            self.edit_dict['divert_mode'] = 'hooktube'
        elif self.radiobutton3.get_active():
            self.edit_dict['divert_mode'] = 'invidious'
        elif self.radiobutton4.get_active():
            self.edit_dict['divert_mode'] = 'other'

        if self.radiobutton4.get_active():
            self.entry.set_sensitive(True)
        else:
            self.entry.set_sensitive(False)
            self.entry.set_text('')


    def on_dl_by_video_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables downloading videos independently of their channels/
        playlists.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['dl_by_video_flag'] = True

            self.checkbutton2.set_active(True)
            self.checkbutton2.set_sensitive(True)
            if not self.retrieve_val('dl_precede_flag'):
                self.checkbutton3.set_active(False)
                self.checkbutton3.set_sensitive(False)
                self.checkbutton4.set_active(False)
                self.checkbutton4.set_sensitive(False)
                self.button3.set_sensitive(False)
                self.button4.set_sensitive(False)
            else:
                self.checkbutton3.set_sensitive(True)
                if not self.retrieve_val('dl_if_subs_flag'):
                    self.checkbutton4.set_active(False)
                    self.checkbutton4.set_sensitive(False)
                    self.button3.set_sensitive(False)
                    self.button4.set_sensitive(False)
                else:
                    if not self.retrieve_val('ignore_if_no_subs_flag'):
                        self.checkbutton4.set_active(False)
                        self.checkbutton4.set_sensitive(False)
                    else:
                        self.checkbutton4.set_sensitive(True)
                    self.button3.set_sensitive(True)
                    self.button4.set_sensitive(True)
            self.checkbutton5.set_sensitive(True)
            if self.retrieve_val('split_flag'):
                self.checkbutton6.set_sensitive(False)
            else:
                self.checkbutton6.set_sensitive(True)
            self.radiobutton.set_sensitive(True)
            self.radiobutton2.set_sensitive(True)
            self.radiobutton3.set_sensitive(True)
            self.radiobutton4.set_sensitive(True)
            if self.retrieve_val('divert_mode') == 'other':
                self.entry.set_sensitive(True)
            else:
                self.entry.set_sensitive(False)
            self.checkbutton8.set_sensitive(True)
            self.checkbutton9.set_sensitive(True)
            self.checkbutton10.set_sensitive(True)
            self.checkbutton11.set_sensitive(True)

        else:

            self.edit_dict['dl_by_video_flag'] = False

            self.checkbutton2.set_sensitive(False)
            self.checkbutton2.set_active(False)
            self.checkbutton3.set_sensitive(False)
            self.checkbutton3.set_active(False)
            self.checkbutton4.set_sensitive(False)
            self.checkbutton4.set_active(False)
            self.button3.set_sensitive(False)
            self.button4.set_sensitive(False)
            self.checkbutton5.set_sensitive(False)
            self.checkbutton5.set_active(False)
            self.checkbutton6.set_sensitive(False)
            self.checkbutton6.set_active(False)
            self.radiobutton.set_sensitive(False)
            self.radiobutton2.set_sensitive(False)
            self.radiobutton3.set_sensitive(False)
            self.radiobutton4.set_sensitive(False)
            self.entry.set_sensitive(False)
            self.checkbutton8.set_active(False)
            self.checkbutton8.set_sensitive(False)
            self.checkbutton9.set_active(False)
            self.checkbutton9.set_sensitive(False)
            self.checkbutton10.set_active(False)
            self.checkbutton10.set_sensitive(False)
            self.checkbutton11.set_active(False)
            self.checkbutton11.set_sensitive(False)


    def on_dl_if_live_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables only downloading broadcasting livestreams.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['dl_if_stream_flag'] = True
            self.checkbutton8.set_active(False)

        else:

            self.edit_dict['dl_if_stream_flag'] = False


    def on_dl_if_old_live_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables only downloading finished livestreams.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['dl_if_old_stream_flag'] = True
            self.checkbutton9.set_active(False)

        else:

            self.edit_dict['dl_if_old_stream_flag'] = False


    def on_dl_if_subs_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables downloading only videos with subtitles.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['dl_if_subs_flag'] = True

            self.checkbutton4.set_sensitive(True)
            self.button3.set_sensitive(True)
            self.button4.set_sensitive(True)

        else:

            self.edit_dict['dl_if_subs_flag'] = False

            self.checkbutton4.set_sensitive(False)
            self.checkbutton4.set_active(False)
            self.button3.set_sensitive(False)
            self.button4.set_sensitive(False)


    def on_dl_precede_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables checking videos, before downloading them independently
        of their channels/playlists.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['dl_precede_flag'] = True

            self.checkbutton3.set_sensitive(True)
            if not self.retrieve_val('dl_if_subs_flag'):
                self.checkbutton4.set_active(False)
                self.checkbutton4.set_sensitive(False)
                self.button3.set_sensitive(False)
                self.button4.set_sensitive(False)
            else:
                self.checkbutton4.set_sensitive(True)
                self.button3.set_sensitive(True)
                self.button4.set_sensitive(True)

        else:

            self.edit_dict['dl_precede_flag'] = False

            self.checkbutton3.set_sensitive(False)
            self.checkbutton3.set_active(False)
            self.checkbutton4.set_sensitive(False)
            self.checkbutton4.set_active(False)
            self.button3.set_sensitive(False)
            self.button4.set_sensitive(False)


    def on_ignore_live_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables not downloading broadcasting livestreams.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['ignore_stream_flag'] = True
            self.checkbutton10.set_active(False)

        else:

            self.edit_dict['ignore_stream_flag'] = False


    def on_ignore_old_live_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables not downloading finished livestreams.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['ignore_old_stream_flag'] = True
            self.checkbutton11.set_active(False)

        else:

            self.edit_dict['ignore_old_stream_flag'] = False


    def on_remove_language_clicked(self, button):

        """Called by callback in self.setup_tabs().

        Args:

            button (Gtk.Button): The widget clicked

        """

        selection = self.treeview2.get_selection()
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
            old_list = self.retrieve_val('dl_if_subs_list')
            new_list = []
            for other_code in old_list:
                if other_code != lang_code:
                    new_list.append(other_code)

            self.edit_dict['dl_if_subs_list'] = new_list

            # Update the treeview
            self.setup_subtitles_tab_redraw_list()


    def on_reset_settings_clicked(self, button):

        """Called by callback in self.setup_tabs().

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Custom downloads > Name'
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
                'yes': 'reset_custom_dl_manager',
                # (Reset this edit window, if the user clicks 'yes')
                'data': [self],
            },
        )


    def on_select_all_button_clicked(self, button):

        """Called by callback in self.setup_tabs().

        Args:

            button (Gtk.Button): The widget clicked

        """

        slice_dict = self.retrieve_val('slice_dict')
        for key in slice_dict:
            slice_dict[key] = True

        self.edit_dict['slice_dict'] = slice_dict

        # Update the treeview
        self.setup_slices_tab_update_treeview()


    def on_slice_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables removing slices from a video.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['slice_flag'] = True

            self.button5.set_sensitive(True)
            self.button6.set_sensitive(True)

        else:

            self.edit_dict['split_flag'] = False

            self.button5.set_sensitive(False)
            self.button6.set_sensitive(False)


    def on_split_button_toggled(self, checkbutton):

        """Called from callback in self.setup_tabs().

        Enables/disables splitting a video into video clips.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if checkbutton.get_active():

            self.edit_dict['split_flag'] = True

            self.checkbutton6.set_sensitive(False)
            self.checkbutton6.set_active(False)

        else:

            self.edit_dict['split_flag'] = False

            self.checkbutton6.set_sensitive(True)


    def on_treeview_button_toggled(self, renderer_toggle, tree_path):

        """Called from callback in self.setup_slices_tab().

        Enables/disables a category of video slice.

        Args:

            renderer_toggle (Gtk.CellRendererToggle): The widget clicked

            tree_path (Gtk.TreePath): Path to the clicked row

        """

        # (This condition makes the treeview insensitive, when other widgets
        #   in the same tab are insensitive)
#        if self.retrieve_val('slice_flag'):
        if self.checkbutton6.get_active():

            self.liststore3[tree_path][0] = not self.liststore3[tree_path][0]

            slice_dict = self.retrieve_val('slice_dict')
            slice_dict[self.liststore3[tree_path][1]] \
            = self.liststore3[tree_path][0]

            self.edit_dict['slice_dict'] = slice_dict


    def on_unselect_all_button_clicked(self, button):

        """Called by callback in self.setup_tabs().

        Args:

            button (Gtk.Button): The widget clicked

        """

        slice_dict = self.retrieve_val('slice_dict')
        for key in slice_dict:
            slice_dict[key] = False

        self.edit_dict['slice_dict'] = slice_dict

        # Update the treeview
        self.setup_slices_tab_update_treeview()
