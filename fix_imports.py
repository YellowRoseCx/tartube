import sys

def fix_file(filename, import_lines):
    with open(filename, 'r') as f:
        content = f.read()

    # The original headers we want to keep at the top
    shebang = "#!/usr/bin/env python3\n"
    encoding = "# -*- coding: utf-8 -*-\n"

    # Remove existing custom imports we added at the very top (and the duplicated ones)
    for imp in import_lines:
        content = content.replace(imp + "\n", "")

    # Also remove any rogue shebangs/encodings in the middle of the file
    content = content.replace(shebang, "")
    content = content.replace(encoding, "")

    # Reconstruct the correct file structure
    final_content = shebang + encoding
    for imp in import_lines:
        final_content += imp + "\n"
    final_content += "\n" + content.lstrip()

    with open(filename, 'w') as f:
        f.write(final_content)

managers_imports = [
    "from .queue import DownloadItem",
    "from .utils import CustomDLManager, PipeReader",
    "from .workers.video import VideoDownloader",
    "from .workers.clip import ClipDownloader",
    "from .workers.stream import StreamDownloader",
    "from .workers.json_fetcher import JSONFetcher, MiniJSONFetcher"
]

utils_imports = [
    "from .queue import DownloadItem"
]

worker_imports = [
    "from ..queue import DownloadItem",
    "from ..utils import PipeReader"
]

fix_file("tartube/downloads/managers.py", managers_imports)
fix_file("tartube/downloads/utils.py", utils_imports)
fix_file("tartube/downloads/workers/video.py", worker_imports)
fix_file("tartube/downloads/workers/clip.py", worker_imports)
fix_file("tartube/downloads/workers/stream.py", worker_imports)
fix_file("tartube/downloads/workers/json_fetcher.py", worker_imports)
