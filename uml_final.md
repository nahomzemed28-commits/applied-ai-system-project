# PawPal+ — Final System Architecture (UML)

This diagram reflects the **final implementation** in `pawpal_system.py`.

```mermaid
classDiagram
    direction TD

    class Task {
        +str description
        +str time
        +str frequency
        +date due_date
        +bool completed
        +mark_complete()
        +reset()
        +next_occurrence() Task
    }

    class Pet {
        +str name
        +str species
        +int age
        +list~Task~ tasks
        +add_task(task: Task)
        +remove_task(description: str)
        +get_pending_tasks() list~Task~
    }

    class Owner {
        +str name
        +str email
        +list~Pet~ owned_pets
        +add_pet(pet: Pet)
        +remove_pet(pet_name: str)
        +get_all_tasks() list~tuple~
    }

    class Scheduler {
        +Owner owner
        +get_todays_schedule() list~tuple~
        +get_pending_tasks() list~tuple~
        +filter_by_pet(pet_name: str) list~tuple~
        +filter_by_status(completed: bool) list~tuple~
        +filter_by_frequency(frequency: str) list~tuple~
        +mark_task_complete(pet_name, description) bool
        +detect_conflicts() list~ConflictWarning~
        +print_schedule(pairs)
    }

    class ConflictWarning {
        +str time
        +Pet pet_a
        +Task task_a
        +Pet pet_b
        +Task task_b
        +message() str
    }

    %% Relationships
    Owner "1" --> "0..*" Pet : owns
    Pet "1" --> "0..*" Task : has
    Scheduler "1" --> "1" Owner : reads from
    Scheduler ..> ConflictWarning : creates
    Task ..> Task : next_occurrence() returns
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `Scheduler` reads from `Owner`, not `Pet` directly | Single entry point; Owner acts as the data boundary |
| `ConflictWarning` is a separate class | Decouples detection logic from display; `.message()` can be used by CLI or UI |
| `Task.next_occurrence()` on the Task itself | Keeps recurrence logic encapsulated in the data class, not the Scheduler |
| `time` stored as `"HH:MM"` string | Lexicographic order = chronological order for 24h format; no parsing needed |
| `due_date` stored as `date` object | Enables `timedelta` arithmetic for recurring task scheduling |
