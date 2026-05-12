from __future__ import annotations

import hashlib

from flask import session

import ckan.plugins.toolkit as tk
from ckan.common import request

from ckanext.feedback import config, model as feedback_model


def _ip_hash() -> str:
    ip = request.access_route[0] if request.access_route else request.remote_addr
    return hashlib.sha256(ip.encode()).hexdigest()


def feedback_rating_avg(package_id: str) -> dict:
    return feedback_model.get_average_rating(package_id)


def feedback_user_rating(package_id: str) -> int | None:
    return feedback_model.get_user_rating(package_id, _ip_hash())


def feedback_recaptcha_site_key() -> str:
    return config.recaptcha_site_key()


def feedback_subject_types() -> list[str]:
    return config.subject_types()


def feedback_reasons() -> list[str]:
    return config.reasons()


def feedback_form_errors() -> list[dict]:
    """Return structured validation errors stashed by the submit view, then
    clear them. Each entry is `{"field": <input id>, "message": <text>}`.

    Pop semantics — same lifecycle as a flash message — so the errors only
    appear on the render that immediately follows the failed submit.
    """
    return session.pop("_feedback_form_errors", []) or []


def feedback_form_data() -> dict:
    """Return the form values from the failed submit so the template can
    repopulate the fields. Cleared on read."""
    return session.pop("_feedback_form_data", {}) or {}