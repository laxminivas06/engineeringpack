import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.mentor_service import (
    get_all_mentors, get_mentor_by_id, create_mentor, update_mentor, delete_mentor,
    get_mentors_for_program, assign_mentor_to_program, remove_mentor_from_program,
    sanitize_public_mentor, process_mentor_links
)

def run_tests():
    print("--- 1. Testing Central Mentor Creation ---")
    social_links = [
        {"platform": "LinkedIn", "url": "https://linkedin.com/in/testmentor"},
        {"platform": "Instagram", "url": "https://instagram.com/testmentor"},
        {"platform": "GitHub", "url": "https://github.com/testmentor"}
    ]
    mentor = create_mentor(
        full_name="Test Mentor Beta",
        professional_title="Senior AI Researcher",
        domain="AI & Robotics",
        experience="8+ Years",
        social_links=social_links
    )
    assert mentor["id"].startswith("mnt_"), "Mentor creation failed"
    print(f"✓ Mentor created cleanly in Central DB: {mentor['full_name']} ({mentor['id']})")

    print("\n--- 2. Testing Dynamic Links & Icons Processing ---")
    processed = process_mentor_links(mentor)
    platforms = [p['platform'] for p in processed]
    assert "Instagram" in platforms, "Instagram link missing"
    assert "LinkedIn" in platforms, "LinkedIn link missing"
    assert "GitHub" in platforms, "GitHub link missing"
    print("✓ Dynamic links (LinkedIn, Instagram, GitHub) processed with matching icons!")

    print("\n--- 3. Testing Editing Central Mentor Profile ---")
    success, updated = update_mentor(mentor["id"], {
        "full_name": "Test Mentor Beta Updated",
        "domain": "Deep Learning & NLP",
        "social_links": [
            {"platform": "YouTube", "url": "https://youtube.com/@testmentor"},
            {"platform": "LinkedIn", "url": "https://linkedin.com/in/testmentor"}
        ]
    })
    assert success, "Profile update failed"
    assert updated["full_name"] == "Test Mentor Beta Updated"
    print("✓ Central Mentor profile updated successfully!")

    print("\n--- 4. Cleanup Test Mentor ---")
    delete_mentor(mentor["id"])
    assert get_mentor_by_id(mentor["id"]) is None
    print("✓ Cleanup successful.")

    print("\nALL MENTOR MANAGEMENT TESTS PASSED PERFECTLY! 🚀")

if __name__ == "__main__":
    run_tests()
