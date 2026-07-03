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


class FFmpegOptionsEditWin(GenericEditWin):

    """Python class for an 'edit window' to modify values in an
    ffmpeg_tartube.FFmpegOptionsManager object.

    Adapted from FFmpeg Command Line Wizard, by AndreKR
        (https://github.com/AndreKR/ffmpeg-command-line-wizard).

    Args:

        app_obj (mainapp.TartubeApp): The main application object

        edit_obj (ffmpeg_tartube.FFmpegOptionsManager): The object whose
            attributes will be edited in this window

        video_list (list): An optional list of media.Video objects. If not
            empty, when the edit window closes, a process operation will
            start, using the FFmpeg options specified by 'edit_obj' to process
            all the videos in the list. If empty, no operation is started; the
            modified FFmpeg options are just updated as normal

    """


    # Standard class methods


    def __init__(self, app_obj, edit_obj, video_list=[]):

        ignore_me = _(
            'TRANSLATOR\'S NOTE: FFmpeg options window starts here.' \
            + ' In the main window, in the Videos tab, right-click a video' \
            + ' and select Special > Process with FFmpeg...'
        )

        Gtk.Window.__init__(self, title=_('FFmpeg options'))

        if self.is_duplicate(app_obj, edit_obj):
            return

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # The ffmpeg_tartube.FFmpegOptionsManager object being edited
        self.edit_obj = edit_obj
        # An optional list of media.Video objects. If not empty, when the edit
        #   window closes, a process operation will start, using the FFmpeg
        #   options specified by 'edit_obj' to process all the videos in the
        #   list. If empty, no operation is started; the modified FFmpeg
        #   options are just updated as normal
        self.video_list = video_list


        # IV list - Gtk widgets
        # ---------------------
        self.grid = None                        # Gtk.Grid
        self.notebook = None                    # Gtk.Notebook
        self.reset_button = None                # Gtk.Button
        self.apply_button = None                # Gtk.Button
        self.ok_button = None                   # Gtk.Button
        self.cancel_button = None               # Gtk.Button
        # (Because of the need to (de)sensitise widgets so often, more of them
        #   than usual have their own IVs)
        # (Name tab)
        self.extra_cmd_string_textview = None   # Gtk.TextView
        self.extra_cmd_string_textbuffer = None # Gtk.TextBuffer
        self.result_textview = None             # Gtk.TextView
        self.results_textbuffer = None          # Gtk.TextBuffer
        # (File tab)
        self.add_end_filename_entry = None      # Gtk.Entry
        self.regex_match_filename_entry = None  # Gtk.Entry
        self.regex_apply_subst_entry = None     # Gtk.Entry
        self.rename_both_flag_checkbutton = None
                                                # Gtk.CheckButton
        self.change_file_ext_entry = None       # Gtk.Entry
        self.delete_original_flag_checkbutton = None
                                                # Gtk.CheckButton
        # (Settings tab)
        self.input_mode_radiobutton = None      # Gtk.RadioButton
        self.input_mode_radiobutton2 = None     # Gtk.RadioButton
        self.audio_flag_checkbutton = None      # Gtk.CheckButton
        self.output_mode_radiobutton = None     # Gtk.RadioButton
        self.output_mode_radiobutton2 = None    # Gtk.RadioButton
        self.output_mode_radiobutton3 = None    # Gtk.RadioButton
        self.output_mode_radiobutton4 = None    # Gtk.RadioButton
        self.output_mode_radiobutton5 = None    # Gtk.RadioButton
        self.output_mode_radiobutton6 = None    # Gtk.RadioButton
        self.h264_grid = None                   # Gtk.Grid
        self.gif_grid = None                    # Gtk.Grid
        self.clip_grid = None                   # Gtk.Grid
        self.slice_grid = None                  # Gtk.Grid
        self.merge_grid = None                  # Gtk.Grid
        self.thumb_grid = None                  # Gtk.Grid
        # (Settings tab, H.264 grid)
        self.audio_bitrate_spinbutton = None    # Gtk.SpinButton
        self.quality_mode_radiobutton = None    # Gtk.RadioButton
        self.quality_mode_radiobutton2 = None   # Gtk.RadioButton
        self.rate_factor_scale = None           # Gtk.Scale
        self.dummy_file_combo = None            # Gtk.ComboBox
        self.patience_preset_combo = None       # Gtk.ComboBox
        self.gpu_encoding_combo = None          # Gtk.ComboBox
        self.hw_accel_combo = None              # Gtk.ComboBox
        # (Settings tab, GIF grid)
        self.palette_mode_radiobutton = None    # Gtk.RadioButton
        self.palette_mode_radiobutton2 = None   # Gtk.RadioButton
        # (Settings tab, split grid)
        self.split_mode_radiobutton = None      # Gtk.RadioButton
        self.split_mode_radiobutton2 = None     # Gtk.RadioButton
        self.split_mode_liststore = None        # Gtk.ListStore
        self.start_stamp_entry = None           # Gtk.Entry
        self.stop_stamp_entry = None            # Gtk.Entry
        self.clip_title_entry = None            # Gtk.Entry
        self.add_timestamp_button = None        # Gtk.Button
        self.delete_timestamp_button = None     # Gtk.Button
        self.show_prefs_button = None           # Gtk.Button
        self.clear_timestamp_button = None      # Gtk.Button
        # (Settings tab, slice grid)
        self.slice_mode_radiobutton = None      # Gtk.RadioButton
        self.slice_mode_radiobutton2 = None     # Gtk.RadioButton
        self.slice_mode_liststore = None        # Gtk.ListStore
        self.category_combo = None              # Gtk.ComboBox
        self.action_combo = None                # Gtk.ComboBox
        self.slice_start_entry = None           # Gtk.Entry
        self.slice_stop_entry = None            # Gtk.Entry
        self.add_slice_button = None            # Gtk.Button
        self.delete_slice_button = None         # Gtk.Button
        self.show_settings_button = None        # Gtk.Button
        self.clear_slice_button = None          # Gtk.Button
        # (Optimise tab)
        self.seek_flag_checkbutton = None       # Gtk.CheckButton
        self.tuning_film_flag_checkbutton = None
                                                # Gtk.CheckButton
        self.tuning_animation_flag_checkbutton = None
                                                # Gtk.CheckButton
        self.tuning_grain_flag_checkbutton = None
                                                # Gtk.CheckButton
        self.tuning_still_image_flag_checkbutton = None
                                                # Gtk.CheckButton
        self.tuning_fast_decode_flag_checkbutton = None
                                                # Gtk.CheckButton
        self.profile_flag_checkbutton = None    # Gtk.CheckButton
        self.fast_start_flag_checkbutton = None # Gtk.CheckButton
        self.tuning_zero_latency_flag_checkbutton = None
                                                # Gtk.CheckButton
        self.limit_flag_checkbutton = None      # Gtk.CheckButton
        self.limit_mbps_spinbutton = None       # Gtk.SpinButton
        self.limit_buffer_spinbutton = None     # Gtk.SpinButton
        # (Clips tab)
        self.simple_split_mode_checkbutton = None
                                                # Gtk.CheckButton
        self.simple_split_mode_radiobutton = None
                                                # Gtk.RadioButton
        self.simple_split_mode_radiobutton2 = None
                                                # Gtk.RadioButton
        self.simple_split_mode_liststore = None # Gtk.ListStore
        self.simple_start_stamp_entry = None
                                                # Gtk.Entry
        self.simple_stop_stamp_entry = None     # Gtk.Entry
        self.simple_clip_title_entry = None     # Gtk.Entry
        self.simple_add_timestamp_button = None # Gtk.Button
        self.simple_delete_timestamp_button = None
                                                # Gtk.Button
        self.simple_show_prefs_button = None    # Gtk.Button
        self.simple_clear_timestamp_button = None
                                                # Gtk.Button
        # (Slices tab)
        self.simple_slice_mode_checkbutton = None
                                                # Gtk.CheckButton
        self.simple_slice_mode_radiobutton = None
                                                # Gtk.RadioButton
        self.simple_slice_mode_radiobutton2 = None
                                                # Gtk.RadioButton
        self.simple_slice_mode_liststore = None # Gtk.ListStore
        self.simple_category_combo = None       # Gtk.ComboBox
        self.simple_action_combo = None         # Gtk.ComboBox
        self.simple_slice_start_entry = None    # Gtk.Entry
        self.simple_slice_stop_entry = None     # Gtk.Entry
        self.simple_show_settings_button = None # Gtk.Button
        # (Videox tab)
        self.video_liststore = None             # Gtk.ListStore

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
        #   in ffmpeg_tartube.FFmpegOptionsManager.options_dict, rather than
        #   corresponding directly to attributes in the
        #   ffmpeg_tartube.FFmpegOptionsManager object
        # Because of that, we use our own .apply_changes() and .retrieve_val()
        #   functions, rather than relying on the generic functions
        # Key-value pairs are added to this dictionary whenever the user
        #   makes a change (so if no changes are made when the window is
        #   closed, the dictionary will still be empty)
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


    def apply_changes(self, apply_button_flag=False):

        """Called by self.on_button_ok_clicked() and
        self.on_button_apply_clicked().

        Any changes the user has made are temporarily stored in self.edit_dict.
        Apply to those changes to the object being edited.

        In this edit window we apply changes to self.edit_obj.options_dict
        (rather than to self.edit_obj's attributes directly, as in the generic
        function.)

        Args:

            apply_button_flag (bool): True when self.apply_button was clicked,
                False when self.ok_button was clicked. When True, we do not
                start a process operation

        """

        # For 'change_file_ext', remove the initial . (e.g. in '.mp4', if
        #   specified
        if 'change_file_ext' in self.edit_dict:
            self.edit_dict['change_file_ext'] = re.sub(
                r'^\.',
                '',
                self.edit_dict['change_file_ext'],
            )

        # Apply any changes the user has made
        for key in self.edit_dict.keys():

            if key in self.edit_obj.options_dict:
                self.edit_obj.options_dict[key] = self.edit_dict[key]

        # The name can also be updated, if it has been changed (but it the
        #   entry was blank, keep the old name)
        if 'name' in self.edit_dict \
        and self.edit_dict['name'] != '':
            self.edit_obj.name = self.edit_dict['name']

        # The changes can now be cleared
        self.edit_dict = {}

        # If a list of videos was supplied, start a process operation
        if self.video_list and not apply_button_flag:

            # Check that every media.Video object still exists, eliminating any
            #   that don't
            mod_list = []
            for video_obj in self.video_list:

                # (Special case: 'dummy' video objects (those downloaded in the
                #   Classic Mode tab) use different IVs)
                if video_obj.dummy_flag \
                or (
                    video_obj.dbid in self.app_obj.media_reg_dict \
                    and self.app_obj.media_reg_dict[video_obj.dbid] \
                    == video_obj
                ):
                    mod_list.append(video_obj)

            if mod_list:

                self.app_obj.process_manager_start(
                    self.edit_obj,
                    mod_list,
                )


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

        elif name == 'uid' or name == 'name':

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
                405,
                'Unrecognised property name \'' + name + '\'',
            )


    # (Setup tabs)


    def setup_tabs(self):

        """Called by self.setup(), .on_button_apply_clicked() and
        .on_button_reset_clicked().

        Sets up the tabs for this edit window.
        """

        self.setup_name_tab()
        self.setup_file_tab()

        if not self.app_obj.simple_ffmpeg_options_flag:
            self.setup_settings_tab()
            self.setup_optimise_tab()
        else:
            self.setup_clips_tab()
            self.setup_slices_tab()

        self.setup_videos_tab()

        # Unusual step: if a list of media.Video objects to be processed has
        #   been supplied, use a different label for the OK button
        if self.video_list:

            self.ok_button.set_label(_('Process files'))
            self.ok_button.set_tooltip_text(
                _('Process the files with FFmpeg'),
            )
            self.ok_button.get_child().set_width_chars(15)


    def setup_name_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Name' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: FFmpeg options > Name'
        )

        tab, grid = self.add_notebook_tab(_('_Name'))
        grid_width = 4

        self.add_label(grid,
            _('Name for these FFmpeg options'),
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

        # (To avoid messing up the neat format of the rows above and below, add
        #   a secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 1, grid_width, 1)

        self.add_label(grid2,
            _('Extra command line options (e.g. --help)'),
            0, 0, 1, 1,
        )

        checkbutton = self.add_checkbutton(grid2,
            _('Use these options exclusively'),
            'extra_override_flag',
            1, 0, 2, 1,
        )

        self.extra_cmd_string_textview, \
        self.extra_cmd_string_textbuffer = self.add_textview(grid,
            'extra_cmd_string',
            0, 2, grid_width, 1,
        )

        self.add_label(grid,
            _('System command, based on all FFmpeg options in this window:'),
            0, 3, grid_width, 1,
        )

        self.result_textview, self.results_textbuffer = self.add_textview(grid,
            None,
            0, 4, grid_width, 1,
        )
        self.result_textview.set_editable(False)
        self.result_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.result_textview.set_can_focus(False)
        # (Set the system command, as it stands)
        self.update_system_cmd()

        if self.app_obj.simple_options_flag:
            frame = self.add_pixbuf(grid,
                'hand_right_large',
                0, 5, 1, 1,
            )
            frame.set_hexpand(False)

        else:
            frame = self.add_pixbuf(grid,
                'hand_left_large',
                0, 5, 1, 1,
            )
            frame.set_hexpand(False)

        button = Gtk.Button()
        grid.attach(button, 1, 5, (grid_width - 1), 1)
        if not self.app_obj.simple_ffmpeg_options_flag:
            button.set_label(_('Show fewer FFmpeg options'))
        else:
            button.set_label(_('Show more FFmpeg options'))
        button.connect('clicked', self.on_simple_options_clicked)

        frame2 = self.add_pixbuf(grid,
            'copy_large',
            0, 6, 1, 1,
        )
        frame2.set_hexpand(False)

        button2 = Gtk.Button(
            _('Import current FFmpeg options into this window'),
        )
        grid.attach(button2, 1, 6, (grid_width - 1), 1)
        button2.connect('clicked', self.on_clone_options_clicked)
        if self.edit_obj == self.app_obj.ffmpeg_options_obj:
            # No point cloning the current options manager into itself
            button2.set_sensitive(False)

        frame3 = self.add_pixbuf(grid,
            'warning_large',
            0, 7, 1, 1,
        )
        frame3.set_hexpand(False)

        button3 = Gtk.Button(
            _('Completely reset all FFmpeg options to their default values'),
        )
        grid.attach(button3, 1, 7, (grid_width - 1), 1)
        button3.connect('clicked', self.on_reset_options_clicked)


    def setup_file_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'File' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: FFmpeg options > File'
        )

        tab, grid = self.add_notebook_tab(_('_File'))

        self.add_label(grid,
            _('Add to end of filename:'),
            0, 0, 1, 1,
        )

        self.add_end_filename_entry = self.add_entry(grid,
            'add_end_filename',
            1, 0, 1, 1,
        )

        self.add_label(grid,
            _('If regex matches filename:'),
            0, 1, 1, 1,
        )

        self.regex_match_filename_entry = self.add_entry(grid,
            None,
            1, 1, 1, 1,
        )
        self.regex_match_filename_entry.set_text(
            self.retrieve_val('regex_match_filename'),
        )
        # (Signal connect appears below)

        self.add_label(grid,
            _('...then apply substitution:'),
            0, 2, 1, 1,
        )

        self.regex_apply_subst_entry = self.add_entry(grid,
            'regex_apply_subst',
            1, 2, 1, 1,
        )
        if self.retrieve_val('regex_match_filename') == '':
            self.regex_apply_subst_entry.set_sensitive(False)

        self.rename_both_flag_checkbutton = self.add_checkbutton(grid,
            _(
            'If the video/audio file is renamed, also rename the thumbnail' \
            + ' (but not vice-versa)',
            ),
            'rename_both_flag',
            0, 3, 2, 1,
        )
        if self.retrieve_val('add_end_filename') == '' \
        and self.retrieve_val('regex_match_filename') == '':
            self.rename_both_flag_checkbutton.set_sensitive(False)

        self.add_label(grid,
            _('Change file extension:'),
            0, 4, 1, 1,
        )

        self.change_file_ext_entry = self.add_entry(grid,
            None,
            1, 4, 1, 1,
        )
        self.change_file_ext_entry.set_text(
            self.retrieve_val('change_file_ext'),
        )
        # (Signal connect appears below)

        self.delete_original_flag_checkbutton = self.add_checkbutton(grid,
            _('After changing the file extension, delete the original file'),
            'delete_original_flag',
            0, 5, 1, 1,
        )
        if self.retrieve_val('change_file_ext') == '':
            self.delete_original_flag_checkbutton.set_sensitive(False)

        # (Signal connects from above)
        self.regex_match_filename_entry.connect(
            'changed',
            self.on_regex_match_filename_entry_changed,
        )

        self.change_file_ext_entry.connect(
            'changed',
            self.on_change_file_ext_entry_changed,
        )

        # (De)sensitise all of these widgets, depending on the value of the
        #   'output_mode' setting
        if self.retrieve_val('output_mode') == 'split':
            self.setup_file_tab_set_sensitive(False)
        else:
            self.setup_file_tab_set_sensitive(True)


    def setup_file_tab_set_sensitive(self, sens_flag):

        """Called by self.setup_file_tab() and various callbacks.

        (De)sensitises all widgets in the tab, as required.

        Args:

            sens_flag (bool): True to sensitise widgets, False to desensitise
                them

        """

        self.add_end_filename_entry.set_sensitive(sens_flag)
        self.regex_match_filename_entry.set_sensitive(sens_flag)

        if self.retrieve_val('regex_match_filename') == '':
            self.regex_apply_subst_entry.set_sensitive(False)
        else:
            self.regex_apply_subst_entry.set_sensitive(sens_flag)

        if self.retrieve_val('add_end_filename') == '' \
        and self.retrieve_val('regex_match_filename') == '':
            self.rename_both_flag_checkbutton.set_sensitive(False)
        else:
            self.rename_both_flag_checkbutton.set_sensitive(sens_flag)

        if self.retrieve_val('output_mode') == 'gif':
            self.change_file_ext_entry.set_sensitive(False)
        else:
            self.change_file_ext_entry.set_sensitive(sens_flag)

        if self.retrieve_val('change_file_ext') == '':
            self.delete_original_flag_checkbutton.set_sensitive(False)
        else:
            self.delete_original_flag_checkbutton.set_sensitive(sens_flag)


    def setup_settings_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Settings' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: FFmpeg options > Settings (to make hidden' \
            ' tabs visible, click the \'Show more FFmpeg options\' button' \
            ' in the Name tab'
        )

        tab, grid = self.add_notebook_tab(_('_Settings'))
        grid_width = 7
        self.settings_grid = grid

        # Source
        label = self.add_label(grid,
            '<u>' + _('Source') + '</u>',
            0, 0, 1, 1,
        )
        label.set_hexpand(False)

        self.input_mode_radiobutton = self.add_radiobutton(grid,
            None,
            _('Downloaded video/audio'),
            None,
            None,
            1, 0, 4, 1,
        )
        self.input_mode_radiobutton.set_hexpand(False)
        # (Signal connect appears below)

        self.audio_flag_checkbutton = self.add_checkbutton(grid,
            _('with audio'),
            None,
            5, 0, 1, 1,
        )
        self.audio_flag_checkbutton.set_hexpand(False)
        if self.retrieve_val('audio_flag'):
            self.audio_flag_checkbutton.set_active(True)
        if self.retrieve_val('input_mode') != 'video':
            self.audio_flag_checkbutton.set_sensitive(False)
        # (Signal connect appears below)

        self.input_mode_radiobutton2 = self.add_radiobutton(grid,
            self.input_mode_radiobutton,
            _('Thumbnail'),
            None,
            None,
            6, 0, 1, 1,
        )
        self.input_mode_radiobutton2.set_hexpand(False)
        if self.retrieve_val('input_mode') == 'thumb':
            self.input_mode_radiobutton2.set_active(True)
        # (Signal connect appears below)

        # Output
        label2 = self.add_label(grid,
            '<u>' + _('Output') + '</u>',
            0, 1, 1, 1,
        )
        label2.set_hexpand(False)

        self.output_mode_radiobutton = self.add_radiobutton(grid,
            None,
            'H.264',
            None,
            None,
            1, 1, 1, 1,
        )
        self.output_mode_radiobutton.set_hexpand(False)
        # (Signal connect appears below)

        self.output_mode_radiobutton2 = self.add_radiobutton(grid,
            self.output_mode_radiobutton,
            'GIF',
            None,
            None,
            2, 1, 1, 1,
        )
        self.output_mode_radiobutton2.set_hexpand(False)
        if self.retrieve_val('output_mode') == 'gif':
            self.output_mode_radiobutton2.set_active(True)
        # (Signal connect appears below)

        self.output_mode_radiobutton3 = self.add_radiobutton(grid,
            self.output_mode_radiobutton2,
            _('Video clip'),
            None,
            None,
            3, 1, 1, 1,
        )
        self.output_mode_radiobutton3.set_hexpand(False)
        if self.retrieve_val('output_mode') == 'split':
            self.output_mode_radiobutton3.set_active(True)
        # (Signal connect appears below)

        self.output_mode_radiobutton4 = self.add_radiobutton(grid,
            self.output_mode_radiobutton3,
            _('Video slice'),
            None,
            None,
            4, 1, 1, 1,
        )
        self.output_mode_radiobutton4.set_hexpand(False)
        if self.retrieve_val('output_mode') == 'slice':
            self.output_mode_radiobutton4.set_active(True)
        # (Signal connect appears below)

        self.output_mode_radiobutton5 = self.add_radiobutton(grid,
            self.output_mode_radiobutton4,
            _('Merge video/audio'),
            None,
            None,
            5, 1, 1, 1,
        )
        self.output_mode_radiobutton5.set_hexpand(False)
        if self.retrieve_val('output_mode') == 'merge':
            self.output_mode_radiobutton5.set_active(True)
        # (Signal connect appears below)

        self.output_mode_radiobutton6 = self.add_radiobutton(grid,
            self.output_mode_radiobutton5,
            _('Thumbnail'),
            None,
            None,
            6, 1, 1, 1,
        )
        self.output_mode_radiobutton6.set_hexpand(False)
        if self.retrieve_val('output_mode') == 'thumb':
            self.output_mode_radiobutton6.set_active(True)
        # (Signal connect appears below)

        # Supplementary grids: one for each 'output_mode'
        # Only one of them is visible at any time (this saves a lot of time
        #   (de)sensitising widgets)
        self.h264_grid = self.setup_settings_tab_h264_grid(2, grid_width)
        self.gif_grid = self.setup_settings_tab_gif_grid(2, grid_width)
        self.clip_grid = self.setup_settings_tab_clip_grid(2, grid_width)
        self.slice_grid = self.setup_settings_tab_slice_grid(2, grid_width)
        self.merge_grid = self.setup_settings_tab_merge_grid(2, grid_width)
        self.thumb_grid = self.setup_settings_tab_thumb_grid(2, grid_width)

        # (Signal connects from above)
        self.input_mode_radiobutton.connect(
            'toggled',
            self.on_input_mode_radiobutton_toggled,
        )
        self.audio_flag_checkbutton.connect(
            'toggled',
            self.on_audio_flag_checkbutton_toggled,
        )
        self.input_mode_radiobutton2.connect(
            'toggled',
            self.on_input_mode_radiobutton_toggled,
        )

        self.output_mode_radiobutton.connect(
            'toggled',
            self.on_output_mode_radiobutton_toggled,
            grid_width,
        )
        self.output_mode_radiobutton2.connect(
            'toggled',
            self.on_output_mode_radiobutton_toggled,
            grid_width,
        )
        self.output_mode_radiobutton3.connect(
            'toggled',
            self.on_output_mode_radiobutton_toggled,
            grid_width,
        )
        self.output_mode_radiobutton4.connect(
            'toggled',
            self.on_output_mode_radiobutton_toggled,
            grid_width,
        )
        self.output_mode_radiobutton5.connect(
            'toggled',
            self.on_output_mode_radiobutton_toggled,
            grid_width,
        )
        self.output_mode_radiobutton6.connect(
            'toggled',
            self.on_output_mode_radiobutton_toggled,
            grid_width,
        )


    def setup_settings_tab_h264_grid(self, row, outer_width):

        """Called by self.setup_settings_tab().

        Creates a supplementary grid, within the tab's outer grid, which can be
        swapped in and out as the 'output_mode' option is changed.

        This supplementary grid is visible when 'output_mode' is 'h264'.

        Args:

            row (int): The row on the tab's outer grid, on which the
                supplementary grid is to be placed

            outer_width (int): The width of the tab's outer grid

        Return values:

            The new Gtk.Grid().

        """

        grid = Gtk.Grid()
        if self.retrieve_val('output_mode') == 'h264':
            self.settings_grid.attach(grid, 0, row, outer_width, 1)
        grid.set_border_width(self.spacing_size)
        grid.set_column_spacing(self.spacing_size)
        grid.set_row_spacing(self.spacing_size)

        inner_width = 3

        self.add_label(grid,
            _('Audio bitrate'),
            0, 0, 1, 1,
        )

        self.audio_bitrate_spinbutton = self.add_spinbutton(grid,
            16, None, 16,
            'audio_bitrate',
            1, 0, 1, 1,
        )
        if self.retrieve_val('input_mode') != 'video' \
        or not self.retrieve_val('audio_flag'):
            self.audio_bitrate_spinbutton.set_sensitive(False)

        label = self.add_label(grid,
            _('How to set the quality') + ' ⓘ',
            0, 1, 1, 1,
        )
        label.set_tooltip_text(
            _(
            'FFmpeg always encodes according to a Rate Factor that specifies' \
            + ' the quality of the result.',
            ) + '\n\n' + _(
            'Instead of directly specifying the Rate Factor, an average bit' \
            + ' rate can be specified. FFmpeg will then determine the' \
            + ' optimal Rate Factor in a first pass.',
            ) + '\n\n' + _(
            'In fact the first pass is only used for determining the Rate' \
            + ' Factor, no other data is carried over into the second pass.',
            ) + '\n\n' + _(
            'Specifying an average bitrate but running only one pass is' \
            + ' possible, but not recommended. FFmpeg would then encode the' \
            + ' beginning of the video with a random Rate Factor and then' \
            + ' change it near the end of the video to eventually reach the' \
            + ' target bitrate.',
            ),
        )

        # N.B. In the original 'FFmpeg command line wizard', the second of this
        #   pair of radiobuttons are disabled (for unknown reasons); here it is
        #   enabled
        self.quality_mode_radiobutton = self.add_radiobutton(grid,
            None,
            _('Manual rate factor'),
            None,
            None,
            1, 1, (inner_width - 1), 1,
        )
        # (Signal connect appears below)

        self.quality_mode_radiobutton2 = self.add_radiobutton(grid,
            self.quality_mode_radiobutton,
            _('Determine from target bitrate (2-Pass)'),
            None,
            None,
            1, 2, (inner_width - 1), 1,
        )
        if self.retrieve_val('quality_mode') == 'abr':
            self.quality_mode_radiobutton2.set_active(True)
        # (Signal connect appears below)

        self.add_label(grid,
            _('Rate factor'),
            0, 3, 1, 1,
        )

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 1, 3, (inner_width - 1), 1)

        label2 = self.add_label(grid2,
            _('Lossless') + '\n' + _('Large file'),
            0, 0, 1, 1,
        )
        label2.set_hexpand(False)

        self.rate_factor_scale = Gtk.Scale().new_with_range(
            Gtk.Orientation.HORIZONTAL,
            0,
            51,
            1,
        )
        grid2.attach(self.rate_factor_scale, 1, 0, 1, 1)
        self.rate_factor_scale.set_draw_value(True)
        self.rate_factor_scale.set_value(
            self.retrieve_val('rate_factor'),
        )
        self.rate_factor_scale.set_hexpand(True)
        if self.retrieve_val('quality_mode') == 'abr':
            self.rate_factor_scale.set_sensitive(False)
        # (Signal connect appears below)

        label3 = self.add_label(grid2,
            _('Bad quality') + '\n' + _('Small file'),
            2, 0, 1, 1,
        )
        label3.set_hexpand(False)
        # (End of the yet another grid)

        label4 = self.add_label(grid,
            _('Name of dummy file') + ' ⓘ',
            0, 4, 1, 1,
        )
        label4.set_tooltip_text(
            _('A dummy file is created during the first pass.'),
        )

        combo_list = [
            [_('Use the output file'), 'output'],
            [_('Dummy'), 'dummy'],
            [_('/dev/null (Linux)'), '/dev/null'],
            [_('NUL (MS Windows)'), 'NUL'],
        ]

        self.dummy_file_combo = self.add_combo_with_data(grid,
            combo_list,
            'dummy_file',
            1, 4, (inner_width - 1), 1,
        )
        if self.retrieve_val('quality_mode') != 'abr':
            self.dummy_file_combo.set_sensitive(False)

        self.add_label(grid,
            _('Patience preset'),
            0, 5, 1, 1,
        )

        combo_list2 = [
            [_('Ultra fast'), 'ultrafast'],
            [_('Super fast'), 'superfast'],
            [_('Very fast'), 'veryfast'],
            [_('Faster'), 'faster'],
            [_('Fast'), 'fast'],
            [_('Medium (default)'), 'medium'],
            [_('Slow (file about 5-10% smaller than medium)'), 'slow'],
            [_('Slower (file about 15% smaller than medium)'), 'slower'],
            [_('Very slow (file about 17% smaller than medium)'), 'veryslow'],
        ]

        self.patience_preset_combo = self.add_combo_with_data(grid,
            combo_list2,
            'patience_preset',
            1, 5, (inner_width - 1), 1,
        )
        self.patience_preset_combo.set_hexpand(False)

        self.add_label(grid,
            _('GPU encoding'),
            0, 6, 1, 1,
        )

        combo_list3 = [
            'libx264', 'libx265', 'h264_amf', 'hevc_amf', 'h264_nvenc',
            'hevc_nvenc',
        ]

        self.gpu_encoding_combo = self.add_combo(grid,
            combo_list3,
            'gpu_encoding',
            1, 6, (inner_width - 1), 1,
        )

        self.add_label(grid,
            _('Hardware acceleration'),
            0, 7, 1, 1,
        )

        combo_list4 = ['none', 'auto', 'vdpau', 'dxva2', 'vaapi', 'qsv']

        self.hw_accel_combo = self.add_combo(grid,
            combo_list4,
            'hw_accel',
            1, 7, (inner_width - 1), 1,
        )

        # (Signal connects from above)
        self.quality_mode_radiobutton.connect(
            'toggled',
            self.on_quality_mode_radiobutton_toggled,
        )
        self.quality_mode_radiobutton2.connect(
            'toggled',
            self.on_quality_mode_radiobutton_toggled,
        )

        self.rate_factor_scale.connect(
            'value-changed',
            self.on_rate_factor_scale_changed,
        )

        return grid


    def setup_settings_tab_gif_grid(self, row, outer_width):

        """Called by self.setup_settings_tab().

        Creates a supplementary grid, within the tab's outer grid, which can be
        swapped in and out as the 'output_mode' option is changed.

        This supplementary grid is visible when 'output_mode' is 'gif'.

        Args:

            row (int): The row on the tab's outer grid, on which the
                supplementary grid is to be placed

            outer_width (int): The width of the tab's outer grid

        Return values:

            The new Gtk.Grid().

        """

        grid = Gtk.Grid()
        if self.retrieve_val('output_mode') == 'gif':
            self.settings_grid.attach(grid, 0, row, outer_width, 1)
        grid.set_border_width(self.spacing_size)
        grid.set_column_spacing(self.spacing_size)
        grid.set_row_spacing(self.spacing_size)

        self.add_label(grid,
            _('Palette:'),
            0, 0, 1, 1,
        )

        self.palette_mode_radiobutton = self.add_radiobutton(grid,
            None,
            _('Faster') + '\n' \
            + _('Uses dithering to a standard palette provided by FFmpeg') \
            + '\n' + _('Can cause dithering artefacts and slight banding'),
            None,
            None,
            1, 0, 1, 1,
        )
        # (Signal connect appears below)

        self.palette_mode_radiobutton2 = self.add_radiobutton(grid,
            self.palette_mode_radiobutton,
            _('Better') + '\n' \
            + _('Determines an optimized palette for the video') + '\n' \
            + _('Uses two passes and a temporary file for the palette'),
            None,
            None,
            1, 1, 1, 1,
        )
        if self.retrieve_val('palette_mode') == 'better':
            self.palette_mode_radiobutton2.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        self.palette_mode_radiobutton.connect(
            'toggled',
            self.on_palette_mode_radiobutton_toggled,
        )
        self.palette_mode_radiobutton2.connect(
            'toggled',
            self.on_palette_mode_radiobutton_toggled,
        )

        return grid


    def setup_settings_tab_clip_grid(self, row, outer_width):

        """Called by self.setup_settings_tab().

        Creates a supplementary grid, within the tab's outer grid, which can be
        swapped in and out as the 'output_mode' option is changed.

        This supplementary grid is visible when 'output_mode' is 'split'.

        Args:

            row (int): The row on the tab's outer grid, on which the
                supplementary grid is to be placed

            outer_width (int): The width of the tab's outer grid

        Return values:

            The new Gtk.Grid().

        """

        grid = Gtk.Grid()
        if self.retrieve_val('output_mode') == 'split':
            self.settings_grid.attach(grid, 0, row, outer_width, 1)
        grid.set_border_width(self.spacing_size)
        grid.set_column_spacing(self.spacing_size)
        grid.set_row_spacing(self.spacing_size)

        grid_width = 4

        self.split_mode_radiobutton = self.add_radiobutton(grid,
            None,
            _('Split videos using their own timestamps'),
            None,
            None,
            0, 0, 1, 1,
        )
        # (Signal connect appears below)

        self.split_mode_radiobutton2 = self.add_radiobutton(grid,
            self.split_mode_radiobutton,
            _('Split videos using these timestamps'),
            None,
            None,
            1, 0, 1, 1,
        )
        if self.retrieve_val('split_mode') == 'custom':
            self.split_mode_radiobutton2.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        self.split_mode_radiobutton.connect(
            'toggled',
            self.on_split_mode_radiobutton_toggled,
        )
        self.split_mode_radiobutton2.connect(
            'toggled',
            self.on_split_mode_radiobutton_toggled,
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

        self.split_mode_liststore = Gtk.ListStore(str, str, str)
        treeview.set_model(self.split_mode_liststore)

        # Initialise the list
        self.setup_settings_tab_update_clip_treeview()

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 2, grid_width, 1)

        # Strip of widgets at the bottom
        label = self.add_label(grid2,
            _('Start timestamp (e.g. 15:29)'),
            0, 0, 1, 1,
        )
        label.set_hexpand(False)

        if self.retrieve_val('split_mode') == 'video':
            custom_flag = False
        else:
            custom_flag = True

        self.start_stamp_entry = self.add_entry(grid2,
            None,
            1, 0, 1, 1,
        )
        self.start_stamp_entry.set_width_chars(12)
        self.start_stamp_entry.set_hexpand(False)
        if not custom_flag:
            self.start_stamp_entry.set_sensitive(False)

        label2 = self.add_label(grid2,
            _('Stop timestamp (optional)'),
            2, 0, 1, 1,
        )
        label2.set_hexpand(False)

        self.stop_stamp_entry = self.add_entry(grid2,
            None,
            3, 0, 1, 1,
        )
        self.stop_stamp_entry.set_width_chars(12)
        self.stop_stamp_entry.set_hexpand(False)
        if not custom_flag:
            self.stop_stamp_entry.set_sensitive(False)

        label3 = self.add_label(grid2,
            _('Clip title (optional)'),
            0, 1, 1, 1,
        )
        label3.set_hexpand(False)

        self.clip_title_entry = self.add_entry(grid2,
            None,
            1, 1, (grid_width - 1), 1,
        )
        self.clip_title_entry.set_hexpand(True)
        if not custom_flag:
            self.clip_title_entry.set_sensitive(False)

        self.add_timestamp_button = Gtk.Button(_('Add timestamp'))
        grid2.attach(self.add_timestamp_button, 0, 2, 1, 1)
        self.add_timestamp_button.connect(
            'clicked',
            self.on_add_timestamp_clicked,
        )
        if not custom_flag:
            self.add_timestamp_button.set_sensitive(False)

        self.delete_timestamp_button = Gtk.Button(_('Delete timestamp'))
        grid2.attach(self.delete_timestamp_button, 1, 2, 1, 1)
        self.delete_timestamp_button.connect(
            'clicked',
            self.on_delete_timestamp_clicked,
            treeview,
        )
        if not custom_flag:
            self.delete_timestamp_button.set_sensitive(False)

        self.show_prefs_button = Gtk.Button(_('Clip preferences'))
        grid2.attach(self.show_prefs_button, 2, 2, 1, 1)
        self.show_prefs_button.connect(
            'clicked',
            self.on_clip_prefs_clicked,
        )

        self.clear_timestamp_button = Gtk.Button(_('Clear list'))
        grid2.attach(self.clear_timestamp_button, 3, 2, 1, 1)
        self.clear_timestamp_button.connect(
            'clicked',
            self.on_clear_timestamp_clicked,
        )
        if not custom_flag:
            self.clear_timestamp_button.set_sensitive(False)

        return grid


    def setup_settings_tab_slice_grid(self, row, outer_width):

        """Called by self.setup_settings_tab().

        Creates a supplementary grid, within the tab's outer grid, which can be
        swapped in and out as the 'output_mode' option is changed.

        This supplementary grid is visible when 'output_mode' is 'slice'.

        Args:

            row (int): The row on the tab's outer grid, on which the
                supplementary grid is to be placed

            outer_width (int): The width of the tab's outer grid

        Return values:

            The new Gtk.Grid().

        """

        grid = Gtk.Grid()
        if self.retrieve_val('output_mode') == 'slice':
            self.settings_grid.attach(grid, 0, row, outer_width, 1)
        grid.set_border_width(self.spacing_size)
        grid.set_column_spacing(self.spacing_size)
        grid.set_row_spacing(self.spacing_size)

        grid_width = 4

        self.slice_mode_radiobutton = self.add_radiobutton(grid,
            None,
            _('Use the videos\' own slice data'),
            None,
            None,
            0, 0, 1, 1,
        )
        # (Signal connect appears below)

        self.slice_mode_radiobutton2 = self.add_radiobutton(grid,
            self.slice_mode_radiobutton,
            _('Use this slice data'),
            None,
            None,
            1, 0, 1, 1,
        )
        if self.retrieve_val('slice_mode') == 'custom':
            self.slice_mode_radiobutton2.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        self.slice_mode_radiobutton.connect(
            'toggled',
            self.on_slice_mode_radiobutton_toggled,
        )
        self.slice_mode_radiobutton2.connect(
            'toggled',
            self.on_slice_mode_radiobutton_toggled,
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

        self.slice_mode_liststore = Gtk.ListStore(str, str, str, str)
        treeview.set_model(self.slice_mode_liststore)

        # Initialise the list
        self.setup_settings_tab_update_slice_treeview()

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 2, grid_width, 1)

        # Strip of widgets at the bottom
        label = self.add_label(grid2,
            _('Category'),
            0, 0, 1, 1,
        )
        label.set_hexpand(False)

        if self.retrieve_val('slice_mode') == 'video':
            custom_flag = False
        else:
            custom_flag = True

        self.category_combo = self.add_combo(grid2,
            formats.SPONSORBLOCK_CATEGORY_LIST,
            None,
            1, 0, 1, 1,
        )
        self.category_combo.set_active(0)
        if not custom_flag:
            self.category_combo.set_sensitive(False)

        label2 = self.add_label(grid2,
            _('Action type'),
            2, 0, 1, 1,
        )
        label2.set_hexpand(False)

        self.action_combo = self.add_combo(grid2,
            formats.SPONSORBLOCK_ACTION_LIST,
            None,
            3, 0, 1, 1,
        )
        self.action_combo.set_active(0)
        if not custom_flag:
            self.action_combo.set_sensitive(False)

        label3 = self.add_label(grid2,
            _('Start (timestamp or seconds)'),
            0, 1, 1, 1,
        )
        label3.set_hexpand(False)

        self.slice_start_entry = self.add_entry(grid2,
            None,
            1, 1, 1, 1,
        )
        if not custom_flag:
            self.slice_start_entry.set_sensitive(False)

        label4 = self.add_label(grid2,
            _('Stop (optional)'),
            2, 1, 1, 1,
        )
        label4.set_hexpand(False)

        self.slice_stop_entry = self.add_entry(grid2,
            None,
            3, 1, 1, 1,
        )
        if not custom_flag:
            self.slice_stop_entry.set_sensitive(False)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid3 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

        self.add_slice_button = Gtk.Button(_('Add slice'))
        grid3.attach(self.add_slice_button, 0, 0, 1, 1)
        self.add_slice_button.set_hexpand(True)
        self.add_slice_button.connect(
            'clicked',
            self.on_add_slice_clicked,
        )
        if not custom_flag:
            self.add_slice_button.set_sensitive(False)

        self.delete_slice_button = Gtk.Button(_('Delete sliuce'))
        grid3.attach(self.delete_slice_button, 1, 0, 1, 1)
        self.delete_slice_button.set_hexpand(True)
        self.delete_slice_button.connect(
            'clicked',
            self.on_delete_slice_clicked,
            treeview,
        )
        if not custom_flag:
            self.delete_slice_button.set_sensitive(False)

        self.show_settings_button = Gtk.Button(_('SponsorBlock settings'))
        grid3.attach(self.show_settings_button, 2, 0, 1, 1)
        self.show_settings_button.set_hexpand(True)
        self.show_settings_button.connect(
            'clicked',
            self.on_slice_settings_clicked,
        )

        self.clear_slice_button = Gtk.Button(_('Clear list'))
        grid3.attach(self.clear_slice_button, 3, 0, 1, 1)
        self.clear_slice_button.set_hexpand(True)
        self.clear_slice_button.connect(
            'clicked',
            self.on_clear_slice_clicked,
        )
        if not custom_flag:
            self.clear_slice_button.set_sensitive(False)

        return grid


    def setup_settings_tab_update_clip_treeview(self):

        """ Called by self.setup_settings_tab_clip_grid().

        Fills or updates the treeview.
        """

        self.split_mode_liststore.clear()

        # Add each timestamp/clip title to the treeview, one row at a time
        for mini_list in self.retrieve_val('split_list'):

            start_stamp = mini_list[0]

            if mini_list[1] is None:
                stop_stamp = ''
            else:
                stop_stamp = mini_list[1]

            if mini_list[2] is None:
                clip_title = ''
            else:
                clip_title = mini_list[1]

            self.split_mode_liststore.append(
                [ start_stamp, stop_stamp, clip_title ],
            )


    def setup_settings_tab_update_slice_treeview(self):

        """ Called by self.setup_settings_tab_slice_grid().

        Fills or updates the treeview.
        """

        self.slice_mode_liststore.clear()

        # Add slice data to the treeview, one row at a time
        for mini_dict in self.retrieve_val('slice_list'):

            self.slice_mode_liststore.append(
                [
                    mini_dict['category'],
                    mini_dict['action'],
                    str(mini_dict['start_time']),
                    str(mini_dict['stop_time']),
                ],
            )


    def setup_settings_tab_merge_grid(self, row, outer_width):

        """Called by self.setup_settings_tab().

        Creates a supplementary grid, within the tab's outer grid, which can be
        swapped in and out as the 'output_mode' option is changed.

        This supplementary grid is visible when 'output_mode' is 'merge'.

        Args:

            row (int): The row on the tab's outer grid, on which the
                supplementary grid is to be placed

            outer_width (int): The width of the tab's outer grid

        Return values:

            The new Gtk.Grid().

        """

        grid = Gtk.Grid()
        if self.retrieve_val('output_mode') == 'merge':
            self.settings_grid.attach(grid, 0, row, outer_width, 1)
        grid.set_border_width(self.spacing_size)
        grid.set_column_spacing(self.spacing_size)
        grid.set_row_spacing(self.spacing_size)

        self.add_label(grid,
            '<i>' + _(
                'This merges a video and audio file with the same name' \
                + ' into a single video file,\nusing the extension' \
                + ' specified in the File tab',
            ) + '</i>',
            0, 0, 1, 1,
        )

        return grid


    def setup_settings_tab_thumb_grid(self, row, outer_width):

        """Called by self.setup_settings_tab().

        Creates a supplementary grid, within the tab's outer grid, which can be
        swapped in and out as the 'output_mode' option is changed.

        This supplementary grid is visible when 'output_mode' is 'thumb'.

        Args:

            row (int): The row on the tab's outer grid, on which the
                supplementary grid is to be placed

            outer_width (int): The width of the tab's outer grid

        Return values:

            The new Gtk.Grid().

        """

        grid = Gtk.Grid()
        if self.retrieve_val('output_mode') == 'thumb':
            self.settings_grid.attach(grid, 0, row, outer_width, 1)
        grid.set_border_width(self.spacing_size)
        grid.set_column_spacing(self.spacing_size)
        grid.set_row_spacing(self.spacing_size)

        self.add_label(grid,
            '<i>' + _(
                'The thumbnail\'s format can be changed in the File tab',
            ) + '</i>',
            0, 0, 1, 1,
        )

        return grid


    def setup_optimise_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Optimisations' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: FFmpeg options > Optimisations'
        )

        tab, grid = self.add_notebook_tab(_('_Optimisations'))
        grid_width = 2

        self.seek_flag_checkbutton = self.add_checkbutton(grid,
            _(
                'Optimise for fast seeking (shorter keyframe interval, about' \
                + ' 10% larger file)',
            ),
            'seek_flag',
            0, 0, grid_width, 1,
        )

        self.tuning_film_flag_checkbutton = self.add_checkbutton(grid,
            _('Input video is a high-quality movie'),
            'tuning_film_flag',
            0, 1, grid_width, 1,
        )

        self.tuning_animation_flag_checkbutton = self.add_checkbutton(grid,
            _('Input video is an animated movie'),
            'tuning_animation_flag',
            0, 2, grid_width, 1,
        )

        self.tuning_grain_flag_checkbutton = self.add_checkbutton(grid,
            _('Input video contains film grain'),
            'tuning_grain_flag',
            0, 3, grid_width, 1,
        )

        self.tuning_still_image_flag_checkbutton = self.add_checkbutton(grid,
            _('Input video is an image slideshow'),
            'tuning_still_image_flag',
            0, 4, grid_width, 1,
        )

        self.tuning_fast_decode_flag_checkbutton = self.add_checkbutton(grid,
            _('Optimise for really weak CPU playback devices'),
            'tuning_fast_decode_flag',
            0, 5, grid_width, 1,
        )

        self.profile_flag_checkbutton = self.add_checkbutton(grid,
            _(
                'Optimise for really old devices (requires rate factor' \
                + ' above 0)',
            ),
            'profile_flag',
            0, 6, grid_width, 1,
        )
        if not self.retrieve_val('rate_factor'):
            self.profile_flag_checkbutton.set_sensitive(False)

        self.fast_start_flag_checkbutton = self.add_checkbutton(grid,
            _(
                'Move headers to beginning of file (so it can play while' \
                + ' still downloading)',
            ),
            'fast_start_flag',
            0, 7, grid_width, 1,
        )

        self.tuning_zero_latency_flag_checkbutton = self.add_checkbutton(grid,
            _('Fast encoding and low latency streaming'),
            'tuning_zero_latency_flag',
            0, 8, grid_width, 1,
        )

        self.limit_flag_checkbutton = self.add_checkbutton(grid,
            _('Limit bitrate (Mbit/s)'),
            None,
            0, 9, 1, 1,
        )
        if self.retrieve_val('limit_flag'):
            self.limit_flag_checkbutton.set_active(True)
        # (Signal connect appears below)

        self.limit_mbps_spinbutton = self.add_spinbutton(grid,
            0, None, 0.2,
            'limit_mbps',
            1, 9, 1, 1,
        )
        if not self.retrieve_val('limit_flag'):
            self.limit_mbps_spinbutton.set_sensitive(False)

        self.add_label(grid,
            '          ' + _('Assuming a receiving buffer (seconds)'),
            0, 10, 1, 1,
        )

        self.limit_buffer_spinbutton = self.add_spinbutton(grid,
            0, None, 0.2,
            'limit_buffer',
            1, 10, 1, 1,
        )
        if not self.retrieve_val('limit_flag'):
            self.limit_buffer_spinbutton.set_sensitive(False)

        # (De)sensitise all of these widgets, depending on the value of the
        #   'output_mode' setting
        if self.retrieve_val('output_mode') == 'h264':
            self.setup_optimise_tab_set_sensitive(True)
        else:
            self.setup_optimise_tab_set_sensitive(False)

        # (Signal connects from above)
        self.limit_flag_checkbutton.connect(
            'toggled',
            self.on_limit_flag_checkbutton_toggled,
        )


    def setup_clips_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Clips' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: FFmpeg options > Clips'
        )

        tab, grid = self.add_notebook_tab(_('_Clips'))
        grid_width = 2

        output_mode = self.retrieve_val('output_mode')
        split_mode = self.retrieve_val('split_mode')

        # N.B. I tried moving the equivalent code from
        #   self.setup_settings_tab_clip_grid() into a function, that could
        #   also be called from here, but that created too many complications
        # However, both calling functions will use the same set of callbacks

        self.simple_split_mode_checkbutton = self.add_checkbutton(grid,
            _('Split the video(s) to create video clips'),
            None,
            0, 0, 1, 1,
        )
        if output_mode == 'split':
            self.simple_split_mode_checkbutton.set_active(True)
        # (Signal connect appears below)

        self.simple_split_mode_radiobutton = self.add_radiobutton(grid,
            None,
            _('Split videos using their own timestamps'),
            None,
            None,
            1, 0, 1, 1,
        )
        if output_mode != 'split':
            self.simple_split_mode_radiobutton.set_sensitive(False)
        # (Signal connect appears below)

        self.simple_split_mode_radiobutton2 = self.add_radiobutton(grid,
            self.simple_split_mode_radiobutton,
            _('Split videos using these timestamps'),
            None,
            None,
            1, 1, 1, 1,
        )
        if output_mode != 'split':
            self.simple_split_mode_radiobutton2.set_sensitive(False)
        if split_mode == 'custom':
            self.simple_split_mode_radiobutton2.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        self.simple_split_mode_checkbutton.connect(
            'toggled',
            self.on_simple_split_toggled,
        )
        self.simple_split_mode_radiobutton.connect(
            'toggled',
            self.on_split_mode_radiobutton_toggled,
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

        self.simple_split_mode_liststore = Gtk.ListStore(str, str, str)
        treeview.set_model(self.simple_split_mode_liststore)

        # Initialise the list
        self.setup_clips_tab_update_treeview()

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

        # Strip of widgets at the bottom
        label = self.add_label(grid2,
            _('Start timestamp (e.g. 15:29)'),
            0, 0, 1, 1,
        )
        label.set_hexpand(False)

        if split_mode == 'video':
            custom_flag = False
        else:
            custom_flag = True

        self.simple_start_stamp_entry = self.add_entry(grid2,
            None,
            1, 0, 1, 1,
        )
        self.simple_start_stamp_entry.set_width_chars(12)
        self.simple_start_stamp_entry.set_hexpand(False)
        if not custom_flag:
            self.simple_start_stamp_entry.set_sensitive(False)

        label2 = self.add_label(grid2,
            _('Stop timestamp (optional)'),
            2, 0, 1, 1,
        )
        label2.set_hexpand(False)

        self.simple_stop_stamp_entry = self.add_entry(grid2,
            None,
            3, 0, 1, 1,
        )
        self.simple_stop_stamp_entry.set_width_chars(12)
        self.simple_stop_stamp_entry.set_hexpand(False)
        if not custom_flag:
            self.simple_stop_stamp_entry.set_sensitive(False)

        label3 = self.add_label(grid2,
            _('Clip title (optional)'),
            0, 1, 1, 1,
        )
        label3.set_hexpand(False)

        self.simple_clip_title_entry = self.add_entry(grid2,
            None,
            1, 1, (grid_width - 1), 1,
        )
        self.simple_clip_title_entry.set_hexpand(True)
        if not custom_flag:
            self.simple_clip_title_entry.set_sensitive(False)

        self.simple_add_timestamp_button = Gtk.Button(_('Add timestamp'))
        grid2.attach(self.simple_add_timestamp_button, 0, 2, 1, 1)
        self.simple_add_timestamp_button.connect(
            'clicked',
            self.on_add_timestamp_clicked,
        )
        if not custom_flag:
            self.simple_add_timestamp_button.set_sensitive(False)

        self.simple_delete_timestamp_button = Gtk.Button(_('Delete timestamp'))
        grid2.attach(self.simple_delete_timestamp_button, 1, 2, 1, 1)
        self.simple_delete_timestamp_button.connect(
            'clicked',
            self.on_delete_timestamp_clicked,
            treeview,
        )
        if not custom_flag:
            self.simple_delete_timestamp_button.set_sensitive(False)

        self.simple_show_prefs_button = Gtk.Button(_('Clip preferences'))
        grid2.attach(self.simple_show_prefs_button, 2, 2, 1, 1)
        self.simple_show_prefs_button.connect(
            'clicked',
            self.on_clip_prefs_clicked,
        )

        self.simple_clear_timestamp_button = Gtk.Button(_('Clear list'))
        grid2.attach(self.simple_clear_timestamp_button, 3, 2, 1, 1)
        self.simple_clear_timestamp_button.connect(
            'clicked',
            self.on_clear_timestamp_clicked,
        )
        if not custom_flag:
            self.simple_clear_timestamp_button.set_sensitive(False)


    def setup_clips_tab_update_treeview(self):

        """ Called by self.setup_clips_tab().

        Fills or updates the treeview.
        """

        self.simple_split_mode_liststore.clear()

        # Add each timestamp/title to the treeview, one row at a time
        for mini_list in self.retrieve_val('split_list'):

            start_stamp = mini_list[0]

            if mini_list[1] is None:
                stop_stamp = ''
            else:
                stop_stamp = mini_list[1]

            if mini_list[2] is None:
                clip_title = ''
            else:
                clip_title = mini_list[1]

            self.simple_split_mode_liststore.append(
                [ start_stamp, stop_stamp, clip_title ],
            )


    def setup_slices_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Slices' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: FFmpeg options > Slices'
        )

        tab, grid = self.add_notebook_tab(_('_Slices'))
        grid_width = 2

        output_mode = self.retrieve_val('output_mode')
        slice_mode = self.retrieve_val('split_mode')

        self.simple_slice_mode_checkbutton = self.add_checkbutton(grid,
            _('Remove slices from the video(s)'),
            None,
            0, 0, 1, 1,
        )
        if output_mode == 'slice':
            self.simple_slice_mode_checkbutton.set_active(True)
        # (Signal connect appears below)

        self.simple_slice_mode_radiobutton = self.add_radiobutton(grid,
            None,
            _('Use the videos\' own slice data'),
            None,
            None,
            1, 0, 1, 1,
        )
        if output_mode != 'slice':
            self.simple_slice_mode_radiobutton.set_sensitive(False)
        # (Signal connect appears below)

        self.simple_slice_mode_radiobutton2 = self.add_radiobutton(grid,
            self.simple_slice_mode_radiobutton,
            _('Use this slice data'),
            None,
            None,
            1, 1, 1, 1,
        )
        if output_mode != 'slice':
            self.simple_slice_mode_radiobutton2.set_sensitive(False)
        if slice_mode == 'custom':
            self.simple_slice_mode_radiobutton2.set_active(True)
        # (Signal connect appears below)

        # (Signal connects from above)
        self.simple_slice_mode_checkbutton.connect(
            'toggled',
            self.on_simple_slice_toggled,
        )
        self.simple_slice_mode_radiobutton.connect(
            'toggled',
            self.on_slice_mode_radiobutton_toggled,
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

        self.simple_slice_mode_liststore = Gtk.ListStore(str, str, str, str)
        treeview.set_model(self.simple_slice_mode_liststore)

        # Initialise the list
        self.setup_slices_tab_update_treeview()

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, 0, 3, grid_width, 1)

        # Strip of widgets at the bottom
        label = self.add_label(grid2,
            _('Category'),
            0, 0, 1, 1,
        )
        label.set_hexpand(False)

        if slice_mode == 'video':
            custom_flag = False
        else:
            custom_flag = True

        self.simple_category_combo = self.add_combo(grid2,
            formats.SPONSORBLOCK_CATEGORY_LIST,
            None,
            1, 0, 1, 1,
        )
        self.simple_category_combo.set_active(0)
        if not custom_flag:
            self.simple_category_combo.set_sensitive(False)

        label2 = self.add_label(grid2,
            _('Action type'),
            2, 0, 1, 1,
        )
        label2.set_hexpand(False)

        self.simple_action_combo = self.add_combo(grid2,
            formats.SPONSORBLOCK_ACTION_LIST,
            None,
            3, 0, 1, 1,
        )
        self.simple_action_combo.set_active(0)
        if not custom_flag:
            self.simple_action_combo.set_sensitive(False)

        label3 = self.add_label(grid2,
            _('Start (timestamp or seconds)'),
            0, 1, 1, 1,
        )
        label3.set_hexpand(False)

        self.simple_slice_start_entry = self.add_entry(grid2,
            None,
            1, 1, 1, 1,
        )
        if not custom_flag:
            self.simple_slice_start_entry.set_sensitive(False)

        label4 = self.add_label(grid2,
            _('Stop (optional)'),
            2, 1, 1, 1,
        )
        label4.set_hexpand(False)

        self.simple_slice_stop_entry = self.add_entry(grid2,
            None,
            3, 1, 1, 1,
        )
        if not custom_flag:
            self.simple_slice_stop_entry.set_sensitive(False)

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid3 = self.add_secondary_grid(grid, 0, 4, grid_width, 1)

        self.simple_add_slice_button = Gtk.Button(_('Add slice'))
        grid3.attach(self.simple_add_slice_button, 0, 2, 1, 1)
        self.simple_add_slice_button.set_hexpand(True)
        self.simple_add_slice_button.connect(
            'clicked',
            self.on_add_slice_clicked,
        )
        if not custom_flag:
            self.simple_add_slice_button.set_sensitive(False)

        self.simple_delete_slice_button = Gtk.Button(_('Delete slice'))
        grid3.attach(self.simple_delete_slice_button, 1, 2, 1, 1)
        self.simple_delete_slice_button.set_hexpand(True)
        self.simple_delete_slice_button.connect(
            'clicked',
            self.on_delete_slice_clicked,
            treeview,
        )
        if not custom_flag:
            self.simple_delete_slice_button.set_sensitive(False)

        self.simple_show_settings_button \
        = Gtk.Button(_('SponsorBlock settings'))
        grid3.attach(self.simple_show_settings_button, 2, 2, 1, 1)
        self.simple_show_settings_button.set_hexpand(True)
        self.simple_show_settings_button.connect(
            'clicked',
            self.on_slice_settings_clicked,
        )

        self.simple_clear_slice_button = Gtk.Button(_('Clear list'))
        grid3.attach(self.simple_clear_slice_button, 3, 2, 1, 1)
        self.simple_clear_slice_button.set_hexpand(True)
        self.simple_clear_slice_button.connect(
            'clicked',
            self.on_clear_slice_clicked,
        )
        if not custom_flag:
            self.simple_clear_slice_button.set_sensitive(False)


    def setup_slices_tab_update_treeview(self):

        """ Called by self.setup_slices_tab().

        Fills or updates the treeview.
        """

        self.simple_slice_mode_liststore.clear()

        # Add slice data to the treeview, one row at a time
        for mini_dict in self.retrieve_val('slice_list'):

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

            self.simple_slice_mode_liststore.append(
                [ category, action, str(start_time), str(stop_time) ],
            )


    def setup_optimise_tab_set_sensitive(self, sens_flag):

        """Called by self.setup_optimise_tab() and various callbacks.

        (De)sensitises all widgets in the tab, as required.

        Args:

            sens_flag (bool): True to sensitise widgets, False to desensitise
                them

        """

        self.seek_flag_checkbutton.set_sensitive(sens_flag)
        self.tuning_film_flag_checkbutton.set_sensitive(sens_flag)
        self.tuning_animation_flag_checkbutton.set_sensitive(sens_flag)
        self.tuning_grain_flag_checkbutton.set_sensitive(sens_flag)
        self.tuning_still_image_flag_checkbutton.set_sensitive(sens_flag)
        self.tuning_fast_decode_flag_checkbutton.set_sensitive(sens_flag)

        if not self.retrieve_val('rate_factor'):
            self.profile_flag_checkbutton.set_sensitive(False)
        else:
            self.profile_flag_checkbutton.set_sensitive(sens_flag)

        self.fast_start_flag_checkbutton.set_sensitive(sens_flag)

        self.limit_flag_checkbutton.set_sensitive(sens_flag)
        self.tuning_zero_latency_flag_checkbutton.set_sensitive(sens_flag)

        if not self.retrieve_val('limit_flag'):
            self.limit_mbps_spinbutton.set_sensitive(False)
        else:
            self.limit_mbps_spinbutton.set_sensitive(sens_flag)

        if not self.retrieve_val('limit_flag'):
            self.limit_buffer_spinbutton.set_sensitive(False)
        else:
            self.limit_buffer_spinbutton.set_sensitive(sens_flag)


    def setup_videos_tab(self):

        """Called by self.setup_tabs().

        Sets up the 'Videos' tab.
        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: FFmpeg options > Videos'
        )

        tab, grid = self.add_notebook_tab(_('_Videos'))
        grid_width = 2

        # List of videos to be processed
        self.add_label(grid,
            '<u>' + _('List of videos to be processed') + '</u>',
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
            [ '#', _('Video'), _('Thumbnail'), _('Name') ]
        ):
            if i == 1 or i == 2:
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

        self.video_liststore = Gtk.ListStore(str, bool, bool, str)
        treeview.set_model(self.video_liststore)

        # Allow drag and drop from the Video Catalogue, or an external
        #   application, hoping to receive full paths to a video/audio file
        #   and/or URLs, which are associated with a media.Video object
        scrolled.connect(
            'drag-data-received',
            self.on_video_drag_data_received,
        )
        # (Without this line, we get Gtk warnings on some systems)
        scrolled.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        # (Continuing)
        scrolled.drag_dest_set_target_list(None)
        scrolled.drag_dest_add_text_targets()

        # Initialise the list
        self.setup_videos_tab_update_treeview()

        # Add editing buttons
        button = Gtk.Button()
        grid.attach(button, 0, 2, 1, 1)
        button.set_label(_('Show video properties and timestamps'))
        button.connect(
            'clicked',
            self.on_video_show_button_clicked,
            treeview,
        )

        button2 = Gtk.Button()
        grid.attach(button2, 1, 2, 1, 1)
        button2.set_label(_('Remove video from list'))
        button2.connect(
            'clicked',
            self.on_video_remove_button_clicked,
            treeview,
        )


    def setup_videos_tab_update_treeview(self):

        """Called by self.setup_videos_tab().

        Fills or updates the treeview.
        """

        self.video_liststore.clear()

        # Sort the video list by .dbid (so the Videos tab looks nice)
        self.video_list.sort(key=lambda x: x.dbid)

        # Add a row for each video in the list
        for video_obj in self.video_list:
            self.setup_videos_tab_add_row(video_obj)


    def setup_videos_tab_add_row(self, video_obj):

        """Called by self.setup_videos_tab_update_treeview().

        Adds a row to the treeview for a specified media.Video object.

        Args:

            video_obj (media.Video): The video to add

        """

        if ttutils.find_thumbnail(self.app_obj, video_obj):
            thumb_flag = True
        else:
            thumb_flag = True

        if video_obj.dummy_flag:

            # Special case: 'dummy' video objects (those downloaded in the
            #   Classic Mode tab) use different IVs
            if video_obj.dummy_path is not None \
            and os.path.isfile(video_obj.dummy_path):
                dl_flag = True
            else:
                dl_flag = False

            self.video_liststore.append(
                [
                    'n/a',
                    dl_flag,
                    thumb_flag,
                    video_obj.dummy_path,
                ],
            )

        else:

            # All other media.Video objects
            self.video_liststore.append(
                [
                    str(video_obj.dbid),
                    video_obj.dl_flag,
                    thumb_flag,
                       video_obj.name,
                ],
            )


    # (Tab support functions)


    def update_system_cmd(self):

        """Called after any widget is manipulated.

        Updates the contents of the textview showing a specimen system command,
        incorporating the modified value.
        """

        # This particular call returns a list inside a tuple, for no obvious
        #   reason (and an identical call from ProcessManager.process_video()
        #   does not)
        # Don't know why, but the FFmpeg system command, as a list, is at
        #   [0][2])
        result_list = self.edit_obj.get_system_cmd(
            self.app_obj,
            None,           # Use a specimen source file
            None,           # ...and specimen timestamps
            None,
            None,
            None,
            self.edit_dict,
        ),

        if not result_list:
            self.results_textbuffer.set_text('')

        else:
            text = ' '.join(result_list[0][2])
            if self.retrieve_val('output_mode') == 'slice':

                # Show the concatenation command on a second line
                concat_list = [
                    self.app_obj.ffmpeg_manager_obj.get_executable(),
                    '-safe',
                    '0',
                    '-f',
                    'concat',
                    '-i',
                    'clips.txt',
                    '-c',
                    'copy',
                    result_list[0][2][-1],      # Path to the output file
                ]

                text += '\n' + ' '.join(concat_list)

            self.results_textbuffer.set_text(text)


    # Callback class methods


    def on_add_slice_clicked(self, button):

        """Called from a callback in self.setup_settings_tab_slice_grid().

        In simple mode, called from a callback in self.setup_slices_tab().

        Adds a new slice to the video's slice list.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' FFmpeg options > Slices'
        )

        if not self.app_obj.simple_ffmpeg_options_flag:

            tree_iter = self.category_combo.get_active_iter()
            model = self.category_combo.get_model()
            category = model[tree_iter][0]

            tree_iter2 = self.action_combo.get_active_iter()
            model2 = self.action_combo.get_model()
            action_type = model2[tree_iter2][0]

            start_time = ttutils.strip_whitespace(
                self.slice_start_entry.get_text(),
            )

            stop_time = ttutils.strip_whitespace(
                self.slice_stop_entry.get_text(),
            )

        else:

            tree_iter = self.simple_category_combo.get_active_iter()
            model = self.simple_category_combo.get_model()
            category = model[tree_iter][0]

            tree_iter2 = self.simple_action_combo.get_active_iter()
            model2 = self.simple_action_combo.get_model()
            action_type = model2[tree_iter2][0]

            start_time = ttutils.strip_whitespace(
                self.simple_slice_start_entry.get_text(),
            )

            stop_time = ttutils.strip_whitespace(
                self.simple_slice_stop_entry.get_text(),
            )

        # Do nothing if specified timestamps aren't valid ('stop_time' is NOT
        #   optional)
        start_time = float(
            ttutils.timestamp_convert_to_seconds(self.app_obj, start_time),
        )

        if stop_time == '':
            stop_time = None
        else:
            stop_time = float(
                ttutils.timestamp_convert_to_seconds(self.app_obj, stop_time),
            )

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

        # Compile the mini-dictionary in the format described by
        #   media.Video.__init__()
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
        slice_list = list(sorted(slice_list, key=lambda x:x['start_time']))
        self.edit_dict['slice_list'] = slice_list

        # Show changes, and empty entry boxes
        if not self.app_obj.simple_ffmpeg_options_flag:

            self.setup_settings_tab_update_slice_treeview()
            self.slice_start_entry.set_text('')
            self.slice_stop_entry.set_text('')

        else:

            self.setup_slices_tab_update_treeview()
            self.simple_slice_start_entry.set_text('')
            self.simple_slice_stop_entry.set_text('')

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_add_timestamp_clicked(self, button):

        """Called from a callback in self.setup_settings_tab_clip_grid().

        In simple mode, called from a callback in self.setup_clips_tab().

        Adds a new timestamp to the video's timestamp list, optionally with a
        clip title.

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' FFmpeg options > Clips'
        )

        if not self.app_obj.simple_ffmpeg_options_flag:

            start_stamp = ttutils.strip_whitespace(
                self.start_stamp_entry.get_text(),
            )
            stop_stamp = ttutils.strip_whitespace(
                self.stop_stamp_entry.get_text(),
            )
            clip_title = ttutils.strip_whitespace(
                self.clip_title_entry.get_text(),
            )

        else:

            start_stamp = ttutils.strip_whitespace(
                self.simple_start_stamp_entry.get_text(),
            )
            stop_stamp = ttutils.strip_whitespace(
                self.simple_stop_stamp_entry.get_text(),
            )
            clip_title = ttutils.strip_whitespace(
                self.simple_clip_title_entry.get_text(),
            )

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
            split_list = self.retrieve_val('split_list')
            split_list.append([ start_stamp, stop_stamp, clip_title ])
            split_list.sort()
            self.edit_dict['split_list'] = split_list

            # (Show changes, and update entry boxes. 'stop_stamp', if
            #   specified, becomes 'start_stamp' for the next group)
            if not self.app_obj.simple_ffmpeg_options_flag:

                self.setup_settings_tab_update_clip_treeview()

                if stop_stamp is not None:
                    self.start_stamp_entry.set_text(
                        ttutils.timestamp_add_second(self.app_obj, stop_stamp),
                    )
                else:
                    self.start_stamp_entry.set_text('')

                self.stop_stamp_entry.set_text('')
                self.clip_title_entry.set_text('')

            else:

                self.setup_clips_tab_update_treeview()
                if stop_stamp is not None:
                    self.simple_start_stamp_entry.set_text(
                        ttutils.timestamp_add_second(self.app_obj, stop_stamp),
                    )
                else:
                    self.simple_start_stamp_entry.set_text('')

                self.simple_stop_stamp_entry.set_text('')
                self.simple_clip_title_entry.set_text('')

        else:

            self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                _('Invalid timestamp(s)'),
                'error',
                'ok',
                self,           # Parent window is this window
                )

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_audio_flag_checkbutton_toggled(self, checkbutton):

        """Called by callback in self.setup_settings_tab().

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if not checkbutton.get_active():

            self.edit_dict['audio_flag'] = False

            self.audio_bitrate_spinbutton.set_sensitive(False)

        else:

            self.edit_dict['audio_flag'] = True

            if self.retrieve_val('input_mode') == 'video':
                self.audio_bitrate_spinbutton.set_sensitive(True)
            else:
                self.audio_bitrate_spinbutton.set_sensitive(False)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_change_file_ext_entry_changed(self, entry):

        """Called by callback in self.setup_file_tab().

        Args:

            entry (Gtk.Entry): The widget clicked

        """

        value = entry.get_text()

        self.edit_dict['change_file_ext'] = value
        if value == '':

            self.delete_original_flag_checkbutton.set_active(False)
            self.delete_original_flag_checkbutton.set_sensitive(False)

        else:
            self.delete_original_flag_checkbutton.set_sensitive(True)


        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_clear_slice_clicked(self, button):

        """Called from a callback in self.setup_settings_tab_slice_grid().

        Empties the slice list.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.edit_dict['slice_list'] = []
        if not self.app_obj.simple_ffmpeg_options_flag:
            self.setup_settings_tab_update_slice_treeview()
        else:
            self.setup_slices_tab_update_treeview()

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_clear_timestamp_clicked(self, button):

        """Called from a callback in self.setup_settings_tab_clip_grid().

        Empties the timestamp list.

        Args:

            button (Gtk.Button): The widget clicked

        """

        self.edit_dict['split_list'] = []
        if not self.app_obj.simple_ffmpeg_options_flag:
            self.setup_settings_tab_update_clip_treeview()
        else:
            self.setup_clips_tab_update_treeview()

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_clip_prefs_clicked(self, button):

        """Called from a callback in self.setup_settings_tab_clip_grid() and
        .setup_clips_tab().

        Opens the preferences window to show clip settings.

        Args:

            button (Gtk.Button): The widget clicked

        """

        SystemPrefWin(self.app_obj, 'clips')


    def on_clone_options_clicked(self, button):

        """Called by callback in self.setup_name_tab().

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' FFmpeg options > Name'
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
                'yes': 'clone_ffmpeg_options_from_window',
                'data': [self, self.edit_obj],
            },
        )


    def on_delete_slice_clicked(self, button, treeview):

        """Called from a callback in self.setup_settings_tab_slice_grid() and
        .setup_slices_tab().

        Deletes the selected slices from the slice list.

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
        #   described by media.Video.__init__()
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

        self.edit_dict['slice_list'] = mod_list

        # (Show changes)
        if not self.app_obj.simple_ffmpeg_options_flag:
            self.setup_settings_tab_update_slice_treeview()
        else:
            self.setup_slices_tab_update_treeview()

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_delete_timestamp_clicked(self, button, treeview):

        """Called from a callback in self.setup_settings_tab_clip_grid() and
        .setup_clips_tab().

        Deletes the selected timestamps from the timestamp list.

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
        split_list = self.retrieve_val('split_list')
        mod_list = []
        match_flag = False

        for mini_list in split_list:

            if not match_flag \
            and mini_list[0] == start_stamp \
            and mini_list[1] == stop_stamp \
            and mini_list[2] == clip_title:
                match_flag = True   # Delete this one
            else:
                mod_list.append(mini_list)

        self.edit_dict['split_list'] = mod_list

        # (Show changes)
        if not self.app_obj.simple_ffmpeg_options_flag:
            self.setup_settings_tab_update_clip_treeview()
        else:
            self.setup_clips_tab_update_treeview()

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_input_mode_radiobutton_toggled(self, radiobutton):

        """Called by callback in self.setup_settings_tab().

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if self.input_mode_radiobutton.get_active():

            self.edit_dict['input_mode'] = 'video'

            self.output_mode_radiobutton.set_active(True)
            self.output_mode_radiobutton.set_sensitive(True)
            self.output_mode_radiobutton2.set_sensitive(True)
            self.output_mode_radiobutton3.set_sensitive(True)
            self.output_mode_radiobutton4.set_sensitive(True)
            self.output_mode_radiobutton5.set_sensitive(False)

            self.audio_flag_checkbutton.set_sensitive(True)
            if not self.retrieve_val('audio_flag'):
                self.audio_bitrate_spinbutton.set_sensitive(False)
            else:
                self.audio_bitrate_spinbutton.set_sensitive(True)

        else:

            self.edit_dict['input_mode'] = 'thumb'

            self.output_mode_radiobutton4.set_active(True)
            self.output_mode_radiobutton.set_sensitive(False)
            self.output_mode_radiobutton2.set_sensitive(False)
            self.output_mode_radiobutton3.set_sensitive(False)
            self.output_mode_radiobutton4.set_sensitive(False)
            self.output_mode_radiobutton5.set_sensitive(True)

            self.audio_flag_checkbutton.set_sensitive(False)
            self.audio_bitrate_spinbutton.set_sensitive(False)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_limit_flag_checkbutton_toggled(self, checkbutton):

        """Called by callback in self.setup_optimise_tab().

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if not checkbutton.get_active():

            self.edit_dict['limit_flag'] = False

            self.limit_mbps_spinbutton.set_sensitive(False)
            self.limit_buffer_spinbutton.set_sensitive(False)

        else:

            self.edit_dict['audio_flag'] = True

            self.limit_mbps_spinbutton.set_sensitive(True)
            self.limit_buffer_spinbutton.set_sensitive(True)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_output_mode_radiobutton_toggled(self, radiobutton, grid_width):

        """Called by callback in self.setup_settings_tab().

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            grid_width (int): The width of self.settings_grid

        """

        old_value = self.retrieve_val('output_mode')
        if old_value == 'h264':
            self.settings_grid.remove(self.h264_grid)
        elif old_value == 'gif':
            self.settings_grid.remove(self.gif_grid)
        elif old_value == 'split':
            self.settings_grid.remove(self.clip_grid)
        elif old_value == 'slice':
            self.settings_grid.remove(self.slice_grid)
        elif old_value == 'merge':
            self.settings_grid.remove(self.merge_grid)
        else:
            self.settings_grid.remove(self.thumb_grid)

        if self.output_mode_radiobutton.get_active():

            self.edit_dict['output_mode'] = 'h264'

            self.settings_grid.attach(self.h264_grid, 0, 2, grid_width, 1)
            self.setup_file_tab_set_sensitive(True)
            self.setup_optimise_tab_set_sensitive(True)

        elif self.output_mode_radiobutton2.get_active():

            self.edit_dict['output_mode'] = 'gif'

            self.settings_grid.attach(self.gif_grid, 0, 2, grid_width, 1)
            self.setup_file_tab_set_sensitive(True)
            self.setup_optimise_tab_set_sensitive(False)

        elif self.output_mode_radiobutton3.get_active():

            self.edit_dict['output_mode'] = 'split'

            self.settings_grid.attach(self.clip_grid, 0, 2, grid_width, 1)
            self.setup_file_tab_set_sensitive(False)
            self.setup_optimise_tab_set_sensitive(False)

        elif self.output_mode_radiobutton4.get_active():

            self.edit_dict['output_mode'] = 'slice'

            self.settings_grid.attach(self.slice_grid, 0, 2, grid_width, 1)
            self.setup_file_tab_set_sensitive(False)
            self.setup_optimise_tab_set_sensitive(False)

        elif self.output_mode_radiobutton5.get_active():

            self.edit_dict['output_mode'] = 'merge'

            self.settings_grid.attach(self.merge_grid, 0, 2, grid_width, 1)
            self.setup_file_tab_set_sensitive(True)
            self.setup_optimise_tab_set_sensitive(False)

        elif self.output_mode_radiobutton6.get_active():

            self.edit_dict['output_mode'] = 'thumb'

            self.settings_grid.attach(self.thumb_grid, 0, 2, grid_width, 1)
            self.setup_file_tab_set_sensitive(True)
            self.setup_optimise_tab_set_sensitive(False)

        self.show_all()

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_palette_mode_radiobutton_toggled(self, radiobutton):

        """Called by callback in self.setup_settings_tab_gif_grid().

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if self.palette_mode_radiobutton.get_active():
            self.edit_dict['palette_mode'] = 'faster'
        else:
            self.edit_dict['palette_mode'] = 'better'

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_quality_mode_radiobutton_toggled(self, radiobutton):

        """Called by callback in self.setup_settings_tab_h264_grid().

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if self.quality_mode_radiobutton.get_active():

            self.edit_dict['quality_mode'] = 'crf'

            self.rate_factor_scale.set_sensitive(True)
            self.dummy_file_combo.set_sensitive(False)

        else:

            self.edit_dict['quality_mode'] = 'abr'

            self.rate_factor_scale.set_sensitive(False)
            self.dummy_file_combo.set_sensitive(True)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_rate_factor_scale_changed(self, scale):

        """Called by callback in self.setup_settings_tab_h264_grid().

        Args:

            scale (Gtk.Scale): The widget clicked

        """

        value = int(self.rate_factor_scale.get_value())

        self.edit_dict['rate_factor'] = value

        if not value:
            self.profile_flag_checkbutton.set_sensitive(False)
        else:
            self.profile_flag_checkbutton.set_sensitive(True)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_regex_match_filename_entry_changed(self, entry):

        """Called by callback in self.setup_file_tab().

        Args:

            entry (Gtk.Entry): The widget clicked

        """

        value = entry.get_text()

        self.edit_dict['regex_match_filename'] = value
        if value == '':

            self.regex_apply_subst_entry.set_text('')
            self.regex_apply_subst_entry.set_sensitive(False)

        else:

            self.regex_apply_subst_entry.set_sensitive(True)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_reset_options_clicked(self, button):

        """Called by callback in self.setup_name_tab().

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' FFmpeg options > Name'
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
                'yes': 'reset_ffmpeg_options',
                # (Reset this edit window, if the user clicks 'yes')
                'data': [self],
            },
        )


    def on_simple_options_clicked(self, button):

        """Called by callback in self.setup_name_tab().

        Args:

            button (Gtk.Button): The widget clicked

        """

        ignore_me = _(
            'TRANSLATOR\'S NOTE: Dialogue window, generated by:' \
            + ' FFmpeg options > Name'
        )

        redraw_flag = False
        if not self.app_obj.simple_ffmpeg_options_flag:

            self.app_obj.set_simple_ffmpeg_options_flag(True)

            if not self.edit_dict:

                # User has not changed any options, so redraw the window to
                #   show the same options.OptionsManager object
                self.reset_with_new_edit_obj(self.edit_obj)

            else:

                # User has already changed some options. We don't want to lose
                #   them, so wait for the window to close and be re-opened,
                #   before switching between simple/advanced options
                redraw_flag = True

                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _(
                    'Fewer FFmpeg options will be visible when you click the' \
                    + ' \'Apply\' or \'Reset\' buttons (or when you close' \
                    + ' and then re-open the window)',
                    ),
                    'info',
                    'ok',
                    self,           # Parent window is this window
                )

                button.set_label(
                    _('Show more FFmpeg options (when window re-opens)'),
                )

        else:

            self.app_obj.set_simple_ffmpeg_options_flag(False)

            if not self.edit_dict:

                self.reset_with_new_edit_obj(self.edit_obj)

            else:

                redraw_flag = True

                self.app_obj.dialogue_manager_obj.show_msg_dialogue(
                    _(
                    'More FFmpeg options will be visible when you click the' \
                    + ' \'Apply\' or \'Reset\' buttons (or when you close' \
                    + ' and then re-open the window)',
                    ),
                    'info',
                    'ok',
                    self,           # Parent window is this window
                )

                button.set_label(
                    _('Show fewer FFmpeg options (when window re-opens)'),
                )

        if redraw_flag:

            # Discard the list of videos, so that this becomes an ordinary
            #   edit window, with an 'OK' button that stores changes (and no
            #   'Process files' button that starts a process operation)
            self.video_list = []

            self.ok_button.set_label(_('OK'))
            self.ok_button.get_child().set_width_chars(10)
            self.ok_button.set_tooltip_text(
                _('Apply changes'),
            )


    def on_simple_slice_toggled(self, checkbutton):

        """Called by callback in self.setup_slices_tab().

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if not checkbutton.get_active():

            self.edit_dict['output_mode'] = 'h264'
            radio_sens_flag = False
            sens_flag = False

        else:

            # (Update the corresponding checkbutton in the 'Clips' tab)
            self.simple_split_mode_checkbutton.set_active(False)

            # (Respond to clicks on this checkbutton)
            self.edit_dict['output_mode'] = 'slice'
            radio_sens_flag = True

            if self.retrieve_val('slice_mode') == 'video':
                sens_flag = False
            else:
                sens_flag = True

        # (De)sensitise widgets
        self.simple_slice_mode_radiobutton.set_sensitive(radio_sens_flag)
        self.simple_slice_mode_radiobutton2.set_sensitive(radio_sens_flag)
        self.simple_category_combo.set_sensitive(sens_flag)
        self.simple_action_combo.set_sensitive(sens_flag)
        self.simple_slice_start_entry.set_sensitive(sens_flag)
        self.simple_slice_stop_entry.set_sensitive(sens_flag)

        self.simple_add_slice_button.set_sensitive(sens_flag)
        self.simple_delete_slice_button.set_sensitive(sens_flag)
        self.simple_show_settings_button.set_sensitive(True)
        self.simple_clear_slice_button.set_sensitive(sens_flag)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_simple_split_toggled(self, checkbutton):

        """Called by callback in self.setup_clips_tab().

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

        """

        if not checkbutton.get_active():

            self.edit_dict['output_mode'] = 'h264'
            radio_sens_flag = False
            sens_flag = False

        else:

            # (Update the corresponding checkbutton in the 'Slices' tab)
            self.simple_slice_mode_checkbutton.set_active(False)

            # (Respond to clicks on this checkbutton)
            self.edit_dict['output_mode'] = 'split'
            radio_sens_flag = True

            if self.retrieve_val('split_mode') == 'video':
                sens_flag = False
            else:
                sens_flag = True

        # (De)sensitise widgets
        self.simple_split_mode_radiobutton.set_sensitive(radio_sens_flag)
        self.simple_split_mode_radiobutton2.set_sensitive(radio_sens_flag)
        self.simple_start_stamp_entry.set_sensitive(sens_flag)
        self.simple_stop_stamp_entry.set_sensitive(sens_flag)
        self.simple_clip_title_entry.set_sensitive(sens_flag)
        self.simple_add_timestamp_button.set_sensitive(sens_flag)
        self.simple_delete_timestamp_button.set_sensitive(sens_flag)
        self.simple_show_prefs_button.set_sensitive(True)
        self.simple_clear_timestamp_button.set_sensitive(sens_flag)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_slice_mode_radiobutton_toggled(self, radiobutton):

        """Called by callback in self.setup_settings_tab_slice_grid().

        In simple mode, called from a callback in self.setup_slices_tab().

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if not self.app_obj.simple_ffmpeg_options_flag:

            if self.slice_mode_radiobutton.get_active():

                self.edit_dict['slice_mode'] = 'video'
                sens_flag = False

            else:

                self.edit_dict['slice_mode'] = 'custom'
                sens_flag = True

            # (De)sensitise widgets
            self.category_combo.set_sensitive(sens_flag)
            self.action_combo.set_sensitive(sens_flag)
            self.slice_start_entry.set_sensitive(sens_flag)
            self.slice_stop_entry.set_sensitive(sens_flag)
            self.add_slice_button.set_sensitive(sens_flag)
            self.delete_slice_button.set_sensitive(sens_flag)
            self.show_settings_button.set_sensitive(True)
            self.clear_slice_button.set_sensitive(sens_flag)

        else:

            if self.simple_slice_mode_radiobutton.get_active():

                self.edit_dict['slice_mode'] = 'video'
                sens_flag = False

            else:

                self.edit_dict['slice_mode'] = 'custom'
                if self.retrieve_val('output_mode') == 'slice':
                    sens_flag = True
                else:
                    sens_flag = False

            # (De)sensitise widgets
            self.simple_category_combo.set_sensitive(sens_flag)
            self.simple_action_combo.set_sensitive(sens_flag)
            self.simple_slice_start_entry.set_sensitive(sens_flag)
            self.simple_slice_stop_entry.set_sensitive(sens_flag)
            self.simple_add_slice_button.set_sensitive(sens_flag)
            self.simple_delete_slice_button.set_sensitive(sens_flag)
            self.simple_show_settings_button.set_sensitive(True)
            self.simple_clear_slice_button.set_sensitive(sens_flag)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_slice_settings_clicked(self, button):

        """Called from a callback in self.setup_settings_tab_slice_grid() and
        .setup_slices_tab().

        Opens the preferences window to show slice settings.

        Args:

            button (Gtk.Button): The widget clicked

        """

        SystemPrefWin(self.app_obj, 'slices')


    def on_split_mode_radiobutton_toggled(self, radiobutton):

        """Called by callback in self.setup_settings_tab_clip_grid().

        In simple mode, called from a callback in self.setup_clips_tab().

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

        """

        if not self.app_obj.simple_ffmpeg_options_flag:

            if self.split_mode_radiobutton.get_active():

                self.edit_dict['split_mode'] = 'video'
                sens_flag = False

            else:

                self.edit_dict['split_mode'] = 'custom'
                sens_flag = True

            # (De)sensitise widgets
            self.start_stamp_entry.set_sensitive(sens_flag)
            self.stop_stamp_entry.set_sensitive(sens_flag)
            self.clip_title_entry.set_sensitive(sens_flag)
            self.add_timestamp_button.set_sensitive(sens_flag)
            self.delete_timestamp_button.set_sensitive(sens_flag)
            self.show_prefs_button.set_sensitive(True)
            self.clear_timestamp_button.set_sensitive(sens_flag)

        else:

            if self.simple_split_mode_radiobutton.get_active():

                self.edit_dict['split_mode'] = 'video'
                sens_flag = False

            else:

                self.edit_dict['split_mode'] = 'custom'
                if self.retrieve_val('output_mode') == 'split':
                    sens_flag = True
                else:
                    sens_flag = False

            # (De)sensitise widgets
            self.simple_start_stamp_entry.set_sensitive(sens_flag)
            self.simple_stop_stamp_entry.set_sensitive(sens_flag)
            self.simple_clip_title_entry.set_sensitive(sens_flag)
            self.simple_add_timestamp_button.set_sensitive(sens_flag)
            self.simple_delete_timestamp_button.set_sensitive(sens_flag)
            self.simple_show_prefs_button.set_sensitive(True)
            self.simple_clear_timestamp_button.set_sensitive(sens_flag)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_video_drag_data_received(self, widget, context, x, y, data, info,
    time):

        """Called from callback in self.setup_videos_tab().

        This function is required for detecting when the user drags and drops
        data into the Videos tab.

        If the data contains full paths to a video/audio file and/or URLs,
        then we can search the media data registry, looking for matching
        media.Video objects.

        Those objects can then be added to self.video_list.

        Args:

            widget (mainwin.MainWin): The widget into which something has been
                dragged

            drag_context (GdkX11.X11DragContext): Data from the drag procedure

            x, y (int): Where the drop happened

            data (Gtk.SelectionData): The object to be filled with drag data

            info (int): Info that has been registered with the target in the
                Gtk.TargetList

            time (int): A timestamp

        """

        text = None
        if info == 0:
            text = data.get_text()

        if text is not None:

            # Hopefully, 'text' contains one or more valid URLs or paths to
            #   video/audio files
            line_list = text.splitlines()
            mod_list = []

            for line in line_list:
                mod_line = ttutils.strip_whitespace(urllib.parse.unquote(line))
                if mod_line != '':

                    # On Linux, URLs are received as expected, but paths to
                    #   media data files are received as 'file://PATH'
                    match = re.search(r'^file\:\/\/(.*)', mod_line)
                    if match:
                        mod_list.append(match.group(1))
                    else:
                        mod_list.append(mod_line)

            # The True argument means to include 'dummy' media.Videos from the
            #   Classic Mode tab in the search
            video_list = self.app_obj.retrieve_videos_from_db(mod_list, True)

            # (Remember if the video list is currently empty, or not)
            old_size = len(self.video_list)

            # Add videos to the list, but don't add duplicates
            for video_obj in video_list:

                if not video_obj in self.video_list:
                    self.video_list.append(video_obj)

            # Redraw the whole video list by calling this function, which also
            #   sorts self.video_list nicely
            self.setup_videos_tab_update_treeview()

            if old_size == 0 and self.video_list:

                # Replace the 'OK' button with a 'Process files' button
                self.ok_button.set_label(_('Process files'))
                self.ok_button.set_tooltip_text(
                    _('Process the files with FFmpeg'),
                )
                self.ok_button.get_child().set_width_chars(15)

        # Without this line, the user's cursor is permanently stuck in drag
        #   and drop mode
        context.finish(True, False, time)


    def on_video_remove_button_clicked(self, button, treeview):

        """Called from callback in self.setup_videos_tab().

        Removes a video from the list of videos to be processed by FFmpeg.

        If there are no videos left, this edit window reverts to its default
        state, in which we just save any changes to the FFmpeg options.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview to be updated

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:

            return

        dbid = int(model[this_iter][0])
        for video_obj in self.video_list:

            if video_obj.dbid == dbid:
                self.video_list.remove(video_obj)
                break

        # Update the visible list
        self.setup_videos_tab_update_treeview()
        # If all videos have been removed, restore the OK button
        if not self.video_list:

            self.ok_button.set_label(_('OK'))
            self.ok_button.get_child().set_width_chars(10)
            self.ok_button.set_tooltip_text(
                _('Apply changes'),
            )


    def on_video_show_button_clicked(self, button, treeview):

        """Called from callback in self.setup_videos_tab().

        Opens the video properties window.

        Args:

            button (Gtk.Button): The widget clicked

            treeview (Gtk.TreeView): The treeview to be updated

        """

        selection = treeview.get_selection()
        (model, path_list) = selection.get_selected_rows()
        if not path_list:

            return

        # (Multiple selection is not enabled)
        this_iter = model.get_iter(path_list[0])
        if this_iter is None:

            return

        dbid = int(model[this_iter][0])
        if dbid in self.app_obj.media_reg_dict:
            VideoEditWin(
                self.app_obj,
                self.app_obj.media_reg_dict[dbid],
            )


    # (Redefined button strip callbacks)


    def on_button_apply_clicked(self, button):

        """Called from a callback in self.setup_button_strip().

        Applies any changes made by the user and re-draws the window's tabs,
        showing their new values.

        Args:

            button (Gtk.Button): The widget clicked

        """

        # Apply any changes the user has made. The True argument identifies
        #   this function as the caller, and prevents a process operation from
        #   starting
        self.apply_changes(True)

        # Remove all existing tabs from the notebook
        number = self.notebook.get_n_pages()
        if number:

            for count in range(0, number):
                self.notebook.remove_page(0)

        # Re-draw all the tabs
        self.setup_tabs()

        # Render the changes
        self.show_all()


    # (Redefined generic callbacks)


    def on_checkbutton_toggled(self, checkbutton, prop):

        """Modified form of the GenericEditWin callback, in which we
        automatically update the system command visible in the 'Name' tab.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        if not checkbutton.get_active():
            self.edit_dict[prop] = False
        else:
            self.edit_dict[prop] = True

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_combo_with_data_changed(self, combo, prop):

        """Modified form of the GenericEditWin callback, in which we
        automatically update the system command visible in the 'Name' tab.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.edit_dict[prop] = model[tree_iter][1]

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_entry_changed(self, entry, prop):

        """Modified form of the GenericEditWin callback, in which we
        automatically update the system command visible in the 'Name' tab.

        Args:

            entry (Gtk.Entry): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        self.edit_dict[prop] = entry.get_text()

        # (De)sensitise the checkbutton for 'rename_both_flag', if required
        if entry == self.add_end_filename_entry \
        or entry == self.regex_match_filename_entry:

            if self.retrieve_val('add_end_filename') == '' \
            and self.retrieve_val('regex_match_filename') == '':
                self.rename_both_flag_checkbutton.set_active(False)
                self.rename_both_flag_checkbutton.set_sensitive(False)
            else:
                self.rename_both_flag_checkbutton.set_sensitive(True)

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_spinbutton_changed(self, spinbutton, prop):

        """Modified form of the GenericEditWin callback, in which we
        automatically update the system command visible in the 'Name' tab.

        Args:

            spinbutton (Gtk.SpinkButton): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        self.edit_dict[prop] = int(spinbutton.get_value())

        # Update the system command in the 'Name' tab
        self.update_system_cmd()


    def on_textview_changed(self, textbuffer, prop):

        """Modified form of the GenericEditWin callback, in which we
        automatically update the system command visible in the 'Name' tab.

        Args:

            textbuffer (Gtk.TextBuffer): The widget modified

            prop (str): The attribute in self.edit_obj to modify

        """

        text = textbuffer.get_text(
            textbuffer.get_start_iter(),
            textbuffer.get_end_iter(),
            # Don't include hidden characters
            False,
        )

        old_value = self.retrieve_val(prop)

        if type(old_value) is list:
            self.edit_dict[prop] = text.split()
        elif type(old_value) is tuple:
            self.edit_dict[prop] = text.split()
        else:
             self.edit_dict[prop] = text

        # Update the system command in the 'Name' tab
        self.update_system_cmd()
