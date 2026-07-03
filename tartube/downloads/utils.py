#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from .queue import DownloadItem

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


"""Download and livestream operation classes."""


# Import Gtk modules
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject


# Import other modules
import datetime
import json
import __main__
import os
import queue
import random
import re
import requests
import shutil
import signal
import subprocess
import sys
import threading
import time


# Import our modules
import formats
import mainapp
import media
import options
import ttutils
# Use same gettext translations
from mainapp import _

if mainapp.HAVE_FEEDPARSER_FLAG:
    import feedparser


# Debugging flag (calls ttutils.debug_time() at the start of every function)
DEBUG_FUNC_FLAG = False


# Decorator to add thread synchronisation to some functions in the
#   downloads.DownloadList object
_SYNC_LOCK = threading.RLock()

def synchronise(lock):
    def _decorator(func):
        def _wrapper(*args, **kwargs):
            lock.acquire()
            ret_value = func(*args, **kwargs)
            lock.release()
            return ret_value
        return _wrapper
    return _decorator


# Classes
class CustomDLManager(object):

    """Called by mainapp.TartubeApp.create_custom_dl_manager().

    Python class to store settings for a custom download. The user can create
    as many instances of this object as they like, and can launch a custom
    download using settings from any of them.

    Args:

        uid (int): Unique ID for this custom download manager (unique only to
            this class of objects)

        name (str): Non-unique name forthis custom download manager

    """


    # Standard class methods


    def __init__(self, uid, name):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11619 __init__')

        # IV list - other
        # ---------------
        # Unique ID for this custom download manager
        self.uid = uid
        # A non-unique name for this custom download manager
        self.name = name

        # If True, during a custom download, download every video which is
        #   marked as not downloaded (often after clicking the 'Check all'
        #   button); don't download channels/playlists directly
        self.dl_by_video_flag = False
        # If True, during a custom download, perform a simulated download first
        #   (as happens by default in custom downloads launched from the
        #   Classic Mode tab). Ignored if self.dl_by_video_flag is False
        self.dl_precede_flag = False

        # If True, during a custom download, only download the video if
        #   subtitles are available for it. Ignored if self.dl_precede_flag is
        #   False
        self.dl_if_subs_flag = False
        # If set, during the checking stage of a custom download, don't add
        #   (checked) videos to Tartube's database. Ignored if
        #   self.dl_if_subs_flag is False
        self.ignore_if_no_subs_flag = False
        # If set, during a custom download, only download the video if
        #   subtitles in any of these formats are available for it. Each item
        #   in the list is a value in formats.LANGUAGE_CODE_DICT (e.g. 'en',
        #   'live_chat'). Ignored if self.dl_if_subs_flag is False
        self.dl_if_subs_list = []

        # If True, during a custom download, split a video into video clips
        #   using its timestamps. Ignored if self.dl_by_video_flag is False
        # Note that IVs for splitting videos (e.g.
        #   mainapp.TartubeApp.split_video_name_mode) apply in this situation
        #   as well
        self.split_flag = False
        # If True, during a custom download, video slices identified by
        #   SponsorBlock are removed. Ignored if self.dl_by_video_flag is
        #   False, or if self.split_flag is True
        self.slice_flag = False
        # A dictionary specifying which categories of video slice should be
        #   removed. Keys are SponsorBlock categories; values are True to
        #   remove the slice, False to retain it
        # NB A sorted list of keys from this dictionary appears in
        #   formats.SPONSORBLOCK_CATEGORY_LIST
        self.slice_dict = {
            'sponsor': True,
            'selfpromo': False,
            'interaction': False,
            'intro': False,
            'outro': False,
            'preview': False,
            'music_offtopic': False,
        }
        # If True, during a custom download, a delay (in minutes) is applied
        #   between media data object downloads. When applied to a
        #   channel/playlist, the delay occurs after the whole channel/
        #   playlist. When applied directly to videos, the delay occurs after
        #   each video
        # NB The delay is applied during real downloads, but not during
        #   simulated downloads (operation types 'custom_sim' or 'classic_sim')
        self.delay_flag = False
        # The maximum delay to apply (in minutes, minimum value 0.2). Ignored
        #   if self.delay_flag is False
        self.delay_max = 5
        # The minimum delay to apply (in minutes, minimum value 0, maximum
        #   value self.delay_max). If specified, the delay is a random length
        #   of time between this value and self.delay_max. Ignored if
        #   self.delay_flag is False
        self.delay_min = 0

        # During a custom download, any videos whose source URL is YouTube can
        #   be diverted to another website. This IV uses the values:
        #       'default' - Use the original YouTube URL
        #       'hooktube' - Divert to hooktube.com
        #       'invidious' - Divert to invidio.us
        #       'other' - user enters their own alternative front-end website
        self.divert_mode = 'default'
        # If self.divert_mode is 'other', the address of the YouTube
        #   alternative. The string directly replaces the 'youtube.com' part of
        #   a URL; so the string must be something like 'hooktube.com' not
        #   'http://hooktube.com' or anything like that
        # Ignored if it does not contain at least 3 characters. Ignored for any
        #   other value of self.divert_mode
        self.divert_website = ''

        # If True, don't download broadcasting livestreams. Ignored if
        #   self.dl_by_video_flag is False
        self.ignore_stream_flag = False
        # If True, don't download finished livestreams. Ignored if
        #   self.dl_by_video_flag is False
        self.ignore_old_stream_flag = False
        # If True, only download broadcasting livestreams. Ignored if
        #   self.dl_by_video_flag is False. Mutually incompatible with
        #   self.ignore_stream_flag
        self.dl_if_stream_flag = False
        # If True, only download finished livestreams. Ignored if
        #   self.dl_by_video_flag is False. Mutually incompatible with
        #   self.ignore_old_stream_flag
        self.dl_if_old_stream_flag = False


    # Public class methods


    def clone_settings(self, other_obj):

        """Called by mainapp.TartubeApp.clone_custom_dl_manager_from_window().

        Clones custom download settings from the specified object into this
        object, completely replacing this object's settings.

        Args:

            other_obj (downloads.CustomDLManager): The custom download manager
                object (usually the current one), from which settings will be
                cloned

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11742 clone_settings')

        self.dl_by_video_flag = other_obj.dl_by_video_flag
        self.dl_if_subs_flag = other_obj.dl_if_subs_flag
        self.ignore_if_no_subs_flag = other_obj.ignore_if_no_subs_flag
        self.dl_if_subs_list = other_obj.dl_if_subs_list
        self.split_flag = other_obj.split_flag
        self.slice_flag = other_obj.slice_flag
        self.slice_dict = other_obj.slice_dict.copy()
        self.divert_mode = other_obj.divert_mode
        self.divert_website = other_obj.divert_website
        self.delay_flag = other_obj.delay_flag
        self.delay_min = other_obj.delay_min


    def reset_settings(self):

        """Currently not called by anything (but might be needed in the
        future).

        Resets settings to their default values.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11766 reset_settings')

        self.dl_by_video_flag = False
        self.dl_if_subs_flag = False
        self.ignore_if_no_subs_flag = False
        self.dl_if_subs_list = []
        self.split_flag = False
        self.slice_flag = False
        self.slice_dict = {
            'sponsor': True,
            'selfpromo': False,
            'interaction': False,
            'intro': False,
            'outro': False,
            'preview': False,
            'music_offtopic': False,
        }
        self.divert_mode = 'default'
        self.divert_website = ''
        self.delay_flag = False
        self.delay_max = 5
        self.delay_min = 0


    def set_dl_precede_flag(self, flag):

        """Can be called by anything. Mostly called by
        mainapp.TartubeApp.start() and .set_dl_precede_flag().

        Updates the IV.

        Args:

            flag (bool): The new value of the IV

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11804 set_dl_precede_flag')

        if not flag:
            self.dl_precede_flag = False
        else:
            self.dl_by_video_flag = True
            self.dl_precede_flag = True


class PipeReader(threading.Thread):

    """Called by downloads.VideoDownloader.__init__().

    Based on the PipeReader class in youtube-dl-gui.

    Python class used by downloads.VideoDownloader, downloads.ClipDownloader,
    downloads.StreamDownloader, downloads.JSONFetcher,
    downloads.MiniJSONFetcher, info.InfoManager and updates.UpdateManager,
    to avoid deadlocks when reading from child process pipes STDOUT and STDERR.

    This class uses python threads and queues in order to read from child
    process pipes in an asynchronous way.

    Args:

        queue (queue.PriorityQueue): Python queue to store the output of the
            child process

        pipe_type (str): This object reads from either 'stdout' or 'stderr'

    Warnings:

        All the actions are based on 'str' types. The calling function must
        convert the queued items back to 'unicode', if necessary

    """


    # Standard class methods


    def __init__(self, queue, pipe_type):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11848 __init__')

        super(PipeReader, self).__init__()

        # IV list - other
        # ---------------
        # Python queue.PriorityQueue to store the output of the child process
        self.queue = queue
        # This object reads from either 'stdout' or 'stderr'
        self.pipe_type = pipe_type

        # The time (in seconds) between iterations of the loop in self.run()
        # Without some kind of delay, the GUI interface becomes sluggish. The
        #   length of the delay doesn't matter, so make it as short as
        #   reasonably possible
        self.sleep_time = 0.001
        # Flag that is set to False by self.join(), which enables the loop in
        #   self.run() to terminate
        self.running_flag = True
        # Set by self.attach_fh(). The filehandle for the child process STDOUT
        #   or STDERR, e.g. downloads.VideoDownloader.child_process.stdout
        self.fh = None


        # Code
        # ----

        # Let's get this party started!
        self.start()


    # Public class methods


    def run(self):

        """Called as a result of self.__init__().

        Reads from STDOUT or STERR using the attached filed filehandle.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11890 run')

        # Use this flag so that the loop can ignore FFmpeg error messsages
        #   (because the parent VideoDownloader object shouldn't use that as a
        #   serious error)
        ignore_line = False

        while self.running_flag:

            if self.fh is not None:

                # Read the filehandle until the sentinel line (matching '') is
                #   found, marking the end of the file; see
                #   https://stackoverflow.com/questions/52446415/
                #   line-in-iterfp-readline-rather-than-line-in-fp
                for line in iter(self.fh.readline, str('')):

                    if line == b'':
                        # End of file
                        break

                    if str.encode('ffmpeg version') in line:
                        ignore_line = True

                    if not ignore_line:

                        # Add a tuple to the queue.PriorityQueue. The queue's
                        #   entries are sorted by the first item of the tuple,
                        #   so the queue is read in the correct order
                        self.queue.put_nowait(
                            [time.time(), self.pipe_type, line],
                        )

                self.fh = None
                ignore_line = False

            # This delay is required; see the comments in self.__init__()
            time.sleep(self.sleep_time)


    def attach_fh(self, fh):

        """Called by downloads.VideoDownloader.do_download() and comparable
        functions.

        Sets the filehandle for the child process STDOUT or STDERR, e.g.
        downloads.VideoDownloader.child_process.stdout

        Args:

            fh (filehandle): The open filehandle for STDOUT or STDERR

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11945 attach_fh')

        self.fh = fh


    def join(self, timeout=None):

        """Called by downloads.VideoDownloader.close(), which is the destructor
        function for that object.

        Join the thread and update IVs.

        Args:

            timeout (-): No calling code sets a timeout

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11964 join')

        self.running_flag = False
        super(PipeReader, self).join(timeout)
