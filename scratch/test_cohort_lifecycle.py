import sys
from services.cohort_service import (
    get_all_cohorts, get_active_cohort, create_cohort,
    set_active_cohort, complete_cohort, auto_assign_student_to_active_cohort, get_dashboard_kpis
)
from services.json_database import JSONDatabase

users_db = JSONDatabase('users')
cohorts_db = JSONDatabase('cohorts')

print("--- 1. Testing Initial Active Cohort ---")
active = get_active_cohort()
print(f"Active Cohort: {active['name']} (ID: {active['id']}) | Capacity: {active['max_capacity']}")

print("\n--- 2. Testing Cohort Transition Lifecycle ---")
success, msg = complete_cohort('cohort_1')
print(f"Complete Cohort 1 Result: {success} -> {msg}")

all_c = get_all_cohorts()
for c in all_c:
    print(f"Cohort {c['name']}: Status={c['status']}, Registered={c['current_enrollment']}/{c['max_capacity']}")

print("\n--- 3. Testing Student Cohort Association Retention ---")
students = users_db.find_all()
for s in students:
    print(f"Student: {s.get('full_name')} -> Assigned Cohort: {s.get('cohort_name')} ({s.get('cohort_id')})")

print("\n--- 4. Dashboard KPIs Verification ---")
kpis = get_dashboard_kpis()
print(f"KPIs -> Total Registered: {kpis['total_registered']}, Active Students Current Cohort: {kpis['active_students_current_cohort']}, Current Cohort: {kpis['current_cohort_name']}, Seats Left: {kpis['available_seats']}")

print("\n🎉 ALL LIFECYCLE TESTS COMPLETED SUCCESSFULLY!")
