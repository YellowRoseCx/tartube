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


class FolderEditWin(GenericEditWin):

    """Python class for an 'edit window' to modify values in a media.Folder
    object.

    Args:

        app_obj (mainapp.TartubeApp): The main application object

        edit_obj (media.Folder): The object whose attributes will be edited in
            this window

    """


    # Standard class methods


    def __init__(self, app_obj, edit_obj):

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Folder properties window starts here.' \
            + ' In the main window, in the Videos tab, right-click a folder' \
            + ' and select Show > Folder properties...'
        )

        Gtk.Window.__init__(self, title=_('Folder properties'))

        if self.is_duplicate(app_obj, edit_obj):
            return

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # The media.Folder object being edited
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
        self.media_type = 'folder'


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

        # Update this media.Channel/media.Playlist in the Video Index
        GObject.timeout_add(
            0,
            self.app_obj.main_win_obj.video_index_update_row_text,
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
        self.setup_statistics_tab()
        if mainapp.HAVE_MATPLOTLIB_FLAG:
            self.setup_history_tab()
        if self.edit_obj == self.app_obj.fixed_recent_folder:
            self.setup_recent_tab()


    def setup_general_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'General' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Folder properties > General'
        )

        tab, grid = self.add_notebook_tab(_('_General'))

        # General properties
        self.add_label(grid,
            '<u>' + _('General properties') + '</u>',
            0, 0, 3, 1,
        )

        # The first sets of widgets are shared by multiple edit windows
        self.add_container_properties(grid)
        self.add_destination_properties(grid)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 7, 3, 1)

        checkbutton = self.add_checkbutton(grid2,
            _('Don\'t add videos to Tartube\'s database'),
            'dl_no_db_flag',
            0, 0, 2, 1,
        )
        checkbutton.set_sensitive(False)

        checkbutton2 = self.add_checkbutton(grid2,
            _('Always simulate download of videos'),
            'dl_sim_flag',
            0, 1, 2, 1,
        )
        checkbutton2.set_sensitive(False)

        checkbutton3 = self.add_checkbutton(grid2,
            _('Disable checking/downloading'),
            'dl_disable_flag',
            0, 2, 2, 1,
        )
        checkbutton3.set_sensitive(False)

        checkbutton4 = self.add_checkbutton(grid2,
            _('This folder is marked as a favourite'),
            'fav_flag',
            0, 3, 2, 1,
        )
        checkbutton4.set_sensitive(False)

        checkbutton5 = self.add_checkbutton(grid2,
            _('This folder is hidden'),
            'hidden_flag',
            2, 0, 1, 1,
        )
        checkbutton5.set_sensitive(False)

        checkbutton6 = self.add_checkbutton(grid2,
            _('This folder can\'t be deleted by the user'),
            'fixed_flag',
            2, 1, 1, 1,
        )
        checkbutton6.set_sensitive(False)

        checkbutton7 = self.add_checkbutton(grid2,
            _('This is a system-controlled folder'),
            'priv_flag',
            2, 2, 1, 1,
        )
        checkbutton7.set_sensitive(False)

        checkbutton8 = self.add_checkbutton(grid2,
            _('All contents deleted when Tartube shuts down'),
            'temp_flag',
            2, 3, 1, 1,
        )
        checkbutton8.set_sensitive(False)

        label = self.add_label(grid2,
            _('Restrictions:'),
            0, 4, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid2,
            None,
            1, 4, 1, 1,
        )
        entry.set_editable(False)
        if self.edit_obj.restrict_mode == 'full':
            entry.set_text(_('Can only contain videos'))
        elif self.edit_obj.restrict_mode == 'partial':
            entry.set_text(_('Can contain folders and videos'))
        else:
            entry.set_text(_('Can contain anything'))


    def setup_statistics_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Statistics' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Folder properties > Statistics'
        )

        tab, grid = self.add_notebook_tab(_('_Statistics'))
        grid_width = 4

        # Statistics
        self.add_label(grid,
            '<u>' + _('Statistics') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            _('This folder contains:'),
            0, 1, grid_width, 1,
        )

        self.add_label(grid,
            _('Videos'),
            0, 2, 1, 1,
        )

        entry = self.add_entry(grid,
            None,
            1, 2, 1, 1,
        )
        entry.set_editable(False)

        self.add_label(grid,
            _('Downloaded'),
            0, 3, 1, 1,
        )

        entry2 = self.add_entry(grid,
            None,
            1, 3, 1, 1,
        )
        entry2.set_editable(False)

        self.add_label(grid,
            _('Other'),
            0, 4, 1, 1,
        )

        entry3 = self.add_entry(grid,
            None,
            1, 4, 1, 1,
        )
        entry3.set_editable(False)

        self.add_label(grid,
            _('Channels'),
            2, 2, 1, 1,
        )

        entry4 = self.add_entry(grid,
            None,
            3, 2, 1, 1,
        )
        entry4.set_editable(False)

        self.add_label(grid,
            _('Playlists'),
            2, 3, 1, 1,
        )

        entry5 = self.add_entry(grid,
            None,
            3, 3, 1, 1,
        )
        entry5.set_editable(False)

        self.add_label(grid,
            _('Sub-folders'),
            2, 4, 1, 1,
        )

        entry6 = self.add_entry(grid,
            None,
            3, 4, 1, 1,
        )
        entry6.set_editable(False)

        # Initialise the entries
        self.setup_statistics_tab_recalculate(
            entry,
            entry2,
            entry3,
            entry4,
            entry5,
            entry6,
        )

        button = Gtk.Button()
        grid.attach(button, 3, 5, 1, 1)
        button.set_label(_('Recalculate'))
        button.connect(
            'clicked',
            self.on_button_recalculate_clicked,
            entry,
            entry2,
            entry3,
            entry4,
            entry5,
            entry6,
        )


    def setup_statistics_tab_recalculate(self, entry, entry2, entry3, entry4,
    entry5, entry6):

        """Called by self.setup_statistics_tab and
        .on_recalculate_button_clicked().

        Args:

            entry, entry2, entry3, entry4, entry5, entry6 (Gtk.Entry): The
                entry boxes to update

        """

        # Get number of videos, channels, playlists and sub-folders
        total_count, video_count, channel_count, playlist_count, \
        folder_count = self.edit_obj.count_descendants( [0, 0, 0, 0, 0] )

        # Calculate downloaded/not downloaded videos
        dl_count = 0
        not_dl_count = 0
        child_list = self.edit_obj.compile_all_videos( [] )

        for video_obj in child_list:

            if video_obj.dl_flag:
                dl_count += 1
            else:
                not_dl_count += 1

        entry.set_text(str(video_count))
        entry2.set_text(str(dl_count))
        entry3.set_text(str(not_dl_count))
        entry4.set_text(str(channel_count))
        entry5.set_text(str(playlist_count))
        entry6.set_text(str(folder_count))


    def setup_history_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'History' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Folder properties > History'
        )

        tab, grid = self.add_notebook_tab(_('_History'))
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


    def setup_recent_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Recent Videos' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Folder properties > Recent videos. Only' \
            + ' visible for the \'Recent videos\' folder'
        )

        tab, grid = self.add_notebook_tab(_('_Recent Videos'))
        grid_width = 2

        # Recent videos
        self.add_label(grid,
            '<u>' + _('Recent videos') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' \
            + _('When videos are checked/downloaded, older downloaded videos' \
            ' are removed from this folder',
            ) + '</i>',
            0, 1, grid_width, 1,
        )

        radiobutton = self.add_radiobutton(grid,
            None,
            _('Empty the whole folder'),
            None,
            None,
            0, 2, grid_width, 1,
        )
        # (Signal connect appears below)

        radiobutton2 = self.add_radiobutton(grid,
            radiobutton,
            _('Remove downloaded videos after days'),
            None,
            None,
            0, 3, 1, 1,
        )

        spinbutton = self.add_spinbutton(grid,
            1,
            14,
            1,
            None,
            1, 3, 1, 1,
        )
        # (Signal connect appears below)

        if not self.app_obj.fixed_recent_folder_days:
            spinbutton.set_sensitive(False)
        else:
            radiobutton2.set_active(True)
            spinbutton.set_value(
                self.app_obj.fixed_recent_folder_days,
            )

        # (Signal connects from above)
        radiobutton.connect(
            'toggled',
            self.on_radiobutton_toggled,
            spinbutton,
        )

        spinbutton.connect(
            'value-changed',
            self.on_spinbutton_changed,
        )


#   def setup_download_options_tab():       # Inherited from GenericConfigWin


    # (Support functions)


#   def add_combos_for_graphs():            # Inherited from GenericConfigWin


#   def plot_graph():                       # Inherited from GenericConfigWin


    # Callback class methods


#   def on_button_apply_options_clicked():  # Inherited from GenericConfigWin


#   def on_button_edit_options_clicked():   # Inherited from GenericConfigWin


#   def on_button_remove_options_clicked(): # Inherited from GenericConfigWin


#   def on_button_draw_graph_clicked():     # Inherited from GenericConfigWin


    def on_button_recalculate_clicked(self, button, entry, entry2, entry3,
    entry4, entry5, entry6):

        """Called from callback in self.setup_statistics_tab().

        Recalculates the number of child media data objects, and updates the
        entry boxes.

        Args:

            button (Gtk.Button): The widget clicked

            entry, entry2, entry3, entry4, entry5, entry6 (Gtk.Entry): The
                entry boxes to update

        """

        self.setup_statistics_tab_recalculate(
            entry,
            entry2,
            entry3,
            entry4,
            entry5,
            entry6,
        )


    def on_radiobutton_toggled(self, radiobutton, spinbutton):

        """Called from callback in self.setup_recent_tab().

        (De)sensitises the spinbutton, depending on which radiobutton is
        selected. Then updates the IV.

        Args:

            radiobutton (Gtk.RadioButton): The clicked widget

            spinbutton (Gtk.SpinButton): Another widget to modify

        """

        if radiobutton.get_active():

            spinbutton.set_sensitive(False)
            self.app_obj.set_fixed_recent_folder_days(0)

        else:

            spinbutton.set_sensitive(True)
#            spinbutton.set_value(self.app_obj.fixed_recent_folder_days)
            self.app_obj.set_fixed_recent_folder_days(
                int(spinbutton.get_value())
            )


    def on_spinbutton_changed(self, spinbutton):

        """Called from callback in self.setup_recent_tab().

        Sets the time after which videos are removed from the fixed 'Recent
        Videos' folder.

        Args:

            spinbutton (Gtk.SpinButton): The clicked widget

        """

        self.app_obj.set_fixed_recent_folder_days(
            int(spinbutton.get_value()),
        )
