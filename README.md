# PawPal+ 🐾

A smart pet care management system built with Python and Streamlit. PawPal+ helps pet owners schedule, track, and organize their pets' daily care routines — with intelligent sorting, filtering, recurring task automation, and conflict detection.

---

## 📸 Demo

<!-- Replace the path below with your actual screenshot once captured -->
<a href="/course_images/ai110/pawpal_screenshot.png" target="_blank">
  <img src='/course_images/ai110/pawpal_screenshot.png' title='PawPal+ App' width='' alt='PawPal App' class='center-block' />
</a>

---

## Features

### Core Management
- **Multiple pets** — Register and manage any number of pets, each with their own profile (name, species, age) and independent task list
- **Flexible tasks** — Each task stores a description, scheduled time (`HH:MM`), frequency, due date, and completion status

### Algorithmic Intelligence (Scheduler class)
- **Chronological sorting** — `get_todays_schedule()` uses Python's `sorted()` with a `lambda` key on the `HH:MM` time string; tasks added in any order always display correctly
- **Multi-axis filtering** — Filter the schedule by pet name (`filter_by_pet()`), completion status (`filter_by_status()`), or recurrence frequency (`filter_by_frequency()`); filters compose and return sorted results
- **Recurring task automation** — Completing a `daily`, `weekly`, or `monthly` task via `mark_task_complete()` automatically appends the next occurrence using Python's `timedelta`; `once` tasks do not recur
- **Conflict detection** — `detect_conflicts()` groups tasks by time slot using a `defaultdict` and returns typed `ConflictWarning` objects with human-readable `.message()` strings — warns without crashing

### Streamlit UI
- **Live filter controls** — Pet dropdown, status radio, and frequency selector dynamically filter the schedule table
- **Inline conflict highlighting** — Conflicting rows appear in orange with ⚠️; an expandable conflict panel shows one warning per clash
- **Pre-flight conflict check** — When adding a new task, the UI warns immediately if the chosen time already has a task for that pet
- **Per-pet metrics** — Each pet card shows Total / Pending / Done counts at a glance
- **Live sidebar stats** — Pets, total tasks, pending count, and a green/red conflict indicator update on every interaction

---

## System Architecture

See [uml_final.md](uml_final.md) for the complete Mermaid.js class diagram.

**Five classes, one clear hierarchy:**

```
Owner ──owns──▶ Pet ──has──▶ Task ──next_occurrence()──▶ Task
  ▲
  └── Scheduler (reads Owner, produces ConflictWarning)
```

---

## Project Structure

```
PawPal/
├── pawpal_system.py      # Core business logic (Task, Pet, Owner, Scheduler, ConflictWarning)
├── app.py               # Streamlit web dashboard
├── main.py              # CLI demo script — run to verify backend in terminal
├── tests/
│   └── test_pawpal.py   # 25 automated pytest tests
├── uml_final.md         # Final Mermaid.js UML class diagram
├── requirements.txt     # Python dependencies
├── reflection.md        # Design reflection and AI collaboration notes
└── README.md            # This file
```

---

## Smarter Scheduling

| Algorithm | Method | Complexity |
|---|---|---|
| Chronological sort | `get_todays_schedule()` | O(n log n) |
| Filter by pet | `filter_by_pet(name)` | O(n) |
| Filter by status | `filter_by_status(completed)` | O(n) |
| Filter by frequency | `filter_by_frequency(freq)` | O(n) |
| Conflict detection | `detect_conflicts()` | O(n) grouping + O(k²) per slot |
| Recurring scheduling | `mark_task_complete()` + `next_occurrence()` | O(1) per task |

**Known tradeoff:** Conflict detection matches exact `HH:MM` slots only. Tasks with overlapping durations at different start times are not flagged. See [reflection.md](reflection.md) section 2b for full analysis.

---

## Testing PawPal+

Run the full test suite:

```bash
python -m pytest
```

**Coverage (25 tests, all passing):**

| Category | Count | What's verified |
|---|---|---|
| Task basics | 5 | Default status, `mark_complete()`, `reset()`, `next_occurrence()` for daily/weekly/once |
| Pet management | 3 | Task count grows, pending filter excludes completed, `remove_task()` |
| Sorting | 1 | Out-of-order tasks return chronologically |
| Filtering | 3 | Filter by pet (case-insensitive), status, frequency |
| Conflict detection | 3 | Same-time tasks flagged, no false positives, warning message readable |
| Recurring tasks | 3 | Daily → +1 day, weekly → +7 days, `once` → no recurrence |
| Edge cases | 7 | Empty pet, no-pet owner, unknown lookups return False, case-insensitive pet match |

**Confidence Level: ★★★★☆ (4/5)** — Core logic fully covered; duration-based overlap detection is the known untested gap.

---

## Installation

```bash
pip install -r requirements.txt
```

## Running the App

```bash
# Launch Streamlit UI
streamlit run app.py

# Verify backend logic in terminal
python3 main.py

# Run tests
python -m pytest
```

---

## License

MIT License
