from __future__ import annotations

import hashlib
import logging

import requests as http_requests
from flask import Blueprint, jsonify, session

import ckan.lib.helpers as h
import ckan.plugins.toolkit as tk
from ckan.common import _, current_user

from ckanext.feedback import config
from ckanext.feedback import model as feedback_model

log = logging.getLogger(__name__)

feedback_blueprint = Blueprint(
    "feedback",
    __name__,
    url_prefix="/dataset/<package_id>/feedback",
)


def _ip_hash() -> str:
    ip = (
        tk.request.access_route[0]
        if tk.request.access_route
        else tk.request.remote_addr
    )
    return hashlib.sha256(ip.encode()).hexdigest()


def _stash_form_state(errors: list[dict], form_data: dict) -> None:
    """Stash structured validation errors and the submitted form values
    so the form template can render them inline after the redirect.

    Both keys are popped (not read) by their respective template helpers,
    so the data only survives one render — same lifecycle as a flash message.
    """
    session["_feedback_form_errors"] = errors
    session["_feedback_form_data"] = form_data


@feedback_blueprint.route("/rate", methods=["POST"])
def rate(package_id: str):
    rating = tk.request.form.get("rating", type=int)
    if not rating or rating < 1 or rating > 5:
        return jsonify({"error": "Invalid rating"}), 400

    # Verify the package exists.
    try:
        tk.get_action("package_show")({}, {"id": package_id})
    except tk.ObjectNotFound:
        return jsonify({"error": "Dataset not found"}), 404

    ip_hash = _ip_hash()
    user_id = current_user.name if current_user.is_authenticated else None

    feedback_model.upsert_rating(package_id, ip_hash, user_id, rating)
    avg = feedback_model.get_average_rating(package_id)

    return jsonify({
        "average": avg["average"],
        "count": avg["count"],
        "user_rating": rating,
    })


@feedback_blueprint.route("/submit", methods=["POST"])
def submit(package_id: str):
    # Verify the package exists.
    try:
        pkg = tk.get_action("package_show")({}, {"id": package_id})
    except tk.ObjectNotFound:
        tk.abort(404, _("Dataset not found"))

    form_data = {
        "author_name": tk.request.form.get("author_name", "").strip(),
        "author_email": tk.request.form.get("author_email", "").strip(),
        "subject_type": tk.request.form.get("subject_type", "").strip(),
        "reason": tk.request.form.get("reason", "").strip(),
        "body": tk.request.form.get("body", "").strip(),
    }

    errors: list[dict] = []
    if not form_data["subject_type"]:
        errors.append({
            "field": "feedback-subject-type",
            "message": _("Please choose what describes you."),
        })
    if not form_data["reason"]:
        errors.append({
            "field": "feedback-reason",
            "message": _("Please choose a reason for your feedback."),
        })
    if not form_data["body"]:
        errors.append({
            "field": "feedback-body",
            "message": _("Please enter your feedback."),
        })

    if errors:
        _stash_form_state(errors, form_data)
        return h.redirect_to("dataset.read", id=package_id)

    # reCAPTCHA verification.
    secret = config.recaptcha_secret_key()
    if secret:
        recaptcha_response = tk.request.form.get("g-recaptcha-response", "")
        recaptcha_failed = False
        try:
            resp = http_requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": secret, "response": recaptcha_response},
                timeout=10,
            )
            if not resp.json().get("success"):
                recaptcha_failed = True
        except http_requests.RequestException:
            log.exception("reCAPTCHA verification request failed")
            recaptcha_failed = True

        if recaptcha_failed:
            _stash_form_state(
                [{
                    "field": "feedback-recaptcha",
                    "message": _("reCAPTCHA verification failed. Please try again."),
                }],
                form_data,
            )
            return h.redirect_to("dataset.read", id=package_id)

    user_id = current_user.name if current_user.is_authenticated else None

    feedback_model.create_submission(
        package_id=package_id,
        user_id=user_id,
        author_name=form_data["author_name"] or None,
        author_email=form_data["author_email"] or None,
        subject_type=form_data["subject_type"],
        reason=form_data["reason"],
        body=form_data["body"],
    )

    # Email notification.
    recipients = config.email_recipients()
    if recipients:
        _send_notification(
            pkg,
            form_data["subject_type"],
            form_data["reason"],
            form_data["body"],
            form_data["author_name"] or None,
            form_data["author_email"] or None,
        )

    h.flash_success(_("Thank you for your feedback!"))
    return h.redirect_to("dataset.read", id=package_id)


def _send_notification(
    pkg: dict,
    subject_type: str,
    reason: str,
    body: str,
    author_name: str | None,
    author_email: str | None,
):
    from ckan.lib.mailer import mail_recipient

    dataset_title = pkg.get("title") or pkg.get("name")
    subject = _("User sent feedback for {title}").format(title=dataset_title)
    mail_body = (
        f"Hello,\n\nYou got feedback from {author_name or 'Anonymous'} ({author_email or 'Not provided'}), {subject_type}\n\n"
        f"Dataset: {dataset_title}\n"
        f"Reason for feedback: {reason}\n\n"
        f"Feedback:\n{body}\n\n"
        f"URL: {h.url_for('dataset.read', id=pkg['name'], _external=True)}\n\n"
        f"Have a good day\n"
    )

    for email in config.email_recipients():
        try:
            mail_recipient("Open Data and Information Portal", email, subject, mail_body)
        except Exception:
            log.exception("Failed to send feedback notification to %s", email)