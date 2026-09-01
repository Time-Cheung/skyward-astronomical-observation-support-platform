"""Helpers for transient, operator-defined observing targets.

The 2LHAASO catalogue remains immutable.  A user-created target is represented
only for the lifetime of a calculation and is never written back into that
catalogue.  Keeping the conventional compact J-name in one helper makes the
web form, HTML result and JSON API agree on the same default identifier.
"""
from __future__ import annotations

from math import floor


def temporary_target_name(ra_deg: float, dec_deg: float) -> str:
    """Return a predictable ``TMP JHHMM±DDMM`` name for J2000 coordinates.

    The format deliberately follows the minute-resolution convention used by
    the 2LHAASO source names.  Values are truncated rather than rounded, which
    prevents a value close to the next minute from unexpectedly changing the
    coordinate-derived identifier.  ``TMP`` makes it visually impossible to
    mistake a browser-created target for a catalogue entry.
    """
    # RA is bounded to [0, 360) by the request schema/form.  The modulo keeps
    # the formatter robust if this helper is reused independently.
    total_ra_minutes = int(floor((ra_deg % 360.0) / 15.0 * 60.0)) % (24 * 60)
    ra_hours, ra_minutes = divmod(total_ra_minutes, 60)

    # Dec may reach +/-90 degrees.  A sign is explicitly retained for +0 so
    # the output has the same unambiguous shape as an IAU-style source name.
    total_dec_minutes = int(floor(abs(dec_deg) * 60.0))
    dec_degrees, dec_minutes = divmod(total_dec_minutes, 60)
    sign = "+" if dec_deg >= 0.0 else "-"
    return f"TMP J{ra_hours:02d}{ra_minutes:02d}{sign}{dec_degrees:02d}{dec_minutes:02d}"


def normalise_temporary_target_name(
    supplied_name: str | None, ra_deg: float, dec_deg: float
) -> str:
    """Use a clean operator name, or fall back to the coordinate-derived one."""
    cleaned = " ".join((supplied_name or "").split())
    return cleaned or temporary_target_name(ra_deg, dec_deg)
