"""
Run this once before presenting to pre-load the app with demo pets and tasks.

    python3 demo_setup.py

Then start the app:

    streamlit run app.py
"""

from datetime import date
from pawpal_system import Owner, Pet, Task, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW

owner = Owner(name="Demo Household", email="demo@pawpal.com")

# ── Pet 1: Luna the dog ───────────────────────────────────────────────────────
luna = Pet(name="Luna", species="Dog", age=3)
luna.add_task(Task("Morning walk",    "07:00", "daily",   date.today(), PRIORITY_HIGH))
luna.add_task(Task("Breakfast",       "07:30", "daily",   date.today(), PRIORITY_HIGH))
luna.add_task(Task("Evening walk",    "18:00", "daily",   date.today(), PRIORITY_MEDIUM))
luna.add_task(Task("Dinner",          "18:30", "daily",   date.today(), PRIORITY_MEDIUM))
luna.add_task(Task("Heartworm pill",  "08:00", "monthly", date.today(), PRIORITY_HIGH))
owner.add_pet(luna)

# ── Pet 2: Mochi the cat ──────────────────────────────────────────────────────
mochi = Pet(name="Mochi", species="Cat", age=5)
mochi.add_task(Task("Breakfast",      "07:30", "daily",   date.today(), PRIORITY_HIGH))
mochi.add_task(Task("Playtime",       "19:00", "daily",   date.today(), PRIORITY_LOW))
mochi.add_task(Task("Dinner",         "18:00", "daily",   date.today(), PRIORITY_MEDIUM))
mochi.add_task(Task("Flea treatment", "09:00", "monthly", date.today(), PRIORITY_HIGH))
owner.add_pet(mochi)

owner.save_to_json("data.json")

print("Demo data loaded.")
print(f"  Pets: {[p.name for p in owner.owned_pets]}")
print(f"  Luna tasks: {len(luna.tasks)}")
print(f"  Mochi tasks: {len(mochi.tasks)}")
print("\nNow run:  streamlit run app.py")
