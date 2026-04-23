# Changelog

## [0.8.0] — 2026-04-23

### Added
- **Vision-enhanced ToC path** (`_get_image_bounded_toc_end`): uses BDRC IIIF page images to
  identify where the ToC ends rather than relying on a fixed 5-page cap.
- **No-marker chapter detection** (`_find_short_line_pages` + `call_gemini_for_no_marker`):
  falls back to a Gemini vision pass when no དཀར་ཆག ToC marker is present, enabling
  extraction from manuscripts without an explicit table of contents.
- **`_pages.py`** — new module for BDRC volume page mapping and IIIF image fetching.
- New `volume_id` argument on `extract_toc_indices` to enable the IIIF-backed image flow.
- `IIIF_API_KEY` environment variable support for authenticated BDRC requests.

### Changed
- Upgraded Gemini model to `gemini-2.5-flash`.
- Breakpoints are now refined to the exact title-start character position
  (not the preceding page-marker position) for higher index accuracy.

### Fixed
- CI workflow: removed non-existent `[all]` install extra (`pip install ".[dev]"` only).

## [0.7.0]

- Refine breakpoints to title start positions.

## [0.6.0]

- Return both `breakpoints` and `toc` dict from `extract_toc_indices`.

## [0.5.0]

- Initial public release with page-number regex matching.
