"""When a report's analysis ran, in Eastern time (triage T3; QA LS-058, X-012,
BZ-030; Jad's decision of 2026-11-17).

Exports used to stamp the moment of download, which hid how old a cached
report was. They now show the analysis time stored with the result
(metadata['generated_at'], written as datetime.now().isoformat() on Cloud
Run, so a naive value is UTC), converted to ET in NCRC style:
"Nov. 20, 2026" and "Nov. 20, 2026, 2:15 pm ET".
"""
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# AP style: these months are abbreviated with a specific date.
_AP_MONTHS = {1: "Jan.", 2: "Feb.", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July",
              8: "Aug.", 9: "Sept.", 10: "Oct.", 11: "Nov.", 12: "Dec."}


def _parse(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def analysis_time(metadata: Optional[Mapping[str, Any]]) -> datetime:
    """The stored analysis time (aware). Falls back to now only for a result
    stored without one."""
    metadata = metadata or {}
    for key in ("generated_at", "created_at"):
        dt = _parse(metadata.get(key))
        if dt is not None:
            return dt
    return datetime.now(timezone.utc)


def et_date(dt: datetime) -> str:
    """'Nov. 20, 2026' in ET."""
    local = dt.astimezone(ET)
    return f"{_AP_MONTHS[local.month]} {local.day}, {local.year}"


def et_time(dt: datetime) -> str:
    """'9 am ET', '2:15 pm ET'. Noon and midnight are written as words (AP)."""
    local = dt.astimezone(ET)
    if local.hour == 12 and local.minute == 0:
        return "noon ET"
    if local.hour == 0 and local.minute == 0:
        return "midnight ET"
    hour = local.hour % 12 or 12
    suffix = "am" if local.hour < 12 else "pm"
    minutes = f":{local.minute:02d}" if local.minute else ""
    return f"{hour}{minutes} {suffix} ET"


def et_stamp(dt: datetime) -> str:
    """'Nov. 20, 2026, 2:15 pm ET'."""
    return f"{et_date(dt)}, {et_time(dt)}"


def analysis_date(metadata) -> str:
    return et_date(analysis_time(metadata))


def analysis_stamp(metadata) -> str:
    return et_stamp(analysis_time(metadata))


def download_stamp() -> str:
    """Download file names: the download time in ET, labeled, e.g.
    '20261120_143705_ET'. File names keep the download time (Jad, 2026-11-20);
    the analysis time is inside the file."""
    return datetime.now(ET).strftime("%Y%m%d_%H%M%S") + "_ET"
