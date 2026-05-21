import datetime
from typing import List

import requests
import streamlit as st
from utils import (
    generate_aside_project_markdown,
    generate_aside_tag_markdown,
    toast_for_rerun,
)

PRIORITY_OPTIONS = [
    {"label": "Idea", "value": -1, "emoji": "💡"},
    {"label": "Low", "value": 0, "emoji": "🟢"},
    {"label": "Medium", "value": 1, "emoji": "🟡"},
    {"label": "High", "value": 2, "emoji": "🟧"},
    {"label": "Critical", "value": 3, "emoji": "🟥"},
    {"label": "Bug", "value": 4, "emoji": "🐞"},
]


@st.dialog("🆕 Create a new Kanban board")
def create_kanban_board():
    board_name = st.text_input(
        "Board name", placeholder="Enter the name of the new Kanban board"
    )
    board_description = st.text_area(
        "Board description",
        placeholder="Enter a description for the new Kanban board (optional)",
        height=100,
    )
    if st.button("Create", use_container_width=True):
        if not board_name:
            st.error("Board name cannot be empty.")
            return

        response = requests.post(
            "http://back:80/kanban/boards?name={}&description={}".format(
                board_name, board_description
            )
        )

        if response.status_code == 200:
            toast_for_rerun("Kanban board created successfully!", icon="✅")
            st.rerun()
        else:
            st.error(
                f"Failed to create Kanban board. Please try again. {response.status_code} : {response.text}"
            )
            st.toast("Failed to create Kanban board. Please try again.", icon="❌")


@st.dialog("✏️ Edit Kanban Board", width="large")
def edit_kanban_board(board):
    new_name = st.text_input("Board name", value=board["name"])
    new_description = st.text_area(
        "Board description", value=board["description"], height=200
    )
    if st.button("Save changes", use_container_width=True):
        if not new_name:
            st.error("Board name cannot be empty.")
            return

        response = requests.put(
            "http://back:80/kanban/boards/{}?name={}&description={}".format(
                board["id"], new_name, new_description
            )
        )

        if response.status_code == 200:
            toast_for_rerun("Kanban board updated successfully!", icon="✅")
            st.rerun()
        else:
            st.error(
                f"Failed to update Kanban board. Please try again. {response.status_code} : {response.text}"
            )
            st.toast("Failed to update Kanban board. Please try again.", icon="❌")


@st.dialog("🗑️ Delete Kanban Board")
def delete_kanban_board(board_id):
    st.markdown(
        "Are you sure you want to delete this Kanban board? This action cannot be undone."
    )
    if st.button("Delete Board", use_container_width=True):
        response = requests.delete("http://back:80/kanban/boards/{}".format(board_id))
        if response.status_code == 200:
            toast_for_rerun("Kanban board deleted successfully!", icon="✅")
            st.rerun()
        else:
            st.error(
                f"Failed to delete Kanban board. Please try again. {response.status_code} : {response.text}"
            )
            st.toast("Failed to delete Kanban board. Please try again.", icon="❌")


@st.dialog("🆕 Create new task", width="large")
def create_task(column, default_project: List[str] = []):
    st.markdown(
        "Enter the content of the new task for the column <a style='color: {}'>{}</a>".format(
            column["color"], column["name"]
        ),
        unsafe_allow_html=True,
    )
    task_title = st.text_input("Task title", placeholder="Enter the title of the task")
    task_description = st.text_area(
        "Task description",
        placeholder="Enter a description for the task (optional)",
        height=400,
    )
    if st.toggle("Start date", key="start_date_toggle"):
        start_date = st.date_input("Start date")
    else:
        start_date = None
    if st.toggle("Due date", key="due_date_toggle"):
        due_date = st.date_input("Due date")
    else:
        due_date = None

    priority = st.selectbox(
        "Priority",
        options=PRIORITY_OPTIONS,
        format_func=lambda x: x["emoji"] + " " + x["label"],
    )

    projects = requests.get("http://back:80/projects").json()
    new_projects = st.multiselect(
        "Projects",
        options=[p["name"] for p in projects],
        default=[
            p for p in default_project if p in [proj["name"] for proj in projects]
        ],
    )
    tags = requests.get("http://back:80/tags").json()
    new_tags = st.multiselect(
        "Tags",
        options=[t["name"] for t in tags],
    )

    if st.button("Add Task", use_container_width=True):
        if not task_title:
            st.error("Task title cannot be empty.")
            return

        response = requests.post(
            "http://back:80/tasks",
            json={
                "title": task_title,
                "description": task_description,
                "projects": new_projects,
                "tags": new_tags,
                "files": [],
                "calendars": [],
                "start_date": start_date.strftime("%Y-%m-%dT%H:%M:%S")
                if start_date
                else None,
                "end_date": due_date.strftime("%Y-%m-%dT%H:%M:%S")
                if due_date
                else None,
                "completed": None,
                "priority": priority["value"],
            },
        )

        if response.status_code == 200:
            response = requests.post(
                "http://back:80/kanban/columns/{column_id}/tasks/{task_id}".format(
                    column_id=column["id"], task_id=response.json()["id"]
                )
            )
            if response.status_code == 200:
                toast_for_rerun("Task added successfully!", icon="✅")
                st.rerun()
            else:
                st.error(
                    f"Failed to add task to column. Please try again. {response.status_code} : {response.text}"
                )
                st.toast("Failed to add task to column. Please try again.", icon="❌")
        else:
            st.error(
                f"Failed to add task. Please try again. {response.status_code} : {response.text}"
            )
            st.toast("Failed to add task. Please try again.", icon="❌")


@st.dialog("✏️ Edit Kanban Column", width="large")
def edit_kanban_column(column, board_id):
    if st.button("🗑️ Delete Column", use_container_width=True):
        response = requests.delete(
            "http://back:80/kanban/columns/{}".format(column["id"])
        )
        if response.status_code == 200:
            toast_for_rerun("Kanban column deleted successfully!", icon="✅")
            st.rerun()
        else:
            st.error(
                f"Failed to delete Kanban column. Please try again. {response.status_code} : {response.text}"
            )
            st.toast("Failed to delete Kanban column. Please try again.", icon="❌")

    new_name = st.text_input("Column name", value=column["name"])
    new_color = st.color_picker("Column color", value=column["color"])
    if st.button("Save changes", use_container_width=True):
        if not new_name:
            st.error("Column name cannot be empty.")
            return

        response = requests.put(
            "http://back:80/kanban/columns/{}".format(column["id"]),
            json={
                "name": new_name,
                "color": new_color,
                "position": column["position"],
            },
        )

        if response.status_code == 200:
            toast_for_rerun("Kanban column updated successfully!", icon="✅")
            st.rerun()
        else:
            st.error(
                f"Failed to update Kanban column. Please try again. {response.status_code} : {response.text}"
            )
            st.toast("Failed to update Kanban column. Please try again.", icon="❌")


@st.dialog("✏️ Edit Task", width="large")
def edit_task(task):
    if st.button("🗑️ Delete Task", use_container_width=True):
        response = requests.delete("http://back:80/tasks/{}".format(task["id"]))
        if response.status_code == 200:
            toast_for_rerun("Task deleted successfully!", icon="✅")
            st.rerun()
        else:
            st.error(
                f"Failed to delete task. Please try again. {response.status_code} : {response.text}"
            )
            st.toast("Failed to delete task. Please try again.", icon="❌")
    st.markdown(
        "Edit the content of the task **{}**".format(task["title"]),
        unsafe_allow_html=True,
    )
    new_title = st.text_input("Task title", value=task["title"])
    new_description = st.text_area(
        "Task description", value=task["description"], height=400
    )
    if st.toggle(
        "Start date", key="edit_start_date_toggle", value=bool(task["start_date"])
    ):
        new_start_date = st.date_input(
            "Start date",
            value=datetime.datetime.strptime(task["start_date"], "%Y-%m-%dT%H:%M:%S")
            if task["start_date"]
            else datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
    else:
        new_start_date = None
    if st.toggle(
        "Due date", key="edit_due_date_toggle", value=task["end_date"] is not None
    ):
        new_due_date = st.date_input(
            "Due date",
            value=datetime.datetime.strptime(task["end_date"], "%Y-%m-%dT%H:%M:%S")
            if task["end_date"]
            else datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
    else:
        new_due_date = None

    new_priority = st.selectbox(
        "Priority",
        options=PRIORITY_OPTIONS,
        format_func=lambda x: x["emoji"] + " " + x["label"],
        index=[p["value"] for p in PRIORITY_OPTIONS].index(task["priority"])
        if task["priority"] is not None
        else 0,
    )

    projects = requests.get("http://back:80/projects").json()
    new_projects = st.multiselect(
        "Projects",
        options=[p["name"] for p in projects],
        default=task["projects"],
    )
    tags = requests.get("http://back:80/tags").json()
    new_tags = st.multiselect(
        "Tags",
        options=[t["name"] for t in tags],
        default=task["tags"],
    )

    if st.button("Save changes", use_container_width=True):
        if not new_title:
            st.error("Task title cannot be empty.")
            return

        response = requests.put(
            "http://back:80/tasks/{}".format(task["id"]),
            json={
                "title": new_title,
                "description": new_description,
                "projects": new_projects,
                "tags": new_tags,
                "files": task["files"],
                "calendars": task["calendars"],
                "start_date": new_start_date.strftime("%Y-%m-%dT%H:%M:%S")
                if new_start_date
                else None,
                "end_date": new_due_date.strftime("%Y-%m-%dT%H:%M:%S")
                if new_due_date
                else None,
                "completed": task["completed"],
                "priority": new_priority["value"],
            },
        )

        if response.status_code == 200:
            toast_for_rerun("Task updated successfully!", icon="✅")
            st.rerun()
        else:
            st.error(
                f"Failed to update task. Please try again. {response.status_code} : {response.text}"
            )
            st.toast("Failed to update task. Please try again.", icon="❌")


def organization():
    with st.sidebar:
        if st.button("🆕 Create Board", use_container_width=True):
            create_kanban_board()
        show_validated_tasks = st.toggle(
            "✅ Show validated tasks", key="validated_tasks_toggle", value=False
        )
        in_sidebar_board_selector = st.toggle(
            "📋 Board selector in sidebar",
            key="board_selector_sidebar_toggle",
            value=False,
        )
        show_edit_columns = st.toggle(
            "✏️ Columns edit", key="show_edit_columns_toggle", value=False
        )
        show_edit_tasks = st.toggle(
            "✏️ Tasks edit", key="show_edit_tasks_toggle", value=True
        )
        min_nbr_columns = st.slider(
            "Minimum number of columns to display",
            min_value=3,
            max_value=10,
            value=5,
            key="min_nbr_columns_slider",
        )

    kaban_boards = requests.get("http://back:80/kanban/boards").json()

    if in_sidebar_board_selector:
        st.sidebar.divider()
        cols = [st.sidebar] * 5
    else:
        cols = st.columns(5)
    with cols[0]:
        selected_board = st.selectbox(
            "Select a Kanban board",
            options=[board for board in kaban_boards],
            format_func=lambda board: board["name"],
        )

    with cols[1]:
        projects = requests.get("http://back:80/projects").json()
        selected_projects = st.multiselect(
            "Select projects to filter",
            options=[p["name"] for p in projects],
        )

    with cols[2]:
        tags = requests.get("http://back:80/tags").json()
        selected_tags = st.multiselect(
            "Select tags to filter",
            options=[t["name"] for t in tags],
        )

    with cols[3]:
        selected_priorities = st.multiselect(
            "Select priorities to filter",
            options=PRIORITY_OPTIONS,
            format_func=lambda x: x["emoji"] + " " + x["label"],
        )

    if selected_board:
        with st.sidebar:
            st.divider()

            st.caption("{} - {}".format(selected_board["name"], selected_board["id"]))
            if st.button("✏️ Edit Board", use_container_width=True):
                edit_kanban_board(selected_board)
            if st.button("🗑️ Delete Board", use_container_width=True):
                delete_kanban_board(selected_board["id"])

        st.markdown(f"## {selected_board['name']}")
        st.markdown(f"{selected_board['description']}")
        with st.spinner("Loading board..."):
            board_info = requests.get(
                "http://back:80/kanban/boards/{}".format(selected_board["id"])
            ).json()

        # MARK: COLUMNS
        n_cols = max(
            len(board_info["columns"]) + (1 if show_edit_columns else 0),
            min_nbr_columns,
        )
        columns = st.columns(n_cols)
        columns = [columns[i].container(border=True) for i in range(n_cols)]
        for i, column in enumerate(board_info["columns"]):
            with columns[i]:
                if show_edit_columns:
                    cols = st.columns(3)
                    with cols[0]:
                        if st.button(
                            "⬅️",
                            use_container_width=True,
                            key=f"move_left_{column['id']}",
                            disabled=i == 0,
                        ):
                            response = requests.put(
                                "http://back:80/kanban/columns/{}/move/left".format(
                                    column["id"]
                                )
                            )
                            if response.status_code == 200:
                                toast_for_rerun(
                                    "Column moved left successfully!", icon="✅"
                                )
                                st.rerun()
                            else:
                                st.error(
                                    f"Failed to move column left. Please try again. {response.status_code} : {response.text}"
                                )
                                st.toast(
                                    "Failed to move column left. Please try again.",
                                    icon="❌",
                                )
                    with cols[1]:
                        if st.button(
                            "✏️", use_container_width=True, key=f"edit_{column['id']}"
                        ):
                            edit_kanban_column(column, board_info["id"])
                    with cols[2]:
                        if st.button(
                            "➡️",
                            use_container_width=True,
                            key=f"move_right_{column['id']}",
                            disabled=i == len(board_info["columns"]) - 1,
                        ):
                            response = requests.put(
                                "http://back:80/kanban/columns/{}/move/right".format(
                                    column["id"]
                                )
                            )
                            if response.status_code == 200:
                                toast_for_rerun(
                                    "Column moved right successfully!", icon="✅"
                                )
                                st.rerun()
                            else:
                                st.error(
                                    f"Failed to move column right. Please try again. {response.status_code} : {response.text}"
                                )
                                st.toast(
                                    "Failed to move column right. Please try again.",
                                    icon="❌",
                                )
                st.markdown(
                    f"<div style='font-size: 2em; font-weight: bold; width: 100%; display: flex; justify-content: center; align-items: center; color: {column['color']}'>{column['name']}</div>",
                    unsafe_allow_html=True,
                )

                if st.button(
                    "➕ Add Task",
                    use_container_width=True,
                    key=f"add_task_{column['id']}",
                ):
                    create_task(column, default_project=selected_projects)

                # MARK: TASKS
                for task in column["tasks"]:
                    if selected_projects and not any(
                        p in task["projects"] for p in selected_projects
                    ):
                        continue
                    if selected_tags and not any(
                        t in task["tags"] for t in selected_tags
                    ):
                        continue
                    if selected_priorities and not any(
                        p["value"] == task["priority"] for p in selected_priorities
                    ):
                        continue
                    if not show_validated_tasks and task["completed"]:
                        continue
                    with st.container(border=True):
                        if show_edit_tasks:
                            cols = st.columns(4)
                            with cols[0]:
                                if st.button(
                                    "⬅️",
                                    use_container_width=True,
                                    key=f"move_left_{task['id']}",
                                    disabled=i == 0,
                                ):
                                    response = requests.put(
                                        "http://back:80/kanban/columns/{column_id}/tasks/{task_id}/move".format(
                                            column_id=board_info["columns"][i - 1][
                                                "id"
                                            ],
                                            task_id=task["id"],
                                        )
                                    )
                                    if response.status_code == 200:
                                        toast_for_rerun(
                                            "Task moved left successfully!", icon="✅"
                                        )
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Failed to move task left. Please try again. {response.status_code} : {response.text}"
                                        )
                                        st.toast(
                                            "Failed to move task left. Please try again.",
                                            icon="❌",
                                        )
                            with cols[1]:
                                if st.button(
                                    "✏️",
                                    use_container_width=True,
                                    key=f"edit_{task['id']}",
                                ):
                                    edit_task(task)
                            with cols[2]:
                                if st.button(
                                    "❌" if task["completed"] else "✅",
                                    use_container_width=True,
                                    key=f"toggle_completed_{task['id']}",
                                ):
                                    if not task["completed"]:
                                        response = requests.put(
                                            "http://back:80/kanban/columns/{column_id}/tasks/{task_id}/move".format(
                                                column_id=board_info["columns"][- 1][
                                                    "id"
                                                ],
                                                task_id=task["id"],
                                            )
                                        )
                                    response = requests.put(
                                        "http://back:80/tasks/{}/complete".format(
                                            task["id"]
                                        )
                                    )
                                    if response.status_code == 200:
                                        toast_for_rerun(
                                            "Task status updated successfully!",
                                            icon="✅",
                                        )
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Failed to update task status. Please try again. {response.status_code} : {response.text}"
                                        )
                                        st.toast(
                                            "Failed to update task status. Please try again.",
                                            icon="❌",
                                        )
                            with cols[3]:
                                if st.button(
                                    "➡️",
                                    use_container_width=True,
                                    key=f"move_right_{task['id']}",
                                    disabled=i == len(board_info["columns"]) - 1,
                                ):
                                    response = requests.put(
                                        "http://back:80/kanban/columns/{column_id}/tasks/{task_id}/move".format(
                                            column_id=board_info["columns"][i + 1][
                                                "id"
                                            ],
                                            task_id=task["id"],
                                        )
                                    )
                                    if response.status_code == 200:
                                        toast_for_rerun(
                                            "Task moved right successfully!", icon="✅"
                                        )
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Failed to move task right. Please try again. {response.status_code} : {response.text}"
                                        )
                                        st.toast(
                                            "Failed to move task right. Please try again.",
                                            icon="❌",
                                        )

                        priority = next(
                            (
                                p
                                for p in PRIORITY_OPTIONS
                                if p["value"] == task["priority"]
                            ),
                            None,
                        )
                        st.markdown(
                            f"### {priority['emoji']} **{task['title']}**"
                            if priority
                            else f"### **{task['title']}**"
                        )
                        if task["description"]:
                            st.markdown(task["description"])

                        if task["start_date"]:
                            start_date = datetime.datetime.strptime(
                                task["start_date"], "%Y-%m-%dT%H:%M:%S"
                            )
                            st.markdown(f"🗓️ Start: {start_date.strftime('%d-%m-%Y')}")
                        if task["end_date"]:
                            due_date = datetime.datetime.strptime(
                                task["end_date"], "%Y-%m-%dT%H:%M:%S"
                            )
                            st.markdown(f"🗓️ Due: {due_date.strftime('%d-%m-%Y')}")
                        if task["projects"]:
                            task_projects = [
                                p for p in projects if p["name"] in task["projects"]
                            ]
                            st.markdown(
                                generate_aside_project_markdown(
                                    [p["name"] for p in task_projects],
                                    [project["color"] for project in task_projects],
                                ),
                                unsafe_allow_html=True,
                            )
                        if task["tags"]:
                            task_tags = [t for t in tags if t["name"] in task["tags"]]
                            st.markdown(
                                generate_aside_tag_markdown(
                                    [t["name"] for t in task_tags],
                                    [tag["color"] for tag in task_tags],
                                ),
                                unsafe_allow_html=True,
                            )
                        if task["files"]:
                            st.markdown(
                                "📎 Attached files: {}".format(", ".join(task["files"]))
                            )
                        if task["calendars"]:
                            st.markdown(
                                "📅 Linked calendars: {}".format(
                                    ", ".join(task["calendars"])
                                )
                            )

        # MARK: ADD NEW COLUMN
        if show_edit_columns:
            with columns[-1]:
                st.markdown("### Add a new column")
                cols = st.columns([4, 1])
                new_column_name = cols[0].text_input(
                    "Name", placeholder="Enter the name of the new column"
                )
                new_column_color = cols[1].color_picker("Color", value="#FFFFFF")
                if st.button("Add Column", use_container_width=True):
                    if not new_column_name:
                        st.error("Column name cannot be empty.")
                        return

                    response = requests.post(
                        "http://back:80/kanban/boards/{}/columns".format(
                            selected_board["id"]
                        ),
                        json={
                            "name": new_column_name,
                            "color": new_column_color,
                            "position": len(board_info["columns"]),
                        },
                    )

                    if response.status_code == 200:
                        toast_for_rerun("Column added successfully!", icon="✅")
                        st.rerun()
                    else:
                        st.error(
                            f"Failed to add column. Please try again. {response.status_code} : {response.text}"
                        )
                        st.toast("Failed to add column. Please try again.", icon="❌")


if __name__ == "__main__":
    organization()
