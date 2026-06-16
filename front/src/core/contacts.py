import base64

import requests
import streamlit as st


def fetch_avatar_b64(contact_id: str) -> str | None:
    cache_key = f"_avatar_b64_{contact_id}"
    if cache_key not in st.session_state:
        resp = requests.get(f"http://back:80/contact/{contact_id}/photo")
        st.session_state[cache_key] = (
            base64.b64encode(resp.content).decode() if resp.status_code == 200 else None
        )
    return st.session_state[cache_key]


def contact_avatar_html(b64: str | None, size: int = 32) -> str:
    if b64:
        return (
            f'<img src="data:image/jpeg;base64,{b64}" '
            f'style="width:{size}px;height:{size}px;border-radius:50%;'
            f'object-fit:cover;display:inline-block;vertical-align:middle;">'
        )
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background:#444;display:inline-flex;align-items:center;'
        f'justify-content:center;font-size:{size // 2}px;vertical-align:middle;">👤</div>'
    )


def contact_pill_html(contact: dict, size: int = 32) -> str:
    b64 = fetch_avatar_b64(contact["id"])
    avatar = contact_avatar_html(b64, size)
    name = contact.get("name", "")
    role = contact.get("role") or ""
    company = contact.get("company") or ""
    subtitle_parts = [p for p in [role, company] if p]
    subtitle = " · ".join(subtitle_parts)
    return (
        f'<div style="display:inline-flex;align-items:center;gap:8px;'
        f'padding:4px 10px 4px 6px;border:1px solid #444;border-radius:20px;'
        f'margin:2px 4px 2px 0;background:transparent;">'
        f"{avatar}"
        f'<div style="display:inline-flex;flex-direction:column;line-height:1.3;">'
        f'<span style="font-weight:600;font-size:13px;">{name}</span>'
        + (f'<span style="color:#888;font-size:11px;">{subtitle}</span>' if subtitle else "")
        + "</div></div>"
    )


def render_contact_pills(contacts: list[dict]) -> None:
    if not contacts:
        return
    pills = "".join(contact_pill_html(c) for c in contacts)
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:2px;margin-top:4px;">{pills}</div>',
        unsafe_allow_html=True,
    )
