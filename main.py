"""Demo script verifying all features including priority scheduling, persistence, and slot suggestion."""

import os
from pawpal_system import (
    Task, Pet, Owner, Scheduler,
    PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW, PRIORITY_EMOJI,
)


def section(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


def main():
    # ── Setup ──────────────────────────────────────────────────────────────────
    owner = Owner(name="Nahom", email="nahom@pawpal.com")
    luna  = Pet(name="Luna",  species="Dog", age=3)
    mochi = Pet(name="Mochi", species="Cat", age=5)
    owner.add_pet(luna)
    owner.add_pet(mochi)

    # Tasks with mixed priorities and out-of-order times
    luna.add_task(Task("Evening walk",       "18:00", "daily",   priority=PRIORITY_MEDIUM))
    luna.add_task(Task("Heartworm meds",     "08:00", "weekly",  priority=PRIORITY_HIGH))
    luna.add_task(Task("Morning walk",       "07:00", "daily",   priority=PRIORITY_MEDIUM))
    luna.add_task(Task("Breakfast feeding",  "08:00", "daily",   priority=PRIORITY_HIGH))   # conflict

    mochi.add_task(Task("Playtime",          "12:00", "daily",   priority=PRIORITY_LOW))
    mochi.add_task(Task("Breakfast feeding", "08:00", "daily",   priority=PRIORITY_HIGH))   # conflict
    mochi.add_task(Task("Flea treatment",    "19:00", "once",    priority=PRIORITY_MEDIUM))

    scheduler = Scheduler(owner)

    # ── 1. Priority + Time Sort ────────────────────────────────────────────────
    section("1. Priority-sorted schedule (High tasks appear first within each time slot)")
    scheduler.print_schedule()

    # ── 2. Filter by priority ──────────────────────────────────────────────────
    section("2. Filter — HIGH priority tasks only")
    scheduler.print_schedule(scheduler.filter_by_priority(PRIORITY_HIGH))

    section("3. Filter — LOW priority tasks only")
    scheduler.print_schedule(scheduler.filter_by_priority(PRIORITY_LOW))

    # ── 3. Conflict detection ──────────────────────────────────────────────────
    section("4. Conflict detection")
    for w in scheduler.detect_conflicts():
        print(f"  {w.message()}")

    # ── 4. Recurring task with priority preserved ──────────────────────────────
    section("5. Complete 'Heartworm meds' (High, weekly) — next occurrence should keep HIGH priority")
    scheduler.mark_task_complete("Luna", "Heartworm meds")
    newest = luna.tasks[-1]
    print(f"  New task: {newest}")
    print(f"  Priority preserved: {PRIORITY_EMOJI[newest.priority]} {newest.priority}")

    # ── 5. Next available slot ─────────────────────────────────────────────────
    section("6. Next available slot (30-min steps) after 07:30")
    slot = scheduler.next_available_slot(after="07:30", step_minutes=30)
    print(f"  Next free slot: {slot}")

    section("7. Top 4 suggested free slots (15-min steps from 06:00)")
    suggestions = scheduler.suggest_slots(count=4, step_minutes=15)
    for s in suggestions:
        print(f"  🕐 {s}")

    # ── 6. JSON persistence ────────────────────────────────────────────────────
    section("8. Save → load round-trip (JSON persistence)")
    test_file = "/tmp/pawpal_test.json"
    owner.save_to_json(test_file)
    reloaded = Owner.load_from_json(test_file)
    print(f"  Original pets : {[p.name for p in owner.owned_pets]}")
    print(f"  Reloaded pets : {[p.name for p in reloaded.owned_pets]}")
    orig_tasks = sum(len(p.tasks) for p in owner.owned_pets)
    load_tasks = sum(len(p.tasks) for p in reloaded.owned_pets)
    print(f"  Task count    : {orig_tasks} → {load_tasks} (match: {orig_tasks == load_tasks})")
    # Verify priority round-trips
    orig_pris  = [t.priority for p in owner.owned_pets for t in p.tasks]
    load_pris  = [t.priority for p in reloaded.owned_pets for t in p.tasks]
    print(f"  Priorities match: {orig_pris == load_pris}")
    os.remove(test_file)


if __name__ == "__main__":
    main()
