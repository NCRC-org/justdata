"""Reference ids for user-facing errors (spec 04 A3).

Users never see raw exception text. They see a short message and a reference
id; the same id is written to the server log next to the real error and
traceback, so staff can find it in Cloud Logging.
"""

import traceback
import uuid
from typing import Optional, Tuple

GENERIC_ERROR = "We couldn't complete this analysis."
REQUEST_ERROR = "We couldn't complete this request."


def new_ref() -> str:
    return uuid.uuid4().hex[:8]


def user_error(message: Optional[str] = None, exc: Optional[BaseException] = None,
               context: str = "") -> Tuple[str, str]:
    """Log the error under a new reference id; return (user_text, ref).

    `message` must be safe to show (written by us, never exception text);
    it defaults to GENERIC_ERROR. Pass the exception as `exc` so its
    traceback is logged, never shown.
    """
    ref = new_ref()
    shown = message or GENERIC_ERROR
    detail = f" {context}" if context else ""
    print(f"[ERROR] ref={ref}{detail}: {shown}")
    if exc is not None:
        print(f"[ERROR] ref={ref} traceback:\n"
              + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    return f"{shown} Reference: {ref}", ref
