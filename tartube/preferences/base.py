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
# Use same gettext translations
from mainapp import _

# Import matplotlib stuff
if mainapp.HAVE_MATPLOTLIB_FLAG:
    from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg
    from matplotlib.figure import Figure
    from matplotlib.ticker import MaxNLocator


class GenericConfigWin(Gtk.Window):

    """Generic Python class for windows in which the user can modify various
    settings.

    Inherited by two types of window - 'preference windows' (in which changes
    are applied immediately), and 'edit windowS' (in which changes are stored
    temporarily, and only applied once the user has finished making changes.
    """


    # Standard class methods


#   def __init__():             # Provided by child object


    # Public class methods


#   def is_duplicate():         # Provided by child object


    def setup(self):

        """Called by self.__init__().

        Sets up the config window when it opens.
        """

        # Set the default window size
        self.set_default_size(
            self.app_obj.config_win_width,
            self.app_obj.config_win_height,
        )

        # Set the window's Gtk icon list
        self.set_icon_list(self.app_obj.main_win_obj.config_win_pixbuf_list)

        # Set up main widgets
        self.setup_grid()
        self.setup_notebook()
        self.setup_button_strip()
        self.setup_gap()

        # Set up tabs
        self.setup_tabs()

        # Procedure complete
        self.show_all()

        # Inform the main window of this window's birth (so that Tartube
        #   doesn't allow an operation to start until all configuration windows
        #   have closed)
        self.app_obj.main_win_obj.add_child_window(self)
        # Add a callback so we can inform the main window of this window's
        #   destruction
        self.connect('destroy', self.close)


    def setup_grid(self):

        """Called by self.setup().

        Sets up a Gtk.Grid, on which a notebook and a button strip will be
        placed. (Each of the notebook's tabs also has its own Gtk.Grid.)
        """

        self.grid = Gtk.Grid()
        self.add(self.grid)


    def setup_notebook(self):

        """Called by self.setup().

        Sets up a Gtk.Notebook, after which self.setup_tabs() is called to fill
        it with tabs.
        """

        self.notebook = Gtk.Notebook()
        self.grid.attach(self.notebook, 0, 1, 1, 1)
        self.notebook.set_border_width(self.spacing_size)
        # It shouldn't be necessary to scroll the notebook's tabs, but we'll
        #   make it possible anyway
        self.notebook.set_scrollable(True)


    def add_notebook_tab(self, name, border_width=None):

        """Called by various functions in the child edit/preference window.

        Adds a tab to the main Gtk.Notebook, creating a Gtk.Grid inside it, on
        which the calling function can add more widgets.

        Args:

            name (str): The name of the tab

            border_width (int): If specified, the border width for the
                Gtk.Grid contained in this tab (usually specified when an inner
                Gtk.Notebook is to be added to this tab). If not specified, a
                default width is used

        Return values:

            The tab created (in the form of a Gtk.Box) and its Gtk.Grid

        """

        if border_width is None:
            border_width = self.spacing_size

        tab = Gtk.Box()
        self.notebook.append_page(tab, Gtk.Label.new_with_mnemonic(name))
        tab.set_hexpand(True)
        tab.set_vexpand(True)
        tab.set_border_width(self.spacing_size)

        scrolled = Gtk.ScrolledWindow()
        tab.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        grid = Gtk.Grid()
        scrolled.add_with_viewport(grid)
        grid.set_border_width(border_width)
        grid.set_column_spacing(self.spacing_size)
        grid.set_row_spacing(self.spacing_size)

        return tab, grid


    def add_inner_notebook(self, grid):

        """Called by various functions in the child edit/preference window.

        Adds an inner Gtk.Notebook to a tab inside the main Gtk.Notebook.

        Args:

            grid (Gtk.Grid): The widget to which the notebook is added

        Return values:

            Returns the new Gtk.Notebook

        """

        inner_notebook = Gtk.Notebook()
        grid.attach(inner_notebook, 0, 1, 1, 1)
        # It shouldn't be necessary to scroll the notebook's tabs, but we'll
        #   make it possible anyway
        inner_notebook.set_scrollable(True)

        return inner_notebook


    def add_inner_notebook_tab(self, name, notebook):

        """Called by various functions in the child edit/preference window.

        A modified form of self.add_notebook_tab, for tabs to be placd in the
        inner notebook created by a call to self.add_inner_notebook.

        Adds a tab to the specified Gtk.Notebook, creating a Gtk.Grid inside
        it, on which the calling function can add more widgets.

        Args:

            name (str): The name of the tab

            notebook (Gtk.Notebook): The notebook to which the tab is added

        Return values:

            The tab created (in the form of a Gtk.Box) and its Gtk.Grid

        """

        tab = Gtk.Box()
        notebook.append_page(tab, Gtk.Label.new_with_mnemonic(name))
        tab.set_hexpand(True)
        tab.set_vexpand(True)

        scrolled = Gtk.ScrolledWindow()
        tab.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        grid = Gtk.Grid()
        scrolled.add_with_viewport(grid)
        grid.set_border_width(self.spacing_size)
        grid.set_column_spacing(self.spacing_size)
        grid.set_row_spacing(self.spacing_size)

        return tab, grid


#   def setup_button_strip():   # Provided by child object


    def setup_gap(self):

        """Called by self.setup().

        Adds an empty box beneath the button strip for aesthetic purposes.
        """

        hbox = Gtk.HBox()
        self.grid.attach(hbox, 0, 3, 1, 1)
        hbox.set_border_width(self.spacing_size)


    def close(self, also_self):

        """Called from callback in self.setup().

        Inform the main window that this window is closing.

        Args:

            also_self (an object inheriting from config.GenericConfigWin):
                Another copy of self

        """

        self.app_obj.main_win_obj.del_child_window(self)


    # (Add widgets)


    def add_secondary_grid(self, grid, x, y, wid, hei):

        """Called by various functions in the child edit window.

        Adds another Gtk.Grid, to be placed inside the tab's main grid, in
        order to avoid messing up widget spacing elsewhere in the tab.

        Args:

            grid (Gtk.Grid): The existing grid on which the new grid will be
                placed

            x, y, wid, hei (int): Position on the existing grid at which the
                new grid is placed

        Return values:

            The new Gtk.Grid

        """

        grid2 = Gtk.Grid()
        grid.attach(grid2, x, y, wid, hei)
        grid2.set_vexpand(False)
        grid2.set_column_spacing(self.spacing_size)
        grid2.set_row_spacing(self.spacing_size)

        return grid2


    def add_image(self, grid, image_path, x, y, wid, hei):

        """Called by various functions in the child edit window.

        Adds a Gtk.Image to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            image_path (str): Full path to the image file to load

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The Gtk.Frame containing the image

        """

        frame = Gtk.Frame()
        grid.attach(frame, x, y, wid, hei)

        image = Gtk.Image()
        frame.add(image)
        image.set_from_pixbuf(
            self.app_obj.file_manager_obj.load_to_pixbuf(image_path),
        )

        return frame


    def add_pixbuf(self, grid, pixbuf_name, x, y, wid, hei):

        """Called by various functions in the child config window.

        Adds a Gtk.Image to the tab's Gtk.Grid. A modified version of
        self.add_image(), which is called with a path to an image file; this
        function is called with one of the pixbuf names specified by
        mainwin.MainWin.pixbuf_dict, e.g. 'video_both_large'.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            pixbuf_name (str): One of the keys in
                mainwin.MainWin.pixbuf_dict, e.g. 'video_both_large'.

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The Gtk.Frame containing the image

        """

        frame = Gtk.Frame()
        grid.attach(frame, x, y, wid, hei)

        image = Gtk.Image()
        frame.add(image)

        main_win_obj = self.app_obj.main_win_obj
        if pixbuf_name in main_win_obj.pixbuf_dict:
            image.set_from_pixbuf(main_win_obj.pixbuf_dict[pixbuf_name])
        else:
            # Unrecognised pixbuf name
            image.set_from_pixbuf(
                main_win_obj.pixbuf_dict['question_large'],
            )

        return frame


    def add_treeview(self, grid, x, y, wid, hei):

        """Called by various functions in the child preference/edit window.

        Adds a single-column Gtk.Treeview to the tab's Gtk.Grid. No callback
        function is created by this function; it's up to the calling code to
        supply one.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            A list containing the treeview widget and liststore created

        """

        frame = Gtk.Frame()
        grid.attach(frame, x, y, wid, hei)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        treeview = Gtk.TreeView()
        scrolled.add(treeview)
        treeview.set_headers_visible(False)

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn(
            '',
            renderer_text,
            text=0,
        )
        treeview.append_column(column_text)

        liststore = Gtk.ListStore(str)
        treeview.set_model(liststore)

        return treeview, liststore


    # (Shared support functions)


    def add_combos_for_graphs(self, grid, row):

        """Called by tabs in ChannelPlaylistEditWin, FolderEditWin and
        SystemPrefWin.

        The tabs that draw graphs share a standard set of comboboxes, with
        which the graph is customised.

        This function is called to create the comboboxes, and to set up
        callbacks so that changes to the settings are remembered between
        windows.

        Args:

            grid (Gtk.Grid): The grid on which widgets are arranged in their
                tab

            row (int): The grid row on which these combos appear

        """

        if isinstance(self, GenericPrefWin):
            pref_win_flag = True
        else:
            pref_win_flag = False

        # Add combos to customise the graph
        combo_list = [
            [_('Downloads'), 'receive'],
            [_('Uploads'), 'upload'],
            [_('File size'), 'size'],
            [_('Duration'), 'duration'],
        ]

        if pref_win_flag:

            combo = self.add_combo_with_data(grid,
                combo_list,
                self.app_obj.graph_data_type,
                0, row, 1, 1,
            )

        else:

            combo = self.add_combo_with_data(grid,
                combo_list,
                None,
                0, row, 1, 1,
            )

            count = -1
            for mini_list in combo_list:
                count += 1
                if mini_list[1] == self.app_obj.graph_data_type:
                    combo.set_active(count)
                    break

        combo.set_hexpand(True)

        combo_list2 = [
            [_('Graph'), 'graph'],
            [_('Bar chart'), 'chart'],
        ]

        if pref_win_flag:

            combo2 = self.add_combo_with_data(grid,
                combo_list2,
                self.app_obj.graph_plot_type,
                1, row, 1, 1,
            )

        else:

            combo2 = self.add_combo_with_data(grid,
                combo_list2,
                None,
                1, row, 1, 1,
            )

            count = -1
            for mini_list in combo_list2:
                count += 1
                if mini_list[1] == self.app_obj.graph_plot_type:
                    combo2.set_active(count)
                    break

        combo2.set_hexpand(True)

        combo_list3 = [
            [_('Show decade'), 60*60*24*365*10],
            [_('Show year'), 60*60*24*365],
            [_('Show quarters'), 60*60*24*90],
            [_('Show month'), 60*60*24*30],
            [_('Show week'), 60*60*24*7],
            [_('Show day'), 60*60*24],
        ]

        if pref_win_flag:

            combo3 = self.add_combo_with_data(grid,
                combo_list3,
                self.app_obj.graph_time_period_secs,
                2, row, 1, 1,
            )

        else:

            combo3 = self.add_combo_with_data(grid,
                combo_list3,
                None,
                2, row, 1, 1,
            )

            count = -1
            for mini_list in combo_list3:
                count += 1
                if mini_list[1] == self.app_obj.graph_time_period_secs:
                    combo3.set_active(count)
                    break

        combo3.set_hexpand(True)
        if self.app_obj.graph_data_type != 'receive' \
        and self.app_obj.graph_data_type != 'upload':
            combo3.set_sensitive(False)

        combo_list4 = [
            [_('Quarters'), 60*60*24*90],
            [_('Months'), 60*60*24*30],
            [_('Weeks'), 60*60*24*7],
            [_('Days'), 60*60*24],
            [_('Hours'), 60*60],
        ]

        if pref_win_flag:

            combo4 = self.add_combo_with_data(grid,
                combo_list4,
                self.app_obj.graph_time_unit_secs,
                3, row, 1, 1,
            )

        else:

            combo4 = self.add_combo_with_data(grid,
                combo_list4,
                None,
                3, row, 1, 1,
            )

            count = -1
            for mini_list in combo_list4:
                count += 1
                if mini_list[1] == self.app_obj.graph_time_unit_secs:
                    combo4.set_active(count)
                    break

        combo4.set_hexpand(True)
        if self.app_obj.graph_data_type != 'receive' \
        and self.app_obj.graph_data_type != 'upload':
            combo4.set_sensitive(False)

        combo_list5 = [
            [_('Red'), 'red'],
            [_('Green'), 'green'],
            [_('Blue'), 'blue'],
            [_('Black'), 'black'],
            [_('White'), 'white'],
        ]

        if pref_win_flag:

            combo5 = self.add_combo_with_data(grid,
                combo_list5,
                self.app_obj.graph_ink_colour,
                4, row, 1, 1,
            )

        else:

            combo5 = self.add_combo_with_data(grid,
                combo_list5,
                None,
                4, row, 1, 1,
            )

            count = -1
            for mini_list in combo_list5:
                count += 1
                if mini_list[1] == self.app_obj.graph_ink_colour:
                    combo5.set_active(count)
                    break

        combo5.set_hexpand(True)

        # (Signal connects from above)
        combo.connect(
            'changed',
            self.on_combo_graph_changed,
            'data_type',
            combo3,
            combo4,
        )
        combo2.connect(
            'changed',
            self.on_combo_graph_changed,
            'plot_type',
            combo3,
            combo4,
        )
        combo3.connect(
            'changed',
            self.on_combo_graph_changed,
            'time_period',
            combo3,
            combo4,
        )
        combo4.connect(
            'changed',
            self.on_combo_graph_changed,
            'time_unit',
            combo3,
            combo4,
        )
        combo5.connect(
            'changed',
            self.on_combo_graph_changed,
            'ink_colour',
            combo3,
            combo4,
        )

        return combo, combo2, combo3, combo4, combo5


    def add_youtube_warning(self, grid, x, y, wid, hei):

        """Can be called by any config window tab, especially those that
        provide a way to pass user credentials to the website (such as
        --username/--password, imported browser cookies, .netrc files etc).

        As of October 2024, some methods will not work, and some may even
        cause the deletion of a YouTube account. The user should consult the
        latest yt-dlp warnings about this issue, before downloading restricted
        videos:

        https://github.com/yt-dlp/yt-dlp/issues/3766
                Return values:

        Args:

            grid (Gtk.Grid): The grid on which widgets are arranged in their
                tab

            x, y, wid, hei (int): Position on the grid at which the warning is
                placed

        Return values:

            The new Gtk.Grid on which the warning is placed

        """

        # (To avoid messing up the neat format of the rows above, add a
        #   secondary grid, and put the next set of widgets inside it)
        grid2 = self.add_secondary_grid(grid, x, y, wid, hei)

        frame = self.add_pixbuf(grid2,
            'attention_large',
            0, 0, 1, 1,
        )
        frame.set_hexpand(False)
        frame.set_border_width(self.spacing_size)
        frame.set_size_request(75, -1)

        frame2 = Gtk.Frame()
        grid2.attach(frame2, 1, 0, 1, 1)

        grid3 = Gtk.Grid()
        frame2.add(grid3)
        grid3.set_border_width(self.spacing_size * 2)
        grid3.set_column_spacing(self.spacing_size * 2)
        grid3.set_row_spacing(self.spacing_size)

        label = Gtk.Label()
        grid3.attach(label, 0, 0, 1, 1)
        label.set_markup(
            _(
                'WARNING! YouTube is trying to block applications like' \
                + ' Tartube!',
            ),
        )
        label.set_hexpand(True)
        label.set_alignment(0, 0.5)

        label2 = Gtk.Label()
        grid3.attach(label2, 0, 1, 1, 1)
        label2.set_markup(
            '<a href="' \
            + html.escape('https://github.com/yt-dlp/yt-dlp/issues/3766') \
            + '" title="' \
            + _('yt-dlp Known Issues FAQ') \
            + '">' \
            + _('Before trying to download restricted videos, read the FAQ!') \
            + '</a>',
        )
        label2.set_hexpand(True)
        label2.set_alignment(0, 0.5)

        return grid2


    def get_options_applied_text(self, options_obj):

        """ Called by OptionsEditWin.setup_name_tab() and
        SystemPrefWin.setup_options_dl_list_tab_add_row().

        Generates text displaying the media data object(s) to which a
        download options manager has been applied.

        Args:

            options_obj (options.OptionsManager): The download options manager

        Return values:

            A single line of displayable text

        """

        if not options_obj.dbid_list:

            # Failsafe; calling code has already checked that
            return ''

        # Database auto-fix: see comments in the called function
        self.get_options_applied_text_autofix(options_obj)

        if len(options_obj.dbid_list) == 1:

            dbid = options_obj.dbid_list[0]
            media_data_obj = self.app_obj.media_reg_dict[dbid]
            return media_data_obj.get_translated_type(True) \
            + ': ' + media_data_obj.name

        else:

            video_count = 0
            channel_count = 0
            playlist_count = 0
            folder_count = 0

            for dbid in options_obj.dbid_list:
                media_data_obj = self.app_obj.media_reg_dict[dbid]
                if isinstance(media_data_obj, media.Video):
                    video_count += 1
                elif isinstance(media_data_obj, media.Channel):
                    channel_count += 1
                elif isinstance(media_data_obj, media.Playlist):
                    playlist_count += 1
                elif isinstance(media_data_obj, media.Folder):
                    folder_count += 1

            msg = ''
            if video_count:
                msg = _('Videos') + ': ' + str(video_count) + ' '

            if channel_count:
                msg = msg + _('Channels') + ': ' + str(channel_count) + ' '

            if playlist_count:
                msg = msg + _('Playlists') + ': ' + str(playlist_count) + ' '

            if folder_count:
                msg = msg + _('Folders') + ': ' + str(folder_count) + ' '

            return msg


    def get_options_applied_text_autofix(self, options_obj):

        """Called by self.get_options_applied_text().

        Git #456 - options.OptionsObj.dbid_list includes .dbid of non-existent
        media data objects.

        Since the cause of the issue is not known, do a quick auto-fix
        whenever the prefwin opens. (The miniscule hit to performance is better
        than a broken preferences window.)

        Args:

            options_obj (options.OptionsManager): The download options manager

        """

        dbid_list = []
        fix_flag = False

        for dbid in options_obj.dbid_list:
            if not dbid in self.app_obj.media_reg_dict:
                fix_flag = True
            else:
                dbid_list.append(dbid)

        if fix_flag:
            options_obj.dbid_list = dbid_list
            self.app_obj.system_error(
                406,
                'Detected and auto-fixed download options applied to non-' \
                + ' existent media. Please do a full database check: in' \
                + ' Tartube\'s menu, click File > Check database integrity',
            )


    def plot_graph(self, hbox, plot_type, data_type, ink_colour, x_label,
    y_label, x_list, y_list):

        """Called by self.on_button_draw_graph_clicked().

        Plots a graph, using the specified settings and data points.

        Args:

            hbox (Gtk.HBox): The container widget

            plot_type (str): 'graph' or 'chart'

            data_type (str): 'receive', 'upload', 'size' or 'duration'

            ink_colour (str): 'red', 'green', 'blue', 'black' or white'

            x_label, y_label (str): Text for each axis on the graph

            x_list (list): List of data points along the x axis

            y_list (list): List of data points along the y axis (both lists
                should contain the same number of items)

        """

        # Sanity check: when the video counts (values in y_list) are all 0,
        #   matplotlib will try to draw a y-axis with fractional values
        # Check for that, so we can prevent it
        simplify_y_axis_flag = True
        for num in y_list:
            if num:
                simplify_y_axis_flag = False
                break

        # Remove the old figure
        for child in hbox.get_children():
            hbox.remove(child)

        # Plot a new figure
        fig = Figure(dpi = 100)

        ax = fig.add_subplot(1, 1, 1)

        if plot_type == 'graph':
            ax.plot(x_list, y_list, color = ink_colour)
        else:
            ax.bar(x_list, y_list, color = ink_colour)

        # Set up the axes
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        # (Negative values are meaningless, so don't allow them to appear on
        #   the x/y axes)
        if simplify_y_axis_flag:
            ax.set_ylim([0, 1])
        else:
            ax.set_ylim(ymin=0)
        if data_type == 'receive' or data_type == 'upload':
            ax.set_xlim(xmin=0)
        # (Fractional values are also meaningless)
        ax.xaxis.set_major_locator(MaxNLocator(integer = True))
        ax.yaxis.set_major_locator(MaxNLocator(integer = True))
        # (For time graphs, reverse the X axis, to show days ago, etc)
        if data_type == 'receive' or data_type == 'upload':
            ax.set_xlim(ax.get_xlim()[::-1])
        # (For some reason, the x-axis label is drawn below the visible area.
        #   Not sure how to fix that, so move it to the top, in which there is
        #   empty space)
        ax.xaxis.set_label_position('top')
        # (Reduce wasted space around the edges)
        fig.tight_layout()

        canvas = FigureCanvasGTK3Agg(fig)  # a Gtk.DrawingArea
        hbox.add(canvas)

        self.show_all()


    def show_spinbutton_leading_zeroes(self, spinbutton, columns):

        """Callback which can be connected to any Gtk.SpinButton.

        Adds leading zeroes to the value displayed in the spinbutton, which is
        expected to be an integer.

        Args:

            spinbutton (Gtk.SpinButton): The widget to modify

            columns (int): A value, 1 or above; e.g. use 2 to show the
                components in a 24-hour clock

        """

        if type(columns) is not int or columns < 1:
            return False

        adjustment = spinbutton.get_adjustment()
        format_str = '{:0' + str(columns) + 'd}'
        spinbutton.set_text(format_str.format(int(adjustment.get_value())))

        return True


    def ytdlp_only(self):

        """Shorcut function, call for various underlined text.

        Return values:

            The formatted string 'yt-dlp only'

        """

        return ' <b>[' + _('yt-dlp only') + ']</b>'


    # (Shared callbacks)


    def on_button_draw_graph_clicked(self, button, hbox, combo, combo2,
    combo3, combo4, combo5):

        """Called from callbacks in ChannelPlaylistEditWin,
        FolderEditWin and SystemPrefWin.

        Prepares data for a graph using the specified settings, then calls
        self.plot_graph() to actually draw it.

        Args:

            button (Gtk.Button): The widget clicked

            hbox (Gtk.HBox): The container widget for the graph

            combo, combo2, combo3, combo4, combo5 (Gtk.ComboBox): Five combos
                specifying the data to view:

                The data type ('receive' for download times, 'upload' for
                upload times, 'size' for file size, 'duration' for video
                duration)

                The type of graph to plot ('graph' for a line plot graph, or
                'chart' for a bar chart)

                The period of time used as the span of the x-axis (in seconds,
                e.g. 31536000 is the equivalent of a year)

                The time unit to use (in seconds, e.g. 604800 is the equivalent
                of a week). We count the number of videos for the time unit
                and use it as a single point on the x-axis

                The colour to use ('red', 'green', 'blue', 'black', white')

        """

        # Extract data from the combos

        # Get the data type ('receive', 'upload', 'size' or 'duration')
        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        data_name = model[tree_iter][0]
        data_type = model[tree_iter][1]

        # Get type of graph to plot ('graph' or 'chart')
        tree_iter2 = combo2.get_active_iter()
        model2 = combo2.get_model()
        plot_type = model2[tree_iter2][1]

        # Get the period of time used as the span of the x-axis, in seconds
        tree_iter3 = combo3.get_active_iter()
        model3 = combo3.get_model()
        time_period_secs = int(model3[tree_iter3][1])

        # Get the time unit to use, in seconds
        tree_iter4 = combo4.get_active_iter()
        model4 = combo4.get_model()
        time_unit = model4[tree_iter4][0]
        time_unit_secs = int(model4[tree_iter4][1])
        # The time unit must not be larger than the total period of time
        if time_unit_secs > time_period_secs:
            time_unit_secs = time_period_secs

        # Get the colour to use ('red', 'green', 'blue', 'black', white')
        tree_iter5 = combo5.get_active_iter()
        model5 = combo5.get_model()
        ink_colour = model5[tree_iter5][1]

        # Compile a dictionary of video counts
        # For 'receive' and 'upload', dictonary in the form
        #   frequency_dict[time_unit_increment] = number_of_videos
        # For 'size', dictionary in the form
        #   frequency_dict[size_category] = number_of_videos
        # For 'duration', dictionary in the form
        #   frequency_dict[duration_category] = number_of_videos
        # When called by SystemPrefWin, use the entire database
        # When called by ChannelPlaylistEditWin or FolderEditWin, use only the
        #   children of that container
        # 'size_category' and 'duration_category' are arbitrary ranges of
        #   values, chosen for aesthetic reasons
        if isinstance(self, GenericEditWin):

            if data_type == 'receive' or data_type == 'upload':

                frequency_dict = self.edit_obj.compile_all_videos_by_frequency(
                    data_type,
                    time_unit_secs,
                    {},
                )

            elif data_type == 'size':

                frequency_dict = self.edit_obj.compile_all_videos_by_size(
                    {},
                )

            elif data_type == 'duration':

                frequency_dict = self.edit_obj.compile_all_videos_by_duration(
                    {},
                )

        else:

            frequency_dict = {}

            for dbid in self.app_obj.container_reg_dict.keys():

                media_data_obj = self.app_obj.media_reg_dict[dbid]
                # Ignore private (system) folders, because they contain
                #   media.Video objects also stored in public folders
                if not isinstance(media_data_obj, media.Folder) \
                or not media_data_obj.priv_flag:

                    if data_type == 'receive' or data_type == 'upload':

                        frequency_dict \
                        = media_data_obj.compile_all_videos_by_frequency(
                            data_type,
                            time_unit_secs,
                            frequency_dict,
                        )

                    elif data_type == 'size':

                        frequency_dict \
                        = media_data_obj.compile_all_videos_by_size(
                            frequency_dict,
                        )

                    elif data_type == 'duration':

                        frequency_dict \
                        = media_data_obj.compile_all_videos_by_duration(
                            frequency_dict,
                        )

        # Compile two lists, with each index giving the x and y coordinates
        #   for the graph to be plotted
        if data_type == 'receive' or data_type == 'upload':

            period_list = []
            frequency_list = []

            for i in range(0, int((time_period_secs / time_unit_secs) + 1)):

                period_list.append(i)
                if i in frequency_dict:
                    frequency_list.append(frequency_dict[i])
                else:
                    frequency_list.append(0)

            # Draw the graph
            self.plot_graph(
                hbox,
                plot_type,
                data_type,
                ink_colour,
                time_unit,
                data_name,
                period_list,
                frequency_list,
            )

        else:

            # NB If these labels are changed, when the corresponding literal
            #   values in media.GenericContainer.compile_all_videos_by_size()
            #   and .compile_all_videos_by_duration() must be changed too
            if data_type == 'size':

                label_list = [
                    '10MB', '25MB', '50MB', '100MB', '250MB',
                    '500MB', '1GB', '2GB', '5GB', '5GB+',
                ]

            else:

                label_list = [
                    '10s', '1m', '5m', '10m', '20m',
                    '30m', '1h', '2h', '5h', '5h+',
                ]

            frequency_list = []
            for label in label_list:

                if label in frequency_dict:
                    frequency_list.append(frequency_dict[label])
                else:
                    frequency_list.append(0)

            # Draw the graph
            self.plot_graph(
                hbox,
                plot_type,
                data_type,
                ink_colour,
                data_name,
                _('Videos'),
                label_list,
                frequency_list,
            )


    def on_combo_graph_changed(self, combo, combo_type, combo2, combo3):

        """Called from callback in self.add_combos_for_graphs().

        Graphs are drawn with five standard combos for customising the graph.
        When the user selects a new setting in a combo, store the value.

        In some cases, one or more of the combos must be (de)sensitised.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            combo_type (str): A string describing which IV to update:
                'data_type', 'plot_type', 'time_period', 'time_unit',
                'ink_colour'

            combo2, combo3 (Gtk.ComboBox): Other combos to be (de)sensitised

        """

        # Extract data from the combo
        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        value = model[tree_iter][1]
        # Update IVs
        self.app_obj.set_graph_values(combo_type, value)

        # (De)sensitise other combos, as appropriate
        if combo_type == 'data_type':

            if (value == 'receive' or value == 'upload'):
                combo2.set_sensitive(True)
                combo3.set_sensitive(True)
            else:
                combo2.set_sensitive(False)
                combo3.set_sensitive(False)



class GenericEditWin(GenericConfigWin):

    """Generic Python class for windows in which the user can modify various
    settings in a class object (such as a media.Video or an
    options.OptionsManager object).

    The modifications are stored temporarily, and only applied once the user
    has finished making changes.
    """


    # Standard class methods


#   def __init__():             # Provided by child object


    # Public class methods


    def is_duplicate(self, app_obj, edit_obj):

        """Called by self.__init__.

        Don't open this edit window, if another with the same .edit_obj is
        already open.

        Args:

            app_obj (mainapp.TartubeApp): The main application object

            edit_obj (options.OptionsManager): The object whose attributes will
                be edited in this window

        Return values:

            True if a duplicate is found, False if not

        """

        for config_win_obj in app_obj.main_win_obj.config_win_list:

            if isinstance(config_win_obj, GenericEditWin) \
            and config_win_obj.edit_obj == edit_obj:

                # Duplicate found
                config_win_obj.present()
                return True

        # Not a duplicate
        return False


#   def setup():                # Inherited from GenericConfigWin


#   def setup_grid():           # Inherited from GenericConfigWin


#   def setup_notebook():       # Inherited from GenericConfigWin


#   def add_notebook_tab():     # Inherited from GenericConfigWin


    def setup_button_strip(self):

        """Called by self.setup().

        Creates a strip of buttons at the bottom of the window. Any changes the
        user has made are applied by clicking the 'OK' or 'Apply' buttons, and
        cancelled by using the 'Reset' or 'Cancel' buttons.

        The window is closed by using the 'OK' and 'Cancel' buttons.

        If self.multi_button_flag is True, only the 'OK' button is created.
        """

        hbox = Gtk.HBox()
        self.grid.attach(hbox, 0, 2, 1, 1)

        if self.multi_button_flag:

            # 'Reset' button
            self.reset_button = Gtk.Button(_('Reset'))
            hbox.pack_start(self.reset_button, False, False, self.spacing_size)
            self.reset_button.get_child().set_width_chars(10)
            self.reset_button.set_tooltip_text(
                _('Reset changes without closing the window'),
            );
            self.reset_button.connect('clicked', self.on_button_reset_clicked)

            # 'Apply' button
            self.apply_button = Gtk.Button(_('Apply'))
            hbox.pack_start(self.apply_button, False, False, self.spacing_size)
            self.apply_button.get_child().set_width_chars(10)
            self.apply_button.set_tooltip_text(
                _('Apply changes without closing the window'),
            );
            self.apply_button.connect('clicked', self.on_button_apply_clicked)

        # 'OK' button
        self.ok_button = Gtk.Button(_('OK'))
        hbox.pack_end(self.ok_button, False, False, self.spacing_size)
        self.ok_button.get_child().set_width_chars(10)
        self.ok_button.set_tooltip_text(_('Apply changes'));
        self.ok_button.connect('clicked', self.on_button_ok_clicked)

        if self.multi_button_flag:

            # 'Cancel' button
            self.cancel_button = Gtk.Button(_('Cancel'))
            hbox.pack_end(self.cancel_button, False, False, self.spacing_size)
            self.cancel_button.get_child().set_width_chars(10)
            self.cancel_button.set_tooltip_text(_('Cancel changes'));
            self.cancel_button.connect(
                'clicked',
                self.on_button_cancel_clicked,
            )


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


    def reset_with_new_edit_obj(self, new_edit_obj):

        """Can be called by anything.

        Resets the object whose values are being edited in this window, i.e.
        self.edit_obj, to the specified object.

        Then redraws the window itself, as if the user had clicked the 'Reset'
        button at the bottom of the window. This makes new_edit_obj's IVs
        visible in the edit window, without the need to destroy the old one and
        replace it with a new one.

        Args:

            new_edit_obj (class): The replacement edit object

        """

        self.edit_obj = new_edit_obj

        # The rest of this function is copied from
        #   self.on_button_reset_clicked()

        # Remove all existing tabs from the notebook
        number = self.notebook.get_n_pages()
        if number:

            for count in range(0, number):
                self.notebook.remove_page(0)

        # Empty self.edit_dict, destroying any changes the user has made
        self.edit_dict = {}

        # Re-draw all the tabs
        self.setup_tabs()

        # Render the changes
        self.show_all()


    def retrieve_val(self, name, default=None):

        """Can be called by anything.

        Any changes the user has made are temporarily stored in self.edit_dict.

        Each key corresponds to an attribute in the object being edited,
        self.edit_obj.

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
        else:
            attrib = getattr(self.edit_obj, name)
            if type(attrib) is list or type(attrib) is dict:
                return attrib.copy()
            else:
                return attrib


    # (Add widgets)


    def add_checkbutton(self, grid, text, prop, x, y, wid, hei):

        """Called by various functions in the child edit window.

        Adds a Gtk.CheckButton to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            text (string or None): The text to display in the checkbutton's
                label. No label is used if 'text' is an empty string or None

            prop (string or None): The name of the attribute in self.edit_obj
                whose value will be set to the contents of this widget. If
                None, no changes are made to self.edit_dict; it's up to the
                calling function to provide a .connect()

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The checkbutton widget created

        """

        checkbutton = Gtk.CheckButton()
        grid.attach(checkbutton, x, y, wid, hei)
        checkbutton.set_hexpand(True)
        if text is not None and text != '':
            checkbutton.set_label(text)

        if prop is not None:
            checkbutton.set_active(self.retrieve_val(prop))
            checkbutton.connect('toggled', self.on_checkbutton_toggled, prop)

        return checkbutton


    def add_combo(self, grid, combo_list, prop, x, y, wid, hei):

        """Called by various functions in the child edit window.

        Adds a simple Gtk.ComboBox to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            combo_list (list): A list of values to display in the combobox.
                This function expects a simple, one-dimensional list. For
                something more complex, see self.add_combo_with_data()

            prop (string or None): The name of the attribute in self.edit_obj
                whose value will be set to the contents of this widget. If
                None, no changes are made to self.edit_dict; it's up to the
                calling function to provide a .connect()

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The combobox widget created

        """

        store = Gtk.ListStore(str)
        for string in combo_list:
            store.append( [str(string)] )

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, x, y, wid, hei)
        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 0)
        combo.set_entry_text_column(0)

        if prop is not None:
            val = self.retrieve_val(prop)
            if val in combo_list:
                index = combo_list.index(val)
                combo.set_active(index)

            combo.connect('changed', self.on_combo_changed, prop)

        return combo


    def add_combo_with_data(self, grid, combo_list, prop, x, y, wid, hei):

        """Called by various functions in the child edit window.

        Adds a more complex Gtk.ComboBox to the tab's Gtk.Grid. This function
        expects a list of values in the form

            [ [val1, val2], [val1, val2], ... ]

        The combobox displays the 'val1' values. If one of them is selected,
        the corresponding 'val2' is used to set the attribute described by
        'prop'.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            combo_list (list): The list described above. For something more
                simple, see self.add_combo()

            prop (string or None): The name of the attribute in self.edit_obj
                whose value will be set to the contents of this widget. If
                None, no changes are made to self.edit_dict; it's up to the
                calling function to provide a .connect()

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The combobox widget created

        """

        store = Gtk.ListStore(str, str)

        index_list = []
        for mini_list in combo_list:
            store.append( [ str(mini_list[0]), str(mini_list[1]) ] )
            index_list.append(mini_list[1])

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, x, y, wid, hei)
        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 0)
        combo.set_entry_text_column(0)

        if prop is not None:
            val = self.retrieve_val(prop)
            if val in index_list:
                index = index_list.index(val)
                combo.set_active(index)

            combo.connect('changed', self.on_combo_with_data_changed, prop)

        return combo


    def add_entry(self, grid, prop, x, y, wid, hei):

        """Called by various functions in the child edit window.

        Adds a Gtk.Entry to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            prop (string or None): The name of the attribute in self.edit_obj
                whose value will be set to the contents of this widget. If
                None, no changes are made to self.edit_dict; it's up to the
                calling function to provide a .connect()

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The entry widget created

        """

        entry = Gtk.Entry()
        grid.attach(entry, x, y, wid, hei)
        entry.set_hexpand(True)

        if prop is not None:
            value = self.retrieve_val(prop)
            if value is not None:
                entry.set_text(str(value))

            entry.connect('changed', self.on_entry_changed, prop)

        return entry


#   def add_image               # Inherited from GenericConfigWin


    def add_label(self, grid, text, x, y, wid, hei):

        """Called by various functions in the child edit window.

        Adds a Gtk.Label to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            text (str): Pango markup displayed in the label

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The label widget created

        """

        label = Gtk.Label()
        grid.attach(label, x, y, wid, hei)
        label.set_markup(text)
        label.set_hexpand(True)
        label.set_alignment(0, 0.5)

        return label


    def add_radiobutton(self, grid, prev_button, text, prop, value, x, y, \
    wid, hei):

        """Called by various functions in the child edit window.

        Adds a Gtk.RadioButton to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            prev_button (Gtk.RadioButton or None): When this is the first
                radio button in the group, None. Otherwise, the previous
                radio button in the group. Use of this argument links the radio
                buttons together, ensuring that only one of them can be active
                at any time

            text (string or None): The text to display in the radiobutton's
                label. No label is used if 'text' is an empty string or None

            prop (string or None): The name of the attribute in self.edit_obj
                whose value will be set to the contents of this widget. If
                None, no changes are made to self.edit_dict; it's up to the
                calling function to provide a .connect()

            value (any): When this radiobutton becomes the active one, and if
                'prop' is not None, then 'prop' and 'value' are added as a new
                key-value pair to self.edit_dict

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The radiobutton widget created

        """

        radiobutton = Gtk.RadioButton.new_from_widget(prev_button)
        grid.attach(radiobutton, x, y, wid, hei)
        radiobutton.set_hexpand(True)
        if text is not None and text != '':
            radiobutton.set_label(text)

        if prop is not None:
            if value is not None and self.retrieve_val(prop) == value:
                radiobutton.set_active(True)

            radiobutton.connect(
                'toggled',
                self.on_radiobutton_toggled, prop, value,
            )

        return radiobutton


    def add_spinbutton(self, grid, min_val, max_val, step, prop, x, y, wid, \
    hei):

        """Called by various functions in the child edit window.

        Adds a Gtk.SpinButton to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            min_val (int): The minimum permitted in the spinbutton

            max_val (int or None): The maximum values permitted in the
                spinbutton. If None, this function assigns a very large maximum
                value (a billion)

            step (int): Clicking the up/down arrows in the spin button
                increments/decrements the value by this much

            prop (string or None): The name of the attribute in self.edit_obj
                whose value will be set to the contents of this widget. If
                None, no changes are made to self.edit_dict; it's up to the
                calling function to provide a .connect()

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The spinbutton widget created

        """

        # If the specified value of 'max_valu' was none, just use a very big
        #   number (as Gtk.SpinButton won't accept the None argument)
        if max_val is None:
            max_val = 1000000000

        spinbutton = Gtk.SpinButton.new_with_range(min_val, max_val, step)
        grid.attach(spinbutton, x, y, wid, hei)
        spinbutton.set_hexpand(False)

        if prop is not None:
            spinbutton.set_value(self.retrieve_val(prop))
            spinbutton.connect(
                'value-changed',
                self.on_spinbutton_changed,
                prop,
            )

        return spinbutton


    def add_textview(self, grid, prop, x, y, wid, hei):

        """Called by various functions in the child edit window.

        Adds a Gtk.TextView to the tab's Gtk.Grid. The contents of the textview
        are used as a single string (perhaps including newline characters) to
        set the value of a string attribute.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            prop (string or None): The name of the attribute in self.edit_obj
                whose value will be set to the contents of this widget. The
                attribute can be an integer, string, list or tuple. If None, no
                changes are made to self.edit_dict; it's up to the calling
                function to provide a .connect()

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The textview and textbuffer widgets created

        """

        frame = Gtk.Frame()
        grid.attach(frame, x, y, wid, hei)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        textview = Gtk.TextView()
        scrolled.add(textview)

        textbuffer = textview.get_buffer()

        if prop is not None:
            value = self.retrieve_val(prop)
            if value is not None:
                if type(value) is list or type(value) is tuple:
                    textbuffer.set_text(str.join('\n', value))
                else:
                    textbuffer.set_text(str(value))

            textbuffer.connect('changed', self.on_textview_changed, prop)

        return textview, textbuffer


#   def add_treeview            # Inherited from GenericConfigWin


    # Callback class methods


    def on_button_apply_clicked(self, button):

        """Called from a callback in self.setup_button_strip().

        Applies any changes made by the user and re-draws the window's tabs,
        showing their new values.

        Args:

            button (Gtk.Button): The widget clicked

        """

        # Apply any changes the user has made
        self.apply_changes()

        # Remove all existing tabs from the notebook
        number = self.notebook.get_n_pages()
        if number:

            for count in range(0, number):
                self.notebook.remove_page(0)

        # Re-draw all the tabs
        self.setup_tabs()

        # Render the changes
        self.show_all()


    def on_button_cancel_clicked(self, button):

        """Called from a callback in self.setup_button_strip().

        Destroys any changes made by the user and re-draws the window's tabs,
        showing their original values.

        Args:

            button (Gtk.Button): The widget clicked

        """

        # Destroy the window
        self.destroy()


    def on_button_ok_clicked(self, button):

        """Called from a callback in self.setup_button_strip().

        Destroys any changes made by the user and then closes the window.

        Args:

            button (Gtk.Button): The widget clicked

        """

        # Apply any changes the user has made
        self.apply_changes()

        # Destroy the window
        self.destroy()


    def on_button_reset_clicked(self, button):

        """Called from a callback in self.setup_button_strip().

        Destroys any changes made by the user and re-draws the window's tabs,
        showing their original values.

        Args:

            button (Gtk.Button): The widget clicked

        """

        # Remove all existing tabs from the notebook
        number = self.notebook.get_n_pages()
        if number:

            for count in range(0, number):
                self.notebook.remove_page(0)

        # Empty self.edit_dict, destroying any changes the user has made
        self.edit_dict = {}

        # Re-draw all the tabs
        self.setup_tabs()

        # Render the changes
        self.show_all()


    def on_checkbutton_toggled(self, checkbutton, prop):

        """Called from a callback in self.add_checkbutton().

        Adds a key-value pair to self.edit_dict, using True if the button is
        selected, False if not.

        Args:

            checkbutton (Gtk.CheckButton): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        if not checkbutton.get_active():
            self.edit_dict[prop] = False
        else:
            self.edit_dict[prop] = True


    def on_combo_changed(self, combo, prop):

        """Called from a callback in self.add_combo().

        Temporarily stores the contents of the widget in self.edit_dict.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.edit_dict[prop] = model[tree_iter][0]


    def on_combo_with_data_changed(self, combo, prop):

        """Called from a callback in self.add_combo_with_data().

        Extracts the value visible in the widget, converts it into another
        value, and stores the later in self.edit_dict.

        Args:

            combo (Gtk.ComboBox): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        tree_iter = combo.get_active_iter()
        model = combo.get_model()
        self.edit_dict[prop] = model[tree_iter][1]


    def on_entry_changed(self, entry, prop):

        """Called from a callback in self.add_entry().

        Temporarily stores the contents of the widget in self.edit_dict.

        Args:

            entry (Gtk.Entry): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        self.edit_dict[prop] = entry.get_text()


    def on_radiobutton_toggled(self, radiobutton, prop, value):

        """Called from a callback in self.add_radiobutton().

        Adds a key-value pair to self.edit_dict, but only if this radiobutton
        (from those in the group) is the selected one.

        Args:

            radiobutton (Gtk.RadioButton): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

            value (-): The attribute's new value

        """

        if radiobutton.get_active():
            self.edit_dict[prop] = value


    def on_spinbutton_changed(self, spinbutton, prop):

        """Called from a callback in self.add_spinbutton().

        Temporarily stores the contents of the widget in self.edit_dict.

        Args:

            spinbutton (Gtk.SpinkButton): The widget clicked

            prop (str): The attribute in self.edit_obj to modify

        """

        self.edit_dict[prop] = int(spinbutton.get_value())


    def on_textview_changed(self, textbuffer, prop):

        """Called from a callback in self.add_textview().

        Temporarily stores the contents of the widget in self.edit_dict.

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

        if type(old_value) is list or type(old_value) is tuple:
            self.edit_dict[prop] = text.splitlines()
        else:
            self.edit_dict[prop] = text


    # (Shared support functions)


    def add_container_properties(self, grid):

        """Called by VideoEditWin.setup_general_tab(),
        ChannelPlaylistEditWin.setup_general_tab() and
        FolderEditWin.setup_general_tab().

        Adds widgets common to those edit windows.

        Args:

            grid (Gtk.Grid): The grid on which widgets are arranged in their
                tab

        """

        entry = self.add_entry(grid,
            None,
            0, 1, 1, 1,
        )
        entry.set_text('#' + str(self.edit_obj.dbid))
        entry.set_editable(False)
        entry.set_hexpand(False)
        entry.set_width_chars(8)

        main_win_obj = self.app_obj.main_win_obj
        if isinstance(self.edit_obj, media.Video):
            icon_path = main_win_obj.icon_dict['video_small']
        elif isinstance(self.edit_obj, media.Channel):
            icon_path = main_win_obj.icon_dict['channel_small']
        elif isinstance(self.edit_obj, media.Playlist):
            icon_path = main_win_obj.icon_dict['playlist_small']
        else:

            if self.edit_obj.priv_flag:
                icon_path = main_win_obj.icon_dict['folder_red_small']
            elif self.edit_obj.temp_flag:
                icon_path = main_win_obj.icon_dict['folder_blue_small']
            elif self.edit_obj.fixed_flag:
                icon_path = main_win_obj.icon_dict['folder_green_small']
            else:
                icon_path = main_win_obj.icon_dict['folder_small']

        frame = self.add_image(grid,
            icon_path,
            1, 1, 1, 1,
        )
        # (The frame looks cramped without this. The icon itself is 16x16)
        frame.set_size_request(
            16 + (self.spacing_size * 2),
            -1,
        )

        entry2 = self.add_entry(grid,
            'name',
            2, 1, 1, 1,
        )
        entry2.set_editable(False)

        label = self.add_label(grid,
            _('Listed as'),
            0, 2, 1, 1,
        )
        label.set_hexpand(False)

        entry3 = self.add_entry(grid,
            'nickname',
            2, 2, 1, 1,
        )
        entry3.set_editable(True)

        label2 = self.add_label(grid,
            _('Contained in'),
            0, 3, 1, 1,
        )
        label2.set_hexpand(False)

        parent_obj = self.edit_obj.parent_obj
        if parent_obj:
            if isinstance(parent_obj, media.Channel):
                icon_path2 = main_win_obj.icon_dict['channel_small']
            elif isinstance(parent_obj, media.Playlist):
                icon_path2 = main_win_obj.icon_dict['playlist_small']
            else:

                if parent_obj.priv_flag:
                    icon_path2 = main_win_obj.icon_dict['folder_red_small']
                elif parent_obj.temp_flag:
                    icon_path2 = main_win_obj.icon_dict['folder_blue_small']
                elif parent_obj.fixed_flag:
                    icon_path2 = main_win_obj.icon_dict['folder_green_small']
                else:
                    icon_path2 = main_win_obj.icon_dict['folder_small']

        else:
            icon_path2 = main_win_obj.icon_dict['folder_black_small']

        frame2 = self.add_image(grid,
            icon_path2,
            1, 3, 1, 1,
        )
        frame2.set_size_request(
            16 + (self.spacing_size * 2),
            -1,
        )

        entry4 = self.add_entry(grid,
            None,
            2, 3, 1, 1,
        )
        entry4.set_editable(False)
        if parent_obj:
            entry4.set_text(parent_obj.name)

        if isinstance(self.edit_obj, media.Video):

            label3 = self.add_label(grid,
                _('Author'),
                0, 4, 1, 1,
            )
            label3.set_hexpand(False)

            entry5 = self.add_entry(grid,
                'author',
                2, 4, 1, 1,
            )
            entry5.set_editable(False)


    def add_destination_properties(self, grid):

        """Called by ChannelPlaylistEditWin.setup_general_tab() and
        FolderEditWin.setup_general_tab().

        Adds widgets common to those edit windows.

        Args:

            grid (Gtk.Grid): The grid on which widgets are arranged in their
                tab

        """

        label = self.add_label(grid,
            _('Download to'),
            0, 5, 1, 1,
        )
        label.set_hexpand(False)

        main_win_obj = self.app_obj.main_win_obj
        dest_obj = self.app_obj.media_reg_dict[self.edit_obj.master_dbid]

        if self.edit_obj.external_dir is not None:
            if self.edit_obj.dbid in self.app_obj.container_unavailable_dict:
                icon_path = main_win_obj.icon_dict['unavailable_small']
            else:
                icon_path = main_win_obj.icon_dict['external_small']
        elif isinstance(dest_obj, media.Channel):
            icon_path = main_win_obj.icon_dict['channel_small']
        elif isinstance(dest_obj, media.Playlist):
            icon_path = main_win_obj.icon_dict['playlist_small']
        else:

            if dest_obj.priv_flag:
                icon_path = main_win_obj.icon_dict['folder_red_small']
            elif dest_obj.temp_flag:
                icon_path = main_win_obj.icon_dict['folder_blue_small']
            elif dest_obj.fixed_flag:
                icon_path = main_win_obj.icon_dict['folder_green_small']
            else:
                icon_path = main_win_obj.icon_dict['folder_small']

        frame = self.add_image(grid,
            icon_path,
            1, 5, 1, 1,
        )
        frame.set_size_request(
            16 + (self.spacing_size * 2),
            -1,
        )

        entry = self.add_entry(grid,
            None,
            2, 5, 1, 1,
        )
        entry.set_editable(False)
        if self.edit_obj.external_dir is not None:
            entry.set_text(self.edit_obj.external_dir)
        else:
            entry.set_text(dest_obj.name)

        label2 = self.add_label(grid,
            _('Default location'),
            0, 6, 2, 1,
        )
        label2.set_hexpand(False)

        entry2 = self.add_entry(grid,
            None,
            2, 6, 1, 1,
        )
        entry2.set_editable(False)
        entry2.set_text(self.edit_obj.get_default_dir(self.app_obj))


    def add_source_properties(self, grid):

        """Called by VideoEditWin.setup_general_tab() and
        ChannelPlaylistEditWin.setup_general_tab().

        Adds widgets common to those edit windows.

        Args:

            grid (Gtk.Grid): The grid on which widgets are arranged in their
                tab

        """

        media_type = self.edit_obj.get_type()
        if media_type == 'channel':
            string = _('Channel URL')
        elif media_type == 'playlist':
            string = _('Playlist URL')
        else:
            string = _('Video URL')

        if isinstance(self.edit_obj, media.Video):
            row = 5
        else:
            row = 4

        label = self.add_label(grid,
            string,
            0, row, 1, 1,
        )
        label.set_hexpand(False)

        entry = self.add_entry(grid,
            'source',
            2, row, 1, 1,
        )
        entry.set_editable(False)


    def setup_download_options_tab(self):

        """Called by VideoEditWin.setup_tabs(),
        ChannelPlaylistEditWin.setup_tabs() and FolderEditWin.setup_tabs().

        Sets up the 'Download options' tab.
        """

        tab, grid = self.add_notebook_tab(_('_Options'))

        # (Many buttons are not clickable when a channel/playlist/folder's
        #   external directory is marked unavailable)
        unavailable_flag = False
        if isinstance(self.edit_obj, media.Video):
            if self.edit_obj.parent_obj.dbid \
            in self.app_obj.container_unavailable_dict:
                unavailable_flag = True
        elif self.edit_obj.dbid in self.app_obj.container_unavailable_dict:
            unavailable_flag = True

        # Download options
        self.add_label(grid,
            '<u>' + _('Download options') + '</u>',
            0, 0, 2, 1,
        )

        self.apply_options_button = Gtk.Button(_('Apply download options'))
        grid.attach(self.apply_options_button, 0, 1, 1, 1)
        self.apply_options_button.connect(
            'clicked',
            self.on_button_apply_options_clicked,
        )

        self.edit_options_button = Gtk.Button(_('Edit download options'))
        grid.attach(self.edit_options_button, 1, 1, 1, 1)
        self.edit_options_button.connect(
            'clicked',
            self.on_button_edit_options_clicked,
        )

        self.remove_options_button = Gtk.Button(_('Remove download options'))
        grid.attach(self.remove_options_button, 1, 2, 1, 1)
        self.remove_options_button.connect(
            'clicked',
            self.on_button_remove_options_clicked,
        )

        if self.edit_obj.options_obj or unavailable_flag:
            self.apply_options_button.set_sensitive(False)

        if not self.edit_obj.options_obj or unavailable_flag:
            self.edit_options_button.set_sensitive(False)
            self.remove_options_button.set_sensitive(False)


    # (Shared callbacks)


    def on_button_apply_options_clicked(self, button):

        """Called from callback in self.setup_download_options_tab().

        Apply download options to the media data object.

        Args:

            button (Gtk.Button): The widget clicked

        """

        if self.edit_obj.options_obj:
            return self.app_obj.system_error(
                401,
                'Download options already applied',
            )

        # Apply download options to the media data object
        self.app_obj.apply_download_options(self.edit_obj)
        # (De)sensitise buttons appropriately
        self.apply_options_button.set_sensitive(False)
        self.edit_options_button.set_sensitive(True)
        self.remove_options_button.set_sensitive(True)


    def on_button_edit_options_clicked(self, button):

        """Called from callback in self.setup_download_options_tab().

        Edit download options for the media data object.

        Args:

            button (Gtk.Button): The widget clicked

        """

        if not self.edit_obj.options_obj:
            return self.app_obj.system_error(
                402,
                'Download options not already applied',
            )

        # Open an edit window to show the options immediately
        OptionsEditWin(
            self.app_obj,
            self.edit_obj.options_obj,
        )


    def on_button_remove_options_clicked(self, button):

        """Called from callback in self.setup_download_options_tab().

        Remove download options from the media data object.

        Args:

            button (Gtk.Button): The widget clicked

        """

        if not self.edit_obj.options_obj:
            return self.app_obj.system_error(
                403,
                'Download options not already applied',
            )

        # Remove download options from the media data object
        self.app_obj.remove_download_options(self.edit_obj)
        # (De)sensitise buttons appropriately
        self.apply_options_button.set_sensitive(True)
        self.edit_options_button.set_sensitive(False)
        self.remove_options_button.set_sensitive(False)



class GenericPrefWin(GenericConfigWin):

    """Generic Python class for windows in which the user can modify various
    system settings.

    Any modifications are applied immediately (unlike in an 'edit window', in
    which the modifications are stored temporarily, and only applied once the
    user has finished making changes).
    """


    # Standard class methods


#   def __init__():             # Provided by child object


    # Public class methods


    def is_duplicate(self, app_obj):

        """Called by self.__init__.

        Don't open this preference window, if another preference window of the
        same class is already open.

        Args:

            app_obj (mainapp.TartubeApp): The main application object

        Return values:

            True if a duplicate is found, False if not

        """

        for config_win_obj in app_obj.main_win_obj.config_win_list:

            if type(self) == type(config_win_obj):

                # Duplicate found
                config_win_obj.present()
                return True

        # Not a duplicate
        return False


#   def setup():                # Inherited from GenericConfigWin


#   def setup_grid():           # Inherited from GenericConfigWin


#   def setup_notebook():       # Inherited from GenericConfigWin


#   def add_notebook_tab():     # Inherited from GenericConfigWin


    def setup_button_strip(self):

        """Called by self.setup().

        Creates a strip of buttons at the bottom of the window. For preference
        windows, there is only a single 'OK' button, which closes the window.
        """

        hbox = Gtk.HBox()
        self.grid.attach(hbox, 0, 2, 1, 1)

        # 'OK' button
        self.ok_button = Gtk.Button(_('OK'))
        hbox.pack_end(self.ok_button, False, False, self.spacing_size)
        self.ok_button.get_child().set_width_chars(10)
        self.ok_button.set_tooltip_text(_('Close this window'));
        self.ok_button.connect('clicked', self.on_button_ok_clicked)


#   def setup_gap():            # Inherited from GenericConfigWin


    # (Non-widget functions)


    def reset_window(self):

        """Can be called by anything.

        Redraws the window, without the need to destroy the old one and replace
        it with a new one.
        """

        # This code is copied from
        #   config.GenericEditWin.on_button_reset_clicked()

        # Remove all existing tabs from the notebook
        number = self.notebook.get_n_pages()
        if number:

            for count in range(0, number):
                self.notebook.remove_page(0)

        # Re-draw all the tabs
        self.setup_tabs()

        # Render the changes
        self.show_all()


    # (Add widgets)


    def add_checkbutton(self, grid, text, set_flag, mod_flag, x, y, wid, hei):

        """Called by various functions in the child preference window.

        Adds a Gtk.CheckButton to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            text (string or None): The text to display in the checkbutton's
                label. No label is used if 'text' is an empty string or None

            set_flag (bool): True if the checkbutton is selected

            mod_flag (bool): True if the checkbutton can be toggled by the user

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The checkbutton widget created

        """

        checkbutton = Gtk.CheckButton()
        grid.attach(checkbutton, x, y, wid, hei)
        checkbutton.set_active(set_flag)
        checkbutton.set_sensitive(mod_flag)
        checkbutton.set_hexpand(True)
        if text is not None and text != '':
            checkbutton.set_label(text)

        return checkbutton


    def add_combo(self, grid, combo_list, active_val, x, y, wid, hei):

        """Called by various functions in the child preference window.

        Adds a simple Gtk.ComboBox to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            combo_list (list): A list of values to display in the combobox.
                This function expects a simple, one-dimensional list

            active_val (string or None): If not None, a value matching one of
                the items in combo_list, that should be the active row in the
                combobox

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The combobox widget created

        """

        store = Gtk.ListStore(str)

        count = -1
        active_index = 0
        for string in combo_list:
            store.append( [string] )

            count += 1
            if active_val is not None and active_val == string:
                active_index = count

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, x, y, wid, hei)
        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 0)
        combo.set_entry_text_column(0)
        combo.set_active(active_index)

        return combo


    def add_combo_with_data(self, grid, combo_list, active_val, x, y, wid,
    hei):

        """Called by various functions in the child preference window.

        Adds a more complex Gtk.ComboBox to the tab's Gtk.Grid. This function
        expects a list of values in the form

            [ [val1, val2], [val1, val2], ... ]

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            combo_list (list): The list described above. For something more
                simple, see self.add_combo()

            active_val (string or None): If not None, a value matching a
                the second item ('val2') in one of the combo_list pairs; the
                specified pair is the active row in the combobox

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The combobox widget created

        """

        store = Gtk.ListStore(str, str)

        count = -1
        active_index = 0
        for mini_list in combo_list:
            store.append( [ str(mini_list[0]), str(mini_list[1]) ] )

            count += 1
            if active_val is not None and active_val == mini_list[1]:
                active_index = count

        combo = Gtk.ComboBox.new_with_model(store)
        grid.attach(combo, x, y, wid, hei)
        renderer_text = Gtk.CellRendererText()
        combo.pack_start(renderer_text, True)
        combo.add_attribute(renderer_text, 'text', 0)
        combo.set_entry_text_column(0)
        combo.set_active(active_index)

        return combo


    def add_entry(self, grid, text, edit_flag, x, y, wid, hei):

        """Called by various functions in the child preference window.

        Adds a Gtk.Entry to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            text (string or None): The initial contents of the entry.

            edit_flag (bool): True if the contents of the entry can be edited

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The entry widget created

        """

        entry = Gtk.Entry()
        grid.attach(entry, x, y, wid, hei)
        entry.set_hexpand(True)

        if text is not None:
            entry.set_text(str(text))

        if not edit_flag:
            entry.set_editable(False)

        return entry


#   def add_image               # Inherited from GenericConfigWin


    def add_label(self, grid, text, x, y, wid, hei):

        """Called by various functions in the child preference window.

        Adds a Gtk.Label to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            text (str): Pango markup displayed in the label

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The label widget created

        """

        label = Gtk.Label()
        grid.attach(label, x, y, wid, hei)
        label.set_markup(text)
        label.set_hexpand(True)
        label.set_alignment(0, 0.5)

        return label


    def add_radiobutton(self, grid, prev_button, text, x, y, wid, hei):

        """Called by various functions in the child preference window.

        Adds a Gtk.RadioButton to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            prev_button (Gtk.RadioButton or None): When this is the first
                radio button in the group, None. Otherwise, the previous
                radio button in the group. Use of this argument links the radio
                buttons together, ensuring that only one of them can be active
                at any time

            text (string or None): The text to display in the radiobutton's
                label. No label is used if 'text' is an empty string or None

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The radiobutton widget created

        """

        radiobutton = Gtk.RadioButton.new_from_widget(prev_button)
        grid.attach(radiobutton, x, y, wid, hei)
        radiobutton.set_hexpand(True)
        if text is not None and text != '':
            radiobutton.set_label(text)

        return radiobutton


    def add_spinbutton(self, grid, min_val, max_val, step, val, x, y, wid, \
    hei):

        """Called by various functions in the child preference window.

        Adds a Gtk.SpinButton to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            min_val (int): The minimum permitted in the spinbutton

            max_val (int or None): The maximum values permitted in the
                spinbutton. If None, this function assigns a very large maximum
                value (a billion)

            step (int): Clicking the up/down arrows in the spin button
                increments/decrements the value by this much

            val (int): The current value of the spinbutton

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The spinbutton widget created

        """

        # If the specified value of 'max_valu' was none, just use a very big
        #   number (as Gtk.SpinButton won't accept the None argument)
        if max_val is None:
            max_val = 1000000000

        spinbutton = Gtk.SpinButton.new_with_range(min_val, max_val, step)
        grid.attach(spinbutton, x, y, wid, hei)
        spinbutton.set_value(val)
        spinbutton.set_hexpand(False)

        return spinbutton


    def add_textview(self, grid, contents_list, x, y, wid, hei):

        """Called by various functions in the child preference window.

        Adds a Gtk.TextView to the tab's Gtk.Grid.

        Args:

            grid (Gtk.Grid): The grid on which this widget will be placed

            contents_list (list): The initial contents of the textview. Each
                item in the list is a line in the textview.

            x, y, wid, hei (int): Position on the grid at which the widget is
                placed

        Return values:

            The textview and textbuffer widgets created

        """

        frame = Gtk.Frame()
        grid.attach(frame, x, y, wid, hei)

        scrolled = Gtk.ScrolledWindow()
        frame.add(scrolled)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        textview = Gtk.TextView()
        scrolled.add(textview)

        textbuffer = textview.get_buffer()

        if contents_list:
            textbuffer.set_text(str.join('\n', contents_list))

        return textview, textbuffer


#   def add_treeview            # Inherited from GenericConfigWin


    # Callback class methods


    def on_button_ok_clicked(self, button):

        """Called from a callback in self.setup_button_strip().

        Closes the window.

        Args:

            button (Gtk.Button): The button clicked

        """

        # Destroy the window
        self.destroy()
