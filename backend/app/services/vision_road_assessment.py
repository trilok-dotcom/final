import os
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field

from app.utils.logging import get_logger

logger = get_logger("app.services.vision_road_assessment")


class RoadSegmentAssessment(BaseModel):
    id: str = Field(..., description="Unique segment identifier e.g. road_001")
    condition: Literal["SAFE", "DEGRADED", "BLOCKED", "UNKNOWN"] = Field(..., description="Estimated road condition")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Visual assessment confidence score (0-1)")
    reason: str = Field(..., description="Visual reasoning for condition classification")
    points: List[List[float]] = Field(
        default_factory=list,
        description="Extracted road polyline or polygon coordinates normalized 0-1000 [x, y] relative to image dimensions"
    )
    before_points: Optional[List[List[float]]] = Field(None, description="Optional bounding box or points in BEFORE image")
    after_points: Optional[List[List[float]]] = Field(None, description="Optional bounding box or points in AFTER image")


class VisionRoadAssessmentResult(BaseModel):
    overall_summary: str = Field(..., description="High-level assessment summary")
    disclaimer: str = Field(
        default="Image-based traversability estimate — not structural safety certification.",
        description="Mandatory disclaimer string"
    )
    roads: List[RoadSegmentAssessment] = Field(default_factory=list, description="Assessed road segments list")


SYSTEM_PROMPT = """You are analyzing satellite/aerial imagery for disaster-response emergency road mapping and traversability.

Image 1 is the BEFORE-disaster satellite image.
Image 2 is the AFTER-disaster satellite image.

1. Detect all visible drivable road surfaces in the AFTER image.
   Do NOT detect rivers, buildings, rooftops, vegetation, railways, sidewalks unless part of drivable road, or empty land.

2. For each detected road segment, extract its geometry as polyline coordinates [x, y] normalized to 0-1000 relative to image width and height (where [0, 0] is top-left and [1000, 1000] is bottom-right). Use [x, y] format.

3. Compare the baseline BEFORE image against the AFTER image to classify post-disaster condition for each road segment:
   - SAFE: road surface intact, clear, continuous, traversable.
   - DEGRADED: road visible but damaged, partially submerged, obstructed, flooded, or covered in debris.
   - BLOCKED: road submerged, destroyed, completely blocked, or severed.
   - UNKNOWN: ambiguous or obscured visual evidence.

Do not claim structural safety. Follow actual visible road geometry. Do not invent roads that are not visible.

Return ONLY raw JSON matching this schema:
{
  "overall_summary": "Detailed summary of detected roads and post-disaster damage observed.",
  "disclaimer": "Image-based traversability estimate — not structural safety certification.",
  "roads": [
    {
      "id": "road_001",
      "condition": "SAFE",
      "confidence": 0.92,
      "reason": "Road surface intact and clear.",
      "points": [[120, 340], [250, 410], [500, 480]]
    }
  ]
}
"""


from dotenv import load_dotenv

# Auto-load .env environment variables
load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


class VisionAssessmentProvider:
    """Configurable Vision AI API Provider for Post-Disaster Road Assessment.

    Uses environment variables:
      - VISION_AI_PROVIDER (e.g. 'gemini', 'openai', 'anthropic', 'ollama', 'custom')
      - VISION_AI_API_KEY / GOOGLE_API_KEY / GEMINI_API_KEY (Server-side API key ONLY)
      - VISION_AI_MODEL (e.g. 'gemini-1.5-flash', 'gpt-4o', 'claude-3-5-sonnet')
    """

    def __init__(self):
        self.provider = os.getenv("VISION_AI_PROVIDER", "gemini").lower().strip()
        self.api_key = (
            os.getenv("VISION_AI_API_KEY", "").strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("GOOGLE_API_KEY", "").strip()
        )
        self.model = os.getenv("VISION_AI_MODEL", "gemini-1.5-flash").strip()

    def is_configured(self) -> bool:
        """Check if Vision AI API provider key is configured."""
        return bool(self.api_key and self.provider != "none")

    def _encode_image_base64(self, image_path: Path) -> str:
        """Encode image file to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def assess_road_traversability(
        self,
        before_image_path: Path,
        after_image_path: Path,
        assessment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send BEFORE and AFTER images to Vision AI API and parse structured JSON.

        Returns:
            Dict containing parsed assessment result or provider_not_configured status.
        """
        if not self.is_configured():
            logger.info("VISION_AI_API_KEY / GOOGLE_API_KEY missing or not configured. Returning provider_not_configured status.")
            return {
                "status": "provider_not_configured",
                "message": "Vision AI provider is not configured.",
                "provider_configured": False,
            }

        logger.info(
            f"VISION AI REQUEST START: provider={self.provider}, model={self.model}, "
            f"before_image={before_image_path.name}, after_image={after_image_path.name}"
        )

        try:
            b64_before = self._encode_image_base64(before_image_path)
            b64_after = self._encode_image_base64(after_image_path)

            if self.provider in ("gemini", "google"):
                raw_json = self._call_gemini_vision_api(b64_before, b64_after)
            elif self.provider in ("openai", "custom"):
                raw_json = self._call_openai_vision_api(b64_before, b64_after)
            else:
                raw_json = self._call_generic_vision_api(b64_before, b64_after)

            # Strip markdown code fencing if present
            cleaned_json = raw_json.strip()
            if cleaned_json.startswith("```"):
                lines = cleaned_json.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned_json = "\n".join(lines).strip()

            # Parse and validate with Pydantic
            parsed_data = json.loads(cleaned_json)
            validated_result = VisionRoadAssessmentResult(**parsed_data)

            safe_cnt = sum(1 for r in validated_result.roads if r.condition == "SAFE")
            degraded_cnt = sum(1 for r in validated_result.roads if r.condition == "DEGRADED")
            blocked_cnt = sum(1 for r in validated_result.roads if r.condition == "BLOCKED")
            unknown_cnt = sum(1 for r in validated_result.roads if r.condition == "UNKNOWN")

            road_cnt = len(validated_result.roads)
            status_str = "COMPLETED" if road_cnt > 0 else "no_roads_detected"

            logger.info(f"VISION AI RESPONSE RECEIVED: status={status_str}")
            logger.info(f"VISION AI SEGMENTS={road_cnt}")
            logger.info(f"VISION AI CONDITIONS: SAFE={safe_cnt}, DEGRADED={degraded_cnt}, BLOCKED={blocked_cnt}, UNKNOWN={unknown_cnt}")

            # Save raw Vision AI response debug JSON (without API keys)
            if assessment_id:
                try:
                    from datetime import datetime
                    output_dir = Path(__file__).resolve().parent.parent.parent / "outputs" / "uploads"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    debug_file = output_dir / f"vision_response_{assessment_id}.json"
                    with open(debug_file, "w", encoding="utf-8") as f:
                        json.dump({
                            "provider": self.provider,
                            "model": self.model,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "road_count": road_cnt,
                            "summary": {
                                "safe": safe_cnt,
                                "degraded": degraded_cnt,
                                "blocked": blocked_cnt,
                                "unknown": unknown_cnt,
                            },
                            "raw_response": parsed_data,
                        }, f, indent=2)
                except Exception as debug_err:
                    logger.warning(f"Failed to save vision debug json: {debug_err}")

            res_dict = validated_result.model_dump()
            res_dict["status"] = status_str
            res_dict["provider_configured"] = True
            res_dict["provider"] = self.provider
            res_dict["model"] = self.model
            res_dict["road_count"] = road_cnt
            return res_dict

        except Exception as e:
            logger.error(f"Vision AI assessment call failed: {e}", exc_info=True)
            return {
                "status": "vision_ai_failed",
                "message": f"Vision AI assessment API call failed: {str(e)}",
                "provider_configured": True,
                "provider": self.provider,
                "model": self.model,
                "road_count": 0,
            }

    def _call_gemini_vision_api(self, b64_before: str, b64_after: str) -> str:
        """Execute HTTP REST call to Google Gemini Vision API."""
        models_to_try = ["gemini-3.6-flash", self.model]
        unique_models = []
        for m in models_to_try:
            if m and m not in unique_models and "gpt" not in m:
                unique_models.append(m)

        last_error = None
        for model in unique_models:
            # 1. Try Native Gemini generateContent endpoint first
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                prompt_text = (
                    f"{SYSTEM_PROMPT}\n\n"
                    "Analyze these two images (Image 1 = BEFORE disaster, Image 2 = AFTER disaster) and extract road traversability coordinates. "
                    "Return strictly raw JSON conforming to the requested schema."
                )
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt_text},
                                {"inline_data": {"mime_type": "image/png", "data": b64_before}},
                                {"inline_data": {"mime_type": "image/png", "data": b64_after}},
                            ]
                        }
                    ],
                    "generationConfig": {
                        "response_mime_type": "application/json",
                        "temperature": 0.2,
                        "maxOutputTokens": 1500,
                    },
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as http_err:
                err_body = http_err.read().decode("utf-8", errors="ignore")
                logger.warning(f"Gemini native endpoint model '{model}' HTTP {http_err.code}: {err_body}")
                last_error = f"HTTP {http_err.code}: {err_body}"
                if http_err.code == 429:
                    # Daily quota exhausted on free tier, fast exit
                    break
            except Exception as ex:
                logger.warning(f"Gemini native endpoint model '{model}' failed: {ex}")
                last_error = str(ex)

            # 2. Try OpenAI-compatible endpoint
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                payload = {
                    "model": model,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Image 1 is BEFORE disaster. Image 2 is AFTER disaster. Compare traversability and return JSON schema."},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_before}"}},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_after}"}},
                            ],
                        },
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.2,
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as http_err:
                err_body = http_err.read().decode("utf-8", errors="ignore")
                logger.warning(f"Gemini OpenAI endpoint model '{model}' HTTP {http_err.code}: {err_body}")
                last_error = f"HTTP {http_err.code}: {err_body}"
                if http_err.code == 429:
                    break
            except Exception as ex:
                logger.warning(f"Gemini OpenAI endpoint model '{model}' failed: {ex}")
                last_error = str(ex)

        raise RuntimeError(f"All Gemini API models failed. Last error: {last_error}")

    def _call_openai_vision_api(self, b64_before: str, b64_after: str) -> str:
        """Execute HTTP REST call to OpenAI Multi-Modal Vision API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model or "gpt-4o",
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Image 1 is BEFORE disaster. Image 2 is AFTER disaster. Analyze road traversability and return structured JSON.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_before}"},
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_after}"},
                        },
                    ],
                },
            ],
            "max_tokens": 1500,
            "temperature": 0.2,
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return content

    def _call_generic_vision_api(self, b64_before: str, b64_after: str) -> str:
        """Generic fallback for other vision AI API providers."""
        return self._call_openai_vision_api(b64_before, b64_after)


vision_assessment_provider = VisionAssessmentProvider()

