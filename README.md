# PawPal+ 🐾

A smart pet care management system that helps owners keep their furry friends happy and healthy.

## Overview

PawPal+ is an intelligent pet care management application designed to help pet owners manage daily routines including:
- **Feedings** - Track and schedule regular meal times for each pet
- **Walks** - Log exercise and outdoor time
- **Medications** - Set reminders for vital medication schedules
- **Appointments** - Manage vet visits and grooming appointments

The system uses algorithmic logic to organize and prioritize tasks, helping owners stay on top of their pets' care needs.

## Key Features

- Track multiple pets and their individual care requirements
- Organize daily tasks with intelligent scheduling
- Detect scheduling conflicts
- Manage recurring vs. one-time tasks
- View today's tasks prioritized by importance

## Technology Stack

- **Backend**: Python with Object-Oriented Programming (OOP)
- **UI**: Streamlit (modern web dashboard)
- **Testing**: pytest for automated test suites

## Project Structure

```
PawPal/
├── pawpal_system.py      # Core business logic and classes
├── demo.py              # CLI demo script for testing backend
├── test_pawpal.py       # Automated test suite
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── reflection.md       # Design reflection and learnings
```

## Smarter Scheduling

PawPal+ includes algorithmic intelligence built into the `Scheduler` class:

- **Sorting** — `get_todays_schedule()` sorts all tasks chronologically using Python's `sorted()` with a `lambda` key on the `"HH:MM"` time string. Tasks can be added in any order and will always display correctly.
- **Filtering** — Tasks can be filtered by pet name (`filter_by_pet()`), completion status (`filter_by_status()`), or recurrence frequency (`filter_by_frequency()`), all returning sorted results.
- **Recurring tasks** — Completing a `daily`, `weekly`, or `monthly` task via `mark_task_complete()` automatically appends the next occurrence using Python's `timedelta`. `once` tasks do not recur.
- **Conflict detection** — `detect_conflicts()` groups tasks by time slot and returns `ConflictWarning` objects for any slot with more than one task. It returns warnings instead of raising exceptions, so the app never crashes on scheduling issues.

## Getting Started

### Phase 1: System Design with UML + AI Support
- Design modular system architecture using OOP
- Create UML diagrams to visualize relationships
- Implement class skeletons

### Phase 2: Core Logic Implementation
- Build scheduling algorithms
- Implement conflict detection
- Handle recurring tasks

### Phase 3: CLI Verification
- Create demo script to test system behavior
- Write pytest test suites

### Phase 4: Streamlit UI
- Create modern web dashboard
- Connect to backend logic

## Testing PawPal+

Run the full test suite with:

```bash
python -m pytest
```

**What the tests cover (25 tests, all passing):**

| Category | Tests | What's verified |
|---|---|---|
| Task basics | 5 | Default status, `mark_complete()`, `reset()`, `next_occurrence()` for daily/weekly/once |
| Pet management | 3 | Task count grows on `add_task()`, pending filter excludes completed, `remove_task()` |
| Sorting | 1 | Tasks added out of order are returned chronologically |
| Filtering | 3 | Filter by pet (case-insensitive), by status, by frequency |
| Conflict detection | 3 | Same-time tasks flagged, no false positives, warning message is human-readable |
| Recurring tasks | 3 | Daily appends next-day task, weekly appends +7 days, `once` does not recur |
| Edge cases | 7 | Empty pet, owner with no pets, unknown pet/task lookup returns False, all tasks complete = no pending |

**Confidence Level: ★★★★☆ (4/5)**

The core scheduling logic — sorting, filtering, conflict detection, and recurrence — is well covered. One-star deducted because task durations are not modeled, so overlapping-but-not-exact-time conflicts are not detected or tested.

## Installation

```bash
pip install -r requirements.txt
```

## License

MIT License
