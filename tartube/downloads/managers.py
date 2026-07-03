#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from .queue import DownloadItem
from .utils import CustomDLManager, PipeReader
from .workers.video import VideoDownloader
from .workers.clip import ClipDownloader
from .workers.stream import StreamDownloader
from .workers.json_fetcher import JSONFetcher, MiniJSONFetcher

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
class DownloadManager(threading.Thread):

    """Called by mainapp.TartubeApp.download_manager_continue().

    Based on the DownloadManager class in youtube-dl-gui.

    Python class to manage a download operation.

    Creates one or more downloads.DownloadWorker objects, each of which handles
    a single download.

    This object runs on a loop, looking for available workers and, when one is
    found, assigning them something to download. The worker completes that
    download and then waits for another assignment.

    Args:

        app_obj: The mainapp.TartubeApp object

        operation_type (str): 'sim' if channels/playlists should just be
            checked for new videos, without downloading anything. 'real' if
            videos should be downloaded (or not) depending on each media data
            object's .dl_sim_flag IV

            'custom_real' is like 'real', but with additional options applied
            (specified by a downloads.CustomDLManager object). A 'custom_real'
            operation is sometimes preceded by a 'custom_sim' operation (which
            is the same as a 'sim' operation, except that it is always followed
            by a 'custom_real' operation)

            For downloads launched from the Classic Mode tab, 'classic_real'
            for an ordinary download, or 'classic_custom' for a custom
            download. A 'classic_custom' operation is always preceded by a
            'classic_sim' operation (which is the same as a 'sim' operation,
            except that it is always followed by a 'classic_custom' operation)

        download_list_obj (downloads.DownloadManager): An ordered list of
            media data objects to download, each one represented by a
            downloads.DownloadItem object

        custom_dl_obj (downloads.CustomDLManager or None): The custom download
            manager that applies to this download operation. Only specified
            when 'operation_type' is 'custom_sim', 'custom_real', 'classic_sim'
            or 'classic_real'

            For 'custom_real' and 'classic_real', not specified if
            mainapp.TartubeApp.temp_stamp_buffer_dict or
            .temp_slice_buffer_dict are specified (because those values take
            priority)

    """


    # Standard class methods


    def __init__(self, app_obj, operation_type, download_list_obj, \
    custom_dl_obj):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 139 __init__')

        super(DownloadManager, self).__init__()

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # Each instance of this object, which represents a single download
        #   operation, creates its own options.OptionsParser object. That
        #   object convert the download options stored in
        #   downloads.DownloadWorker.options_list into a list of youtube-dl
        #   command line options
        self.options_parser_obj = None
        # An ordered list of media data objects to download, each one
        #   represented by a downloads.DownloadItem object
        self.download_list_obj = download_list_obj
        # The custom download manager (downloads.CustomDLManager) that applies
        #   to this download operation. Only specified when 'operation_type' is
        #   'custom_sim', 'custom_real', 'classic_sim' or 'classic_real'
        # For 'custom_real' and 'classic_real', not specified if
        #   mainapp.TartubeApp.temp_stamp_buffer_dict or
        #   .temp_slice_buffer_dict are specified (because those values take
        #   priority)
        self.custom_dl_obj = custom_dl_obj
        # List of downloads.DownloadWorker objects, each one handling one of
        #   several simultaneous downloads
        self.worker_list = []


        # IV list - other
        # ---------------
        # 'sim' if channels/playlists should just be checked for new videos,
        #   without downloading anything. 'real' if videos should be downloaded
        #   (or not) depending on each media data object's .dl_sim_flag IV
        # 'custom_real' is like 'real', but with additional options applied
        #   (specified by a downloads.CustomDLManager object). A 'custom_real'
        #   operation is sometimes preceded by a 'custom_sim' operation (which
        #   is the same as a 'sim' operation, except that it is always followed
        #   by a 'custom_real' operation)
        # For downloads launched from the Classic Mode tab, 'classic_real' for
        #   an ordinary download, or 'classic_custom' for a custom download. A
        #   'classic_custom' operation is always preceded by a 'classic_sim'
        #   operation (which is the same as a 'sim' operation, except that it
        #   is always followed by a 'classic_custom' operation)
        # This is the default value for the download operation, when it starts.
        #   If the user wants to add new download.DownloadItem objects during
        #   an operation, the code can call
        #   downloads.DownloadList.create_item() with a non-default value of
        #   operation_type
        self.operation_type = operation_type
        # Shortcut flag to test the operation type; True for 'classic_sim',
        #   'classic_real' and 'classic_custom'; False for all other values
        self.operation_classic_flag = False         # (Set below)

        # The time at which the download operation began (in seconds since
        #   epoch)
        self.start_time = int(time.time())
        # The time at which the download operation completed (in seconds since
        #   epoch)
        self.stop_time = None
        # The time (in seconds) between iterations of the loop in self.run()
        self.sleep_time = 0.25

        # Flag set to False if self.stop_download_operation() is called
        # The False value halts the main loop in self.run()
        self.running_flag = True
        # Flag set to True if the operation has been stopped manually by the
        #   user (via a call to self.stop_download_operation() or
        #   .stop_download_operation_soon()
        self.manual_stop_flag = False

        # Number of download jobs started (number of downloads.DownloadItem
        #   objects which have been allocated to a worker)
        self.job_count = 0
        # The current downloads.DownloadItem being handled by self.run()
        #   (stored in this IV so that anything can update the main window's
        #   progress bar, at any time, by calling self.nudge_progress_bar() )
        self.current_item_obj = None

        # On-going counts of how many videos have been downloaded (real and
        #   simulated, and including videos from which one or more clips have
        #   been extracted), how many clips have been extracted, how many video
        #   slices have been removed, and how much disc space has been consumed
        #   (in bytes), so that the operation can be auto-stopped, if required
        self.total_video_count = 0
        self.total_dl_count = 0
        self.total_sim_count = 0
        self.total_clip_count = 0
        self.total_slice_count = 0
        self.total_size_count = 0
        # Special count for media.Video objects which have already been
        #   checked/downloaded, and are being checked again (directly, for
        #   example after right-clicking the video)
        # If non-zero, prevents mainwin.NewbieDialogue from opening
        self.other_video_count = 0

        # If mainapp.TartubeApp.operation_convert_mode is set to any value
        #   other than 'disable', then a media.Video object whose URL
        #   represents a channel/playlist is converted into multiple new
        #   media.Video objects, one for each video actually downloaded
        # The original media.Video object is added to this list, via a call to
        #   self.mark_video_as_doomed(). At the end of the whole download
        #   operation, any media.Video object in this list is destroyed
        self.doomed_video_list = []

        # When the self.operation_type is 'classic_sim', we just compile a list
        #   of all videos detected. (A single URL may produce multiple videos)
        # A second download operation is due to be launched when this one
        #   finishes, with self.operation_type set to 'classic_custom'. During
        #   that operation, each of these video will be downloaded individually
        # The list is in groups of two, in the form
        #   [ parent_obj, json_dict ]
        # ...where 'parent_obj' is a 'dummy' media.Video object representing a
        #   video, channel or playlist, from which the metedata for a single
        #   video, 'json_dict', has been extracted
        self.classic_extract_list = []

        # Flag set to True when alternative performance limits currently apply,
        #   False when not. By checking the previous value (stored here)
        #   against the new one, we can see whether the period of alternative
        #   limits has started (or stopped)
        self.alt_limits_flag = self.check_alt_limits()
        # Alternative limits are checked every five minutes. The time (in
        #   minutes past the hour) at which the next check should be performed
        self.alt_limits_check_time = None


        # Code
        # ----

        # Set the flag
        if operation_type == 'classic_sim' \
        or operation_type == 'classic_real' \
        or operation_type == 'classic_custom':
            self.operation_classic_flag = True

        # Create an object for converting download options stored in
        #   downloads.DownloadWorker.options_list into a list of youtube-dl
        #   command line options
        self.options_parser_obj = options.OptionsParser(self.app_obj)

        # Create a list of downloads.DownloadWorker objects, each one handling
        #   one of several simultaneous downloads
        # Note that if a downloads.DownloadItem was created by a
        #   media.Scheduled object that specifies more (or fewer) workers,
        #   then self.change_worker_count() will be called
        if self.alt_limits_flag:
            worker_count = self.app_obj.alt_num_worker
        elif self.app_obj.num_worker_apply_flag:
            worker_count = self.app_obj.num_worker_default
        else:
            worker_count = self.app_obj.num_worker_max

        for i in range(1, worker_count + 1):
            self.worker_list.append(DownloadWorker(self))

        # Set the time at which the first check for alternative limits is
        #   performed
        local = ttutils.get_local_time()
        self.alt_limits_check_time \
        = (int(int(local.strftime('%M')) / 5) * 5) + 5
        if self.alt_limits_check_time > 55:
            self.alt_limits_check_time = 0
        # (Also update the icon in the Progress tab)
        GObject.timeout_add(
            0,
            self.app_obj.main_win_obj.toggle_alt_limits_image,
            self.alt_limits_flag,
        )

        # Let's get this party started!
        self.start()


    # Public class methods


    def run(self):

        """Called as a result of self.__init__().

        On a continuous loop, passes downloads.DownloadItem objects to each
        downloads.DownloadWorker object, as they become available, until the
        download operation is complete.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 319 run')

        manager_string = _('D/L Manager:') + '   '

        self.app_obj.main_win_obj.output_tab_write_stdout(
            0,
            manager_string + _('Starting download operation'),
        )

        # (Monitor changes to the number of workers, and number of available
        #   workers, so that we can display a running total in the Output tab's
        #   summary page)
        local_worker_available_count = 0
        local_worker_total_count = 0

        # Perform the download operation until there is nothing left to
        #   download, or until something has called
        #   self.stop_download_operation()
        while self.running_flag:

            # Send a message to the Output tab's summary page, if required.
            #   The number of workers shown doesn't include those dedicated to
            #   broadcasting livestreams
            available_count = 0
            total_count = 0
            for worker_obj in self.worker_list:
                if not worker_obj.broadcast_flag:
                    total_count += 1
                    if worker_obj.available_flag:
                        available_count += 1

            if local_worker_available_count != available_count \
            or local_worker_total_count != total_count:
                local_worker_available_count = available_count
                local_worker_total_count = total_count
                self.app_obj.main_win_obj.output_tab_write_stdout(
                    0,
                    manager_string + _('Workers: available:') + ' ' \
                    + str(available_count) + ', ' + _('total:') + ' ' \
                    + str(total_count),
                )

            # Auto-stop the download operation, if required
            for scheduled_obj in self.download_list_obj.scheduled_list:

                if scheduled_obj.autostop_time_flag:

                    # Calculate the current time limit, in seconds
                    unit = scheduled_obj.autostop_time_unit
                    time_limit = scheduled_obj.autostop_time_value \
                    * formats.TIME_METRIC_DICT[unit]

                    if (time.time() - self.start_time) > time_limit:
                        break

            if self.app_obj.autostop_time_flag:

                # Calculate the current time limit, in seconds
                time_limit = self.app_obj.autostop_time_value \
                * formats.TIME_METRIC_DICT[self.app_obj.autostop_time_unit]

                if (time.time() - self.start_time) > time_limit:
                    break

            # Every five minutes, check whether the period of alternative
            #   performance limits has started (or stopped)
            local = ttutils.get_local_time()
            if int(local.strftime('%M')) >= self.alt_limits_check_time:

                self.alt_limits_check_time += 5
                if self.alt_limits_check_time > 55:
                    self.alt_limits_check_time = 0

                new_flag = self.check_alt_limits()
                if new_flag != self.alt_limits_flag:

                    self.alt_limits_flag = new_flag
                    if not new_flag:

                        self.app_obj.main_win_obj.output_tab_write_stdout(
                            0,
                            _(
                            'Alternative performance limits no longer apply',
                            ),
                        )

                    else:

                        self.app_obj.main_win_obj.output_tab_write_stdout(
                            0,
                            _('Alternative performance limits now apply'),
                        )

                    # Change the number of workers. Bandwidth changes are
                    #   applied by OptionsParser.build_limit_rate()
                    if self.app_obj.num_worker_default \
                    != self.app_obj.alt_num_worker:

                        if not new_flag:

                            self.change_worker_count(
                                self.app_obj.num_worker_default,
                            )

                        else:

                            self.change_worker_count(
                                self.app_obj.alt_num_worker,
                            )

                    # (Also update the icon in the Progress tab)
                    GObject.timeout_add(
                        0,
                        self.app_obj.main_win_obj.toggle_alt_limits_image,
                        self.alt_limits_flag,
                    )

            # Fetch information about the next media data object to be
            #   downloaded (and store it in an IV, so the main window's
            #   progress bar can be updated at any time, by any code)
            self.current_item_obj = self.download_list_obj.fetch_next_item()

            # Exit this loop when there are no more downloads.DownloadItem
            #   objects whose .status is formats.MAIN_STAGE_QUEUED, and when
            #   all workers have finished their downloads
            # Otherwise, wait for an available downloads.DownloadWorker, and
            #   then assign the next downloads.DownloadItem to it
            if not self.current_item_obj:
                if self.check_workers_all_finished():

                    # Send a message to the Output tab's summary page
                    self.app_obj.main_win_obj.output_tab_write_stdout(
                        0,
                        manager_string + _('All threads finished'),
                    )

                    break

            else:
                worker_obj = self.get_available_worker(
                    self.current_item_obj.media_data_obj,
                )

                # If the worker has been marked as doomed (because the number
                #   of simultaneous downloads allowed has decreased) then we
                #   can destroy it now
                if worker_obj and worker_obj.doomed_flag:

                    worker_obj.close()
                    self.remove_worker(worker_obj)

                # Otherwise, initialise the worker's IVs for the next job
                elif worker_obj:

                    # Send a message to the Output tab's summary page
                    self.app_obj.main_win_obj.output_tab_write_stdout(
                        0,
                        _('Thread #') + str(worker_obj.worker_id) \
                        + ': ' + _('Downloading:') + ' \'' \
                        + self.current_item_obj.media_data_obj.name + '\'',
                    )

                    # Initialise IVs
                    worker_obj.prepare_download(self.current_item_obj)
                    # Change the download stage for that downloads.DownloadItem
                    self.download_list_obj.change_item_stage(
                        self.current_item_obj.item_id,
                        formats.MAIN_STAGE_ACTIVE,
                    )
                    # Update the main window's progress bar (but not for
                    #   workers dedicated to broadcasting livestreams)
                    if not worker_obj.broadcast_flag:
                        self.job_count += 1

                    # Throughout the downloads.py code, instead of calling a
                    #   mainapp.py or mainwin.py function directly (which is
                    #   not thread-safe), set a Glib timeout to handle it
                    if not self.operation_classic_flag:
                        self.nudge_progress_bar()

                    # If this downloads.DownloadItem was marked (while it was
                    #   still in the queue) as being the last one that should
                    #   be checked/downloaded, we can prevent any more items
                    #   being fetched from the downloads.DownloadList
                    if self.download_list_obj.final_item_id is not None \
                    and self.download_list_obj.final_item_id \
                    == self.current_item_obj.item_id:
                        self.download_list_obj.prevent_fetch_new_items()

            # Pause a moment, before the next iteration of the loop (don't want
            #   to hog resources)
            time.sleep(self.sleep_time)

        # Download operation complete (or has been stopped). Send messages to
        #   the Output tab's summary page
        self.app_obj.main_win_obj.output_tab_write_stdout(
            0,
            manager_string + _('Downloads complete (or stopped)'),
        )

        # Close all the workers
        self.app_obj.main_win_obj.output_tab_write_stdout(
            0,
            manager_string + _('Halting all workers'),
        )

        for worker_obj in self.worker_list:
            worker_obj.close()

        # Join and collect
        self.app_obj.main_win_obj.output_tab_write_stdout(
            0,
            manager_string + _('Join and collect threads'),
        )

        for worker_obj in self.worker_list:
            worker_obj.join()

        self.app_obj.main_win_obj.output_tab_write_stdout(
            0,
            manager_string + _('Operation complete'),
        )

        # Set the stop time
        self.stop_time = int(time.time())

        # Tell the Progress List (or Classic Progress List) to display any
        #   remaining download statistics immediately
        if not self.operation_classic_flag:

            GObject.timeout_add(
                0,
                self.app_obj.main_win_obj.progress_list_display_dl_stats,
            )

        else:

            GObject.timeout_add(
                0,
                self.app_obj.main_win_obj.classic_mode_tab_display_dl_stats,
            )

        # Any media.Video objects which have been marked as doomed, can now be
        #   destroyed
        for video_obj in self.doomed_video_list:
            self.app_obj.delete_video(
                video_obj,
                True,           # Delete any files associated with the video
                True,           # Don't update the Video Index yet
                True,           # Don't update the Video Catalogue yet
            )

        # (Also update the icon in the Progress tab)
        GObject.timeout_add(
            0,
            self.app_obj.main_win_obj.toggle_alt_limits_image,
            False,
        )

        # When youtube-dl reports it is finished, there is a short delay before
        #   the final downloaded video(s) actually exist in the filesystem
        # Therefore, mainwin.MainWin.progress_list_display_dl_stats() may not
        #   have marked the final video(s) as downloaded yet
        # Let the timer run for a few more seconds to allow those videos to be
        #   marked as downloaded (we can stop before that, if all the videos
        #   have been already marked)
        if not self.operation_classic_flag:

            GObject.timeout_add(
                0,
                self.app_obj.download_manager_halt_timer,
            )

        else:

            # For download operations launched from the Classic Mode tab, we
            #   don't need to wait at all
            GObject.timeout_add(
                0,
                self.app_obj.download_manager_finished,
            )


    def apply_ignore_limits(self):

        """Called by mainapp>TartubeApp.script_slow_timer_callback(), after
        starting a download operation to check/download everything.

        One of the media.Scheduled objects specified that operation limits
        should be ignored, so apply that setting to everything in the download
        list.

        (Doing things this way is a lot simpler than the alternatives.)
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 631 apply_ignore_limits')

        for item_id in self.download_list_obj.download_item_list:

            download_item_obj \
            = self.download_list_obj.download_item_dict[item_id]
            download_item_obj.set_ignore_limits_flag()


    def check_alt_limits(self):

        """Called by self.__init__() and .run().

        Checks whether alternative performance limits apply right now, or not.

        Return values:

            True if alternative limits apply, False if not

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 653 check_alt_limits')

        if not self.app_obj.alt_num_worker_apply_flag:
            return False

        # Get the current time and day of the week
        local = ttutils.get_local_time()
        current_hours = int(local.strftime('%H'))
        current_minutes = int(local.strftime('%M'))
        # 0=Monday, 6=Sunday
        current_day = local.today().weekday()
        target_day_str = self.app_obj.alt_day_string

        # The period of alternative performance limits have a start and stop
        #   time, stored as strings in the form '21:00'
        start_hours = int(self.app_obj.alt_start_time[0:2])
        start_minutes = int(self.app_obj.alt_start_time[3:5])
        stop_hours = int(self.app_obj.alt_stop_time[0:2])
        stop_minutes = int(self.app_obj.alt_stop_time[3:5])

        # Is the current time before or after the start/stop times?
        if current_hours < start_hours \
        or (current_hours == start_hours and current_minutes < start_minutes):
            start_before_flag = True
        else:
            start_before_flag = False

        if current_hours < stop_hours \
        or (current_hours == stop_hours and current_minutes < stop_minutes):
            stop_before_flag = True
        else:
            stop_before_flag = False

        # If the start time is earlier than the stop time, we assume they're on
        #   the same day
        if start_hours < stop_hours \
        or (start_hours == stop_hours and start_minutes < stop_minutes):

            if not ttutils.check_day(current_day, target_day_str) \
            or start_before_flag \
            or (not stop_before_flag):
                return False
            else:
                return True

        # Otherwise, we assume the stop time occurs the following day (e.g.
        #   21:00 to 07:00)
        else:

            prev_day = current_day - 1
            if prev_day < 0:
                prev_day = 6

            if (
                ttutils.check_day(current_day, target_day_str) \
                and (not start_before_flag)
            ) or (
                ttutils.check_day(prev_day, target_day_str) \
                and stop_before_flag
            ):
                return True
            else:
                return False


    def change_worker_count(self, number):

        """Called by mainapp.TartubeApp.set_num_worker_default(). Can also be
        called by self.run() when the period of alternative performances limits
        begins or ends.

        When the number of simultaneous downloads allowed is changed during a
        download operation, this function responds.

        If the number has increased, creates an extra download worker object.

        If the number has decreased, marks the worker as doomed. When its
        current download is completed, the download manager destroys it.

        Args:

            number (int): The new number of simultaneous downloads allowed

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 739 change_worker_count')

        # How many workers do we have already?
        current = len(self.worker_list)
        # If this object hasn't set up its worker pool yet, let the setup code
        #   proceed as normal
        # Sanity check: if the specified value is less than 1, or hasn't
        #   changed, take no action
        if not current or number < 1 or current == number:
            return

        # Usually, the number of workers goes up or down by one at a time, but
        #   we'll check for larger leaps anyway
        for i in range(1, (abs(current-number) + 1)):

            if number > current:

                # The number has increased. If any workers have marked as
                #   doomed, they can be unmarked, allowing them to continue
                match_flag = False

                for worker_obj in self.worker_list:
                    if worker_obj.doomed_flag:
                        worker_obj.set_doomed_flag(True)
                        match_flag = True
                        break

                if not match_flag:
                    # No workers were marked doomed, so create a brand new
                    #   download worker
                    self.worker_list.append(DownloadWorker(self))

            else:

                # The number has decreased. The first worker in the list is
                #   marked as doomed - that is, when it has finished its
                #   current job, it closes (rather than being given another
                #   job, as usual)
                for worker_obj in self.worker_list:
                    if not worker_obj.doomed_flag:
                        worker_obj.set_doomed_flag(True)
                        break


    def check_master_slave(self, media_data_obj):

        """Called by VideoDownloader.do_download().

        When two channels/playlists/folders share a download destination, we
        don't want to download both of them at the same time.

        This function is called when media_data_obj is about to be
        downloaded.

        Every worker is checked, to see if it's downloading to the same
        destination. If so, this function returns True, and
        VideoDownloader.do_download() waits a few seconds, before trying
        again.

        Otherwise, this function returns False, and
        VideoDownloader.do_download() is free to start its download.

        Args:

            media_data_obj (media.Channel, media.Playlist, media.Folder):
                The media data object that the calling function wants to
                download

        Return values:

            True or False, as described above

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 814 check_master_slave')

        for worker_obj in self.worker_list:

            if not worker_obj.available_flag \
            and worker_obj.download_item_obj:

                other_obj = worker_obj.download_item_obj.media_data_obj

                if other_obj.dbid != media_data_obj.dbid:

                    if (
                        not isinstance(other_obj, media.Video)
                        and other_obj.external_dir is not None
                    ):
                        if other_obj.external_dir \
                        == media_data_obj.external_dir:
                            return True

                    # (Alternative download destinations only apply when no
                    #   external directory is specified)
                    elif other_obj.dbid == media_data_obj.master_dbid:
                        return True

        return False


    def check_workers_all_finished(self):

        """Called by self.run().

        Based on DownloadManager._jobs_done().

        Return values:

            True if all downloads.DownloadWorker objects have finished their
                jobs, otherwise returns False

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 855 check_workers_all_finished')

        for worker_obj in self.worker_list:
            if not worker_obj.available_flag:
                return False

        return True


    def create_bypass_worker(self):

        """Called by downloads.DownloadList.create_item().

        For a broadcasting livestream, we create additional workers if
        required, possibly bypassing the limit specified by
        mainapp.TartubeApp.num_worker_default.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 874 create_bypass_worker')

        # How many workers do we have already?
        current = len(self.worker_list)
        # If this object hasn't set up its worker pool yet, let the setup code
        #   proceed as normal
        if not current:
            return

        # If we don't already have the maximum number of workers (or if no
        #   limit currently applies), then we don't need to create any more
        if not self.app_obj.num_worker_apply_flag \
        or current < self.app_obj.num_worker_default:
            return

        # Check the existing workers, in case one is already available
        for worker_obj in self.worker_list:
            if worker_obj.available_flag:
                return

        # Bypass the worker limit to create an additional worker, to be used
        #   only for broadcasting livestreams
        self.worker_list.append(DownloadWorker(self, True))
        # Create an additional page in the main window's Output tab, if
        #   required
        GObject.timeout_add(
            0,
            self.app_obj.main_win_obj.output_tab_setup_pages,
        )


    def get_available_worker(self, media_data_obj):

        """Called by self.run().

        Based on DownloadManager._get_worker().

        Args:

            media_data_obj (media.Video, media.Channel, media.Playlist or
                media.Folder): The media data object which is the next to be
                downloaded

        Return values:

            The first available downloads.DownloadWorker, or None if there are
                no available workers

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 922 get_available_worker')

        # Some workers are only available when media_data_obj is media.Video
        #   that's a broadcasting livestream
        if isinstance(media_data_obj, media.Video) \
        and media_data_obj.live_mode == 2:
            broadcast_flag = True
        else:
            broadcast_flag = False

        for worker_obj in self.worker_list:

            if worker_obj.available_flag \
            and (broadcast_flag or not worker_obj.broadcast_flag):
                return worker_obj

        return None


    def mark_video_as_doomed(self, video_obj):

        """Called by VideoDownloader.check_dl_is_correct_type().

        When youtube-dl reports the URL associated with a download item
        object contains multiple videos (or potentially contains multiple
        videos), then the URL represents a channel or playlist, not a video.

        If the channel/playlist was about to be downloaded into a media.Video
        object, then the calling function takes action to prevent it.

        It then calls this function to mark the old media.Video object to be
        destroyed, once the download operation is complete.

        Args:

            video_obj (media.Video): The video object whose URL is not a video,
                and which must be destroyed

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 963 mark_video_as_doomed')

        if isinstance(video_obj, media.Video) \
        and not video_obj in self.doomed_video_list:
            self.doomed_video_list.append(video_obj)


    def nudge_progress_bar(self):

        """Can be called by anything.

        Called by self.run() during the download operation.

        Also called by code in other files, just after that code adds a new
        media data object to our download list.

        Updates the main window's progress bar.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 983 nudge_progress_bar')

        if self.current_item_obj:

            GObject.timeout_add(
                0,
                self.app_obj.main_win_obj.update_progress_bar,
                self.current_item_obj.media_data_obj.name,
                self.job_count,
                len(self.download_list_obj.download_item_list),
            )


    def register_classic_url(self, parent_obj, json_dict):

        """Called by VideoDownloader.extract_stdout_data().

        When the self.operation_type is 'classic_sim', we just compile a list
        of all videos detected.  (A single URL may produce multiple videos).

        A second download operation is due to be launched when this one
        finishes, with self.operation_type set to 'classic_custom'. During that
        operation, each of these URLs will be downloaded individually.

        Args:

            parent_obj (media.Video, media.Channel, media.Playlist): The
                media data object from which the URL was extracted

            json_dict (dict): Metadata extracted from a single video,
                stored as a dictionary

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1018 register_classic_url')

        self.classic_extract_list.append(parent_obj)
        self.classic_extract_list.append(json_dict)


    def register_clip(self):

        """Called by ClipDownloader.confirm_video().

        A shorter version of self.register_video(). Clips do not count
        towards video limits, but we still keep track of them.

        When all of the clips for a video have been extracted, a further call
        to self.register_video() must be made.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1036 register_clip')

        self.total_clip_count += 1


    def register_slice(self):

        """Called by ClipDownloader.do_download_remove_slices().

        A shorter version of self.register_video(). Video slices removed from
        videos do not count towards video limits, but we still keep track of
        them.

        When all of the video sliceshave been removed, a further call to
        self.register_video() must be made.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1054 register_slice')

        self.total_slice_count += 1


    def register_video(self, dl_type):

        """Called by VideoDownloader.confirm_new_video(), when a video is
        downloaded, or by .confirm_sim_video(), when a simulated download finds
        a new video.

        Can also be called by .confirm_old_video() when downloading from the
        Classic Mode tab.

        Furthermore, called by ClipDownloader.do_download() when all clips for
        a video have been extracted, at least one of them successfully.

        This function adds the new video to its ongoing total and, if a limit
        has been reached, stops the download operation.

        Args:

            dl_type (str): 'new', 'sim', 'old', 'clip' or 'other', depending on
                the calling function

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1082 register_video')

        if dl_type == 'other':
            # Special count for already checked/downloaded media.Videos, in
            #   order to prevent mainwin.NewbieDialogue opening
            self.other_video_count += 1

        else:
            self.total_video_count += 1
            if dl_type == 'new':
                self.total_dl_count += 1
            elif dl_type == 'sim':
                self.total_sim_count += 1

            for scheduled_obj in self.download_list_obj.scheduled_list:

                if scheduled_obj.autostop_videos_flag \
                and self.total_video_count \
                >= scheduled_obj.autostop_videos_value:
                    return self.stop_download_operation()

            if self.app_obj.autostop_videos_flag \
            and self.total_video_count >= self.app_obj.autostop_videos_value:
                self.stop_download_operation()


    def register_video_size(self, size=None):

        """Called by mainapp.TartubeApp.update_video_when_file_found().

        Called with the size of a video that's just been downloaded. This
        function adds the size to its ongoing total and, if a limit has been
        reached, stops the download operation.

        Args:

            size (int): The size of the downloaded video (in bytes)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1123 register_video_size')

        # (In case the filesystem didn't detect the file size, for whatever
        #   reason, we'll check for a None value)
        if size is not None:

            self.total_size_count += size

            for scheduled_obj in self.download_list_obj.scheduled_list:

                if scheduled_obj.autostop_size_flag:

                    # Calculate the current limit
                    unit = scheduled_obj.autostop_size_unit
                    limit = scheduled_obj.autostop_size_value \
                    * formats.FILESIZE_METRIC_DICT[unit]

                    if self.total_size_count >= limit:
                        return self.stop_download_operation()

            if self.app_obj.autostop_size_flag:

                # Calculate the current limit
                limit = self.app_obj.autostop_size_value \
                * formats.FILESIZE_METRIC_DICT[self.app_obj.autostop_size_unit]

                if self.total_size_count >= limit:
                    self.stop_download_operation()


    def remove_worker(self, worker_obj):

        """Called by self.run().

        When a worker marked as doomed has completed its download job, this
        function is called to remove it from self.worker_list.

        Args:

            worker_obj (downloads.DownloadWorker): The worker object to remove

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1167 remove_worker')

        new_list = []

        for other_obj in self.worker_list:
            if other_obj != worker_obj:
                new_list.append(other_obj)

        self.worker_list = new_list


    def stop_download_operation(self):

        """Called by mainapp.TartubeApp.do_shutdown(), .stop_continue(),
        .dl_timer_callback(), .on_button_stop_operation().

        Also called by mainwin.StatusIcon.on_stop_menu_item().

        Also called by self.register_video() and .register_video_size().

        Based on DownloadManager.stop_downloads().

        Stops the download operation. On the next iteration of self.run()'s
        loop, the downloads.DownloadWorker objects are cleaned up.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1194 stop_download_operation')

        self.running_flag = False
        self.manual_stop_flag = True

        # In the Progress List, change the status of remaining items from
        #   'Waiting' to 'Not started'
        self.download_list_obj.abandon_remaining_items()


    def stop_download_operation_soon(self):

        """Called by mainwin.MainWin.on_progress_list_stop_all_soon(), after
        the user clicks the 'Stop after these videos' option in the Progress
        List.

        Stops the download operation, but only after any videos which are
        currently being downloaded have finished downloading.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1215 stop_download_operation_soon')

        self.manual_stop_flag = True

        self.download_list_obj.prevent_fetch_new_items()
        for worker_obj in self.worker_list:
            if worker_obj.running_flag \
            and worker_obj.downloader_obj is not None:
                worker_obj.downloader_obj.stop_soon()

        # In the Progress List, change the status of remaining items from
        #   'Waiting' to 'Not started'
        self.download_list_obj.abandon_remaining_items()


class DownloadWorker(threading.Thread):

    """Called by downloads.DownloadManager.__init__().

    Based on the Worker class in youtube-dl-gui.

    Python class for managing simultaneous downloads. The parent
    downloads.DownloadManager object can create one or more workers, each of
    which handles a single download.

    The download manager runs on a loop, looking for available workers and,
    when one is found, assigns them something to download.

    After the download is completely, the worker optionally checks a channel's
    or a playlist's RSS feed, looking for livestreams.

    When all tasks are completed, the worker waits for another assignment.

    Args:

        download_manager_obj (downloads.DownloadManager): The parent download
            manager object

        broadcast_flag (bool): True if this worker has been created
            specifically to handle broadcasting livestreams (see comments
            below); False if not

    """


    # Standard class methods


    def __init__(self, download_manager_obj, broadcast_flag=False):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1266 __init__')

        super(DownloadWorker, self).__init__()

        # IV list - class objects
        # -----------------------
        # The parent downloads.DownloadManager object
        self.download_manager_obj = download_manager_obj
        # The downloads.DownloadItem object for the current job
        self.download_item_obj = None
        # The downloads.VideoDownloader, downloads.ClipDownloader or
        #   downloads.StreamDownloader object for the current job (if it
        #   exists)
        self.downloader_obj = None
        # The downloads.JSONFetcher object for the current job (if it exists)
        self.json_fetcher_obj = None
        # The options.OptionsManager object for the current job
        self.options_manager_obj = None


        # IV list - other
        # ---------------
        # A number identifying this worker, matching the number of the page
        #   in the Output tab (so the first worker created is #1)
        self.worker_id = len(download_manager_obj.worker_list) + 1

        # The time (in seconds) between iterations of the loop in self.run()
        self.sleep_time = 0.25

        # Flag set to False if self.close() is called
        # The False value halts the main loop in self.run()
        self.running_flag = True
        # Flag set to True when the parent downloads.DownloadManager object
        #   wants to destroy this worker, having called self.set_doomed_flag()
        #   to do that
        # The worker is not destroyed until its current download is complete
        self.doomed_flag = False
        # Downloads of broadcasting livestreams must start as soon as possible.
        #   If the worker limit (mainapp.TartubeApp.num_worker_default) has
        #   been reached, additional workers are created to handle them
        # If True, this worker can only be used for broadcasting livestreams.
        #   If False, it can be used for anything
        self.broadcast_flag = broadcast_flag

        # Options list (used by downloads.VideoDownloader)
        # Initialised in the call to self.prepare_download()
        self.options_list = []
        # Flag set to True when the worker is available for a new job, False
        #   when it is already occupied with a job
        self.available_flag = True


        # Code
        # ----

        # Let's get this party started!
        self.start()


    # Public class methods


    def run(self):

        """Called as a result of self.__init__().

        Waits until this worker has been assigned a job, at which time we
        create a new downloads.VideoDownloader or downloads.StreamDownloader
        object and wait for the result.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1338 run')

        # Import the main application and custom download manager (for
        #   convenience)
        app_obj = self.download_manager_obj.app_obj
        custom_dl_obj = self.download_manager_obj.custom_dl_obj

        # Handle a job, or wait for the downloads.DownloadManager to assign
        #   this worker a job
        while self.running_flag:

            # If this worker is currently assigned a job...
            if not self.available_flag:

                # Import the media data object (for convenience)
                media_data_obj = self.download_item_obj.media_data_obj

                # If the downloads.DownloadItem was created by a scheduled
                #   download (media.Scheduled), then change the number of
                #   workers, if necessary
                if self.download_item_obj.scheduled_obj:

                    scheduled_obj = self.download_item_obj.scheduled_obj
                    if scheduled_obj.scheduled_num_worker_apply_flag \
                    and scheduled_obj.scheduled_num_worker \
                    != len(self.download_manager_obj.worker_list):

                        self.download_manager_obj.change_worker_count(
                            scheduled_obj.scheduled_num_worker,
                        )

                # When downloading a livestream that's broadcasting now, we
                #   call StreamDownloader rather than VideoDownloader
                # When downloading video clips, use youtube-dl with FFmpeg as
                #   its external downloader
                # Otherwise, use youtube-dl with an argument list determined by
                #   the download options applied
                if isinstance(media_data_obj, media.Video) \
                and media_data_obj.live_mode == 2 \
                and self.download_item_obj.operation_type != 'sim' \
                and self.download_item_obj.operation_type != 'custom_sim' \
                and self.download_item_obj.operation_type != 'classic_sim':
                    self.run_stream_downloader(media_data_obj)

                elif isinstance(media_data_obj, media.Video) \
                and not media_data_obj.live_mode \
                and (
                    (
                        (
                            self.download_item_obj.operation_type \
                            == 'custom_real' \
                            or self.download_item_obj.operation_type \
                            == 'classic_custom'
                        ) and (
                            (
                                custom_dl_obj \
                                and custom_dl_obj.dl_by_video_flag \
                                and custom_dl_obj.split_flag
                                and media_data_obj.stamp_list
                            ) or (
                                custom_dl_obj \
                                and custom_dl_obj.dl_by_video_flag \
                                and not custom_dl_obj.split_flag \
                                and custom_dl_obj.slice_flag
                                and media_data_obj.slice_list
                            ) or media_data_obj.dbid in \
                            app_obj.temp_stamp_buffer_dict \
                            or media_data_obj.dbid in \
                            app_obj.temp_slice_buffer_dict \
                        )
                    ) or (
                        self.download_item_obj.operation_type \
                        == 'classic_real' \
                        and media_data_obj.dbid in \
                        app_obj.temp_stamp_buffer_dict
                    )
                ):
                    self.run_clip_slice_downloader(media_data_obj)

                else:
                    self.run_video_downloader(media_data_obj)

                # Send a message to the Output tab's summary page
                app_obj.main_win_obj.output_tab_write_stdout(
                    0,
                    _('Thread #') + str(self.worker_id) \
                    + ': ' + _('Job complete') + ' \'' \
                    + self.download_item_obj.media_data_obj.name + '\'',
                )

                # This worker is now available for a new job
                self.available_flag = True

                # Send a message to the Output tab's summary page
                app_obj.main_win_obj.output_tab_write_stdout(
                    0,
                    _('Thread #') + str(self.worker_id) \
                    + ': ' + _('Worker now available again'),
                )

                # During (real, not simulated) custom downloads, apply a delay
                #   if one has been specified
                if (
                    self.download_item_obj.operation_type == 'custom_real' \
                    or self.download_item_obj.operation_type \
                    == 'classic_custom'
                ) and custom_dl_obj \
                and custom_dl_obj.delay_flag:

                    # Set the delay (in seconds), a randomised value if
                    #   required
                    if custom_dl_obj.delay_min:
                        delay = random.randint(
                            int(custom_dl_obj.delay_min * 60),
                            int(custom_dl_obj.delay_max * 60),
                        )
                    else:
                        delay = int(custom_dl_obj.delay_max * 60)

                    time.sleep(delay)

            # Pause a moment, before the next iteration of the loop (don't want
            #   to hog resources)
            time.sleep(self.sleep_time)


    def run_video_downloader(self, media_data_obj):

        """Called by self.run()

        Creates a new downloads.VideoDownloader to handle the download(s) for
        this job, and destroys it when it's finished.

        If possible, checks the channel/playlist RSS feed for videos we don't
        already have, and mark them as livestreams

        Args:

            media_data_obj (media.Video, media.Channel, media.Playlist,
                media.Folder): The media data object being downloaded. When the
                download operation was launched from the Classic Mode tab, a
                dummy media.Video object

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1484 run_video_downloader')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # If the download stalls, the VideoDownloader may need to be replaced
        #   with a new one. Use a while loop for that
        first_flag = True
        restart_count = 0

        while True:

            # Set up the new downloads.VideoDownloader object
            self.downloader_obj = VideoDownloader(
                self.download_manager_obj,
                self,
                self.download_item_obj,
            )

            if first_flag:

                first_flag = False
                # Send a message to the Output tab's summary page
                app_obj.main_win_obj.output_tab_write_stdout(
                    0,
                    _('Thread #') + str(self.worker_id) \
                    + ': ' + _('Assigned job:') + ' \'' \
                    + self.download_item_obj.media_data_obj.name \
                    + '\'',
                )

            # Execute the assigned job
            return_code = self.downloader_obj.do_download()

            # Any youtube-dl error/warning messages which have not yet been
            #   passed to their media.Video objects can now be processed
            for vid in self.downloader_obj.video_msg_buffer_dict.keys():
                self.downloader_obj.process_error_warning(vid)

            # Unless the download was stopped manually (return code 5), any
            #   'dummy' media.Video objects can be set, so that their URLs are
            #   not remembered in the next Tartube session
            if isinstance(media_data_obj, media.Video) \
            and media_data_obj.dummy_flag \
            and return_code < 5:
                media_data_obj.set_dummy_dl_flag(True)

            # If the download stalled, -1 is returned. If we're allowed to
            #   restart a stalled download, do that; otherwise give up
            if return_code > -1 \
            or (
                app_obj.operation_auto_restart_max != 0
                and restart_count >= app_obj.operation_auto_restart_max
            ):
                break

            else:
                restart_count += 1
                msg = _('Tartube is restarting a stalled download')

                # Show confirmation of the restart
                if app_obj.ytdl_output_stdout_flag:
                    app_obj.main_win_obj.output_tab_write_stdout(
                        self.worker_id,
                        msg,
                    )

                if app_obj.ytdl_write_stdout_flag:
                    print(msg)

                if app_obj.ytdl_log_stdout_flag:
                    app_obj.write_downloader_log(msg)

        # If the downloads.VideoDownloader object collected any youtube-dl
        #   error/warning messages, display them in the Error List
        if media_data_obj.error_list or media_data_obj.warning_list:
            GObject.timeout_add(
                0,
                app_obj.main_win_obj.errors_list_add_operation_msg,
                media_data_obj,
            )

        # In the event of an error, nothing updates the video's row in the
        #   Video Catalogue, and therefore the error icon won't be visible
        # Do that now (but don't if mainwin.ComplexCatalogueItem objects aren't
        #   being used in the Video Catalogue)
        if not self.download_item_obj.operation_classic_flag \
        and return_code == VideoDownloader.ERROR \
        and isinstance(media_data_obj, media.Video) \
        and app_obj.catalogue_mode_type != 'simple':
            GObject.timeout_add(
                0,
                app_obj.main_win_obj.video_catalogue_update_video,
                media_data_obj,
            )

        # Call the destructor function of VideoDownloader object
        self.downloader_obj.close()

        # If possible, check the channel/playlist RSS feed for videos we don't
        #   already have, and mark them as livestreams
        if self.running_flag \
        and mainapp.HAVE_FEEDPARSER_FLAG \
        and app_obj.enable_livestreams_flag \
        and (
            isinstance(media_data_obj, media.Channel) \
            or isinstance(media_data_obj, media.Playlist)
        ) and not media_data_obj.dl_no_db_flag \
        and media_data_obj.child_list \
        and media_data_obj.rss:

            # Send a message to the Output tab's summary page
            app_obj.main_win_obj.output_tab_write_stdout(
                0,
                _('Thread #') + str(self.worker_id) \
                + ': ' + _('Checking RSS feed'),
            )

            # Check the RSS feed for the media data object
            self.check_rss(media_data_obj)


    def run_clip_slice_downloader(self, media_data_obj):

        """Called by self.run()

        Creates a new downloads.ClipDownloader to handle the download(s) for
        this job, and destroys it when it's finished.

        Args:

            media_data_obj (media.Video): The media data object being
                downloaded. When the download operation was launched from the
                Classic Mode tab, a dummy media.Video object

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1622 run_clip_slice_downloader')

        # Import the main application and custom download manager (for
        #   convenience)
        app_obj = self.download_manager_obj.app_obj
        custom_dl_obj = self.download_manager_obj.custom_dl_obj

        # Set up the new downloads.ClipDownloader object
        self.downloader_obj = ClipDownloader(
            self.download_manager_obj,
            self,
            self.download_item_obj,
        )

        # Send a message to the Output tab's summary page
        app_obj.main_win_obj.output_tab_write_stdout(
            0,
            _('Thread #') + str(self.worker_id) \
            + ': ' + _('Assigned job:') + ' \'' \
            + self.download_item_obj.media_data_obj.name \
            + '\'',
        )

        # Execute the assigned job
        # ClipDownloader handles two related operations. Both start by
        #   downloading the video as clips. The second operation concatenates
        #   the clips back together, which has the effect of removing one or
        #   more slices from a video
        if (
            custom_dl_obj \
            and custom_dl_obj.split_flag \
            and media_data_obj.stamp_list
        ) or media_data_obj.dbid in app_obj.temp_stamp_buffer_dict:
            return_code = self.downloader_obj.do_download_clips()
        else:
            return_code = self.downloader_obj.do_download_remove_slices()

        # In the event of an error, nothing updates the video's row in the
        #   Video Catalogue, and therefore the error icon won't be visible
        # Do that now (but don't if mainwin.ComplexCatalogueItem objects aren't
        #   being used in the Video Catalogue)
        if not self.download_item_obj.operation_classic_flag \
        and return_code == ClipDownloader.ERROR \
        and app_obj.catalogue_mode_type != 'simple':
            GObject.timeout_add(
                0,
                app_obj.main_win_obj.video_catalogue_update_video,
                media_data_obj,
            )

        # Call the destructor function of ClipDownloader object
        self.downloader_obj.close()


    def run_stream_downloader(self, media_data_obj):

        """Called by self.run()

        A modified version of self.run_video_downloader(), used when
        downloading a media.Video object that's a livestream broadcasting now.

        First creates a new downloads.VideoDownloader to check the video, if
        it hasn't already been checked (which fetches the thumbnail,
        description, annotations and metadata files).

        Then creates a new downloads.StreamDownloader to handle the download
        for this job.

        Args:

            media_data_obj (media.Video): The media data object being
                downloaded

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1698 run_stream_downloader')

        # Import the main application (for convenience)
        app_obj = self.download_manager_obj.app_obj

        # Checking a livestream (simulated download), before downloading it
        #   (real download) makes sure that the thumbnail and other metadata
        #   files are downloaded, if required
        # Assume that the video has not been checked if its path or name are
        #   not set
        # If mainapp.TartubeApp.livestream_dl_mode is 'default', meaning that
        #   youtube-dl is downloading the livestream directly, then there is
        #   no need to check the video first
        if app_obj.livestream_dl_mode != 'default' \
        and not self.download_manager_obj.operation_classic_flag \
        and (
            app_obj.livestream_force_check_flag \
            or media_data_obj.file_name is None \
            or media_data_obj.file_ext is None
        ):
            # Set up the new downloads.VideoDownloader object. The True
            #   argument forces it to do a simulated download
            self.downloader_obj = VideoDownloader(
                self.download_manager_obj,
                self,
                self.download_item_obj,
                True,
            )

            # Send a message to the Output tab's summary page
            app_obj.main_win_obj.output_tab_write_stdout(
                0,
                _('Thread #') + str(self.worker_id) \
                + ': ' + _('Assigned job:') + ' \'' \
                + self.download_item_obj.media_data_obj.name \
                + '\'',
            )

            # Execute the assigned job (but regardless of success or failure,
            #   we press on with the livestream download below)
            return_code = self.downloader_obj.do_download()

            # Any youtube-dl error/warning messages which have not yet been
            #   passed to their media.Video objects can now be processed
            for vid in self.downloader_obj.video_msg_buffer_dict.keys():
                self.downloader_obj.process_error_warning(vid)

            # If the downloads.VideoDownloader object collected any youtube-dl
            #   error/warning messages, display them in the Error List
            if media_data_obj.error_list or media_data_obj.warning_list:
                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.errors_list_add_operation_msg,
                    media_data_obj,
                )

            # In the event of an error, nothing updates the video's row in the
            #   Video Catalogue, and therefore the error icon won't be visible
            # Do that now (but don't if mainwin.ComplexCatalogueItem objects
            #   aren't being used in the Video Catalogue)
            if not self.download_item_obj.operation_classic_flag \
            and return_code == VideoDownloader.ERROR \
            and isinstance(media_data_obj, media.Video) \
            and app_obj.catalogue_mode_type != 'simple':
                GObject.timeout_add(
                    0,
                    app_obj.main_win_obj.video_catalogue_update_video,
                    media_data_obj,
                )

            # Call the destructor function of VideoDownloader object
            self.downloader_obj.close()

            # In the event of an error during the checking stage, don't
            #   proceed with the download
            if return_code >= VideoDownloader.ERROR:
                return

            # Reset our IVs, ready for the call to StreamDownloader
            self.prepare_download(self.download_item_obj)

        # Now proceed with the livestream download. Set up the new
        #   downloads.StreamDownloader object
        self.downloader_obj = StreamDownloader(
            self.download_manager_obj,
            self,
            self.download_item_obj,
        )

        # Send a message to the Output tab's summary page
        app_obj.main_win_obj.output_tab_write_stdout(
            0,
            _('Thread #') + str(self.worker_id) \
            + ': ' + _('Assigned job:') + ' \'' \
            + self.download_item_obj.media_data_obj.name \
            + '\'',
        )

        # Execute the assigned job
        return_code = self.downloader_obj.do_download()

        # In the event of an error, nothing updates the video's row in the
        #   Video Catalogue, and therefore the error icon won't be visible
        # Do that now (but don't if mainwin.ComplexCatalogueItem objects aren't
        #   being used in the Video Catalogue)
        if not self.download_item_obj.operation_classic_flag \
        and return_code == StreamDownloader.ERROR \
        and app_obj.catalogue_mode_type != 'simple':
            GObject.timeout_add(
                0,
                app_obj.main_win_obj.video_catalogue_update_video,
                media_data_obj,
            )

        # Call the destructor function of StreamDownloader object
        self.downloader_obj.close()


    def close(self):

        """Called by downloads.DownloadManager.run().

        This worker object is closed when:

            1. The download operation is complete (or has been stopped)
            2. The worker has been marked as doomed, and the calling function
                is now ready to destroy it

        Tidy up IVs and stop any child processes.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1830 close')

        self.running_flag = False

        if self.downloader_obj:
            self.downloader_obj.stop()

        if self.json_fetcher_obj:
            self.json_fetcher_obj.stop()


    def check_rss(self, container_obj):

        """Called by self.run(), after the VideoDownloader has finished.

        If possible, check the channel/playlist RSS feed for videos we don't
        already have, and mark them as livestreams.

        This process works on YouTube (each media.Channel and media.Playlist
        has the URL for its RSS feed set automatically).

        It might work on other compatible websites (the user must set the
        channel's/playlist's RSS feed manually).

        On a compatible website, when youtube-dl fetches a list of videos in
        the channel/playlist, it won't fetch any that are livestreams (either
        waiting to start, or currently broadcasting).

        However, livestreams (both waiting and broadcasting) do appear in the
        RSS feed. We can compare the RSS feed against the channel's/playlist's
        list of child media.Video objects (which has just been updated), in
        order to detect livestreams (with reasonably good accuracy).

        Args:

            container_obj (media.Channel, media.Playlist): The channel or
                playlist which the VideoDownloader has just checked/downloaded.
                (This function is not called for media.Folders or for
                individual media.Video objects)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1873 check_rss')

        app_obj = self.download_manager_obj.app_obj

        # Livestreams are usually the first entry in the RSS feed, having not
        #   started yet (or being currently broadcast), but there's no
        #   gurantee of that
        # In addition, although RSS feeds are normally quite short (with
        #    dozens of entries, not thousands), there is no guarantee of this
        # mainapp.TartubeApp.livestream_max_days specifies how many days of
        #   videos we should check, looking for livestreams
        # Implement this by stopping when an entry in the RSS feed matches a
        #   particular media.Video object
        # (If we can't decide which video to match, the default to searching
        #   the whole RSS feed)
        time_limit_video_obj = None
        check_source_list = []
        check_name_list = []

        if app_obj.livestream_max_days:

            # Stop checking the RSS feed at the first matching video that's
            #   older than the specified time
            # (Of course, the 'first video' must not itself be a livestream)
            older_time = int(
                time.time() - (app_obj.livestream_max_days * 86400),
            )

            for child_obj in container_obj.child_list:

                # An entry in the RSS feed is a new livestream, if it doesn't
                #   match one of the videos in these lists
                # (We don't need to check each RSS entry against the entire
                #   contents of the channel/playlist - which might be thousands
                #   of videos - just those up to the time limit)
                if child_obj.source:
                    check_source_list.append(child_obj.source)
                if child_obj.name != app_obj.default_video_name:
                    check_name_list.append(child_obj.name)

            # The time limit will apply to this video, when found
            for child_obj in container_obj.child_list:
                if child_obj.source \
                and not child_obj.live_mode \
                and child_obj.upload_time is not None \
                and child_obj.upload_time < older_time:
                    time_limit_video_obj = child_obj
                    break

        else:

            # Stop checking the RSS feed at the first matching video, no matter
            #   how old
            for child_obj in container_obj.child_list:
                if child_obj.source:
                    check_source_list.append(child_obj.source)
                if child_obj.name != app_obj.default_video_name:
                    check_name_list.append(child_obj.name)

            for child_obj in container_obj.child_list:
                if child_obj.source \
                and not time_limit_video_obj \
                and not child_obj.live_mode:
                    time_limit_video_obj = child_obj
                    break

        # Fetch the RSS feed
        try:
            feed_dict = feedparser.parse(container_obj.rss)
        except:
            return

        # Check each entry in the feed, stopping at the first one which matches
        #   the selected media.Video object
        for entry_dict in feed_dict['entries']:

            if time_limit_video_obj \
            and entry_dict['link'] == time_limit_video_obj.source:

                # Found a matching media.Video object, so we can stop looking
                #   for livestreams now
                break

            elif not entry_dict['link'] in check_source_list \
            and not entry_dict['title'] in check_name_list:

                # New livestream detected. Create a new JSONFetcher object to
                #   fetch its JSON data
                # If the data is received, the livestream is live. If the data
                #   is not received, the livestream is waiting to go live
                self.json_fetcher_obj = JSONFetcher(
                    self.download_manager_obj,
                    self,
                    container_obj,
                    entry_dict,
                )

                # Then execute the assigned job
                self.json_fetcher_obj.do_fetch()

                # Call the destructor function of the JSONFetcher object
                self.json_fetcher_obj.close()
                self.json_fetcher_obj = None


    def prepare_download(self, download_item_obj):

        """Called by downloads.DownloadManager.run().

        Also called by self.run_stream_downloader() after the checking phase,
        just before downloading the broadcasting livestream for real.

        Based on Worker.download().

        Updates IVs for a new job, so that self.run can initiate the download.

        Args:

            download_item_obj (downloads.DownloadItem): The download item
                object describing the URL from which youtube-dl should download
                video(s).

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 1998 prepare_download')

        self.download_item_obj = download_item_obj
        self.options_manager_obj = download_item_obj.options_manager_obj

        self.options_list = self.download_manager_obj.options_parser_obj.parse(
            self.download_item_obj.media_data_obj,
            self.options_manager_obj,
            self.download_item_obj.operation_type,
            self.download_item_obj.scheduled_obj,
        )

        self.available_flag = False


    def set_doomed_flag(self, flag):

        """Called by downloads.DownloadManager.change_worker_count()."""

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2018 set_doomed_flag')

        self.doomed_flag = flag


    # Callback class methods


    def data_callback(self, dl_stat_dict, last_flag=False):

        """Called by downloads.VideoDownloader.read_child_process() and
        .last_data_callback().

        Based on Worker._data_hook() and ._talk_to_gui().

        'dl_stat_dict' holds a dictionary of statistics in a standard format
        specified by downloads.VideoDownloader.extract_stdout_data().

        This callback receives that dictionary and passes it on to the main
        window, so the statistics can be displayed there.

        Args:

            dl_stat_dict (dict): The dictionary of statistics described above

            last_flag (bool): True when called by .last_data_callback(),
                meaning that the VideoDownloader object has finished, and is
                sending this function the final set of statistics

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2050 data_callback')

        main_win_obj = self.download_manager_obj.app_obj.main_win_obj

        if not self.download_item_obj.operation_classic_flag:

            GObject.timeout_add(
                0,
                main_win_obj.progress_list_receive_dl_stats,
                self.download_item_obj,
                dl_stat_dict,
                last_flag,
            )

            # If downloading a video individually, need to update the tooltips
            #   in the Results List to show any errors/warnings (which won't
            #   show up if the video was not downloaded)
            if last_flag \
            and isinstance(self.download_item_obj.media_data_obj, media.Video):

                GObject.timeout_add(
                    0,
                    main_win_obj.results_list_update_tooltip,
                    self.download_item_obj.media_data_obj,
                )

        else:

            GObject.timeout_add(
                0,
                main_win_obj.classic_mode_tab_receive_dl_stats,
                self.download_item_obj,
                dl_stat_dict,
                last_flag,
            )


class StreamManager(threading.Thread):

    """Called by mainapp.TartubeApp.livestream_manager_start().

    Python class to create a system child process, to check media.Video objects
    already marked as livestreams, to see whether they have started or stopped
    broadcasting.

    Reads from the child process STDOUT and STDERR, having set up a
    downloads.PipeReader object to do so in an asynchronous way.

    Args:

        app_obj (mainapp.TartubeApp): The main application

    """


    # Standard class methods


    def __init__(self, app_obj):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11094 __init__')

        super(StreamManager, self).__init__()

        # IV list - class objects
        # -----------------------
        # The mainapp.TartubeApp object
        self.app_obj = app_obj
        # The downloads.MiniJSONFetcher object used to check each media.Video
        #   object marked as a livestream
        self.mini_fetcher_obj = None


        # IV list - other
        # ---------------
        # A local list of media.Video objects marked as livestreams (in case
        #   the mainapp.TartubeApp IV changes during the course of this
        #   operation)
        # Dictionary in the form:
        #   key = media data object's unique .dbid
        #   value = the media data object itself
        self.video_dict = {}

        # Flag set to False if self.stop_livestream_operation() is called
        # The False value halts the loop in self.run()
        self.running_flag = True

        # Code
        # ----

        # Let's get this party started!
        self.start()


    # Public class methods


    def run(self):

        """Called as a result of self.__init__().

        Initiates the download.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11139 run')

        # Generate a local list of media.Video objects marked as livestreams
        #   (in case the mainapp.TartubeApp IV changes during the course of
        #   this operation)
        self.video_dict = self.app_obj.media_reg_live_dict.copy()

        for video_obj in self.video_dict.values():

            if not self.running_flag:
                break

            # For each media.Video in turn, try to fetch JSON data
            # If the data is received, assume the livestream is live. If a
            #   'This video is unavailable' error is received, the livestream
            #   is waiting to go live
            self.mini_fetcher_obj = MiniJSONFetcher(self, video_obj)

            # Then execute the assigned job
            self.mini_fetcher_obj.do_fetch()

            # Call the destructor function of the MiniJSONFetcher object
            #   (first checking it still exists, in case
            #   self.stop_livestream_operation() has been called)
            if self.mini_fetcher_obj:
                self.mini_fetcher_obj.close()
                self.mini_fetcher_obj = None

        # Operation complete. If self.stop_livestream_operation() was called,
        #   then the mainapp.TartubeApp function has already been called
        if self.running_flag:
            self.running_flag = False
            GObject.timeout_add(
                0,
                self.app_obj.livestream_manager_finished,
            )


    def stop_livestream_operation(self):

        """Can be called by anything.

        Based on downloads.DownloadManager.stop_downloads().

        Stops the livestream operation. On the next iteration of self.run()'s
        loop, the downloads.MiniJSONFetcher objects are cleaned up.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 11185 stop_livestream_operation')

        self.running_flag = False

        # Halt the MiniJSONFetcher; it doesn't matter if it was in the middle
        #   of doing something
        if self.mini_fetcher_obj:
            self.mini_fetcher_obj.close()
            self.mini_fetcher_obj = None

        # Call the mainapp.TartubeApp function to update everything (it's not
        #   called from self.run(), in this situation)
        GObject.timeout_add(
            0,
            self.app_obj.livestream_manager_finished,
        )
