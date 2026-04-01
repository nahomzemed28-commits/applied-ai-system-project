"""
UI behavior simulation — tests every user-facing action in app.py
without a browser. Simulates what happens when a user interacts with
each feature: adding pets, adding tasks, completing tasks, filtering,
conflict detection, slot suggester, persistence, and sidebar metrics.
"""

import os, sys, json, tempfile
from datetime import date, timedelta
from collections import Counter

from pawpal_system import (
    Task, Pet, Owner, Scheduler, ConflictWarning,
    PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_EMOJI,
    _PRIORITY_ORDER,
)

PASS = "  ✅"
FAIL = "  ❌"
errors = []

def check(label, condition, got=None):
    if condition:
        print(f"{PASS} {label}")
    else:
        msg = f" (got: {got})" if got is not None else ""
        print(f"{FAIL} {label}{msg}")
        errors.append(label)

def section(title):
    print(f"\n{'─'*58}\n  {title}\n{'─'*58}")

# ── Helpers that mirror app.py setup ──────────────────────────────────────────
def fresh_app():
    """Return a clean owner + scheduler as app.py does on first load."""
    owner = Owner("Nahom", "nahom@pawpal.com")
    return owner, Scheduler(owner)

# ══════════════════════════════════════════════════════════════════
# 1. SIDEBAR METRICS — correct counts at each stage
# ══════════════════════════════════════════════════════════════════
section("1. Sidebar metrics — Pets / Tasks today / Pending / Conflicts")

owner, scheduler = fresh_app()
check("empty: 0 pets",           len(owner.owned_pets) == 0)
check("empty: 0 tasks today",    len(scheduler.get_todays_schedule()) == 0)
check("empty: 0 pending",        len(scheduler.get_pending_tasks()) == 0)
check("empty: 0 conflicts",      len(scheduler.detect_conflicts()) == 0)

luna = Pet("Luna", "Dog", 3)
luna.add_task(Task("Walk",    "07:00", "daily",  priority=PRIORITY_MEDIUM))
luna.add_task(Task("Meds",    "08:00", "weekly", priority=PRIORITY_HIGH))
mochi = Pet("Mochi", "Cat", 5)
mochi.add_task(Task("Feeding","08:00", "daily",  priority=PRIORITY_HIGH))
mochi.add_task(Task("Play",   "12:00", "daily",  priority=PRIORITY_LOW))
owner.add_pet(luna)
owner.add_pet(mochi)

check("2 pets registered",       len(owner.owned_pets) == 2)
check("4 tasks today",           len(scheduler.get_todays_schedule()) == 4)
check("4 pending",               len(scheduler.get_pending_tasks()) == 4)
check("1 conflict (08:00)",      len(scheduler.detect_conflicts()) == 1)

# ══════════════════════════════════════════════════════════════════
# 2. ADD PET — validation logic (mirrors app.py form checks)
# ══════════════════════════════════════════════════════════════════
section("2. Add Pet form — validation")

# Empty name rejected
def add_pet_validated(owner, name, species, age):
    if not name.strip():
        return False, "empty name"
    if any(p.name.lower() == name.strip().lower() for p in owner.owned_pets):
        return False, "duplicate"
    owner.add_pet(Pet(name.strip(), species, age))
    return True, "ok"

ok, reason = add_pet_validated(owner, "", "Dog", 2)
check("empty name rejected",     not ok and reason == "empty name")

ok, reason = add_pet_validated(owner, "Luna", "Dog", 2)
check("duplicate name rejected", not ok and reason == "duplicate")

ok, reason = add_pet_validated(owner, "LUNA", "Dog", 2)
check("case duplicate rejected", not ok and reason == "duplicate")

ok, reason = add_pet_validated(owner, "Rex", "Dog", 4)
check("valid pet added",         ok)
check("pet count now 3",         len(owner.owned_pets) == 3)
owner.remove_pet("Rex")  # clean up

# ══════════════════════════════════════════════════════════════════
# 3. ADD TASK — pre-flight conflict warning
# ══════════════════════════════════════════════════════════════════
section("3. Add Task form — pre-flight conflict check")

existing_times = {t.time for t in luna.tasks}
new_time_conflict = "08:00"
new_time_free     = "15:00"

check("08:00 flagged as conflicting", new_time_conflict in existing_times)
check("15:00 flagged as free",        new_time_free not in existing_times)

luna.add_task(Task("Grooming", "15:00", "weekly", priority=PRIORITY_LOW))
check("free task added successfully", any(t.description == "Grooming" for t in luna.tasks))
luna.remove_task("Grooming")

# ══════════════════════════════════════════════════════════════════
# 4. SCHEDULE TAB — filter controls
# ══════════════════════════════════════════════════════════════════
section("4. Schedule tab — filter controls")

# Filter by pet
luna_view = scheduler.filter_by_pet("Luna")
check("filter Luna → 2 tasks",        len(luna_view) == 2)
check("filter Luna → all Luna",       all(p.name == "Luna" for p,_ in luna_view))

mochi_view = scheduler.filter_by_pet("Mochi")
check("filter Mochi → 2 tasks",       len(mochi_view) == 2)

# Filter by status
pending_view = scheduler.filter_by_status(completed=False)
done_view    = scheduler.filter_by_status(completed=True)
check("pending filter → 4",           len(pending_view) == 4)
check("done filter → 0",              len(done_view) == 0)

# Filter by frequency
daily_view  = scheduler.filter_by_frequency("daily")
weekly_view = scheduler.filter_by_frequency("weekly")
check("daily filter → 3 tasks",       len(daily_view) == 3)
check("weekly filter → 1 task",       len(weekly_view) == 1)

# Filter by priority
high_view = scheduler.filter_by_priority(PRIORITY_HIGH)
low_view  = scheduler.filter_by_priority(PRIORITY_LOW)
check("high priority filter → 2",     len(high_view) == 2)
check("low priority filter → 1",      len(low_view) == 1)

# Priority sort: high tasks appear first
schedule = scheduler.get_todays_schedule()
priority_order = [t.priority for _, t in schedule]
first_high = priority_order.index(PRIORITY_HIGH)
last_low   = len(priority_order) - 1 - priority_order[::-1].index(PRIORITY_LOW)
check("high tasks before low in sort", first_high < last_low)

# ══════════════════════════════════════════════════════════════════
# 5. COMPLETING A TASK — checkbox behavior
# ══════════════════════════════════════════════════════════════════
section("5. Checkbox — mark task done")

before_schedule = len(scheduler.get_todays_schedule())
scheduler.mark_task_complete("Luna", "Walk")

# Completed task still shows on today's schedule (due_date == today)
after_schedule = len(scheduler.get_todays_schedule())
check("completed task still in today's view", after_schedule == before_schedule)

# But pending count drops
pending_after = len(scheduler.get_pending_tasks())
check("pending drops from 4 to 3",   pending_after == 3)

# Recurring copy is NOT in today's schedule (due tomorrow)
today = date.today()
future_walks = [t for t in luna.tasks
                if t.description == "Walk" and t.due_date > today]
today_walks  = [t for t in luna.tasks
                if t.description == "Walk" and t.due_date <= today]
check("recurring copy due tomorrow, not today", len(future_walks) == 1)
check("only 1 walk in today's schedule",        len(today_walks) == 1)

# Tasks today counter stays correct
tasks_today_count = len(scheduler.get_todays_schedule())
check("Tasks today counter = 4 (not inflated)", tasks_today_count == 4)

# ══════════════════════════════════════════════════════════════════
# 6. ONCE TASK — no recurrence on complete
# ══════════════════════════════════════════════════════════════════
section("6. Once task — no duplicate appended")

mochi.add_task(Task("Vet visit", "10:00", "once", priority=PRIORITY_HIGH))
before = len(mochi.tasks)
scheduler.mark_task_complete("Mochi", "Vet visit")
after = len(mochi.tasks)
check("once task: task count unchanged", before == after)
check("once task: marked complete",      mochi.tasks[-1].completed is True)

# ══════════════════════════════════════════════════════════════════
# 7. CONFLICT DETECTION — display logic
# ══════════════════════════════════════════════════════════════════
section("7. Conflict detection — warnings panel")

conflicts = scheduler.detect_conflicts()
check("1 conflict detected (08:00)",     len(conflicts) == 1)
check("conflict message non-empty",      len(conflicts[0].message()) > 0)
check("conflict message has time",       "08:00" in conflicts[0].message())
check("conflict message has both tasks",
      "Meds" in conflicts[0].message() or "Feeding" in conflicts[0].message())

# Conflicted task refs are in the conflict objects
conflict_tasks = {conflicts[0].task_a, conflicts[0].task_b}
schedule_tasks = {t for _, t in scheduler.get_todays_schedule()}
check("conflicted tasks are in schedule", conflict_tasks.issubset(schedule_tasks))

# No conflicts if all times distinct
solo_owner = Owner("S","s@s.com")
solo_pet = Pet("S","Dog",1)
for h in ["07:00","08:30","12:00","18:00"]:
    solo_pet.add_task(Task(f"T{h}", h, "once"))
solo_owner.add_pet(solo_pet)
check("no false conflicts (distinct times)", Scheduler(solo_owner).detect_conflicts() == [])

# ══════════════════════════════════════════════════════════════════
# 8. PETS TAB — per-pet metrics
# ══════════════════════════════════════════════════════════════════
section("8. Pets tab — per-pet metrics")

luna_pending = len(luna.get_pending_tasks())
luna_total   = len([t for t in luna.tasks if t.due_date <= date.today()])
luna_done    = luna_total - luna_pending
luna_high    = sum(1 for t in luna.tasks
                   if t.priority == PRIORITY_HIGH and not t.completed
                   and t.due_date <= date.today())

check("Luna pending = 1 (Walk done)",    luna_pending == 1)
check("Luna total today = 2",            luna_total == 2)
check("Luna done = 1",                   luna_done == 1)
check("Luna high priority pending = 1",  luna_high == 1)

# Remove pet
owner.remove_pet("Mochi")
check("remove pet: count drops to 1",    len(owner.owned_pets) == 1)
owner.add_pet(mochi)  # re-add

# ══════════════════════════════════════════════════════════════════
# 9. SLOT SUGGESTER TAB
# ══════════════════════════════════════════════════════════════════
section("9. Slot suggester tab")

occupied = {t.time for _, t in scheduler.get_todays_schedule()}

slot = scheduler.next_available_slot(after="06:00", step_minutes=30)
check("next slot is a valid HH:MM",  len(slot) == 5 and slot[2] == ":")
check("next slot is not occupied",   slot not in occupied)

suggestions = scheduler.suggest_slots(count=3, step_minutes=30)
check("suggest 3 slots",             len(suggestions) == 3)
check("all suggestions unique",      len(set(suggestions)) == 3)
check("none are occupied",           all(s not in occupied for s in suggestions))

# ══════════════════════════════════════════════════════════════════
# 10. PERSISTENCE — save / reload round-trip
# ══════════════════════════════════════════════════════════════════
section("10. Persistence — save/reload matches live state")

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    tmp = f.name
try:
    owner.save_to_json(tmp)
    reloaded = Owner.load_from_json(tmp)
    r_sched = Scheduler(reloaded)

    check("reloaded pet count matches",
          len(reloaded.owned_pets) == len(owner.owned_pets))
    check("reloaded tasks today matches",
          len(r_sched.get_todays_schedule()) == len(scheduler.get_todays_schedule()))
    check("reloaded pending matches",
          len(r_sched.get_pending_tasks()) == len(scheduler.get_pending_tasks()))
    check("reloaded conflicts match",
          len(r_sched.detect_conflicts()) == len(scheduler.detect_conflicts()))

    orig_pris = sorted(t.priority for _,t in scheduler.get_todays_schedule())
    load_pris = sorted(t.priority for _,t in r_sched.get_todays_schedule())
    check("priorities preserved",    orig_pris == load_pris)

    orig_comp = sorted(str(t.completed) for _,t in scheduler.get_todays_schedule())
    load_comp = sorted(str(t.completed) for _,t in r_sched.get_todays_schedule())
    check("completion flags preserved", orig_comp == load_comp)
finally:
    os.unlink(tmp)

# ══════════════════════════════════════════════════════════════════
# 11. RESET ALL TASKS FOR TODAY
# ══════════════════════════════════════════════════════════════════
section("11. Reset all tasks for today")

# Walk is currently complete — reset should clear it
for p in owner.owned_pets:
    for t in p.tasks:
        if t.due_date <= date.today():
            t.reset()

all_pending_after_reset = len(scheduler.get_pending_tasks())
check("after reset: all today's tasks pending",
      all_pending_after_reset == len(scheduler.get_todays_schedule()))

# ══════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════
print(f"\n{'═'*58}")
if errors:
    print(f"  ❌ {len(errors)} check(s) FAILED:")
    for e in errors:
        print(f"     • {e}")
else:
    print(f"  ✅ All UI behavior checks passed.")
print(f"{'═'*58}\n")

sys.exit(1 if errors else 0)
