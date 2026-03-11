"""
Shared review controls — accept/reject + rating + feedback widgets.
Used by Production Pipeline (inline review) and Drafts Review (full review).
"""
import streamlit as st

from src.services.creative_queries import (
    update_scenario_feedback,
    update_music_feedback,
    update_job_feedback,
)
from src.services.carousel_queries import update_carousel_feedback

STATUS_COLORS = {
    "draft": "blue",
    "unreviewed": "blue",
    "accepted": "green",
    "rejected": "red",
    "completed": "blue",
    "published": "violet",
    "validated": "green",
}


def _do_feedback(item_id: str, item_type: str, status: str, feedback: str, rating: int):
    """Dispatch feedback update to the right DB function."""
    fb = feedback if feedback else None
    if item_type == "scenario":
        update_scenario_feedback(item_id, status, feedback=fb, rating=rating)
    elif item_type == "music":
        update_music_feedback(item_id, status, feedback=fb, rating=rating)
    elif item_type == "video":
        update_job_feedback(item_id, status=status, feedback=fb, rating=rating)
    elif item_type == "carousel":
        update_carousel_feedback(item_id, status, feedback=fb, rating=rating)


def render_review_controls(item_id: str, item_type: str, current_status: str, key_prefix: str):
    """Render accept/reject + rating + feedback controls (full version for Drafts Review).

    item_type: 'scenario' | 'music' | 'video' | 'carousel'
    """
    already_reviewed = current_status in ("accepted", "rejected")

    if already_reviewed:
        color = STATUS_COLORS.get(current_status, "gray")
        st.markdown(f"Status: :{color}[{current_status.upper()}]")

    rating = st.slider(
        "Rating", 1, 5, 3, key=f"{key_prefix}_rating_{item_id}",
        help="Your quality assessment: 1 = poor, 5 = excellent. Used to improve future AI prompts.",
    )
    feedback_text = st.text_input(
        "Feedback",
        key=f"{key_prefix}_fb_{item_id}",
        placeholder="Optional — what's good or bad about this?",
    )

    col_accept, col_reject = st.columns(2)
    with col_accept:
        accept_label = "Accepted" if current_status == "accepted" else "Accept"
        if st.button(
            accept_label,
            key=f"{key_prefix}_accept_{item_id}",
            type="primary" if current_status != "accepted" else "secondary",
            use_container_width=True,
        ):
            _do_feedback(item_id, item_type, "accepted", feedback_text, rating)
            st.rerun()
    with col_reject:
        reject_label = "Rejected" if current_status == "rejected" else "Reject"
        if st.button(
            reject_label,
            key=f"{key_prefix}_reject_{item_id}",
            type="secondary",
            use_container_width=True,
        ):
            _do_feedback(item_id, item_type, "rejected", feedback_text, rating)
            st.rerun()


def render_inline_review(item_id: str, item_type: str, current_status: str, key_prefix: str,
                         on_accept_callback=None,
                         calendar_id: str = None, accept_creative_status: str = None):
    """Compact inline review for Production Pipeline — accept/reject with feedback.

    on_accept_callback: optional callable(item_id) invoked after accept (e.g. to reject siblings).
    calendar_id + accept_creative_status: if both set, advances creative_status on accept.
    Returns True if an action was taken.
    """
    is_accepted = current_status == "accepted"
    is_rejected = current_status == "rejected"

    if is_rejected:
        st.markdown(f":red[REJECTED]")
        return False

    if is_accepted:
        # Show accepted badge + compact reject option
        _ac, _rc = st.columns([3, 1])
        _ac.markdown(":green[ACCEPTED]")
        feedback_text = _rc.text_input(
            "fb", key=f"{key_prefix}_fb_{item_id}",
            placeholder="Reason", label_visibility="collapsed",
        )
        if _rc.button("Reject", key=f"{key_prefix}_rej_{item_id}",
                       use_container_width=True):
            if not feedback_text.strip():
                st.warning("Please add a reason before rejecting")
            else:
                _do_feedback(item_id, item_type, "rejected", feedback_text, 2)
                st.rerun()
        return False

    feedback_text = st.text_input(
        "Feedback",
        key=f"{key_prefix}_fb_{item_id}",
        placeholder="Why accept/reject? (required for reject)",
        label_visibility="collapsed",
    )
    col_a, col_r = st.columns(2)
    with col_a:
        if st.button("Accept", key=f"{key_prefix}_acc_{item_id}", type="primary",
                      use_container_width=True):
            _do_feedback(item_id, item_type, "accepted", feedback_text, 3)
            if on_accept_callback:
                on_accept_callback(item_id)
            if calendar_id and accept_creative_status:
                from src.services.editorial_queries import update_calendar_creative_status
                update_calendar_creative_status(calendar_id, accept_creative_status)
            st.rerun()
    with col_r:
        if st.button("Reject", key=f"{key_prefix}_rej_{item_id}",
                      use_container_width=True):
            if not feedback_text.strip():
                st.warning("Please add a reason before rejecting")
            else:
                _do_feedback(item_id, item_type, "rejected", feedback_text, 2)
                st.rerun()
    return False
