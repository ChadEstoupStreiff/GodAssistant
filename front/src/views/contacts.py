import base64

import requests
import streamlit as st
from core.files import display_files, representation_mode_select
from utils import (
    generate_project_visual_markdown,
    generate_tag_visual_markdown,
    refractor_text_area,
    toast_for_rerun,
)

BACK = "http://back:80"


def _load_contacts():
    search = st.session_state.get("contact_search", "")
    url = f"{BACK}/contacts"
    if search:
        url += f"?search={search}"
    resp = requests.get(url)
    st.session_state.contacts_list = resp.json() if resp.status_code == 200 else []


def _get_contact(contact_id: str) -> dict:
    resp = requests.get(f"{BACK}/contacts/{contact_id}")
    return resp.json() if resp.status_code == 200 else {}


def _round_avatar_html(b64: str, size: int | None = None) -> str:
    if size is None:
        style = "width:100%;aspect-ratio:1/1;border-radius:50%;object-fit:cover;display:block;"
    else:
        style = f"width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;display:block;"
    return f'<img src="data:image/jpeg;base64,{b64}" style="{style}">'


def _fetch_avatar_b64(contact_id: str) -> str | None:
    resp = requests.get(f"{BACK}/contact/{contact_id}/photo")
    if resp.status_code == 200:
        return base64.b64encode(resp.content).decode()
    return None


@st.dialog("➕ New Contact", width="large")
def dialog_create_contact():
    name = st.text_input("Name *", placeholder="Full name")
    cols = st.columns(2)
    with cols[0]:
        email = st.text_input("Email", placeholder="email@example.com")
        company = st.text_input("Company", placeholder="Acme Corp")
    with cols[1]:
        phone = st.text_input("Phone", placeholder="+1 555 000 0000")
        role = st.text_input("Role", placeholder="Engineer")
    description = st.text_area("Description", placeholder="Short bio or notes about this contact")

    if st.button("Create", use_container_width=True, type="primary", disabled=not name.strip()):
        resp = requests.post(
            f"{BACK}/contacts",
            json={
                "name": name.strip(),
                "email": email or None,
                "phone": phone or None,
                "company": company or None,
                "role": role or None,
                "description": description or None,
                "notes": "",
            },
        )
        if resp.status_code == 200:
            new_id = resp.json().get("id")
            st.session_state.selected_contact_id = new_id
            _load_contacts()
            toast_for_rerun("Contact created.", icon="✅")
            st.rerun()
        else:
            st.error(f"Failed to create contact: {resp.text}")


@st.dialog("🗑️ Delete Contact")
def dialog_delete_contact(contact_id: str, contact_name: str):
    st.warning(f"Delete **{contact_name}**? This cannot be undone.")
    if st.button("Delete", use_container_width=True, type="primary"):
        resp = requests.delete(f"{BACK}/contacts/{contact_id}")
        if resp.status_code == 200:
            if st.session_state.get("selected_contact_id") == contact_id:
                del st.session_state["selected_contact_id"]
            _load_contacts()
            toast_for_rerun(f"Contact '{contact_name}' deleted.", icon="🗑️")
            st.rerun()
        else:
            st.error(f"Failed to delete: {resp.text}")


@st.dialog("✏️ Edit Contact", width="large")
def dialog_edit_contact(contact: dict):
    contact_id = contact["id"]

    name = st.text_input("Name *", value=contact.get("name", ""))
    cols = st.columns(2)
    with cols[0]:
        email = st.text_input("Email", value=contact.get("email") or "")
        company = st.text_input("Company", value=contact.get("company") or "")
    with cols[1]:
        phone = st.text_input("Phone", value=contact.get("phone") or "")
        role = st.text_input("Role", value=contact.get("role") or "")
    description = st.text_area("Description", value=contact.get("description") or "")

    save_col, del_col = st.columns([3, 1])
    with save_col:
        if st.button("Save", use_container_width=True, type="primary", disabled=not name.strip()):
            resp = requests.put(
                f"{BACK}/contacts/{contact_id}",
                json={
                    "name": name.strip(),
                    "email": email or None,
                    "phone": phone or None,
                    "company": company or None,
                    "role": role or None,
                    "description": description or None,
                    "notes": contact.get("notes", ""),
                    "projects": contact.get("projects", []),
                    "tags": contact.get("tags", []),
                    "files": contact.get("files", []),
                },
            )
            if resp.status_code == 200:
                _load_contacts()
                toast_for_rerun("Contact updated.", icon="✅")
                st.rerun()
            else:
                st.error(f"Failed to update: {resp.text}")
    with del_col:
        if st.button("🗑️ Delete", use_container_width=True):
            dialog_delete_contact(contact_id, contact.get("name", ""))


def _render_details_tab(contact: dict):
    contact_id = contact["id"]
    avatar_b64 = _fetch_avatar_b64(contact_id)

    # Counter key prevents the file uploader from re-firing on rerun
    counter_key = f"avatar_counter_{contact_id}"
    upload_key = f"avatar_upload_{contact_id}_{st.session_state.get(counter_key, 0)}"

    header_cols = st.columns([1, 6, 2])
    with header_cols[0]:
        if avatar_b64:
            st.markdown(_round_avatar_html(avatar_b64), unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="width:100%;aspect-ratio:1/1;border-radius:50%;background:#444;'
                'display:flex;align-items:center;justify-content:center;'
                'font-size:2rem;color:white;">👤</div>',
                unsafe_allow_html=True,
            )
        # File uploader sits directly below the circle, same column width
        photo_file = st.file_uploader(
            "photo",
            type=["jpg", "jpeg", "png", "webp"],
            key=upload_key,
            label_visibility="collapsed",
            help="Upload a profile photo (compressed to 256×256 JPEG)",
        )
        if photo_file:
            resp = requests.post(
                f"{BACK}/contact/{contact_id}/photo",
                files={"photo": (photo_file.name, photo_file, photo_file.type)},
            )
            if resp.status_code == 200:
                # Bump counter so the widget key changes, resetting the uploader
                st.session_state[counter_key] = st.session_state.get(counter_key, 0) + 1
                toast_for_rerun("Photo updated.", icon="🖼️")
                st.rerun()
            else:
                st.error(f"Failed to upload photo: {resp.text}")
    with header_cols[1]:
        st.markdown(f"## {contact['name']}")
        subtitle = " · ".join(filter(None, [contact.get("role"), contact.get("company")]))
        if subtitle:
            st.caption(subtitle)
    with header_cols[2]:
        if st.button("✏️ Edit", use_container_width=True, key=f"edit_contact_{contact_id}"):
            dialog_edit_contact(contact)

    st.divider()
    info_cols = st.columns(2)
    with info_cols[0]:
        if contact.get("email"):
            st.markdown(f"📧 **Email:** {contact['email']}")
        if contact.get("phone"):
            st.markdown(f"📞 **Phone:** {contact['phone']}")
    with info_cols[1]:
        if contact.get("company"):
            st.markdown(f"🏢 **Company:** {contact['company']}")
        if contact.get("role"):
            st.markdown(f"💼 **Role:** {contact['role']}")

    if contact.get("description"):
        st.markdown("#### Description")
        with st.container(border=True):
            st.write(contact["description"])


def _render_files_tab(contact: dict):
    contact_id = contact["id"]
    files = contact.get("files", [])

    if files:
        with st.columns([1, 4])[0]:
            representation_mode, show_preview, nbr_per_line = representation_mode_select()
        st.divider()
        display_files(
            files,
            representation_mode=representation_mode,
            show_preview=show_preview,
            nbr_of_files_per_line=nbr_per_line,
        )
    else:
        st.info("No files linked to this contact.")

    with st.expander("🔗 Link a file"):
        search_text = st.text_input(
            "Search files",
            key=f"contact_file_search_{contact_id}",
            placeholder="filename or keyword",
        )
        if st.button("Search", key=f"contact_file_search_btn_{contact_id}"):
            url = f"{BACK}/files/search?search_mode=0&start_date=2000-01-01&end_date=2099-12-31"
            if search_text:
                url += f"&text={search_text}"
            resp = requests.get(url)
            st.session_state[f"contact_file_results_{contact_id}"] = (
                resp.json() if resp.status_code == 200 else []
            )

        results = st.session_state.get(f"contact_file_results_{contact_id}", [])
        if results:
            already_linked = set(files)
            available = [f for f in results if f not in already_linked]
            if available:
                selected = st.selectbox(
                    "Select file to link",
                    options=available,
                    format_func=lambda f: f.split("/")[-1],
                    key=f"contact_file_select_{contact_id}",
                )
                if st.button(
                    "Link file",
                    key=f"contact_file_link_btn_{contact_id}",
                    use_container_width=True,
                ):
                    resp = requests.post(
                        f"{BACK}/contact/{contact_id}/file",
                        params={"file": selected},
                    )
                    if resp.status_code == 200:
                        toast_for_rerun("File linked.", icon="✅")
                        st.rerun()
                    else:
                        st.error(f"Failed to link file: {resp.text}")
            else:
                st.info("All matching files are already linked.")

    if files:
        with st.expander("🗑️ Unlink a file"):
            file_to_remove = st.selectbox(
                "Select file to unlink",
                options=files,
                format_func=lambda f: f.split("/")[-1],
                key=f"contact_file_unlink_select_{contact_id}",
            )
            if st.button(
                "Unlink",
                key=f"contact_file_unlink_btn_{contact_id}",
                use_container_width=True,
            ):
                resp = requests.delete(
                    f"{BACK}/contact/{contact_id}/file",
                    params={"file": file_to_remove},
                )
                if resp.status_code == 200:
                    toast_for_rerun("File unlinked.", icon="🗑️")
                    st.rerun()
                else:
                    st.error(f"Failed to unlink file: {resp.text}")


def _render_projects_tags_tab(contact: dict):
    contact_id = contact["id"]
    current_projects = contact.get("projects", [])
    current_tags = contact.get("tags", [])

    all_projects = requests.get(f"{BACK}/projects").json()
    all_tags = requests.get(f"{BACK}/tags").json()

    proj_col, tag_col = st.columns(2)

    with proj_col:
        st.markdown("#### 🗂️ Projects")
        available_projects = [p for p in all_projects if p["name"] not in current_projects]
        if available_projects:
            new_proj = st.selectbox(
                "Add project",
                options=available_projects,
                format_func=lambda p: p["name"],
                key=f"add_proj_{contact_id}",
            )
            if st.button("Add", key=f"add_proj_btn_{contact_id}", use_container_width=True):
                resp = requests.post(
                    f"{BACK}/contact/{contact_id}/project",
                    params={"project": new_proj["name"]},
                )
                if resp.status_code == 200:
                    toast_for_rerun(f"Added to project '{new_proj['name']}'.", icon="✅")
                    st.rerun()
                else:
                    st.error(f"Failed: {resp.text}")

        for proj_name in current_projects:
            proj_data = next((p for p in all_projects if p["name"] == proj_name), None)
            color = proj_data["color"] if proj_data else "#888888"
            badge_col, btn_col = st.columns([4, 1])
            with badge_col:
                st.markdown(
                    generate_project_visual_markdown(proj_name, color),
                    unsafe_allow_html=True,
                )
            with btn_col:
                if st.button("✕", key=f"rm_proj_{contact_id}_{proj_name}"):
                    resp = requests.delete(
                        f"{BACK}/contact/{contact_id}/project",
                        params={"project": proj_name},
                    )
                    if resp.status_code == 200:
                        toast_for_rerun(f"Removed from project '{proj_name}'.", icon="🗑️")
                        st.rerun()

        if not current_projects:
            st.caption("No projects linked.")

    with tag_col:
        st.markdown("#### 🏷️ Tags")
        available_tags = [t for t in all_tags if t["name"] not in current_tags]
        if available_tags:
            new_tag = st.selectbox(
                "Add tag",
                options=available_tags,
                format_func=lambda t: t["name"],
                key=f"add_tag_{contact_id}",
            )
            if st.button("Add", key=f"add_tag_btn_{contact_id}", use_container_width=True):
                resp = requests.post(
                    f"{BACK}/contact/{contact_id}/tag",
                    params={"tag": new_tag["name"]},
                )
                if resp.status_code == 200:
                    toast_for_rerun(f"Added tag '{new_tag['name']}'.", icon="✅")
                    st.rerun()
                else:
                    st.error(f"Failed: {resp.text}")

        for tag_name in current_tags:
            tag_data = next((t for t in all_tags if t["name"] == tag_name), None)
            color = tag_data["color"] if tag_data else "#888888"
            badge_col, btn_col = st.columns([4, 1])
            with badge_col:
                st.markdown(
                    generate_tag_visual_markdown(tag_name, color),
                    unsafe_allow_html=True,
                )
            with btn_col:
                if st.button("✕", key=f"rm_tag_{contact_id}_{tag_name}"):
                    resp = requests.delete(
                        f"{BACK}/contact/{contact_id}/tag",
                        params={"tag": tag_name},
                    )
                    if resp.status_code == 200:
                        toast_for_rerun(f"Removed tag '{tag_name}'.", icon="🗑️")
                        st.rerun()

        if not current_tags:
            st.caption("No tags linked.")


def _render_notes_tab(contact: dict):
    contact_id = contact["id"]
    notes = contact.get("notes", "")

    def save_notes(notes_value):
        if f"contact_notes_{contact_id}" in st.session_state:
            updated = st.session_state[f"contact_notes_{contact_id}"]
            requests.post(
                f"{BACK}/contact/{contact_id}/notes",
                params={"notes": updated},
            )

    refractor_text_area(
        notes,
        key=f"contact_notes_{contact_id}",
        on_change=save_notes,
    )


def contacts():
    with st.sidebar:
        if st.button("➕ New Contact", use_container_width=True, type="primary"):
            dialog_create_contact()

        st.text_input(
            "Search",
            key="contact_search",
            on_change=_load_contacts,
            placeholder="Name, email, company…",
        )

        if "contacts_list" not in st.session_state:
            _load_contacts()

        contacts_list = st.session_state.get("contacts_list", [])
        st.divider()

        if not contacts_list:
            st.caption("No contacts found.")
        else:
            for c in contacts_list:
                is_selected = st.session_state.get("selected_contact_id") == c["id"]

                # Fetch avatar for sidebar display
                avatar_b64 = _fetch_avatar_b64(c["id"])
                subtitle = " · ".join(filter(None, [c.get("role"), c.get("company")]))

                with st.container():
                    row = st.columns([1, 4])
                    with row[0]:
                        if avatar_b64:
                            st.markdown(
                                _round_avatar_html(avatar_b64, 40),
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                '<div style="width:40px;height:40px;border-radius:50%;'
                                'background:#555;display:flex;align-items:center;'
                                'justify-content:center;font-size:1.2rem;">👤</div>',
                                unsafe_allow_html=True,
                            )
                    with row[1]:
                        label = c["name"]
                        if subtitle:
                            label += f"\n{subtitle}"
                        if st.button(
                            label,
                            key=f"contact_btn_{c['id']}",
                            use_container_width=True,
                            type="primary" if is_selected else "secondary",
                        ):
                            st.session_state.selected_contact_id = c["id"]
                            st.rerun()

    contact_id = st.session_state.get("selected_contact_id")
    if not contact_id:
        st.markdown("## 👤 Contacts")
        st.info("Select a contact from the sidebar or create a new one.")
        return

    contact = _get_contact(contact_id)
    if not contact:
        st.error("Contact not found.")
        del st.session_state["selected_contact_id"]
        return

    tab_details, tab_files, tab_projects_tags, tab_notes = st.tabs(
        ["📋 Details", "📁 Files", "📂 Projects & Tags", "📝 Notes"]
    )

    with tab_details:
        _render_details_tab(contact)

    with tab_files:
        _render_files_tab(contact)

    with tab_projects_tags:
        _render_projects_tags_tab(contact)

    with tab_notes:
        _render_notes_tab(contact)


contacts()
