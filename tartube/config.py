#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2026 A S Lewis
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Configuration window classes (Facade).
This module has been refactored. The actual classes now reside in the
`tartube.preferences` package. They are imported here for backwards compatibility.
"""

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


# Export all preference window classes
from tartube.preferences.base import GenericConfigWin, GenericEditWin, GenericPrefWin
from tartube.preferences.editors.custom_dl import CustomDLEditWin
from tartube.preferences.editors.options import OptionsEditWin
from tartube.preferences.editors.ffmpeg import FFmpegOptionsEditWin
from tartube.preferences.editors.video import VideoEditWin
from tartube.preferences.editors.channel_playlist import ChannelPlaylistEditWin
from tartube.preferences.editors.folder import FolderEditWin
from tartube.preferences.editors.scheduled import ScheduledEditWin
from tartube.preferences.system_prefs import SystemPrefWin

