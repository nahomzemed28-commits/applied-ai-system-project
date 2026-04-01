"""PawPal+ Streamlit UI — connects directly to pawpal_system.py logic layer."""

import streamlit as st

# ── Step 1: Import the logic layer ───────────────────────────────────────────
from pawpal_system import Task, Pet, Owner, Scheduler

# ── Step 2: Session-state "memory" — persist Owner across re-runs ─────────────
# st.session_state acts like a dictionary that survives button clicks.
# We only create the Owner once; every re-run reuses the existing object.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="My Household", email="owner@pawpal.com")

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")
st.caption("Smart pet care management — keeping your furry friends happy and healthy.")

# ── Sidebar — owner settings ──────────────────────────────────────────────────
with st.sidebar:
    st.header("Owner Settings")
    new_name = st.text_input("Your name", value=owner.name)
    if new_name != owner.name:
        owner.name = new_name

    st.divider()
    st.metric("Pets registered", len(owner.owned_pets))
    total_tasks = sum(len(p.tasks) for p in owner.owned_pets)
    st.metric("Total tasks", total_tasks)
    pending_count = len(scheduler.get_pending_tasks())
    st.metric("Pending today", pending_count)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_schedule, tab_pets, tab_tasks = st.tabs(["📅 Today's Schedule", "🐶 My Pets", "➕ Add Task"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Today's Schedule
# ─────────────────────────────────────────────────────────────────────────────
with tab_schedule:
    st.subheader("Today's Schedule")

    schedule = scheduler.get_todays_schedule()
    conflicts = scheduler.detect_conflicts()

    if conflicts:
        st.warning(f"⚠️ {len(conflicts)} scheduling conflict(s) detected — multiple tasks share the same time slot.")

    if not schedule:
        st.info("No tasks scheduled yet. Add some pets and tasks to get started!")
    else:
        for pet, task in schedule:
            col_check, col_time, col_pet, col_desc, col_freq = st.columns([1, 2, 2, 4, 2])
            with col_check:
                # Unique key per task so Streamlit tracks each checkbox independently
                key = f"complete_{pet.name}_{task.description}"
                done = st.checkbox("", value=task.completed, key=key)
                if done and not task.completed:
                    scheduler.mark_task_complete(pet.name, task.description)
                    st.rerun()
            with col_time:
                st.write(f"**{task.time}**")
            with col_pet:
                st.write(pet.name)
            with col_desc:
                if task.completed:
                    st.write(f"~~{task.description}~~")
                else:
                    st.write(task.description)
            with col_freq:
                st.caption(task.frequency)

    if st.button("🔄 Reset All Tasks for Today"):
        for pet in owner.owned_pets:
            for task in pet.tasks:
                task.reset()
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — My Pets
# ─────────────────────────────────────────────────────────────────────────────
with tab_pets:
    st.subheader("My Pets")

    # ── Step 3: Wire "Add Pet" form to Owner.add_pet() ───────────────────────
    with st.form("add_pet_form", clear_on_submit=True):
        st.write("**Register a new pet**")
        col1, col2, col3 = st.columns(3)
        with col1:
            pet_name = st.text_input("Pet name", placeholder="e.g. Luna")
        with col2:
            species = st.selectbox("Species", ["Dog", "Cat", "Bird", "Rabbit", "Other"])
        with col3:
            age = st.number_input("Age (years)", min_value=0, max_value=30, value=1)

        submitted = st.form_submit_button("Add Pet")
        if submitted:
            if not pet_name.strip():
                st.error("Please enter a pet name.")
            elif any(p.name.lower() == pet_name.strip().lower() for p in owner.owned_pets):
                st.error(f"A pet named '{pet_name}' is already registered.")
            else:
                # This is the key wiring: form data → Pet object → Owner
                new_pet = Pet(name=pet_name.strip(), species=species, age=age)
                owner.add_pet(new_pet)
                st.success(f"✅ {pet_name} added!")
                st.rerun()

    st.divider()

    # ── Display registered pets ───────────────────────────────────────────────
    if not owner.owned_pets:
        st.info("No pets registered yet.")
    else:
        for pet in owner.owned_pets:
            with st.expander(f"🐾 {pet.name} — {pet.species}, age {pet.age}"):
                if not pet.tasks:
                    st.write("No tasks assigned yet.")
                else:
                    for task in pet.tasks:
                        status = "✓" if task.completed else "○"
                        st.write(f"  {status} **{task.time}** — {task.description} _{task.frequency}_")

                if st.button(f"Remove {pet.name}", key=f"remove_{pet.name}"):
                    owner.remove_pet(pet.name)
                    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Add Task
# ─────────────────────────────────────────────────────────────────────────────
with tab_tasks:
    st.subheader("Schedule a New Task")

    if not owner.owned_pets:
        st.warning("Add at least one pet before scheduling tasks.")
    else:
        # ── Step 3: Wire "Add Task" form to Pet.add_task() ───────────────────
        with st.form("add_task_form", clear_on_submit=True):
            pet_names = [p.name for p in owner.owned_pets]
            selected_pet = st.selectbox("Assign to pet", pet_names)

            col1, col2, col3 = st.columns(3)
            with col1:
                description = st.text_input("Task description", placeholder="e.g. Morning walk")
            with col2:
                time_str = st.time_input("Scheduled time")
            with col3:
                frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly", "once"])

            submitted = st.form_submit_button("Add Task")
            if submitted:
                if not description.strip():
                    st.error("Please enter a task description.")
                else:
                    # Format time as HH:MM string and wire to Pet.add_task()
                    formatted_time = time_str.strftime("%H:%M")
                    target_pet = next(p for p in owner.owned_pets if p.name == selected_pet)
                    target_pet.add_task(Task(
                        description=description.strip(),
                        time=formatted_time,
                        frequency=frequency
                    ))
                    st.success(f"✅ '{description}' added to {selected_pet}'s schedule at {formatted_time}.")
                    st.rerun()
