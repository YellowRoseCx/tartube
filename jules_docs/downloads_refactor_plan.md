# Refactoring Plan: `tartube/downloads.py`

## Overview
`downloads.py` is roughly 12,000 lines long and handles the core functionality of Tartube: managing downloads and interacting with external downloaders like `youtube-dl` and `yt-dlp`.

It contains 12 classes that manage different aspects of the download lifecycle, including threading managers (`DownloadManager`, `DownloadWorker`, `StreamManager`), data structures for queues (`DownloadList`, `DownloadItem`), and the actual wrappers for executing downloads (`VideoDownloader`, `ClipDownloader`, `StreamDownloader`, `JSONFetcher`).

## Refactoring Recommendations

This file is functionally cohesive (it's all about downloading) but is too large for a single file. The threading logic is mixed with the process execution logic and the queue data structures.

### 1. Extract Queue and Data Structures (`tartube/downloads/queue.py`)
- **Action:** Create a `tartube/downloads/` package directory.
- **Action:** Extract `DownloadList` and `DownloadItem` into `tartube/downloads/queue.py`. These classes simply represent the state of items waiting to be downloaded.

### 2. Extract Downloader Implementations (`tartube/downloads/workers/`)
The classes that actually execute `youtube-dl` or streamlink commands (`VideoDownloader`, `ClipDownloader`, `StreamDownloader`, `JSONFetcher`, `MiniJSONFetcher`) are massive because they construct complex subprocess arguments and parse output.
- **Action:** Create `tartube/downloads/workers/` (or `executors/`).
- **Action:** Extract `VideoDownloader` to `tartube/downloads/workers/video.py`. (This is nearly 4000 lines on its own and may need further splitting into argument generation and output parsing).
- **Action:** Extract `ClipDownloader` to `tartube/downloads/workers/clip.py`.
- **Action:** Extract `StreamDownloader` to `tartube/downloads/workers/stream.py`.
- **Action:** Extract `JSONFetcher` and `MiniJSONFetcher` to `tartube/downloads/workers/json_fetcher.py`.

### 3. Extract Thread Managers (`tartube/downloads/managers.py`)
The thread management classes oversee the queue and dispatch workers.
- **Action:** Extract `DownloadManager`, `DownloadWorker`, and `StreamManager` into `tartube/downloads/managers.py`.

### 4. Extract Utilities and Custom Managers (`tartube/downloads/utils.py`)
- **Action:** Extract `PipeReader` (used for reading subprocess output asynchronously) to a utility module.
- **Action:** Extract `CustomDLManager` to its own module, as it handles custom user-defined download commands.

## Execution Strategy
1. **Create Package Structure:** Convert `tartube/downloads.py` into a package: rename it to `tartube/downloads_old.py` (temporarily), create a `tartube/downloads/` directory, and add an `__init__.py`.
2. **Move Data Structures:** Start by moving `DownloadList` and `DownloadItem` as they have the fewest dependencies.
3. **Move Executors:** Move the `*Downloader` classes. These will rely on the queue items.
4. **Move Thread Managers:** Move the threading classes that tie it all together.
5. **Fix Imports:** Use `tartube/downloads/__init__.py` to re-export the classes so that `mainapp.py` and other modules don't need their import statements rewritten immediately (maintaining backward compatibility during the refactor).
