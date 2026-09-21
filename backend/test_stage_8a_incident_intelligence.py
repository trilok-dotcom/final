import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root workspace directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.database import init_db


def run_stage_8a_incident_intelligence_test():
    print("==================================================")
    print("  RESQROUTE — STAGE 8A: INCIDENT INTELLIGENCE TEST")
    print("==================================================")

    init_db()

    with TestClient(app) as client:
        # Reset units for clean baseline
        units = client.get("/api/rescue-units").json()
        for u in units:
            client.patch(f"/api/rescue-units/{u['id']}/status", json={"status": "AVAILABLE"})

        # 1. Test Collapsed Building Critical Incident Analysis
        print("[1/15] Testing Collapsed Building CRITICAL incident analysis...")
        inc1_res = client.post("/api/incidents", json={
            "incident_type": "COLLAPSED_BUILDING",
            "severity": "CRITICAL",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "location_name": "Metro Tower Structural Failure",
            "description": "Building structural collapse with trapped victims.",
        })
        assert inc1_res.status_code == 201
        inc1_id = inc1_res.json()["id"]

        an1_res = client.post(f"/api/incidents/{inc1_id}/analyze")
        assert an1_res.status_code == 200
        an1 = an1_res.json()

        assert an1["priority"] == "CRITICAL"
        assert an1["priority_score"] >= 80.0
        assert an1["urgency"] == "IMMEDIATE"
        assert len(an1["recommended_resources"]) >= 2
        print(f"       Priority: {an1['priority']} | Score: {an1['priority_score']} | Urgency: {an1['urgency']}")

        # 2. Test Fire High-Severity Incident Analysis
        print("[2/15] Testing Fire HIGH severity incident analysis...")
        inc2_res = client.post("/api/incidents", json={
            "incident_type": "FIRE",
            "severity": "HIGH",
            "latitude": 12.9780,
            "longitude": 77.5850,
            "location_name": "Sector 3 Warehouse Fire",
            "description": "Industrial warehouse fire spreading.",
        })
        assert inc2_res.status_code == 201
        inc2_id = inc2_res.json()["id"]

        an2_res = client.post(f"/api/incidents/{inc2_id}/analyze")
        assert an2_res.status_code == 200
        an2 = an2_res.json()
        assert 70.0 <= an2["priority_score"] <= 100.0
        assert an2["priority"] in ("HIGH", "CRITICAL")
        print(f"       Priority: {an2['priority']} | Score: {an2['priority_score']}")

        # 3. Test Medical Critical Incident Analysis
        print("[3/15] Testing Medical CRITICAL incident analysis...")
        inc3_res = client.post("/api/incidents", json={
            "incident_type": "MEDICAL",
            "severity": "CRITICAL",
            "latitude": 12.9666,
            "longitude": 77.5999,
            "location_name": "Bus Stand Medical Collapse",
            "description": "Multiple casualties after sudden collapse.",
        })
        inc3_id = inc3_res.json()["id"]
        an3 = client.get(f"/api/incidents/{inc3_id}/intelligence").json()
        assert an3["priority"] in ("CRITICAL", "HIGH")
        assert any(r["unit_type"] == "AMBULANCE" for r in an3["recommended_resources"])

        # 4. Test Low Severity Incident Analysis
        print("[4/15] Testing Low Severity incident analysis...")
        inc4_res = client.post("/api/incidents", json={
            "incident_type": "OTHER",
            "severity": "LOW",
            "latitude": 12.97,
            "longitude": 77.58,
            "location_name": "Minor Traffic Obstruction",
        })
        inc4_id = inc4_res.json()["id"]
        an4 = client.post(f"/api/incidents/{inc4_id}/analyze").json()
        assert an4["priority_score"] < 70.0
        assert an4["urgency"] in ("PRIORITY", "ROUTINE")
        print(f"       Priority: {an4['priority']} | Score: {an4['priority_score']}")

        # 5. Verify Resource Recommendation Structure
        print("[5/15] Verifying Resource Recommendation structure...")
        recs = an1["recommended_resources"]
        for r in recs:
            assert "unit_type" in r
            assert "quantity" in r
            assert "reason" in r
            assert r["quantity"] >= 1

        # 6. Verify Priority Score Range 0–100
        print("[6/15] Verifying score boundaries (0 <= score <= 100)...")
        assert 0.0 <= an1["priority_score"] <= 100.0
        assert 0.0 <= an4["priority_score"] <= 100.0

        # 7. Verify Priority Classification Labels
        print("[7/15] Verifying Priority Level classification labels...")
        valid_priorities = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert an1["priority"] in valid_priorities
        assert an4["priority"] in valid_priorities

        # 8. Verify Risk Classification Labels
        print("[8/15] Verifying Risk Level classification labels...")
        valid_risks = ("CRITICAL", "HIGH", "MODERATE", "LOW")
        assert an1["risk_level"] in valid_risks

        # 9. Verify Urgency Classification Labels
        print("[9/15] Verifying Urgency classification labels...")
        valid_urgencies = ("IMMEDIATE", "URGENT", "PRIORITY", "ROUTINE")
        assert an1["urgency"] in valid_urgencies

        # 10. Verify AI Explanation Summary Generation
        print("[10/15] Verifying AI explanation text generation...")
        assert len(an1["explanation"]) > 20
        assert "priority classified as" in an1["explanation"].lower()

        # 11. Verify Factors Breakdown Structure
        print("[11/15] Verifying 5-Factor scoring breakdown structure...")
        factors = an1["factors"]
        assert len(factors) == 5
        for f in factors:
            assert "name" in f
            assert "raw_score" in f
            assert "weight" in f
            assert "weighted_score" in f
            assert "reason" in f

        # 12. Test Unknown / OTHER Incident Type Handling
        print("[12/15] Testing unknown / OTHER incident type fallback...")
        inc_other = client.post("/api/incidents", json={
            "incident_type": "OTHER",
            "severity": "MEDIUM",
            "latitude": 12.97,
            "longitude": 77.58,
        }).json()
        an_other = client.post(f"/api/incidents/{inc_other['id']}/analyze").json()
        assert "priority_score" in an_other

        # 13. Test Non-Existent Incident (HTTP 404)
        print("[13/15] Testing non-existent incident rejection (HTTP 404)...")
        res_404 = client.post("/api/incidents/non_existent_inc_999/analyze")
        assert res_404.status_code == 404

        # 14. Verify Existing Incident CRUD Still Works
        print("[14/15] Verifying existing incident CRUD operations...")
        res_get = client.get(f"/api/incidents/{inc1_id}")
        assert res_get.status_code == 200
        assert res_get.json()["incident_type"] == "COLLAPSED_BUILDING"

        # 15. Clean up Test Records
        print("[15/15] Cleaning up test incidents...")
        client.delete(f"/api/incidents/{inc1_id}")
        client.delete(f"/api/incidents/{inc2_id}")
        client.delete(f"/api/incidents/{inc3_id}")
        client.delete(f"/api/incidents/{inc4_id}")
        client.delete(f"/api/incidents/{inc_other['id']}")

        print("\n============================================================")
        print("STAGE 8A INCIDENT INTELLIGENCE TESTS COMPLETED SUCCESSFULLY")
        print("============================================================")


if __name__ == "__main__":
    run_stage_8a_incident_intelligence_test()
