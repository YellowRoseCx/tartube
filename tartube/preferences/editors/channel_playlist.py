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


class ChannelPlaylistEditWin(GenericEditWin):

    """Python class for an 'edit window' to modify values in a media.Channel or
    media.Playlist object.

    Args:

        app_obj (mainapp.TartubeApp): The main application object

        edit_obj (media.Channel, media.Playlist): The object whose attributes
            will be edited in this window

    """


    # Standard class methods


    def __init__(self, app_obj, edit_obj):

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Channel/playlist properties window starts' \
            + ' here. In the main window, in the Videos tab, right-click' \
            + ' a channel or playlist and select Show > Channel' \
            + ' properties... of Show > Playlist properties...'
        )

        if isinstance(edit_obj, media.Channel):
            media_type = 'channel'
            win_title = _('Channel properties')
        else:
            media_type = 'playlist'
            win_title = _('Playlist properties')

        Gtk.Window.__init__(self, title=win_title)

        if self.is_duplicate(app_obj, edit_obj):
            return

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # The media.Channel or media.Playlist object being edited
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
        # (Widgets used in the Playlists tab)
        self.playlists_liststore = None         # Gtk.ListStore

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

        # String set to 'channel' or 'playlist'
        self.media_type = media_type


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
        if self.edit_obj.enhanced:
            self.setup_assoc_playlist_tab()
        if mainapp.HAVE_MATPLOTLIB_FLAG:
            self.setup_history_tab()
        self.setup_rss_feed_tab()
        self.setup_errors_warnings_tab()


    def setup_general_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'General' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Channel properties > General'
        )

        tab, grid = self.add_notebook_tab(_('_General'))

        # General properties
        self.add_label(grid,
            '<u>' + _('General properties') + '</u>',
            0, 0, 3, 1,
        )

        # The first sets of widgets are shared by multiple edit windows
        self.add_container_properties(grid)
        self.add_source_properties(grid)
        self.add_destination_properties(grid)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 7, 3, 1)

        if self.media_type == 'channel':
            string = _(
                'Don\'t add videos in this channel to Tartube\'s database',
            )
        else:
            string = _(
                'Don\'t add videos in this playlist to Tartube\'s database',
            )

        checkbutton = self.add_checkbutton(grid2,
            string,
            'dl_no_db_flag',
            0, 0, 1, 1,
        )
        checkbutton.set_sensitive(False)

        if self.media_type == 'channel':
            string = _('Always simulate download of videos in this channel')
        else:
            string = _('Always simulate download of videos in this playlist')

        checkbutton2 = self.add_checkbutton(grid2,
            string,
            'dl_sim_flag',
            0, 1, 1, 1,
        )
        checkbutton2.set_sensitive(False)

        if self.media_type == 'channel':
            string = _('Disable checking/downloading for this channel')
        else:
            string = _('Disable checking/downloading for this playlist')

        checkbutton3 = self.add_checkbutton(grid2,
            string,
            'dl_disable_flag',
            0, 2, 1, 1,
        )
        checkbutton3.set_sensitive(False)

        if self.media_type == 'channel':
            string = _('This channel is marked as a favourite')
        else:
            string = _('This playlist is marked as a favourite')

        checkbutton4 = self.add_checkbutton(grid2,
            string,
            'fav_flag',
            0, 3, 1, 1,
        )
        checkbutton4.set_sensitive(False)

        self.add_label(grid2,
            _('Total videos'),
            1, 0, 1, 1,
        )
        entry = self.add_entry(grid2,
            'vid_count',
            2, 0, 1, 1,
        )
        entry.set_editable(False)
        entry.set_width_chars(8)
        entry.set_hexpand(False)

        self.add_label(grid2,
            _('New videos'),
            1, 1, 1, 1,
        )
        entry2 = self.add_entry(grid2,
            'new_count',
            2, 1, 1, 1,
        )
        entry2.set_editable(False)
        entry2.set_width_chars(8)
        entry2.set_hexpand(False)

        self.add_label(grid2,
            _('Favourite videos'),
            1, 2, 1, 1,
        )
        entry3 = self.add_entry(grid2,
            'fav_count',
            2, 2, 1, 1,
        )
        entry3.set_editable(False)
        entry3.set_width_chars(8)
        entry3.set_hexpand(False)

        self.add_label(grid2,
            _('Downloaded videos'),
            1, 3, 1, 1,
        )
        entry4 = self.add_entry(grid2,
            'dl_count',
            2, 3, 1, 1,
        )
        entry4.set_editable(False)
        entry4.set_width_chars(8)
        entry4.set_hexpand(False)


#   def setup_download_options_tab():   # Inherited from GenericConfigWin


    def setup_assoc_playlist_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Associated Playlists' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Channel properties > Associated playlists.' \
            + ' Only visible for the compatible websites (e.g. YouTube)',
        )

        tab, grid = self.add_notebook_tab(_('Associated _Playlists'))
        grid_width = 4

        # Associated playlists
        self.add_label(grid,
            '<u>' + _('Associated playlists') + '</u>',
            0, 0, grid_width, 1,
        )

        self.add_label(grid,
            '<i>' + _(
                'When a video is associated with a playlist, the playlist\'s' \
                + ' ID is stored here',
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
            [ _('Playlist ID'), _('Playlist Title') ],
        ):
            renderer_text = Gtk.CellRendererText()
            column_text = Gtk.TreeViewColumn(
                column_title,
                renderer_text,
                text=i,
            )
            treeview.append_column(column_text)
            column_text.set_resizable(True)

        self.playlists_liststore = Gtk.ListStore(str, str)
        treeview.set_model(self.playlists_liststore)

        # Initialise the list
        self.setup_assoc_playlist_tab_update_treeview()

        # Strip of widgets at the bottom
        checkbutton = self.add_checkbutton(grid,
            _('Set the channel as the download destination'),
            None,
            0, 3, 2, 1,
        )
        if self.media_type != 'channel':
            checkbutton.set_sensitive(False)

        button = Gtk.Button(_('Add selected playlist'))
        grid.attach(button, 2, 3, 1, 1)
        button.connect(
            'clicked',
            self.on_add_assoc_playlist_button_clicked,
            treeview,
            checkbutton,
        )

        button2 = Gtk.Button(_('Add all playlists'))
        grid.attach(button2, 3, 3, 1, 1)
        button2.connect(
            'clicked',
            self.on_all_assoc_playlist_button_clicked,
            checkbutton,
        )

        button3 = Gtk.Button(_('Download preferences'))
        grid.attach(button3, 0, 4, 1, 1)
        button3.connect(
            'clicked',
            self.on_assoc_playlist_prefs_button_clicked,
        )

        button4 = Gtk.Button(_('Clear list'))
        grid.attach(button4, 1, 4, 1, 1)
        button4.connect(
            'clicked',
            self.on_clear_assoc_playlist_button_clicked,
        )

        # (This button works even if mainapp.TartubeApp.store_playlist_id_flag
        #   is False)
        button5 = Gtk.Button(_('Reset list using metadata file'))
        grid.attach(button5, 2, 4, 2, 1)
        button5.connect(
            'clicked',
            self.on_reset_assoc_playlist_button_clicked,
        )


    def setup_assoc_playlist_tab_update_treeview(self):

        """ Called by self.setup_assoc_playlist_tab().

        Fills or updates the treeview.
        """

        self.playlists_liststore.clear()

        # Add each playlist to the treeview, one row at a time
        # (The treeview needs to be sorted by its second column, corresponding
        #   to values in the IV's key-value pairs)
        sort_list = sorted(
            self.edit_obj.playlist_id_dict.items(), key=lambda x:x[1],
        )
        sort_dict = dict(sort_list)

        for playlist_id in sort_dict.keys():

            playlist_title = self.edit_obj.playlist_id_dict[playlist_id]

            if playlist_title is None:
                self.playlists_liststore.append(
                    [ playlist_id, '<' + _('Unnamed playlist') + '>' ],
                )

            else:
                self.playlists_liststore.append(
                    [ playlist_id, playlist_title ],
                )


    def setup_history_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'History' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Channel properties > History'
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


    def setup_rss_feed_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'RSS feed' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Channel properties > RSS feed'
        )

        tab, grid = self.add_notebook_tab(_('_RSS feed'))
        grid_width = 3

        # RSS feed (used to detect livestreams)
        self.add_label(grid,
            '<u>' + _('RSS feed (used to detect livestreams)') + '</u>',
            0, 0, grid_width, 1,
        )

        if self.media_type == 'channel':
            msg = _(
                'If Tartube cannot detect the channel\'s RSS feed, you' \
                + ' can enter the URL here',
            )
        else:
            msg = _(
                'If Tartube cannot detect the playlist\'s RSS feed, you' \
                + ' can enter the URL here',
            )

        self.add_label(grid,
            '<i>' + msg + '</i>',
            0, 1, grid_width, 1,
        )

        entry = self.add_entry(grid,
            None,
            0, 2, grid_width, 1,
        )
        entry.set_editable(True)
        entry.set_hexpand(True)
        if self.edit_obj.rss:
            entry.set_text(self.edit_obj.rss)
        entry.connect('changed', self.on_rss_entry_changed)

        button = Gtk.Button(_('Open in web browser'))
        grid.attach(button, 0, 3, 1, 1)
        button.set_hexpand(False)
        button.connect('clicked', self.on_open_feed_button_clicked)

        button2 = Gtk.Button(_('Set to default feed'))
        grid.attach(button2, 1, 3, 1, 1)
        button2.set_hexpand(False)
        if not self.edit_obj.source or not self.edit_obj.enhanced:
            button2.set_sensitive(False)
        button2.connect('clicked', self.on_set_feed_button_clicked, entry)

        button3 = Gtk.Button(_('Reset feed'))
        grid.attach(button3, 2, 3, 1, 1)
        button3.set_hexpand(False)
        button3.connect('clicked', self.on_reset_feed_button_clicked, entry)

        self.add_label(grid,
            '<i>' + _(
                'N.B. The <b>Set to default feed</b> button won\'t work if' \
                + ' the RSS feed was obtained from video metadata',
            ) + '</i>',
            0, 4, grid_width, 1,
        )


    def setup_errors_warnings_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Errors / Warnings' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Channel properties > Errors / Warnings'
        )

        tab, grid = self.add_notebook_tab(_('_Errors / Warnings'))

        # Errors / Warnings
        self.add_label(grid,
            '<u>' + _('Errors / Warnings') + '</u>',
            0, 0, 1, 1,
        )

        if self.media_type == 'channel':
            string = _(
                'Error messages produced the last time this channel was' \
                + ' checked/downloaded',
            )
        else:
            string = _(
                'Error messages produced the last time this playlist was' \
                + ' checked/downloaded',
            )

        self.add_label(grid,
            '<i>' + string + '</i>',
            0, 1, 1, 1,
        )

        textview, textbuffer = self.add_textview(grid,
            'error_list',
            0, 2, 1, 1,
        )
        textview.set_editable(False)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_can_focus(False)

        if self.media_type == 'channel':
            string = _(
                'Warning messages produced the last time this channel was' \
                + ' checked/downloaded',
            )
        else:
            string = _(
                'Warning messages produced the last time this playlist was' \
                + ' checked/downloaded',
            )

        self.add_label(grid,
            '<i>' + string + '</i>',
            0, 3, 1, 1,
        )

        textview2, textbuffer2 = self.add_textview(grid,
            'warning_list',
            0, 4, 1, 1,
        )
        textview2.set_editable(False)
        textview2.set_wrap_mode(Gtk.WrapMode.WORD)
        textview2.set_can_focus(False)


    # (Support functions)


#   def add_combos_for_graphs():            # Inherited from GenericConfigWin


#   def plot_graph():                       # Inherited from GenericConfigWin


    # Callback class methods


    def on_add_assoc_playlist_button_clicked(self, button, treeview, \
    checkbutton):

        """Called from a callback in self.setup_assoc_playlist_tab().

        The selected associated playlist is added to Tartube's database (if
        possible).

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeVies): The treeview displaying the associated
                playlist list

            checkbutton (Gtk.CheckButton): Another widget to check

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Channel properties > Associated playlists'
        )

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:

            return

        playlist_id = model[this_iter][0]
        playlist_title = model[this_iter][1]

        # If 'playlist_title' is specified, then only create a playlist if no
        #   other container has the same URL or name
        # If 'playlist_title' is not specified, the just check for duplicate
        #   URLs; if a new playlist is created, create an artificial title
        if playlist_title != '' \
        and not self.app_obj.is_container(playlist_title):

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('The name \'{0}\' is already in use').format(playlist_title),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        url = ttutils.convert_enhanced_template_from_json(
            'convert_playlist_list',
            self.edit_obj.enhanced,
            {
                'playlist_id': playlist_id,
                'playlist_title': playlist_title,
            },
        )
        if url is None:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Unable to extrapolate the URL for this playlist'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        for dbid in self.app_obj.container_reg_dict.keys():

            media_data_obj = self.app_obj.media_reg_dict[dbid]
            if not isinstance(media_data_obj, media.Folder) \
            and media_data_obj.source == url:

                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _('The playlist is already in Tartube\'s database'),
                    'error',
                    'ok',
                    self,           # Parent window is this window
                )

                return

        # Name an unnamed playlist
        if playlist_title == '':
            playlist_title \
            = ttutils.find_available_name(self, 'playlist', 1, -1)

        # Create the new playlist, with the same parent as this window's
        #   channel/playlist
        playlist_obj = self.app_obj.add_playlist(
            playlist_title,
            self.edit_obj.parent_obj,       # May be 'None'
            url,
        )
        if not playlist_obj:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Unable to create new playlist'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            return

        else:

            # This window's channel is the download destination for the
            #   playlist, if required
            if checkbutton.get_active():
                playlist_obj.set_master_dbid(self.app_obj, self.edit_obj.dbid)

            # Update the Video Index. The True argument tells the function not
            #   to select the new playlist
            self.app_obj.main_win_obj.video_index_add_row(playlist_obj, True)

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _(
                'Added playlist \'{0}\' to Tartube\'s database',
                ).format(playlist_title),
                'info',
                'ok',
                self,           # Parent window is this window
            )

            return


    def on_all_assoc_playlist_button_clicked(self, button, checkbutton):

        """Called from a callback in self.setup_assoc_playlist_tab().

        All associated playlists are added to Tartube's database (where
        possible).

        Args:

            button (Gtk.Button): The widget clicked

            checkbutton (Gtk.CheckButton): Another widget to check

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' Channel properties > Associated playlists'
        )

        success_count = 0
        fail_count = 0

        if not self.edit_obj.playlist_id_dict:
            # No playlists to add
            return

        # Go through the list of associated playlists, eliminating any which
        #   already exist (duplicate names or duplicate source URLs), and
        #   assigning a name to any unnamed playlist
        for playlist_id in self.edit_obj.playlist_id_dict.keys():

            playlist_title = self.edit_obj.playlist_id_dict[playlist_id]

            if playlist_title != '' \
            and not self.app_obj.is_container(playlist_title):
                fail_count += 1
                continue

            url = ttutils.convert_enhanced_template_from_json(
                'convert_playlist_list',
                self.edit_obj.enhanced,
                {
                    'playlist_id': playlist_id,
                    'playlist_title': playlist_title,
                },
            )
            if url is None:
                continue

            match_flag = False
            for dbid in self.app_obj.container_reg_dict.keys():

                media_data_obj = self.app_obj.media_reg_dict[dbid]
                if not isinstance(media_data_obj, media.Folder) \
                and media_data_obj.source == url:
                    match_flag = True
                    break

            if match_flag:
                fail_count += 1
                continue

            # Name an unnamed playlist
            if playlist_title == '':
                playlist_title = ttutils.find_available_name(
                    self,
                    'playlist',
                    1,
                    -1,
                ),

            # Create the new playlist, with the same parent as this window's
            #   channel/playlist
            playlist_obj = self.app_obj.add_playlist(
                playlist_title,
                self.edit_obj.parent_obj,       # May be 'None'
                url,
            )
            if not playlist_obj:
                fail_count += 1

            else:
                # This window's channel is the download destination for the
                #   playlist, if required
                if checkbutton.get_active():
                    playlist_obj.set_master_dbid(
                        self.app_obj,
                        self.edit_obj.dbid,
                    )

                # Update the Video Index. The True argument tells the function
                #   not to select the new playlist
                self.app_obj.main_win_obj.video_index_add_row(
                    playlist_obj,
                    True,
                )

                success_count += 1

        # Show confirmation
        msg = _('Playlists added: {0}').format(success_count) \
        + '\n' + _('Playlists not added: {0}').format(fail_count)

        self.app_obj.dialogue_manager_obj.show_simple_msg_dialogue(
            msg,
           'info',
           'ok',
            self,           # Parent window is this window
        )

        return


    def on_assoc_playlist_prefs_button_clicked(self, button):

        """Called from a callback in self.setup_assoc_playlist_tab().

        Opens the preferences window to show associated playlist settings.

        Args:

            button (Gtk.Button): The widget clicked

        """

        SystemPrefWin(self.app_obj, 'downloads')


#   def on_button_apply_options_clicked():  # Inherited from GenericConfigWin


#   def on_button_edit_options_clicked():   # Inherited from GenericConfigWin


#   def on_button_remove_options_clicked(): # Inherited from GenericConfigWin


    def on_clear_assoc_playlist_button_clicked(self, button):

        """Called from a callback in self.setup_assoc_playlist_tab().

        Empties the channel/playlist's associated playlist list.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.edit_obj.reset_playlist_id()
        self.setup_assoc_playlist_tab_update_treeview()


    def on_open_feed_button_clicked(self, button):

        """Called from a callback in self.setup_rss_feed_tab().

        Opens the RSS feed in a web browser.

        Args:

            button (Gtk.Button): The widget clicked

        """

        rss = self.retrieve_val('rss')
        if rss:
            ttutils.open_file(self.app_obj, rss)


    def on_reset_assoc_playlist_button_clicked(self, button):

        """Called from a callback in self.setup_assoc_playlist_tab().

        Restores the channel/playlist's associated playlist list, extracting
        playlist IDs from the metadata file of each child video.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.edit_obj.extract_playlist_id(self.app_obj)
        self.setup_assoc_playlist_tab_update_treeview()


    def on_rss_entry_changed(self, entry):

        """Called by callback in self.setup_rss_feed_tab().

        Sets the RSS feed.

        Args:
            entry (Gtk.Entry): The entry box modified

        """

        rss = entry.get_text()
        if rss == '':
            self.edit_dict['rss'] = None
        else:
            self.edit_dict['rss'] = rss


    def on_set_feed_button_clicked(self, button, entry):

        """Called from a callback in self.setup_rss_feed_tab().

        Sets the RSS feed to its expected value.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to modify

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Channel properties > RSS feed'
        )

        rss = self.retrieve_val('rss')
        # Update code won't work if the .rss IV is set
        self.edit_obj.reset_rss()

        # Try to set the RSS feed using the channel/playlist URL
        self.edit_obj.update_rss_from_url(self.retrieve_val('source'))
        # Try to set the RSS feed using a child video, if any
        if not self.edit_obj.rss and self.edit_obj.child_list:

            # Look for the first video whose URL is set, then give up
            for child_obj in self.edit_obj.child_list:
                if child_obj.source:
                    self.edit_obj.update_rss_from_url(child_obj.source)
                    break

        if not self.edit_obj.rss:

            # Failed. Restore the previous value
            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Could not set the RSS feed'),
                'error',
                'ok',
                self,           # Parent window is this window
            )

            if rss:
                entry.set_text(rss)

        else:

            # Succeeded
            entry.set_text(self.edit_obj.rss)


    def on_reset_feed_button_clicked(self, button, entry):

        """Called from a callback in self.setup_rss_feed_tab().

        Resets the RSS feed.

        Args:

            button (Gtk.Button): The widget clicked

            entry (Gtk.Entry): Another widget to modify

        """

        # (Updating the entry sets self.edit_dict)
        entry.set_text('')
