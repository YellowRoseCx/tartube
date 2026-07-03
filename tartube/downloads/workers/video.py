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
class VideoDownloader(object):

    """Called by downloads.DownloadWorker.run_video_downloader() or
    .run_stream_downloader().

    Based on the YoutubeDLDownloader class in youtube-dl-gui.

    Python class to create a system child process. Uses the child process to
    instruct youtube-dl to download all videos associated with the URL
    described by a downloads.DownloadItem object (which might be an individual
    video, or a channel or playlist).

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
            describing the URL from which youtube-dl should download video(s)

        force_sim_flag (bool): Set to True when called by
            .run_stream_downloader(), in which case a simulated download rather
            than a real download is performed, regardless of other settings

    Warnings:

        The calling function is responsible for calling the close() method
        when it's finished with this object, in order for this object to
        properly close down.

    """


    # Attributes


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
    download_item_obj, force_sim_flag=False):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3314 __init__')

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
        #   self.do_download()
        self.sleep_time = 0.1
        # The time (in seconds) to wait for an existing download, which shares
        #   a common download destination with this media data object, to
        #   finish downloading
        self.long_sleep_time = 10

        # The time (matches time.time() ) at which the first youtube-dl
        #   network error was detected. Reset back to None when the download
        #   resumes. If the download does not resume quickly enough
        #   (according to settings), then this download is marked as stalled,
        #   and can be restarted, if settings require that
        self.network_error_time = None

        # Flag set to True if we are simulating downloads for this media data
        #   object, or False if we actually downloading videos (updated below)
        self.dl_sim_flag = force_sim_flag
        # Flag set to True if this download operation was launched from the
        #   Classic Mode tab, False if not (set below)
        self.dl_classic_flag = False

        # Flag set to True by a call from any function to self.stop_soon()
        # After being set to True, this VideoDownloader should give up after
        #   the next call to self.confirm_new_video(), .confirm_old_video()
        #   .confirm_sim_video()
        self.stop_soon_flag = False
        # Exception: after the FFmpeg "Merging formats into..." message, wait
        #   for the merge to complete before giving up
        self.stop_after_merge_flag = False
        # When self.stop_soon_flag is True, the next call to
        #   self.confirm_new_video(), .confirm_old_video() or
        #   .confirm_sim_video() sets this flag to True, informing
        #   self.do_download() that it can stop the child process
        self.stop_now_flag = False

        # youtube-dl is passed a URL, which might represent an individual
        #   video, a channel or a playlist
        # Assume it's an individual video unless youtube-dl reports a
        #   channel or playlist (in which case, we can update these IVs later)
        # For real downloads, self.video_num is the current video number, and
        #   self.video_total is the number of videos in the channel/playlist
        # For simulated downloads, both IVs are set to the number of
        #   videos actually found
        self.video_num = 0
        self.video_total = 0
        # When the 'Downloading webpage' message is detected, denoting the
        #   start of a real (not simulated) download, this IV is set to the
        #   video's ID. The value is reset when self.confirm_new_video() etc
        #   is called, or when an error/warning with a different video ID is
        #   detected
        # When set, any youtube-dl errors/warnings which do not specify their
        #   own video ID can be assumed to belong to this video
        self.probable_video_id = None
        # self.extract_stdout_data() detects the completion of a download job
        #   in one of several ways
        # The first time it happens for each individual video,
        #   self.extract_stdout_data() takes action. It calls
        #   self.confirm_new_video(), self.confirm_old_video() or
        #   self.confirm_sim_video() when required
        # On subsequent occasions, the completion message is ignored (as
        #   youtube-dl may pass us more than one completion message for a
        #   single video)
        # There is one exception: in calls to self.confirm_new_video, a
        #   subsequent call to self.confirm_new_video() updates the file
        #   extension of the media.Video. (yt-dlp and/or FFmpeg may send
        #   several completion messages as it converts one file format to
        #   another; the final one is the one we want)
        # Dictionary of videos, used to check for the first completion message
        #   for each unique video
        # Dictionary in the form
        #       key = the video number (matches self.video_num)
        #       value = the media.Video object created
        self.video_check_dict = {}
        # The code imported from youtube-dl-gui doesn't recognise a downloaded
        #   video, if FFmpeg isn't used to extract it (because FFmpeg is not
        #   installed, or because the website doesn't support it, or whatever)
        # In this situation, youtube-dl's STDOUT messages don't definitively
        #   establish when it has finished downloading a video
        # When a file destination is announced; it is temporarily stored in
        #   these IVs. When STDOUT receives a message in the form
        #       [download] 100% of 2.06MiB in 00:02
        #   ...and the filename isn't one that FFmpeg would use (e.g.
        #       'myvideo.f136.mp4' or 'myvideo.f136.m4a', then assume that the
        #       video has finished downloading
        self.temp_path = None
        self.temp_filename = None
        self.temp_extension = None

        # When checking a channel/playlist, this number is incremented every
        #   time youtube-dl gives us the details of a video which the Tartube
        #   database already contains (with a minimum number of IVs already
        #   set)
        # When downloading a channel/playlist, this number is incremented every
        #   time youtube-dl gives us a 'video already downloaded' message
        #   (unless the Tartube database hasn't actually marked the video as
        #   downloaded)
        # Every time the value is incremented, we check the limits specified by
        #   mainapp.TartubeApp.operation_check_limit or
        #   .operation_download_limit. If the limit has been reached, we stop
        #   checking/downloading the channel/playlist
        # No check is carried out if self.download_item_obj represents an
        #   individual media.Video object (and not a whole channel or playlist)
        self.video_limit_count = 0
        # Git issue #9 describes youtube-dl failing to download the video's
        #   JSON metadata. We can't do anything about the youtube-dl code, but
        #   we can apply our own timeout
        # This IV is set whenever self.confirm_sim_video() is called. After
        #   being set, if a certain time has passed without another call to
        #   self.confirm_sim_video, self.do_download() halts the child process
        # The time to wait is specified by mainapp.TartubeApp IVs
        #   .json_timeout_no_comments_time and .json_timeout_with_comments_time
        self.last_sim_video_check_time = None

        # If mainapp.TartubeApp.operation_convert_mode is set to any value
        #   other than 'disable', then a media.Video object whose URL
        #   represents a channel/playlist is converted into multiple new
        #   media.Video objects, one for each video actually downloaded
        # Flag set to True when self.download_item_obj.media_data_obj is a
        #   media.Video object, but a channel/playlist is detected (regardless
        #   of the value of mainapp.TartubeApp.operation_convert_mode)
        self.url_is_not_video_flag = False
        # Flag which specifies whether formats.ACTIVE_STAGE_PRE_PROCESS or
        #   formats.ACTIVE_STAGE_POST_PROCESS currently applies
        # Set to True by self.extract_stdout_data() when
        #   formats.ACTIVE_STAGE_DOWNLOAD is detected; set back to False by the
        #   same function when the start of a new video download is detected
        self.video_download_started_flag = False

        # Buffer for youtube-dl error/warning messages that can be associated
        #   with a particular video ID
        # The corresponding media.Video object might not exist at the time the
        #   error/warning is processed, so it is temporarily stored here, so
        #   that the parent downloads.DownloadWorker can retrieve it
        # Dictionary in the form
        #   key = The video ID (corresponds to media.Video.vid)
        #   value = A list in the form
        #       [ [type, message], [type, message] ... ]
        # ...where 'type' is the string 'error' or 'warning', and 'message'
        #   is the error/warning generated
        self.video_msg_buffer_dict = {}
        # Errors/warnings for individual media.Video objects requires special
        #   handling. We can't predict where, in the check/download process,
        #   the first error/warning will occur
        # Dictionary of videos which have been assigned an error/warning
        #   by this instance of the VideoDownloader. The first error/warning
        #   removes any errors/warnings generated by previous operations.
        #   The call to self.confirm_new_video(), .confirm_old_video() and
        #   .confirm_sim_video() removes any errors/warnings generated by
        #   previous operations by consulting this dictionary
        # Dictionary in the form
        #   key = The video ID (corresponds to media.Video.vid)
        #   value = True (not required)
        self.video_error_warning_dict = {}

        # List of regexes used by self.extract_stdout_data() to check for
        #   certain filtered videos
        # As of January 2025, these regexes match both youtube-dl and yt-dlp
        self.filter_regex_list = [
            r'upload date is not in range',
            r'because it has not reached minimum view count',
            r'because it has exceeded the maximum view count',
            r'because it is age restricted',
        ]

        # For channels/playlists, a list of child media.Video objects, used to
        #   track missing videos (when required)
        self.missing_video_check_list = []
        # Flag set to True (for convenience) if the list is populated
        self.missing_video_check_flag = False


        # Code
        # ----
        # Initialise IVs depending on whether this is a real or simulated
        #   download
        media_data_obj = self.download_item_obj.media_data_obj

        # All media data objects can be marked as simulate downloads only
        #   (except when the download operation was launched from the Classic
        #   Mode tab)
        # The setting applies not just to the media data object, but all of its
        #   descendants
        if not self.download_item_obj.operation_classic_flag:

            if (
                force_sim_flag \
                or self.download_item_obj.operation_type == 'sim' \
                or self.download_item_obj.operation_type == 'custom_sim'
            ):
                dl_sim_flag = True
            else:
                dl_sim_flag = media_data_obj.dl_sim_flag
                parent_obj = media_data_obj.parent_obj

                while not dl_sim_flag and parent_obj is not None:
                    dl_sim_flag = parent_obj.dl_sim_flag
                    parent_obj = parent_obj.parent_obj

            if dl_sim_flag:
                self.dl_sim_flag = True
            else:
                self.dl_sim_flag = False

        else:

            self.dl_classic_flag = True
            if self.download_item_obj.operation_type == 'classic_sim':
                self.dl_sim_flag = True

        # If the user wants to detect missing videos in channels/playlists
        #   (those that have been downloaded by the user, but since removed
        #   from the website by the creator), set that up
        if (
            isinstance(media_data_obj, media.Channel) \
            or isinstance(media_data_obj, media.Playlist)
        ) and (
            self.download_item_obj.operation_type == 'real' \
            or self.download_item_obj.operation_type == 'sim'
        ) and download_manager_obj.app_obj.track_missing_videos_flag:

            # Compile a list of child videos. Videos can be removed from the
            #   list as they are detected
            self.missing_video_check_list = media_data_obj.child_list.copy()
            if self.missing_video_check_list:
                self.missing_video_check_flag = True


    # Public class methods


    def do_download(self):

        """Called by downloads.DownloadWorker.run_video_downloader().

        Based on YoutubeDLDownloader.download().

        Downloads video(s) from a URL described by self.download_item_obj.

        Return values:

            The final return code, a value in the range 0-5 (as described
                above)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3578 do_download')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Set the default return code. Everything is OK unless we encounter
        #   any problems
        self.set_return_code(self.OK)

        if not self.dl_classic_flag:

            # Reset the errors/warnings stored in the media data object, the
            #   last time it was checked/downloaded
            self.download_item_obj.media_data_obj.reset_error_warning()
            if isinstance(
                self.download_item_obj.media_data_obj,
                media.Video,
            ):
                self.download_item_obj.media_data_obj.set_block_flag(False)

            else:
                # If two channels/playlists/folders share a download
                #   destination, we don't want to download both of them at the
                #   same time
                # If this media data obj shares a download destination with
                #   another downloads.DownloadWorker, wait until that download
                #   has finished before starting this one
                while self.download_manager_obj.check_master_slave(
                    self.download_item_obj.media_data_obj,
                ):
                    time.sleep(self.long_sleep_time)

        # Prepare a system command...
        options_obj = self.download_worker_obj.options_manager_obj
        if options_obj.options_dict['direct_cmd_flag']:

            cmd_list = ttutils.generate_direct_system_cmd(
                app_obj,
                self.download_item_obj.media_data_obj,
                options_obj,
            )

        else:

            divert_mode = None
            if (
                self.download_item_obj.operation_type == 'custom_real' \
                or self.download_item_obj.operation_type == 'classic_custom'
            ) and isinstance(
                self.download_item_obj.media_data_obj,
                media.Video,
            ) and self.download_manager_obj.custom_dl_obj:
                divert_mode \
                = self.download_manager_obj.custom_dl_obj.divert_mode


            import subprocess
            import json
            import copy

            # Check if we are re-downloading and 'Keep existing files' is selected
            # We know this if media is a Video, it has downloaded_formats, and the archive is *NOT* blocked
            media_obj = self.download_item_obj.media_data_obj
            modified_options_list = copy.deepcopy(self.download_worker_obj.options_list)

            if isinstance(media_obj, media.Video) and hasattr(media_obj, 'downloaded_formats') and len(media_obj.downloaded_formats) > 0 and self.dl_classic_flag == False and not self.dl_sim_flag:
                # Construct a custom format string that excludes downloaded formats
                # We do this by running yt-dlp -J to get the current formats and their bitrates,
                # and comparing them against our stored bitrates.

                # Include auth/cookie args for the -J dump command
                # Include auth/cookie args for the -J dump command
                # Safely fallback to video URL if media_obj.source is missing or None
                video_url = getattr(media_obj, 'source', None) or media_obj.get_url()
                dump_cmd = [app_obj.ytdl_path, '-J', video_url]

                # Copy authentication-related arguments
                skip_next = False
                for arg_idx, arg in enumerate(modified_options_list):
                    if skip_next:
                        skip_next = False
                        continue
                    if arg.startswith('--cookies') or arg == '--username' or arg == '--password' or arg == '--proxy':
                        dump_cmd.append(arg)
                        if not arg.startswith('--cookies=') and arg_idx + 1 < len(modified_options_list):
                            dump_cmd.append(modified_options_list[arg_idx + 1])
                            skip_next = True
                try:
                    proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = proc.communicate(timeout=15)
                    video_info = json.loads(stdout)

                    available_formats = video_info.get('formats', [])
                    format_bitrates = {}
                    for f in available_formats:
                        fid = str(f.get('format_id'))
                        tbr = f.get('tbr')
                        vbr = f.get('vbr')
                        abr = f.get('abr')
                        tbr = float(tbr) if tbr is not None else 0.0
                        vbr = float(vbr) if vbr is not None else 0.0
                        abr = float(abr) if abr is not None else 0.0
                        bitrate = tbr or (vbr + abr)
                        format_bitrates[fid] = bitrate

                    downloaded_ids_to_exclude = set()
                    exclusion_str = ""

                    for existing in media_obj.downloaded_formats:
                        if isinstance(existing, dict):
                            fid = existing.get('id')
                            stored_bitrate = existing.get('bitrate', 0)
                            current_bitrate = format_bitrates.get(fid, 0)

                            # Exclude if the current bitrate is NOT greater than what we already have
                            if current_bitrate <= stored_bitrate:
                                downloaded_ids_to_exclude.add(fid)
                        elif isinstance(existing, str):
                            # Legacy format, just exclude it
                            downloaded_ids_to_exclude.add(existing)

                    if downloaded_ids_to_exclude:
                        exclusion_str = "".join([f"[format_id!={fid}]" for fid in downloaded_ids_to_exclude])

                        # Find if there's an existing -f arg
                        format_idx = -1
                        if '-f' in modified_options_list:
                            format_idx = modified_options_list.index('-f')
                        elif '--format' in modified_options_list:
                            format_idx = modified_options_list.index('--format')

                        if format_idx != -1 and format_idx + 1 < len(modified_options_list):
                            existing_format = modified_options_list[format_idx + 1]

                            # Format comma separated
                            new_comma_parts = []
                            for comma_part in existing_format.split(','):
                                new_slash_parts = []
                                for slash_part in comma_part.split('/'):
                                    new_plus_parts = []
                                    for plus_part in slash_part.split('+'):
                                        # Fix brackets for yt-dlp: if there's already a bracket, insert into it
                                        if ']' in plus_part:
                                            # Remove outer brackets from exclusion string to make it comma separated for insertion inside existing bracket
                                            inner_exclusion = exclusion_str.replace('][', ',').replace('[', '').replace(']', '')
                                            # insert it right before the last bracket
                                            idx = plus_part.rfind(']')
                                            new_part = plus_part[:idx] + ',' + inner_exclusion + plus_part[idx:]
                                        else:
                                            new_part = f"{plus_part}{exclusion_str}"
                                        new_plus_parts.append(new_part)
                                    new_slash_parts.append("+".join(new_plus_parts))
                                new_comma_parts.append("/".join(new_slash_parts))

                            modified_options_list[format_idx + 1] = ",".join(new_comma_parts)
                        else:
                            modified_options_list.extend(['-f', f"bestvideo{exclusion_str}+bestaudio{exclusion_str}/best{exclusion_str}"])
                except Exception as e:
                    print(f"Failed to fetch format info for deduplication: {e}")

            cmd_list = ttutils.generate_ytdl_system_cmd(
                app_obj,
                self.download_item_obj.media_data_obj,
                modified_options_list,
                self.dl_sim_flag,
                self.dl_classic_flag,
                self.missing_video_check_flag,
                self.download_manager_obj.custom_dl_obj,
                divert_mode,
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

            # Apply the JSON timeout, if required
            if app_obj.apply_json_timeout_flag \
            and self.last_sim_video_check_time is not None \
            and self.last_sim_video_check_time < time.time():
                # Halt the child process, which stops checking this channel/
                #   playlist
                self.stop()

                GObject.timeout_add(
                    0,
                    app_obj.system_error,
                    303,
                    'Enforced timeout because downloader took too long to' \
                    + ' fetch a video\'s JSON data',
                )

            # If a download has stalled (there has been no activity for some
            #   time), halt the child process (allowing the parent worker to
            #   restart the stalled download, if required)
            if app_obj.operation_auto_restart_flag \
            and self.network_error_time is not None:

                restart_time = app_obj.operation_auto_restart_time * 60
                if (self.network_error_time + restart_time) < time.time():

                    # Stalled download. Stop the child process
                    self.stop()

                    # Pass a dictionary of values to downloads.DownloadWorker,
                    #   confirming the result of the job. The values are passed
                    #   on to the main window
                    self.set_return_code(self.STALLED)
                    self.last_data_callback()

                    return self.return_code

            # Stop this video downloader, if required to do so, having just
            #   finished checking/downloading a video
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
            #   Output tab, terminal and/or downloader log)
            self.set_error(
                self.download_item_obj.media_data_obj,
                internal_msg,
            )

            if app_obj.ytdl_output_stderr_flag:
                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    internal_msg,
                )

            if app_obj.ytdl_write_stderr_flag:
                print(internal_msg)

            if app_obj.ytdl_log_stderr_flag:
                app_obj.write_downloader_log(internal_msg)

        # For channels/playlists, detect missing videos (those downloaded by
        #   the user, but since deleted from the website by the creator)
        # We only perform the check if the process completed without errors,
        #   and was not halted early by the user (or halted by the download
        #   manager, because too many videos have been downloaded)
        # We also ignore livestreams
        detected_list = []

        if app_obj.track_missing_videos_flag \
        and self.missing_video_check_list \
        and self.download_manager_obj.running_flag \
        and not self.stop_soon_flag \
        and not self.stop_now_flag \
        and self.return_code <= self.WARNING \
        and self.video_num > 0:
            for check_obj in self.missing_video_check_list:
                if check_obj.dbid in app_obj.media_reg_dict \
                and check_obj.dl_flag \
                and not check_obj.live_mode:

                    # Filter out videos that are too old
                    if (
                        app_obj.track_missing_time_flag \
                        and app_obj.track_missing_time_days > 0
                    ):
                        # Convert the video's upload time from seconds to days
                        days = check_obj.upload_time / (60 * 60 * 24)
                        if days <= app_obj.track_missing_time_days:

                            # Mark this video as missing
                            detected_list.append(check_obj)

                    else:

                        # Mark this video as missing
                        detected_list.append(check_obj)

        for detected_obj in detected_list:
            app_obj.mark_video_missing(
                detected_obj,
                True,       # Video is missing
                True,       # Don't update the Video Index
                True,       # Don't update the Video Catalogue
                True,       # Don't sort the parent channel/playlist
            )

        # Pass a dictionary of values to downloads.DownloadWorker, confirming
        #   the result of the job. The values are passed on to the main
        #   window
        self.last_data_callback()

        # Pass the result back to the parent downloads.DownloadWorker object
        return self.return_code


    def check_dl_is_correct_type(self):

        """Called by self.extract_stdout_data().

        When youtube-dl reports the URL associated with the download item
        object contains multiple videos (or potentially contains multiple
        videos), then the URL represents a channel or playlist, not a video.

        This function checks whether a channel/playlist is about to be
        downloaded into a media.Video object. If so, it takes action to prevent
        that from happening.

        The action taken depends on the value of
        mainapp.TartubeApp.operation_convert_mode.

        Return values:

            False if a channel/playlist was about to be downloaded into a
                media.Video object, which has since been replaced by a new
                media.Channel/media.Playlist object

            True in all other situations (including when a channel/playlist was
                about to be downloaded into a media.Video object, which was
                not replaced by a new media.Channel/media.Playlist object)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3847 check_dl_is_correct_type')

        # Special case: if the download operation was launched from the
        #   Classic Mode tab, there is no need to do anything
        if self.dl_classic_flag:
            return True

        # Otherwise, import IVs (for convenience)
        app_obj = self.download_manager_obj.app_obj
        media_data_obj = self.download_item_obj.media_data_obj

        if isinstance(self.download_item_obj.media_data_obj, media.Video):

            # If the mode is 'disable', or if it the original media.Video
            #   object is contained in a channel or a playlist, then we must
            #   stop downloading this URL immediately
            if app_obj.operation_convert_mode == 'disable' \
            or not isinstance(
                self.download_item_obj.media_data_obj.parent_obj,
                media.Folder,
            ):
                self.url_is_not_video_flag = True

                # Stop downloading this URL
                self.stop()
                self.set_error(
                    media_data_obj,
                    '\'' + media_data_obj.name + '\' ' + _(
                        'This video has a URL that points to a channel or a' \
                        + ' playlist, not a video',
                    ),
                )

                # Don't allow self.confirm_sim_video() to be called
                return False

            # Otherwise, we can create new media.Video objects for each
            #   video downloaded/checked. The new objects may be placd into a
            #   new media.Channel or media.Playlist object
            elif not self.url_is_not_video_flag:

                self.url_is_not_video_flag = True

                # Mark the original media.Video object to be destroyed at the
                #   end of the download operation
                self.download_manager_obj.mark_video_as_doomed(media_data_obj)

                if app_obj.operation_convert_mode != 'multi':

                    # Create a new media.Channel or media.Playlist object and
                    #   add it to the download manager
                    # Then halt this job, so the new channel/playlist object
                    #   can be downloaded
                    self.convert_video_to_container()

                # Don't allow self.confirm_sim_video() to be called
                return False

        # Do allow self.confirm_sim_video() to be called
        return True


    def close(self):

        """Can be called by anything.

        Destructor function for this object.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3917 close')

        # Tell the PipeReader objects to shut down, thus joining their threads
        self.stdout_reader.join()
        self.stderr_reader.join()


    def confirm_archived_video(self, filename):

        """Called by self.extract_stdout_data().

        A modified version of self.confirm_old_video(), called when
        youtube-dl's 'has already been recorded in archive' message is detected
        (but only when checking for missing videos).

        Tries to find a match for the video name and, if one is found, marks it
        as not missing.

        Args:

            filename (str): The video name, which should match the .name of a
                media.Video object in self.missing_video_check_list

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3943 confirm_archived_video')

        # Create shortcut variables (for convenience)
        app_obj = self.download_manager_obj.app_obj
        media_data_obj = self.download_item_obj.media_data_obj

        # media_data_obj is a media.Channel or media.Playlist object. Check its
        #   child objects, looking for a matching video
        match_obj = media_data_obj.find_matching_video(app_obj, filename)
        if match_obj and match_obj in self.missing_video_check_list:
            self.missing_video_check_list.remove(match_obj)


    def confirm_filtered_video(self):

        """Called by self.extract_stdout_data().

        A modified version of self.confirm_old_video(), handling only the
        checks for operation limits.

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3944 confirm_filtered_video')

        # Create shortcut variables (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # This filtered video applies towards the limit specified by
        #  mainapp.TartubeApp.operation_download_limit (which the calling code
        #   has already checked is enabled)

        self.video_limit_count += 1

        if not isinstance(self.download_item_obj.media_data_obj, media.Video) \
        and not self.download_item_obj.ignore_limits_flag:

            if (
                self.dl_sim_flag \
                and app_obj.operation_check_limit \
                and self.video_limit_count >= app_obj.operation_check_limit
            ) or (
                not self.dl_sim_flag \
                and app_obj.operation_download_limit \
                and self.video_limit_count >= app_obj.operation_download_limit
            ):
                # Limit reached; stop downloading videos in this channel/
                #   playlist
                self.stop()


    def confirm_new_video(self, dir_path, filename, extension, \
    merge_flag=False):

        """Called by self.extract_stdout_data().

        A successful download is announced in one of several ways.

        When an announcement is detected, this function is called. Use the
        first announcement to update self.video_check_dict. For subsequent
        announcements, only a media.Video's file extension is updated (see the
        comments in self.__init__() ).

        Args:

            dir_path (str): The full path to the directory in which the video
                is saved, e.g. '/home/yourname/tartube/downloads/Videos'

            filename (str): The video's filename, e.g. 'My Video'

            extension (str): The video's extension, e.g. '.mp4'

            merge_flag (bool): True if this function was called as the result
                of a 'Merging formats into...' message

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3983 confirm_new_video')

        # Create shortcut variables (for convenience)
        app_obj = self.download_manager_obj.app_obj
        media_data_obj = self.download_item_obj.media_data_obj

        # Error/warning handling for individual videos
        video_obj = None

        # Special case: don't add videos to the Tartube database at all
        if not isinstance(media_data_obj, media.Video) \
        and media_data_obj.dl_no_db_flag:

            # Add this video to the buffer that will handle the removal of
            #   metadata files, at the end of the download operation
            app_obj.other_metadata_buffer_list.append({
                'options_obj': self.download_worker_obj.options_manager_obj,
                'dir_path': dir_path,
                'filename': filename,
            })

            # Register the download with DownloadManager, so that download
            #   limits can be applied, if required
            self.download_manager_obj.register_video('new')

        # Special case: if the download operation was launched from the
        #   Classic Mode tab, then we only need to update the dummy
        #   media.Video object, and to move/remove description/metadata/
        #   thumbnail files, as appropriate
        elif self.dl_classic_flag:

            self.confirm_new_video_classic_mode(dir_path, filename, extension)

        # All other cases
        elif not self.video_num in self.video_check_dict:

            # Create a new media.Video object for the video
            if self.url_is_not_video_flag:

                video_obj = app_obj.convert_video_from_download(
                    self.download_item_obj.media_data_obj.parent_obj,
                    self.download_item_obj.options_manager_obj,
                    dir_path,
                    filename,
                    extension,
                    True,               # Don't sort parent containers yet
                )

            else:

                video_obj = app_obj.create_video_from_download(
                    self.download_item_obj,
                    dir_path,
                    filename,
                    extension,
                    True,               # Don't sort parent containers yet
                )

            # If downloading from a channel/playlist, remember the video's
            #   index. (The server supplies an index even for a channel, and
            #   the user might want to convert a channel to a playlist)
            if self.video_num > 0 and (
                isinstance(video_obj.parent_obj, media.Channel) \
                or isinstance(video_obj.parent_obj, media.Playlist)
            ):
                video_obj.set_index(self.video_num)

            # Contact SponsorBlock server to fetch video slice data
            if app_obj.custom_sblock_mirror != '' \
            and app_obj.sblock_fetch_flag \
            and video_obj.vid != None \
            and (not video_obj.slice_list or app_obj.sblock_replace_flag):
                ttutils.fetch_slice_data(
                    app_obj,
                    video_obj,
                    self.download_worker_obj.worker_id,
                    True,       # Write to terminal/log, if allowed
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
            self.download_manager_obj.register_video('new')

            # Update the checklist
            if self.video_num > 0:
                self.video_check_dict[self.video_num] = video_obj

        elif self.video_num > 0:

            # Update the video's file extension, in case one file format has
            #   been converted to another (with a new call to this function
            #   each time)
            video_obj = self.video_check_dict[self.video_num]

            if video_obj.file_ext is None \
            or (extension is not None and video_obj.file_ext != extension):
                video_obj.set_file_ext(extension)

        # The probable video ID, if captured, can now be reset
        self.probable_video_id = None

        if video_obj:

            # If no errors/warnings were received during this operation,
            #   errors/warnings that already exist (from previous operations)
            #   can now be cleared
            if not video_obj.dbid in self.video_error_warning_dict:
                video_obj.reset_error_warning()

            # This confirmation clears a video marked as blocked
            video_obj.set_block_flag(False)

        # This VideoDownloader can now stop, if required to do so after a video
        #   has been checked/downloaded
        if self.stop_soon_flag:
            if merge_flag and not self.stop_now_flag:
                self.stop_after_merge_flag = True
            else:
                self.stop_now_flag = True


    def confirm_new_video_classic_mode(self, dir_path, filename, extension):

        """Called by self.confirm_new_video() when a download operation was
        launched from the Classic Mode tab.

        Handles the download.

        Args:

            dir_path (str): The full path to the directory in which the video
                is saved, e.g. '/home/yourname/tartube/downloads/Videos'

            filename (str): The video's filename, e.g. 'My Video'

            extension (str): The video's extension, e.g. '.mp4'

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 4135 confirm_new_video_classic_mode')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Update the dummy media.Video object
        dummy_obj = self.download_item_obj.media_data_obj

        dummy_obj.set_dl_flag(True)
        dummy_obj.set_dummy_path(
            os.path.abspath(os.path.join(dir_path, filename + extension)),
        )

        # Contact SponsorBlock server to fetch video slice data
        if app_obj.custom_sblock_mirror != '' \
        and app_obj.sblock_fetch_flag \
        and dummy_obj.vid != None \
        and (not dummy_obj.slice_list or app_obj.sblock_replace_flag):
            ttutils.fetch_slice_data(
                app_obj,
                dummy_obj,
                self.download_worker_obj.worker_id,
                True,       # Write to terminal/log, if allowed
            )

        # Add this video to the buffer that will handle the removal of metadata
        #   files, at the end of the download operation
        app_obj.other_metadata_buffer_list.append({
            'options_obj': self.download_worker_obj.options_manager_obj,
            'dir_path': dir_path,
            'filename': filename,
            'dummy_obj': dummy_obj,
        })

        # Register the download with DownloadManager, so that download limits
        #   can be applied, if required
        self.download_manager_obj.register_video('new')

        # The probable video ID, if captured, can now be reset
        self.probable_video_id = None


    def confirm_old_video(self, dir_path, filename, extension):

        """Called by self.extract_stdout_data().

        When youtube-dl reports a video has already been downloaded, make sure
        the media.Video object is marked as downloaded, and upate the main
        window if necessary.

        Args:

            dir_path (str): The full path to the directory in which the video
                is saved, e.g. '/home/yourname/tartube/downloads/Videos'

            filename (str): The video's filename, e.g. 'My Video'

            extension (str): The video's extension, e.g. '.mp4'

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 4197 confirm_old_video')

        # Create shortcut variables (for convenience)
        app_obj = self.download_manager_obj.app_obj
        media_data_obj = self.download_item_obj.media_data_obj

        # Error/warning handling for individual videos
        if isinstance(media_data_obj, media.Video):
            video_obj = media_data_obj
        else:
            video_obj = None

        # Special case: don't add videos to the Tartube database at all
        if video_obj is None and media_data_obj.dl_no_db_flag:

            # Register the download with DownloadManager, so that download
            #   limits can be applied, if required
            self.download_manager_obj.register_video('old')

        # Special case: if the download operation was launched from the
        #   Classic Mode tab, then we only need to update the dummy
        #   media.Video object
        elif self.dl_classic_flag:

            media_data_obj.set_dl_flag(True)
            media_data_obj.set_dummy_path(
                os.path.abspath(os.path.join(dir_path, filename + extension)),
            )

            # Register the download with DownloadManager, so that download
            #   limits can be applied, if required
            self.download_manager_obj.register_video('old')

        # All other cases
        elif video_obj:

            # v2.4.456: added an additional check; if youtube-dl downloaded the
            #   video but Tartube's database didn't detect it in the filesystem
            #   (for example because of encoding problems in Git #320), then
            #   this call to mark_video_downloaded() messes up the database
            if not video_obj.dl_flag \
            and video_obj.name == filename \
            and os.path.isfile(
                os.path.abspath(os.path.join(dir_path, filename + extension)),
            ):
                GObject.timeout_add(
                    0,
                    app_obj.mark_video_downloaded,
                    video_obj,
                    True,               # Video is downloaded
                    True,               # Video is not new
                )

        else:

            # media_data_obj is a media.Channel or media.Playlist object. Check
            #   its child objects, looking for a matching video
            match_obj = media_data_obj.find_matching_video(app_obj, filename)
            if match_obj:

                # This video will not be marked as a missing video
                if match_obj in self.missing_video_check_list:
                    self.missing_video_check_list.remove(match_obj)

                if not match_obj.dl_flag:

                    GObject.timeout_add(
                        0,
                        app_obj.mark_video_downloaded,
                        match_obj,
                        True,           # Video is downloaded
                        True,           # Video is not new
                    )

                else:

                    # Register the download with DownloadManager, so that
                    #   download limits can be applied, if required
                    self.download_manager_obj.register_video('old')

                    # This video applies towards the limit (if any) specified
                    #   by mainapp.TartubeApp.operation_download_limit
                    self.video_limit_count += 1

                    if not isinstance(
                        self.download_item_obj.media_data_obj,
                        media.Video,
                    ) \
                    and not self.download_item_obj.ignore_limits_flag \
                    and app_obj.operation_limit_flag \
                    and app_obj.operation_download_limit \
                    and self.video_limit_count >= \
                    app_obj.operation_download_limit:
                        # Limit reached; stop downloading videos in this
                        #   channel/playlist
                        self.stop()

            else:

                # No match found, so create a new media.Video object for the
                #   video file that already exists on the user's filesystem
                video_obj = app_obj.create_video_from_download(
                    self.download_item_obj,
                    dir_path,
                    filename,
                    extension,
                )

                if self.video_num > 0:
                    self.video_check_dict[self.video_num] = video_obj

                # Update the main window
                if media_data_obj.external_dir is not None \
                and media_data_obj.master_dbid != media_data_obj.dbid:

                    # The container is storing its videos in another
                    #   container's sub-directory, which (probably) explains
                    #   why we couldn't find a match. Don't add anything to the
                    #   Results List
                    GObject.timeout_add(
                        0,
                        app_obj.announce_video_clone,
                        video_obj,
                    )

                else:

                    # Do add an entry to the Results List (as well as updating
                    #   the Video Catalogue, as normal)
                    GObject.timeout_add(
                        0,
                        app_obj.announce_video_download,
                        self.download_item_obj,
                        video_obj,
                        ttutils.compile_mini_options_dict(
                            self.download_worker_obj.options_manager_obj,
                        ),
                    )

                    # Register the download with DownloadManager, so that
                    #   download limits can be applied, if required
                    self.download_manager_obj.register_video('new')

        # The probable video ID, if captured, can now be reset
        self.probable_video_id = None

        if video_obj:

            # If no errors/warnings were received during this operation,
            #   errors/warnings that already exist (from previous operations)
            #   can now be cleared
            if not video_obj.dbid in self.video_error_warning_dict:
                video_obj.reset_error_warning()

            # This confirmation clears a video marked as blocked
            video_obj.set_block_flag(False)

        # This VideoDownloader can now stop, if required to do so after a video
        #   has been checked/downloaded
        if self.stop_soon_flag:
            self.stop_now_flag = True


    def confirm_remuxed_video(self, dir_path, filename, extension):

        """Called by self.extract_stdout_data().

        Written to handle problems described in Git #714.

        When youtube-dl reports a video has been remuxed, make sure that the
        media.Video object has its file extension updated.

        If no matching video can be found, call .confirm_old_video() to handle
        it.

        Args:

            dir_path (str): The full path to the directory in which the video
                is saved, e.g. '/home/yourname/tartube/downloads/Videos'

            filename (str): The video's filename, e.g. 'My Video'

            extension (str): The video's extension, e.g. '.mp4'

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 4197 confirm_remuxed_video')

        # Create shortcut variables (for convenience)
        app_obj = self.download_manager_obj.app_obj
        media_data_obj = self.download_item_obj.media_data_obj

        # Find the matching video, and update its file extension
        if isinstance(media_data_obj, media.Video):
            video_obj = media_data_obj

        else:
            video_obj = media_data_obj.find_matching_video(app_obj, filename)

        if video_obj:
            video_obj.set_file_ext(extension)

        else:
            # No matching video found, so let .confirm_old_video() handle it
            return confirm_old_video(self, dir_path, filename, extension)


    def confirm_sim_video(self, json_dict):

        """Called by self.extract_stdout_data().

        After a successful simulated download, youtube-dl presents us with JSON
        data for the video. Use that data to update everything.

        Args:

            json_dict (dict): JSON data from STDOUT, converted into a python
                dictionary

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 4368 confirm_sim_video')

        # Create shortcut variables (for convenience)
        app_obj = self.download_manager_obj.app_obj
        dl_list_obj = self.download_manager_obj.download_list_obj
        options_obj = self.download_worker_obj.options_manager_obj
        # Call self.stop(), if the limit described in the comments for
        #   self.__init__() have been reached
        stop_flag = False

        # Set the time at which a JSON timeout should be applied, if no more
        #   calls to this function have been made
        if app_obj.apply_json_timeout_flag:

            if (
                self.dl_sim_flag \
                and options_obj.options_dict['check_fetch_comments']
            ) or (
                not self.dl_sim_flag \
                and options_obj.options_dict['dl_fetch_comments']
            ):
                wait_secs = app_obj.json_timeout_with_comments_time * 60
            else:
                wait_secs = app_obj.json_timeout_no_comments_time * 60

            self.last_sim_video_check_time = int(time.time()) + wait_secs

        # From the JSON dictionary, extract the data we need
        # Git #177 reports that this value might be 'None', so check for that
        if '_filename' in json_dict \
        and json_dict['_filename'] is not None:
            full_path = json_dict['_filename']
            path, filename, extension = self.extract_filename(full_path)
        else:
            GObject.timeout_add(
                0,
                app_obj.system_error,
                304,
                'Missing filename in JSON data',
            )

            return

        # (Git #322, 'upload_date' might be None)
        if 'upload_date' in json_dict \
        and json_dict['upload_date'] is not None:

            try:
                # date_string in form YYYYMMDD
                date_string = json_dict['upload_date']
                dt_obj = datetime.datetime.strptime(date_string, '%Y%m%d')
                upload_time = dt_obj.timestamp()
            except:
                upload_time = None

        else:
            upload_time = None

        if 'duration' in json_dict:
            duration = json_dict['duration']
        else:
            duration = None

        if 'title' in json_dict:
            name = json_dict['title']
        else:
            name = None

        if 'id' in json_dict:
            vid = json_dict['id']

        chapter_list = []
        if 'chapters' in json_dict:
            chapter_list = json_dict['chapters']

        if 'uploader' in json_dict:
            author = json_dict['uploader']
        elif 'channel' in json_dict:
            author = json_dict['channel']
        else:
            author = None

        if 'description' in json_dict:
            descrip = json_dict['description']
        else:
            descrip = None

        if 'thumbnail' in json_dict:
            thumbnail = json_dict['thumbnail']
        else:
            thumbnail = None

#        if 'webpage_url' in json_dict:
#            source = json_dict['webpage_url']
#        else:
#            source = None
        # !!! DEBUG: yt-dlp Git #119: filter out the extraneous characters at
        #   the end of the URL, if present
        if 'webpage_url' in json_dict:

            source = re.sub(
                r'\&has_verified\=.*\&bpctr\=.*',
                '',
                json_dict['webpage_url'],
            )

        else:
            source = None

        if 'playlist_index' in json_dict:
            playlist_index = json_dict['playlist_index']
        else:
            playlist_index = None

        if 'is_live' in json_dict:
            if json_dict['is_live']:
                live_flag = True
            else:
                live_flag = False
        else:
            live_flag = False

        if 'was_live' in json_dict:
            if json_dict['was_live']:
                was_live_flag = True
            else:
                was_live_flag = False
        else:
            was_live_flag = False

        if 'comments' in json_dict:
            comment_list = json_dict['comments']
        else:
            comment_list = []

        if 'playlist_id' in json_dict:
            playlist_id = json_dict['playlist_id']
            if 'playlist_title' in json_dict:
                playlist_title = json_dict['playlist_title']
            else:
                playlist_title = None
        else:
            playlist_id = None

        if 'subtitles' in json_dict and json_dict['subtitles']:
            subs_flag = True
        else:
            subs_flag = False

        # Does an existing media.Video object match this video?
        media_data_obj = self.download_item_obj.media_data_obj
        video_obj = None

        if self.url_is_not_video_flag:

            # media_data_obj has a URL which represents a channel or playlist,
            #   but media_data_obj itself is a media.Video object
            # media_data_obj's parent is a media.Folder object. Check its
            #   child objects, looking for a matching video
            # (video_obj is set to None, if no match is found)
            video_obj = media_data_obj.parent_obj.find_matching_video(
                app_obj,
                filename,
            )

            if not video_obj:
                video_obj = media_data_obj.parent_obj.find_matching_video(
                    app_obj,
                    name,
                )

        elif isinstance(media_data_obj, media.Video):

            # media_data_obj is a media.Video object
            video_obj = media_data_obj

        else:

            # media_data_obj is a media.Channel or media.Playlist object. Check
            #   its child objects, looking for a matching video
            # (video_obj is set to None, if no match is found)
            video_obj = media_data_obj.find_matching_video(app_obj, filename)
            if not video_obj:
                video_obj = media_data_obj.find_matching_video(app_obj, name)

        new_flag = False
        update_results_flag = False
        if not video_obj:

            # Special case: during the checking phase of a custom download,
            #   don't create a new media.Video object if the video has no
            #   available subtitles (if that's what the settings in the
            #   CustomDLManager specify)
            if (
                self.download_item_obj.operation_type == 'custom_sim' \
                or self.download_item_obj.operation_type == 'classic_sim'
            ) and dl_list_obj.custom_dl_obj \
            and dl_list_obj.custom_dl_obj.dl_by_video_flag \
            and dl_list_obj.custom_dl_obj.dl_precede_flag \
            and dl_list_obj.custom_dl_obj.dl_if_subs_flag \
            and dl_list_obj.custom_dl_obj.ignore_if_no_subs_flag \
            and (
                not subs_flag \
                or (
                    dl_list_obj.custom_dl_obj.dl_if_subs_list \
                    and not ttutils.match_subs(
                        dl_list_obj.custom_dl_obj,
                        list(json_dict['subtitles'].keys),
                    )
                )
            ):
                return

            # No matching media.Video object found, so create a new one
            new_flag = True
            update_results_flag = True

            if self.url_is_not_video_flag:

                video_obj = app_obj.convert_video_from_download(
                    self.download_item_obj.media_data_obj.parent_obj,
                    self.download_item_obj.options_manager_obj,
                    path,
                    filename,
                    extension,
                    # Don't sort parent container objects yet; wait for
                    #   mainwin.MainWin.results_list_update_row() to do it
                    True,
                )

            else:

                video_obj = app_obj.create_video_from_download(
                    self.download_item_obj,
                    path,
                    filename,
                    extension,
                    True,
                )

            # Update its IVs with the JSON information we extracted
            if filename is not None:
                video_obj.set_name(filename)

            if name is not None:
                video_obj.set_nickname(name)
            elif filename is not None:
                video_obj.set_nickname(filename)

            if vid is not None:
                video_obj.set_vid(vid)

            if upload_time is not None:
                video_obj.set_upload_time(upload_time)

            if duration is not None:
                video_obj.set_duration(duration)

            if source is not None:
                video_obj.set_source(source)

            if chapter_list:
                video_obj.extract_timestamps_from_chapters(
                    app_obj,
                    chapter_list,
                )

            if author is not None:
                video_obj.set_author(author)

            if descrip is not None:
                video_obj.set_video_descrip(
                    app_obj,
                    descrip,
                    app_obj.main_win_obj.descrip_line_max_len,
                )

            if was_live_flag:
                video_obj.set_was_live_flag(True)

            if comment_list \
            and options_obj.options_dict['store_comments_in_db']:
                video_obj.set_comments(comment_list)

            if app_obj.store_playlist_id_flag \
            and playlist_id is not None \
            and not isinstance(video_obj.parent_obj, media.Folder):
                video_obj.parent_obj.set_playlist_id(
                    playlist_id,
                    playlist_title,
                )

            if subs_flag:
                video_obj.extract_subs_list(json_dict['subtitles'])

            app_obj.extract_parent_name_from_metadata(
                video_obj,
                json_dict,
            )

            if isinstance(video_obj.parent_obj, media.Channel) \
            or isinstance(video_obj.parent_obj, media.Playlist):
                # 'Enhanced' websites only: set the channel/playlist RSS feed,
                #   if not already set
                video_obj.parent_obj.update_rss_from_json(json_dict)

                # If downloading from a channel/playlist, remember the video's
                #   index. (The server supplies an index even for a channel,
                #   and the user might want to convert a channel to a playlist)
                video_obj.set_index(playlist_index)

            # Now we can sort the parent containers
            video_obj.parent_obj.sort_children(app_obj)
            app_obj.fixed_all_folder.sort_children(app_obj)
            if video_obj.bookmark_flag:
                app_obj.fixed_bookmark_folder.sort_children(app_obj)
            if video_obj.fav_flag:
                app_obj.fixed_fav_folder.sort_children(app_obj)
            if video_obj.live_mode:
                app_obj.fixed_live_folder.sort_children(app_obj)
            if video_obj.missing_flag:
                app_obj.fixed_missing_folder.sort_children(app_obj)
            if video_obj.new_flag:
                app_obj.fixed_new_folder.sort_children(app_obj)
            if video_obj in app_obj.fixed_recent_folder.child_list:
                app_obj.fixed_recent_folder.sort_children(app_obj)
            if video_obj.waiting_flag:
                app_obj.fixed_waiting_folder.sort_children(app_obj)

        else:

            # This video will not be marked as a missing video
            if video_obj in self.missing_video_check_list:
                self.missing_video_check_list.remove(video_obj)

            # A media.Video object that already exists is not displayed in the
            #   Results list (unless it's a downloaded video that is being
            #   re-checked)
            if video_obj.file_name \
            and video_obj.name != app_obj.default_video_name \
            and not video_obj.dl_flag:

                # This video must not be displayed in the Results List, and
                #   counts towards the limit (if any) specified by
                #   mainapp.TartubeApp.operation_check_limit
                self.video_limit_count += 1

                if not isinstance(
                    self.download_item_obj.media_data_obj,
                    media.Video,
                ) \
                and not self.download_item_obj.ignore_limits_flag \
                and app_obj.operation_limit_flag \
                and app_obj.operation_check_limit \
                and self.video_limit_count >= app_obj.operation_check_limit:
                    # Limit reached. When we reach the end of this function,
                    #   stop checking videos in this channel/playlist
                    stop_flag = True

                # The call to DownloadManager.register_video() below doesn't
                #   take account of this situation, so make our own call
                self.download_manager_obj.register_video('other')

            else:

                # This video must be displayed in the Results List, and counts
                #   towards the limit (if any) specified by
                #   mainapp.TartubeApp.autostop_videos_value
                update_results_flag = True

            # If the 'Add videos' button was used, the path/filename/extension
            #   won't be set yet
            if not video_obj.file_name and full_path:
                video_obj.set_file(filename, extension)

            # Update any video object IVs that are not set
            if video_obj.name == app_obj.default_video_name \
            and filename is not None:
                video_obj.set_name(filename)

            if video_obj.nickname == app_obj.default_video_name:
                if name is not None:
                    video_obj.set_nickname(name)
                elif filename is not None:
                    video_obj.set_nickname(filename)

            if not video_obj.vid and vid is not None:
                video_obj.set_vid(vid)

            if not video_obj.upload_time and upload_time is not None:
               video_obj.set_upload_time(upload_time)

            if not video_obj.duration and duration is not None:
                video_obj.set_duration(duration)

            if not video_obj.source and source is not None:
                video_obj.set_source(source)

            if chapter_list:
                video_obj.extract_timestamps_from_chapters(
                    app_obj,
                    chapter_list,
                )

            if not video_obj.author and author is not None:
                video_obj.set_author(author)

            if not video_obj.descrip and descrip is not None:
                video_obj.set_video_descrip(
                    app_obj,
                    descrip,
                    app_obj.main_win_obj.descrip_line_max_len,
                )

            if was_live_flag:
                video_obj.set_was_live_flag(True)

            if not video_obj.comment_list \
            and comment_list \
            and options_obj.options_dict['store_comments_in_db']:
                video_obj.set_comments(comment_list)

            if app_obj.store_playlist_id_flag \
            and playlist_id is not None \
            and not isinstance(video_obj.parent_obj, media.Folder):
                video_obj.parent_obj.set_playlist_id(
                    playlist_id,
                    playlist_title,
                )

            if subs_flag:
                video_obj.extract_subs_list(json_dict['subtitles'])

            app_obj.extract_parent_name_from_metadata(
                video_obj,
                json_dict,
            )

            if isinstance(video_obj.parent_obj, media.Channel) \
            or isinstance(video_obj.parent_obj, media.Playlist):
                # 'Enhanced' websites only: set the channel/playlist RSS feed,
                #   if not already set
                video_obj.parent_obj.update_rss_from_json(json_dict)

                # If downloading from a channel/playlist, remember the video's
                #   index. (The server supplies an index even for a channel,
                #   and the user might want to convert a channel to a playlist)
                video_obj.set_index(playlist_index)

        # Deal with livestreams
        if video_obj.live_mode != 2 and live_flag:

            GObject.timeout_add(
                0,
                app_obj.mark_video_live,
                video_obj,
                2,                  # Livestream is broadcasting
                {},                 # No livestream data
                True,               # Don't update Video Index yet
                True,               # Don't update Video Catalogue yet
            )

        elif video_obj.live_mode != 0 and not live_flag:

            GObject.timeout_add(
                0,
                app_obj.mark_video_live,
                video_obj,
                0,                  # Livestream has finished
                {},                 # Reset any livestream data
                True,               # Don't update Video Index yet
                True,               # Don't update Video Catalogue yet
            )

        # Deal with the video description, JSON data and thumbnail, according
        #   to the settings in options.OptionsManager
        options_dict \
        = self.download_worker_obj.options_manager_obj.options_dict

        if descrip and options_dict['write_description']:

            descrip_path = os.path.abspath(
                os.path.join(path, filename + '.description'),
            )

            if not options_dict['sim_keep_description']:

                descrip_path = ttutils.convert_path_to_temp_dl_dir(
                    app_obj,
                    descrip_path,
                )

            # (Don't replace a file that already exists, and obviously don't
            #   do anything if the call returned None because of a filesystem
            #   error)
            if descrip_path is not None and not os.path.isfile(descrip_path):

                try:
                    fh = open(descrip_path, 'wb')
                    fh.write(descrip.encode('utf-8'))
                    fh.close()

                    if options_dict['move_description']:
                        ttutils.move_metadata_to_subdir(
                            app_obj,
                            video_obj,
                            '.description',
                        )

                except:
                    pass

        if options_dict['write_info']:

            json_path = os.path.abspath(
                os.path.join(path, filename + '.info.json'),
            )

            if not options_dict['sim_keep_info']:
                json_path = ttutils.convert_path_to_temp_dl_dir(
                    app_obj,
                    json_path,
                )

            if json_path is not None and not os.path.isfile(json_path):

                try:
                    with open(json_path, 'w') as outfile:
                        json.dump(json_dict, outfile, indent=4)

                    if options_dict['move_info']:
                        ttutils.move_metadata_to_subdir(
                            app_obj,
                            video_obj,
                            '.info.json',
                        )

                except:
                    pass

        # v2.1.101 - Annotations were removed by YouTube in 2019, so this
        #   feature is not available, and will not be available until the
        #   authors have some annotations to test
#        if options_dict['write_annotations']:
#
#            xml_path = os.path.abspath(
#                os.path.join(path, filename + '.annotations.xml'),
#            )
#
#            if not options_dict['sim_keep_annotations']:
#                xml_path \
#                = ttutils.convert_path_to_temp_dl_dir(app_obj, xml_path)

        if thumbnail and options_dict['write_thumbnail']:

            # Download the thumbnail, if we don't already have it
            # The thumbnail's URL is something like
            #   'https://i.ytimg.com/vi/abcdefgh/maxresdefault.jpg'
            # When saved to disc by youtube-dl, the file is given the same name
            #   as the video (but with a different extension)
            # Get the thumbnail's extension...
            remote_file, remote_ext = os.path.splitext(thumbnail)
            # Fix for Odysee videos, whose thumbnail extension is not specified
            #   in the .info.json file
            if remote_ext == '':
                remote_ext = '.webp'

            # ...and thus get the filename used by youtube-dl when storing the
            #   thumbnail locally
            thumb_path = video_obj.get_actual_path_by_ext(app_obj, remote_ext)

            if not options_dict['sim_keep_thumbnail']:
                thumb_path = ttutils.convert_path_to_temp_dl_dir(
                    app_obj,
                    thumb_path,
                )

            if thumb_path is not None and not os.path.isfile(thumb_path):

                # v2.0.013 The requests module fails if the connection drops
                # v1.2.006 Writing the file fails if the directory specified
                #   by thumb_path doesn't exist
                # Use 'try' so that neither problem is fatal
                try:
                    request_obj = requests.get(
                        thumbnail,
                        timeout = app_obj.request_get_timeout,
                    )

                    with open(thumb_path, 'wb') as outfile:
                        outfile.write(request_obj.content)

                except:
                    pass

            # Convert .webp thumbnails to .jpg, if required
            thumb_path = ttutils.find_thumbnail_webp_intact_or_broken(
                app_obj,
                video_obj,
            )
            if thumb_path is not None \
            and not app_obj.ffmpeg_fail_flag \
            and app_obj.ffmpeg_convert_webp_flag \
            and not app_obj.ffmpeg_manager_obj.convert_webp(thumb_path):

                app_obj.set_ffmpeg_fail_flag(True)
                GObject.timeout_add(
                    0,
                    app_obj.system_error,
                    305,
                    app_obj.ffmpeg_fail_msg,
                )

            # Move to the sub-directory, if required
            if options_dict['move_thumbnail']:

                ttutils.move_thumbnail_to_subdir(app_obj, video_obj)

        # Contact SponsorBlock server to fetch video slice data
        if app_obj.custom_sblock_mirror != '' \
        and app_obj.sblock_fetch_flag \
        and video_obj.vid != None \
        and (not video_obj.slice_list or app_obj.sblock_replace_flag):
            ttutils.fetch_slice_data(
                app_obj,
                video_obj,
                self.download_worker_obj.worker_id,
                True,       # Write to terminal/log, if allowed
            )

        # If a new media.Video object was created (or if a video whose name is
        #   unknown, now has a name), add a line to the Results List, as well
        #   as updating the Video Catalogue
        # The True argument passes on the download options 'move_description',
        #   etc, but not 'keep_description', etc
        if update_results_flag:

            GObject.timeout_add(
                0,
                app_obj.announce_video_download,
                self.download_item_obj,
                video_obj,
                # No call to ttutils.compile_mini_options_dict(), because this
                #   function deals with download options like
                #   'move_description' by itself
                {},
            )

        else:

            # Otherwise, just update the Video Catalogue
            GObject.timeout_add(
                0,
                app_obj.main_win_obj.video_catalogue_update_video,
                video_obj,
            )

        # For simulated downloads, self.do_download() has not displayed
        #   anything in the Output tab/terminal window/downloader log; so do
        #   that now (if required)
        if app_obj.ytdl_output_stdout_flag:

            app_obj.main_win_obj.output_tab_write_stdout(
                self.download_worker_obj.worker_id,
                '[' + video_obj.parent_obj.name + '] <' \
                + _('Simulated download of:') + ' \'' + filename + '\'>',
            )

        if app_obj.ytdl_write_stdout_flag:

            # v2.2.039 Partial fix for Git #106, #115 and #175, for which we
            #   get a Python error when print() receives unicode characters
            filename = filename.encode().decode(
                ttutils.get_encoding(),
                'replace',
            )

            try:

                print(
                    '[' + video_obj.parent_obj.name + '] <' \
                    + _('Simulated download of:') + ' \'' + filename + '\'>',
                )

            except:

                print(
                    '[' + video_obj.parent_obj.name + '] <' \
                    + _(
                    'Simulated download of video with unprintable characters',
                    ) + '>',
                )

        if app_obj.ytdl_log_stdout_flag:

            app_obj.write_downloader_log(
                '[' + video_obj.parent_obj.name + '] <' \
                + _('Simulated download of:') + ' \'' + filename + '\'>',
            )

        # If a new media.Video object was created (or if a video whose name is
        #   unknown, now has a name), register the simulated download with
        #   DownloadManager, so that download limits can be applied, if
        #   required
        if update_results_flag:
            self.download_manager_obj.register_video('sim')

        if video_obj:

            # If no errors/warnings were received during this operation,
            #   errors/warnings that already exist (from previous operations)
            #   can now be cleared
            if not video_obj.dbid in self.video_error_warning_dict:
                video_obj.reset_error_warning()

            # This confirmation clears a video marked as blocked
            video_obj.set_block_flag(False)

        # Stop checking videos in this channel/playlist, if a limit has been
        #   reached
        if stop_flag:
            self.stop()

        # This VideoDownloader can now stop, if required to do so after a video
        #   has been checked/downloaded
        elif self.stop_soon_flag:
            self.stop_now_flag = True


    def convert_video_to_container(self):

        """Called by self.check_dl_is_correct_type().

        Creates a new media.Channel or media.Playlist object to replace an
        existing media.Video object. The new object is given some of the
        properties of the old one.

        This function doesn't destroy the old object; DownloadManager.run()
        handles that.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5079 convert_video_to_container')

        app_obj = self.download_manager_obj.app_obj
        old_video_obj = self.download_item_obj.media_data_obj
        container_obj = old_video_obj.parent_obj

        # Some media.Folder objects cannot contain channels or playlists (for
        #   example, the 'Unsorted Videos' folder)
        # If that is the case, the new channel/playlist is created without a
        #   parent. Otherwise, it is created at the same location as the
        #   original media.Video object
        if container_obj.restrict_mode != 'open':
            container_obj = None

        # Decide on a name for the new channel/playlist, e.g. 'channel_1' or
        #   'playlist_4'. The name must not already be in use. The user can
        #   customise the name when they're ready
        name = ttutils.find_available_name(
            app_obj,
            # e.g. 'channel'
            app_obj.operation_convert_mode,
            # Allow 'channel_1', if available
            1,
        )

        # (Prevent any possibility of an infinite loop by giving up after some
        #   thousands of attempts)
        name = None
        new_container_obj = None

        for n in range (1, 9999):
            test_name = app_obj.operation_convert_mode + '_'  + str(n)
            if not app_obj.is_container(test_name):
                name = test_name
                break

        if name is not None:

            # Create the new channel/playlist. Very unlikely that the old
            #   media.Video object has its .dl_sim_flag set, but we'll use it
            #   nonetheless
            if app_obj.operation_convert_mode == 'channel':

                new_container_obj = app_obj.add_channel(
                    name,
                    container_obj,      # May be None
                    source = old_video_obj.source,
                    dl_sim_flag = old_video_obj.dl_sim_flag,
                )

            else:

                new_container_obj = app_obj.add_playlist(
                    name,
                    container_obj,      # May be None
                    source = old_video_obj.source,
                    dl_sim_flag = old_video_obj.dl_sim_flag,
                )

        if new_container_obj is None:

            # New channel/playlist could not be created (for some reason), so
            #   stop downloading from this URL
            self.stop()
            self.set_error(
                media_data_obj,
                '\'' + media_data_obj.name + '\' ' + _(
                    'This video has a URL that points to a channel or a' \
                    + ' playlist, not a video',
                ),
            )

        else:

            # Update IVs for the new channel/playlist object
            new_container_obj.set_options_obj(old_video_obj.options_obj)
            new_container_obj.set_source(old_video_obj.source)

            # Add the new channel/playlist to the Video Index (but don't
            #   select it)
            GObject.timeout_add(
                0,
                app_obj.main_win_obj.video_index_add_row,
                new_container_obj,
                True,
            )

            # Add the new channel/playlist to the download manager's list of
            #   things to download...
            return_list \
            = self.download_manager_obj.download_list_obj.create_item(
                new_container_obj,
                self.download_item_obj.scheduled_obj,
                self.download_item_obj.operation_type,
                False,                  # priority_flag
                self.download_item_obj.ignore_limits_flag,
            )

            # ...and add rows in the Progress List
            for new_download_item_obj in return_list:
                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.progress_list_add_row,
                    new_download_item_obj.item_id,
                    new_download_item_obj.media_data_obj,
                )

            # Stop this download job, allowing the replacement one to start
            self.stop()


    def create_child_process(self, cmd_list):

        """Called by self.do_download() immediately after the call to
        ttutils.generate_ytdl_system_cmd().

        Based on YoutubeDLDownloader._create_process().

        Executes the system command, creating a new child process which
        executes youtube-dl.

        Sets self.return_code in the event of an error.

        Args:

            cmd_list (list): Python list that contains the command to execute

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5200 create_child_process')

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
            #   as the code in self.do_download() will notice the child
            #   process didn't start, and set its own error message)
            self.set_return_code(self.ERROR)


    def extract_filename(self, input_data):

        """Called by self.confirm_sim_video() and .extract_stdout_data().

        Based on the extract_data() function in youtube-dl-gui's
        downloaders.py.

        Extracts various components of a filename.

        Args:

            input_data (str): Full path to a file which has been downloaded
                and saved to the filesystem

        Return values:

            Returns the path, filename and extension components of the full
                file path.

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5259 extract_filename')

        path, fullname = os.path.split(input_data.strip("\""))
        filename, extension = os.path.splitext(fullname)

        return path, filename, extension


    def extract_stdout_data(self, stdout):

        """Called by self.read_child_process().

        Based on the extract_data() function in youtube-dl-gui's
        downloaders.py.

        Extracts youtube-dl statistics from the child process.

        Args:

            stdout (str): String that contains a line from the child process
                STDOUT (i.e., a message from youtube-dl)

        Return values:

            Python dictionary in a standard format also used by the main window
            code. Dictionaries in this format are generally called
            'dl_stat_dict' (or some variation of it).

            The returned dictionary can be empty if there is no data to
            extract, otherwise it contains one or more of the following keys:

            'status'         : Contains the status of the download
            'path'           : Destination path
            'filename'       : The filename without the extension
            'extension'      : The file extension
            'percent'        : The percentage of the video being downloaded
            'eta'            : Estimated time for the completion of the
                                download
            'speed'          : Download speed
            'filesize'       : The size of the video file being downloaded
            'playlist_index' : The playlist index of the current video file
                                being downloaded
            'playlist_size'  : The number of videos in the playlist
            'dl_sim_flag'    : Flag set to True if we are simulating downloads
                                for this media data object, or False if we
                                actually downloading videos (set below)

            Other parts of the code may add the following keys:

            'finished_at'    : String describing the time at which the download
                                finished

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5309 extract_stdout_data')

        # Import the main application and media data object (for convenience)
        app_obj = self.download_manager_obj.app_obj
        media_data_obj = self.download_item_obj.media_data_obj

        # Initialise the dictionary with default key-value pairs for the main
        #   window to display, to be overwritten (if possible) with new key-
        #   value pairs as this function interprets the STDOUT message
        dl_stat_dict = {
            'playlist_index': self.video_num,
            'playlist_size': self.video_total,
            'dl_sim_flag': self.dl_sim_flag,
        }

        # If STDOUT has not been received by this function, then the main
        #   window can be passed just the default key-value pairs
        if not stdout:
            return dl_stat_dict

        # In some cases, we want to preserve the multiple successive whitespace
        #   characters in the STDOUT message, in order to extract filenames
        #   in their original form
        # In other cases, we just eliminate multiple successive whitespace
        #   characters
        stdout_with_spaces_list = stdout.split(' ')
        stdout_list = stdout.split()

        # The '[download] XXX has already been recorded in the archive'
        #   message does not cause a call to self.confirm_new_video(), etc,
        #   so we must handle it here
        # (Note that the first word might be '[download]', or '[Youtube]', etc)
        match = re.search(
            r'^\[\w+\]\s(.*)\shas already been recorded in (the )?' \
            + 'archive$',
            stdout,
        )
        if match:

            # In the Classic Mode tab, marking a (dummy) video as downloaded
            #   allows the 'Clear downloaded videos' button to work with it
            if self.dl_classic_flag:
                self.download_item_obj.media_data_obj.set_dl_flag(True)
                self.download_manager_obj.register_video('other')
                return dl_stat_dict

            # If checking missing videos, update our list of missing videos
            if self.missing_video_check_flag:
                self.confirm_archived_video(match.group(1))
                self.download_manager_obj.register_video('other')
                return dl_stat_dict

        # Likewise for the frame messages from youtube-dl direct downloads
        match = re.search(
            r'^frame.*size\=\s*([\S]+).*bitrate\=\s*([\S]+)',
            stdout,
        )
        if match:
            dl_stat_dict['filesize'] = match.groups()[0]
            dl_stat_dict['speed'] = match.groups()[1]
            return dl_stat_dict

        # Depending on settings, some filtered videos may count towards the
        #   operation limit. As we have to match several regexes, first check
        #   that the operation limit is enabled
        if app_obj.operation_limit_include_out_of_range_flag is True:

            for regex in self.filter_regex_list:
                match = re.search(regex, stdout)
                if match:
                    self.confirm_filtered_video()
                    return dl_stat_dict

        # Detect the start of a new channel/playlist/video download
        if stdout_list[1] == 'Extracting' and stdout_list[2] == 'URL:':
            self.video_download_started_flag = False

        # Extract the data. Because of the (small) possibility of a Python
        #   IndexError, we need to wrap the whole thing in a try..except
        try:

            stdout_list[0] = stdout_list[0].lstrip('\r')
            if stdout_list[0] == '[download]':

                dl_stat_dict['status'] = formats.ACTIVE_STAGE_DOWNLOAD
                self.video_download_started_flag = True

                if self.network_error_time is not None:
                    self.network_error_time = None

                # Get path, filename and extension
                if stdout_list[1] == 'Destination:':
                    path, filename, extension = self.extract_filename(
                        ' '.join(stdout_with_spaces_list[2:]),
                    )

                    dl_stat_dict['path'] = path
                    dl_stat_dict['filename'] = filename
                    dl_stat_dict['extension'] = extension

                    # v2.3.013 - the path to the subtitles file is being
                    #   mistaken for the path to the video file here. Only use
                    #   the destination if the path is a recognised video/audio
                    #   format (and if we don't already have it)
                    short_ext = extension[1:]
                    if self.temp_path is None \
                    and (
                        short_ext in formats.VIDEO_FORMAT_LIST \
                        or short_ext in formats.AUDIO_FORMAT_LIST
                    ):
                        self.set_temp_destination(path, filename, extension)

                # Get progress information
                if '%' in stdout_list[1]:
                    if stdout_list[1] != '100%':

                        # Old format, e.g.
                        #   [download]  27.0% of 7.55MiB at 73.63KiB/s ETA
                        #       01:16
                        if stdout_list[3] != '~':
                            dl_stat_dict['percent'] = stdout_list[1]
                            dl_stat_dict['eta'] = stdout_list[7]
                            dl_stat_dict['speed'] = stdout_list[5]
                            dl_stat_dict['filesize'] = stdout_list[3]
                        # New format (approx December 2022), e.g.
                        #   [download] 8.5% of ~ 19.87MiB at 2.35MiB/s ETA
                        #       00:07 (frag 8/94)
                        else:
                            dl_stat_dict['percent'] = stdout_list[1]
                            dl_stat_dict['eta'] = stdout_list[8]
                            dl_stat_dict['speed'] = stdout_list[6]
                            dl_stat_dict['filesize'] = stdout_list[4]

                    else:
                        dl_stat_dict['percent'] = '100%'
                        dl_stat_dict['eta'] = ''
                        dl_stat_dict['speed'] = ''
                        dl_stat_dict['filesize'] = stdout_list[3]

                        # If the most recently-received filename isn't one used
                        #   by FFmpeg, then this marks the end of a video
                        #   download
                        # (See the comments in self.__init__)
                        if len(stdout_list) > 4 \
                        and stdout_list[4] == 'in' \
                        and self.temp_filename is not None \
                        and not re.search(
                            r'^.*\.f\d{1,3}$',
                            self.temp_filename,
                        ):
                            self.confirm_new_video(
                                self.temp_path,
                                self.temp_filename,
                                self.temp_extension,
                            )

                            self.reset_temp_destination()

                # Get playlist information (when downloading a channel or a
                #   playlist, this line is received once per video)
                # youtube-dl 'Downloading video n of n'
                # yt-dlp: 'Downloading item n of n'
                if stdout_list[1] == 'Downloading' \
                and (stdout_list[2] == 'video' or stdout_list[2] == 'item') \
                and stdout_list[4] == 'of':
                    dl_stat_dict['playlist_index'] = int(stdout_list[3])
                    self.video_num = int(stdout_list[3])
                    dl_stat_dict['playlist_size'] = int(stdout_list[5])
                    self.video_total = int(stdout_list[5])

                    # If youtube-dl is about to download a channel or playlist
                    #   into a media.Video object, decide what to do to prevent
                    #   it
                    if not self.dl_classic_flag:
                        self.check_dl_is_correct_type()

                # Remove the 'and merged' part of the STDOUT message when using
                #   FFmpeg to merge the formats
                if stdout_list[-3] == 'downloaded' \
                and stdout_list[-1] == 'merged':
                    stdout_list = stdout_list[:-2]
                    stdout_with_spaces_list = stdout_with_spaces_list[:-2]

                    dl_stat_dict['percent'] = '100%'

                # Get file already downloaded status
#               if stdout_list[-1] == 'downloaded':
                if re.search(r' has already been downloaded$', stdout):

                    path, filename, extension = self.extract_filename(
                        ' '.join(stdout_with_spaces_list[1:-4]),
                    )

                    # v2.3.013 - same problem as above
                    short_ext = extension[1:]
                    if short_ext in formats.VIDEO_FORMAT_LIST \
                    or short_ext in formats.AUDIO_FORMAT_LIST:

                        dl_stat_dict['status'] \
                        = formats.COMPLETED_STAGE_ALREADY
                        dl_stat_dict['path'] = path
                        dl_stat_dict['filename'] = filename
                        dl_stat_dict['extension'] = extension
                        self.reset_temp_destination()

                        self.confirm_old_video(path, filename, extension)

                # Get filesize abort status
                if stdout_list[-1] == 'Aborting.':
                    dl_stat_dict['status'] = formats.ERROR_STAGE_ABORT

            elif stdout_list[0] == '[hlsnative]':

                # Get information from the native HLS extractor (see
                #   https://github.com/rg3/youtube-dl/blob/master/youtube_dl/
                #       downloader/hls.py#L54
                dl_stat_dict['status'] = formats.ACTIVE_STAGE_DOWNLOAD
                self.video_download_started_flag = True

                if len(stdout_list) == 7:
                    segment_no = float(stdout_list[6])
                    current_segment = float(stdout_list[4])

                    # Get the percentage
                    percent \
                    = '{0:.1f}%'.format(current_segment / segment_no * 100)
                    dl_stat_dict['percent'] = percent

            # youtube-dl uses [ffmpeg], yt-dlp uses [Merger] or [ExtractAudio]
            elif stdout_list[0] == '[ffmpeg]' \
            or stdout_list[0] == '[Merger]' \
            or stdout_list[0] == '[ExtractAudio]':

                # Using FFmpeg, not the the native HLS extractor
                # A successful video download is announced in one of several
                #   ways. Use the first announcement to update
                #   self.video_check_dict, and ignore subsequent announcements
                dl_stat_dict['status'] = formats.ACTIVE_STAGE_POST_PROCESS

                # Get the final file extension after the merging process has
                #   completed
                if stdout_list[1] == 'Merging':
                    path, filename, extension = self.extract_filename(
                        ' '.join(stdout_with_spaces_list[4:]),
                    )

                    dl_stat_dict['path'] = path
                    dl_stat_dict['filename'] = filename
                    dl_stat_dict['extension'] = extension
                    self.reset_temp_destination()

                    self.confirm_new_video(path, filename, extension, True)

                # Get the final file extension after simple FFmpeg post-
                #   processing (i.e. not after a file merge)
                elif stdout_list[1] == 'Destination:':
                    path, filename, extension = self.extract_filename(
                        ' '.join(stdout_with_spaces_list[2:]),
                    )

                    dl_stat_dict['path'] = path
                    dl_stat_dict['filename'] = filename
                    dl_stat_dict['extension'] = extension
                    self.reset_temp_destination()

                    self.confirm_new_video(path, filename, extension)

                # Get final file extension after the recoding process
                elif stdout_list[1] == 'Converting':
                    path, filename, extension = self.extract_filename(
                        ' '.join(stdout_with_spaces_list[8:]),
                    )

                    dl_stat_dict['path'] = path
                    dl_stat_dict['filename'] = filename
                    dl_stat_dict['extension'] = extension
                    self.reset_temp_destination()

                    self.confirm_new_video(path, filename, extension)

            elif stdout_list[0] == '[VideoRemuxer]':

                # Get final file extension after the remuxing process
                path, filename, extension = self.extract_filename(
                    ' '.join(stdout_with_spaces_list[8:]),
                )

                dl_stat_dict['path'] = path
                dl_stat_dict['filename'] = filename
                dl_stat_dict['extension'] = extension
                self.reset_temp_destination()

                self.confirm_remuxed_video(path, filename, extension)

            elif (
                isinstance(media_data_obj, media.Channel)
                and not media_data_obj.rss \
                and stdout_list[0] == '[youtube:channel]' \
            ) or (
                isinstance(media_data_obj, media.Playlist) \
                and not media_data_obj.rss \
                and stdout_list[0] == '[youtube:playlist]' \
                and stdout_list[2] == 'Downloading' \
                and stdout_list[3] == 'webpage'
            ):
                # YouTube only: set the channel/playlist RSS feed, if not
                #   already set, first removing the final colon that should be
                #   there
                # (This is the old method of setting the RSS; no longer
                #   necessary as of v2.3.602, but retained in case it is useful
                #   in the future)
                container_id = re.sub(r'\:*$', '', stdout_list[1])
                media_data_obj.update_rss_from_id(container_id)

            elif (
                not self.dl_sim_flag \
                and stdout_list[2] == 'Downloading' \
                and stdout_list[3] == 'webpage' \
                and re.search(r'^\[[^\]\:]+\]', stdout_list[0]) \
            ):
                # (The re.search() above excludes [youtube:channel] and
                #   [youtube:playlist], etc)
                self.probable_video_id = re.sub(r'\:*$', '', stdout_list[1])

            elif (
                stdout_list[0] == 'Deleting' \
                and stdout_list[1] == 'original' \
                and stdout_list[2] == 'file' \
                and self.stop_after_merge_flag \
            ):
                # (We were waiting for an FFmpeg to finish, before stopping the
                #   download)
                self.stop_now_flag = True
                self.stop_after_merge_flag = False
                return dl_stat_dict

            elif stdout_list[0][0] == '{':

                # JSON data, the result of a simulated download. Convert to a
                #   python dictionary
                if self.dl_sim_flag:

                    # (Try/except to check for invalid JSON)
                    try:
                        json_dict = json.loads(stdout)

                    except:
                        GObject.timeout_add(
                            0,
                            app_obj.system_error,
                            306,
                            'Invalid JSON data received from server',
                        )

                        return dl_stat_dict

                    if json_dict:

                        # For some Classic Mode custom downloads, Tartube
                        #   performs two consecutive download operations: one
                        #   simulated download to fetch URLs of individual
                        #   videos, and another to download each video
                        #   separately
                        # If we're on the first operation, the dummy
                        #   media.Video object's URL may represent an
                        #   individual video, or a channel or playlist
                        # In both cases, we simply make a list of each video
                        #   detected, along with its metadata, ready for the
                        #   second operation
                        if self.download_item_obj.operation_type \
                        == 'classic_sim':

                            # (If the URL can't be retrieved for any reason,
                            #   then just ignore this batch of JSON)
                            if 'webpage_url' in json_dict:
                                self.download_manager_obj.register_classic_url(
                                    self.download_item_obj.media_data_obj,
                                    json_dict,
                                )

                        # If youtube-dl is about to download a channel or
                        #   playlist into a media.Video object, decide what to
                        #   do to prevent that
                        # The called function returns a True/False value,
                        #   specifically to allow this code block to call
                        #   self.confirm_sim_video when required
                        # v1.3.063 At this point, self.video_num can be 0 for a
                        #   URL that's an individual video, but > 0 for a URL
                        #   that's actually a channel/playlist
                        elif not self.video_num \
                        or self.check_dl_is_correct_type():
                            self.confirm_sim_video(json_dict)

                        self.video_num += 1
                        dl_stat_dict['playlist_index'] = self.video_num
                        self.video_total += 1
                        dl_stat_dict['playlist_size'] = self.video_total

                        dl_stat_dict['status'] = formats.ACTIVE_STAGE_CHECKING

            elif stdout_list[0][0] != '[' or stdout_list[0] == '[debug]':

                # (Just ignore this output)
                return dl_stat_dict

            elif self.video_download_started_flag:

                # The download has already started
                dl_stat_dict['status'] = formats.ACTIVE_STAGE_POST_PROCESS

            else:

                # The download is about to start
                dl_stat_dict['status'] = formats.ACTIVE_STAGE_PRE_PROCESS

        except:

            # !!! DEBUG Git #395
            GObject.timeout_add(
                0,
                app_obj.system_error,
                319,
                'VideoDownloader.extract_stdout_data() index error. This is' \
                + ' an unresolved bug; please show the authors the URL that' \
                + ' caused it, and this text: ' + str(stdout),
                )

        return dl_stat_dict


    def extract_stdout_status(self, dl_stat_dict):

        """Called by self.read_child_process() immediately after a call to
        self.extract_stdout_data().

        Based on YoutubeDLDownloader._extract_info().

        If the job's status is formats.COMPLETED_STAGE_ALREADY or
        formats.ERROR_STAGE_ABORT, translate that into a new value for the
        return code, and then use that value to actually set self.return_code
        (which halts the download).

        Args:

            dl_stat_dict (dict): The Python dictionary returned by the call to
                self.extract_stdout_data(), in the standard form described by
                the comments for that function

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5714 extract_stdout_status')

        if 'status' in dl_stat_dict:
            if dl_stat_dict['status'] == formats.COMPLETED_STAGE_ALREADY:
                self.set_return_code(self.ALREADY)
                dl_stat_dict['status'] = None

            if dl_stat_dict['status'] == formats.ERROR_STAGE_ABORT:
                self.set_return_code(self.FILESIZE_ABORT)
                dl_stat_dict['status'] = None


    def is_blocked(self, stderr):

        """Called by self.register_error_warning().

        See if a STDERR message indicates a video that is censored, age-
        restricted or otherwise unavailable for download.

        Args:

            stderr (str): A message from the child process STDERR

        Return values:

            True if the video is blocked, False if not

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5744 is_blocked')

        # N.B. These strings also appear in self.is_ignorable()
        regex_list = [
            'Content Warning',
            'This video may be inappropriate for some users',
            'Sign in to confirm your age',
            'This video contains content from.*copyright grounds',
            'This video requires payment to watch',
            'The uploader has not made this video available',
        ]

        for regex in regex_list:

            if re.search(r'\s*(\S*)\:\s' + regex, stderr):
                return True

        # Not blocked
        return None


    def is_child_process_alive(self):

        """Called by self.do_download() and self.stop().

        Based on YoutubeDLDownloader._proc_is_alive().

        Called continuously during the self.do_download() loop to check whether
        the child process has finished or not.

        Return values:

            True if the child process is alive, otherwise returns False

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5781 is_child_process_alive')

        if self.child_process is None:
            return False

        return self.child_process.poll() is None


    def is_debug(self, stderr):

        """Called by self.do_download().

        Based on YoutubeDLDownloader._is_warning().

        After the child process has terminated with an error of some kind,
        checks the STERR message to see if it's an error or just a debug
        message (generated then youtube-dl verbose output is turned on).

        Args:

            stderr (str): A message from the child process STDERR

        Return values:

            True if the STDERR message is a youtube-dl debug message, False if
                it's an error

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5811 is_debug')

        return stderr.split(' ')[0] == '[debug]'


    def is_ignorable(self, stderr):

        """Called by self.register_error_warning().

        Before testing a STDERR message, see if it's one of the frequent
        messages which the user has opted to ignore (if any).

        Args:

            stderr (str): A message from the child process STDERR

        Return values:

            True if the STDERR message is ignorable, False if it should be
                tested further

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 5835 is_ignorable')

        app_obj = self.download_manager_obj.app_obj
        media_data_obj = self.download_item_obj.media_data_obj

        if (
            app_obj.ignore_http_404_error_flag \
            and (
                re.search(
                    r'unable to download video data\: HTTP Error 404',
                    stderr,
                ) or re.search(
                    r'Unable to extract video data',
                    stderr,
                )
            )
        ) or (
            app_obj.ignore_data_block_error_flag \
            and re.search(r'Did not get any data blocks', stderr)
        ) or (
            app_obj.ignore_merge_warning_flag \
            and re.search(
                r'Requested formats are incompatible for merge',
                stderr,
            )
        ) or (
            app_obj.ignore_missing_format_error_flag \
            and re.search(
                r'No video formats found; please report this issue',
                stderr,
            )
        ) or (
            app_obj.ignore_no_annotations_flag \
            and re.search(
                r'There are no annotations to write',
                stderr,
            )
        ) or (
            app_obj.ignore_no_subtitles_flag \
            and re.search(
                r'video doesn\'t have subtitles',
                stderr,
            )
        ) or (
            app_obj.ignore_page_given_flag \
            and re.search(
                r'A channel.user page was given',
                stderr,
            )
        ) or (
            app_obj.ignore_no_descrip_flag \
            and re.search(
                r'There.s no playlist description to write',
                stderr,
            )
        ) or (
            app_obj.ignore_thumb_404_flag \
            and re.search(
                r'Unable to download video thumbnail.*HTTP Error 404',
                stderr,
            )
        ) or (
            app_obj.ignore_twitch_not_live_flag \
            and re.search(
                r'twitch.*The channel is not currently live',
                stderr,
            )
        ) or (
            app_obj.ignore_yt_age_restrict_flag \
            and (
                re.search(
                    r'Content Warning',
                    stderr,
                ) or re.search(
                    r'This video may be inappropriate for some users',
                    stderr,
                ) or re.search(
                    r'Sign in to confirm your age',
                    stderr,
                )
            )
        ) or (
            app_obj.ignore_yt_copyright_flag \
            and (
                re.search(
                    r'This video contains content from.*copyright grounds',
                    stderr,
                ) or re.search(
                    r'Sorry about that\.',
                    stderr,
                )
            )
        ) or (
            app_obj.ignore_yt_payment_flag \
            and re.search(
                r'This video requires payment to watch',
                stderr,
            )

        ) or (
            app_obj.ignore_yt_uploader_deleted_flag \
            and (
                re.search(
                    r'The uploader has not made this video available',
                    stderr,
                )
            )
        ):
            # This message is ignorable
            return True

        # Check the custom list of messages
        for item in app_obj.ignore_custom_msg_list:
            if (
                (not app_obj.ignore_custom_regex_flag) \
                and stderr.find(item) > -1
            ) or (
                app_obj.ignore_custom_regex_flag and re.search(item, stderr)
            ):
                # This message is ignorable
                return True

        # This message is not ignorable
        return False


    def is_network_error(self, stderr):

        """Called by self.read_child_process().

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
            ttutils.debug_time('dld 5982 is_network_error')

        if re.search(r'[Uu]nable to download video data', stderr) \
        or re.search(r'[Uu]nable to download webpage', stderr) \
        or re.search(r'[Nn]ame or service not known', stderr) \
        or re.search(r'urlopen error', stderr) \
        or re.search(r'Got server HTTP error', stderr):
            return True
        else:
            return False


    def is_warning(self, stderr):

        """Called by self.do_download().

        Based on YoutubeDLDownloader._is_warning().

        After the child process has terminated with an error of some kind,
        checks the STERR message to see if it's an error or just a warning.

        Args:

            stderr (str): A message from the child process STDERR

        Return values:

            True if the STDERR message is a warning, False if it's an error

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6014 is_warning')

        return stderr.split(':')[0] == 'WARNING'


    def last_data_callback(self):

        """Called by self.read_child_process().

        Based on YoutubeDLDownloader._last_data_hook().

        After the child process has finished, creates a new Python dictionary
        in the standard form described by self.extract_stdout_data().

        Sets key-value pairs in the dictonary, then passes it to the parent
        downloads.DownloadWorker object, confirming the result of the child
        process.

        The new key-value pairs are used to update the main window.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6036 last_data_callback')

        dl_stat_dict = {}

        if self.return_code == self.OK:
            dl_stat_dict['status'] = formats.COMPLETED_STAGE_FINISHED
        elif self.return_code == self.ERROR:
            dl_stat_dict['status'] = formats.MAIN_STAGE_ERROR
            dl_stat_dict['eta'] = ''
            dl_stat_dict['speed'] = ''
        elif self.return_code == self.WARNING:
            dl_stat_dict['status'] = formats.COMPLETED_STAGE_WARNING
            dl_stat_dict['eta'] = ''
            dl_stat_dict['speed'] = ''
        elif self.return_code == self.STOPPED:
            dl_stat_dict['status'] = formats.ERROR_STAGE_STOPPED
            dl_stat_dict['eta'] = ''
            dl_stat_dict['speed'] = ''
        elif self.return_code == self.ALREADY:
            dl_stat_dict['status'] = formats.COMPLETED_STAGE_ALREADY
        elif self.return_code == self.STALLED:
            dl_stat_dict['status'] = formats.MAIN_STAGE_STALLED
        else:
            dl_stat_dict['status'] = formats.ERROR_STAGE_ABORT

        # Use some empty values in dl_stat_dict so that the Progress tab
        #   doesn't show arbitrary data from the last file downloaded
        # Exception: in Classic Mode, don't do that for self.ALREADY, otherwise
        #   the filename will never be visible
        if not self.dl_classic_flag or self.return_code != self.ALREADY:
            dl_stat_dict['filename'] = ''
            dl_stat_dict['extension'] = ''
        dl_stat_dict['percent'] = ''
        dl_stat_dict['eta'] = ''
        dl_stat_dict['speed'] = ''
        dl_stat_dict['filesize'] = ''

        # The True argument shows that this function is the caller
        self.download_worker_obj.data_callback(dl_stat_dict, True)


    def match_vid_or_url(self, media_data_obj, vid, url=None):

        """Called by self.register_error_warning().

        Tests whether a media.Video object has a specified video ID, or a the
        URL expected from that video ID.

        Args:

            media_data_obj (media.Video): The video to test

            vid (str): The video ID

            url (str or None): A URL expected from that video ID, or None if
                we don't know how to convert the video ID into a URL

        Return values:

            True if the video matches the video ID or URL, False otherwise

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6100 match_vid_or_url')

        if (
            media_data_obj.vid is not None \
            and media_data_obj.vid == vid
        ) or (
            media_data_obj.source is not None \
            and media_data_obj.source == url
        ):
            return True
        else:
            return False


    def process_error_warning(self, vid):

        """Called by downloads.DownloadWorker.run_video_downloader() or by any
        other code.

        When a youtube-dl error/warning message is received with an
        identifiable video ID, the corresponding media.Video object might not
        yet exist.

        The error/warning is stored temporarily in self.video_msg_buffer_dict()
        until it can be passed on to the media.Video. (If the media.Video still
        does not exist, pass it on to the parent channel/playlist instead.)

        Args:

            vid (str): The video ID, a key in self.video_msg_buffer_dict

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6134 process_error_warning')

        if not vid in self.video_msg_buffer_dict:

            GObject.timeout_add(
                0,
                app_obj.system_error,
                307,
                'Missing VID in video error/warning buffer',
            )

            return

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Search for a matching media.Video
        video_obj = None

        if isinstance(self.download_item_obj.media_data_obj, media.Video):

            # This should not happen, but handle it anyway
            video_obj = self.download_item_obj.media_data_obj

        else:

            for child_obj in self.download_item_obj.media_data_obj.child_list:

                if isinstance(child_obj, media.Video) \
                and child_obj.vid is not None \
                and child_obj.vid == vid:

                    video_obj = child_obj
                    break

        # mini_list is in the form [ msg_type, data ]
        for mini_list in self.video_msg_buffer_dict[vid]:

            if video_obj is None:

                # No matching media.Video found; assign the error/warning to
                #   the parent channel/playlist instead
                if mini_list[0] == 'warning':
                    self.set_return_code(self.WARNING)
                    self.download_item_obj.media_data_obj.set_warning(
                        mini_list[1],
                    )

                else:
                    self.set_return_code(self.ERROR)
                    self.download_item_obj.media_data_obj.set_error(
                        mini_list[1],
                    )

            else:

                if mini_list[0] == 'warning':
                    self.set_warning(video_obj, mini_list[1])
                else:
                    self.set_error(video_obj, mini_list[1])

                # Code in downloads.DownloadWorker.run_video_downloader()
                #   calls mainwin.MainWin.errors_list_add_operation_msg() for
                #   the main downloads.DownloadItem and its errors/warnings;
                #   but for a child video, we have to call it directly
                # The True argument means 'display the last error/warning only'
                #   in case the same video generates several errors
                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.errors_list_add_operation_msg,
                    video_obj,
                    True,
                )

                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.video_catalogue_update_video,
                    video_obj,
                )


    def read_child_process(self):

        """Called by self.do_download().

        Reads from the child process STDOUT and STDERR, in the correct order.

        Return values:

            True if either STDOUT or STDERR were read. None if both queues were
                empty, or if STDERR was read and a network error was detected

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6227 read_child_process')

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
                308,
                'Malformed STDOUT or STDERR data',
            )

        # STDOUT or STDERR has been read
        data = mini_list[2].rstrip()
        # On MS Windows we use cp1252, so that Tartube can communicate with the
        #   Windows console
        data = data.decode(ttutils.get_encoding(), 'replace')

        # youtube-dl livestream downloads are normally handles by
        #   downloads.StreamDownloader, but in certain circumstances this
        #   VideoDownloader might be asked to handle them
        # When youtube-dl is downloading the livestream directly (i.e. without
        #   .m3u), it produces a lot of output in STDERR, most of which can be
        #   ignored, but some of which should be converted to STDOUT
        if mini_list[1] == 'stderr':
            mod_data = ttutils.stream_output_is_ignorable(data)
            if mod_data is None:
                # Ignore whole line
                self.queue.task_done()

                return True
            elif mod_data != data:
                # Ignore the unmatched portion of the line, and convert STDERR
                #   to STDOUT (so self.extract_stdout_data() can process it as
                #   normal)
                data = mod_data
                mini_list[1] = 'stdout'

        # STDOUT
        if mini_list[1] == 'stdout':

            # Look out for network errors that indicate a stalled download
            # (I'm not sure why this message does not appear in STDERR;
            #   self.is_network_error() checks for the same pattern)
            if app_obj.operation_auto_restart_flag \
            and self.network_error_time is None \
            and re.search('Got server HTTP error', data):

                self.network_error_time = time.time()

            else:

                # Convert download statistics into a python dictionary in a
                #   standard format, specified in the comments for
                #   self.extract_stdout_data()
                dl_stat_dict = self.extract_stdout_data(data)
                # If the job's status is formats.COMPLETED_STAGE_ALREADY or
                #   formats.ERROR_STAGE_ABORT, set our self.return_code IV
                self.extract_stdout_status(dl_stat_dict)
                # Pass the dictionary on to self.download_worker_obj so the
                #   main window can be updated
                self.download_worker_obj.data_callback(dl_stat_dict)

            # Show output in the Output tab (if required). For simulated
            #   downloads, a message is displayed by self.confirm_sim_video()
            #   instead
            if app_obj.ytdl_output_stdout_flag \
            and (
                not app_obj.ytdl_output_ignore_progress_flag \
                or not re.search(
                    r'^\[download\]\s+[0-9\.]+\%\sof\s.*\sat\s.*\sETA',
                    data,
                )
            ) and (
                not app_obj.ytdl_output_ignore_json_flag \
                or data[:1] != '{'
            ):
                app_obj.main_win_obj.output_tab_write_stdout(
                    self.download_worker_obj.worker_id,
                    data,
                )

            # Show output in the terminal (if required). For simulated
            #   downloads, a message is displayed by
            #   self.confirm_sim_video() instead
            if app_obj.ytdl_write_stdout_flag \
            and (
                not app_obj.ytdl_write_ignore_progress_flag \
                or not re.search(
                    r'^\[download\]\s+[0-9\.]+\%\sof\s.*\sat\s.*\sETA',
                    data,
                )
            ) and (
                not app_obj.ytdl_write_ignore_json_flag \
                or data[:1] != '{'
            ):
                # Git #175, Japanese text may produce a codec error here,
                #   despite the .decode() call above
                try:
                    print(
                        data.encode(ttutils.get_encoding(), 'replace'),
                    )
                except:
                    print('STDOUT text with unprintable characters')

            # Write output to the download log (if required). For simulated
            #   downloads, a message is displayed by
            #   self.confirm_sim_video() instead
            if app_obj.ytdl_log_stdout_flag \
            and (
                not app_obj.ytdl_log_ignore_progress_flag \
                or not re.search(
                    r'^\[download\]\s+[0-9\.]+\%\sof\s.*\sat\s.*\sETA',
                    data,
                )
            ) and (
                not app_obj.ytdl_log_ignore_json_flag \
                or data[:1] != '{'
            ):
                app_obj.write_downloader_log(data)

        # STDERR (ignoring any empty error messages)
        elif data != '':

            # Look out for network errors that indicate a stalled download
            if app_obj.operation_auto_restart_flag \
            and self.network_error_time is None \
            and self.is_network_error(data):

                self.network_error_time = time.time()

            else:

                # Check for recognised errors/warnings, and update the
                #   appropriate media data object (immediately, if possible, or
                #   later otherwise)
                self.register_error_warning(data)

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

            # For Tartube's MS Windows portable version, when the whole
            #   installation folder is moved to a new location in the
            #   filesystem, youtube-dl must be uninstalled, then reinstalled
            if re.search('Fatal error in launcher: U', data) \
            and app_obj.ytdl_output_stderr_flag:

                app_obj.main_win_obj.output_tab_write_stderr(
                    self.download_worker_obj.worker_id,
                    self.app_obj.get_downloader() + ': ' \
                    + _('Please reinstall/update your downloader'),
                )

        # Either (or both) of STDOUT and STDERR were non-empty
        self.queue.task_done()
        return True


    def register_error_warning(self, data):

        """Called by self.read_child_process()

        When youtube-dl produces an error or warning (in its STDERR), pass that
        error/warning on to the appropriate media data object: the video
        responsible, if possible, or the parent channel/playlist if not.

        Args:

            data (str): The error/warning message from the child process STDERR

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6418 register_error_warning')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Try to identify the video ID that produced the error/warning. As of
        #   v2.3.453, some error/warning messages contain the video ID, others
        #   do not
        msg_type = None
        vid = None
        site_name = None

        if self.is_warning(data):

            self.set_return_code(self.WARNING)
            msg_type = 'warning'

            # e.g. WARNING: [youtube] abcdefgh: here are no annotations
            match = re.search(
                r'^WARNING\:\s*\[([^\]]+)\]\s*(\S+)\s*\:',
                data,
            )

            if match:
                site_name = match.groups()[0]
                vid = match.groups()[1]

        elif not self.is_debug(data):

            self.set_return_code(self.ERROR)
            msg_type = 'error'

            # e.g. ERROR: [youtube] abcdefgh: Sign in to confirm your age
            match = re.search(
                r'^ERROR\:\s*\[([^\]]+)\]\s*(\S+)\s*\:',
                data,
            )

            if match:
                site_name = match.groups()[0]
                vid = match.groups()[1]

        if not msg_type:
            # Not an error/warning
            return

        # If the error/warning marks the video as blocked, we can add it to
        #   the database (to alert the user about its existence)
        new_obj = None
        if app_obj.add_blocked_videos_flag \
        and vid is not None \
        and self.is_blocked(data):

            # Check this video is not already in the parent channel/playlist/
            #   folder
            media_data_obj = self.download_item_obj.media_data_obj
            url = ttutils.convert_enhanced_template_from_json(
                'convert_video_list',
                site_name,
                { 'video_id': vid },
            )

            if isinstance(media_data_obj, media.Video):

                if self.match_vid_or_url(media_data_obj, vid, url):
                    media_data_obj.set_block_flag(True)

            else:

                match_flag = False
                for child_obj in media_data_obj.child_list:

                    if self.match_vid_or_url(child_obj, vid, url):
                        match_flag = True
                        break

                if not match_flag:

                    # Video is not in the database, so add it
                    new_obj = app_obj.add_video(media_data_obj, url)
                    if new_obj:
                        new_obj.set_block_flag(True)
                        new_obj.set_vid(vid)

        # For some reason, YouTube messages giving the (approximate) start time
        #   of a livestream are written to STDERR
        # If the video's ID is recognised, we can update the media.Video
        #   object. However, we won't add a new video to the database;
        #   JSONFetcher can do that
        if new_obj is None \
        and app_obj.enable_livestreams_flag \
        and vid is not None:

            live_data_dict = ttutils.extract_livestream_data(data)
            if live_data_dict:

                # Check this video is not already in the parent channel/
                #   playlist/folder
                media_data_obj = self.download_item_obj.media_data_obj
                url = ttutils.convert_enhanced_template_from_json(
                    'convert_video_list',
                    site_name,
                    { 'video_id': vid },
                )

                if isinstance(media_data_obj, media.Video):

                    if self.match_vid_or_url(media_data_obj, vid, url):
                        GObject.timeout_add(
                            0,
                            app_obj.mark_video_live,
                            media_data_obj,
                            1,
                            live_data_dict,
                        )

                        # (We don't want mainwin.NewbieDialogue to appear in
                        #   this situation)
                        self.download_manager_obj.register_video('other')

                else:

                    for child_obj in media_data_obj.child_list:

                        if self.match_vid_or_url(child_obj, vid, url):
                            GObject.timeout_add(
                                0,
                                app_obj.mark_video_live,
                                child_obj,
                                1,
                                live_data_dict,
                            )

                            self.download_manager_obj.register_video('other')

                            break

                # Not a true error/warning, so don't mark it as one in the code
                #   below
                return

        # Assign the error/warning to a media data object
        if not self.is_ignorable(data):

            # If the error/warning is anonymous (does not contain the video
            #   ID), then we can use the most probable video ID
            if vid is None \
            and app_obj.auto_assign_errors_warnings_flag \
            and self.probable_video_id is not None:
                vid = self.probable_video_id

            # Decide which media data object should have this error/warning
            #   assigned to it
            if self.dl_classic_flag:

                # During Classic Mode downloads, no point trying to assign
                #   errors/warnings to dummy media.Video objects in a channel/
                #   playlist
                if msg_type == 'warning':
                    self.set_warning(
                        self.download_item_obj.media_data_obj,
                        data,
                    )
                else:
                    self.set_error(
                        self.download_item_obj.media_data_obj,
                        data,
                    )

            elif new_obj:

                # We created a new media.Video object just a moment ago, so
                #   assign the error/warning to it directly
                if msg_type == 'warning':
                    self.set_warning(new_obj, data)
                else:
                    self.set_error(new_obj, data)

                # Code in downloads.DownloadWorker.run_video_downloader()
                #   calls mainwin.MainWin.errors_list_add_operation_msg() for
                #   the main downloads.DownloadItem and its errors/warnings;
                #   but for a child video, we have to call it directly
                # The True argument means 'display the last error/warning only'
                #   in case the same video generates several errors
                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.errors_list_add_operation_msg,
                    new_obj,
                    True,
                )

                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.video_catalogue_update_video,
                    new_obj,
                )

            elif isinstance(
                self.download_item_obj.media_data_obj,
                media.Video,
            ):
                # We are downloading a single video, so we don't need the video
                #   ID (in which case, the error/warning can be assigned to it
                #   directly)
                if msg_type == 'warning':
                    self.set_warning(
                        self.download_item_obj.media_data_obj,
                        data,
                    )
                else:
                    self.set_error(
                        self.download_item_obj.media_data_obj,
                        data,
                    )

                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.video_catalogue_update_video,
                    self.download_item_obj.media_data_obj,
                )

            elif vid is None:

                # We are downloading a channel/playlist and the video ID is not
                #   known, so assign the error/warning to the channel/playlist
                if msg_type == 'warning':
                    self.set_warning(
                        self.download_item_obj.media_data_obj,
                        data,
                    )
                else:
                    self.set_error(
                        self.download_item_obj.media_data_obj,
                        data,
                    )

            else:

                # The corresponding media.Video object might not exist yet.
                #   Temporarily store the error/warning in a buffer, so that
                #   the parent downloads.DownloadWorker can retrieve it
                if vid in self.video_msg_buffer_dict:
                    self.video_msg_buffer_dict[vid].append( [msg_type, data] )
                else:
                    self.video_msg_buffer_dict[vid] = [ [msg_type, data] ]


    def set_error(self, media_data_obj, msg):

        """Wrapper for media.Video.set_error().

        Args:

            media_data_obj (media.Video, media.Channel or media.Playlist):
                The media data object to update. Only videos are updated by
                this function

            msg (str): The error message for this video

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6678 set_error')

        if isinstance(media_data_obj, media.Video):

            if not media_data_obj.dbid in self.video_error_warning_dict:

                # The new error is the first error/warning generated during
                #   this operation; remove any errors/warnings from previous
                #   operations
                media_data_obj.reset_error_warning()
                self.video_error_warning_dict[media_data_obj.dbid] = True

            # Set the new error
            media_data_obj.set_error(msg)


    def set_warning(self, media_data_obj, msg):

        """Wrapper for media.Video.set_warning().

        Args:

            media_data_obj (media.Video, media.Channel or media.Playlist):
                The media data object to update. Only videos are updated by
                this function

            msg (str): The warning message for this video

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6709 set_warning')

        if isinstance(media_data_obj, media.Video):

            if not media_data_obj.dbid in self.video_error_warning_dict:

                # The new warning is the first error/warning generated during
                #   this operation; remove any errors/warnings from previous
                #   operations
                media_data_obj.reset_error_warning()
                self.video_error_warning_dict[media_data_obj.dbid] = True

            # Set the new warning
            media_data_obj.set_warning(msg)


    def set_return_code(self, code):

        """Called by self.do_download(), .create_child_process(),
        .extract_stdout_status() and .stop().

        Based on YoutubeDLDownloader._set_returncode().

        After the child process has terminated with an error of some kind,
        sets a new value for self.return_code, but only if the new return code
        is higher in the hierarchy of return codes than the current value.

        Args:

            code (int): A return code in the range 0-5

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6743 set_return_code')

        # (The code -1, STALLED, overrules everything else)
        if code == -1 or code >= self.return_code:
            self.return_code = code


    def set_temp_destination(self, path, filename, extension):

        """Called by self.extract_stdout_data()."""

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6755 set_temp_destination')

        self.temp_path = path
        self.temp_filename = filename
        self.temp_extension = extension


    def reset_temp_destination(self):

        """Called by self.extract_stdout_data()."""

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6767 reset_temp_destination')

        self.temp_path = None
        self.temp_filename = None
        self.temp_extension = None


    def stop(self):

        """Called by DownloadWorker.close() and also by
        mainwin.MainWin.on_progress_list_stop_now().

        Terminates the child process and sets this object's return code to
        self.STOPPED.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6784 stop')

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

        Sets the flag that causes this VideoDownloader to stop after the
        current video.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 6814 stop_soon')

        self.stop_soon_flag = True
