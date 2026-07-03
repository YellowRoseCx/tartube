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
class ClipDownloader(object):

    """Called by downloads.DownloadWorker.run_clip_slice_downloader().

    A modified VideoDownloader to download one or more video clips from a
    specified video (rather than downloading the complete video).

    Optionally concatenates the clips back together, which has the effect of
    removing one or more slices from a video.

    Python class to create multiple system child processes, one for each clip.

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
            describing the URL from which youtube-dl should download clip(s)

    Warnings:

        The calling function is responsible for calling the close() method
        when it's finished with this object, in order for this object to
        properly close down.

    """


    # Attributes (the same set used by VideoDownloader; not all of them are
    #   used by ClipDownloader)


    # Valid values for self.return_code. The larger the number, the higher in
    #   the hierarchy of return codes.
    # Codes lower in the hierarchy (with a smaller number) cannot overwrite
    #   higher in the hierarchy (with a bigger number)
    #
    # 0 - The download operation completed successfully
    OK = 0
    # 1 - A warning occured during the download operation
    WARNING = 1
    # 2 - An error occured during the download operation
    ERROR = 2
    # 3 - The corresponding url video file was larger or smaller from the given
    #   filesize limit
    FILESIZE_ABORT = 3
    # 4 - The video(s) for the specified URL have already been downloaded
    ALREADY = 4
    # 5 - The download operation was stopped by the user
    STOPPED = 5
    # 6 - The download operation has stalled. The parent worker can restart it,
    #   if required
    STALLED = -1


    # Standard class methods


    def __init__(self, download_manager_obj, download_worker_obj, \
    download_item_obj):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6898 __init__')

        # IV list - class objects
        # -----------------------
        # The downloads.DownloadManager object handling the entire download
        #   operation
        self.download_manager_obj = download_manager_obj
        # The parent downloads.DownloadWorker object
        self.download_worker_obj = download_worker_obj
        # The downloads.DownloadItem object describing the URL from which
        #   youtube-dl should download video(s)
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
        #   self.do_download_clips()
        self.sleep_time = 0.1

        # Flag set to True if this download operation was launched from the
        #   Classic Mode tab, False if not (set below)
        self.dl_classic_flag = False
        # Flag set to True if an attempt to copy an original videos' thumbnail
        #   fails (in which case, don't try again)
        self.thumb_copy_fail_flag = False

        # Flag set to True by a call from any function to self.stop_soon()
        # After being set to True, this ClipDownloader should give up after
        #   the next clip has been downloaded
        self.stop_soon_flag = False
        # When self.stop_soon_flag is True, the next call to
        #   self.extract_stdout_data() for a downloaded clip sets this flag to
        #   True, informing self.do_download_clips() that it can stop the child
        #   process
        self.stop_now_flag = False

        # Named for compatibility with VideoDownloader, both IVs are set to the
        #   number of clips that have been downloaded
        self.video_num = 0
        self.video_total = 0

        # The type of download, depending on which function is called:
        #   'chapters':     self.do_download_clips_with_chapters()
        #   'downloader':   self.do_download_clips_with_downloader()
        #   'ffmpeg':       self.do_download_clips_with_ffmpeg()
        #   'slices':       self.do_download_remove_slices()
        self.dl_type = None

        # Used for 'ffmpeg' and 'slices':
        # Output generated by youtube-dl/FFmpeg may vary, depending on the
        #   file format specified. We have to record every file path
        #   we receive; the last path received is the one that remains on the
        #   filesystem (earlier ones are generally deleted).
        # These two variables are reset at the beginning/end of every clip
        # The file path currently being downloaded/processed
        self.dl_path = None
        # Flag set to True when youtube-dl/FFmpeg appears to have finished
        #   downloading/post-processing the clip
        self.dl_confirm_flag = False

        # Used for self.dl_type = 'chapters':
        self.chapter_dest_obj = None
        self.chapter_dest_dir = None
        self.chapter_orig_video_obj = None

        # Used for self.dl_type = 'downloader':
        self.downloader_path_list = []

        # Dictionary of clip titles used during this operation (i.e. when
        #   splitting a video into clips), used to re-name duplicates
        # Not used when removing video slices
        self.clip_title_dict = {}

        # Code
        # ----
        # Initialise IVs
        if self.download_item_obj.operation_classic_flag:
            self.dl_classic_flag = True


    # Public class methods


    def do_download_clips(self):

        """Called by downloads.DownloadWorker.run_clip_slice_downloader().

        Using the URL described by self.download_item_obj (which must
        represent a media.Video object, during a 'custom_real' or
        'classic_custom' download operation), downloads a series of one or more
        clips, using the timestamps specified by the media.Video itself.

        Return values:

            The final return code, a value in the range 0-5 (as described
                above)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 7016 do_download_clips')

        # Import the main application and video object (for convenience)
        app_obj = self.download_manager_obj.app_obj
        orig_video_obj = self.download_item_obj.media_data_obj

        # Set the default return code. Everything is OK unless we encounter any
        #   problems
        self.return_code = self.OK

        if not self.dl_classic_flag:

            # Reset the errors/warnings stored in the media data object, the
            #   last time it was checked/downloaded
            orig_video_obj.reset_error_warning()

        if orig_video_obj.dbid in app_obj.temp_stamp_buffer_dict:

            # Retrieve the entry from the main application's temporary
            #   timestamp buffer, if it exists
            stamp_list = app_obj.temp_stamp_buffer_dict[orig_video_obj.dbid]
            # (The temporary buffer, once used, must be emptied immediately)
            app_obj.del_temp_stamp_buffer_dict(orig_video_obj.dbid)

            # The first entry in 'stamp_list' is one of the values 'chapters',
            #   'downloader' or 'ffmpeg'; extract it
            dl_mode = stamp_list.pop(0)
            if dl_mode != 'chapters' \
            and dl_mode != 'downloader' \
            and dl_mode != 'ffmpeg':
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    _('Invalid timestamps in temporary buffer'),
                )

                self.stop()
                return self.ERROR

        else:

            # Otherwise, re-extract timestamps from the video's .info.json or
            #   description file, if allowed
            if app_obj.video_timestamps_re_extract_flag \
            and not orig_video_obj.stamp_list:
                app_obj.update_video_from_json(orig_video_obj, 'chapters')

            if app_obj.video_timestamps_re_extract_flag \
            and not orig_video_obj.stamp_list:
                orig_video_obj.extract_timestamps_from_descrip(app_obj)

            # Check that at least one timestamp now exists
            if not orig_video_obj.stamp_list:
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    _('No timestamps defined in video\'s timestamp list'),
                )

                self.stop()
                return self.ERROR

            else:
                stamp_list = orig_video_obj.stamp_list.copy()
                dl_mode = 'default'

        # Set the containing folder, creating a media.Folder object and/or a
        #   sub-directory for the video clips, if required
        parent_obj, parent_dir, dest_obj, dest_dir \
        = ttutils.clip_set_destination(app_obj, orig_video_obj)

        if parent_obj is None:

            # Duplicate media.Folder name, this is a fatal error
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                _(
                'FAILED: Can\'t create the destination folder either because' \
                + ' a folder with the same name already exists, or because' \
                + ' new folders can\'t be added to the parent folder',
                ),
            )

            self.stop()

            return self.ERROR

        # Download the clips
        if dl_mode == 'chapters':
            return self.do_download_clips_with_chapters(
                orig_video_obj,
                parent_obj,
                parent_dir,
                dest_obj,
                dest_dir,
            )

        elif dl_mode == 'downloader':

            return self.do_download_clips_with_downloader(
                orig_video_obj,
                stamp_list,
                parent_obj,
                parent_dir,
                dest_obj,
                dest_dir,
            )

        else:

            # (dl_mode == 'ffmpeg')
            return self.do_download_clips_with_ffmpeg(
                orig_video_obj,
                stamp_list,
                parent_obj,
                parent_dir,
                dest_obj,
                dest_dir,
            )


    def do_download_clips_with_chapters(self, orig_video_obj, parent_obj,
    parent_dir, dest_obj, dest_dir):

        """Called by self.do_download_clips().

        Downloads video clips using yt-dlp's --split-chapters. A single
        system command is used to download all requested video clips together.

        Args:

            orig_video_obj (media.Video): The video whose clips are being
                downloaded

            parent_obj (media.Folder): orig_video_obj's containing folder

            parent_dir (str): Path to the containing folder's directory in
                Tartube's data folder

            dest_obj (media.Folder): The actual folder to which video clips are
                downloaded, which might be different from 'parent_obj'

            dest_dir (str): Path to the destination folder

        Return values:

            The final return code, a value in the range 0-5 (as described
                above)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 7166 do_download_clips_with_chapters')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Set the download type and its associated IVs
        self.dl_type = 'chapters'
        self.chapter_dest_obj = dest_obj
        self.chapter_dest_dir = dest_dir
        self.chapter_orig_video_obj = orig_video_obj

        # Get an output template for these clip(s)
        if self.dl_classic_flag:
            output_template = ttutils.clip_prepare_chapter_output_template(
                app_obj,
                orig_video_obj,
                orig_video_obj.dummy_dir,
            )

        else:
            output_template = ttutils.clip_prepare_chapter_output_template(
                app_obj,
                orig_video_obj,
                dest_dir,
            )

        # Create a temporary directory to which the full video is downloaded
        temp_dir = self.create_temp_dir_for_chapters(orig_video_obj)
        if temp_dir is None:
            self.set_return_code(self.ERROR)
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                _('FAILED: Cannot create temporary directory'),
            )

            return

        # Prepare a system command...
        if self.download_manager_obj.custom_dl_obj is not None:
            divert_mode = self.download_manager_obj.custom_dl_obj.divert_mode
        else:
            divert_mode = None

        cmd_list = ttutils.generate_chapters_split_system_cmd(
            app_obj,
            orig_video_obj,
            self.download_worker_obj.options_list.copy(),
            dest_dir,
            temp_dir,
            output_template,
            self.download_manager_obj.custom_dl_obj,
            divert_mode,
            self.dl_classic_flag,
        )

        # ...display it in the Output tab (if required)...
        display_cmd = ttutils.prepare_system_cmd_for_display(cmd_list)
        if app_obj.ytdl_output_system_cmd_flag:
            app_obj.main_win_obj.output_tab_write_system_cmd(
                self.download_worker_obj.worker_id,
                display_cmd,
            )

        # ...and the terminal (if required)
        if app_obj.ytdl_write_system_cmd_flag:
            print(display_cmd)

        # ...and the downloader log (if required)
        if app_obj.ytdl_log_system_cmd_flag:
            app_obj.write_downloader_log(display_cmd)

        # Write an additional message in the Output tab, in the same style
        #   as those produced by youtube-dl/FFmpeg (and therefore not
        #   translated)
        app_obj.main_win_obj.output_tab_write_stdout(
            self.download_worker_obj.worker_id,
            '[' + __main__.__packagename__ + '] Downloading chapters',
        )

        # Create a new child process using that command...
        self.create_child_process(cmd_list)
        # ...and set up the PipeReader objects to read from the child
        #   process STDOUT and STDERR
        if self.child_process is not None:
            self.stdout_reader.attach_fh(self.child_process.stdout)
            self.stderr_reader.attach_fh(self.child_process.stderr)

        # Pass data on to self.download_worker_obj so the main window can be
        #   updated. We don't know for sure how many chapters there will be, so
        #   just use default values
        self.download_worker_obj.data_callback({
            'playlist_index': 1,
            'playlist_size': 1,
            'status': formats.ACTIVE_STAGE_DOWNLOAD,
            'filename': '',
            # This guarantees the the Classic Progress List shows the clip
            #   title, not the original filename
            'clip_flag': True,
        })

        # While downloading the media data object(s), update the callback
        #   function with the status of the current job
        while self.is_child_process_alive():

            # Pause a moment between each iteration of the loop (we don't want
            #   to hog system resources)
            time.sleep(self.sleep_time)

            # Read from the child process STDOUT and STDERR, in the correct
            #   order, until there is nothing left to read
            while self.read_child_process():
                pass

            # Stop this clip downloader, if required to do so
            if self.stop_now_flag:
                self.stop()

        # The child process has finished
        # We also set the return code to self.ERROR if the download didn't
        #   start or if the child process return code is greater than 0
        # Original notes from youtube-dl-gui:
        #   NOTE: In Linux if the called script is just empty Python exits
        #       normally (ret=0), so we can't detect this or similar cases
        #       using the code below
        #   NOTE: In Unix a negative return code (-N) indicates that the child
        #       was terminated by signal N (e.g. -9 = SIGKILL)
        if self.child_process is None:
            self.set_return_code(self.ERROR)
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                _('FAILED: Clip download did not start'),
            )

        elif self.child_process.returncode > 0:
            self.set_return_code(self.ERROR)
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                    _(
                    'FAILED: Child process exited with non-zero code: {}'
                    ).format(self.child_process.returncode),
            )

        # If at least one clip was extracted...
        if self.video_total:

            # ...then the number of video downloads must be incremented
            self.download_manager_obj.register_video('clip')

            # Delete the original video, if required, and if it's not inside a
            #   channel/playlist
            # (Don't bother trying to delete a 'dummy' media.Video object, for
            #   download operations launched from the Classic Mode tab)
            if app_obj.split_video_auto_delete_flag \
            and not isinstance(orig_video_obj.parent_obj, media.Channel) \
            and not isinstance(orig_video_obj.parent_obj, media.Playlist) \
            and not orig_video_obj.dummy_flag:

                app_obj.delete_video(
                    orig_video_obj,
                    True,           # Delete all files
                    True,           # Don't update Video Index yet
                    True,           # Don't update Video Catalogue yet
                )


            # Open the destination directory, if required to do so
            if dest_dir is not None \
            and app_obj.split_video_auto_open_flag:
                ttutils.open_file(app_obj, dest_dir)

        # Pass a dictionary of values to downloads.DownloadWorker, confirming
        #   the result of the job. The values are passed on to the main
        #   window
        self.last_data_callback()

        # Pass the result back to the parent downloads.DownloadWorker object
        return self.return_code


    def do_download_clips_with_downloader(self, orig_video_obj, stamp_list,
    parent_obj, parent_dir, dest_obj, dest_dir):

        """Called by self.do_download_clips().

        Downloads video clips using yt-dlp's download-sections. A single
        system command is used to download all requested video clips together.

        Args:

            orig_video_obj (media.Video): The video whose clips are being
                downloaded

            stamp_list (list): List in groups of three, in the form
                [start_timestamp, stop_timestamp, clip_title]

            parent_obj (media.Folder): orig_video_obj's containing folder

            parent_dir (str): Path to the containing folder's directory in
                Tartube's data folder

            dest_obj (media.Folder): The actual folder to which video clips are
                downloaded, which might be different from 'parent_obj'

            dest_dir (str): Path to the destination folder

        Return values:

            The final return code, a value in the range 0-5 (as described
                above)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 7379 do_download_clips_with_downloader')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Set the download type
        self.dl_type = 'downloader'

        # Create a temporary directory to which the full video is downloaded
        temp_dir = self.create_temp_dir_for_chapters(orig_video_obj)
        if temp_dir is None:
            self.set_return_code(self.ERROR)
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                _('FAILED: Cannot create temporary directory'),
            )

            return

        # Prepare a system command...
        if self.download_manager_obj.custom_dl_obj is not None:
            divert_mode = self.download_manager_obj.custom_dl_obj.divert_mode
        else:
            divert_mode = None

        cmd_list = ttutils.generate_downloader_split_system_cmd(
            app_obj,
            orig_video_obj,
            self.download_worker_obj.options_list.copy(),
            dest_dir,
            temp_dir,
            stamp_list,
            self.download_manager_obj.custom_dl_obj,
            divert_mode,
            self.dl_classic_flag,
        )

        # ...display it in the Output tab (if required)...
        display_cmd = ttutils.prepare_system_cmd_for_display(cmd_list)
        if app_obj.ytdl_output_system_cmd_flag:
            app_obj.main_win_obj.output_tab_write_system_cmd(
                self.download_worker_obj.worker_id,
                display_cmd,
            )

        # ...and the terminal (if required)
        if app_obj.ytdl_write_system_cmd_flag:
            print(display_cmd)

        # ...and the downloader log (if required)
        if app_obj.ytdl_log_system_cmd_flag:
            app_obj.write_downloader_log(display_cmd)

        # Write an additional message in the Output tab, in the same style
        #   as those produced by youtube-dl/FFmpeg (and therefore not
        #   translated)
        app_obj.main_win_obj.output_tab_write_stdout(
            self.download_worker_obj.worker_id,
            '[' + __main__.__packagename__ + '] Downloading sections',
        )

        # Create a new child process using that command...
        self.create_child_process(cmd_list)
        # ...and set up the PipeReader objects to read from the child
        #   process STDOUT and STDERR
        if self.child_process is not None:
            self.stdout_reader.attach_fh(self.child_process.stdout)
            self.stderr_reader.attach_fh(self.child_process.stderr)

        # Pass data on to self.download_worker_obj so the main window can be
        #   updated. We don't know for sure how many chapters there will be, so
        #   just use default values
        self.download_worker_obj.data_callback({
            'playlist_index': 1,
            'playlist_size': 1,
            'status': formats.ACTIVE_STAGE_DOWNLOAD,
            'filename': '',
            # This guarantees the the Classic Progress List shows the clip
            #   title, not the original filename
            'clip_flag': True,
        })

        # While downloading the media data object(s), update the callback
        #   function with the status of the current job
        while self.is_child_process_alive():

            # Pause a moment between each iteration of the loop (we don't want
            #   to hog system resources)
            time.sleep(self.sleep_time)

            # Read from the child process STDOUT and STDERR, in the correct
            #   order, until there is nothing left to read
            while self.read_child_process():
                pass

            # Stop this clip downloader, if required to do so
            if self.stop_now_flag:
                self.stop()

        # The child process has finished
        # We also set the return code to self.ERROR if the download didn't
        #   start or if the child process return code is greater than 0
        # Original notes from youtube-dl-gui:
        #   NOTE: In Linux if the called script is just empty Python exits
        #       normally (ret=0), so we can't detect this or similar cases
        #       using the code below
        #   NOTE: In Unix a negative return code (-N) indicates that the child
        #       was terminated by signal N (e.g. -9 = SIGKILL)
        if self.child_process is None:
            self.set_return_code(self.ERROR)
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                _('FAILED: Clip download did not start'),
            )

        elif self.child_process.returncode > 0:
            self.set_return_code(self.ERROR)
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                    _(
                    'FAILED: Child process exited with non-zero code: {}'
                    ).format(self.child_process.returncode),
            )

        # Set the destination directory, which is different from the current
        #   value, in downloads from the Classic Mode tab
        if self.dl_classic_flag:
            dest_dir = orig_video_obj.dummy_dir

        # self.downloader_path_list contains a list of paths that yt-dlp
        #   attempted to download, hopefully in the same order as 'stamp_list'
        if self.downloader_path_list:

            for i in range(len(self.downloader_path_list)):

                old_path = self.downloader_path_list[i]

                if not os.path.isfile(old_path):
                    continue
                elif i >= len(stamp_list):
                    break

                # List in groups of 3, in the form
                #   [start_stamp, optional_stop_stamp, optional_clip_title]
                mini_list = stamp_list[i]

                # Rename the clip, ready for it to be added to the Tartube
                #   database
                directory, filename, extension \
                = ttutils.extract_path_components(old_path)
                # (This is a scaled-down version of code in
                #   ttutils.clip_prepare_title() )
                orig_name = orig_video_obj.file_name
                if orig_name is None \
                and orig_video_obj.dummy_flag \
                and orig_video_obj.nickname != app_obj.default_video_name:
                    orig_name = orig_video_obj.nickname

                this_title = mini_list[2]
                if this_title is None:
                    this_title = 'Clip'

                if app_obj.split_video_name_mode == 'num':
                    mod_title = str(i + 1)
                elif app_obj.split_video_name_mode == 'clip':
                    mod_title = this_title
                elif app_obj.split_video_name_mode == 'num_clip':
                    mod_title = str(i + 1) + ' ' + this_title
                elif app_obj.split_video_name_mode == 'clip_num':
                    mod_title = this_title + ' ' + str(i + 1)

                elif app_obj.split_video_name_mode == 'orig' \
                or app_obj.split_video_name_mode == 'orig_num':

                    # N.B. We must have a unique clip name, so these two
                    #   settings are combined
                    if orig_name is None:
                        mod_title = str(i + 1)
                    else:
                        mod_title = orig_name + ' ' + str(i + 1)

                elif app_obj.split_video_name_mode == 'orig_clip':

                    if orig_name is None:
                        mod_title = this_title
                    else:
                        mod_title = orig_name + ' ' + this_title

                elif app_obj.split_video_name_mode == 'orig_num_clip':

                    if orig_name is None:
                        mod_title = str(i + 1) + ' ' + this_title
                    else:
                        mod_title = orig_name + ' ' + str(i + 1) + ' ' \
                        + this_title

                elif app_obj.split_video_name_mode == 'orig_clip_num':

                    if orig_name is None:
                        mod_title = this_title + ' ' + str(i + 1)
                    else:
                        mod_title = orig_name + ' ' + this_title + ' ' \
                        + str(i + 1)

                # Failsafe
                if mod_title is None:
                    mod_title = str(i + 1)

                new_path = os.path.abspath(
                    os.path.join(dest_dir, mod_title + extension),
                )

                ttutils.rename_file(app_obj, old_path, new_path)

                if os.path.isfile(new_path):
                    self.confirm_video_clip(
                        dest_obj,
                        dest_dir,
                        orig_video_obj,
                        mod_title,
                        new_path,
                    )

        # If at least one clip was extracted...
        if self.video_total:

            # ...then the number of video downloads must be incremented
            self.download_manager_obj.register_video('clip')

            # Delete the original video, if required, and if it's not inside a
            #   channel/playlist
            # (Don't bother trying to delete a 'dummy' media.Video object, for
            #   download operations launched from the Classic Mode tab)
            if app_obj.split_video_auto_delete_flag \
            and not isinstance(orig_video_obj.parent_obj, media.Channel) \
            and not isinstance(orig_video_obj.parent_obj, media.Playlist) \
            and not orig_video_obj.dummy_flag:

                app_obj.delete_video(
                    orig_video_obj,
                    True,           # Delete all files
                    True,           # Don't update Video Index yet
                    True,           # Don't update Video Catalogue yet
                )

            # Open the destination directory, if required to do so
            if dest_dir is not None \
            and app_obj.split_video_auto_open_flag:
                ttutils.open_file(app_obj, dest_dir)

        # Pass a dictionary of values to downloads.DownloadWorker, confirming
        #   the result of the job. The values are passed on to the main
        #   window
        self.last_data_callback()

        # Pass the result back to the parent downloads.DownloadWorker object
        return self.return_code


    def do_download_clips_with_ffmpeg(self, orig_video_obj, stamp_list,
    parent_obj, parent_dir, dest_obj, dest_dir):

        """Called by self.do_download_clips().

        Downloads video clips using FFmpeg, on clip at a time.

        Args:

            orig_video_obj (media.Video): The video whose clips are being
                downloaded

            stamp_list (list): List in groups of three, in the form
                [start_timestamp, stop_timestamp, clip_title]

            parent_obj (media.Folder): orig_video_obj's containing folder

            parent_dir (str): Path to the containing folder's directory in
                Tartube's data folder

            dest_obj (media.Folder): The actual folder to which video clips are
                downloaded, which might be different from 'parent_obj'

            dest_dir (str): Path to the destination folder

        Return values:

            The final return code, a value in the range 0-5 (as described
                above)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 7671 do_download_clips_with_ffmpeg')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Set the download type
        self.dl_type = 'ffmpeg'

        # Download the clips, one at a time
        list_size = len(stamp_list)
        for i in range(list_size):

            # Reset detection variables
            self.dl_path = None
            self.dl_confirm_flag = False

            # List in the form [start_stamp, stop_stamp, clip_title]
            # If 'stop_stamp' is not specified, then 'start_stamp' of the next
            #   clip is used. If there are no more clips, then this clip will
            #   end at the end of the video
            start_stamp, stop_stamp, clip_title \
            = ttutils.clip_extract_data(stamp_list, i)

            # Set a (hopefully unique) clip title
            clip_title = ttutils.clip_prepare_title(
                app_obj,
                orig_video_obj,
                self.clip_title_dict,
                clip_title,
                i + 1,
                list_size,
            )

            self.clip_title_dict[clip_title] = None

            # Prepare a system command...
            if self.download_manager_obj.custom_dl_obj is not None:
                divert_mode \
                = self.download_manager_obj.custom_dl_obj.divert_mode
            else:
                divert_mode = None

            cmd_list = ttutils.generate_ffmpeg_split_system_cmd(
                app_obj,
                orig_video_obj,
                self.download_worker_obj.options_list.copy(),
                dest_dir,
                clip_title,
                start_stamp,
                stop_stamp,
                self.download_manager_obj.custom_dl_obj,
                divert_mode,
                self.dl_classic_flag,
            )

            # ...display it in the Output tab (if required)...
            display_cmd = ttutils.prepare_system_cmd_for_display(cmd_list)
            if app_obj.ytdl_output_system_cmd_flag:
                app_obj.main_win_obj.output_tab_write_system_cmd(
                    self.download_worker_obj.worker_id,
                    display_cmd,
                )

            # ...and the terminal (if required)
            if app_obj.ytdl_write_system_cmd_flag:
                print(display_cmd)

            # ...and the downloader log (if required)
            if app_obj.ytdl_log_system_cmd_flag:
                app_obj.write_downloader_log(display_cmd)

            # Write an additional message in the Output tab, in the same style
            #   as those produced by youtube-dl/FFmpeg (and therefore not
            #   translated)
            app_obj.main_win_obj.output_tab_write_stdout(
                self.download_worker_obj.worker_id,
                '[' + __main__.__packagename__ + '] Downloading clip ' \
                + str(i + 1) + '/' + str(list_size),
            )

            # Create a new child process using that command...
            self.create_child_process(cmd_list)
            # ...and set up the PipeReader objects to read from the child
            #   process STDOUT and STDERR
            if self.child_process is not None:
                self.stdout_reader.attach_fh(self.child_process.stdout)
                self.stderr_reader.attach_fh(self.child_process.stderr)

            # Pass data on to self.download_worker_obj so the main window can
            #   be updated
            self.download_worker_obj.data_callback({
                'playlist_index': i + 1,
                'playlist_size': list_size,
                'status': formats.ACTIVE_STAGE_DOWNLOAD,
                'filename': clip_title,
                # This guarantees the the Classic Progress List shows the clip
                #   title, not the original filename
                'clip_flag': True,
            })

            # While downloading the media data object, update the callback
            #   function with the status of the current job
            while self.is_child_process_alive():

                # Pause a moment between each iteration of the loop (we don't
                #   want to hog system resources)
                time.sleep(self.sleep_time)

                # Read from the child process STDOUT and STDERR, in the correct
                #   order, until there is nothing left to read
                while self.read_child_process():
                    pass

                # Stop this clip downloader, if required to do so, having just
                #   finished downloading a clip
                if self.stop_now_flag:
                    self.stop()

            # The child process has finished
            # We also set the return code to self.ERROR if the download didn't
            #   start or if the child process return code is greater than 0
            # Original notes from youtube-dl-gui:
            #   NOTE: In Linux if the called script is just empty Python exits
            #       normally (ret=0), so we can't detect this or similar cases
            #       using the code below
            #   NOTE: In Unix a negative return code (-N) indicates that the
            #       child was terminated by signal N (e.g. -9 = SIGKILL)
            if self.child_process is None:
                self.set_return_code(self.ERROR)
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    _('FAILED: Clip download did not start'),
                )

            elif self.child_process.returncode > 0:
                self.set_return_code(self.ERROR)
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                        _(
                        'FAILED: Child process exited with non-zero code: {}'
                        ).format(self.child_process.returncode),
                )

            # General error handling
            if self.return_code != self.OK:
                break

            # Deal with a confirmed download (if any)
            if self.dl_path is not None and self.dl_confirm_flag:

                self.confirm_video_clip(
                    dest_obj,
                    dest_dir,
                    orig_video_obj,
                    clip_title
                )

        # If at least one clip was extracted...
        if self.video_total:

            # ...then the number of video downloads must be incremented
            self.download_manager_obj.register_video('clip')

            # Delete the original video, if required, and if it's not inside a
            #   channel/playlist
            # (Don't bother trying to delete a 'dummy' media.Video object, for
            #   download operations launched from the Classic Mode tab)
            if app_obj.split_video_auto_delete_flag \
            and not isinstance(orig_video_obj.parent_obj, media.Channel) \
            and not isinstance(orig_video_obj.parent_obj, media.Playlist) \
            and not orig_video_obj.dummy_flag:

                app_obj.delete_video(
                    orig_video_obj,
                    True,           # Delete all files
                    True,           # Don't update Video Index yet
                    True,           # Don't update Video Catalogue yet
                )

            # Open the destination directory, if required to do so
            if dest_dir is not None \
            and app_obj.split_video_auto_open_flag:
                ttutils.open_file(app_obj, dest_dir)

        # Pass a dictionary of values to downloads.DownloadWorker, confirming
        #   the result of the job. The values are passed on to the main
        #   window
        self.last_data_callback()

        # Pass the result back to the parent downloads.DownloadWorker object
        return self.return_code


    def do_download_remove_slices(self):

        """Called by downloads.DownloadWorker.run_clip_slice_downloader().

        Modified version of self.do_download_clips().

        The media.Video object specifies one or more video slices that must be
        removed. We start by downloading the video in clips, as before. The
        clips are the portions of the video that we want to keep.

        Then, we concatenate the clips back together, which has the effect of
        'downloading' a video with the specified slices removed.

        Return values:

            The final return code, a value in the range 0-5 (as described
                above)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 7885 do_download_remove_slices')

        # Import the main application and video object (for convenience)
        app_obj = self.download_manager_obj.app_obj
        orig_video_obj = self.download_item_obj.media_data_obj

        # Set the download type
        self.dl_type = 'slices'

        # Set the default return code. Everything is OK unless we encounter any
        #   problems
        self.return_code = self.OK

        if not self.dl_classic_flag:

            # Reset the errors/warnings stored in the media data object, the
            #   last time it was checked/downloaded
            self.download_item_obj.media_data_obj.reset_error_warning()

        # Contact the SponsorBlock server to update the video's slice data, if
        #   allowed
        # (No point doing it, if the temporary buffer is set)
        if not orig_video_obj.dbid in app_obj.temp_slice_buffer_dict:

            if app_obj.sblock_re_extract_flag \
            and not orig_video_obj.slice_list:
                ttutils.fetch_slice_data(
                    app_obj,
                    orig_video_obj,
                    self.download_worker_obj.worker_id,
                )

            # Check that at least one slice now exists
            if not orig_video_obj.slice_list:

                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    _('No slices defined in video\'s slice list'),
                )

                self.stop()
                return self.ERROR

        # Create a temporary directory for this video so we don't accidentally
        #   overwrite anything
        parent_dir = orig_video_obj.parent_obj.get_actual_dir(app_obj)
        temp_dir = self.create_temp_dir_for_slices(orig_video_obj)
        if temp_dir is None:
            return self.ERROR

        # If the temporary buffer specifies a slice list, use it; otherwise
        #   use the video's actual slice list
        if not orig_video_obj.dbid in app_obj.temp_slice_buffer_dict:
            slice_list = orig_video_obj.slice_list.copy()
            temp_flag = False

        else:
            slice_list = app_obj.temp_slice_buffer_dict[orig_video_obj.dbid]
            # The first entry in 'slice_list' is the value 'default'; remove it
            slice_list.pop(0)

            # (The temporary buffer, once used, must be emptied immediately)
            app_obj.del_temp_slice_buffer_dict(orig_video_obj.dbid)
            temp_flag = True

        # Convert this list from a list of video slices to be removed, to a
        #   list of video clips to be retained
        # The returned list is in groups of two, in the form
        #   [start_time, stop_time]
        # ...where 'start_time' and 'stop_time' are floating-point values in
        #   seconds. 'stop_time' can be None to signify the end of the video,
        #   but 'start_time' is 0 to signify the start of the video
        clip_list = ttutils.convert_slices_to_clips(
            app_obj,
            self.download_manager_obj.custom_dl_obj,
            slice_list,
            temp_flag,
        )

        # Download the clips, one at a time
        confirmed_list = []
        count = 0
        list_size = len(clip_list)
        for mini_list in clip_list:

            count += 1
            start_time = mini_list[0]
            stop_time = mini_list[1]

            # Reset detection variables
            self.dl_path = None
            self.dl_confirm_flag = False

            # Prepare a system command...
            if self.download_manager_obj.custom_dl_obj is not None:
                divert_mode \
                = self.download_manager_obj.custom_dl_obj.divert_mode
            else:
                divert_mode = None

            cmd_list = ttutils.generate_slice_system_cmd(
                app_obj,
                orig_video_obj,
                self.download_worker_obj.options_list.copy(),
                temp_dir,
                count,
                start_time,
                stop_time,
                self.download_manager_obj.custom_dl_obj,
                divert_mode,
                self.dl_classic_flag,
            )

            # ...display it in the Output tab (if required)...
            display_cmd = ttutils.prepare_system_cmd_for_display(cmd_list)
            if app_obj.ytdl_output_system_cmd_flag:
                app_obj.main_win_obj.output_tab_write_system_cmd(
                    self.download_worker_obj.worker_id,
                    display_cmd,
                )

            # ...and the terminal (if required)
            if app_obj.ytdl_write_system_cmd_flag:
                print(display_cmd)

            # ...and the downloader log (if required)
            if app_obj.ytdl_log_system_cmd_flag:
                app_obj.write_downloader_log(display_cmd)

            # Write an additional message in the Output tab, in the same style
            #   as those produced by youtube-dl/FFmpeg (and therefore not
            #   translated)
            app_obj.main_win_obj.output_tab_write_stdout(
                self.download_worker_obj.worker_id,
                '[' + __main__.__packagename__ + '] Downloading clip ' \
                + str(count) + '/' + str(list_size),
            )

            # Create a new child process using that command...
            self.create_child_process(cmd_list)
            # ...and set up the PipeReader objects to read from the child
            #   process STDOUT and STDERR
            if self.child_process is not None:
                self.stdout_reader.attach_fh(self.child_process.stdout)
                self.stderr_reader.attach_fh(self.child_process.stderr)

            # Pass data on to self.download_worker_obj so the main window can
            #   be updated
            if stop_time is not None:
                clip = 'Clip ' + str(start_time) + 's - ' + str(stop_time) \
                + 's'
            else:
                clip = 'Clip ' + str(start_time) + 's - end'

            self.download_worker_obj.data_callback({
                'playlist_index': count,
                'playlist_size': list_size,
                'status': formats.ACTIVE_STAGE_DOWNLOAD,
                'filename': clip,
            })

            # While downloading the media data object, update the callback
            #   function with the status of the current job
            while self.is_child_process_alive():

                # Pause a moment between each iteration of the loop (we don't
                #   want to hog system resources)
                time.sleep(self.sleep_time)

                # Read from the child process STDOUT and STDERR, in the correct
                #   order, until there is nothing left to read
                while self.read_child_process():
                    pass

                # Stop this clip downloader, if required to do so, having just
                #   finished downloading a clip
                if self.stop_now_flag:
                    self.stop()

            # The child process has finished
            # We also set the return code to self.ERROR if the download didn't
            #   start or if the child process return code is greater than 0
            # Original notes from youtube-dl-gui:
            #   NOTE: In Linux if the called script is just empty Python exits
            #       normally (ret=0), so we can't detect this or similar cases
            #       using the code below
            #   NOTE: In Unix a negative return code (-N) indicates that the
            #       child was terminated by signal N (e.g. -9 = SIGKILL)
            if self.child_process is None:
                self.set_return_code(self.ERROR)
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    _('FAILED: Clip download did not start'),
                )

            elif self.child_process.returncode > 0:
                self.set_return_code(self.ERROR)
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                        _(
                        'FAILED: Child process exited with non-zero code: {}'
                        ).format(self.child_process.returncode),
                )

            # General error handling
            if self.return_code != self.OK:

                break

            # Add a confirmed download to the list
            if self.dl_path is not None and self.dl_confirm_flag:

                confirmed_list.append(self.dl_path)
                self.video_num += 1
                self.video_total += 1

        # If fewer clips than expected were downloaded, then don't use any of
        #   them
        if len(confirmed_list) != len(clip_list):

            self.set_return_code(self.ERROR)

            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                _('FAILED: One or more clips were not downloaded'),
            )

        else:

            # Otherwise, get the video's (original) file extension from the
            #   first clip
            file_path, file_ext = os.path.splitext(confirmed_list[0])

            # Ordinarily, the user will check a video before custom downloading
            #   it. If not, the media.Video object won't have a .file_name set,
            #   which breaks the code below; in that case, we'll have to
            #   generate a name ourselves
            if orig_video_obj.file_name is None:
                fallback_name = _('Video') + ' ' + str(orig_video_obj.dbid)
                orig_video_obj.set_name(fallback_name)
                orig_video_obj.set_nickname(fallback_name)
                orig_video_obj.set_file(fallback_name, file_ext)

            # If there is more than one clip, they must be concatenated to
            #   produce a single video (like the original video, from which the
            #   video slices have been removed)
            if len(confirmed_list) == 1:
                output_path = confirmed_list[0]

            else:
                # For FFmpeg's benefit, write a text file listing every clip
                line_list = []
                clips_file = os.path.abspath(
                    os.path.join(temp_dir, 'clips.txt'),
                )

                for confirmed_path in confirmed_list:
                    line_list.append('file \'' + confirmed_path + '\'')

                with open(clips_file, 'w') as fh:
                    fh.write('\n'.join(line_list))

                # Prepare the FFmpeg command to concatenate the clips together
                output_path = os.path.abspath(
                    os.path.join(
                        temp_dir,
                        orig_video_obj.file_name + file_ext,
                    ),
                )

                cmd_list = [
                    app_obj.ffmpeg_manager_obj.get_executable(),
                    '-safe',
                    '0',
                    '-f',
                    'concat',
                    '-i',
                    clips_file,
                    '-c',
                    'copy',
                    output_path,
                ]

                # ...display it in the Output tab (if required)...
                if app_obj.ytdl_output_system_cmd_flag:
                    app_obj.main_win_obj.output_tab_write_system_cmd(
                        self.download_worker_obj.worker_id,
                        ' '.join(cmd_list),
                    )

                # ...and the terminal (if required)
                if app_obj.ytdl_write_system_cmd_flag:
                    print(' '.join(cmd_list))

                # ...and the downloader log (if required)
                if app_obj.ytdl_log_system_cmd_flag:
                    app_obj.write_downloader_log(' '.join(cmd_list))

                # Create a new child process using that command...
                self.create_child_process(cmd_list)
                # ...and set up the PipeReader objects to read from the child
                #   process STDOUT and STDERR
                if self.child_process is not None:
                    self.stdout_reader.attach_fh(self.child_process.stdout)
                    self.stderr_reader.attach_fh(self.child_process.stderr)

                # Pass data on to self.download_worker_obj so the main window
                #   can be updated
                self.download_worker_obj.data_callback({
                    'playlist_index': self.video_total,
                    'playlist_size': self.video_total,
                    'status': formats.ACTIVE_STAGE_CONCATENATE,
                    'filename': '',
                })

                # Wait for the concatenation to finish. We are not bothered
                #   about reading the child process STDOUT/STDERR, since we can
                #   just test for the existence of the output file
                while self.is_child_process_alive():
                    time.sleep(self.sleep_time)

                if not os.path.isfile(output_path):

                    app_obj.main_win_obj.output_tab_write_stderr(
                        self.download_worker_obj.worker_id,
                        _('FAILED: Can\'t concatenate clips'),
                    )

                    return self.ERROR

            # Move the single video file back into the parent directory,
            #   replacing any file of the same name that's already there
            moved_path = os.path.abspath(
                os.path.join(
                    parent_dir,
                    orig_video_obj.file_name + file_ext,
                ),
            )

            if os.path.isfile(moved_path):
                app_obj.remove_file(moved_path)

            if not app_obj.move_file_or_directory(output_path, moved_path):
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    _(
                        'FAILED: Clips were concatenated, but could not move' \
                        + ' the output file out of the temporary directory',
                    ),
                )

                return self.ERROR

            # Also move metadata files, if they don't already exist in the
            #   parent directory (or its /.data and ./thumbs sub-directories)
            self.move_metadata_files(orig_video_obj, temp_dir, parent_dir)

            # Update media.Video IVs (in particular, in some circumstances,
            #   FFmpeg may have switched the file extension to a different one)
            orig_video_obj.set_file(orig_video_obj.file_name, file_ext)

            # downloads.DownloadManager tracks the number of video slices
            #   removed
            for i in range(len(slice_list)):
                self.download_manager_obj.register_slice()

            # Update Tartube's database
            self.confirm_video_remove_slices(orig_video_obj, moved_path)

        # Delete the temporary directory
        app_obj.remove_directory(temp_dir)

        # Pass a dictionary of values to downloads.DownloadWorker, confirming
        #   the result of the job. The values are passed on to the main
        #   window
        self.last_data_callback()

        # Pass the result back to the parent downloads.DownloadWorker object
        return self.return_code


    def close(self):

        """Can be called by anything.

        Destructor function for this object.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8274 close')

        # Tell the PipeReader objects to shut down, thus joining their threads
        self.stdout_reader.join()
        self.stderr_reader.join()


    def confirm_video_clip(self, dest_obj, dest_dir, orig_video_obj, \
    clip_title, clip_path=None):

        """Called by self.do_download_clips_with_ffmpeg(),
        self.extract_stdout_data(), etc, when a video clip is confirmed as
        having been downloaded.

        Args:

            dest_obj (media.Folder): The folder object into which the new video
                object is to be created

            dest_dir (str): The path to that folder on the filesystem

            orig_video_obj (media.Video): The original video, from which the
                video clip has been split

            clip_title (str): The clip title for the new video, matching its
                filename

            clip_path (str or None): Full path to the video clip; specified
                only when required

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8307 confirm_video_clip')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Download confirmed
        self.video_num += 1
        self.video_total += 1
        self.download_manager_obj.register_clip()

        if dest_obj \
        and app_obj.split_video_add_db_flag \
        and not orig_video_obj.dummy_flag:

            # Add the clip to Tartube's database
            if self.dl_type == 'ffmpeg':

                clip_video_obj = ttutils.clip_add_to_db(
                    app_obj,
                    dest_obj,
                    orig_video_obj,
                    clip_title,
                    self.dl_path,
                )

            elif self.dl_type == 'chapters' or self.dl_type == 'downloader':

                clip_video_obj = ttutils.clip_add_to_db(
                    app_obj,
                    dest_obj,
                    orig_video_obj,
                    clip_title,
                    clip_path,
                )

            if clip_video_obj and not orig_video_obj.dummy_flag:

                # Update the Results List (unless the download operation was
                #   launched from the Classic Mode tab)
                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.results_list_add_row,
                    self.download_item_obj,
                    clip_video_obj,
                    {},                 # No 'mini_options_dict' to apply
                )

        elif app_obj.split_video_copy_thumb_flag \
        and not self.thumb_copy_fail_flag:

            # The call to ttutils.clip_add_to_db() copies the original
            #   thumbnail, when required
            # Since we're not going to call that, copy the thumbnail here
            thumb_path = ttutils.find_thumbnail(app_obj, orig_video_obj)
            if thumb_path is not None:

                _, thumb_ext = os.path.splitext(thumb_path)
                new_path = os.path.abspath(
                    os.path.join(dest_dir, clip_title + thumb_ext),
                )

                try:

                    shutil.copyfile(thumb_path, new_path)

                except:

                    GObject.timeout_add(
                        0,
                        app_obj.system_error,
                        309,
                        _(
                            'Failed to copy the original video\'s' \
                            + ' thumbnail',
                        ),
                    )

                    # Don't try to copy orig_video_obj's thumbnail again
                    self.thumb_copy_fail_flag = True

        # This ClipDownloader can now stop, if required to do so after a clip
        #   has been downloaded
        if self.stop_soon_flag:
            self.stop_now_flag = True


    def confirm_video_remove_slices(self, orig_video_obj, output_path):

        """Called by self.do_download_remove_slices().

        Once a video has been downloaded as a sequence of clips, then
        concatenated into a single video file (thereby removing one or more
        video slices), make sure the medai.Video object is marked as
        downloaded, and update the main window.

        Args:

            orig_video_obj (media.Video): The video to be downloaded

            output_path (str): Full path to the concatenated video

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8409 confirm_video_remove_slices')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Special case: don't add videos to the Tartube database
        if orig_video_obj.parent_obj.dl_no_db_flag:
            # (Do nothing, in this case)
            pass

        # Special case: if the download operation was launched from the
        #   Classic Mode tab, then we only need to update the dummy
        #   media.Video object, and to move/remove description/metadata/
        #   thumbnail files, as appropriate
        elif self.dl_classic_flag:

            orig_video_obj.set_dl_flag(True)
            orig_video_obj.set_dummy_path(output_path)

        elif not orig_video_obj.dl_flag:

            # Mark the video as downloaded
            GObject.timeout_add(
                0,
                app_obj.mark_video_downloaded,
                orig_video_obj,
                True,               # Video is downloaded
            )

            # Do add an entry to the Results List (as well as updating the
            #   Video Catalogue, as normal)
            GObject.timeout_add(
                0,
                app_obj.announce_video_download,
                self.download_item_obj,
                orig_video_obj,
                # No call to ttutils.compile_mini_options_dict(), because this
                #   function deals with download options like
                #   'move_description' by itself
                {},
            )

            # Try to detect the video's new length. The TRUE argument tells
            #   the function to override the existing length, if set
            app_obj.update_video_from_filesystem(
                orig_video_obj,
                output_path,
                True,
            )

        # Register the download with DownloadManager, so that download limits
        #   can be applied, if required
        self.download_manager_obj.register_video('new')

        # Timestamp and slice information is now obsolete for this video, and
        #   can be removed, if required
        if app_obj.slice_video_cleanup_flag:
            orig_video_obj.reset_timestamps()
            orig_video_obj.reset_slices()


    def create_child_process(self, cmd_list):

        """Called by self.do_download_clips() shortly after the call to
        ttutils.generate_ffmpeg_split_system_cmd(), etc.

        Based on YoutubeDLDownloader._create_process().

        Executes the system command, creating a new child process which
        executes youtube-dl.

        Sets self.return_code in the event of an error.

        Args:

            cmd_list (list): Python list that contains the command to execute

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8489 create_child_process')

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

        except (ValueError, OSError) as error:
            # (There is no need to update the media data object's error list,
            #   as the code in self.do_download_clips() will notice the child
            #   process didn't start, and set its own error message)
            self.set_return_code(self.ERROR)


    def create_temp_dir_for_chapters(self, orig_video_obj):

        """Called by self.do_download_clips_with_chapters().

        Create a temporary directory for files used while yt-dlp downloads
        video chapters.

        Args:

            orig_video_obj (media.Video): The video to be downloaded

        Return values:

            The temporary directory created on success, None on failure

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8544 create_temp_dir_for_chapters')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Work out where the temporary directory should be...
        temp_dir = os.path.abspath(
            os.path.join(
                app_obj.temp_dir,
                '.clips_' + str(orig_video_obj.dbid)
            ),
        )

        # ...then create it
        try:
            if os.path.isdir(temp_dir):
                app_obj.remove_directory(temp_dir)

            app_obj.make_directory(temp_dir)

            return temp_dir

        except:
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                _('FAILED: Can\'t create a temporary folder for video clips'),
            )

            self.stop()

            return None


    def create_temp_dir_for_slices(self, orig_video_obj):

        """Called by self.do_download_remove_slices().

        Before downloading a video in clips, and then concatenating the clips,
        create a temporary directory for the clips so we don't accidentally
        overwrite anything.

        Args:

            orig_video_obj (media.Video): The video to be downloaded

        Return values:

            The temporary directory created on success, None on failure

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8596 create_temp_dir_for_slices')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Work out where the temporary directory should be...
        temp_dir = os.path.abspath(
            os.path.join(
                app_obj.temp_dir,
                '.slices_' + str(orig_video_obj.dbid)
            ),
        )

        # ...then create it
        try:
            if os.path.isdir(temp_dir):
                app_obj.remove_directory(temp_dir)

            app_obj.make_directory(temp_dir)

            return temp_dir

        except:
            app_obj.main_win_obj.output_tab_write_stderr(
                self.download_worker_obj.worker_id,
                _('FAILED: Can\'t create a temporary folder for video slices'),
            )

            self.stop()

            return None


    def extract_stdout_data(self, stdout):

        """Called by self.read_child_process().

        Extracts output from the child process.

        Output generated by youtube-dl/FFmpeg may vary, depending on the file
        format specified. We have to record every file path we receive; the
        last path received is the one that remains on the filesystem (earlier
        ones are generally deleted).

        Args:

            stdout (str): String that contains a line from the child process
                STDOUT (i.e. a message from youtube-dl)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8648 extract_stdout_data')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Output received from self.do_download_clips_with_ffmpeg() and
        #   self.do_download_remove_slices()
        if self.dl_type == 'ffmpeg' or self.dl_type == 'slices':

            # Check for a media file being downloaded
            match = re.search(r'^\[download\] Destination\:\s(.*)$', stdout)
            if match:

                self.dl_path = match.group(1)
                return

            match = re.search(r'^\[ffmpeg\] Destination\:\s(.*)$', stdout)
            if match:

                self.dl_path = match.group(1)
                self.dl_confirm_flag = True
                return

            # Check for completion of a media file download
            match = re.search(r'^\[download\] 100% of .* in', stdout)
            if match:

                self.dl_confirm_flag = True
                return

            # Check for confirmation of post-processing
            match = re.search(
                r'^\[ffmpeg\] Merging formats into \"(.*)\"$',
                stdout
            )
            if match:

                self.dl_path = match.group(1)
                self.dl_confirm_flag = True

                return

        elif self.dl_type == 'chapters':

            # !!! DEBUG v2.4.306
            # Would like to extract download progress here, but yt-dlp is
            #   sending all progress updates from 0.1% to 100% in a single line
            #   and not in a consistent way

            # Check for completion of a media file download
            match = re.search(
                r'^\[SplitChapters\] Chapter \d+\; Destination\: (.*)$',
                stdout,
            )
            if match:

                _, name, _ = ttutils.extract_path_components(match.group(1))

                self.confirm_video_clip(
                    self.chapter_dest_obj,
                    self.chapter_dest_dir,
                    self.chapter_orig_video_obj,
                    name,
                    match.group(1),
                )

        elif self.dl_type == 'downloader':

            # Check for the start of a media file download, storing the path
            #   in the list. Hopefully, yt-dlp announces a list of paths that
            #   is in the same order as the sections we specified
            match = re.search(
                r'^\[download\] Destination\: (.*)$',
                stdout,
            )
            if match:
                self.downloader_path_list.append(match.group(1))


    def is_child_process_alive(self):

        """Called by self.do_download_clips(), .do_download_remove_slices and
        .stop().

        Based on YoutubeDLDownloader._proc_is_alive().

        Called continuously during the loop to check whether the child process
        has finished or not.

        Return values:

            True if the child process is alive, otherwise returns False

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8744 is_child_process_alive')

        if self.child_process is None:
            return False

        return self.child_process.poll() is None


    def is_network_error(self, stderr):

        """Called by self.do_download_clips(); an exact copy of the function in
        VideoDownloader.

        Try to detect network errors, indicating a stalled download.

        youtube-dl's output is system-dependent, so this function may not
        detect every type of network error.

        Args:

            stderr (str): A message from the child process STDERR

        Return values:

            True if the STDERR message seems to be a network error, False if it
                should be tested further

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8774 is_network_error')

        # v2.3.012, this error is seen on MS Windows:
        #   unable to download video data: <urlopen error [WinError 10060] A
        #   connection attempt failed because the connected party did not
        #   properly respond after a period of time, or established connection
        #   failed because connected host has failed to respond>
        # Don't know yet what the equivalent on other operating systems is, so
        #   we'll detect the first part, which is a string generated by
        #   youtube-dl itself

        if re.search(r'unable to download video data', stderr):
            return True
        else:
            return False


    def last_data_callback(self):

        """Called by self.read_child_process().

        Based on VideoDownloader.last_data_callback().

        After the child process has finished, creates a new Python dictionary
        in the standard form described by self.extract_stdout_data().

        Sets key-value pairs in the dictonary, then passes it to the parent
        downloads.DownloadWorker object, confirming the result of the child
        process.

        The new key-value pairs are used to update the main window.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8808 last_data_callback')

        dl_stat_dict = {}

        # (Some of these statuses are not actually used, but the code
        #   references them, in case they are added in future)
        if self.return_code == self.OK:
            dl_stat_dict['status'] = formats.COMPLETED_STAGE_FINISHED
        elif self.return_code == self.ERROR:
            dl_stat_dict['status'] = formats.MAIN_STAGE_ERROR
        elif self.return_code == self.WARNING:
            dl_stat_dict['status'] = formats.COMPLETED_STAGE_WARNING
        elif self.return_code == self.STOPPED:
            dl_stat_dict['status'] = formats.ERROR_STAGE_STOPPED
        elif self.return_code == self.ALREADY:
            dl_stat_dict['status'] = formats.COMPLETED_STAGE_ALREADY
        elif self.return_code == self.STALLED:
            dl_stat_dict['status'] = formats.MAIN_STAGE_STALLED
        else:
            dl_stat_dict['status'] = formats.ERROR_STAGE_ABORT

        # In the Classic Progress List, the 'Incoming File' column showed
        #   clipped names. Replace that with the full video name
        dl_stat_dict['filename'] = self.download_item_obj.media_data_obj.name
        dl_stat_dict['clip_flag'] = True

        # The True argument shows that this function is the caller
        self.download_worker_obj.data_callback(dl_stat_dict, True)


    def move_metadata_files(self, orig_video_obj, temp_dir, parent_dir):

        """Called by self.do_download_remove_slices().

        After moving the (concatenated) video file from its temporary directory
        into the parent container's directory, do the same to the metadata
        files.

        Depending on settings in the options.OptionsManager, they may be
        moved into a sub-directory of the parent cotainer's directory instead.

        Args:

            orig_video_obj (media.Video): The video that was downloaded as a
                sequence of clips

            temp_dir (str): Full path to the temporary directory into which the
                video and its metadata files was downloaded

            parent_dir (str): Full path to the parent container's directory

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 8862 move_metadata_files')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Handle the description file
        options_obj = self.download_worker_obj.options_manager_obj
        if options_obj.options_dict['keep_description']:

            descrip_path = os.path.abspath(
                os.path.join(temp_dir, 'clip_1.description'),
            )

            if os.path.isfile(descrip_path):

                moved_path = os.path.abspath(
                    os.path.join(
                        parent_dir,
                        orig_video_obj.file_name + '.description',
                    ),
                )

                if options_obj.options_dict['move_description']:
                    final_path = os.path.abspath(
                        os.path.join(
                            parent_dir,
                            '.data',
                            orig_video_obj.file_name + '.description',
                        ),
                    )
                else:
                    final_path = moved_path

                if not os.path.isfile(moved_path) \
                and not os.path.isfile(final_path):
                    app_obj.move_file_or_directory(descrip_path, moved_path)

                    # Further move the file into its sub-directory, if
                    #   required, first creating that sub-directory if it
                    #   doesn't exist
                    if options_obj.options_dict['move_description']:
                        ttutils.move_metadata_to_subdir(
                            app_obj,
                            orig_video_obj,
                            '.description',
                        )

        # Handle the .info.json file
        if options_obj.options_dict['keep_info']:

            json_path = os.path.abspath(
                os.path.join(temp_dir, 'clip_1.info.json'),
            )

            if os.path.isfile(json_path):

                moved_path = os.path.abspath(
                    os.path.join(
                        parent_dir,
                        orig_video_obj.file_name + '.info.json',
                    ),
                )

                if options_obj.options_dict['move_info']:
                    final_path = os.path.abspath(
                        os.path.join(
                            parent_dir,
                            '.data',
                            orig_video_obj.file_name + '.info.json',
                        ),
                    )
                else:
                    final_path = moved_path

                if not os.path.isfile(moved_path) \
                and not os.path.isfile(final_path):
                    app_obj.move_file_or_directory(json_path, moved_path)

                    if options_obj.options_dict['move_info']:
                        ttutils.move_metadata_to_subdir(
                            app_obj,
                            orig_video_obj,
                            '.info.json',
                        )

        # v2.1.101 - Annotations were removed by YouTube in 2019, so this
        #   feature is not available, and will not be available until the
        #   authors have some annotations to test
#       if options_obj.options_dict['keep_annotations']:
#
#           xml_path = os.path.abspath(
#               os.path.join(temp_dir, 'clip_1.annotations.xml'),
#           )
#
#           if os.path.isfile(xml_path):
#
#               moved_path = os.path.abspath(
#                   os.path.join(
#                       parent_dir,
#                       orig_video_obj.file_name + '.annotations.xml',
#                   ),
#               )
#
#               if options_obj.options_dict['move_annotations']:
#                   final_path = os.path.abspath(
#                       os.path.join(
#                           parent_dir,
#                           '.data',
#                           orig_video_obj.file_name + '.annotations.xml',
#                       ),
#                   )
#               else:
#                   final_path = moved_path
#
#               if not os.path.isfile(moved_path) \
#               and not os.path.isfile(final_path):
#                   app_obj.move_file_or_directory(xml_path, moved_path)
#
#                   if options_obj.options_dict['move_annotations']:
#                       ttutils.move_metadata_to_subdir(
#                           app_obj,
#                           orig_video_obj,
#                           '.annotations.xml',
#                       )

        # Handle the thumbnail
        if options_obj.options_dict['keep_thumbnail']:

            thumb_path = ttutils.find_thumbnail_from_filename(
                app_obj,
                temp_dir,
                'clip_1',
            )

            if thumb_path is not None and os.path.isfile(thumb_path):

                name, ext = os.path.splitext(thumb_path)

                moved_path = os.path.abspath(
                    os.path.join(
                        parent_dir,
                        orig_video_obj.file_name + ext,
                    ),
                )

                if not os.path.isfile(moved_path):
                    app_obj.move_file_or_directory(thumb_path, moved_path)

                    # Convert .webp thumbnails to .jpg, if required
                    convert_path \
                    = ttutils.find_thumbnail_webp_intact_or_broken(
                        app_obj,
                        orig_video_obj,
                    )
                    if convert_path is not None \
                    and not app_obj.ffmpeg_fail_flag \
                    and app_obj.ffmpeg_convert_webp_flag \
                    and not app_obj.ffmpeg_manager_obj.convert_webp(
                        convert_path,
                    ):
                        app_obj.set_ffmpeg_fail_flag(True)
                        GObject.timeout_add(
                            0,
                            app_obj.system_error,
                            310,
                            app_obj.ffmpeg_fail_msg,
                        )

                    # Move to the sub-directory, if required
                    if options_obj.options_dict['move_thumbnail']:
                        ttutils.move_thumbnail_to_subdir(
                            app_obj,
                            orig_video_obj,
                        )


    def read_child_process(self):

        """Called by self.do_download_clips() and
        self.do_download_remove_slices().

        Reads from the child process STDOUT and STDERR, in the correct order.

        Return values:

            True if either STDOUT or STDERR were read, None if both queues were
                empty

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9052 read_child_process')

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
                311,
                'Malformed STDOUT or STDERR data',
            )

        # STDOUT or STDERR has been read
        data = mini_list[2].rstrip()
        # On MS Windows we use cp1252, so that Tartube can communicate with the
        #   Windows console
        data = data.decode(ttutils.get_encoding(), 'replace')

        # STDOUT
        if mini_list[1] == 'stdout':

            # Remove weird carriage returns that insert empty lines into the
            #   Output tab
            data = re.sub(r'[\r]+', '', data)

            # Extract output from STDOUT
            self.extract_stdout_data(data)

            # Show output in the Output tab (if required)
            if app_obj.ytdl_output_stdout_flag:

                app_obj.main_win_obj.output_tab_write_stdout(
                    self.download_worker_obj.worker_id,
                    data,
                )

            # Show output in the terminal (if required)
            if app_obj.ytdl_write_stdout_flag:

                # Git #175, Japanese text may produce a codec error
                #   here, despite the .decode() call above
                try:
                    print(
                        data.encode(
                            ttutils.get_encoding(),
                            'replace',
                        ),
                    )
                except:
                    print(
                        'STDOUT text with unprintable characters'
                    )

            # Write output in the downloader log (if required)
            if app_obj.ytdl_output_stdout_flag:
                app_obj.write_downloader_log(data)

        # STDERR (ignoring any empty error messages)
        elif data != '':

            # v2.3.168 I'm not sure that any detectable errors are actually
            #   produced, but nevertheless this section can handle any such
            #   errors

            # After a network error, stop trying to download clips
            if self.is_network_error(data):

                self.stop()
                self.last_data_callback()
                self.set_return_code(self.STALLED)

                self.queue.task_done()
                return None

            # Show output in the Output tab (if required)
            if app_obj.ytdl_output_stderr_flag:
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    data,
                )

            # Show output in the terminal (if required)
            if app_obj.ytdl_write_stderr_flag:
                # Git #175, Japanese text may produce a codec error here,
                #   despite the .decode() call above
                try:
                    print(data.encode(ttutils.get_encoding(), 'replace'))
                except:
                    print('STDERR text with unprintable characters')

            # Write output to the downloader log (if required)
            if app_obj.ytdl_log_stderr_flag:
                app_obj.write_downloader_log(data)

        # Either (or both) of STDOUT and STDERR were non-empty
        self.queue.task_done()
        return True


    def set_return_code(self, code):

        """Called by self.do_download_clips(), .do_download_remove_slices(),
        .create_child_process() and .stop().

        Based on YoutubeDLDownloader._set_returncode().

        After the child process has terminated with an error of some kind,
        sets a new value for self.return_code, but only if the new return code
        is higher in the hierarchy of return codes than the current value.

        Args:

            code (int): A return code in the range 0-5

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9182 set_return_code')

        if code >= self.return_code:
            self.return_code = code


    def stop(self):

        """Called by DownloadWorker.close() and also by
        mainwin.MainWin.on_progress_list_stop_now().

        Terminates the child process and sets this object's return code to
        self.STOPPED.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9198 stop')

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

        Sets the flag that causes this ClipDownloader to stop after the
        current video.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 9228 stop_soon')

        self.stop_soon_flag = True
