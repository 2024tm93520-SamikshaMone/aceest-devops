"""
test_app.py
Unit tests for ACEest Fitness & Gym Flask API

Author  : Samiksha Mangeshrao Mone
BITS ID : 2024TM93520
Course  : Introduction to DevOps (CSIZG514/SEZG514), S2-25

Run:
    pytest tests/ -v
    pytest tests/ -v --cov=app --cov-report=term-missing
"""

import json
import os
import sys
import tempfile

import pytest

# make sure app.py is importable when running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app, init_db, PROGRAMS


# ── fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path):
    """
    Fresh Flask test client backed by a real temp SQLite file.

    Why a file and not :memory:?
    SQLite :memory: creates a separate DB per connection.
    Flask's test client opens a new connection for every request,
    so :memory: would lose the schema immediately after init_db().
    A real temp file keeps the same DB across all requests in a test.
    """
    db_file = str(tmp_path / "test_aceest.db")
    os.environ["DB_PATH"] = db_file

    flask_app.config["TESTING"] = True
    init_db()

    with flask_app.test_client() as c:
        yield c


def post(client, url, payload):
    """Helper - POST JSON to a URL."""
    return client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json"
    )


# ── 1. home & health ───────────────────────────────────────────────────────────

class TestHomeAndHealth:

    def test_home_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_home_has_message(self, client):
        data = json.loads(client.get("/").data)
        assert "message" in data

    def test_home_has_status(self, client):
        data = json.loads(client.get("/").data)
        assert "status" in data

    def test_home_status_is_running(self, client):
        data = json.loads(client.get("/").data)
        assert data["status"] == "running"

    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_status_ok(self, client):
        data = json.loads(client.get("/health").data)
        assert data["status"] == "ok"


# ── 2. programs ────────────────────────────────────────────────────────────────

class TestPrograms:

    def test_get_programs_200(self, client):
        assert client.get("/api/programs").status_code == 200

    def test_returns_exactly_three_programs(self, client):
        data = json.loads(client.get("/api/programs").data)
        assert len(data) == 3

    def test_fat_loss_present(self, client):
        data = json.loads(client.get("/api/programs").data)
        assert "Fat Loss (FL)" in data

    def test_muscle_gain_present(self, client):
        data = json.loads(client.get("/api/programs").data)
        assert "Muscle Gain (MG)" in data

    def test_beginner_present(self, client):
        data = json.loads(client.get("/api/programs").data)
        assert "Beginner (BG)" in data

    def test_each_program_has_workout(self, client):
        data = json.loads(client.get("/api/programs").data)
        for name, prog in data.items():
            assert "workout" in prog, f"{name} missing workout"

    def test_each_program_has_diet(self, client):
        data = json.loads(client.get("/api/programs").data)
        for name, prog in data.items():
            assert "diet" in prog, f"{name} missing diet"

    def test_each_program_has_calorie_factor(self, client):
        data = json.loads(client.get("/api/programs").data)
        for name, prog in data.items():
            assert "calorie_factor" in prog, f"{name} missing calorie_factor"

    def test_calorie_factors_are_positive(self, client):
        data = json.loads(client.get("/api/programs").data)
        for name, prog in data.items():
            assert prog["calorie_factor"] > 0


# ── 3. calorie calculation ─────────────────────────────────────────────────────

class TestCalories:

    def test_fat_loss_70kg(self, client):
        """Fat Loss factor is 22. 70 x 22 = 1540."""
        r = post(client, "/api/calories",
                 {"weight": 70, "program": "Fat Loss (FL)"})
        assert r.status_code == 200
        assert json.loads(r.data)["estimated_calories"] == 1540

    def test_muscle_gain_80kg(self, client):
        """Muscle Gain factor is 35. 80 x 35 = 2800."""
        r = post(client, "/api/calories",
                 {"weight": 80, "program": "Muscle Gain (MG)"})
        assert r.status_code == 200
        assert json.loads(r.data)["estimated_calories"] == 2800

    def test_beginner_60kg(self, client):
        """Beginner factor is 26. 60 x 26 = 1560."""
        r = post(client, "/api/calories",
                 {"weight": 60, "program": "Beginner (BG)"})
        assert r.status_code == 200
        assert json.loads(r.data)["estimated_calories"] == 1560

    def test_decimal_weight(self, client):
        """Should handle float weights correctly."""
        r = post(client, "/api/calories",
                 {"weight": 72.5, "program": "Fat Loss (FL)"})
        assert r.status_code == 200
        assert json.loads(r.data)["estimated_calories"] == int(72.5 * 22)

    def test_response_echoes_weight(self, client):
        r = post(client, "/api/calories",
                 {"weight": 75, "program": "Fat Loss (FL)"})
        assert json.loads(r.data)["weight"] == 75

    def test_response_echoes_program(self, client):
        r = post(client, "/api/calories",
                 {"weight": 75, "program": "Fat Loss (FL)"})
        assert json.loads(r.data)["program"] == "Fat Loss (FL)"

    def test_missing_weight_returns_400(self, client):
        r = post(client, "/api/calories", {"program": "Fat Loss (FL)"})
        assert r.status_code == 400

    def test_missing_program_returns_400(self, client):
        r = post(client, "/api/calories", {"weight": 70})
        assert r.status_code == 400

    def test_empty_body_returns_400(self, client):
        r = client.post("/api/calories", content_type="application/json")
        assert r.status_code == 400

    def test_negative_weight_returns_400(self, client):
        r = post(client, "/api/calories",
                 {"weight": -10, "program": "Fat Loss (FL)"})
        assert r.status_code == 400

    def test_zero_weight_returns_400(self, client):
        r = post(client, "/api/calories",
                 {"weight": 0, "program": "Fat Loss (FL)"})
        assert r.status_code == 400

    def test_unknown_program_returns_404(self, client):
        r = post(client, "/api/calories",
                 {"weight": 70, "program": "Zumba"})
        assert r.status_code == 404


# ── 4. clients ─────────────────────────────────────────────────────────────────

class TestClients:

    def test_empty_list_on_fresh_db(self, client):
        r = client.get("/api/clients")
        assert r.status_code == 200
        assert json.loads(r.data) == []

    def test_add_client_returns_201(self, client):
        r = post(client, "/api/clients",
                 {"name": "Ravi Kumar", "age": 25,
                  "weight": 75, "program": "Muscle Gain (MG)"})
        assert r.status_code == 201

    def test_add_client_response_has_name(self, client):
        r = post(client, "/api/clients",
                 {"name": "Ravi Kumar", "age": 25,
                  "weight": 75, "program": "Muscle Gain (MG)"})
        assert json.loads(r.data)["name"] == "Ravi Kumar"

    def test_calories_auto_calculated(self, client):
        """60 x 22 (Fat Loss) = 1320"""
        r = post(client, "/api/clients",
                 {"name": "Priya", "weight": 60, "program": "Fat Loss (FL)"})
        assert json.loads(r.data)["calories"] == 1320

    def test_client_appears_in_list_after_add(self, client):
        post(client, "/api/clients",
             {"name": "Ananya", "age": 27,
              "weight": 55, "program": "Beginner (BG)"})
        names = [c["name"] for c in json.loads(client.get("/api/clients").data)]
        assert "Ananya" in names

    def test_multiple_clients_stored(self, client):
        post(client, "/api/clients",
             {"name": "Alice", "weight": 55, "program": "Fat Loss (FL)"})
        post(client, "/api/clients",
             {"name": "Bob", "weight": 80, "program": "Muscle Gain (MG)"})
        assert len(json.loads(client.get("/api/clients").data)) == 2

    def test_missing_name_returns_400(self, client):
        r = post(client, "/api/clients", {"age": 22, "weight": 68})
        assert r.status_code == 400

    def test_blank_name_returns_400(self, client):
        r = post(client, "/api/clients", {"name": "   ", "weight": 68})
        assert r.status_code == 400

    def test_unknown_program_returns_404(self, client):
        r = post(client, "/api/clients",
                 {"name": "Test", "weight": 70, "program": "Zumba"})
        assert r.status_code == 404

    def test_no_body_returns_400(self, client):
        r = client.post("/api/clients", content_type="application/json")
        assert r.status_code == 400

    def test_get_client_by_name_200(self, client):
        post(client, "/api/clients",
             {"name": "Kiran", "age": 30,
              "weight": 80, "program": "Muscle Gain (MG)"})
        r = client.get("/api/clients/Kiran")
        assert r.status_code == 200

    def test_get_client_data_correct(self, client):
        post(client, "/api/clients",
             {"name": "Deepa", "age": 28,
              "weight": 58, "program": "Fat Loss (FL)"})
        data = json.loads(client.get("/api/clients/Deepa").data)
        assert data["name"] == "Deepa"
        assert data["age"] == 28
        assert data["weight"] == 58

    def test_get_unknown_client_404(self, client):
        r = client.get("/api/clients/NoSuchPerson999")
        assert r.status_code == 404

    def test_update_existing_client(self, client):
        """INSERT OR REPLACE should update when same name sent twice."""
        post(client, "/api/clients",
             {"name": "Suresh", "weight": 80, "program": "Fat Loss (FL)"})
        post(client, "/api/clients",
             {"name": "Suresh", "weight": 75, "program": "Fat Loss (FL)"})
        data = json.loads(client.get("/api/clients/Suresh").data)
        assert data["weight"] == 75


# ── 5. progress tracking ───────────────────────────────────────────────────────

class TestProgress:

    def test_save_progress_returns_201(self, client):
        r = post(client, "/api/progress",
                 {"client_name": "Ravi", "week": "Week 01 - 2025",
                  "adherence": 80})
        assert r.status_code == 201

    def test_save_progress_response_has_message(self, client):
        r = post(client, "/api/progress",
                 {"client_name": "Ravi", "week": "Week 01 - 2025",
                  "adherence": 80})
        assert "message" in json.loads(r.data)

    def test_get_progress_for_client(self, client):
        post(client, "/api/progress",
             {"client_name": "Meera", "week": "Week 01", "adherence": 80})
        post(client, "/api/progress",
             {"client_name": "Meera", "week": "Week 02", "adherence": 85})
        data = json.loads(client.get("/api/progress/Meera").data)
        assert len(data) == 2

    def test_adherence_value_stored_correctly(self, client):
        post(client, "/api/progress",
             {"client_name": "Kiran", "week": "Week 03", "adherence": 75})
        data = json.loads(client.get("/api/progress/Kiran").data)
        assert data[0]["adherence"] == 75

    def test_week_value_stored_correctly(self, client):
        post(client, "/api/progress",
             {"client_name": "Kiran", "week": "Week 03", "adherence": 75})
        data = json.loads(client.get("/api/progress/Kiran").data)
        assert data[0]["week"] == "Week 03"

    def test_missing_fields_returns_400(self, client):
        r = post(client, "/api/progress", {"client_name": "Ravi"})
        assert r.status_code == 400

    def test_adherence_over_100_returns_400(self, client):
        r = post(client, "/api/progress",
                 {"client_name": "X", "week": "W1", "adherence": 150})
        assert r.status_code == 400

    def test_negative_adherence_returns_400(self, client):
        r = post(client, "/api/progress",
                 {"client_name": "X", "week": "W1", "adherence": -5})
        assert r.status_code == 400

    def test_zero_adherence_is_valid(self, client):
        r = post(client, "/api/progress",
                 {"client_name": "X", "week": "W1", "adherence": 0})
        assert r.status_code == 201

    def test_100_adherence_is_valid(self, client):
        r = post(client, "/api/progress",
                 {"client_name": "X", "week": "W1", "adherence": 100})
        assert r.status_code == 201

    def test_unknown_client_returns_empty_list(self, client):
        r = client.get("/api/progress/NoOneLikeThis999")
        assert r.status_code == 200
        assert json.loads(r.data) == []


# ── 6. pure unit tests (no HTTP) ──────────────────────────────────────────────

class TestProgramData:
    """Test the PROGRAMS dict directly - no DB, no HTTP needed."""

    def test_fat_loss_calorie_factor_is_22(self):
        assert PROGRAMS["Fat Loss (FL)"]["calorie_factor"] == 22

    def test_muscle_gain_calorie_factor_is_35(self):
        assert PROGRAMS["Muscle Gain (MG)"]["calorie_factor"] == 35

    def test_beginner_calorie_factor_is_26(self):
        assert PROGRAMS["Beginner (BG)"]["calorie_factor"] == 26

    def test_all_programs_have_workout_text(self):
        for name, data in PROGRAMS.items():
            assert len(data["workout"]) > 0, f"{name} has empty workout"

    def test_all_programs_have_diet_text(self):
        for name, data in PROGRAMS.items():
            assert len(data["diet"]) > 0, f"{name} has empty diet"

    def test_calorie_formula_fat_loss(self):
        """70 x 22 = 1540"""
        result = int(70 * PROGRAMS["Fat Loss (FL)"]["calorie_factor"])
        assert result == 1540

    def test_calorie_formula_muscle_gain(self):
        """80 x 35 = 2800"""
        result = int(80 * PROGRAMS["Muscle Gain (MG)"]["calorie_factor"])
        assert result == 2800

    def test_calorie_formula_beginner(self):
        """60 x 26 = 1560"""
        result = int(60 * PROGRAMS["Beginner (BG)"]["calorie_factor"])
        assert result == 1560
