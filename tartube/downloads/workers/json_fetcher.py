#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ..queue import DownloadItem
from ..utils import PipeReader

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
class JSONFetcher(object):

    """Called by downloads.DownloadWorker.check_rss().

    Python class to download JSON data for a video which is believed to be a
    livestream, using youtube-dl.

    The video has been found in the channel's/playlist's RSS feed, but not by
    youtube-dl, when the channel/playlist was last checked downloaded.

    If the data can be downloaded, we assume that the livestream is currently
    broadcasting. If we get a 'This video is unavailable' error, we assume that
    the livestream is waiting to start.

    This is the behaviour exhibited on YouTube. It might work on other
    compatible websites, too, if the user has set manually set the URL for the
    channel/playlist RSS feed.

    This class creates a system child process and uses the child process to
    instruct youtube-dl to fetch the JSON data for the video.

    Reads from the child process STDOUT and STDERR, having set up a
    downloads.PipeReader object to do so in an asynchronous way.

    If one of the two outcomes described above takes place, the media.Video
    object's IVs are updated to mark it as a livestream.

    Args:

        download_manager_obj (downloads.DownloadManager): The download manager
            object handling the entire download operation

        download_worker_obj (downloads.DownloadWorker): The parent download
            worker object. The download manager uses multiple workers to
            implement simultaneous downloads. The download manager checks for
            free workers and, when it finds one, assigns it a
            download.DownloadItem object. When the worker is assigned a
            download item, it creates a new instance of this object for each
            detected livestream, and waits for this object to complete its
            task

        container_obj (media.Channel, media.Playlist): The channel/playlist
            in which a livestream has been detected

        entry_dict (dict): A dictionary of values generated when reading the
            RSS feed (provided by the Python feedparser module. The dictionary
            represents available data for a single livestream video

    Warnings:

        The calling function is responsible for calling the close() method
        when it's finished with this object, in order for this object to
        properly close down.

    """


    # Standard class methods


    def __init__(self, download_manager_obj, download_worker_obj, \
    container_obj, entry_dict):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10668 __init__')

        # IV list - class objects
        # -----------------------
        # The downloads.DownloadManager object handling the entire download
        #   operation
        self.download_manager_obj = download_manager_obj
        # The parent downloads.DownloadWorker object
        self.download_worker_obj = download_worker_obj
        # The media.Channel or media.Playlist object in which a livestream has
        #   been detected
        self.container_obj = container_obj

        # The child process created by self.create_child_process()
        self.child_process = None

        # Read from the child process STDOUT (i.e. self.child_process.stdout)
        #   and STDERR (i.e. self.child_process.stderr) in an asynchronous way
        #   by polling this queue.PriorityQueue object
        self.queue = queue.PriorityQueue()
        self.stdout_reader = PipeReader(self.queue, 'stdout')
        self.stderr_reader = PipeReader(self.queue, 'stderr')


        # IV list - other
        # ---------------
        # A dictionary of values generated when reading the RSS feed (provided
        #   by the Python feedparser module. The dictionary represents
        #   available data for a single livestream video
        self.entry_dict = entry_dict
        # Important data is extracted from the entry (below), and added to
        #   these IVs, ready for use
        self.video_name = None
        self.video_source = None
        self.video_descrip = None
        self.video_thumb_source = None
        self.video_upload_time = None

        # The time (in seconds) between iterations of the loop in
        #   self.do_fetch()
        self.sleep_time = 0.1


        # Code
        # ----
        # Initialise IVs from the RSS feed entry for the livestream video
        #   (saves a bit of time later)
        if 'title' in entry_dict:
            self.video_name = entry_dict['title']

        if 'link' in entry_dict:
            self.video_source = entry_dict['link']

        if 'summary' in entry_dict:
            self.video_descrip = entry_dict['summary']

        if 'media_thumbnail' in entry_dict \
        and entry_dict['media_thumbnail'] \
        and 'url' in entry_dict['media_thumbnail'][0]:
            self.video_thumb_source = entry_dict['media_thumbnail'][0]['url']

        if 'published_parsed' in entry_dict:

            try:
                # A time.struct_time object; convert to Unix time, to match
                #   media.Video.upload_time
                dt_obj = datetime.datetime.fromtimestamp(
                    time.mktime(entry_dict['published_parsed']),
                )

                self.video_upload_time = int(dt_obj.timestamp())

            except:
                self.video_upload_time = None


    # Public class methods


    def do_fetch(self):

        """Called by downloads.DownloadWorker.check_rss().

        Downloads JSON data for the livestream video whose URL is
        self.video_source.

        If the data can be downloaded, we assume that the livestream is
        currently broadcasting. If we get a 'This video is unavailable' error,
        we assume that the livestream is waiting to start.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10760 do_fetch')

        # Import the main app (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Convert a youtube-dl path beginning with ~ (not on MS Windows)
        #   (code copied from ttutils.generate_ytdl_system_cmd() )
        ytdl_path = app_obj.check_downloader(app_obj.ytdl_path)
        if os.name != 'nt':
            ytdl_path = re.sub(r'^\~', os.path.expanduser('~'), ytdl_path)

        # Generate the system command (but don't display it in the Output tab)
        if app_obj.ytdl_path_custom_flag:
            cmd_list = ['python3'] + [ytdl_path] + ['--dump-json'] \
            + [self.video_source]
        else:
            cmd_list = [ytdl_path] + ['--dump-json'] + [self.video_source]

        # Create a new child process using that command...
        self.create_child_process(cmd_list)
        # ...and set up the PipeReader objects to read from the child process'
        #   STDOUT and STDERR
        if self.child_process is not None:
            self.stdout_reader.attach_fh(self.child_process.stdout)
            self.stderr_reader.attach_fh(self.child_process.stderr)

        # Wait for the process to finish
        while self.is_child_process_alive():

            # Pause a moment between each iteration of the loop (we don't want
            #   to hog system resources)
            time.sleep(self.sleep_time)

        # Process has finished. Read from STDOUT and STDERR
        if self.read_child_process():

            # Download the video's thumbnail, if possible
            if self.video_thumb_source:

                # Get the thumbnail's extension...
                remote_file, remote_ext = os.path.splitext(
                    self.video_thumb_source,
                )

                # ...and thus get the filename used by youtube-dl when storing
                #   the thumbnail locally (assuming that the video's name, and
                #   the filename when it is later downloaded, are the same)
                local_thumb_path = os.path.abspath(
                    os.path.join(
                        self.container_obj.get_actual_dir(app_obj),
                        self.video_name + remote_ext,
                    ),
                )

                options_obj = self.download_worker_obj.options_manager_obj
                if not options_obj.options_dict['sim_keep_thumbnail']:
                    local_thumb_path = ttutils.convert_path_to_temp_dl_dir(
                        app_obj,
                        local_thumb_path,
                    )

                elif options_obj.options_dict['move_thumbnail']:
                    local_thumb_path = os.path.abspath(
                        os.path.join(
                            self.container_obj.get_actual_dir(app_obj),
                            app_obj.thumbs_sub_dir,
                            self.video_name + remote_ext,
                        )
                    )

                if local_thumb_path:
                    try:
                        request_obj = requests.get(
                            self.video_thumb_source,
                            timeout = app_obj.request_get_timeout,
                        )

                        with open(local_thumb_path, 'wb') as outfile:
                            outfile.write(request_obj.content)

                    except:
                        pass

                # Convert .webp thumbnails to .jpg, if required
                if local_thumb_path is not None \
                and not app_obj.ffmpeg_fail_flag \
                and app_obj.ffmpeg_convert_webp_flag \
                and not app_obj.ffmpeg_manager_obj.convert_webp(
                    local_thumb_path
                ):
                    app_obj.set_ffmpeg_fail_flag(True)
                    GObject.timeout_add(
                        0,
                        app_obj.system_error,
                        314,
                        app_obj.ffmpeg_fail_msg,
                    )


    def close(self):

        """Called by downloads.DownloadWorker.check_rss().

        Destructor function for this object.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10876 close')

        # Tell the PipeReader objects to shut down, thus joining their threads
        self.stdout_reader.join()
        self.stderr_reader.join()


    def create_child_process(self, cmd_list):

        """Called by self.do_fetch().

        Based on YoutubeDLDownloader._create_process().

        Executes the system command, creating a new child process which
        executes youtube-dl.

        Args:

            cmd_list (list): Python list that contains the command to execute

        Return values:

            True on success, False on an error

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10894 create_child_process')

        # Strip double quotes from arguments
        # (Since we're sending the system command one argument at a time, we
        #   don't need to retain the double quotes around any single argument
        #   and, in fact, doing so would cause an error)
        cmd_list = ttutils.strip_double_quotes(cmd_list)

        # Create the child process
        info = preexec = None

        if os.name == 'nt':
            # Hide the child process window that MS Windows helpfully creates
            #   for us
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            # Make this child process the process group leader, so that we can
            #   later kill the whole process group with os.killpg
            preexec = os.setsid

        try:
            self.child_process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=preexec,
                startupinfo=info,
            )

            return True

        except (ValueError, OSError) as error:
            # (Errors are expected and frequent)
            return False


    def is_child_process_alive(self):

        """Called by self.do_fetch() and self.stop().

        Based on YoutubeDLDownloader._proc_is_alive().

        Called continuously during the self.do_fetch() loop to check whether
        the child process has finished or not.

        Return values:

            True if the child process is alive, otherwise returns False.

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10947 is_child_process_alive')

        if self.child_process is None:
            return False

        return self.child_process.poll() is None


    def read_child_process(self):

        """Called by self.do_fetch().

        Reads from the child process STDOUT and STDERR, in the correct order.

        For this JSONFetcher object, the order doesn't matter very much: we
        are expecting data in either STDOUT or STDERR.

        Return values:

            True if either STDOUT or STDERR were read, None if both queues were
                empty

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10972 read_child_process')

        # mini_list is in the form [time, pipe_type, data]
        try:
            mini_list = self.queue.get_nowait()

        except:
            # Nothing left to read
            return None

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Failsafe check
        if not mini_list \
        or (mini_list[1] != 'stdout' and mini_list[1] != 'stderr'):

            # Just in case...
            GObject.timeout_add(
                0,
                self.download_manager_obj.app_obj.system_error,
                315,
                'Malformed STDOUT or STDERR data',
            )

        # STDOUT or STDERR has been read
        data = mini_list[2].rstrip()
        # Convert bytes to string
        data = data.decode(ttutils.get_encoding(), 'replace')

        # STDOUT
        if mini_list[1] == 'stdout':

            if data[:1] == '{':

                # Broadcasting livestream detected; create a new media.Video
                #   object
                GObject.timeout_add(
                    0,
                    app_obj.create_livestream_from_download,
                    self.container_obj,
                    2,                      # Livestream has started
                    self.video_name,
                    self.video_source,
                    self.video_descrip,
                    self.video_upload_time,
                )

        # STDERR (ignoring any empty error messages)
        elif data != '':

            live_data_dict = ttutils.extract_livestream_data(data)
            if live_data_dict:

                # Waiting livestream detected; create a new media.Video object
                GObject.timeout_add(
                    0,
                    app_obj.create_livestream_from_download,
                    self.container_obj,
                    1,                  # Livestream waiting to start
                    self.video_name,
                    self.video_source,
                    self.video_descrip,
                    self.video_upload_time,
                    live_data_dict,
                )

        # Either (or both) of STDOUT and STDERR were non-empty
        self.queue.task_done()
        return True


    def stop(self):

        """Called by DownloadWorker.close().

        Terminates the child process.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11052 stop')

        if self.is_child_process_alive():

            if os.name == 'nt':
                # os.killpg is not available on MS Windows (see
                #   https://bugs.python.org/issue5115 )
                self.child_process.kill()

                # When we kill the child process on MS Windows the return code
                #   gets set to 1, so we want to reset the return code back to
                #   0
                self.child_process.returncode = 0

            else:
                os.killpg(self.child_process.pid, signal.SIGKILL)


class MiniJSONFetcher(object):

    """Called by downloads.StreamManager.run().

    A modified version of downloads.JSONFetcher (the former is called by
    downloads.DownloadWorker only; using a second Python class for the same
    objective makes the code somewhat simpler).

    Python class to fetch JSON data for a livestream video, using youtube-dl.

    Creates a system child process and uses the child process to instruct
    youtube-dl to fetch the JSON data for the video.

    Reads from the child process STDOUT and STDERR, having set up a
    downloads.PipeReader object to do so in an asynchronous way.

    Args:

        livestream_manager_obj (downloads.StreamManager): The livestream
            manager object handling the entire livestream operation

        video_obj (media.Video): The livestream video whose JSON data should be
            fetched (the equivalent of right-clicking the video in the Video
            Catalogue, and selecting 'Check this video')

    """


    # Standard class methods


    def __init__(self, livestream_manager_obj, video_obj):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11234 __init__')

        # IV list - class objects
        # -----------------------
        # The downloads.StreamManager object handling the entire livestream
        #   operation
        self.livestream_manager_obj = livestream_manager_obj
        # The media.Video object for which new JSON data must be fetched
        #   (the equivalent of right-clicking the video in the Video Catalogue,
        #   and selecting 'Check this video')
        self.video_obj = video_obj

        # The child process created by self.create_child_process()
        self.child_process = None

        # Read from the child process STDOUT (i.e. self.child_process.stdout)
        #   and STDERR (i.e. self.child_process.stderr) in an asynchronous way
        #   by polling this queue.PriorityQueue object
        self.queue = queue.PriorityQueue()
        self.stdout_reader = PipeReader(self.queue, 'stdout')
        self.stderr_reader = PipeReader(self.queue, 'stderr')


        # IV list - other
        # ---------------
        # The time (in seconds) between iterations of the loop in
        #   self.do_fetch()
        self.sleep_time = 0.1


    # Public class methods


    def do_fetch(self):

        """Called by downloads.StreamManager.run().

        Downloads JSON data for the livestream video, self.video_obj.

        If the data can be downloaded, we assume that the livestream is
        currently broadcasting. If we get a 'This video is unavailable' error,
        we assume that the livestream is waiting to start.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11279 do_fetch')

        # Import the main app (for convenience)
        app_obj = self.livestream_manager_obj.app_obj

        # Convert a youtube-dl path beginning with ~ (not on MS Windows)
        #   (code copied from ttutils.generate_ytdl_system_cmd() )
        ytdl_path = app_obj.check_downloader(app_obj.ytdl_path)
        if os.name != 'nt':
            ytdl_path = re.sub(r'^\~', os.path.expanduser('~'), ytdl_path)

        # Generate the system command
        if app_obj.ytdl_path_custom_flag:
            cmd_list = ['python3'] + [ytdl_path] + ['--dump-json'] \
            + [self.video_obj.source]
        else:
            cmd_list = [ytdl_path] + ['--dump-json'] + [self.video_obj.source]

        # Create a new child process using that command...
        self.create_child_process(cmd_list)
        # ...and set up the PipeReader objects to read from the child process
        #   STDOUT and STDERR
        if self.child_process is not None:
            self.stdout_reader.attach_fh(self.child_process.stdout)
            self.stderr_reader.attach_fh(self.child_process.stderr)

        # Wait for the process to finish
        while self.is_child_process_alive():

            # Pause a moment between each iteration of the loop (we don't want
            #   to hog system resources)
            time.sleep(self.sleep_time)

            # Read from the child process STDOUT and STDERR, in the correct
            #   order, until there is nothing left to read
            while self.read_child_process():
                pass


    def close(self):

        """Called by downloads.StreamManager.run().

        Destructor function for this object.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11326 close')

        # Tell the PipeReader objects to shut down, thus joining their threads
        self.stdout_reader.join()
        self.stderr_reader.join()


    def create_child_process(self, cmd_list):

        """Called by self.do_fetch().

        Based on YoutubeDLDownloader._create_process().

        Executes the system command, creating a new child process which
        executes youtube-dl.

        Args:

            cmd_list (list): Python list that contains the command to execute

        Return values:

            True on success, False on an error

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11353 create_child_process')

        # Strip double quotes from arguments
        # (Since we're sending the system command one argument at a time, we
        #   don't need to retain the double quotes around any single argument
        #   and, in fact, doing so would cause an error)
        cmd_list = ttutils.strip_double_quotes(cmd_list)

        # Create the child process
        info = preexec = None

        if os.name == 'nt':
            # Hide the child process window that MS Windows helpfully creates
            #   for us
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            # Make this child process the process group leader, so that we can
            #   later kill the whole process group with os.killpg
            preexec = os.setsid

        try:
            self.child_process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=preexec,
                startupinfo=info,
            )

            return True

        except (ValueError, OSError) as error:
            # (Errors are expected and frequent)
            return False


    def is_child_process_alive(self):

        """Called by self.do_fetch() and self.stop().

        Based on YoutubeDLDownloader._proc_is_alive().

        Called continuously during the self.do_fetch() loop to check whether
        the child process has finished or not.

        Return values:

            True if the child process is alive, otherwise returns False

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11406 is_child_process_alive')

        if self.child_process is None:
            return False

        return self.child_process.poll() is None


    def parse_json(self, stdout):

        """Called by self.do_fetch().

        Code copied from downloads.VideoDownloader.extract_stdout_data().

        Converts the receivd JSON data into a dictionary, and returns the
        dictionary.

        Args:

            stdout (str): A string of JSON data as it was received from
                youtube-dl (and starting with the character { )

        Return values:

            The JSON data, converted into a Python dictionary

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11435 parse_json')

        # (Try/except to check for invalid JSON)
        try:
            return json.loads(stdout)

        except:
            GObject.timeout_add(
                0,
                app_obj.system_error,
                316,
                'Invalid JSON data received from server',
            )

            return {}


    def read_child_process(self):

        """Called by self.do_fetch().

        Reads from the child process STDOUT and STDERR, in the correct order.

        Return values:

            True if either STDOUT or STDERR were read, None if both queues were
                empty

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11466 read_child_process')

        # mini_list is in the form [time, pipe_type, data]
        try:
            mini_list = self.queue.get_nowait()

        except:
            # Nothing left to read
            return None

        # Import the main application (for convenience)
        app_obj = self.livestream_manager_obj.app_obj

        # Failsafe check
        if not mini_list \
        or (mini_list[1] != 'stdout' and mini_list[1] != 'stderr'):

            # Just in case...
            GObject.timeout_add(
                0,
                self.download_manager_obj.app_obj.system_error,
                317,
                'Malformed STDOUT or STDERR data',
            )

        # STDOUT or STDERR has been read
        data = mini_list[2].rstrip()
        # Convert bytes to string
        data = data.decode(ttutils.get_encoding(), 'replace')

        # STDOUT
        if mini_list[1] == 'stdout':

            if data[:1] == '{':

                # Broadcasting livestream detected
                json_dict = self.parse_json(data)
                if self.video_obj.live_mode == 1:

                    # Waiting livestream has gone live
                    GObject.timeout_add(
                        0,
                        app_obj.mark_video_live,
                        self.video_obj,
                        2,              # Livestream is broadcasting
                        {},             # No livestream data
                        True,           # Don't update Video Index yet
                        True,           # Don't update Video Catalogue yet
                    )

                elif self.video_obj.live_mode == 2 \
                and (not 'is_live' in json_dict or not json_dict['is_live']):

                    # Broadcasting livestream has finished
                    GObject.timeout_add(
                        0,
                        app_obj.mark_video_live,
                        self.video_obj,
                        0,                  # Livestream has finished
                        {},             # Reset any livestream data
                        None,           # Reset any l/s server messages
                        True,           # Don't update Video Index yet
                        True,           # Don't update Video Catalogue yet
                    )

                # The video's name and description might change during the
                #   livestream; update them, if so
                if 'title' in json_dict:
                    self.video_obj.set_nickname(json_dict['title'])

                if 'id' in json_dict:
                    self.video_obj.set_vid(json_dict['id'])

                if 'description' in json_dict:
                    self.video_obj.set_video_descrip(
                        app_obj,
                        json_dict['description'],
                        app_obj.main_win_obj.descrip_line_max_len,
                    )

        # STDERR (ignoring any empty error messages)
        elif data != '':

            # (v2.2.100: In approximately October 2020, YouTube started using a
            #   new error message for livestreams waiting to start)
            if self.video_obj.live_mode == 1:

                live_data_dict = ttutils.extract_livestream_data(data)
                if live_data_dict:
                    self.video_obj.set_live_data(live_data_dict)

            elif self.video_obj.live_mode == 2 \
            and re.search('This video is unavailable', data):

                # The livestream broadcast has been deleted by its owner (or is
                #   not available on the website, possibly temporarily)
                app_obj.add_media_reg_live_vanished_dict(self.video_obj),

        # Either (or both) of STDOUT and STDERR were non-empty
        self.queue.task_done()
        return True


    def stop(self):

        """Called by DownloadWorker.close().

        Terminates the child process.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11577 stop')

        if self.is_child_process_alive():

            if os.name == 'nt':
                # os.killpg is not available on MS Windows (see
                #   https://bugs.python.org/issue5115 )
                self.child_process.kill()

                # When we kill the child process on MS Windows the return code
                #   gets set to 1, so we want to reset the return code back to
                #   0
                self.child_process.returncode = 0

            else:
                os.killpg(self.child_process.pid, signal.SIGKILL)
