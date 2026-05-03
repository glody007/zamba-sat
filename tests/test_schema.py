"""Schema and parser tests."""

from __future__ import annotations

import pytest

from zamba_sat.schema import DeforestationAnnotation, parse_response


VALID_RESPONSE = """\
<frame_descriptions>
Frame t-1: Dense unbroken canopy with a meandering river in the lower left.
Frame t-0: Same canopy with a fresh linear clearing visible in the upper right quadrant.
</frame_descriptions>

<change_analysis>
A new linear clearing appeared between t-1 and t-0, consistent with a logging road
roughly 200m long. No clouds in either frame; the change is unambiguous.
</change_analysis>

<final_pattern>
Pattern: clearing
Reasoning: A road-like break in the canopy is present in t-0 and absent in t-1.
</final_pattern>

<json>
{
  "deforestation_detected": true,
  "change_pattern": "clearing",
  "trajectory_confidence": "high",
  "severity": "low",
  "clearing_type": "logging_roads",
  "area_bucket_t1": "none",
  "area_bucket_t0": "lt_1ha",
  "active_operation": false,
  "active_machinery_visible": false,
  "smoke_or_fire_visible": false,
  "recent_road_construction": true,
  "frame_quality": ["good", "good"]
}
</json>
"""


def test_parse_valid_response_returns_typed_annotation():
    parsed = parse_response(VALID_RESPONSE)
    assert isinstance(parsed.annotation, DeforestationAnnotation)
    assert parsed.annotation.deforestation_detected is True
    assert parsed.annotation.change_pattern == "clearing"
    assert parsed.annotation.frame_quality == ["good", "good"]


def test_parse_response_strips_markdown_fences_inside_json():
    text = VALID_RESPONSE.replace(
        '<json>\n{', '<json>\n```json\n{'
    ).replace('}\n</json>', '}\n```\n</json>')
    parsed = parse_response(text)
    assert parsed.annotation.change_pattern == "clearing"


def test_parse_response_rejects_missing_section():
    text = VALID_RESPONSE.replace("<change_analysis>", "<missing>").replace(
        "</change_analysis>", "</missing>"
    )
    with pytest.raises(ValueError, match="missing <change_analysis>"):
        parse_response(text)


def test_parse_response_rejects_invalid_enum():
    text = VALID_RESPONSE.replace('"clearing"', '"definitely_not_a_pattern"', 1)
    with pytest.raises(ValueError, match="schema validation"):
        parse_response(text)


def test_frame_quality_must_be_length_two():
    with pytest.raises(ValueError):
        DeforestationAnnotation(
            deforestation_detected=False,
            change_pattern="stable",
            trajectory_confidence="high",
            severity="none",
            clearing_type="none",
            area_bucket_t1="none",
            area_bucket_t0="none",
            active_operation=False,
            active_machinery_visible=False,
            smoke_or_fire_visible=False,
            recent_road_construction=False,
            frame_quality=["good"],  # too short
        )
