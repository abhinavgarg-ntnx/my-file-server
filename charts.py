"""
Helm chart download from Artifactory.
"""

import logging
import os
import shutil
import tarfile

from config import ARTIFACTORY_URL, ARTIFACTORY_API_KEY

log = logging.getLogger(__name__)

try:
    import requests as req_lib
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

_HEADERS = {
    "Accept": "application/octet-stream",
    "X-JFrog-Art-Api": ARTIFACTORY_API_KEY,
}


def download_and_extract_chart(name, version, dest_dir):
    """Download a Helm chart .tgz from Artifactory and extract it.

    Returns:
        (extract_dir, None) on success or (None, error_message) on failure.
    """
    if not HAS_REQUESTS:
        return (
            None,
            "Python 'requests' library is not installed. Run: pip install requests",
        )

    chart_filename = f"{name}-{version}.tgz"
    url = ARTIFACTORY_URL.format(name=name, version=version)
    local_path = os.path.join(dest_dir, chart_filename)

    if os.path.exists(local_path):
        os.remove(local_path)

    log.info("Downloading chart %s-%s from Artifactory", name, version)
    resp = req_lib.get(url, headers=_HEADERS, timeout=120, verify=False)
    resp.raise_for_status()

    with open(local_path, "wb") as f:
        f.write(resp.content)
    log.info("Saved %s (%d bytes)", local_path, len(resp.content))

    extract_dir = os.path.join(dest_dir, f"{name}-{version}")
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)

    with tarfile.open(local_path, "r:gz") as tar:
        tar.extractall(path=extract_dir)

    log.info("Extracted to %s", extract_dir)
    return extract_dir, None
