"""Test barcode album lookups for the Open Subsonic provider."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from libopensonic.errors import ParameterError
from music_assistant_models.enums import ExternalID

from music_assistant.providers.opensubsonic.sonic_provider import OpenSonicProvider


def _provider(albums: list[MagicMock] | None) -> tuple[OpenSonicProvider, AsyncMock]:
    prov = OpenSonicProvider.__new__(OpenSonicProvider)
    prov.logger = MagicMock()
    prov.conn = MagicMock()
    prov.conn.search3 = AsyncMock(return_value=MagicMock(album=albums))
    get_album = AsyncMock(return_value="album")
    prov.get_album = get_album  # type: ignore[method-assign]
    return prov, get_album


async def test_barcode_is_searched_and_first_album_returned() -> None:
    """A barcode is searched as its UPC and the first album found is returned."""
    prov, get_album = _provider([MagicMock(id="ext-qobuz-album-0888880127631")])

    assert await prov.get_album_by_external_id("0888880127631", ExternalID.BARCODE) == "album"
    prov.conn.search3.assert_awaited_once_with(
        query="888880127631", artist_count=0, album_count=1, song_count=0
    )
    get_album.assert_awaited_once_with("ext-qobuz-album-0888880127631")


async def test_barcode_without_match_returns_none() -> None:
    """A server that finds nothing for the barcode yields no album."""
    prov, get_album = _provider([])

    assert await prov.get_album_by_external_id("0888880127631", ExternalID.BARCODE) is None
    get_album.assert_not_awaited()


async def test_search_error_returns_none() -> None:
    """A server rejecting the query yields no album."""
    prov, _ = _provider(None)
    prov.conn.search3 = AsyncMock(side_effect=ParameterError("bad query"))

    assert await prov.get_album_by_external_id("0888880127631", ExternalID.BARCODE) is None


@pytest.mark.parametrize(
    ("external_id", "external_id_type"),
    [
        ("12345", ExternalID.BARCODE),  # not a barcode
        ("0888880127631", ExternalID.MB_RELEASEGROUP),
    ],
)
async def test_other_ids_are_not_searched(external_id: str, external_id_type: ExternalID) -> None:
    """Invalid barcodes and other id types are not looked up."""
    prov, _ = _provider([MagicMock(id="x")])

    assert await prov.get_album_by_external_id(external_id, external_id_type) is None
    prov.conn.search3.assert_not_awaited()
