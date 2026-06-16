import datetime
import json
import urllib.parse

import requests
import streamlit as st
from utils import clear_cache, fmt_bytes, toast_for_rerun

FILE_TYPE_ICONS = {
    "pdf": "📄",
    "doc": "📝",
    "docx": "📝",
    "xls": "📊",
    "xlsx": "📊",
    "ppt": "📊",
    "pptx": "📊",
    "txt": "📃",
    "md": "📃",
    "png": "🖼️",
    "jpg": "🖼️",
    "jpeg": "🖼️",
    "gif": "🖼️",
    "svg": "🖼️",
    "mp3": "🎵",
    "mp4": "🎬",
    "wav": "🎵",
    "zip": "📦",
    "py": "🐍",
    "js": "🟨",
    "ts": "🔷",
    "html": "🌐",
    "css": "🎨",
    "json": "📋",
    "csv": "📊",
}


def _file_icon(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return FILE_TYPE_ICONS.get(ext, "📎")


def quick_upload():
    projects_resp = requests.get("http://back:80/projects").json()
    tags_resp = requests.get("http://back:80/tags").json()
    contacts_resp = requests.get("http://back:80/contacts").json()
    project_names = [p["name"] for p in projects_resp]
    tag_names = [t["name"] for t in tags_resp]

    def _on_change():
        st.session_state.quick_upload_new_files = True

    files = st.file_uploader(
        "Drop or select files",
        accept_multiple_files=True,
        on_change=_on_change,
        label_visibility="collapsed",
    )

    if not files:
        st.info("Select or drop files above to begin uploading.", icon="☝️")
        return


    # --- Global defaults ---
    with st.container(border=True):
        st.markdown("#### Global defaults")
        st.caption("Applied to every file unless that file overrides them.")
        gcols = st.columns([1, 2, 2, 2])
        with gcols[0]:
            global_date = st.date_input(
                "Date",
                value=datetime.date.today(),
                key="qu_global_date",
            )
        with gcols[1]:
            global_projects = st.multiselect(
                "Projects",
                options=project_names,
                key="qu_global_projects",
            )
        with gcols[2]:
            global_tags = st.multiselect(
                "Tags",
                options=tag_names,
                key="qu_global_tags",
            )
        with gcols[3]:
            global_contacts_sel = st.multiselect(
                "Contacts",
                options=contacts_resp,
                format_func=lambda c: c["name"],
                key="qu_global_contacts",
            )
    global_contact_ids = [c["id"] for c in global_contacts_sel]

    st.divider()
    st.markdown(f"#### {len(files)} file{'s' if len(files) != 1 else ''} selected")

    file_edit_info = {}

    for file in files:
        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        icon = _file_icon(file.name)
        size_str = fmt_bytes(file.size)
        file_edit_info[file.name] = {}

        with st.container(border=True):
            top_cols = st.columns([0.4, 5, 2])
            with top_cols[0]:
                st.markdown(f"<div style='font-size:2rem;line-height:1'>{icon}</div>", unsafe_allow_html=True)
            with top_cols[1]:
                file_edit_info[file.name]["name"] = st.text_input(
                    "Save as",
                    value=file.name,
                    key=f"qu_name_{file.name}",
                    label_visibility="collapsed",
                )
                st.caption("Uploaded as: " + file_edit_info[file.name]["name"])
                badge = f"`{ext.upper()}`" if ext else "`file`"
                st.caption(f"{badge} · {size_str}")
            with top_cols[2]:
                override = st.toggle(
                    "Override defaults",
                    key=f"qu_override_{file.name}",
                    value=False,
                    help="Enable to set date, projects and tags specifically for this file.",
                )

            if override:
                ov_cols = st.columns([1, 2, 2, 2])
                with ov_cols[0]:
                    file_edit_info[file.name]["date"] = st.date_input(
                        "Date",
                        value=global_date,
                        key=f"qu_date_{file.name}",
                    ).strftime("%Y-%m-%d")
                with ov_cols[1]:
                    file_edit_info[file.name]["projects"] = st.multiselect(
                        "Projects",
                        options=project_names,
                        default=global_projects,
                        key=f"qu_projects_{file.name}",
                    )
                with ov_cols[2]:
                    file_edit_info[file.name]["tags"] = st.multiselect(
                        "Tags",
                        options=tag_names,
                        default=global_tags,
                        key=f"qu_tags_{file.name}",
                    )
                with ov_cols[3]:
                    file_contacts_sel = st.multiselect(
                        "Contacts",
                        options=contacts_resp,
                        format_func=lambda c: c["name"],
                        default=global_contacts_sel,
                        key=f"qu_contacts_{file.name}",
                    )
                    file_edit_info[file.name]["contacts"] = [c["id"] for c in file_contacts_sel]


    if st.button("✅ Upload all files", use_container_width=True, type="primary"):
        with st.spinner("Uploading files...", show_time=True):
            files_payload = [("files", (f.name, f, f.type)) for f in files]
            params = {
                "subdirectory": "uploads",
                "file_edit_info": json.dumps(file_edit_info),
                "projects": json.dumps(global_projects),
                "tags": json.dumps(global_tags),
                "contacts": json.dumps(global_contact_ids),
                "date": global_date.strftime("%Y-%m-%d"),
            }
            url = f"http://back:80/files/upload?{urllib.parse.urlencode(params)}"
            response = requests.post(url, files=files_payload)
            if response.status_code == 200:
                st.session_state.pop("quick_upload_new_files", None)
                clear_cache()
                toast_for_rerun("Files uploaded successfully!", icon="🆕")
                st.rerun()
            else:
                st.error(f"Upload failed: {response.text}")


if __name__ == "__main__":
    quick_upload()
