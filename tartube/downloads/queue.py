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
class DownloadList(object):

    """Called by mainapp.TartubeApp.download_manager_continue().

    Based on the DownloadList class in youtube-dl-gui.

    Python class to keep track of all the media data objects to be downloaded
    (for real or in simulation) during a downloaded operation.

    This object contains an ordered list of downloads.DownloadItem objects.
    Each of those objects represents a media data object to be downloaded
    (media.Video, media.Channel, media.Playlist or media.Folder).

    Videos are downloaded in the order specified by the list.

    Args:

        app_obj (mainapp.TartubeApp): The main application

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

        media_data_list (list): List of media.Video, media.Channel,
            media.Playlist and/or media.Folder objects. Can also be a list of
            (exclusively) media.Scheduled objects. If not an empty list, only
            the specified media data objects (and their children) are
            checked/downloaded. If an empty list, all media data objects are
            checked/downloaded. If operation_type is 'classic', then the
            media_data_list contains a list of dummy media.Video objects from a
            previous call to this function. If an empty list, all
            dummy media.Video objects are downloaded

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


    def __init__(self, app_obj, operation_type, media_data_list, \
    custom_dl_obj):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2153 __init__')

        # IV list - class objects
        # -----------------------
        self.app_obj = app_obj

        # The custom download manager (downloads.CustomDLManager) that applies
        #   to this download operation. Only specified when 'operation_type' is
        #   'custom_sim', 'custom_real', 'classic_sim' or 'classic_real'
        # For 'custom_real' and 'classic_real', not specified if
        #   mainapp.TartubeApp.temp_stamp_buffer_dict or
        #   .temp_slice_buffer_dict are specified (because those values take
        #   priority)
        self.custom_dl_obj = custom_dl_obj

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
        # This IV records the default setting for this operation. Once the
        #   download operation starts, new download.DownloadItem objects can
        #   be added to the list in a call to self.create_item(), and that call
        #   can specify a value that overrides the default value, just for that
        #   call
        # Overriding the default value is not possible for download operations
        #   initiated from the Classic Mode tab
        self.operation_type = operation_type
        # Shortcut flag to test the operation type; True for 'classic_sim',
        #   'classic_real' and 'classic_custom'; False forall other values
        self.operation_classic_flag = False         # (Set below)
        # Flag set to True in a call to self.prevent_fetch_new_items(), in
        #   which case subsequent calls to self.fetch_next_item() return
        #   nothing, preventing any further downloads
        self.prevent_fetch_flag = False

        # Number of download.DownloadItem objects created (used to give each a
        #   unique ID)
        self.download_item_count = 0

        # An ordered list of downloads.DownloadItem objects, one for each
        #   media.Video, media.Channel, media.Playlist or media.Folder object
        #   (including dummy media.Video objects used by download operations
        #   launched from the Classic Mode tab)
        # This list stores each item's .item_id
        self.download_item_list = []
        # A supplementary list of downloads.DownloadItem objects
        # Suppose self.download_item_list already contains items A B C, and
        #   some of part of the code wants to add items X Y Z to the beginning
        #   of the list, producing the list X Y Z A B C (and not Z Y X A B C)
        # The new items are added (one at a time) to this temporary list, and
        #   then added to the beginning/end of self.download_item_list at the
        #   end of this function (or in the next call to
        #   self.fetch_next_item() )
        self.temp_item_list = []

        # We preserve the 'media_data_list' argument (which may be an empty
        #   list). Used by mainapp.TartubeApp.download_manager_finished during
        #   a 'custom_sim' operation, in order to initiate the subsequent
        #   'custom_real' operation
        self.orig_media_data_list = media_data_list

        # Corresponding dictionary of downloads.DownloadItem items for quick
        #   lookup, containing items from both self.download_item_list and
        #   self.temp_item_list
        # Dictionary in the form
        #   key = download.DownloadItem.item_id
        #   value = the download.DownloadItem object itself
        self.download_item_dict = {}
        # The .item_id of a download.DownloadItem.item_id, which is set (if
        #   required) by a call to self.set_final_item()
        # When self.fetch_next_item() fetches this item, that item is the last
        #   item to be fetched: self.download_item_list() and
        #   self.temp_item_list() are emptied, and any items they contained are
        #   not checked/downloaded
        self.final_item_id = None

        # List of any media.Scheduled objects involved in the current download
        #   operation
        self.scheduled_list = []


        # Code
        # ----

        # Set the flag
        if operation_type == 'classic_sim' \
        or operation_type == 'classic_real' \
        or operation_type == 'classic_custom':
            self.operation_classic_flag = True

        # Compile the list

        # Scheduled downloads
        if media_data_list and isinstance(media_data_list[0], media.Scheduled):

            # media_data_list is a list of media.Scheduled objects, each one
            #   handling a scheduled download
            all_obj = False
            ignore_limits_flag = False

            for scheduled_obj in media_data_list:
                if scheduled_obj.all_flag:
                    all_obj = scheduled_obj
                if scheduled_obj.ignore_limits_flag:
                    ignore_limits_flag = True
                if all_obj:
                    break


            if all_obj:

                # Use all media data objects
                for dbid in self.app_obj.container_top_level_list:
                    obj = self.app_obj.media_reg_dict[dbid]
                    self.create_item(
                        obj,
                        all_obj,    # media.Scheduled object
                        None,       # override_operation_type
                        False,      # priority_flag
                        ignore_limits_flag,
                    )

            else:

                # Use only media data objects specified by the media.Scheduled
                #   objects
                # Don't add the same media data object twice
                check_dict = {}

                for scheduled_obj in media_data_list:

                    if scheduled_obj.join_mode == 'priority':
                        priority_flag = True
                    else:
                        priority_flag = False

                    for dbid in scheduled_obj.media_list:
                        if not dbid in check_dict:

                            obj = self.app_obj.media_reg_dict[dbid]
                            self.create_item(
                                obj,
                                scheduled_obj,
                                scheduled_obj.dl_mode,
                                priority_flag,
                                scheduled_obj.ignore_limits_flag,
                            )

                            check_dict[dbid] = None

        # Normal downloads
        elif not self.operation_classic_flag:

            # For each media data object to be downloaded, create a
            #   downloads.DownloadItem object, and update the IVs above
            if not media_data_list:

                # Use all media data objects
                for dbid in self.app_obj.container_top_level_list:
                    obj = self.app_obj.media_reg_dict[dbid]
                    self.create_item(
                        obj,
                        None,       # media.Scheduled object
                        None,       # override_operation_type
                        False,      # priority_flag
                        False,      # ignore_limits_flag
                    )

            else:

                for media_data_obj in media_data_list:

                    if isinstance(media_data_obj, media.Folder) \
                    and media_data_obj.priv_flag:

                        # Videos in a private folder's .child_list can't be
                        #   downloaded (since they are also a child of a
                        #   channel, playlist or a public folder)
                        GObject.timeout_add(
                            0,
                            app_obj.system_error,
                            301,
                            _('Cannot download videos in a private folder'),
                        )

                    else:

                        # Use the specified media data object
                        self.create_item(
                            media_data_obj,
                            None,       # media.Scheduled object
                            None,       # override_operation_type
                            False,      # priority_flag
                            False,      # ignore_limits_flag
                        )

            # Some media data objects have an alternate download destination,
            #   for example, a playlist ('slave') might download its videos
            #   into the directory used by a channel ('master')
            # This can increase the length of the operation, because a 'slave'
            #   won't start until its 'master' is finished
            # Make sure all designated 'masters' are handled before 'slaves' (a
            #   media data object can't be both a master and a slave)
            self.reorder_master_slave()

        # Downloads from the Classic Mode tab
        else:

            # The download operation was launched from the Classic Mode tab.
            #   Each URL to be downloaded is represented by a dummy media.Video
            #   object (one which is not in the media data registry)
            main_win_obj = self.app_obj.main_win_obj

            # The user may have rearranged rows in the Classic Mode tab, so
            #   get a list of (all) dummy media.Videos in the rearranged order
            # (It should be safe to assume that the Gtk.Liststore contains
            #   exactly the same number of rows, as dummy media.Video objects
            #   in mainwin.MainWin.classic_media_dict)
            dbid_list = []
            for row in main_win_obj.classic_progress_liststore:
                dbid_list.append(row[0])

            # Compile a list of dummy media.Video objects in the correct order
            obj_list = []
            if not media_data_list:

                # Use all of them
                for dbid in dbid_list:
                    obj_list.append(main_win_obj.classic_media_dict[dbid])

            else:

                # Use a subset of them
                for dbid in dbid_list:

                    dummy_obj = main_win_obj.classic_media_dict[dbid]
                    if dummy_obj in media_data_list:
                        obj_list.append(dummy_obj)


            # For each dummy media.Video object, create a
            #   downloads.DownloadItem object, and update the IVs above
            # Don't re-download a video already marked as downloaded (if the
            #   user actually wants to re-download a video, then
            #   mainapp.TartubeApp.on_button_classic_redownload() has reset the
            #   flag)
            for dummy_obj in obj_list:

                if not dummy_obj.dl_flag:
                    self.create_dummy_item(dummy_obj)

        # We can now merge the two DownloadItem lists
        if self.temp_item_list:

            self.download_item_list \
            = self.temp_item_list + self.download_item_list
            self.temp_item_list = []


    # Public class methods


    @synchronise(_SYNC_LOCK)
    def abandon_remaining_items(self):

        """Called by downloads.DownloadManager.stop_download_operation() and
        .stop_download_operation_soon().

        When the download operation has been stopped by the user, any rows in
        the main window's Progress List (or Classic Progress List) currently
        marked as 'Waiting' should be marked as 'Not started'.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2439 abandon_remaining_items')

        main_win_obj = self.app_obj.main_win_obj
        download_manager_obj = self.app_obj.download_manager_obj

        # In case of any recent calls to self.create_item(), which want to
        #   place new DownloadItems at the beginning of the queue, then
        #   merge the temporary queue into the main one
        if self.temp_item_list:
            self.download_item_list \
            = self.temp_item_list + self.download_item_list

        # 'dl_stat_dict' holds a dictionary of statistics in a standard format
        #   specified by downloads.VideoDownloader.extract_stdout_data()
        # Prepare the dictionary to be passed on to the main window, so the
        #   statistics can be displayed there for every 'Waiting' item
        dl_stat_dict = {}
        dl_stat_dict['status'] = formats.MAIN_STAGE_NOT_STARTED

        for item_id in self.download_item_list:
            this_item = self.download_item_dict[item_id]

            if this_item.stage == formats.MAIN_STAGE_QUEUED:
                this_item.stage = formats.MAIN_STAGE_NOT_STARTED

                if not download_manager_obj.operation_classic_flag:

                    GObject.timeout_add(
                        0,
                        main_win_obj.progress_list_receive_dl_stats,
                        this_item,
                        dl_stat_dict,
                        True,       # Final set of statistics for this item
                    )

                else:

                    GObject.timeout_add(
                        0,
                        main_win_obj.classic_mode_tab_receive_dl_stats,
                        this_item,
                        dl_stat_dict,
                        True,       # Final set of statistics for this item
                    )


    @synchronise(_SYNC_LOCK)
    def change_item_stage(self, item_id, new_stage):

        """Called by downloads.DownloadManager.run().

        Based on DownloadList.change_stage().

        Changes the download stage for the specified downloads.DownloadItem
        object.

        Args:

            item_id (int): The specified item's .item_id

            new_stage: The new download stage, one of the values imported from
                formats.py (e.g. formats.MAIN_STAGE_QUEUED)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2505 change_item_stage')

        self.download_item_dict[item_id].stage = new_stage


    def create_item(self, media_data_obj, scheduled_obj=None,
    override_operation_type=None, priority_flag=False,
    ignore_limits_flag=False, recursion_flag=False):

        """Called initially by self.__init__() (or by many other functions,
        for example in mainapp.TartubeApp).

        Subsequently called by this function recursively.

        Creates a downloads.DownloadItem object for media data objects in the
        media data registry.

        Doesn't create a download item object for:
            - media.Video, media.Channel and media.Playlist objects whose
                .source is None
            - media.Video objects whose parent is not a media.Folder (i.e.
                whose parent is a media.Channel or a media.Playlist)
            - media.Video objects in any restricted folder
            - media.Video objects in the fixed 'Unsorted Videos' folder which
                are already marked as downloaded
            - media.Video objects which have an ancestor (e.g. a parent
                media.Channel) for which checking/downloading is disabled
            - media.Video objects whose parent is a media.Folder, and whose
                file IVs are set, and for which a thumbnail exists, if
                mainapp.TartubeApp.operation_sim_shortcut_flag is set, and if
                the operation_type is 'sim'
            - media.Channel and media.Playlist objects for which checking/
                downloading are disabled, or which have an ancestor (e.g. a
                parent media.folder) for which checking/downloading is disabled
            - media.Channel, media.Playlist and media.Folder objects whose
                .dl_no_db_flag is set, during simulated downloads
            - media.Channel and media.Playlist objects during custom downloads
                in which videos are to be downloaded independently
            - media.Channel and media.Playlist objects which are disabled
                because their external directory is not available
            - media.Video objects whose parent channel/playlist/folder is
                marked unavailable because its external directory is not
                accessible
            - media.Folder objects

        Adds the resulting downloads.DownloadItem object to this object's IVs.

        Args:

            media_data_obj (media.Video, media.Channel, media.Playlist,
                media.Folder): A media data object

            scheduled_obj (media.Scheduled): The scheduled download object
                which wants to download media_data_obj (None if no scheduled
                download applies in this case)

            override_operation_type (str): After the download operation has
                started, any code can call this function to add new
                downloads.DownloadItem objects to this downloads.DownloadList,
                specifying a value that overrides the default value of
                self.operation_type. Note that this is not allowed when
                self.operation_type is 'classic_real', 'classic_sim' or
                'classic_custom', and will cause an error. The value is always
                None when called by self.__init__(). Otherwise, the value can
                be None, 'sim', 'real', 'custom_sim' or 'custom_real'

            priority_flag (bool): True if media_data_obj is to be added to the
                beginning of the list, False if it is to be added to the end
                of the list

            ignore_limits_flag (bool): True if operation limits
                (mainapp.TartubeApp.operation_limit_flag) should be ignored

            recursion_flag (bool): True when called by this function
                recursively, False when called (for the first time) by anything
                else. If False and media_data_obj is a media.Video object, we
                download it even if its parent is a channel or a playlist

        Return values:

            A list of downloads.DownloadItem objects created (an empty list if
                none are created)

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2592 create_item')

        # (Use two lists for code clarity)
        return_list = []
        empty_list = []

        # Sanity check - if no URL is specified, then there is nothing to
        #   download
        if not isinstance(media_data_obj, media.Folder) \
        and media_data_obj.source is None:
            return empty_list

        # Apply the operation_type override, if specified
        if override_operation_type is not None:

            if self.operation_classic_flag:

                GObject.timeout_add(
                    0,
                    self.app_obj.system_error,
                    302,
                    'Invalid argument in Classic Mode tab download operation',
                )

                return empty_list

            else:

                operation_type = override_operation_type

        else:

            operation_type = self.operation_type

        if operation_type == 'custom_real' \
        or operation_type == 'classic_custom':
            custom_flag = True
        else:
            custom_flag = False

        # Get the options.OptionsManager object that applies to this media
        #   data object
        # (The manager might be specified by obj itself, or it might be
        #   specified by obj's parent, or we might use the default
        #   options.OptionsManager)
        if not self.operation_classic_flag:

            options_manager_obj = ttutils.get_options_manager(
                self.app_obj,
                media_data_obj,
            )

        else:

            # Classic Mode tab
            if self.app_obj.classic_options_obj is not None:
                options_manager_obj = self.app_obj.classic_options_obj
            else:
                options_manager_obj = self.app_obj.general_options_obj

        # Ignore private folders, and don't download any of their children
        #   (because they are all children of some other non-private folder)
        if isinstance(media_data_obj, media.Folder) \
        and media_data_obj.priv_flag:
            return empty_list

        # Don't download videos that we already have (but do check a video
        #   that's already been downloaded)
        # Don't download videos if they're in a channel or playlist (since
        #   downloading the channel/playlist downloads the videos it contains)
        # (Exception: download a single video if that's what the calling code
        #   has specifically requested)
        # (Exception: for custom downloads, do get videos independently of
        #   their channel/playlist, if allowed)
        # Don't download videos in a folder, if this is a simulated download,
        #   and the video has already been checked (exception: if the video
        #   has been passed to the download operation directly, for example by
        #   right-clicking the video and selecting 'Check video')
        # (Exception: do download videos in a folder if they're marked as
        #   livestreams, in case the livestream has finished)
        # During custom downloads that required a subtitled video, don't
        #   download an un-subtitles video
        if isinstance(media_data_obj, media.Video):

            if media_data_obj.dl_flag \
            and operation_type != 'sim' \
            and not media_data_obj.dbid \
            in self.app_obj.temp_stamp_buffer_dict \
            and not media_data_obj.dbid in self.app_obj.temp_slice_buffer_dict:
                return empty_list

            if (
                not isinstance(media_data_obj.parent_obj, media.Folder) \
                and recursion_flag
                and (
                    not custom_flag
                    or (
                        self.custom_dl_obj \
                        and not self.custom_dl_obj.dl_by_video_flag
                    ) or media_data_obj.dl_flag
                )
            ):
                return empty_list

            if isinstance(media_data_obj.parent_obj, media.Folder) \
            and (
                operation_type == 'sim' \
                or operation_type == 'custom_sim' \
                or operation_type == 'classic_sim'
            ) and self.app_obj.operation_sim_shortcut_flag \
            and recursion_flag \
            and media_data_obj.file_name \
            and not media_data_obj.live_mode \
            and ttutils.find_thumbnail(self.app_obj, media_data_obj):
                return empty_list

            if custom_flag \
            and self.custom_dl_obj \
            and self.custom_dl_obj.dl_by_video_flag:

                if self.custom_dl_obj.dl_precede_flag \
                and self.custom_dl_obj.dl_if_subs_flag \
                and (
                    not media_data_obj.subs_list \
                    or (
                        self.custom_dl_obj.dl_if_subs_list \
                        and not ttutils.match_subs(
                            self.custom_dl_obj,
                            media_data_obj.subs_list,
                        )
                    )
                ):
                    return empty_list

                elif (
                    self.custom_dl_obj.ignore_stream_flag \
                    and media_data_obj.live_mode
                ) or (
                    self.custom_dl_obj.ignore_old_stream_flag \
                    and media_data_obj.was_live_flag
                ) or (
                    self.custom_dl_obj.dl_if_stream_flag \
                    and not media_data_obj.live_mode
                ) or (
                    self.custom_dl_obj.dl_if_old_stream_flag \
                    and not media_data_obj.was_live_flag
                ):
                    return empty_list

        # Don't download videos in channels/playlists/folders which have been
        #   marked unavailable, because their external directory is not
        #   accessible
        if isinstance(media_data_obj, media.Video):
            if media_data_obj.parent_obj.dbid \
            in self.app_obj.container_unavailable_dict:
                return empty_list

        elif not isinstance(media_data_obj, media.Video) \
        and media_data_obj.dbid in self.app_obj.container_unavailable_dict:
            return empty_list

        # Don't simulated downloads of video in channels/playlists/folders
        #   whose whose .dl_no_db_flag is set
        if (operation_type == 'sim' or operation_type == 'custom_sim') \
        and (
            (
                isinstance(media_data_obj, media.Video) \
                and media_data_obj.parent_obj.dl_no_db_flag
            ) or (
                not isinstance(media_data_obj, media.Video) \
                and media_data_obj.dl_no_db_flag
            )
        ):
            return empty_list

        # Don't create a download.DownloadItem object if checking/download is
        #   disabled for the media data object
        if not isinstance(media_data_obj, media.Video) \
        and media_data_obj.dl_disable_flag:
            return empty_list

        # Don't create a download.DownloadItem object for a media.Folder,
        #   obviously
        # Don't create a download.DownloadItem object for a media.Channel or
        #   media.Playlist during a custom download in which videos are to be
        #   downloaded independently
        if (
            isinstance(media_data_obj, media.Video)
            and custom_flag
            and (
                (self.custom_dl_obj and self.custom_dl_obj.dl_by_video_flag) \
                or media_data_obj.dbid in self.app_obj.temp_stamp_buffer_dict \
                or media_data_obj.dbid in self.app_obj.temp_slice_buffer_dict
            )
        ) or (
            isinstance(media_data_obj, media.Video)
            and (
                not custom_flag \
                or (
                    self.custom_dl_obj \
                    and not self.custom_dl_obj.dl_by_video_flag
                )
            )
        ) or (
            (
                isinstance(media_data_obj, media.Channel) \
                or isinstance(media_data_obj, media.Playlist)
            ) and (
                not custom_flag \
                or (
                    self.custom_dl_obj \
                    and not self.custom_dl_obj.dl_by_video_flag
                )
            )
        ):
            # (Broadcasting livestreams should always take priority over
            #   everything else)
            if isinstance(media_data_obj, media.Video) \
            and media_data_obj.live_mode == 2:

                broadcast_flag = True
                # For a broadcasting livestream, we create additional workers
                #   if required, possibly bypassing the limit specified by
                #   mainapp.TartubeApp.num_worker_default
                if self.app_obj.download_manager_obj:
                    self.app_obj.download_manager_obj.create_bypass_worker()

            else:

                broadcast_flag = False

            # Create a new download.DownloadItem object...
            self.download_item_count += 1
            download_item_obj = DownloadItem(
                self.download_item_count,
                media_data_obj,
                scheduled_obj,
                options_manager_obj,
                operation_type,
                ignore_limits_flag,
            )

            # ...and add it to our lists
            return_list.append(download_item_obj)

            if broadcast_flag:
                self.download_item_list.insert(0, download_item_obj.item_id)
            elif priority_flag:
                self.temp_item_list.append(download_item_obj.item_id)
            else:
                self.download_item_list.append(download_item_obj.item_id)

            self.download_item_dict[download_item_obj.item_id] \
            = download_item_obj

            # Keep track of any media.Scheduled objects involved in the
            #   current download operation
            if scheduled_obj is not None \
            and not scheduled_obj in self.scheduled_list:
                self.scheduled_list.append(scheduled_obj)

        # Call this function recursively for any child media data objects in
        #   the following situations:
        #   1. A media.Folder object has children
        #   2. A media.Channel/media.Playlist object has child media.Video
        #       objects, and this is a custom download in which videos are to
        #       be downloaded independently of their channel/playlist
        if isinstance(media_data_obj, media.Folder) \
        or (
            not isinstance(media_data_obj, media.Video)
            and custom_flag
            and self.custom_dl_obj
            and self.custom_dl_obj.dl_by_video_flag
        ):
            for child_obj in media_data_obj.child_list:
                return_list += self.create_item(
                    child_obj,
                    scheduled_obj,
                    operation_type,
                    priority_flag,
                    ignore_limits_flag,
                    True,                   # Recursion
                )

        # Procedure complete
        return return_list


    def create_dummy_item(self, media_data_obj):

        """Called by self.__init__() only, when the download operation was
        launched from the Classic Mode tab (this function is not called
        recursively).

        Creates a downloads.DownloadItem object for each dummy media.Video
        object.

        Adds the resulting downloads.DownloadItem object to this object's IVs.

        Args:

            media_data_obj (media.Video): A media data object

        Return values:

            The downloads.DownloadItem object created

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2896 create_dummy_item')

        if media_data_obj.options_obj is not None:
            # (Download options specified by the Drag and Drop tab)
            options_manager_obj = media_data_obj.options_obj
        elif self.app_obj.classic_options_obj is not None:
            options_manager_obj = self.app_obj.classic_options_obj
        else:
            options_manager_obj = self.app_obj.general_options_obj

        # Create a new download.DownloadItem object...
        self.download_item_count += 1
        download_item_obj = DownloadItem(
            media_data_obj.dbid,
            media_data_obj,
            None,                       # media.Scheduled object
            options_manager_obj,
            self.operation_type,        # 'classic_real'. 'classic_sim' or
                                        #   'classic_custom'
            False,                      # ignore_limits_flag
        )

        # ...and add it to our list
        self.download_item_list.append(download_item_obj.item_id)
        self.download_item_dict[download_item_obj.item_id] = download_item_obj

        # Procedure complete
        return download_item_obj


    @synchronise(_SYNC_LOCK)
    def fetch_next_item(self):

        """Called by downloads.DownloadManager.run().

        Based on DownloadList.fetch_next().

        Return values:

            The next downloads.DownloadItem object, or None if there are none
                left

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2941 fetch_next_item')

        if not self.prevent_fetch_flag:

            # In case of any recent calls to self.create_item(), which want to
            #   place new DownloadItems at the beginning of the queue, then
            #   merge the temporary queue into the main one
            if self.temp_item_list:
                self.download_item_list \
                = self.temp_item_list + self.download_item_list

            for item_id in self.download_item_list:
                this_item = self.download_item_dict[item_id]

                # Don't return an item that's marked as
                #   formats.MAIN_STAGE_ACTIVE
                if this_item.stage == formats.MAIN_STAGE_QUEUED:
                    return this_item

        return None


    @synchronise(_SYNC_LOCK)
    def is_queuing(self, item_id):

        """Called by mainwin.MainWin.progress_list_popup_menu(), etc.

        Checks whether the specified DownloadItem object is waiting in the
        queue (i.e. waiting to start checking/downloading).

        Args:

            item_id (int): The .item_id of a downloads.DownloadItem object;
                should be a key in self.download_item_dict

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 2979 is_queuing')

        if item_id in self.download_item_dict:
            item_obj = self.download_item_dict[item_id]
            if item_obj.stage == formats.MAIN_STAGE_QUEUED:
                return True

        return False


    @synchronise(_SYNC_LOCK)
    def move_item_to_bottom(self, download_item_obj):

        """Called by mainwin.MainWin.on_progress_list_dl_last().

        Moves the specified DownloadItem object to the end of
        self.download_item_list, so it is assigned a DownloadWorker last
        (after all other DownloadItems).

        Args:

            download_item_obj (downloads.DownloadItem): The download item
                object to move

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3006 move_item_to_bottom')

        # Move the item to the bottom (end) of the list
        if download_item_obj is None \
        or not download_item_obj.item_id in self.download_item_list:
            return
        else:
            self.download_item_list.append(
                self.download_item_list.pop(
                    self.download_item_list.index(download_item_obj.item_id),
                ),
            )


    @synchronise(_SYNC_LOCK)
    def move_item_to_top(self, download_item_obj):

        """Called by mainwin.MainWin.on_progress_list_dl_next().

        Moves the specified DownloadItem object to the start of
        self.download_item_list, so it is the next item to be assigned a
        DownloadWorker.

        Args:

            download_item_obj (downloads.DownloadItem): The download item
                object to move

        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3037 move_item_to_top')

        # Move the item to the top (beginning) of the list
        if download_item_obj is None \
        or not download_item_obj.item_id in self.download_item_list:
            return
        else:
            self.download_item_list.insert(
                0,
                self.download_item_list.pop(
                    self.download_item_list.index(download_item_obj.item_id),
                ),
            )


    @synchronise(_SYNC_LOCK)
    def prevent_fetch_new_items(self):

        """Called by DownloadManager.stop_download_operation_soon().

        Sets the flag that prevents calls to self.fetch_next_item() from
        fetching anything new, which allows the download operation to stop as
        soon as any ongoing video downloads have finished.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3063 prevent_fetch_new_items')

        self.prevent_fetch_flag = True


    @synchronise(_SYNC_LOCK)
    def set_final_item(self, item_id):

        """Called by mainwin.MainWin.on_progress_list_stop_soon(), etc.

        After the specified DownloadItem object is assigned to a worker, no
        more DownloadItem objects are assigned to a worker (i.e. do not start
        to check/download).
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3079 set_final_item')

        if item_id in self.download_item_dict:
            self.final_item_id = item_id

        else:
            GObject.timeout_add(
                0,
                app_obj.system_error,
                318,
                _('Unrecognised download item ID'),
            )


    def reorder_master_slave(self):

        """Called by self.__init__() after the calls to self.create_item() are
        finished.

        Some media data objects have an alternate download destination, for
        example, a playlist ('slave') might download its videos into the
        directory used by a channel ('master').

        This can increase the length of the operation, because a 'slave' won't
        start until its 'master' is finished.

        Make sure all designated 'masters' are handled before 'slaves' (a media
        media data object can't be both a master and a slave).

        Even if this doesn't reduce the time the 'slaves' spend waiting to
        start, it at least makes the download order predictable.
        """

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3113 reorder_master_slave')

        master_list = []
        other_list = []
        for item_id in self.download_item_list:
            download_item_obj = self.download_item_dict[item_id]

            if isinstance(download_item_obj.media_data_obj, media.Video) \
            or not download_item_obj.media_data_obj.slave_dbid_list:
                other_list.append(item_id)
            else:
                master_list.append(item_id)

        self.download_item_list = []
        self.download_item_list.extend(master_list)
        self.download_item_list.extend(other_list)


class DownloadItem(object):

    """Called by downloads.DownloadList.create_item() and
    .create_dummy_item().

    Based on the DownloadItem class in youtube-dl-gui.

    Python class used to track the download status of a media data object
    (media.Video, media.Channel, media.Playlist or media.Folder), one of many
    in a downloads.DownloadList object.

    Args:

        item_id (int): The number of downloads.DownloadItem objects created,
            used to give each one a unique ID

        media_data_obj (media.Video, media.Channel, media.Playlist,
            media.Folder): The media data object to be downloaded. When the
            download operation was launched from the Classic Mode tab, a dummy
            media.Video object

        scheduled_obj (media.Scheduled): The scheduled download object which
            wants to download media_data_obj (None if no scheduled download
            applies in this case)

        options_manager_obj (options.OptionsManager): The object which
            specifies download options for the media data object

        operation_type (str): The value that applies to this DownloadItem only
            (might be different from the default value stored in
            DownloadManager.operation_type)

        ignore_limits_flag (bool): Flag set to True if operation limits
            (mainapp.TartubeApp.operation_limit_flag) should be ignored

    """


    # Standard class methods


    def __init__(self, item_id, media_data_obj, scheduled_obj,
    options_manager_obj, operation_type, ignore_limits_flag):

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3176 __init__')

        # IV list - class objects
        # -----------------------
        # The media data object to be downloaded. When the download operation
        #   was launched from the Classic Mode tab, a dummy media.Video object
        self.media_data_obj = media_data_obj
        # The scheduled download object which wants to download media_data_obj
        #   (None if no scheduled download applies in this case)
        self.scheduled_obj = scheduled_obj
        # The object which specifies download options for the media data object
        self.options_manager_obj = options_manager_obj

        # IV list - other
        # ---------------
        # A unique ID for this object
        self.item_id = item_id
        # The current download stage
        self.stage = formats.MAIN_STAGE_QUEUED

        # The value that applies to this DownloadItem only (might be different
        #   from the default value stored in DownloadManager.operation_type)
        self.operation_type = operation_type
        # Shortcut flag to test the operation type; True for 'classic_sim',
        #   'classic_real' and 'classic_custom'; False for all other values
        self.operation_classic_flag = False         # (Set below)

        # Flag set to True if operation limits
        #   (mainapp.TartubeApp.operation_limit_flag) should be ignored
        self.ignore_limits_flag = ignore_limits_flag


        # Code
        # ----

        # Set the flag
        if operation_type == 'classic_sim' \
        or operation_type == 'classic_real' \
        or operation_type == 'classic_custom':
            self.operation_classic_flag = True


    # Set accessors


    def set_ignore_limits_flag(self):

        """Called by DownloadManager.apply_ignore_limits(), following a call
        from mainapp>TartubeApp.script_slow_timer_callback()."""

        if DEBUG_FUNC_FLAG:
            ttutils.debug_time('dld 3227 set_ignore_limits_flag')

        self.ignore_limits_flag = True
