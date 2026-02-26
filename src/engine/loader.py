"""
src/engine/loader.py
====================
``loadDeck`` — the sole entry-point for turning a registered deck definition
into a list of ready-to-use :class:`~src.engine.models.Card` objects.

Asset URL convention
--------------------
The loader constructs image URLs without hardcoding any path or importing any
image.  Given ``DeckDefinition.asset_path = "/project/napolitane"``:

*Default artwork variant*::

    /project/napolitane/{suit}/{value}_{suit}.png
    # e.g. /project/napolitane/bastoni/7_bastoni.png

*Non-default artwork variant* (e.g. ``art_variant="vintage"``):

    /project/napolitane/vintage/{suit}/{value}_{suit}.png

This two-level layout lets you add alternate artwork sets simply by adding a
sub-directory inside the deck's asset root — no code changes required.

Validation
----------
For **filesystem paths** the loader verifies that each image file exists
before constructing the Card.  Pass ``skip_image_validation=True`` when the
assets live behind an HTTP URL or a CDN where ``Path.is_file()`` would be
meaningless.

Game-engine contract
--------------------
The returned ``list[Card]`` is the *only* thing the game engine ever sees.
It never reads ``card.image_url`` for logic decisions — that field belongs
exclusively to the rendering layer.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .exceptions import IncompleteDeckError, MissingCardImageError
from .models import Card
from .registry import DeckRegistry


def loadDeck(
    deck_name: str,
    art_variant: str = "default",
    *,
    skip_image_validation: bool = False,
) -> list[Card]:
    """
    Load all 40 cards for the deck registered under *deck_name*.

    For every ``(suit, value)`` pair declared in the
    :class:`~src.engine.models.DeckDefinition` the function:

    1. Builds a deterministic image URL via :func:`_build_image_url`.
    2. Validates the file exists on disk (unless *skip_image_validation* or
       the path is an HTTP URL).
    3. Constructs an immutable :class:`~src.engine.models.Card`.

    The result is always ordered: outer loop = suits (in definition order),
    inner loop = values (in definition order).

    Parameters
    ----------
    deck_name:
        Key under which the deck was registered via
        :py:meth:`~src.engine.registry.DeckRegistry.register`.
    art_variant:
        Selects an alternate artwork set declared in the definition's
        ``art_variants`` tuple.  Defaults to ``"default"``.
    skip_image_validation:
        When ``True``, bypass the filesystem existence check.  Use this for
        remote / CDN URLs or in test environments with mock asset paths.

    Returns
    -------
    list[Card]
        Exactly 40 :class:`~src.engine.models.Card` objects.

    Raises
    ------
    DeckNotFoundError
        If *deck_name* is not in the registry.
    ValueError
        If *art_variant* is not declared in the definition.
    MissingCardImageError
        If a required image file is missing on the local filesystem.
    IncompleteDeckError
        If the produced card list has a count other than 40 (logic guard).
    """
    definition = DeckRegistry.get(deck_name)  # raises DeckNotFoundError

    if art_variant not in definition.art_variants:
        raise ValueError(
            f"Art variant '{art_variant}' is not declared for deck "
            f"'{deck_name}'.  Available variants: {list(definition.art_variants)}"
        )

    is_local = _is_local_path(definition.asset_path)
    validate_images = is_local and not skip_image_validation

    cards: list[Card] = []

    for suit in definition.suits:
        for value in definition.values:
            image_url = _build_image_url(
                definition.asset_path, suit, value, art_variant
            )

            if validate_images:
                _validate_local_image(image_url, suit, value)

            cards.append(
                Card(
                    suit=suit,
                    value=value,
                    id=f"{deck_name}::{suit}::{value}",
                    image_url=image_url,
                )
            )

    # Integrity guard — should never fire if DeckDefinition was registered
    # correctly, but catches any future discrepancy between definition and loop.
    if len(cards) != definition.expected_card_count:
        raise IncompleteDeckError(
            deck_name, definition.expected_card_count, len(cards)
        )

    return cards


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_image_url(
    asset_path: str,
    suit: str,
    value: int,
    art_variant: str,
) -> str:
    """
    Construct the fully-qualified image URL for a single card.

    Layout
    ------
    ``"default"`` variant::

        {asset_path}/{suit}/{value}_{suit}.png

    Any other variant::

        {asset_path}/{art_variant}/{suit}/{value}_{suit}.png

    Parameters
    ----------
    asset_path:
        Deck root (filesystem path or URL base), with or without trailing
        slash — normalised internally.
    suit, value:
        Card identity.
    art_variant:
        Active artwork variant key.
    """
    base = asset_path.rstrip("/")
    filename = f"{value}_{suit}.png"

    if art_variant == "default":
        return f"{base}/{suit}/{filename}"

    return f"{base}/{art_variant}/{suit}/{filename}"


def _is_local_path(asset_path: str) -> bool:
    """
    Return ``True`` when *asset_path* refers to a local filesystem path.

    A path is considered local when its URL scheme is ``""`` (no scheme) or
    ``"file"``.  Anything else (``http``, ``https``, ``s3``, …) is treated
    as a remote URL and skips filesystem validation.
    """
    scheme = urlparse(asset_path).scheme
    return scheme in ("", "file")


def _validate_local_image(url: str, suit: str, value: int) -> None:
    """
    Raise :class:`~src.engine.exceptions.MissingCardImageError` when the
    file at *url* does not exist on the local filesystem.

    Handles both plain paths and ``file://`` URIs.
    """
    path = Path(url[7:]) if url.startswith("file://") else Path(url)
    if not path.is_file():
        raise MissingCardImageError(suit, value, url)
