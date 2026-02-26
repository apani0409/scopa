"""
src/engine/metadata.py
======================
Utility for loading a deck's optional ``metadata.json`` descriptor.

The file is expected at the *root* of the deck's asset directory::

    napolitane/
        metadata.json   ← loaded by this module
        bastoni/
        coppe/
        oro/
        spade/

The JSON schema is intentionally permissive: only ``display_name``,
``origin``, and ``aspect_ratio`` are required; everything else has a
sensible default.  Unknown keys are silently ignored, which lets you
add richer metadata to the file without breaking older engine versions.

Future extensions
-----------------
* ``"artwork_variants"``  — list of available variant names
* ``"card_back_image"``   — path to the card-back asset
* ``"min_players"`` / ``"max_players"``
* ``"rules_url"``

Just add the keys to ``metadata.json``; the engine will ignore them
until you explicitly handle them here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import DeckMetadata


def load_metadata(deck_asset_path: str) -> Optional[DeckMetadata]:
    """
    Attempt to parse ``{deck_asset_path}/metadata.json`` into a
    :class:`~src.engine.models.DeckMetadata` instance.

    Parameters
    ----------
    deck_asset_path:
        Filesystem path to the deck's root asset directory
        (the same value stored in ``DeckDefinition.asset_path``).

    Returns
    -------
    DeckMetadata
        Populated instance when the file exists and is valid.
    None
        When the file does not exist (non-error: metadata is optional).

    Raises
    ------
    ValueError
        If the file exists but contains invalid JSON or is missing
        required keys (``display_name``, ``origin``, ``aspect_ratio``).
    """
    path = Path(deck_asset_path) / "metadata.json"

    if not path.is_file():
        return None

    try:
        raw: dict = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in '{path}': {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ValueError(
            f"'{path}' must contain a JSON object at the top level."
        )

    # ── Required keys ─────────────────────────────────────────────────────────
    required = {"display_name", "origin", "aspect_ratio"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(
            f"metadata.json at '{path}' is missing required keys: "
            f"{sorted(missing)}"
        )

    # ── Type coercions ────────────────────────────────────────────────────────
    try:
        aspect_ratio = float(raw["aspect_ratio"])
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"'aspect_ratio' in '{path}' must be a number, "
            f"got {raw['aspect_ratio']!r}."
        ) from exc

    return DeckMetadata(
        display_name=str(raw["display_name"]),
        origin=str(raw["origin"]),
        aspect_ratio=aspect_ratio,
        artwork_variant=str(raw.get("artwork_variant", "default")),
        description=str(raw.get("description", "")),
    )
