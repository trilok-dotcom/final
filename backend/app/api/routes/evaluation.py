from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.services.evaluation_service import (
    evaluate_ai_model,
    evaluate_routing,
    evaluate_rerouting,
    evaluate_resources,
    evaluate_missions,
    evaluate_simulation,
    evaluate_osrm_baseline,
    evaluate_nearest_unit_baseline,
    get_overview,
    get_evaluation_runs,
    get_evaluation_run,
    export_run_metrics,
)

router = APIRouter(prefix="/evaluation", tags=["System Evaluation"])


class RunAiEvalRequest(BaseModel):
    sample_count: int = Field(default=50, ge=1, le=500)


class RunRoutingEvalRequest(BaseModel):
    sample_count: int = Field(default=20, ge=1, le=100)


@router.post("/ai", summary="Execute AI model accuracy, threshold sweep & inference latency evaluation")
async def run_ai_eval(req: Optional[RunAiEvalRequest] = None):
    sample_count = req.sample_count if req else 50
    try:
        res = evaluate_ai_model(num_samples=sample_count)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routing", summary="Execute AI emergency routing & route health evaluation")
async def run_routing_eval(req: Optional[RunRoutingEvalRequest] = None):
    sample_count = req.sample_count if req else 20
    try:
        res = evaluate_routing(num_samples=sample_count)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rerouting", summary="Execute dynamic rerouting performance evaluation")
async def run_rerouting_eval():
    try:
        res = evaluate_rerouting()
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resources", summary="Execute Stage 8B resource optimization & fleet utilization evaluation")
async def run_resources_eval():
    try:
        res = evaluate_resources()
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/missions", summary="Execute dispatch latency & live mission telemetry evaluation")
async def run_missions_eval():
    try:
        res = evaluate_missions()
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulation/{simulation_id}", summary="Execute disaster exercise simulation evaluation")
async def run_simulation_eval(simulation_id: str):
    try:
        res = evaluate_simulation(simulation_id=simulation_id)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/baseline/osrm", summary="Execute AI Emergency Routing vs OSRM Baseline comparison")
async def run_osrm_baseline_eval(sample_count: int = Query(10, ge=1, le=50)):
    try:
        res = evaluate_osrm_baseline(num_samples=sample_count)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/baseline/nearest-unit", summary="Execute Stage 8B Optimization vs Nearest Unit Baseline comparison")
async def run_nearest_unit_baseline_eval(sample_count: int = Query(10, ge=1, le=50)):
    try:
        res = evaluate_nearest_unit_baseline(num_samples=sample_count)
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview", summary="Retrieve system evaluation overview across all categories")
async def get_eval_overview():
    try:
        res = get_overview()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs", summary="List historical evaluation runs")
async def list_eval_runs():
    try:
        runs = get_evaluation_runs()
        return {"success": True, "count": len(runs), "runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}", summary="Get evaluation run details")
async def get_eval_run_detail(run_id: str):
    run_data = get_evaluation_run(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail=f"Evaluation run '{run_id}' not found.")
    return {"success": True, "data": run_data}


@router.get("/runs/{run_id}/metrics", summary="Get evaluation run metrics list")
async def get_eval_run_metrics(run_id: str):
    run_data = get_evaluation_run(run_id)
    if not run_data:
        raise HTTPException(status_code=404, detail=f"Evaluation run '{run_id}' not found.")
    return {"success": True, "count": len(run_data.get("metrics", [])), "metrics": run_data.get("metrics", [])}


@router.get("/runs/{run_id}/export", summary="Export evaluation run metrics in JSON or CSV format")
async def export_eval_run(run_id: str, format: str = Query("json", regex="^(json|csv)$")):
    try:
        content, mime_type = export_run_metrics(run_id, export_format=format)
        filename = f"{run_id}_export.{format.lower()}"
        return Response(
            content=content,
            media_type=mime_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
