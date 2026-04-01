"""PawPal+ Streamlit UI — fully wired to the pawpal_system.py algorithmic layer."""

import streamlit as st
from datetime import date

from pawpal_system import Task, Pet, Owner, Scheduler

# ── Session state — persist Owner across Streamlit re-runs ───────────────────
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="My Household", email="owner@pawpal.com")

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("Smart pet care management — keeping your furry friends happy and healthy.")

# ── Sidebar — live stats ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("Dashboard")

    new_name = st.text_input("Owner name", value=owner.name)
    if new_name != owner.name:
        owner.name = new_name

    st.divider()

    total_tasks = sum(len(p.tasks) for p in owner.owned_pets)
    pending_count = len(scheduler.get_pending_tasks())
    conflict_count = len(scheduler.detect_conflicts())

    st.metric("Pets", len(owner.owned_pets))
    st.metric("Tasks today", total_tasks)
    st.metric("Pending", pending_count)

    if conflict_count:
        st.error(f"⚠️ {conflict_count} conflict(s)")
    else:
        st.success("No conflicts")

    st.divider()
    st.caption(f"Today: {date.today().strftime('%A, %B %d %Y')}")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_schedule, tab_pets, tab_add_task = st.tabs(
    ["📅 Today's Schedule", "🐶 My Pets", "➕ Add Task"]
)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Today's Schedule
# ═════════════════════════════════════════════════════════════════════════════
with tab_schedule:

    # ── Conflict warnings — each conflict gets its own callout ────────────────
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        with st.expander(f"⚠️ {len(conflicts)} scheduling conflict(s) — click to review", expanded=True):
            st.caption(
                "These tasks are scheduled at the same time. "
                "Consider rescheduling one to avoid rushing."
            )
            for warning in conflicts:
                st.warning(warning.message())

    st.subheader("Today's Schedule")

    # ── Filter controls ───────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
    with col_f1:
        pet_options = ["All pets"] + [p.name for p in owner.owned_pets]
        selected_pet_filter = st.selectbox("Filter by pet", pet_options, key="sched_pet_filter")
    with col_f2:
        status_filter = st.radio(
            "Filter by status", ["All", "Pending", "Done"],
            horizontal=True, key="sched_status_filter"
        )
    with col_f3:
        freq_options = ["All"] + sorted({t.frequency for _, t in scheduler.get_todays_schedule()})
        freq_filter = st.selectbox("Filter by frequency", freq_options, key="sched_freq_filter")

    # ── Apply filters using Scheduler methods ─────────────────────────────────
    if selected_pet_filter == "All pets":
        view = scheduler.get_todays_schedule()
    else:
        view = scheduler.filter_by_pet(selected_pet_filter)

    if status_filter == "Pending":
        view = [(p, t) for p, t in view if not t.completed]
    elif status_filter == "Done":
        view = [(p, t) for p, t in view if t.completed]

    if freq_filter != "All":
        view = [(p, t) for p, t in view if t.frequency == freq_filter]

    st.divider()

    # ── Schedule table ────────────────────────────────────────────────────────
    if not view:
        st.info("No tasks match the current filters.")
    else:
        # Column headers
        hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([1, 2, 2, 4, 2, 2])
        hc1.caption("Done")
        hc2.caption("Time")
        hc3.caption("Pet")
        hc4.caption("Task")
        hc5.caption("Frequency")
        hc6.caption("Due")
        st.divider()

        for pet, task in view:
            # Flag tasks that conflict at this time slot
            is_conflicted = any(
                (w.task_a is task or w.task_b is task) for w in conflicts
            )

            col_done, col_time, col_pet, col_desc, col_freq, col_due = st.columns([1, 2, 2, 4, 2, 2])

            with col_done:
                cb_key = f"cb_{pet.name}_{task.description}_{task.due_date}"
                done = st.checkbox("", value=task.completed, key=cb_key)
                if done and not task.completed:
                    scheduler.mark_task_complete(pet.name, task.description)
                    st.rerun()

            with col_time:
                if is_conflicted:
                    st.markdown(f"**:orange[{task.time}]**")
                else:
                    st.markdown(f"**{task.time}**")

            with col_pet:
                st.write(pet.name)

            with col_desc:
                if task.completed:
                    st.markdown(f"~~{task.description}~~")
                elif is_conflicted:
                    st.markdown(f":orange[{task.description}] ⚠️")
                else:
                    st.write(task.description)

            with col_freq:
                badge = {"daily": "🔁 daily", "weekly": "📆 weekly",
                         "monthly": "🗓️ monthly", "once": "1️⃣ once"}.get(task.frequency, task.frequency)
                st.caption(badge)

            with col_due:
                if task.due_date == date.today():
                    st.caption("Today")
                elif task.due_date > date.today():
                    st.caption(task.due_date.strftime("%b %d"))
                else:
                    st.caption(f":red[{task.due_date.strftime('%b %d')}]")

    st.divider()
    if st.button("🔄 Reset all tasks for today"):
        for p in owner.owned_pets:
            for t in p.tasks:
                if t.due_date == date.today():
                    t.reset()
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — My Pets
# ═════════════════════════════════════════════════════════════════════════════
with tab_pets:
    st.subheader("My Pets")

    # ── Add pet form ──────────────────────────────────────────────────────────
    with st.form("add_pet_form", clear_on_submit=True):
        st.write("**Register a new pet**")
        c1, c2, c3 = st.columns(3)
        with c1:
            pet_name = st.text_input("Pet name", placeholder="e.g. Luna")
        with c2:
            species = st.selectbox("Species", ["Dog", "Cat", "Bird", "Rabbit", "Other"])
        with c3:
            age = st.number_input("Age (years)", min_value=0, max_value=30, value=1)

        if st.form_submit_button("Add Pet"):
            if not pet_name.strip():
                st.error("Please enter a pet name.")
            elif any(p.name.lower() == pet_name.strip().lower() for p in owner.owned_pets):
                st.error(f"'{pet_name}' is already registered.")
            else:
                owner.add_pet(Pet(name=pet_name.strip(), species=species, age=age))
                st.success(f"✅ {pet_name.strip()} added!")
                st.rerun()

    st.divider()

    # ── Pet cards — metrics + filtered task list ──────────────────────────────
    if not owner.owned_pets:
        st.info("No pets registered yet. Use the form above to add your first pet!")
    else:
        for pet in owner.owned_pets:
            pending = len(pet.get_pending_tasks())
            total = len(pet.tasks)
            done = total - pending

            with st.expander(f"🐾 **{pet.name}** — {pet.species}, age {pet.age}", expanded=False):
                m1, m2, m3 = st.columns(3)
                m1.metric("Total tasks", total)
                m2.metric("Pending", pending)
                m3.metric("Done today", done)

                if not pet.tasks:
                    st.caption("No tasks assigned yet.")
                else:
                    st.divider()
                    for task in sorted(pet.tasks, key=lambda t: t.time):
                        status_icon = "✅" if task.completed else "⏳"
                        freq_icon = {"daily": "🔁", "weekly": "📆",
                                     "monthly": "🗓️", "once": "1️⃣"}.get(task.frequency, "")
                        st.write(
                            f"{status_icon} **{task.time}** — {task.description} "
                            f"{freq_icon} _{task.frequency}_  `due {task.due_date}`"
                        )

                st.divider()
                if st.button(f"🗑️ Remove {pet.name}", key=f"remove_{pet.name}"):
                    owner.remove_pet(pet.name)
                    st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — Add Task
# ═════════════════════════════════════════════════════════════════════════════
with tab_add_task:
    st.subheader("Schedule a New Task")

    if not owner.owned_pets:
        st.warning("Register at least one pet before scheduling tasks.")
    else:
        with st.form("add_task_form", clear_on_submit=True):
            selected_pet_name = st.selectbox(
                "Assign to pet", [p.name for p in owner.owned_pets]
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                description = st.text_input("Task description", placeholder="e.g. Morning walk")
            with c2:
                time_str = st.time_input("Scheduled time")
            with c3:
                frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly", "once"])

            if st.form_submit_button("Add Task"):
                if not description.strip():
                    st.error("Please enter a task description.")
                else:
                    formatted_time = time_str.strftime("%H:%M")
                    target_pet = next(p for p in owner.owned_pets if p.name == selected_pet_name)

                    # Preview conflict before adding
                    existing_times = {t.time for t in target_pet.tasks}
                    will_conflict = formatted_time in existing_times

                    target_pet.add_task(Task(
                        description=description.strip(),
                        time=formatted_time,
                        frequency=frequency
                    ))

                    if will_conflict:
                        st.warning(
                            f"⚠️ Task added, but **{formatted_time}** already has "
                            f"another task for {selected_pet_name}. Consider a different time."
                        )
                    else:
                        st.success(
                            f"✅ '{description.strip()}' added to {selected_pet_name}'s "
                            f"schedule at {formatted_time} ({frequency})."
                        )
                    st.rerun()

        # ── Conflict summary for context while adding ─────────────────────────
        current_conflicts = scheduler.detect_conflicts()
        if current_conflicts:
            st.divider()
            st.subheader("Current Conflicts")
            st.caption("Resolve these by rescheduling tasks in the My Pets tab.")
            for w in current_conflicts:
                st.warning(w.message())
