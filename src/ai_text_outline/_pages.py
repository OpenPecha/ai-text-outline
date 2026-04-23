"""Page mapping and image fetching from BDRC services."""

from __future__ import annotations

import base64
import os

import requests


BDRC_API_BASE_URL = "https://bec-otapi.bdrc.io/api/v1"
IIIF_BASE_URL = "https://iiif.bdrc.io"


def get_volume_pages(
    volume_id: str,
    api_base_url: str | None = None,
) -> tuple[str, list[dict]]:
    """Fetch page list for a volume from the BDRC backend API.

    Args:
        volume_id: Full volume identifier (e.g. W1KG16648_I4PD2559_0459be_google_books).
        api_base_url: Override for the API base URL.

    Returns:
        Tuple of (vol_id, pages) where vol_id is the BDRC volume ID (e.g. I4PD2559)
        and pages is a list of dicts with keys: cstart, cend, pnum, pname.

    Raises:
        RuntimeError: If the API call fails.
    """
    base = api_base_url or os.environ.get("BDRC_API_BASE_URL", BDRC_API_BASE_URL)
    url = f"{base}/volumes/{volume_id}"
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch volume {volume_id}: HTTP {resp.status_code}"
        )
    data = resp.json()
    vol_id = data.get("vol_id", "")
    return vol_id, data.get("pages", [])


def find_pages_for_range(
    pages: list[dict],
    char_start: int,
    char_end: int,
) -> list[dict]:
    """Find pages that overlap with a character range.

    Args:
        pages: List of page dicts with cstart/cend.
        char_start: Start character index.
        char_end: End character index.

    Returns:
        Subset of pages overlapping [char_start, char_end], sorted by cstart.
    """
    overlapping = [
        p for p in pages
        if p["cend"] >= char_start and p["cstart"] <= char_end
    ]
    return sorted(overlapping, key=lambda p: p["cstart"])


def fetch_page_image(
    vol_id: str,
    pname: str,
    iiif_api_key: str,
    max_width: int = 1024,
) -> bytes:
    """Fetch a single page image from the IIIF service.

    Args:
        vol_id: BDRC volume ID (e.g. I4PD2559).
        pname: Page image filename (e.g. I4PD25590003.jpg).
        iiif_api_key: API key for IIIF authentication.
        max_width: Maximum image width in pixels.

    Returns:
        JPEG image bytes.

    Raises:
        RuntimeError: If the image fetch fails.
    """
    b64_key = base64.b64encode(iiif_api_key.encode()).decode()
    url = f"{IIIF_BASE_URL}/bdr:{vol_id}::{pname}/full/{max_width},/0/default.jpg"
    headers = {"Authorization": f"XBdrcKey {b64_key}"}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch image {pname}: HTTP {resp.status_code}"
        )
    return resp.content


def fetch_toc_page_images(
    volume_id: str,
    char_start: int,
    char_end: int,
    iiif_api_key: str | None = None,
    max_width: int = 1024,
    max_pages: int = 15,
    vol_id: str | None = None,
    pages: list[dict] | None = None,
) -> list[bytes]:
    """Fetch page images covering a character range.

    End-to-end: fetches volume pages from API (unless pre-fetched ones are
    supplied), finds overlapping pages, downloads images from IIIF.

    Args:
        volume_id: Full volume identifier.
        char_start: Start of character range (e.g. ToC start).
        char_end: End of character range (e.g. ToC end).
        iiif_api_key: IIIF API key. Falls back to IIIF_API_KEY env var.
        max_width: Maximum image width in pixels.
        max_pages: Maximum number of page images to fetch (prevents excessive downloads).
        vol_id: Optional pre-fetched BDRC volume id (from get_volume_pages).
            When provided with pages, skips the volume API call.
        pages: Optional pre-fetched page list (from get_volume_pages).
            When provided with vol_id, skips the volume API call.

    Returns:
        List of JPEG image bytes in page order.
    """
    api_key = iiif_api_key or os.environ.get("IIIF_API_KEY")
    if not api_key:
        return []

    if vol_id is None or pages is None:
        vol_id, pages = get_volume_pages(volume_id)
    if not pages or not vol_id:
        return []

    toc_pages = find_pages_for_range(pages, char_start, char_end)
    if not toc_pages:
        return []

    toc_pages = toc_pages[:max_pages]

    images = []
    for page in toc_pages:
        try:
            img_bytes = fetch_page_image(
                vol_id, page["pname"], api_key, max_width=max_width
            )
            images.append(img_bytes)
        except RuntimeError:
            continue

    return images
