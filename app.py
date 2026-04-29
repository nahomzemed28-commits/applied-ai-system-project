"""PawPal+ Streamlit UI — priority scheduling, JSON persistence, smart slot suggestions, RAG AI."""

import os
import streamlit as st
from datetime import date
from dotenv import load_dotenv

load_dotenv()

from pawpal_system import (
    Task, Pet, Owner, Scheduler,
    PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_EMOJI,
    _PRIORITY_ORDER,
)

DATA_FILE = "data.json"

# ── Session state — load persisted Owner on first run, keep it across re-runs ─
if "owner" not in st.session_state:
    st.session_state.owner = Owner.load_from_json(DATA_FILE)

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)


def save():
    """Helper: persist owner to disk and trigger a rerun."""
    owner.save_to_json(DATA_FILE)
    st.rerun()


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("Smart pet care management — priority scheduling, conflict detection, and auto-recurrence.")

# ── Sidebar — live stats + save/load controls ─────────────────────────────────
with st.sidebar:
    st.header("Dashboard")

    new_name = st.text_input("Owner name", value=owner.name)
    if new_name != owner.name:
        owner.name = new_name

    st.divider()

    total_tasks = len(scheduler.get_todays_schedule())
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

    # Challenge 2 — Persistence controls
    if st.button("💾 Save data", use_container_width=True):
        owner.save_to_json(DATA_FILE)
        st.success("Saved!")

    if st.button("🔃 Reload from file", use_container_width=True):
        st.session_state.owner = Owner.load_from_json(DATA_FILE)
        st.rerun()

    st.caption(f"Today: {date.today().strftime('%A, %B %d %Y')}")

# ── Priority legend ────────────────────────────────────────────────────────────
with st.expander("Priority legend", expanded=False):
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"{PRIORITY_EMOJI[PRIORITY_HIGH]} **High** — urgent care (meds, vet appointments)")
    col2.markdown(f"{PRIORITY_EMOJI[PRIORITY_MEDIUM]} **Medium** — regular routine (feedings, walks)")
    col3.markdown(f"{PRIORITY_EMOJI[PRIORITY_LOW]} **Low** — optional / enrichment (playtime, grooming)")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_schedule, tab_pets, tab_add_task, tab_suggest, tab_ai = st.tabs([
    "📅 Today's Schedule", "🐶 My Pets", "➕ Add Task", "💡 Slot Suggester", "🤖 Ask PawPal AI"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Today's Schedule
# ══════════════════════════════════════════════════════════════════════════════
with tab_schedule:

    # Conflict warnings
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        with st.expander(f"⚠️ {len(conflicts)} scheduling conflict(s) — click to review", expanded=True):
            st.caption("These tasks share a time slot. Consider rescheduling one.")
            for warning in conflicts:
                st.warning(warning.message())

    st.subheader("Today's Schedule")
    st.caption("Sorted by priority (🔴 High → 🟡 Medium → 🟢 Low), then by time within each priority tier.")

    # Filters
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
    with col_f1:
        pet_opts = ["All pets"] + [p.name for p in owner.owned_pets]
        pet_filter = st.selectbox("Pet", pet_opts, key="sf_pet")
    with col_f2:
        status_filter = st.radio("Status", ["All", "Pending", "Done"],
                                 horizontal=True, key="sf_status")
    with col_f3:
        freq_opts = ["All"] + sorted({t.frequency for _, t in scheduler.get_todays_schedule()})
        freq_filter = st.selectbox("Frequency", freq_opts, key="sf_freq")
    with col_f4:
        pri_opts = ["All", "🔴 High", "🟡 Medium", "🟢 Low"]
        pri_filter = st.selectbox("Priority", pri_opts, key="sf_pri")

    # Apply filters
    view = scheduler.get_todays_schedule() if pet_filter == "All pets" else scheduler.filter_by_pet(pet_filter)
    if status_filter == "Pending":
        view = [(p, t) for p, t in view if not t.completed]
    elif status_filter == "Done":
        view = [(p, t) for p, t in view if t.completed]
    if freq_filter != "All":
        view = [(p, t) for p, t in view if t.frequency == freq_filter]
    if pri_filter != "All":
        pri_map = {"🔴 High": PRIORITY_HIGH, "🟡 Medium": PRIORITY_MEDIUM, "🟢 Low": PRIORITY_LOW}
        view = [(p, t) for p, t in view if t.priority == pri_map[pri_filter]]

    st.divider()

    if not view:
        st.info("No tasks match the current filters.")
    else:
        # Column headers
        hc = st.columns([1, 1, 2, 2, 4, 2, 2])
        for col, label in zip(hc, ["Done", "Pri", "Time", "Pet", "Task", "Freq", "Due"]):
            col.caption(label)
        st.divider()

        for idx, (pet, task) in enumerate(view):
            is_conflicted = any((w.task_a is task or w.task_b is task) for w in conflicts)
            c_done, c_pri, c_time, c_pet, c_desc, c_freq, c_due = st.columns([1, 1, 2, 2, 4, 2, 2])

            with c_done:
                cb_key = f"cb_{idx}_{pet.name}_{task.description}_{task.due_date}"
                done = st.checkbox("Done", value=task.completed, key=cb_key,
                                   label_visibility="collapsed")
                if done and not task.completed:
                    scheduler.mark_task_complete(pet.name, task.description)
                    owner.save_to_json(DATA_FILE)   # auto-save on completion
                    st.rerun()

            with c_pri:
                badge = PRIORITY_EMOJI.get(task.priority, "")
                st.write(badge)

            with c_time:
                if is_conflicted:
                    st.markdown(f"**:orange[{task.time}]**")
                else:
                    st.markdown(f"**{task.time}**")

            with c_pet:
                st.write(pet.name)

            with c_desc:
                if task.completed:
                    st.markdown(f"~~{task.description}~~")
                elif is_conflicted:
                    st.markdown(f":orange[{task.description}] ⚠️")
                elif task.priority == PRIORITY_HIGH:
                    st.markdown(f"**{task.description}**")
                else:
                    st.write(task.description)

            with c_freq:
                freq_badge = {"daily": "🔁", "weekly": "📆",
                              "monthly": "🗓️", "once": "1️⃣"}.get(task.frequency, "")
                st.caption(f"{freq_badge} {task.frequency}")

            with c_due:
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
        owner.save_to_json(DATA_FILE)
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — My Pets
# ══════════════════════════════════════════════════════════════════════════════
with tab_pets:
    st.subheader("My Pets")

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
                save()

    st.divider()

    if not owner.owned_pets:
        st.info("No pets registered yet.")
    else:
        for pet in owner.owned_pets:
            pending = len(pet.get_pending_tasks())
            total = len(pet.tasks)
            high_count = sum(1 for t in pet.tasks if t.priority == PRIORITY_HIGH and not t.completed)

            header = f"🐾 **{pet.name}** — {pet.species}, age {pet.age}"
            if high_count:
                header += f"  🔴 ×{high_count}"

            with st.expander(header, expanded=False):
                m1, m2, m3 = st.columns(3)
                m1.metric("Total tasks", total)
                m2.metric("Pending", pending)
                m3.metric("High priority", high_count)

                if not pet.tasks:
                    st.caption("No tasks assigned yet.")
                else:
                    st.divider()
                    for task in sorted(pet.tasks, key=lambda t: (_PRIORITY_ORDER.get(t.priority, 1), t.time)):
                        status_icon = "✅" if task.completed else "⏳"
                        badge = PRIORITY_EMOJI.get(task.priority, "")
                        st.write(
                            f"{status_icon} {badge} **{task.time}** — {task.description} "
                            f"_{task.frequency}_  `due {task.due_date}`"
                        )

                st.divider()
                if st.button(f"🗑️ Remove {pet.name}", key=f"remove_{pet.name}"):
                    owner.remove_pet(pet.name)
                    save()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Add Task
# ══════════════════════════════════════════════════════════════════════════════
with tab_add_task:
    st.subheader("Schedule a New Task")

    if not owner.owned_pets:
        st.warning("Register at least one pet before scheduling tasks.")
    else:
        with st.form("add_task_form", clear_on_submit=True):
            selected_pet_name = st.selectbox("Assign to pet", [p.name for p in owner.owned_pets])
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            with c1:
                description = st.text_input("Task description", placeholder="e.g. Morning walk")
            with c2:
                time_str = st.time_input("Scheduled time")
            with c3:
                frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly", "once"])
            with c4:
                priority = st.selectbox(
                    "Priority",
                    [PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW],
                    format_func=lambda p: f"{PRIORITY_EMOJI[p]} {p.capitalize()}",
                    index=1
                )

            if st.form_submit_button("Add Task"):
                if not description.strip():
                    st.error("Please enter a task description.")
                else:
                    formatted_time = time_str.strftime("%H:%M")
                    target_pet = next(p for p in owner.owned_pets if p.name == selected_pet_name)
                    existing_times = {t.time for t in target_pet.tasks}

                    target_pet.add_task(Task(
                        description=description.strip(),
                        time=formatted_time,
                        frequency=frequency,
                        priority=priority,
                    ))
                    owner.save_to_json(DATA_FILE)

                    if formatted_time in existing_times:
                        st.warning(
                            f"⚠️ Task added, but **{formatted_time}** already has another "
                            f"task for {selected_pet_name}. Consider a different time."
                        )
                    else:
                        st.success(
                            f"✅ {PRIORITY_EMOJI[priority]} '{description.strip()}' added to "
                            f"{selected_pet_name}'s schedule at {formatted_time} ({frequency})."
                        )
                    st.rerun()

        current_conflicts = scheduler.detect_conflicts()
        if current_conflicts:
            st.divider()
            st.subheader("Current Conflicts")
            for w in current_conflicts:
                st.warning(w.message())

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Slot Suggester (Challenge 1)
# ══════════════════════════════════════════════════════════════════════════════
with tab_suggest:
    st.subheader("💡 Smart Slot Suggester")
    st.caption(
        "Find open time slots across all pets' schedules. "
        "The algorithm scans from 06:00 in configurable increments, "
        "skipping every slot that already has a task."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        step = st.select_slider(
            "Slot granularity (minutes)", options=[15, 30, 60], value=30
        )
    with col_b:
        count = st.number_input("Number of suggestions", min_value=1, max_value=10, value=3)

    if st.button("Find open slots"):
        suggestions = scheduler.suggest_slots(count=count, step_minutes=step)
        occupied = sorted({t.time for _, t in scheduler.get_todays_schedule()})

        col_left, col_right = st.columns(2)
        with col_left:
            st.write("**Suggested free slots:**")
            if suggestions:
                for slot in suggestions:
                    st.success(f"🕐 {slot} — available")
            else:
                st.warning("No free slots found with current settings.")

        with col_right:
            st.write("**Currently occupied slots:**")
            if occupied:
                for slot in occupied:
                    st.error(f"🔒 {slot} — taken")
            else:
                st.info("No tasks scheduled yet — all slots are free!")

    st.divider()
    st.subheader("Next available slot after a specific time")
    after_time = st.time_input("Find first free slot after:", key="suggest_after")
    if st.button("Find next slot"):
        next_slot = scheduler.next_available_slot(
            after=after_time.strftime("%H:%M"), step_minutes=step
        )
        st.success(f"Next available slot: **{next_slot}**")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Ask PawPal AI (RAG)
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.subheader("🤖 Ask PawPal AI")
    st.caption(
        "Ask any pet care question. The AI retrieves relevant passages from a curated knowledge "
        "base before answering — so responses are grounded, not guessed."
    )

    # Lazy-load the assistant once per session
    if "ai_assistant" not in st.session_state:
        from ai_assistant import PetCareAssistant
        st.session_state.ai_assistant = PetCareAssistant()

    ai = st.session_state.ai_assistant

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning(
            "ANTHROPIC_API_KEY not set. Set it in your environment or a .env file, "
            "then restart the app. Guardrail and retrieval tests still work without it."
        )

    with st.form("ai_form", clear_on_submit=False):
        query = st.text_area(
            "Your question",
            placeholder="e.g. How often should I feed my adult dog?",
            height=80,
        )
        submitted = st.form_submit_button("Ask", use_container_width=True)

    if submitted and query.strip():
        with st.spinner("Retrieving knowledge and generating answer..."):
            result = ai.answer(query)

        if result["blocked"]:
            st.warning(result["answer"])
        elif result["error"]:
            st.error(f"AI service error: {result['error']}")
            st.info("Check that your ANTHROPIC_API_KEY is valid and try again.")
        else:
            # Confidence badge
            conf_colors = {"high": "green", "medium": "orange", "low": "red"}
            conf_label = result["confidence_label"]
            conf_score = result["confidence"]
            st.markdown(
                f"**Confidence:** :{conf_colors.get(conf_label, 'gray')}[{conf_label.upper()} "
                f"({conf_score:.2f})]"
            )

            st.divider()
            st.markdown(result["answer"])

            if result["sources"]:
                with st.expander("Sources retrieved from knowledge base", expanded=False):
                    for src in result["sources"]:
                        st.caption(f"• `{src}`")

            if conf_label == "low":
                st.info(
                    "Low retrieval confidence — the knowledge base may not fully cover this topic. "
                    "Consult your vet for authoritative advice."
                )

    # Query history from the log file
    with st.expander("Recent query log (last 10 entries)", expanded=False):
        log_path = ai.LOG_DIR / "ai_queries.log" if hasattr(ai, "LOG_DIR") else None
        from ai_assistant import LOG_DIR as _log_dir
        log_file = _log_dir / "ai_queries.log"
        if log_file.exists():
            lines = log_file.read_text().strip().splitlines()
            for line in lines[-10:]:
                st.caption(line)
        else:
            st.caption("No queries logged yet.")
