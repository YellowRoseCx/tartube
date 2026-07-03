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
class StreamDownloader(object):

    """Called by downloads.DownloadWorker.run_stream_downloader().

    Python class to create a system child process. Uses the child process to
    download a currently broadcasting livestream, using the URL described by a
    downloads.DownloadItem object.

    Reads from the child process STDOUT and STDERR, having set up a
    downloads.PipeReader object to do so in an asynchronous way.

    Sets self.return_code to a value in the range 0-5, described below. The
    parent downloads.DownloadWorker object checks that return code once this
    object's child process has finished.

    Args:

        download_manager_obj (downloads.DownloadManager): The download manager
            object handling the entire download operation

        download_worker_obj (downloads.DownloadWorker): The parent download
            worker object. The download manager uses multiple workers to
            implement simultaneous downloads. The download manager checks for
            free workers and, when it finds one, assigns it a
            download.DownloadItem object. When the worker is assigned a
            download item, it creates a new instance of this object to
            interface with youtube-dl, and waits for this object to return a
            return code

        download_item_obj (downloads.DownloadItem): The download item object
            describing the URL with which the livestream must be downloaded

    Warnings:

        The calling function is responsible for calling the close() method
        when it's finished with this object, in order for this object to
        properly close down.

    """

    # Attributes


    # Valid vlues for self.return_code, following the model established by
    #   downloads.VideoDownloader (but with a smaller set of values)
    # 0 - The download operation completed successfully
    OK = 0
    # 2 - An error occured during the download operation
    ERROR = 2
    # 5 - The download operation was stopped by the user
    STOPPED = 5


    # Standard class methods


    def __init__(self, download_manager_obj, download_worker_obj, \
    download_item_obj):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9293 __init__')

        # IV list - class objects
        # -----------------------
        # The downloads.DownloadManager object handling the entire download
        #   operation
        self.download_manager_obj = download_manager_obj
        # The parent downloads.DownloadWorker object
        self.download_worker_obj = download_worker_obj
        # The downloads.DownloadItem object describing the URL of the
        #   broadcasting livestream
        self.download_item_obj = download_item_obj

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
        # The current return code, using values in the range 0-5, as described
        #   above
        # The value remains set to self.OK unless we encounter any problems
        # The larger the number, the higher in the hierarchy of return codes.
        #   Codes lower in the hierarchy (with a smaller number) cannot
        #   overwrite higher in the hierarchy (with a bigger number)
        self.return_code = self.OK
        # The time (in seconds) between iterations of the loop in
        #   self.do_download_basic()
        self.sleep_time = 0.5
        # The time (in seconds) between iterations of the loop in
        #   self.do_download_m3u() and .do_download_streamlink()
        self.longer_sleep_time = 0.25
        # Flag set to True after the first error message processed
        self.first_error_flag = False

        # Shortcut to the livestream download mode: 'default', 'default_mu3' or
        #   'streamlink'
        self.dl_mode = self.download_manager_obj.app_obj.livestream_dl_mode

        # Flag set to True when we're expecting the .m3u manifest in STDOUT,
        #   set back to False when it is received
        self.m3u_waiting_flag = False
        # The text of the .m3u manifest, when received. Stored here so that
        #   self.do_download_m3u() can retrieve it
        self.m3u_manifest = None

        # The actual (video) output path, set when intercepted (and used to
        #   update the Progress List)
        # (YouTube and other sites add a date/time to the video title, which
        #   chnages every minutes; so the output path may not be the one we
        #   were expecting)
        self.actual_output_path = None
        # ...and its components (for quick lookup)
        self.actual_output_dir = None
        self.actual_output_filename = None
        self.actual_output_ext = None
        # The expected output path. In some modes, it is passed directly to the
        #   downloader
        self.expect_output_path = self.choose_path()

        # Flag set to True for downloads in 'streamlink' mode, when the
        #   download started message is detected. The actual output path is on
        #   the next line of STDOU; when this flag is True, that output path
        #   can be intercepted
        self.streamlink_start_flag = False

        # Number of segments downloaded so far
        self.segment_count = 0
        # The time at which we should stop waiting for the next segment
        #   (matches time.time())
        self.check_time = 0
        # Size of the output file, and the time (matches time.time()) at which
        #   this value was set
        # (These IVs are only use by 'default_m3u' and 'streamlink' modes
        self.output_size = 0
        self.output_size_time = 0


    # Public class methods


    def do_download(self):

        """Called by downloads.DownloadWorker.run_stream_downloader().

        Downloads a broadcasting livestream using the URL described by
        self.download_item_obj.

        Return values:

            The final return code, a value in the range 0-5 (as described
                above)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9396 do_download')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj
        video_obj = self.download_item_obj.media_data_obj

        # Set the default return code. Everything is OK unless we encounter any
        #   problems
        self.set_return_code(self.OK)

        if not self.download_item_obj.operation_classic_flag:

            # Reset the errors/warnings stored in the media data object, the
            #   last time it was checked/downloaded
            video_obj.reset_error_warning()
            video_obj.set_block_flag(False)

        # If the file already exists (indicating an incomplete livestream
        #   download), we can replace it before re-starting the download, if
        #   required
        if app_obj.livestream_replace_flag \
        and video_obj.file_name is not None:

            if os.path.isfile(self.expect_output_path):
                app_obj.remove_file(self.expect_output_path)

            part_path = self.expect_output_path + '.part'
            if os.path.isfile(part_path):
                app_obj.remove_file(part_path)

        # There are currently three download methods, specified by self.dl_mode
        msg = _('Tartube is starting the livestream download')
        if self.dl_mode == 'default':

            self.show_msg(msg + ' (' + app_obj.get_downloader() + ')...')
            self.do_download_basic()

        elif self.dl_mode == 'default_m3u':

            self.show_msg(
                msg + ' (' + app_obj.get_downloader() + '/FFmpeg/.m3u)...',
            )
            self.do_download_m3u()

        elif self.dl_mode == 'streamlink':

            self.show_msg(msg + ' (streamlink)...')
            self.do_download_streamlink()

        else:

            GObject.timeout_add(
                0,
                app_obj.system_error,
                312,
                _('Invalid livestream download mode'),
            )

            self.set_return_code(self.ERROR)

        # If the file described by the output path actually exists, we can mark
        #   the video as downloaded
        if self.return_code == self.ERROR \
        or self.actual_output_path is None \
        or (
            not os.path.isfile(self.actual_output_path) \
            and not os.path.isfile(self.actual_output_path + '.part')
        ):
            # Video is not marked as downloaded
            self.show_error('Livestream download failed')
            self.set_error(video_obj, 'Livestream download failed')

        else:

            # Because of YouTube's delightful habit of appending the date/time
            #   to a livestream video's title, the media.Video's .file_name
            #   may be different to the name of the file actually downloaded
            # Rectify the situation by renaming the video and/or the .part file
            if not os.path.isfile(self.expect_output_path) \
            and os.path.isfile(self.actual_output_path):

                app_obj.move_file_or_directory(
                    self.actual_output_path,
                    self.expect_output_path,
                )

            if not os.path.isfile(self.expect_output_path + '.part') \
            and os.path.isfile(self.actual_output_path + '.part'):

                app_obj.move_file_or_directory(
                    self.actual_output_path + '.part',
                    self.expect_output_path + '.part',
                )

            # If we have a .part file instead of a video file, we can
            #   optionally salvage the download by converting it (e.g.
            #   convert output.mp4.part to output.mp4, and hope it works)
            if not os.path.isfile(self.expect_output_path) \
            and os.path.isfile(self.expect_output_path + '.part'):

                if app_obj.livestream_stop_is_final_flag:

                    self.show_msg(
                        _(
                            'Incomplete livestream download detected;' \
                            + ' removing the .part component from the' \
                            + ' output file',
                        ),
                    )

                    app_obj.move_file_or_directory(
                        part_path,
                        self.expect_output_path,
                    )

                elif not self.download_item_obj.operation_classic_flag:

                    self.show_msg(
                        _(
                            'Incomplete livestream download detected;' \
                            + ' to complete the download, right-click the' \
                            + ' video and select \'Finalise livestream\'',
                        ),
                    )

            # Update IVs and the main window
            if self.return_code == self.STOPPED \
            and not app_obj.livestream_stop_is_final_flag:

                # Video is not marked as downloaded
                self.show_msg('Livestream download stopped')

            else:

                # Video is marked as downloaded
                if self.return_code == self.STOPPED:
                    self.show_msg('Livestream download stopped')
                else:
                    self.show_msg('Livestream download complete')

                if not self.download_item_obj.operation_classic_flag:

                    # Download from the Videos tab
                    GObject.timeout_add(
                        0,
                        app_obj.mark_video_downloaded,
                        video_obj,
                        True,               # Video is downloaded
                    )
                    GObject.timeout_add(
                        0,
                        app_obj.mark_video_live,
                        video_obj,
                        0,                  # Not live
                    )

                else:

                    # Download from the Classic Mode tab
                    video_obj.set_dl_flag(True)
                    if os.path.isfile(self.expect_output_path):
                        video_obj.set_dummy_path(
                            self.expect_output_path,
                        )
                    else:
                        video_obj.set_dummy_path(
                            self.expect_output_path + '.part',
                        )

                # Update the main window
                GObject.timeout_add(
                    0,
                    app_obj.announce_video_download,
                    self.download_item_obj,
                    video_obj,
                    ttutils.compile_mini_options_dict(
                        self.download_worker_obj.options_manager_obj,
                    ),
                )

                # Register the download with DownloadManager, so that download
                #   limits can be applied, if required
                # (Use 'new' rather than 'old', even though the media.Video
                #   object already exists; the download operation's
                #   confirmation window will be less confusing that way)
                self.download_manager_obj.register_video('new')

        # Pass a dictionary of values to downloads.DownloadWorker, confirming
        #   the result of the job. The values are passed on to the main window
        self.last_data_callback()

        # Pass the result back to the parent downloads.DownloadWorker object
        return self.return_code


    def do_download_basic(self):

        """Called by self.do_download() when self.dl_mode is set to 'default'.

        Downloads a broadcasting livestream using youtube-dl alone.

        This function is based on VideoDownload.do_download() (but simplified,
        because self.download_item_obj.media_data_obj is always a media.Video).
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9602 do_download_basic')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Prepare a system command
        options_obj = self.download_worker_obj.options_manager_obj
        if options_obj.options_dict['direct_cmd_flag']:

            cmd_list = ttutils.generate_direct_system_cmd(
                app_obj,
                self.download_item_obj.media_data_obj,
                options_obj,
            )

        else:

            cmd_list = ttutils.generate_ytdl_system_cmd(
                app_obj,
                self.download_item_obj.media_data_obj,
                self.download_worker_obj.options_list,
            )

        # Display the (modified) command in the Output tab and/or terminal (if
        #   required)...
        if app_obj.ytdl_output_system_cmd_flag:
            self.show_cmd(ttutils.prepare_system_cmd_for_display(cmd_list))

        # Create a new child process using that command...
        self.create_child_process(cmd_list)
        # ...and set up the PipeReader objects to read from the child process
        #   STDOUT and STDERR
        if self.child_process is not None:
            self.stdout_reader.attach_fh(self.child_process.stdout)
            self.stderr_reader.attach_fh(self.child_process.stderr)

        # While downloading the media data object, update the callback function
        #   with the status of the current job
        while self.is_child_process_alive():

            # Pause a moment between each iteration of the loop (we don't want
            #   to hog system resources)
            time.sleep(self.sleep_time)

            # Read from the child process STDOUT and STDERR, in the correct
            #   order, until there is nothing left to read
            while self.read_child_process():
                pass

            # Perform a timeout, if necessary
            if self.check_time > 0 and self.check_time < time.time():

                # Halt the child process
                self.stop()
                self.show_msg('Download timed out')
                return

        # The child process has finished
        # We also set the return code to self.ERROR if the download didn't
        #   start or if the child process return code is greater than 0
        # Original notes from youtube-dl-gui:
        #   NOTE: In Linux if the called script is just empty Python exits
        #       normally (ret=0), so we can't detect this or similar cases
        #       using the code below
        #   NOTE: In Unix a negative return code (-N) indicates that the child
        #       was terminated by signal N (e.g. -9 = SIGKILL)
        internal_msg = None
        if self.child_process is None:
            self.set_return_code(self.ERROR)
            internal_msg = _('Download did not start')

        elif self.child_process.returncode > 0:
            self.set_return_code(self.ERROR)
            if not app_obj.ignore_child_process_exit_flag:
                internal_msg = _(
                    'Child process exited with non-zero code: {}',
                ).format(self.child_process.returncode)

        if internal_msg:

            # (The message must be visible in the Errors/Warnings tab, the
            #   Output tab and/or the terminal)
            self.set_error(
                self.download_item_obj.media_data_obj,
                internal_msg,
            )

            self.show_error(internal_msg)

        return


    def do_download_m3u(self):

        """Called by self.do_download() when self.dl_mode is set to
        'default_m3u'.

        Downloads a broadcasting livestream, instructing youtube-dl to fetch
        the .m3u manifest first.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9704 do_download_m3u')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Prepare a system command to fetch the .m3u manifest...
        cmd_list = ttutils.generate_m3u_system_cmd(
            app_obj,
            self.download_item_obj.media_data_obj,
        )

        # ...and display it in the Output tab and/or terminal, if required
        self.show_cmd(ttutils.prepare_system_cmd_for_display(cmd_list))

        # Create a new child process using that command...
        self.create_child_process(cmd_list)
        # ...and set up the PipeReader objects to read from the child process
        #   STDOUT and STDERR
        if self.child_process is not None:
            self.stdout_reader.attach_fh(self.child_process.stdout)
            self.stderr_reader.attach_fh(self.child_process.stderr)

        # The first message in STDOUT should be the .m3u manifest
        self.m3u_waiting_flag = True

        # While downloading the media data object, update the callback function
        #   with the status of the current job
        while self.is_child_process_alive():

            # Pause a moment between each iteration of the loop (we don't want
            #   to hog system resources)
            time.sleep(self.longer_sleep_time)

            # Read from the child process STDOUT and STDERR, in the correct
            #   order, until there is nothing left to read
            while self.read_child_process():
                pass

            # !!! DEBUG: Any stall/timeout code goes here
            pass

        # Reset the child process, ready for the next one
        self.reset()

        # Check the .m3u manifest was fetched
        if self.m3u_manifest is None or self.m3u_manifest == '':

            msg = _('Failed to download the .m3u manifest')

            self.set_error(
                self.download_item_obj.media_data_obj,
                msg,
            )
            self.show_error(msg)

            self.set_return_code(self.ERROR)
            return

        # Prepare a system command to download the livestream using the .m3u
        #   manifest...
        cmd_list = [
            app_obj.ffmpeg_manager_obj.get_executable(),
            '-i',
            self.m3u_manifest,
            '-c',
            'copy',
            self.expect_output_path,
        ]

        # ...and display it in the Output tab and/or terminal, if required
        self.show_cmd(' '.join(cmd_list))

        # Create a new child process using that command...
        self.create_child_process(cmd_list)
        # ...and set up the PipeReader objects to read from the child process
        #   STDOUT and STDERR
        if self.child_process is not None:
            self.stdout_reader.attach_fh(self.child_process.stdout)
            self.stderr_reader.attach_fh(self.child_process.stderr)

        # !!! DEBUG: Because STDOUT/STDERR messages are missing, artificially
        # !!!   update the Progress List, as if the start of the download had
        # !!!   been detected (in self.read_child_process() code)
        self.set_actual_output_path(self.expect_output_path)

        # While downloading the media data object, update the callback function
        #   with the status of the current job
        while self.is_child_process_alive():

            # Pause a moment between each iteration of the loop (we don't want
            #   to hog system resources)
            time.sleep(self.sleep_time)

            # Read from the child process STDOUT and STDERR, in the correct
            #   order, until there is nothing left to read
            while self.read_child_process():
                pass

            # Check on our progress. As of v2.3.618, youtube-dl output on lines
            #   without a newline character cannot be retrieved by
            #   downloads.PipeReader; this is the next best thing
            if self.actual_output_path \
            and os.path.isfile(self.actual_output_path):

                current_size = os.path.getsize(self.actual_output_path)
                if current_size != self.output_size:

                    self.output_size = current_size
                    self.output_size_time = time.time()
                    self.segment_count += 1

                    # (Convert to, e.g. '27.5 MiB')
                    converted_size = ttutils.convert_bytes_to_string(
                        current_size,
                    )

                    self.download_data_callback('', str(converted_size))
                    self.show_msg(
                        ('Downloaded segment #{0}, size {1}').format(
                            self.segment_count,
                            converted_size,
                        ),
                    )

                    self.check_time = (app_obj.livestream_dl_timeout * 60) \
                    + time.time()

            # Perform a timeout, if necessary
            if self.check_time > 0 and self.check_time < time.time():

                # Halt the child process
                self.stop()
                self.show_msg('Download timed out')
                return


    def do_download_streamlink(self):

        """Called by self.do_download() when self.dl_mode is set to
        'streamlink'.

        Downloads a broadcasting livestream using streamlink.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9849 do_download_streamlink')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Prepare a system command to download the livestream...
        cmd_list = ttutils.generate_streamlink_system_cmd(
            app_obj,
            self.download_item_obj.media_data_obj,
            self.expect_output_path,
        )

        # ...and display it in the Output tab and/or terminal, if required
        self.show_cmd(ttutils.prepare_system_cmd_for_display(cmd_list))

        # Create a new child process using that command...
        self.create_child_process(cmd_list)
        # ...and set up the PipeReader objects to read from the child process
        #   STDOUT and STDERR
        if self.child_process is not None:
            self.stdout_reader.attach_fh(self.child_process.stdout)
            self.stderr_reader.attach_fh(self.child_process.stderr)

        # While downloading the media data object, update the callback function
        #   with the status of the current job
        while self.is_child_process_alive():

            # Pause a moment between each iteration of the loop (we don't want
            #   to hog system resources)
            time.sleep(self.longer_sleep_time)

            # Read from the child process STDOUT and STDERR, in the correct
            #   order, until there is nothing left to read
            while self.read_child_process():
                pass

            # Check on our progress. As of v2.3.618, youtube-dl output on lines
            #   without a newline character cannot be retrieved by
            #   downloads.PipeReader; this is the next best thing
            if self.actual_output_path \
            and os.path.isfile(self.actual_output_path):

                current_size = os.path.getsize(self.actual_output_path)
                if current_size != self.output_size:

                    self.output_size = current_size
                    self.output_size_time = time.time()
                    self.segment_count += 1

                    # (Convert to, e.g. '27.5 MiB')
                    converted_size = ttutils.convert_bytes_to_string(
                        current_size,
                    )

                    self.download_data_callback('', str(converted_size))
                    self.show_msg(
                        ('Downloaded segment #{0}, size {1}').format(
                            self.segment_count,
                            converted_size,
                        ),
                    )

                    # Streamlink has been passed a --stream-timeout argument;
                    #   so add a few seconds to the usual timeout value, hoping
                    #   that streamlink's own timeout will happen first
                    self.check_time = (app_obj.livestream_dl_timeout * 60) \
                    + time.time() + 30

            # Perform a timeout, if necessary
            if self.check_time > 0 and self.check_time < time.time():

                # Halt the child process
                self.stop()
                self.show_msg('Download timed out')
                return


    def choose_path(self):

        """Called by self.__init__().

        When downloading from the Classic Mode tab, we don't know the video's
        name, so we have to choose an arbitrary one.

        Otherwise, the video's name (and file path) is already known, so we
        can just use the normal media.Video function to get it.

        Return values:

            The new value of self.expect_output_path

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9943 choose_path')

        video_obj = self.download_item_obj.media_data_obj
        if not video_obj.dummy_flag:
            return video_obj.get_actual_path(self.download_manager_obj.app_obj)

        else:

            # Retrieve the user's preferred file extension
            file_ext = None
            if video_obj.dummy_format is not None:
                convert_flag, file_ext, resolution \
                = ttutils.extract_dummy_format(video_obj.dummy_format)

            if file_ext is None:
                file_ext = 'mp4'

            # Use an arbitrary filename in the form 'livestream_N.EXT'
            count = 0
            while 1:
                count += 1
                path = os.path.abspath(
                    os.path.join(
                        video_obj.dummy_dir, 'livestream_' + str(count) \
                        + '.' + file_ext,
                    ),
                )

                if not os.path.isfile(path):
                    return path


    def close(self):

        """Can be called by anything.

        Destructor function for this object.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9982 close')

        # Tell the PipeReader objects to shut down, thus joining their threads
        self.stdout_reader.join()
        self.stderr_reader.join()


    def create_child_process(self, cmd_list):

        """Called by self.do_download_basic(), .do_download_m3u() and
        .do_download_streamlink().

        Based on YoutubeDLDownloader._create_process().

        Executes the system command, creating a new child process which
        executes youtube-dl.

        Args:

            cmd_list (list): Python list that contains the command to execute

        Return values:

            True on success, False on an error

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10010 create_child_process')

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


    def download_data_callback(self, speed='', filesize=''):

        """Called by self.read_child_process() and .set_actual_output_path().

        Passes a dictionary of values to self.download_worker_obj so the main
        window can be updated.

        The dictionary is based on the one created by downloads.VideoDownloader
        (but with far fewer values included).

        This function is only called when a download is in progress;
        self.last_data_callback() is called at the end of it.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10062 download_data_callback')

        if self.segment_count == 0:
            percent = '?'
        else:
            percent = str(self.segment_count) + '/?'

        dl_stat_dict = {
            'status': formats.ACTIVE_STAGE_DOWNLOAD,
            'path': self.actual_output_dir,
            'filename': self.actual_output_filename,
            'extension': self.actual_output_ext,
            'percent': percent,
            'speed': speed,
            'filesize': filesize,
            'playlist_index': 1,
            'dl_sim_flag': False,
        }

        self.download_worker_obj.data_callback(dl_stat_dict)


    def is_child_process_alive(self):

        """Called by self.do_download_basic(), .do_download_m3u(),
        .do_download_streamlink() and .stop().

        Based on YoutubeDLDownloader._proc_is_alive().

        Called continuously during the self.do_fetch() loop to check whether
        the child process has finished or not.

        Return values:

            True if the child process is alive, otherwise returns False

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10101 is_child_process_alive')

        if self.child_process is None:
            return False

        return self.child_process.poll() is None


    def last_data_callback(self):

        """Called by self.do_download().

        Based on YoutubeDLDownloader._last_data_hook().

        After the child process has finished, creates a new Python dictionary
        in the standard form described by
        downloads.VideoDownloader.extract_stdout_data().

        Sets key-value pairs in the dictonary, then passes it to the parent
        downloads.DownloadWorker object, confirming the result of the child
        process.

        The new key-value pairs are used to update the main window.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10127 last_data_callback')

        dl_stat_dict = {}

        if self.return_code == self.OK:
            dl_stat_dict['status'] = formats.COMPLETED_STAGE_FINISHED
        elif self.return_code == self.ERROR:
            dl_stat_dict['status'] = formats.MAIN_STAGE_ERROR
        elif self.return_code == self.STOPPED:
            dl_stat_dict['status'] = formats.ERROR_STAGE_STOPPED

        # Use some empty values in dl_stat_dict so that the Progress tab
        #   doesn't show arbitrary data from the most recent call to
        #   self.download_data_callback()
        dl_stat_dict['path'] = ''
        dl_stat_dict['filename'] = ''
        dl_stat_dict['extension'] = ''
        dl_stat_dict['percent'] = ''
        dl_stat_dict['speed'] = ''
        dl_stat_dict['filesize'] = ''
        dl_stat_dict['playlist_index'] = 1
        dl_stat_dict['dl_sim_flag'] = False

        # The True argument shows that this function is the caller
        self.download_worker_obj.data_callback(dl_stat_dict, True)


    def read_child_process(self):

        """Called by self.do_download_basic(), .do_download_m3u() and
        .do_download_streamlink().

        Reads from the child process STDOUT and STDERR, in the correct order.

        Return values:

            True if either STDOUT or STDERR were read. None if both queues were
                empty, or if STDERR was read and a network error was detected

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10169 read_child_process')

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
                313,
                'Malformed STDOUT or STDERR data',
            )

        # STDOUT or STDERR has been read
        data = mini_list[2].rstrip()
        # On MS Windows we use cp1252, so that Tartube can communicate with the
        #   Windows console
        data = data.decode(ttutils.get_encoding(), 'replace')

        # STDOUT
        if mini_list[1] == 'stdout':

            if self.m3u_waiting_flag:

                # Assume the first line of text received in STDOUT is the .mu3
                #   manifest
                self.m3u_waiting_flag = False
                self.m3u_manifest = data
                # (The manifest will be visible in the next system command, so
                #   don't show it here)
                self.show_msg(
                    _(
                    'Downloaded the .m3u manifest, now downloading the' \
                    + ' livestream...'),
                )

                self.queue.task_done()
                return True

            # Capture the actual output path provided by the downloader
            if self.actual_output_path is None:

                output_path = None
                if self.dl_mode != 'streamlink':

                    match = re.search(
                        r'^\[download\] Destination\: (.*)\s*$',
                        data,
                    )
                    if match:
                        output_path = match.groups()[0]

                else:

                    if self.streamlink_start_flag == False \
                    and re.search(
                        r'^\[cli\]\[info\] Writing output to',
                        data,
                    ):
                        # Next line contains the output path
                        self.streamlink_start_flag = True

                    elif self.streamlink_start_flag == True:
                        # This line contains the output path
                        output_path = data
                        self.streamlink_start_flag = False

                if output_path:
                    self.set_actual_output_path(output_path)

            # Download updates in 'streamlink' download mode
            if self.dl_mode == 'streamlink':

                # !!! DEBUG This has not been tested, as the message is
                # !!!   currently not intercepted
                # e.g.
                # [download][output.mp4] Written 9.5 MB (36s @ 132.6 KB/s)
                match = re.search(
                    r'^\[download\]\[[^\[\]]+\] Written (.*) \(\S+ \@ (.*)\)',
                    data,
                )

                if match:
                    self.segment_count += 1

                    # Pass a dictionary of values to
                    #   self.download_worker_obj so the Progress List can be
                    #   updated
                    self.download_data_callback(
                        match.groups()[1],      # Bitrate
                        match.groups()[0],      # Filesize
                    )

            # Show output in the Output tab and/or terminal (if required)
            self.show_msg(data)

        # STDERR (downloads using youtube-dl, with or without .m3u; ignoring
        #   any empty error messages)
        elif data != '' and self.dl_mode != 'streamlink':

            mod_data = ttutils.stream_output_is_ignorable(data)
            if mod_data is not None:

                # Treat this as if it were a STDOUT message

                # Download updates in 'default' and 'default_m3u' download
                #   modes
                match = re.search(
                    r'^frame.*size\=\s*([\S]+).*bitrate\=\s*([\S]+)',
                    mod_data,
                )
                if match:
                    self.segment_count += 1

                    self.check_time = (app_obj.livestream_dl_timeout * 60) \
                    + time.time()

                    # Pass a dictionary of values to self.download_worker_obj
                    #   so the Progress List can be updated
                    self.download_data_callback(
                        match.groups()[1],      # Bitrate
                        match.groups()[0],      # Filesize
                    )

                # Show output in the Output tab and/or terminal (if required)
                self.show_msg(mod_data)

        # STDERR (downloads using youtube-dl/.m3u/FFmpeg, or using streamlink;
        #   ignoring any empty error messages)
        elif data != '':

            # Check for recognised errors/warnings, and update the appropriate
            #   media data object (immediately, if possible, or later
            #   otherwise)
            self.set_error(self.download_item_obj.media_data_obj, data)

            # Show output in the Output tab and/or terminal (if required)
            self.show_error(data)

            # (An error fetching the .m3u manifest is fatal)
            if self.m3u_waiting_flag:
                self.show_error(_('Failed to download the .m3u manifest'))
                self.set_return_code(self.ERROR)

        # Either (or both) of STDOUT and STDERR were non-empty
        self.queue.task_done()
        return True


    def reset(self):

        """Called by self.do_download_m3u().

        A modified version of self.close().

        The calling code uses two sub-processes, one after the other. This
        function is called when the first process is finished to reset
        everything, ready for the second function.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10342 reset')

        if self.child_process:

            # Tell the PipeReader objects to shut down, thus joining their
            #   threads
            self.stdout_reader.join()
            self.stderr_reader.join()

        self.child_process = None
        self.queue = queue.PriorityQueue()
        self.stdout_reader = PipeReader(self.queue, 'stdout')
        self.stderr_reader = PipeReader(self.queue, 'stderr')


    def set_actual_output_path(self, output_path):

        """Called by self.do_download_m3u() and .read_child_process().

        The downloader's output path is captured, meaning that the download has
        started.

        Updates IVs and the Progress List.

        Args:

            output_path (str): Full path to the downloader's output file

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10373 set_actual_output_path')

        # Update IVs
        directory, filename, ext = ttutils.extract_path_components(output_path)

        self.actual_output_path = output_path
        self.actual_output_dir = directory
        self.actual_output_filename = filename
        self.actual_output_ext = ext

        # Pass a dictionary of values to self.download_worker_obj so the main
        #   window can be updated
        self.download_data_callback()


    def set_error(self, media_data_obj, msg):

        """Wrapper for media.Video.set_error().

        Args:

            media_data_obj (media.Video): The media data object to update. Only
                videos are updated by this function

            msg (str): The error message for this video

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10402 set_error')

        if not self.first_error_flag:

            self.first_error_flag = True

            # The new error is the first error/warning generated during this
            #   operation; remove any errors/warnings from previous operations
            media_data_obj.reset_error_warning()

        # Set the new error
        media_data_obj.set_error(msg)


    def set_return_code(self, code):

        """Can be called by anything.

        Based on YoutubeDLDownloader._set_returncode().

        After the child process has terminated with an error of some kind,
        sets a new value for self.return_code, but only if the new return code
        is higher in the hierarchy of return codes than the current value.

        Args:

            code (int): A return code in the range 0-5

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10433 set_return_code')

        if code >= self.return_code:
            self.return_code = code


    def show_cmd(self, cmd):

        """Can be called by anything.

        Shows a system command in the Output tab and/or terminal window, if
        required.

        Args:

            cmd (str): The system command to display

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10453 show_cmd')

        # Import the main app (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Display the command in the Output tab, if allowed
        if app_obj.ytdl_output_system_cmd_flag:
            app_obj.main_win_obj.output_tab_write_system_cmd(
                self.download_worker_obj.worker_id,
                cmd,
            )

        # Display the message in the terminal, if allowed
        if app_obj.ytdl_write_system_cmd_flag:
            try:
                print(cmd)
            except:
                print('Command echoed in STDOUT with unprintable characters')

        # Display the message in the downloader log, if allowed
        if app_obj.ytdl_log_system_cmd_flag:
            app_obj.write_downloader_log(cmd)


    def show_msg(self, msg):

        """Can be called by anything.

        Shows a message in the Output tab and/or terminal window, if required.

        Args:

            msg (str): The message to display

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10490 show_msg')

        # Import the main app (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Display the message in the Output tab, if allowed
        if app_obj.ytdl_output_stdout_flag:
            app_obj.main_win_obj.output_tab_write_stdout(
                self.download_worker_obj.worker_id,
                msg,
            )

        # Display the message in the terminal, if allowed
        if app_obj.ytdl_write_stdout_flag:
            # Git #175, Japanese text may produce a codec error here,
            #   despite the .decode() call above
            try:
                print(
                    msg.encode(ttutils.get_encoding(), 'replace'),
                )
            except:
                print('Message echoed in STDOUT with unprintable characters')

        # Write the message to the downloader log, if allowed
        if app_obj.ytdl_log_stdout_flag:
            app_obj.write_downloader_log(msg)


    def show_error(self, msg):

        """Can be called by anything.

        Shows an error message in the Output tab and/or terminal window, if
        required.

        Args:

            msg (str): The message to display

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10532 show_error')

        # Import the main app (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Display the message in the Output tab, if allowed
        if app_obj.ytdl_output_stdout_flag:
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                msg,
            )

        # Display the message in the terminal, if allowed
        if app_obj.ytdl_write_stderr_flag:
            # Git #175, Japanese text may produce a codec error here,
            #   despite the .decode() call above
            try:
                print(
                    msg.encode(ttutils.get_encoding(), 'replace'),
                )
            except:
                print('Message echoed in STDERR with unprintable characters')

        # Write the message to the downloader log (if required)
        if app_obj.ytdl_log_stderr_flag:
            app_obj.write_downloader_log(msg)


    def stop(self):

        """Called by DownloadWorker.close().

        Terminates the child process and sets this object's return code to
        self.STOPPED.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10569 stop')

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

            self.set_return_code(self.STOPPED)


    def stop_soon(self):

        """Can be called by anything. Currently called by
        mainwin.MainWin.on_progress_list_stop_soon().

        StreamDownloader only downloads a single video, so we can ignore an
        instruction to stop after that download has finished.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 10599 stop_soon')

        pass
