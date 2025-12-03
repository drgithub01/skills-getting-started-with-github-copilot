"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    initial_state = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }
    activities.clear()
    activities.update(initial_state)
    yield
    activities.clear()
    activities.update(initial_state)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_get_activities_has_correct_structure(self, client, reset_activities):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)

    def test_get_activities_returns_participants(self, client, reset_activities):
        """Test that activities include participant data"""
        response = client.get("/activities")
        data = response.json()
        
        assert data["Chess Club"]["participants"] == ["michael@mergington.edu", "daniel@mergington.edu"]
        assert data["Programming Class"]["participants"] == ["emma@mergington.edu", "sophia@mergington.edu"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self, client, reset_activities):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]

    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_already_signed_up(self, client, reset_activities):
        """Test signing up when already registered"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_activity_full(self, client, reset_activities):
        """Test signing up when activity is at max capacity"""
        # Create a full activity
        activities["Full Activity"] = {
            "description": "A full activity",
            "schedule": "Monday, 5:00 PM",
            "max_participants": 1,
            "participants": ["existing@mergington.edu"]
        }
        
        response = client.post(
            "/activities/Full Activity/signup",
            params={"email": "new@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "full" in data["detail"]

    def test_signup_multiple_participants(self, client, reset_activities):
        """Test that multiple participants can sign up"""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                "/activities/Gym Class/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all were added
        gym_participants = activities["Gym Class"]["participants"]
        for email in emails:
            assert email in gym_participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]

    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregistering from a non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_non_participant(self, client, reset_activities):
        """Test unregistering someone not registered"""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_removes_only_specified_participant(self, client, reset_activities):
        """Test that unregister only removes the specified participant"""
        chess_participants_before = activities["Chess Club"]["participants"].copy()
        
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify only one participant was removed
        chess_participants_after = activities["Chess Club"]["participants"]
        assert len(chess_participants_after) == len(chess_participants_before) - 1
        assert "daniel@mergington.edu" in chess_participants_after

    def test_unregister_then_signup_again(self, client, reset_activities):
        """Test that a participant can unregister and sign up again"""
        email = "michael@mergington.edu"
        
        # Unregister
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email not in activities["Chess Club"]["participants"]
        
        # Sign up again
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities["Chess Club"]["participants"]


class TestActivityAvailability:
    """Tests for activity availability calculations"""

    def test_availability_calculation(self, client, reset_activities):
        """Test that availability is calculated correctly"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        expected_spots = chess_club["max_participants"] - len(chess_club["participants"])
        assert expected_spots == 10  # 12 - 2

    def test_availability_after_signup(self, client, reset_activities):
        """Test availability updates after signup"""
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "new@mergington.edu"}
        )
        
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        expected_spots = chess_club["max_participants"] - len(chess_club["participants"])
        assert expected_spots == 9  # 12 - 3

    def test_availability_after_unregister(self, client, reset_activities):
        """Test availability updates after unregister"""
        client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        expected_spots = chess_club["max_participants"] - len(chess_club["participants"])
        assert expected_spots == 11  # 12 - 1
