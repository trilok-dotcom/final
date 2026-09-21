from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel

from app.db.database import get_db_connection
from app.services.route_health_service import route_health_service
from app.services.dynamic_routing_service import dynamic_routing_service
from app.services.reroute_service import reroute_service
from app.utils.logging import get_logger

logger = get_logger("app.api.routes.rerouting")

router = APIRouter()


class EvaluateRouteRequest(BaseModel):
    simulated_scenario: Optional[str] = None


class SimulateDegradationRequest(BaseModel):
    scenario: str


class ApproveRerouteRequest(BaseModel):
    recommended_route_id: Optional[str] = None
    approved_by: Optional[str] = "DISPATCH_OPERATOR"


@router.post("/dispatches/{dispatch_id}/evaluate-route")
def evaluate_route_health_endpoint(
    dispatch_id: str, payload: Optional[EvaluateRouteRequest] = None
):
    """Evaluate current route health for an active emergency mission."""
    try:
        scenario = payload.simulated_scenario if payload else None
        res = route_health_service.evaluate_route_health(dispatch_id, simulated_scenario=scenario)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error evaluating route health for dispatch '{dispatch_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/dispatches/{dispatch_id}/alternatives")
def generate_alternative_routes_endpoint(dispatch_id: str):
    """Generate candidate alternative AI routes for active mission."""
    try:
        res = dynamic_routing_service.generate_alternative_routes(dispatch_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating alternative routes for dispatch '{dispatch_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/dispatches/{dispatch_id}/reroute-evaluate")
def evaluate_reroute_endpoint(
    dispatch_id: str, payload: Optional[EvaluateRouteRequest] = None
):
    """Evaluate whether rerouting should be recommended for active mission."""
    try:
        scenario = payload.simulated_scenario if payload else None
        res = reroute_service.evaluate_reroute(dispatch_id, simulated_scenario=scenario)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error evaluating reroute decision for dispatch '{dispatch_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/dispatches/{dispatch_id}/reroute-approve")
def approve_reroute_endpoint(
    dispatch_id: str, payload: Optional[ApproveRerouteRequest] = None
):
    """Operator-approved route replacement."""
    try:
        rec_id = payload.recommended_route_id if payload else None
        operator = (payload.approved_by if payload and payload.approved_by else "DISPATCH_OPERATOR")
        res = reroute_service.approve_reroute(
            dispatch_id=dispatch_id, recommended_route_id=rec_id, approved_by=operator
        )
        if not res.get("success") and res.get("error") == "ROUTE_RECALCULATION_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("message", "The recommended route was generated too long ago. Recalculate alternatives before approval."),
            )
        return res
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving reroute for dispatch '{dispatch_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/dispatches/{dispatch_id}/simulate-route-degradation")
@router.post("/dispatches/{dispatch_id}/simulate-degradation")
def simulate_route_degradation_endpoint(
    dispatch_id: str, payload: SimulateDegradationRequest
):
    """Simulate route degradation scenarios for development and testing."""
    allowed_scenarios = [
        "LOW_CONFIDENCE",
        "HIGH_RISK",
        "ETA_INCREASE",
        "ROUTE_DISCONNECTED",
        "UNIT_DEVIATION",
        "MINOR_DEGRADATION",
        "NO_ALTERNATIVE",
        "BRIDGE_COLLAPSE",
    ]
    scen_upper = payload.scenario.upper()
    if scen_upper not in allowed_scenarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scenario '{payload.scenario}'. Allowed scenarios: {allowed_scenarios}",
        )
    try:
        # Persist degradation attributes into SQLite dispatch record
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if scen_upper in ["LOW_CONFIDENCE", "ROUTE_DISCONNECTED", "NO_ALTERNATIVE", "BRIDGE_COLLAPSE"]:
                cursor.execute("UPDATE dispatches SET risk_level = 'CRITICAL', average_confidence = 0.35 WHERE id = ?;", (dispatch_id,))
            elif scen_upper in ["HIGH_RISK", "UNIT_DEVIATION"]:
                cursor.execute("UPDATE dispatches SET risk_level = 'HIGH', average_confidence = 0.55 WHERE id = ?;", (dispatch_id,))
            conn.commit()
        finally:
            conn.close()

        res = reroute_service.evaluate_reroute(dispatch_id, simulated_scenario=scen_upper)
        res["simulated_scenario"] = scen_upper
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error simulating route degradation for dispatch '{dispatch_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
