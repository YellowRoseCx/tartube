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


class ScheduledEditWin(GenericEditWin):

    """Python class for an 'edit window' to modify values in a media.Scheduled
    object.

    Args:

        app_obj (mainapp.TartubeApp): The main application object

        edit_obj (media.Scheduled): The object whose attributes will be edited
            in this window

    """


    # Standard class methods


    def __init__(self, app_obj, edit_obj):

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Scheduled downloads window starts here.' \
            + ' In the menu, click Edit > System preferences...' \
            + ' Scheduling > Start. In the \'Scheduled download name\'' \
            + ' box, add a name. Then click the Add button'
        )

        Gtk.Window.__init__(self, title=_('Scheduled download'))

        if self.is_duplicate(app_obj, edit_obj):
            return

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # The media.Scheduled object being edited
        self.edit_obj = edit_obj


        # IV list - Gtk widgets
        # ---------------------
        self.grid = None                        # Gtk.Grid
        self.notebook = None                    # Gtk.Notebook
        self.reset_button = None                # Gtk.Button
        self.apply_button = None                # Gtk.Button
        self.ok_button = None                   # Gtk.Button
        self.cancel_button = None               # Gtk.Button
        # (IVs used to handle widget changes in the 'Media' tab)
        self.radiobutton = None                 # Gtk.RadioButton
        self.radiobutton2 = None                # Gtk.RadioButton

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
        # The key-value pairs in the dictionary correspond directly to
        #   the names of attributes, and their balues in self.edit_obj
        # Key-value pairs are added to this dictionary whenever the user
        #   makes a change (so if no changes are made when the window is
        #   closed, the dictionary will still be empty)
        self.edit_dict = {}

        # String identifying the media type
        self.media_type = 'scheduled'


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

        # Since the edit window opened, channels/playlists/folders may have
        #   been deleted. Check that any items in the .media_list IV still
        #   exist
        for dbid in self.edit_obj.media_list:

            if not dbid in self.app_obj.container_reg_dict:
                self.edit_obj.media_list.remove(dbid)

        # Update the parent preference window's list of scheduled downloads
        for win_obj in self.app_obj.main_win_obj.config_win_list:

            if isinstance(win_obj, SystemPrefWin):
                win_obj.setup_scheduling_start_tab_update_treeview()


#   def retrieve_val():         # Inherited from GenericConfigWin


    # (Setup tabs)


    def setup_tabs(self):

        """Called by self.setup(), .on_button_apply_clicked() and
        .on_button_reset_clicked().

        Sets up the tabs for this edit window.
        """

        self.setup_general_tab()
        self.setup_start_tab()
        self.setup_stop_tab()
        self.setup_conflicts_tab()
        self.setup_media_tab()
        self.setup_limits_tab()
        self.setup_other_tab()


    def setup_general_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'General' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Scheduled downloads > General'
        )

        tab, grid = self.add_notebook_tab(_('_General'))
        grid_width = 3

        # General properties
        self.add_label(grid,
            '<u>' + _('General properties') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            _('Scheduled download name'),
            0, 1, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            1, 1, (grid_width - 1), 1,
        )
        entry.set_text(self.edit_obj.name)
        entry.set_editable(False)

        self.add_label(grid,
            _('Download mode'),
            0, 2, 1, 1,
        )

        combo_list = [
            [_('Check channels, playlist and folders'), 'sim'],
            [_('Download channels, playlists and folders'), 'real'],
            [_('Perform a custom download'), 'custom_real'],
        ]

        combo = self.add_combo_with_data(grid,
            combo_list,
            'dl_mode',
            1, 2, (grid_width - 1), 1,
        )
        combo.set_hexpand(True)
        # (Signal connect appears below, overriding the generic one)

        self.add_label(grid,
            _('Custom download name'),
            0, 3, 1, 1,
        )

        combo_list2 = [
            [
                '',
                '',     # self.on_custom_dl_combo_changed() converts it to None
            ],
            [
                self.app_obj.general_custom_dl_obj.name,
                self.app_obj.general_custom_dl_obj.uid,
            ],
        ]
        if self.app_obj.classic_custom_dl_obj is not None:
            combo_list2.append([
                self.app_obj.classic_custom_dl_obj.name,
                self.app_obj.classic_custom_dl_obj.uid,
            ])

        for custom_dl_obj in self.app_obj.custom_dl_reg_dict.values():
            if self.app_obj.general_custom_dl_obj != custom_dl_obj \
            and (
                not self.app_obj.classic_custom_dl_obj \
                or self.app_obj.classic_custom_dl_obj != custom_dl_obj
            ):
                combo_list2.append([custom_dl_obj.name, custom_dl_obj.uid])

        combo2 = self.add_combo_with_data(grid,
            combo_list2,
            'custom_dl_uid',
            1, 3, (grid_width - 1), 1,
        )
        combo2.set_hexpand(True)
        if self.edit_obj.dl_mode != 'custom_real':
            combo2.set_sensitive(False)
        # (Signal connect appears below, overriding the generic one)

        # (Signal connects from above)
        combo.connect(
            'changed',
            self.on_dl_mode_combo_changed,
            combo2,
        )
        combo2.connect(
            'changed',
            self.on_custom_dl_combo_changed,
        )


    def setup_start_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Start' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Scheduled downloads > Start'
        )

        tab, grid = self.add_notebook_tab(_('_Start'))
        grid_width = 4

        # Start conditions
        self.add_label(grid,
            '<u>' + _('Start conditions') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            _('Start mode'),
            0, 1, 1, 1,
        )

        combo_list = [
            [_('Perform this download at regular intervals'), 'repeat'],
            [_('Perform this download when Tartube starts'), 'start'],
            [
                _('Perform this download some time after Tartube starts'),
                'start_after',
            ],
            [_('Perform this download at specified times'), 'timetable'],
            [_('Disable this scheduled download'), 'disabled'],
        ]

        combo = self.add_combo_with_data(grid,
            combo_list,
            None,
            1, 1, (grid_width - 1), 1,
        )
        combo.set_hexpand(True)
        # (Signal connect appears below)

        label = self.add_label(grid,
            '',
            0, 2, 1, 1,
        )

        spinbutton = self.add_spinbutton(grid,
            1, None, 1,
            'wait_value',
            1, 2, 1, 1,
        )

        combo2_list = []
        for unit in formats.TIME_METRIC_LIST:
            if unit != 'seconds':
                combo2_list.append(
                    [ formats.TIME_METRIC_TRANS_DICT[unit], unit ],
                )

        combo2 = self.add_combo_with_data(grid,
            combo2_list,
            'wait_unit',
            2, 2, 2, 1,
        )
        combo2.set_hexpand(True)

        label2 = self.add_label(grid,
            '',
            0, 3, 1, 1,
        )

        treeview, liststore = self.add_treeview(grid,
            1, 3, 1, 10,
        )
        self.setup_start_tab_update_treeview(liststore)

        combo3_list = []
        for key in formats.SPECIFIED_DAYS_LIST:
            combo3_list.append(
                [ formats.SPECIFIED_DAYS_DICT[key], key ],
            )

        combo3 = self.add_combo_with_data(grid,
            combo3_list,
            None,
            2, 3, 2, 1,
        )
        combo3.set_hexpand(True)
        combo3.set_active(0)

        label3 = self.add_label(grid,
            _('Hours'),
            2, 4, 1, 1,
        )
        label3.set_hexpand(False)

        spinbutton2 = self.add_spinbutton(grid,
            0, 23, 1,
            None,
            3, 4, 1, 1,
        )
        # (Signal connect appears below)

        label4 = self.add_label(grid,
            _('Minutes'),
            2, 5, 1, 1,
        )
        label4.set_hexpand(False)

        spinbutton3 = self.add_spinbutton(grid,
            0, 55, 5,
            None,
            3, 5, 1, 1,
        )
        # (Signal connect appears below)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 2, 6, 2, 1)

        button = Gtk.Button()
        grid2.attach(button, 0, 0, 1, 1)
        button.set_label(_('Add'))
        button.set_hexpand(True)
        # (Signal connect appears below)

        button2 = Gtk.Button()
        grid2.attach(button2, 1, 0, 1, 1)
        button2.set_label(_('Remove'))
        button2.set_hexpand(True)
        # (Signal connect appears below)

        # (Set up widgets in their initial state)
        if self.edit_obj.start_mode == 'repeat':
            combo.set_active(0)
        elif self.edit_obj.start_mode == 'start':
            combo.set_active(1)
        elif self.edit_obj.start_mode == 'start_after':
            combo.set_active(2)
        elif self.edit_obj.start_mode == 'timetable':
            combo.set_active(3)
        else:
            # .start_mode is 'disabled'
            combo.set_active(4)

        self.setup_start_tab_update_widgets(
            label,
            spinbutton,
            combo2,
            label2,
            combo3,
            spinbutton2,
            spinbutton3,
            button,
            button2,
        )

        # (Signal connects from above)
        combo.connect(
            'changed',
            self.on_start_mode_combo_changed,
            label,
            spinbutton,
            combo2,
            label2,
            combo3,
            spinbutton2,
            spinbutton3,
            button,
            button2,
        )

        # (Signal for showing leading zeroes for both hours and minutes)
        spinbutton2.connect('output', self.show_spinbutton_leading_zeroes, 2)
        spinbutton3.connect('output', self.show_spinbutton_leading_zeroes, 2)

        button.connect(
            'clicked',
            self.on_add_timetable_button_clicked,
            liststore,
            combo3,
            spinbutton2,
            spinbutton3,
        )
        button2.connect(
            'clicked',
            self.on_remove_timetable_button_clicked,
            treeview,
            liststore,
        )


    def setup_start_tab_update_widgets(self, label, spinbutton, combo2, \
    label2, combo3, spinbutton2, spinbutton3, button, button2):

        """Called by self.setup_start_tab() and .on_start_mode_combo_changed().

        Sets up widgets on opening, and when the first combo (marked 'Start
        Mode') changes.

        Args:

            label (Gtk.Label): A widget to be modified

            spinbutton (Gtk.SpinButton): Another widget to be modified

            combo2 (Gtk.Combo): Another widget to be modified

            label2 (Gtk.Label): Another widget to be modified

            combo3 (Gtk.Combo): Another widget to be modified

            spinbutton2, spinbutton3 (Gtk.SpinButton): Other widgets to be
                modified

            button, button (Gtk.Button): Other widgets to be modified

        """

        label.set_markup('')
        spinbutton.set_sensitive(False)
        combo2.set_sensitive(False)
        label2.set_markup('')
        combo3.set_sensitive(False)
        spinbutton2.set_sensitive(False)
        spinbutton3.set_sensitive(False)
        button.set_sensitive(False)
        button2.set_sensitive(False)

        start_mode = self.retrieve_val('start_mode')
        if start_mode == 'repeat':
            label.set_markup(_('Interval time'))
            spinbutton.set_sensitive(True)
            combo2.set_sensitive(True)
        elif start_mode == 'start':
            pass
        elif start_mode == 'start_after':
            label.set_markup('Time after startup')
            spinbutton.set_sensitive(True)
            combo2.set_sensitive(True)
        elif start_mode == 'timetable':
            label2.set_markup(_('Start times'))
            combo3.set_sensitive(True)
            spinbutton2.set_sensitive(True)
            spinbutton3.set_sensitive(True)
            button.set_sensitive(True)
            button2.set_sensitive(True)
        else:
            # 'start_mode' is 'disabled'
            pass


    def setup_start_tab_update_treeview(self, liststore):

        """Called by self.setup_start_tab(), .on_add_timetable_button_clicked()
        and .on_remove_timetable_button_clicked().

        Updates the treeview showing timetabled start times.

        Args:

            liststore (Gtk.ListStore): The treeview's model

        """

        timetable_list = self.retrieve_val('timetable_list')
        liststore.clear()

        # Each 'mini_list' is in the form [ day_string, time_string ]
        for mini_list in timetable_list:
            liststore.append([
                formats.SPECIFIED_DAYS_DICT[mini_list[0]] + ' ' + mini_list[1],
            ])


    def setup_stop_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Stop' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Scheduled downloads > Stop'
        )

        tab, grid = self.add_notebook_tab(_('_Stop'))
        grid_width = 4

        # Stop conditions
        self.add_label(grid,
            '<u>' + _('Stop conditions') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
            'N.B. When this setting is triggered, the entire download' \
            + ' operation stops',
            ) + '</i>',
            0, 1, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Stop download operation after this much time'),
            None,
            0, 2, 1, 1,
        )
        checkbutton.set_active(self.edit_obj.autostop_time_flag)
        # (Signal connect appears below)

        spinbutton = self.add_spinbutton(grid,
            1, None, 1,
            None,
            1, 2, 1, 1,
        )
        spinbutton.set_value(self.edit_obj.autostop_time_value)
        if not self.edit_obj.autostop_time_flag:
            spinbutton.set_sensitive(False)
        # (Signal connect appears below)

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
                self.edit_obj.autostop_time_unit,
            )
        )
        if not self.edit_obj.autostop_time_flag:
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
            _('Stop download operation after this many videos'),
            None,
            0, 3, 1, 1,
        )
        checkbutton2.set_active(self.edit_obj.autostop_videos_flag)
        # (Signal connect appears below)

        spinbutton2 = self.add_spinbutton(grid,
            1, None, 1,
            None,
            1, 3, 1, 1,
        )
        spinbutton2.set_value(self.edit_obj.autostop_videos_value)
        if not self.edit_obj.autostop_videos_flag:
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
            _('Stop download operation after this much disk space'),
            None,
            0, 4, 1, 1,
        )
        checkbutton3.set_active(self.edit_obj.autostop_size_flag)
        # (Signal connect appears below)

        spinbutton3 = self.add_spinbutton(grid,
            1, None, 1,
            None,
            1, 4, 1, 1,
        )
        spinbutton3.set_value(self.edit_obj.autostop_size_value)
        if not self.edit_obj.autostop_size_flag:
            spinbutton3.set_sensitive(False)
        # (Signal connect appears below)

        combo3 = self.add_combo(grid,
            formats.FILESIZE_METRIC_LIST,
            None,
            2, 4, 1, 1,
        )
        combo3.set_active(
            formats.FILESIZE_METRIC_LIST.index(
                self.edit_obj.autostop_size_unit,
            )
        )
        if not self.edit_obj.autostop_size_flag:
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


    def setup_conflicts_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Conflicts' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Scheduled downloads > Conflicts'
        )

        tab, grid = self.add_notebook_tab(_('_Conflicts'))

        # Conflict settings
        self.add_label(grid,
            '<u>' + _('Conflict settings') + '</u>',
            0, 0, 1, 1,
        )

        self.add_label(grid,
            _('If another scheduled download is running:'),
            0, 1, 1, 1,
        )

        combo4_list = [
            [
                _(
                'Add channels, playlists and folders to the end of the queue',
                ),
                'join',
            ],
            [
                _(
                'Add channels, playlists and folders to the beginning of the' \
                + ' queue',
                ),
                'priority',
            ],
            [
                _(
                'Do nothing, just wait until the next scheduled download' \
                + ' time',
                ),
                'skip',
            ],
        ]

        combo4 = self.add_combo_with_data(grid,
            combo4_list,
            'join_mode',
            0, 2, 1, 1,
        )
        combo4.set_hexpand(True)

        self.add_checkbutton(grid,
            _('This scheduled download takes priority over others') \
            + '\n' \
            + _(
            'Other scheduled downloads won\'t start until this one is' \
            + ' finished',
            ),
            'exclusive_flag',
            0, 3, 1, 1,
        )


    def setup_media_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'General' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Scheduled downloads > Media'
        )

        tab, grid = self.add_notebook_tab(_('_Media'))
        grid_width = 4

        # Media to download
        self.add_label(grid,
            '<u>' + _('Media to download') + '</u>',
            0, 0, grid_width, 1,
        )

        self.radiobutton = self.add_radiobutton(grid,
            None,
            _('Check/download everything'),
            None,
            None,
            0, 1, grid_width, 1,
        )

        self.radiobutton2 = self.add_radiobutton(grid,
            self.radiobutton,
            _('Only check/download the media below'),
            None,
            None,
            0, 2, grid_width, 1,
        )
        if not self.edit_obj.all_flag:
            self.radiobutton2.set_active(True)
        self.radiobutton2.connect(
            'toggled',
            self.on_all_flag_toggled,
        )

        self.add_label(grid,
            '<i>' + _(
            'Hint: you can drag and drop channels, playlists and your own' \
            + ' folders here',
            ) + '</i>',
            0, 3, grid_width, 1,
        )

        # Create a treeview, containing the .dbid (invisible) and .name
        #   (visible) for each media data object added
        frame = Gtk.Frame()
        grid.attach(frame, 0, 4, grid_width, 1)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        treestore = Gtk.ListStore(int, str)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_model(treestore)
        treeview.set_headers_visible(False)
        treeview.set_hexpand(True)

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn(
            '',
            renderer_text,
            text=1,
        )
        treeview.append_column(column_text)

        # Initialise the treeview
        self.setup_media_tab_update_treeview(treestore)

        # Set up drag and drop into the treeview
        drag_target_list = [('text/plain', 0, 0)]
        treeview.enable_model_drag_dest(
            # Table of targets the drag procedure supports, and array length
            drag_target_list,
            # Bitmask of possible actions for a drag from this widget
            Gdk.DragAction.DEFAULT,
        )
        treeview.connect(
            'drag-drop',
            self.on_video_index_drag_drop,
        )
        treeview.connect(
            'drag-data-received',
            self.on_video_index_drag_data_received,
        )

        # Editing widgets
        obj_list = []
        for media_data_obj in self.app_obj.container_reg_dict.values():

            if not isinstance(media_data_obj, media.Folder) \
            or not media_data_obj.fixed_flag:
                obj_list.append(media_data_obj)

        obj_list.sort(key=lambda x: x.name.lower())

        combostore = Gtk.ListStore(int, str)
        for media_data_obj in obj_list:
            combostore.append( [media_data_obj.dbid, media_data_obj.name] )

        combo = Gtk.ComboBox.new_with_model(combostore)
        grid.attach(combo, 0, 5, 1, 1)

        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 1)

        combo.set_entry_text_column(1)
        combo.set_active(0)

        button = Gtk.Button()
        grid.attach(button, 1, 5, 1, 1)
        button.set_label(_('Add'))
        button.connect(
            'clicked',
            self.on_add_media_button_clicked,
            combo,
            treestore,
        )

        button2 = Gtk.Button()
        grid.attach(button2, 2, 5, 1, 1)
        button2.set_label(_('Remove'))
        button2.connect(
            'clicked',
            self.on_remove_media_button_clicked,
            treeview,
        )

        button3 = Gtk.Button()
        grid.attach(button3, 3, 5, 1, 1)
        button3.set_label(_('Clear list'))
        button3.connect(
            'clicked',
            self.on_clear_media_button_clicked,
            treestore,
        )


    def setup_media_tab_update_treeview(self, liststore):

        """Called by self.setup_media_tab() and some callbacks.

        Updates the treeview to display the media.Scheduled object's
        .media_list IV, first checking that any specified media data objects
        still exist.

        Args:

            liststore (Gtk.ListStore): The treeview's model

        """

        liststore.clear()

        media_list = self.retrieve_val('media_list')
        for dbid in media_list:

            # This media data object may be deleted while the window is open
            #   (but the .media_list IV is checked, when the 'Save' or 'Apply'
            #   buttons are clicked)
            if dbid in self.app_obj.container_reg_dict:
                media_data_obj = self.app_obj.media_reg_dict[dbid]
                liststore.append([media_data_obj.dbid, media_data_obj.name])


    def setup_limits_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Limits' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Scheduled downloads > Limits'
        )

        tab, grid = self.add_notebook_tab(_('_Limits'))
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

        self.add_label(grid,
            '<i>' + _('These limits override the default and alternative' \
            + ' limits specified elsewhere') + '</i>',
            0, 2, grid_width, 1,
        )

        checkbutton = self.add_checkbutton(grid,
            _('Limit simultaneous downloads to'),
            'scheduled_num_worker_apply_flag',
            0, 3, 1, 1,
        )
        checkbutton.set_hexpand(False)

        spinbutton = self.add_spinbutton(grid,
            self.app_obj.num_worker_min,
            self.app_obj.num_worker_max,
            1,                  # Step
            'scheduled_num_worker',
            1, 3, 1, 1,
        )

        checkbutton2 = self.add_checkbutton(grid,
            _('Limit download speed to'),
            'scheduled_bandwidth_apply_flag',
            0, 4, 1, 1,
        )
        checkbutton2.set_hexpand(False)

        spinbutton2 = self.add_spinbutton(grid,
            self.app_obj.bandwidth_min,
            self.app_obj.bandwidth_max,
            1,                  # Step
            'scheduled_bandwidth',
            1, 4, 1, 1,
        )

        self.add_label(grid,
            'KiB/s',
            2, 3, 1, 1,
        )


    def setup_other_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Other' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Scheduled downloads > Other'
        )

        tab, grid = self.add_notebook_tab(_('_Other'))

        # Other settings
        self.add_label(grid,
            '<u>' + _('Other settings') + '</u>',
            0, 0, 1, 1,
        )

        self.add_checkbutton(grid,
            _(
            'Ignore time-saving preferences, and check/download the whole' \
            + ' channel/playlist/folder',
            ),
            'ignore_limits_flag',
            0, 1, 1, 1,
        )

        self.add_checkbutton(grid,
            _('Shut down Tartube when this scheduled download has finished'),
            'shutdown_flag',
            0, 2, 1, 1,
        )


    # Callback class methods


#   def on_button_apply_options_clicked():  # Inherited from GenericConfigWin


#   def on_button_edit_options_clicked():   # Inherited from GenericConfigWin


#   def on_button_remove_options_clicked(): # Inherited from GenericConfigWin


    def on_add_media_button_clicked(self, button, combo, liststore):

        """Called by callback in self.setup_media_tab().

        Args:

            button (Gtk.Button): The widget clicked

            combo (Gtk.ComboBox): A combo in which the user has selected a new
                media data object

            liststore (Gtk.ListStore): The treeview's model

        """

        combo_iter = combo.get_active_iter()
        combo_model = combo.get_model()
        dbid = combo_model[combo_iter][0]

        # Check the media data object hasn't already been added to the list,
        #   and that is still exists in the media data registry
        media_list = self.retrieve_val('media_list')

        if not dbid in media_list \
        and dbid in self.app_obj.container_reg_dict:

            media_list.append(dbid)
            self.edit_dict['media_list'] = media_list

            self.radiobutton2.set_active(True)

            # Update the treeview
            self.setup_media_tab_update_treeview(liststore)


    def on_add_timetable_button_clicked(self, button, liststore, combo, \
    spinbutton, spinbutton2):

        """Called by callback in self.setup_start_tab().

        Args:

            button (Gtk.Button): The widget clicked

            liststore (Gtk.ListStore): The treeview's model

            combo (Gtk.ComboBox): A widget to modify

            spinbutton, spinbutton2 (Gtk.SpinButton): Other widgets to modify

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        day_str = model[tree_iter][1]

        hours = int(spinbutton.get_value())
        minutes = int(spinbutton2.get_value())

        # Each 'mini_list' is in the form [ day_string, time_string ]
        timetable_list = self.retrieve_val('timetable_list')
        mini_list = [
            day_str,
            '{:02d}'.format(hours) + ':' + '{:02d}'.format(minutes),
        ]
        # Check for duplicates
        for other_list in timetable_list:
            if other_list[0] == mini_list[0] \
            and other_list[1] == mini_list[1]:
                return

        # No duplicates found
        timetable_list.append(mini_list)
        self.edit_dict['timetable_list'] = timetable_list
        self.setup_start_tab_update_treeview(liststore)


    def on_all_flag_toggled(self, radiobutton):

        """Called from callback in self.setup_media_tab().

        Enables/disables checking/downloading all media.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if radiobutton.get_active():
            self.edit_obj.all_flag = False
        else:
            self.edit_obj.all_flag = True


    def on_autostop_size_button_toggled(self, checkbutton, spinbutton, combo):

        """Called from callback in self.setup_stop_tab().

        Enables/disables auto-stopping a download operation after a certain
        amount of disk space.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): Another widget to modify

            combo (Gtk.ComboBox): Another widget to modify

        """

        if not checkbutton.get_active():
            self.edit_dict['autostop_size_flag'] = False
            spinbutton.set_sensitive(False)
            combo.set_sensitive(False)
        else:
            self.edit_dict['autostop_size_flag'] = True
            spinbutton.set_sensitive(True)
            combo.set_sensitive(True)


    def on_autostop_size_combo_changed(self, combo):

        """Called from a callback in self.setup_stop_tab().

        Sets the disk space unit at which a download operation is auto-stopped.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.edit_dict['autostop_size_unit'] = model[tree_iter][0]


    def on_autostop_size_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_stop_tab().

        Sets the disk space value at which a download operation is
        auto-stopped.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.edit_dict['autostop_size_value'] = spinbutton.get_value()


    def on_autostop_time_button_toggled(self, checkbutton, spinbutton, combo):

        """Called from callback in self.setup_stop_tab().

        Enables/disables auto-stopping a download operation after a certain
        time.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): Another widget to modify

            combo (Gtk.ComboBox): Another widget to modify

        """

        if not checkbutton.get_active():
            self.edit_dict['autostop_time_flag'] = False
            spinbutton.set_sensitive(False)
            combo.set_sensitive(False)
        else:
            self.edit_dict['autostop_time_flag'] = True
            spinbutton.set_sensitive(True)
            combo.set_sensitive(True)


    def on_autostop_time_combo_changed(self, combo):

        """Called from a callback in self.setup_stop_tab().

        Sets the time unit at which a download operation is auto-stopped.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.edit_dict['autostop_time_unit'] = model[tree_iter][0]


    def on_autostop_time_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_stop_tab().

        Sets the time value at which a download operation is auto-stopped.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.edit_dict['autostop_time_value'] = spinbutton.get_value()


    def on_autostop_videos_button_toggled(self, checkbutton, spinbutton):

        """Called from callback in self.setup_stop_tab().

        Enables/disables auto-stopping a download operation after a certain
        number of videos.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            spinbutton (Gtk.SpinButton): Another widget to modify

        """

        if not checkbutton.get_active():
            self.edit_dict['autostop_videos_flag'] = False
            spinbutton.set_sensitive(False)
        else:
            self.edit_dict['autostop_videos_flag'] = True
            spinbutton.set_sensitive(True)


    def on_autostop_videos_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_stop_tab().

        Sets the number of videos at which a download operation is
        auto-stopped.

        Args:

            spinbutton (Gtk.SpinButton): The widget clicked

        """

        self.edit_dict['autostop_videos_value'] = spinbutton.get_value()


    def on_clear_media_button_clicked(self, button, liststore):

        """Called by callback in self.setup_media_tab().

        Args:

            button (Gtk.Button): The widget clicked

            liststore (Gtk.ListStore): The treeview's model

        """

        # Update the IV
        self.edit_dict['media_list'] = []
        # Update widgets
        liststore.clear()
        self.radiobutton.set_active(True)


    def on_custom_dl_combo_changed(self, combo):

        """Called from callback in self.setup_general_tab().

        Sets the IV.

        Args:

            combo (Gtk.ComboBox): The widget clicked

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        value = model[tree_iter][1]

        if value is None or value == '':
            self.edit_dict['custom_dl_uid'] = None
        else:
            self.edit_dict['custom_dl_uid'] = int(value)


    def on_dl_mode_combo_changed(self, combo, combo2):

        """Called from callback in self.setup_general_tab().

        Sets the IV, and (de)sensitises other widgets.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            combo2 (Gtk.ComboBox): Another widget to update

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.edit_dict['dl_mode'] = model[tree_iter][1]

        if self.edit_dict['dl_mode'] == 'custom_real':
            combo2.set_sensitive(True)
        else:
            combo2.set_active(0)
            combo2.set_sensitive(False)


    def on_remove_media_button_clicked(self, button, treeview):

        """Called by callback in self.setup_media_tab().

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The list of media data objects

        """

        selection = treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:

            # Nothing selected
            return

        else:

            dbid = model[tree_iter][0]

        # Check the media data object exists in the list and in the media data
        #   registry
        media_list = self.retrieve_val('media_list')
        if dbid in media_list:

            media_list.remove(dbid)
            self.edit_dict['media_list'] = media_list

            # Update widgets
            self.setup_media_tab_update_treeview(treeview.get_model())
            if not media_list:
                self.radiobutton.set_active(True)


    def on_remove_timetable_button_clicked(self, button, treeview, liststore):

        """Called by callback in self.setup_start_tab().

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview to be updated

            liststore (Gtk.ListStore): The treeview's model

        """

        selection = treeview.get_selection()
        (model, tree_iter) = selection.get_selected()
        if tree_iter is None:
            # Nothing selected
            return

        display_str = model[tree_iter][0]

        match = re.search(r'^(.*)\s(\d\d\:\d\d)', display_str)
        if match:

            translated_str = match.groups()[0]
            time_str = match.groups()[1]

            # Compile a reversed dictionary for lookup
            rev_dict = {}
            for key in formats.SPECIFIED_DAYS_DICT.keys():
                rev_dict[formats.SPECIFIED_DAYS_DICT[key]] = key

            if not translated_str in rev_dict:
                return

            # Each 'mini_list' is in the form [ day_string, time_string ]
            # 'display_str' contains 'time_string', and a translated version of
            #   'day_string'
            # Compile the 'mini_list' for the new entry
            mini_list = [ rev_dict[translated_str], time_str ]

            # Look for a match in the IV
            new_list = []
            for other_list in self.retrieve_val('timetable_list'):
                if other_list[0] != mini_list[0] \
                or other_list[1] != mini_list[1]:
                    new_list.append(other_list)

            # Update the IV and the treeview
            self.edit_dict['timetable_list'] = new_list
            self.setup_start_tab_update_treeview(liststore)


    def on_start_mode_combo_changed(self, combo, label, spinbutton, combo2, \
    label2, combo3, spinbutton2, spinbutton3, button, button2):

        """Called from callback in self.setup_start_tab().

        Sets the IV, and (de)sensitises other widgets.

        Args:

            label (Gtk.Label): A widget to be modified

            spinbutton (Gtk.SpinButton): Another widget to be modified

            combo2 (Gtk.Combo): Another widget to be modified

            label2 (Gtk.Label): Another widget to be modified

            combo3 (Gtk.Combo): Another widget to be modified

            spinbutton2, spinbutton3 (Gtk.SpinButton): Other widgets to be
                modified

            button, button (Gtk.Button): Other widgets to be modified

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.edit_dict['start_mode'] = model[tree_iter][1]

        self.setup_start_tab_update_widgets(
            label,
            spinbutton,
            combo2,
            label2,
            combo3,
            spinbutton2,
            spinbutton3,
            button,
            button2,
        )


    def on_video_index_drag_drop(self, treeview, drag_context, x, y, time):

        """Called from callback in self.setup_media_tab().

        Override the usual Gtk handler, and allow
        self.on_video_index_drag_data_received() to collect the results of the
        drag procedure.

        Args:

            treeview (Gtk.TreeView): This tab's treeview

            drag_context (GdkX11.X11DragContext): Data from the drag procedure

            x, y (int): Cell coordinates in the treeview

            time (int): A timestamp

        """

        # Must override the usual Gtk handler
        treeview.stop_emission('drag_drop')

        # The second of these lines cause the 'drag-data-received' signal to be
        #   emitted
        target_list = drag_context.list_targets()
        treeview.drag_get_data(drag_context, target_list[-1], time)


    def on_video_index_drag_data_received(self, treeview, drag_context, x, y, \
    selection_data, info, timestamp):

        """Called from callback in self.setup_media_tab().

        Retrieve the media data object being dragged. update the
        media.Scheduled object, and update the treeview itself.

        Args:

            treeview (Gtk.TreeView): This tab's treeview

            drag_context (GdkX11.X11DragContext): Data from the drag procedure

            x, y (int): Cell coordinates in the treeview

            selection_data (Gtk.SelectionData): Data from the dragged row

            info (int): Ignored

            timestamp (int): Ignored

        """

        # Must override the usual Gtk handler
        treeview.stop_emission('drag_data_received')

        # Get the dragged media data object
        old_selection \
        = self.app_obj.main_win_obj.video_index_treeview.get_selection()
        (model, start_iter) = old_selection.get_selected()
        if start_iter is not None:

            drag_dbid = model[start_iter][0]

            # Check the media data object hasn't already been added to the
            #   list, and that is still exists in the media data registry
            media_list = self.retrieve_val('media_list')
            if not drag_dbid in media_list \
            and drag_dbid in self.app_obj.container_reg_dict:

                # (System folders can't be dragged here)
                media_data_obj = self.app_obj.media_reg_dict[drag_dbid]

                if not isinstance(media_data_obj, media.Folder) \
                or not media_data_obj.fixed_flag:

                    media_list.append(drag_dbid)
                    self.edit_dict['media_list'] = media_list

                    self.radiobutton2.set_active(True)

                    # Update the treeview
                    self.setup_media_tab_update_treeview(treeview.get_model())
