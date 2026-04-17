"""
Comprehensive test suite for the Mergington High School Activity Management API
Using AAA (Arrange-Act-Assert) testing pattern

Tests cover:
- GET /activities endpoint
- POST /activities/{activity_name}/signup with valid and invalid cases
- DELETE /activities/{activity_name}/remove with valid and invalid cases
- Edge cases (duplicates, non-existent activities, capacity limits)
- Proper fixtures and test data isolation
"""

import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Provides a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_activities():
    """Provides a deep copy of the activities to avoid test pollution."""
    return deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities(sample_activities):
    """Reset activities to initial state before each test."""
    activities.clear()
    activities.update(deepcopy(sample_activities))
    yield
    # Cleanup after test
    activities.clear()
    activities.update(deepcopy(sample_activities))


class TestRootEndpoint:
    """Test the root endpoint redirect."""

    def test_root_redirect(self, client):
        # Arrange
        expected_redirect_path = "/static/index.html"

        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        assert response.url.path == expected_redirect_path


class TestGetActivities:
    """Test the GET /activities endpoint."""

    def test_get_all_activities(self, client):
        # Arrange
        expected_activity_count = 9

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == expected_activity_count

        # Check that each activity has required fields
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_activity_structure(self, client):
        # Arrange
        expected_chess_club = {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12
        }

        # Act
        response = client.get("/activities")

        # Assert
        data = response.json()
        chess_club = data["Chess Club"]
        assert chess_club["description"] == expected_chess_club["description"]
        assert chess_club["schedule"] == expected_chess_club["schedule"]
        assert chess_club["max_participants"] == expected_chess_club["max_participants"]
        assert isinstance(chess_club["participants"], list)


class TestSignupEndpoint:
    """Test the POST /activities/{activity_name}/signup endpoint."""

    def test_successful_signup(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "test@mergington.edu"
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity_name]["participants"])

        # Act
        response = client.post(f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}")

        # Assert
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert f"Signed up {email} for {activity_name}" in data["message"]

        # Verify participant was added
        updated_response = client.get("/activities")
        updated_data = updated_response.json()
        assert len(updated_data[activity_name]["participants"]) == initial_count + 1
        assert email in updated_data[activity_name]["participants"]

    def test_signup_nonexistent_activity(self, client):
        # Arrange
        nonexistent_activity = "NonExistent"
        email = "test@mergington.edu"

        # Act
        response = client.post(f"/activities/{nonexistent_activity}/signup?email={email}")

        # Assert
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]

    def test_duplicate_signup(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "duplicate@mergington.edu"

        # Act - First signup (should succeed)
        response1 = client.post(f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}")
        response2 = client.post(f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}")

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 400

        data = response2.json()
        assert "detail" in data
        assert "Student is already signed up for this activity" in data["detail"]

    def test_signup_with_spaces_in_activity_name(self, client):
        # Arrange
        activity_name = "Programming Class"
        email = "test@mergington.edu"

        # Act
        response = client.post(f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}")

        # Assert
        assert response.status_code == 200

        data = response.json()
        assert activity_name in data["message"]

    def test_signup_capacity_not_enforced(self, client):
        # Arrange
        activity_name = "Tennis Club"
        initial_response = client.get("/activities")
        initial_participants = len(initial_response.json()[activity_name]["participants"])
        max_capacity = initial_response.json()[activity_name]["max_participants"]

        # Act - Add participants beyond capacity
        for i in range(max_capacity):
            email = f"student{i}@mergington.edu"
            response = client.post(f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}")
            assert response.status_code == 200

        # Assert - Verify capacity was exceeded (current behavior)
        activities_response = client.get("/activities")
        final_participants = len(activities_response.json()[activity_name]["participants"])
        assert final_participants == initial_participants + max_capacity
        assert final_participants > max_capacity


class TestRemoveParticipantEndpoint:
    """Test the DELETE /activities/{activity_name}/remove endpoint."""

    def test_successful_removal(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "remove_me@mergington.edu"
        client.post(f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}")

        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity_name]["participants"])

        # Act
        response = client.delete(f"/activities/{activity_name.replace(' ', '%20')}/remove?email={email}")

        # Assert
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert f"Removed {email} from {activity_name}" in data["message"]

        # Verify participant was removed
        updated_response = client.get("/activities")
        updated_count = len(updated_response.json()[activity_name]["participants"])
        assert updated_count == initial_count - 1

    def test_remove_from_nonexistent_activity(self, client):
        # Arrange
        nonexistent_activity = "NonExistent"
        email = "test@mergington.edu"

        # Act
        response = client.delete(f"/activities/{nonexistent_activity}/remove?email={email}")

        # Assert
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]

    def test_remove_nonexistent_participant(self, client):
        # Arrange
        activity_name = "Chess Club"
        nonexistent_email = "not_signed_up@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity_name.replace(' ', '%20')}/remove?email={nonexistent_email}")

        # Assert
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "Participant not found in this activity" in data["detail"]

    def test_remove_initial_participant(self, client):
        # Arrange
        activity_name = "Chess Club"
        email_to_remove = "michael@mergington.edu"
        email_to_keep = "daniel@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity_name.replace(' ', '%20')}/remove?email={email_to_remove}")

        # Assert
        assert response.status_code == 200

        # Verify correct participant was removed
        activities_response = client.get("/activities")
        chess_participants = activities_response.json()[activity_name]["participants"]
        assert email_to_remove not in chess_participants
        assert email_to_keep in chess_participants


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple operations."""

    def test_signup_then_remove_then_signup_again(self, client):
        # Arrange
        activity_name = "Chess Club"
        email = "integration_test@mergington.edu"

        # Act - Signup, remove, signup again
        response1 = client.post(f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}")
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity_name]["participants"]

        response2 = client.delete(f"/activities/{activity_name.replace(' ', '%20')}/remove?email={email}")
        activities_response = client.get("/activities")
        assert email not in activities_response.json()[activity_name]["participants"]

        response3 = client.post(f"/activities/{activity_name.replace(' ', '%20')}/signup?email={email}")
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity_name]["participants"]

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

    def test_multiple_activities_same_student(self, client):
        # Arrange
        email = "multi_activity@mergington.edu"
        activity1 = "Chess Club"
        activity2 = "Programming Class"

        # Act - Signup for both activities
        response1 = client.post(f"/activities/{activity1.replace(' ', '%20')}/signup?email={email}")
        response2 = client.post(f"/activities/{activity2.replace(' ', '%20')}/signup?email={email}")

        # Assert - Verify in both activities
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email in data[activity1]["participants"]
        assert email in data[activity2]["participants"]

        # Act - Remove from one activity
        client.delete(f"/activities/{activity1.replace(' ', '%20')}/remove?email={email}")

        # Assert - Verify removed from one but not the other
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email not in data[activity1]["participants"]
        assert email in data[activity2]["participants"]