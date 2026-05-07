"""Annotation schema and parser for the deforestation labeling pipeline.

The labeling model emits four XML sections followed by a JSON block; this
module owns both the typed schema for the JSON and the parser that extracts
it from the model's full response.
"""

from __future__ import annotations

import json
import re
from typing import List, Literal

from pydantic import BaseModel, Field, ValidationError

ChangePattern = Literal["stable", "clearing", "expansion", "regrowth", "cloud_artifact"]
FrameQuality = Literal["good", "cloudy", "partial", "no_data"]
Confidence = Literal["low", "medium", "high"]


class DeforestationAnnotation(BaseModel):
    """Slim deforestation schema (v2 onwards).

    Five fields from the original 13-field schema were dropped because
    they were not learnable at our dataset scale (24 train rows) and
    introduced internal contradictions (e.g. `change_pattern: expansion`
    + `deforestation_detected: false`):

      - deforestation_detected  (redundant with change_pattern)
      - severity, clearing_type, area_bucket_t1, area_bucket_t0
        (fine-grained categoricals; 0% on held-out)

    Existing `data/runs/.../annotation.json` files retain all 13 fields;
    `prepare_finetune.py` filters the dropped keys at training-data
    rendering time, and `evaluate.py` only scores the kept fields.
    """

    change_pattern: ChangePattern
    trajectory_confidence: Confidence

    active_operation: bool
    active_machinery_visible: bool
    smoke_or_fire_visible: bool
    recent_road_construction: bool

    frame_quality: List[FrameQuality] = Field(min_length=2, max_length=2)


class ParsedResponse(BaseModel):
    """Full parsed labeling response: the four XML sections plus the typed JSON."""

    frame_descriptions: str
    change_analysis: str
    final_pattern: str
    annotation: DeforestationAnnotation


_TAG_RE = {
    "frame_descriptions": re.compile(
        r"<frame_descriptions>(.*?)</frame_descriptions>", re.DOTALL
    ),
    "change_analysis": re.compile(r"<change_analysis>(.*?)</change_analysis>", re.DOTALL),
    "final_pattern": re.compile(r"<final_pattern>(.*?)</final_pattern>", re.DOTALL),
    "json": re.compile(r"<json>(.*?)</json>", re.DOTALL),
}


def parse_response(text: str) -> ParsedResponse:
    """Parse a full labeling response into typed sections.

    Raises:
        ValueError: if any required tag is missing or the JSON block is invalid.
    """
    sections: dict[str, str] = {}
    for key, pattern in _TAG_RE.items():
        match = pattern.search(text)
        if match is None:
            raise ValueError(f"missing <{key}> section in response")
        sections[key] = match.group(1).strip()

    raw_json = sections["json"]
    if raw_json.startswith("```"):
        raw_json = raw_json.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in <json> block: {exc}\n---\n{raw_json}") from exc

    try:
        annotation = DeforestationAnnotation(**payload)
    except ValidationError as exc:
        raise ValueError(f"annotation failed schema validation: {exc}") from exc

    return ParsedResponse(
        frame_descriptions=sections["frame_descriptions"],
        change_analysis=sections["change_analysis"],
        final_pattern=sections["final_pattern"],
        annotation=annotation,
    )
