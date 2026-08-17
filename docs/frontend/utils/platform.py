"""
platform.py — small platform helpers used by the TUI.

Everything here is intentionally side-effect-isolated: the functions
return ``(ok, message)`` tuples so the calling widget can show a
toast / status line / footer banner instead of raising into the
caller. The pilot tests import this module and patch the module-level
functions to assert behaviour without actually opening the user's
browser or touching the clipboard.

Functions:
    source_type_from_url(url)               -> str  ("filing"|"news"|"macro"|"web")
    open_in_browser(url)                    -> (bool, str)
    copy_to_clipboard(text)                 -> (bool, str)

The source-type heuristic is intentionally simple — host-only, no
fancy path inspection. We can grow the catalog as the connector set
grows (research/connectors/*.py). Unknown hosts fall back to "web".
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# source type heuristic
# ---------------------------------------------------------------------------
_FILING_HOSTS = {"sec.gov", "www.sec.gov"}
_NEWS_HOSTS = {
    "reuters.com", "www.reuters.com",
    "bloomberg.com", "www.bloomberg.com",
    "wsj.com", "www.wsj.com",
    "ft.com", "www.ft.com", "financialtimes.com",
    "cnbc.com", "www.cnbc.com",
    "nytimes.com", "www.nytimes.com",
    "foxbusiness.com", "www.foxbusiness.com",
    "seekingalpha.com", "www.seekingalpha.com",
    "marketwatch.com", "www.marketwatch.com",
    "barrons.com", "www.barrons.com",
    "investors.com",
}
_MACRO_HOSTS = {
    "fred.stlouisfed.org",
    "federalreserve.gov", "www.federalreserve.gov",
    "bea.gov", "www.bea.gov",
    "home.treasury.gov",
    "bls.gov", "www.bls.gov",
    "census.gov", "www.census.gov",
}


def source_type_from_url(url: str) -> str:
    """Maps a URL to one of: ``filing``, ``news``, ``macro``, ``web``.

    Unknown hosts return ``web`` (the catch-all). Caller can show a
    neutral pill for those.
    """
    if not url:
        return "web"
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return "web"
    if not host:
        return "web"
    # Strip leading "www." for catalog hits; keep the original for
    # display purposes (handled by callers).
    bare = host[4:] if host.startswith("www.") else host
    if host in _FILING_HOSTS or bare in _FILING_HOSTS:
        return "filing"
    if host in _NEWS_HOSTS or bare in _NEWS_HOSTS:
        return "news"
    if host in _MACRO_HOSTS or bare in _MACRO_HOSTS:
        return "macro"
    # Suffix fallbacks for sites we recognise by their domain tail
    # (e.g. ``reuters.com`` matches already; we add a few common ones).
    for suffix in (".reuters.com", ".bloomberg.net", ".wsj.com", ".ft.com",
                  ".cnbc.com", ".seekingalpha.com", ".marketwatch.com"):
        if host.endswith(suffix):
            return "news"
    for suffix in (".stlouisfed.org", ".federalreserve.gov",
                  ".treasury.gov", ".bea.gov", ".bls.gov"):
        if host.endswith(suffix):
            return "macro"
    for suffix in (".sec.gov",):
        if host.endswith(suffix):
            return "filing"
    return "web"


# ---------------------------------------------------------------------------
# open in default browser
# ---------------------------------------------------------------------------
def open_in_browser(url: str) -> tuple[bool, str]:
    """Open *url* in the user's default browser.

    Returns ``(True, "")`` on success, ``(False, reason)`` on failure.
    Uses Python's standard-library ``webbrowser`` which dispatches to:
        - macOS:   ``open``       (built-in)
        - Linux:   ``xdg-open``   (most distros)
        - Windows: ``os.startfile``

    Falls back to a subprocess call if webbrowser refuses. Always
    returns a tuple so callers can render a toast on failure.
    """
    if not url:
        return False, "empty url"
    try:
        import webbrowser
        opened = webbrowser.open_new_tab(url)
        if opened:
            return True, ""
        # Some headless / sandbox environments report False but the
        # OS handler is fine. Try the platform-native fallback.
        ok, msg = _open_native(url)
        if ok:
            return True, ""
        return False, f"webbrowser refused ({msg or 'no handler'})"
    except Exception as e:
        # Last-ditch fallback to a subprocess.
        ok, msg = _open_native(url)
        if ok:
            return True, ""
        return False, f"{type(e).__name__}: {e} | fallback: {msg}"


def _open_native(url: str) -> tuple[bool, str]:
    """Platform-specific browser launch as a fallback."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", url])
            return True, ""
        if system == "Linux":
            for cmd in (["xdg-open"], ["wslview"]):
                if shutil.which(cmd[0]):
                    subprocess.Popen(cmd + [url])
                    return True, ""
            return False, "no xdg-open / wslview on PATH"
        if system == "Windows":
            # os.startfile is built-in; no extra cmd needed.
            os_startfile = getattr(os, "startfile", None)
            if os_startfile is not None:
                os_startfile(url)
                return True, ""
            return False, "no os.startfile"
        return False, f"no native launcher for {system}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# copy to clipboard
# ---------------------------------------------------------------------------
def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Copy *text* to the system clipboard.

    Returns ``(True, "")`` on success, ``(False, reason)`` on failure.

    Tries, in order:
        1. ``pyperclip`` (if installed) — cross-platform
        2. ``pbcopy`` (macOS)        — built-in
        3. ``xclip -selection clipboard`` (Linux X11)
        4. ``xsel --clipboard --input`` (Linux X11 fallback)
        5. ``clip`` (Windows)

    A failure returns with the reason so the caller can show a
    helpful toast like "clipboard unavailable — install xclip".
    """
    if not text:
        return False, "empty text"
    # 1. pyperclip (preferred — works on every platform if installed)
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        return True, ""
    except Exception:
        pass
    # 2–5. Platform fallbacks via subprocess.
    system = platform.system()
    enc = text.encode("utf-8")
    try:
        if system == "Darwin":
            if shutil.which("pbcopy"):
                subprocess.run(["pbcopy"], input=enc, check=True)
                return True, ""
            return False, "no pbcopy on PATH"
        if system == "Linux":
            for cmd in (["xclip", "-selection", "clipboard"],
                       ["xsel", "--clipboard", "--input"]):
                if shutil.which(cmd[0]):
                    subprocess.run(cmd, input=enc, check=True)
                    return True, ""
            return False, "no xclip / xsel — install one and retry"
        if system == "Windows":
            if shutil.which("clip"):
                subprocess.run(["clip"], input=enc, check=True)
                return True, ""
            return False, "no clip on PATH"
        return False, f"no clipboard tool for {system}"
    except subprocess.CalledProcessError as e:
        return False, f"{e.cmd[0]}: exit {e.returncode}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# Re-export at module level for clarity.
__all__ = ["source_type_from_url", "open_in_browser", "copy_to_clipboard"]
