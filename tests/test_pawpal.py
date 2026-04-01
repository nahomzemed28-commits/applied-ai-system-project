"""Automated tests for PawPal+ core logic."""

import json
import os
import tempfile
from datetime import date, timedelta
import pytest
from pawpal_system import (
    Task, Pet, Owner, Scheduler,
    PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW,
)


# ── Task tests ──────────────────────────────────────────────────────────────

def test_mark_complete_changes_status():
    """Task completion status should be False by default, True after mark_complete()."""
    task = Task("Morning walk", "07:00", "daily")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_task_reset_clears_completion():
    """Calling reset() on a completed task should set completed back to False."""
    task = Task("Evening walk", "18:00", "daily")
    task.mark_complete()
    task.reset()
    assert task.completed is False


def test_next_occurrence_daily():
    """next_occurrence() for a daily task should return a task due tomorrow."""
    today = date.today()
    task = Task("Walk", "07:00", "daily", due_date=today)
    next_task = task.next_occurrence()
    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.completed is False


def test_next_occurrence_weekly():
    """next_occurrence() for a weekly task should return a task due in 7 days."""
    today = date.today()
    task = Task("Meds", "08:00", "weekly", due_date=today)
    next_task = task.next_occurrence()
    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=7)


def test_next_occurrence_once_returns_none():
    """next_occurrence() for a 'once' task should return None (no recurrence)."""
    task = Task("Vet visit", "10:00", "once")
    assert task.next_occurrence() is None


# ── Pet tests ────────────────────────────────────────────────────────────────

def test_add_task_increases_count():
    """Adding a task to a Pet should increase its task list by one."""
    pet = Pet(name="Luna", species="Dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(Task("Feeding", "08:00", "daily"))
    assert len(pet.tasks) == 1
    pet.add_task(Task("Walk", "17:00", "daily"))
    assert len(pet.tasks) == 2


def test_get_pending_tasks_excludes_completed():
    """get_pending_tasks() should only return tasks that are not completed."""
    pet = Pet(name="Mochi", species="Cat", age=2)
    t1 = Task("Feeding", "08:00", "daily")
    t2 = Task("Playtime", "12:00", "daily")
    pet.add_task(t1)
    pet.add_task(t2)
    t1.mark_complete()
    pending = pet.get_pending_tasks()
    assert len(pending) == 1
    assert pending[0].description == "Playtime"


# ── Scheduler tests ──────────────────────────────────────────────────────────

def _make_scheduler(*pets):
    """Helper: create an Owner + Scheduler with the given pets."""
    owner = Owner("Test Owner", "test@test.com")
    for pet in pets:
        owner.add_pet(pet)
    return Scheduler(owner)


def test_schedule_sorted_by_time():
    """get_todays_schedule() should return tasks in chronological order."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Evening walk", "18:00", "daily"))
    pet.add_task(Task("Morning walk", "07:00", "daily"))
    scheduler = _make_scheduler(pet)
    times = [task.time for _, task in scheduler.get_todays_schedule()]
    assert times == sorted(times)


def test_filter_by_pet_returns_only_that_pet():
    """filter_by_pet() should return only tasks belonging to the named pet."""
    luna = Pet("Luna", "Dog", 3)
    mochi = Pet("Mochi", "Cat", 5)
    luna.add_task(Task("Walk", "07:00", "daily"))
    mochi.add_task(Task("Playtime", "12:00", "daily"))
    scheduler = _make_scheduler(luna, mochi)
    result = scheduler.filter_by_pet("Luna")
    assert all(pet.name == "Luna" for pet, _ in result)
    assert len(result) == 1


def test_filter_by_status_pending():
    """filter_by_status(completed=False) should return only incomplete tasks."""
    pet = Pet("Buddy", "Dog", 1)
    t1 = Task("Walk", "07:00", "daily")
    t2 = Task("Feeding", "08:00", "daily")
    pet.add_task(t1)
    pet.add_task(t2)
    t1.mark_complete()
    scheduler = _make_scheduler(pet)
    pending = scheduler.filter_by_status(completed=False)
    assert all(not task.completed for _, task in pending)
    assert len(pending) == 1


def test_filter_by_frequency():
    """filter_by_frequency('weekly') should return only weekly tasks."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Walk", "07:00", "daily"))
    pet.add_task(Task("Meds", "08:00", "weekly"))
    scheduler = _make_scheduler(pet)
    result = scheduler.filter_by_frequency("weekly")
    assert all(task.frequency == "weekly" for _, task in result)
    assert len(result) == 1


def test_detect_conflicts_finds_same_time():
    """detect_conflicts() should flag tasks scheduled at the exact same time."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Medication", "08:00", "daily"))
    pet.add_task(Task("Feeding", "08:00", "daily"))
    scheduler = _make_scheduler(pet)
    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) > 0


def test_detect_conflicts_no_false_positives():
    """detect_conflicts() should return no conflicts when all tasks are at different times."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Walk", "07:00", "daily"))
    pet.add_task(Task("Feeding", "08:00", "daily"))
    pet.add_task(Task("Playtime", "12:00", "daily"))
    scheduler = _make_scheduler(pet)
    assert scheduler.detect_conflicts() == []


def test_mark_task_complete_via_scheduler():
    """Scheduler.mark_task_complete() should return True and mark the task done."""
    pet = Pet("Buddy", "Dog", 1)
    task = Task("Morning walk", "07:00", "daily")
    pet.add_task(task)
    scheduler = _make_scheduler(pet)
    result = scheduler.mark_task_complete("Buddy", "Morning walk")
    assert result is True
    assert task.completed is True


def test_recurring_task_appends_next_occurrence():
    """Completing a daily task via the Scheduler should add a new pending task for tomorrow."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Walk", "07:00", "daily"))
    scheduler = _make_scheduler(pet)
    scheduler.mark_task_complete("Buddy", "Walk")
    assert len(pet.tasks) == 2
    assert pet.tasks[-1].completed is False
    assert pet.tasks[-1].due_date == date.today() + timedelta(days=1)


def test_once_task_does_not_recur():
    """Completing a 'once' task via the Scheduler should NOT add a new task."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Vet visit", "10:00", "once"))
    scheduler = _make_scheduler(pet)
    scheduler.mark_task_complete("Buddy", "Vet visit")
    assert len(pet.tasks) == 1


# ── Edge case tests ──────────────────────────────────────────────────────────

def test_pet_with_no_tasks_returns_empty_schedule():
    """A pet with no tasks should produce an empty schedule without errors."""
    pet = Pet("Empty", "Dog", 2)
    scheduler = _make_scheduler(pet)
    assert scheduler.get_todays_schedule() == []


def test_owner_with_no_pets_returns_empty_schedule():
    """An owner with no pets should produce an empty schedule without errors."""
    scheduler = _make_scheduler()  # no pets
    assert scheduler.get_todays_schedule() == []
    assert scheduler.get_pending_tasks() == []
    assert scheduler.detect_conflicts() == []


def test_mark_task_complete_unknown_pet_returns_false():
    """mark_task_complete() should return False when the pet name doesn't exist."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Walk", "07:00", "daily"))
    scheduler = _make_scheduler(pet)
    result = scheduler.mark_task_complete("Ghost", "Walk")
    assert result is False


def test_mark_task_complete_unknown_task_returns_false():
    """mark_task_complete() should return False when the task description doesn't match."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Walk", "07:00", "daily"))
    scheduler = _make_scheduler(pet)
    result = scheduler.mark_task_complete("Buddy", "Nonexistent task")
    assert result is False


def test_conflict_warning_message_is_readable():
    """ConflictWarning.message() should return a non-empty human-readable string."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Feeding", "08:00", "daily"))
    pet.add_task(Task("Meds", "08:00", "daily"))
    scheduler = _make_scheduler(pet)
    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) == 1
    msg = conflicts[0].message()
    assert "08:00" in msg
    assert "Feeding" in msg
    assert "Meds" in msg


def test_filter_by_pet_case_insensitive():
    """filter_by_pet() should match pet names regardless of case."""
    pet = Pet("Luna", "Dog", 3)
    pet.add_task(Task("Walk", "07:00", "daily"))
    scheduler = _make_scheduler(pet)
    assert len(scheduler.filter_by_pet("luna")) == 1
    assert len(scheduler.filter_by_pet("LUNA")) == 1


def test_all_tasks_complete_leaves_no_pending():
    """After completing every task, get_pending_tasks() should return an empty list."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Walk", "07:00", "once"))
    pet.add_task(Task("Feeding", "08:00", "once"))
    scheduler = _make_scheduler(pet)
    scheduler.mark_task_complete("Buddy", "Walk")
    scheduler.mark_task_complete("Buddy", "Feeding")
    assert scheduler.get_pending_tasks() == []


def test_next_occurrence_preserves_description_and_time():
    """next_occurrence() should copy the description and time from the original task."""
    task = Task("Morning walk", "07:30", "daily")
    next_task = task.next_occurrence()
    assert next_task.description == "Morning walk"
    assert next_task.time == "07:30"
    assert next_task.frequency == "daily"


def test_remove_task_from_pet():
    """remove_task() should delete the matching task and leave others intact."""
    pet = Pet("Luna", "Dog", 3)
    pet.add_task(Task("Walk", "07:00", "daily"))
    pet.add_task(Task("Feeding", "08:00", "daily"))
    pet.remove_task("Walk")
    assert len(pet.tasks) == 1
    assert pet.tasks[0].description == "Feeding"


# ── Priority tests ───────────────────────────────────────────────────────────

def test_task_default_priority_is_medium():
    """A Task created without an explicit priority should default to 'medium'."""
    task = Task("Walk", "07:00", "daily")
    assert task.priority == PRIORITY_MEDIUM


def test_priority_sort_high_before_medium_before_low():
    """get_todays_schedule() should order: high tasks first, then medium, then low."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Grooming",  "10:00", "once",  priority=PRIORITY_LOW))
    pet.add_task(Task("Walk",      "10:00", "daily", priority=PRIORITY_MEDIUM))
    pet.add_task(Task("Meds",      "10:00", "daily", priority=PRIORITY_HIGH))
    scheduler = _make_scheduler(pet)
    priorities = [task.priority for _, task in scheduler.get_todays_schedule()]
    assert priorities == [PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW]


def test_high_priority_sorted_before_lower_at_same_time():
    """Within the same time slot, a high-priority task should appear before a low-priority one."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Playtime", "09:00", "daily", priority=PRIORITY_LOW))
    pet.add_task(Task("Meds",     "09:00", "daily", priority=PRIORITY_HIGH))
    scheduler = _make_scheduler(pet)
    schedule = scheduler.get_todays_schedule()
    assert schedule[0][1].priority == PRIORITY_HIGH


def test_filter_by_priority_returns_only_matching():
    """filter_by_priority('high') should return only high-priority tasks."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Meds",     "08:00", "daily", priority=PRIORITY_HIGH))
    pet.add_task(Task("Walk",     "09:00", "daily", priority=PRIORITY_MEDIUM))
    pet.add_task(Task("Grooming", "10:00", "once",  priority=PRIORITY_LOW))
    scheduler = _make_scheduler(pet)
    result = scheduler.filter_by_priority(PRIORITY_HIGH)
    assert len(result) == 1
    assert result[0][1].priority == PRIORITY_HIGH


def test_next_occurrence_preserves_priority():
    """next_occurrence() should carry the same priority level to the new task."""
    task = Task("Meds", "08:00", "daily", priority=PRIORITY_HIGH)
    next_task = task.next_occurrence()
    assert next_task.priority == PRIORITY_HIGH


# ── JSON persistence tests ────────────────────────────────────────────────────

def _round_trip(owner: Owner) -> Owner:
    """Save owner to a temp file and reload it; return the reloaded Owner."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        owner.save_to_json(path)
        return Owner.load_from_json(path)
    finally:
        os.unlink(path)


def test_save_and_load_preserves_pet_names():
    """After a save/load round trip, pet names should be identical."""
    owner = Owner("Test", "t@t.com")
    owner.add_pet(Pet("Luna", "Dog", 3))
    owner.add_pet(Pet("Mochi", "Cat", 5))
    reloaded = _round_trip(owner)
    assert [p.name for p in reloaded.owned_pets] == ["Luna", "Mochi"]


def test_save_and_load_preserves_task_count():
    """After a save/load round trip, the total task count must match exactly."""
    owner = Owner("Test", "t@t.com")
    pet = Pet("Luna", "Dog", 3)
    pet.add_task(Task("Walk",    "07:00", "daily",  priority=PRIORITY_MEDIUM))
    pet.add_task(Task("Feeding", "08:00", "daily",  priority=PRIORITY_HIGH))
    pet.add_task(Task("Meds",    "09:00", "weekly", priority=PRIORITY_HIGH))
    owner.add_pet(pet)
    reloaded = _round_trip(owner)
    assert len(reloaded.owned_pets[0].tasks) == 3


def test_save_and_load_preserves_priority():
    """Priority levels must survive the JSON serialization round trip."""
    owner = Owner("Test", "t@t.com")
    pet = Pet("Luna", "Dog", 3)
    pet.add_task(Task("Meds", "08:00", "daily", priority=PRIORITY_HIGH))
    owner.add_pet(pet)
    reloaded = _round_trip(owner)
    assert reloaded.owned_pets[0].tasks[0].priority == PRIORITY_HIGH


def test_save_and_load_preserves_completion_status():
    """A completed task should still be marked completed after a round trip."""
    owner = Owner("Test", "t@t.com")
    pet = Pet("Luna", "Dog", 3)
    task = Task("Walk", "07:00", "once")
    task.mark_complete()
    pet.add_task(task)
    owner.add_pet(pet)
    reloaded = _round_trip(owner)
    assert reloaded.owned_pets[0].tasks[0].completed is True


def test_load_from_nonexistent_file_returns_blank_owner():
    """load_from_json() on a missing file should return a blank Owner, not raise."""
    owner = Owner.load_from_json("/tmp/__does_not_exist_pawpal__.json")
    assert isinstance(owner, Owner)
    assert len(owner.owned_pets) == 0


# ── Slot suggester tests ──────────────────────────────────────────────────────

def test_next_available_slot_skips_occupied():
    """next_available_slot() should skip times that already have a task."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Walk",    "07:00", "daily"))
    pet.add_task(Task("Feeding", "07:30", "daily"))
    scheduler = _make_scheduler(pet)
    # Both 07:00 and 07:30 are taken; next 30-min slot after 06:30 should be 08:00
    slot = scheduler.next_available_slot(after="06:30", step_minutes=30)
    assert slot == "08:00"


def test_suggest_slots_returns_requested_count():
    """suggest_slots() should return exactly `count` slots when enough are free."""
    pet = Pet("Buddy", "Dog", 1)
    pet.add_task(Task("Walk", "07:00", "daily"))
    scheduler = _make_scheduler(pet)
    suggestions = scheduler.suggest_slots(count=4, step_minutes=30)
    assert len(suggestions) == 4


def test_suggest_slots_are_all_unique():
    """suggest_slots() should never return duplicate time slots."""
    pet = Pet("Buddy", "Dog", 1)
    scheduler = _make_scheduler(pet)
    suggestions = scheduler.suggest_slots(count=5, step_minutes=60)
    assert len(suggestions) == len(set(suggestions))
