"""Security-header middleware and header builders.

Reads header values from environment variables, validates them against
known-safe patterns, and falls back to secure defaults when invalid.
The ``SecurityHeadersMiddleware`` class applies all configured headers
to every response.
"""

import os
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.update(set_security_headers())
        return response


def set_security_headers() -> Dict[str, str]:
    """Build a dict of security headers from environment variables.

    Only headers whose env var is set are included. Each value is validated
    against a format pattern; invalid values are replaced with a safe default.
    """
    options = {}
    header_setters = {
        "CACHE_CONTROL": set_cache_control,
        "HSTS": set_hsts,
        "PERMISSIONS_POLICY": set_permissions_policy,
        "REFERRER_POLICY": set_referrer,
        "XCONTENT_TYPE": set_xcontent_type,
        "XDOWNLOAD_OPTIONS": set_xdownload_options,
        "XFRAME_OPTIONS": set_xframe,
        "XPERMITTED_CROSS_DOMAIN_POLICIES": set_xpermitted_cross_domain_policies,
        "CONTENT_SECURITY_POLICY": set_content_security_policy,
    }

    for env_var, setter in header_setters.items():
        value = os.environ.get(env_var, None)
        if value:
            header = setter(value)
            if header:
                options.update(header)

    return options


def set_hsts(value: str):
    """Set HTTP Strict Transport Security (HSTS) response header."""
    pattern = r"^max-age=(\d+)(;includeSubDomains)?(;preload)?$"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        value = "max-age=31536000;includeSubDomains"
    return {"Strict-Transport-Security": value}


def set_xframe(value: str):
    """Set X-Frame-Options response header."""
    pattern = r"^(DENY|SAMEORIGIN)$"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        value = "DENY"
    return {"X-Frame-Options": value}


def set_permissions_policy(value: str):
    """Set Permissions-Policy response header."""
    pattern = r"^(?:(accelerometer|autoplay|camera|clipboard-read|clipboard-write|fullscreen|geolocation|gyroscope|magnetometer|microphone|midi|payment|picture-in-picture|sync-xhr|usb|xr-spatial-tracking)=\((self)?\),?)*$"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        value = "none"
    return {"Permissions-Policy": value}


def set_referrer(value: str):
    """Set Referrer-Policy response header."""
    pattern = r"^(no-referrer|no-referrer-when-downgrade|origin|origin-when-cross-origin|same-origin|strict-origin|strict-origin-when-cross-origin|unsafe-url)$"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        value = "no-referrer"
    return {"Referrer-Policy": value}


def set_cache_control(value: str):
    """Set Cache-Control response header."""
    pattern = r"^(public|private|no-cache|no-store|must-revalidate|proxy-revalidate|max-age=\d+|s-maxage=\d+|no-transform|immutable)(,\s*(public|private|no-cache|no-store|must-revalidate|proxy-revalidate|max-age=\d+|s-maxage=\d+|no-transform|immutable))*$"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        value = "no-store, max-age=0"
    return {"Cache-Control": value}


def set_xdownload_options(value: str):
    """Set X-Download-Options response header."""
    if value != "noopen":
        value = "noopen"
    return {"X-Download-Options": value}


def set_xcontent_type(value: str):
    """Set X-Content-Type-Options response header."""
    if value != "nosniff":
        value = "nosniff"
    return {"X-Content-Type-Options": value}


def set_xpermitted_cross_domain_policies(value: str):
    """Set X-Permitted-Cross-Domain-Policies response header."""
    pattern = r"^(none|master-only|by-content-type|by-ftp-filename)$"
    match = re.match(pattern, value, re.IGNORECASE)
    if not match:
        value = "none"
    return {"X-Permitted-Cross-Domain-Policies": value}


def set_content_security_policy(value: str):
    """Set Content-Security-Policy response header (pass-through, no validation)."""
    return {"Content-Security-Policy": value}
