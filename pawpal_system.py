"""PawPal+ core business logic: Task, Pet, Owner, Scheduler, ConflictWarning."""

import json
from datetime import date, timedelta
from collections import defaultdict
from pathlib import Path

# ── Priority constants ────────────────────────────────────────────────────────
PRIORITY_HIGH   = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW    = "low"

# Sort key: lower number = higher priority in the sorted output
_PRIORITY_ORDER = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}

# UI badges used by both CLI and Streamlit
PRIORITY_EMOJI = {PRIORITY_HIGH: "🔴", PRIORITY_MEDIUM: "🟡", PRIORITY_LOW: "🟢"}


class Task:
    """Represents a single pet care activity with description, time, frequency, priority, and status."""

    _RECURRENCE_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}

    def __init__(self, description: str, time: str, frequency: str = "daily",
                 due_date: date | None = None, priority: str = PRIORITY_MEDIUM):
        """Initialize a Task with description, time, frequency, due date, and priority."""
        self.description = description
        self.time = time              # "HH:MM" 24-hour string
        self.frequency = frequency   # "daily" | "weekly" | "monthly" | "once"
        self.due_date = due_date or date.today()
        self.priority = priority     # "high" | "medium" | "low"
        self.completed = False

    def mark_complete(self):
        """Mark this task as completed."""
        self.completed = True

    def reset(self):
        """Reset completion status (e.g. at the start of a new day)."""
        self.completed = False

    def next_occurrence(self) -> "Task | None":
        """Return a fresh Task for the next scheduled occurrence, or None if frequency is 'once'."""
        days = self._RECURRENCE_DAYS.get(self.frequency)
        if days is None:
            return None
        return Task(self.description, self.time, self.frequency,
                    self.due_date + timedelta(days=days), self.priority)

    def to_dict(self) -> dict:
        """Serialize this Task to a JSON-compatible dictionary."""
        return {
            "description": self.description,
            "time": self.time,
            "frequency": self.frequency,
            "due_date": self.due_date.isoformat(),
            "priority": self.priority,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Deserialize a Task from a dictionary (inverse of to_dict)."""
        task = cls(
            description=data["description"],
            time=data["time"],
            frequency=data.get("frequency", "daily"),
            due_date=date.fromisoformat(data["due_date"]),
            priority=data.get("priority", PRIORITY_MEDIUM),
        )
        task.completed = data.get("completed", False)
        return task

    def __repr__(self):
        """Return a developer-friendly string representation."""
        status = "✓" if self.completed else "○"
        badge = PRIORITY_EMOJI.get(self.priority, "")
        return f"[{status}] {badge} {self.time} — {self.description} ({self.frequency}, due {self.due_date})"


class Pet:
    """Stores pet details and maintains a list of care tasks."""

    def __init__(self, name: str, species: str, age: int):
        """Initialize a Pet with a name, species, and age."""
        self.name = name
        self.species = species
        self.age = age
        self.tasks: list[Task] = []

    def add_task(self, task: Task):
        """Add a care task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, description: str):
        """Remove all tasks matching the given description."""
        self.tasks = [t for t in self.tasks if t.description != description]

    def get_pending_tasks(self) -> list[Task]:
        """Return all incomplete tasks for this pet."""
        return [t for t in self.tasks if not t.completed]

    def to_dict(self) -> dict:
        """Serialize this Pet to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pet":
        """Deserialize a Pet from a dictionary (inverse of to_dict)."""
        pet = cls(name=data["name"], species=data["species"], age=data["age"])
        pet.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        return pet

    def __repr__(self):
        """Return a developer-friendly string representation."""
        return f"Pet({self.name}, {self.species}, age={self.age})"


class Owner:
    """Manages multiple pets, provides unified task access, and handles JSON persistence."""

    def __init__(self, name: str, email: str):
        """Initialize an Owner with a name and email address."""
        self.name = name
        self.email = email
        self.owned_pets: list[Pet] = []

    def add_pet(self, pet: Pet):
        """Register a pet under this owner."""
        self.owned_pets.append(pet)

    def remove_pet(self, pet_name: str):
        """Remove a pet by name."""
        self.owned_pets = [p for p in self.owned_pets if p.name != pet_name]

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Return all (pet, task) pairs across every owned pet."""
        return [(pet, task) for pet in self.owned_pets for task in pet.tasks]

    # ── JSON persistence ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize the full owner (including all pets and tasks) to a dictionary."""
        return {
            "name": self.name,
            "email": self.email,
            "owned_pets": [p.to_dict() for p in self.owned_pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Owner":
        """Deserialize an Owner from a dictionary (inverse of to_dict)."""
        owner = cls(name=data["name"], email=data["email"])
        owner.owned_pets = [Pet.from_dict(p) for p in data.get("owned_pets", [])]
        return owner

    def save_to_json(self, path: str = "data.json"):
        """Persist the owner, pets, and tasks to a JSON file.

        Writes an atomic replacement so a crash mid-write never corrupts the file.
        """
        file = Path(path)
        tmp = file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2))
        tmp.replace(file)

    @classmethod
    def load_from_json(cls, path: str = "data.json") -> "Owner":
        """Load and reconstruct an Owner from a JSON file.

        Returns a blank Owner if the file does not exist, so first-run is safe.
        """
        file = Path(path)
        if not file.exists():
            return cls(name="My Household", email="owner@pawpal.com")
        data = json.loads(file.read_text())
        return cls.from_dict(data)

    def __repr__(self):
        """Return a developer-friendly string representation."""
        return f"Owner({self.name}, {len(self.owned_pets)} pet(s))"


class ConflictWarning:
    """Represents a detected scheduling conflict between two tasks."""

    def __init__(self, time: str, pet_a: Pet, task_a: Task, pet_b: Pet, task_b: Task):
        """Store the conflicting time slot and both (pet, task) pairs."""
        self.time = time
        self.pet_a = pet_a
        self.task_a = task_a
        self.pet_b = pet_b
        self.task_b = task_b

    def message(self) -> str:
        """Return a human-readable warning string (never raises, never crashes)."""
        return (
            f"⚠ Conflict at {self.time}: "
            f"'{self.task_a.description}' ({self.pet_a.name}) "
            f"clashes with '{self.task_b.description}' ({self.pet_b.name})"
        )

    def __repr__(self):
        """Return the conflict warning message."""
        return self.message()


class Scheduler:
    """The brain of PawPal+: sorts by priority+time, filters, detects conflicts, finds open slots."""

    def __init__(self, owner: Owner):
        """Initialize the Scheduler with a reference to an Owner."""
        self.owner = owner

    # ── Sorting ───────────────────────────────────────────────────────────────

    def get_todays_schedule(self) -> list[tuple[Pet, Task]]:
        """Return all tasks sorted first by priority (high→low), then chronologically by time.

        Challenge 3 — Priority-Based Scheduling:
        The sort key is a tuple (priority_rank, time_string). Python compares tuples
        element-by-element, so high-priority tasks always float above lower-priority ones
        that share the same time slot, without any explicit if-else logic.
        """
        all_tasks = self.owner.get_all_tasks()
        return sorted(
            all_tasks,
            key=lambda pair: (_PRIORITY_ORDER.get(pair[1].priority, 1), pair[1].time)
        )

    # ── Filtering ─────────────────────────────────────────────────────────────

    def get_pending_tasks(self) -> list[tuple[Pet, Task]]:
        """Return only incomplete tasks, sorted by priority then time."""
        return [(pet, task) for pet, task in self.get_todays_schedule()
                if not task.completed]

    def filter_by_pet(self, pet_name: str) -> list[tuple[Pet, Task]]:
        """Return tasks for a specific pet, matched case-insensitively, sorted by priority+time."""
        return [
            (pet, task) for pet, task in self.get_todays_schedule()
            if pet.name.lower() == pet_name.lower()
        ]

    def filter_by_status(self, completed: bool) -> list[tuple[Pet, Task]]:
        """Return tasks filtered by completion status, sorted by priority then time."""
        return [
            (pet, task) for pet, task in self.get_todays_schedule()
            if task.completed == completed
        ]

    def filter_by_frequency(self, frequency: str) -> list[tuple[Pet, Task]]:
        """Return tasks matching a specific frequency, sorted by priority then time."""
        return [
            (pet, task) for pet, task in self.get_todays_schedule()
            if task.frequency.lower() == frequency.lower()
        ]

    def filter_by_priority(self, priority: str) -> list[tuple[Pet, Task]]:
        """Return only tasks at the given priority level ('high', 'medium', or 'low')."""
        return [
            (pet, task) for pet, task in self.get_todays_schedule()
            if task.priority.lower() == priority.lower()
        ]

    # ── Recurring tasks ───────────────────────────────────────────────────────

    def mark_task_complete(self, pet_name: str, task_description: str) -> bool:
        """Mark a task complete and auto-schedule the next occurrence for recurring tasks.

        Returns True if the task was found, False otherwise.
        """
        for pet in self.owner.owned_pets:
            if pet.name.lower() != pet_name.lower():
                continue
            for task in pet.tasks:
                if task.description.lower() != task_description.lower():
                    continue
                task.mark_complete()
                next_task = task.next_occurrence()
                if next_task:
                    pet.add_task(next_task)
                return True
        return False

    # ── Conflict detection ────────────────────────────────────────────────────

    def detect_conflicts(self) -> list[ConflictWarning]:
        """Return ConflictWarning objects for every pair of tasks sharing the same time slot.

        Strategy: O(n) grouping by time slot via defaultdict; flags any slot with >1 task.
        Returns warnings, never raises — the app never crashes on scheduling issues.
        Tradeoff: only exact HH:MM matches detected; overlapping durations are not.
        """
        by_time: dict[str, list[tuple[Pet, Task]]] = defaultdict(list)
        for pet, task in self.get_todays_schedule():
            by_time[task.time].append((pet, task))

        warnings: list[ConflictWarning] = []
        for time_slot, entries in by_time.items():
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    pet_a, task_a = entries[i]
                    pet_b, task_b = entries[j]
                    warnings.append(ConflictWarning(time_slot, pet_a, task_a, pet_b, task_b))
        return warnings

    # ── Challenge 1: Next available slot ──────────────────────────────────────

    def next_available_slot(self, after: str = "00:00",
                            step_minutes: int = 30) -> str:
        """Find the next free HH:MM time slot with no tasks already scheduled.

        Challenge 1 — Advanced Algorithmic Capability:
        Algorithm: generate candidate slots from `after` in `step_minutes` increments
        across a 24-hour window. Return the first candidate not present in the set of
        already-occupied slots. This is O(slots_per_day) in the worst case — at most
        48 iterations for 30-minute steps — and always terminates.

        Args:
            after: Start searching from this time (HH:MM, exclusive). Defaults to "00:00".
            step_minutes: Granularity of slot candidates in minutes. Defaults to 30.

        Returns:
            The first unoccupied HH:MM slot string, or "No slot available" if the full
            24-hour window is occupied (extremely unlikely in practice).
        """
        occupied = {task.time for _, task in self.owner.get_all_tasks()}

        # Parse start time into total minutes
        start_h, start_m = map(int, after.split(":"))
        start_total = start_h * 60 + start_m + step_minutes  # exclusive — start after `after`

        # Clamp to within 24 hours (1440 minutes)
        total_minutes_in_day = 24 * 60
        steps = total_minutes_in_day // step_minutes

        for i in range(steps):
            candidate_total = (start_total + i * step_minutes) % total_minutes_in_day
            h, m = divmod(candidate_total, 60)
            candidate = f"{h:02d}:{m:02d}"
            if candidate not in occupied:
                return candidate

        return "No slot available"

    def suggest_slots(self, count: int = 3, step_minutes: int = 30) -> list[str]:
        """Return up to `count` free time slots spread across the day.

        Useful for suggesting when to schedule a new task without creating conflicts.
        Scans from 06:00 (typical pet care start) in `step_minutes` increments.
        """
        occupied = {task.time for _, task in self.owner.get_all_tasks()}
        suggestions: list[str] = []
        start_total = 6 * 60  # 06:00
        steps = (24 * 60) // step_minutes

        for i in range(steps):
            if len(suggestions) >= count:
                break
            candidate_total = (start_total + i * step_minutes) % (24 * 60)
            h, m = divmod(candidate_total, 60)
            candidate = f"{h:02d}:{m:02d}"
            if candidate not in occupied:
                suggestions.append(candidate)

        return suggestions

    # ── CLI printing ──────────────────────────────────────────────────────────

    def print_schedule(self, pairs: list[tuple[Pet, Task]] | None = None):
        """Print a formatted, priority-color-coded schedule table to the terminal."""
        pairs = pairs if pairs is not None else self.get_todays_schedule()
        width = 60
        print(f"\n{'=' * width}")
        print(f"  PawPal+ Schedule — {self.owner.name}")
        print(f"{'=' * width}")
        if not pairs:
            print("  No tasks to display.")
        for pet, task in pairs:
            status = "✓" if task.completed else "○"
            badge = PRIORITY_EMOJI.get(task.priority, "")
            print(
                f"  {task.time}  {badge} [{pet.name:10s}]"
                f"  {task.description:<25s}  {'Done' if task.completed else 'Pending'}"
            )
        print(f"{'=' * width}\n")
