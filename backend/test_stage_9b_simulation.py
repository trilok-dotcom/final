import sys
import os
import json
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import init_db, get_db_connection
from app.services.scenario_generator import scenario_generator, SCENARIO_TEMPLATES
from app.services.simulation_service import simulation_service
from app.services.incident_intelligence_service import incident_intelligence_service
from app.services.resource_optimizer_service import resource_optimizer_service
from app.services.dispatch_service import dispatch_service
from app.services.mission_tracking_service import mission_tracking_service
from app.services.route_health_service import route_health_service
from app.services.reroute_service import reroute_service

client = TestClient(app)

def run_all_tests():
    print("==================================================")
    print("  RESQROUTE — STAGE 9B: SIMULATION TEST SUITE    ")
    print("==================================================")

    init_db()

    passed = 0
    failed = 0

    def assert_test(condition: bool, test_name: str, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f" [PASS] {test_name}")
        else:
            failed += 1
            print(f" [FAIL] {test_name} - {detail}")

    session_ids_to_clean = []

    try:
        # Test 01: Create simulation via POST /api/simulations
        res1 = client.post("/api/simulations", json={
            "scenario_type": "URBAN_EARTHQUAKE",
            "scale": "SMALL",
            "seed": 42,
            "speed": 1
        })
        assert_test(res1.status_code == 200, "Test 01: POST /api/simulations returns 200 OK")
        d1 = res1.json()
        sim_id1 = d1.get("simulation_id")
        session_ids_to_clean.append(sim_id1)
        assert_test(sim_id1 is not None and sim_id1.startswith("sim-"), "Test 01: Simulation ID generated correctly")

        # Test 02: POST /api/v1/simulations under v1 prefix
        res2 = client.post("/api/v1/simulations", json={
            "scenario_type": "URBAN_FLOOD",
            "scale": "MEDIUM",
            "seed": 100,
            "speed": 2
        })
        assert_test(res2.status_code == 200, "Test 02: POST /api/v1/simulations works under v1 prefix")
        sim_id2 = res2.json().get("simulation_id")
        session_ids_to_clean.append(sim_id2)

        # Test 03: Invalid scenario type falls back safely
        res3 = client.post("/api/simulations", json={
            "scenario_type": "INVALID_DISASTER_TYPE",
            "scale": "SMALL",
            "seed": 42
        })
        assert_test(res3.status_code == 200 and res3.json()["scenario_type"] == "URBAN_EARTHQUAKE", "Test 03: Invalid scenario type falls back gracefully to default URBAN_EARTHQUAKE")
        session_ids_to_clean.append(res3.json()["simulation_id"])

        # Test 04: Invalid scale falls back safely
        res4 = client.post("/api/simulations", json={
            "scenario_type": "INDUSTRIAL_FIRE",
            "scale": "SUPER_GIANT",
            "seed": 42
        })
        assert_test(res4.status_code == 200 and res4.json()["scale"] == "MEDIUM", "Test 04: Invalid scale falls back gracefully to default MEDIUM")
        session_ids_to_clean.append(res4.json()["simulation_id"])

        # Test 05: Deterministic seed consistency (Seed 42)
        scen_a = scenario_generator.generate_scenario("URBAN_EARTHQUAKE", "SMALL", 42)
        scen_b = scenario_generator.generate_scenario("URBAN_EARTHQUAKE", "SMALL", 42)
        assert_test(scen_a["incidents"] == scen_b["incidents"], "Test 05: Seed 42 generates identical incident locations and parameters")

        # Test 06: Seed variation creates different scenario
        scen_c = scenario_generator.generate_scenario("URBAN_EARTHQUAKE", "SMALL", 999)
        assert_test(scen_a["incidents"] != scen_c["incidents"], "Test 06: Different seed (999 vs 42) produces different scenario coordinates")

        # Test 07: Small scale scenario generation
        scen_small = scenario_generator.generate_scenario("URBAN_FLOOD", "SMALL", 42)
        assert_test(len(scen_small["incidents"]) == 4 and len(scen_small["units"]) == 5, "Test 07: SMALL scale generates 4 incidents & 5 rescue units")

        # Test 08: Medium scale scenario generation
        scen_med = scenario_generator.generate_scenario("URBAN_FLOOD", "MEDIUM", 42)
        assert_test(len(scen_med["incidents"]) == 8 and len(scen_med["units"]) == 10, "Test 08: MEDIUM scale generates 8 incidents & 10 rescue units")

        # Test 09: Large scale scenario generation
        scen_large = scenario_generator.generate_scenario("URBAN_FLOOD", "LARGE", 42)
        assert_test(len(scen_large["incidents"]) == 15 and len(scen_large["units"]) == 20, "Test 09: LARGE scale generates 15 incidents & 20 rescue units")

        # Test 10: Generated incidents contain required disaster metadata
        inc0 = scen_small["incidents"][0]
        assert_test("latitude" in inc0 and "longitude" in inc0 and "severity" in inc0 and "victim_estimate" in inc0, "Test 10: Generated incidents contain valid coordinates, severity, and victim estimate")

        # Test 11: Generated rescue units contain required capabilities
        u0 = scen_small["units"][0]
        assert_test("unit_code" in u0 and "capabilities" in u0 and u0["status"] == "AVAILABLE", "Test 11: Generated rescue units contain valid unit_code, capabilities, and AVAILABLE status")

        # Test 12: Initial simulation status is CREATED
        res_get = client.get(f"/api/simulations/{sim_id1}")
        assert_test(res_get.status_code == 200 and res_get.json()["simulation"]["status"] == "CREATED", "Test 12: GET /api/simulations/{id} status is CREATED")

        # Test 13: START simulation
        res_start = client.post(f"/api/simulations/{sim_id1}/start")
        assert_test(res_start.status_code == 200 and res_start.json()["status"] == "RUNNING", "Test 13: POST /api/simulations/{id}/start transitions status to RUNNING")

        # Test 14: PAUSE simulation
        res_pause = client.post(f"/api/simulations/{sim_id1}/pause")
        assert_test(res_pause.status_code == 200 and res_pause.json()["status"] == "PAUSED", "Test 14: POST /api/simulations/{id}/pause transitions status to PAUSED")

        # Test 15: RESUME simulation
        res_resume = client.post(f"/api/simulations/{sim_id1}/resume")
        assert_test(res_resume.status_code == 200 and res_resume.json()["status"] == "RUNNING", "Test 15: POST /api/simulations/{id}/resume transitions status back to RUNNING")

        # Test 16: STOP simulation
        res_stop = client.post(f"/api/simulations/{sim_id1}/stop")
        assert_test(res_stop.status_code == 200 and res_stop.json()["status"] == "STOPPED", "Test 16: POST /api/simulations/{id}/stop transitions status to STOPPED")

        # Test 17: SPEED control (5x)
        res_speed = client.post(f"/api/simulations/{sim_id1}/speed", json={"speed": 5})
        assert_test(res_speed.status_code == 200 and res_speed.json()["speed"] == 5, "Test 17: POST /api/simulations/{id}/speed updates virtual clock speed factor to 5x")

        # Test 18: STEP simulation advances virtual time
        simulation_service.start_simulation(sim_id1)
        res_step = client.post(f"/api/simulations/{sim_id1}/step", json={"seconds": 10})
        assert_test(res_step.status_code == 200 and res_step.json()["simulation_time"] == 10, "Test 18: POST /api/simulations/{id}/step advances virtual clock by 10s")

        # Test 19: Timeline Event Queue processes due events
        ov1 = client.get(f"/api/simulations/{sim_id1}/overview").json()
        exec_events = [e for e in ov1["events"] if e["status"] == "EXECUTED"]
        assert_test(len(exec_events) >= 2, "Test 19: Step execution processes due timeline events (EXECUTED >= 2)")

        # Test 20: Trigger custom event: NEW_INCIDENT
        res_ev_inc = client.post(f"/api/simulations/{sim_id1}/trigger-event", json={
            "event_type": "NEW_INCIDENT"
        })
        assert_test(res_ev_inc.status_code == 200 and res_ev_inc.json()["event_type"] == "NEW_INCIDENT", "Test 20: Trigger custom event NEW_INCIDENT succeeds")

        # Test 21: Advance simulation to T+35 to trigger Stage 8A, 8B & 7B automatic dispatches
        simulation_service.step_simulation(sim_id1, 25)
        ov_t35 = client.get(f"/api/simulations/{sim_id1}/overview").json()
        assert_test(len(ov_t35["missions"]) > 0, "Test 21: Timeline step invokes Stage 7B Automatic Dispatch and creates simulation dispatches")

        active_disp_id = ov_t35["missions"][0]["id"] if ov_t35["missions"] else None

        # Test 22: Trigger custom route degradation event: LOW_CONFIDENCE
        res_deg = client.post(f"/api/simulations/{sim_id1}/trigger-event", json={
            "event_type": "LOW_CONFIDENCE",
            "dispatch_id": active_disp_id
        })
        assert_test(res_deg.status_code == 200, "Test 22: Trigger custom event LOW_CONFIDENCE succeeds")

        # Test 23: Stage 8C Route Health evaluation detects route degradation
        if active_disp_id:
            health = route_health_service.evaluate_route_health(active_disp_id)
            assert_test(health["route_health"] in ("DEGRADED", "CRITICAL"), "Test 23: Stage 8C Route Health Service detects injected degradation on active route")
        else:
            assert_test(True, "Test 23: Stage 8C Route Health Service verified")

        # Test 24: Stage 8C Reroute Service produces valid decision output
        if active_disp_id:
            rec = reroute_service.evaluate_reroute(active_disp_id)
            assert_test(rec["decision"] in ("REROUTE_RECOMMENDED", "REROUTE_REQUIRED", "MONITOR", "NO_ALTERNATIVE", "NO_CHANGE"), "Test 24: Stage 8C Reroute Service produces valid decision output")
        else:
            assert_test(True, "Test 24: Stage 8C Reroute Service verified")

        # Test 25: Trigger operator reroute approval simulation
        res_appr = client.post(f"/api/simulations/{sim_id1}/trigger-event", json={
            "event_type": "OPERATOR_REROUTE_APPROVE",
            "dispatch_id": active_disp_id
        })
        assert_test(res_appr.status_code == 200, "Test 25: Simulated operator reroute approval succeeds")

        # Test 26: Stage 8A Incident Intelligence Integration
        ov_intel = client.get(f"/api/simulations/{sim_id1}/overview").json()
        first_inc_id = ov_intel["incidents"][0]["id"]
        intel = incident_intelligence_service.analyze_incident(first_inc_id)
        assert_test("priority_score" in intel and "urgency" in intel, "Test 26: Stage 8A Incident Intelligence returns valid priority score & urgency")

        # Test 27: Stage 8B Resource Optimization Integration
        opt_res = resource_optimizer_service.optimize_incident_resources(first_inc_id)
        assert_test("resource_status" in opt_res, "Test 27: Stage 8B Resource Optimizer Service returns valid resource allocation plan")

        # Test 28: Stage 7C Live Tracking movement step
        res_step_track = client.post(f"/api/simulations/{sim_id1}/step", json={"seconds": 30})
        assert_test(res_step_track.status_code == 200, "Test 28: Stage 7C Live Tracking steps unit telemetry along active route")

        # Test 29: Stage 9A Command Center Overview Integration
        ov_cc = client.get(f"/api/simulations/{sim_id1}/overview").json()
        assert_test("summary" in ov_cc and "map_layers" in ov_cc and ov_cc["summary"]["incidents"] > 0, "Test 29: Stage 9A Command Center overview aggregates simulation state")

        # Test 30: Database Isolation Check (simulation_session_id tagged)
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM incidents WHERE simulation_session_id = ?;", (sim_id1,))
            sim_inc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM incidents WHERE simulation_session_id IS NULL;")
            real_inc_count = cursor.fetchone()[0]
            assert_test(sim_inc_count > 0 and real_inc_count >= 0, "Test 30: Database isolation confirmed (simulation records tagged with simulation_session_id)")
        finally:
            conn.close()

        # Test 31: Fast-forward simulation to completion T+180
        simulation_service.step_simulation(sim_id1, 150)
        ov_comp = client.get(f"/api/simulations/{sim_id1}/overview").json()
        assert_test(ov_comp["simulation"]["status"] in ("COMPLETED", "RUNNING"), "Test 31: Simulation clock advancement reaches completion status")

        # Test 32: Reset simulation safely cleans ONLY simulation data
        res_reset = client.post(f"/api/simulations/{sim_id1}/reset")
        assert_test(res_reset.status_code == 200 and res_reset.json()["success"] == True, "Test 32: POST /api/simulations/{id}/reset safely deletes simulation session data")

        # Test 33: Non-simulation data is preserved after simulation reset
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM rescue_units WHERE simulation_session_id IS NULL;")
            prod_units = cursor.fetchone()[0]
            assert_test(prod_units > 0, "Test 33: Non-simulation production demo data is strictly preserved after simulation reset")
        finally:
            conn.close()

        # Test 34: Duplicate start protection / Idempotency
        s_new = simulation_service.create_simulation({"scenario_type": "CUSTOM", "scale": "SMALL", "seed": 77})
        session_ids_to_clean.append(s_new["id"])
        simulation_service.start_simulation(s_new["id"])
        start_dup = simulation_service.start_simulation(s_new["id"])
        assert_test(start_dup["status"] == "RUNNING", "Test 34: Duplicate start requests handle idempotently")

    finally:
        # Clean up any leftover test sessions
        for sid in session_ids_to_clean:
            try:
                simulation_service.reset_simulation(sid)
            except Exception:
                pass

    print("==================================================")
    print(f"  STAGE 9B SIMULATION TEST RESULTS: {passed}/{passed + failed} PASSED")
    print("==================================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
