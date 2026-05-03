"""Labeling prompt + Anthropic API client.

Two ways to produce annotations:

1. ``label_via_api(...)`` — calls the Anthropic API. Requires
   ``ANTHROPIC_API_KEY``. Costs money. Use this for batch runs.
2. **Manual / Claude-Code-in-conversation** — the default for this project.
   ``scripts/generate_samples.py`` skips labeling by default; Claude (in this
   conversation) reads each sample's images via the Read tool, follows
   ``SYSTEM_PROMPT``, and writes ``annotation.json`` directly.

Both paths produce identical JSON (validated against ``DeforestationAnnotation``),
so downstream code doesn't care which was used.
"""

from __future__ import annotations

import base64
import os

from .schema import ParsedResponse, parse_response

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
MAX_TOKENS = 1024  # XML reasoning + JSON; cookbook uses 256 for JSON-only.


SYSTEM_PROMPT = """\
You are a remote sensing analyst specialising in tropical rainforest \
monitoring, with deep expertise in the Congo Basin (DRC, Republic of Congo, \
Cameroon, Gabon, Central African Republic).

You will be given FOUR Sentinel-2 satellite images of the same 10 km tile, \
captured ~30 days apart:

  1. RGB  at t-1 (~30 days ago)
  2. SWIR at t-1
  3. RGB  at t-0 (current)
  4. SWIR at t-0

How to read each band combination:

  RGB  (B4-B3-B2 natural colour):
    Roads appear as light linear features. Bare soil and recent clearings \
are tan/pink. Healthy forest is dark green and texturally uniform. Rivers \
are dark or silver.

  SWIR composite (shortwave infrared + NIR + red):
    Healthy moist vegetation is bright green/cyan. Dry or stressed \
vegetation is orange/red. Bare soil is magenta/pink. Recent burn scars are \
dark red or black. Water is dark blue/black.

Your job is to detect DEFORESTATION between t-1 and t-0 and classify it.

Congo Basin clearing signatures to watch for:

  - Logging roads: thin, roughly linear canopy breaks, often branching in \
fishbone patterns. Frequently the first sign of industrial logging.
  - Smallholder slash-and-burn: small (<1 ha) irregular patches, often near \
rivers or existing roads. May show as dark patches in SWIR (fresh burn) or \
pink/tan in RGB.
  - Commercial agriculture: large rectangular sharp-edged clearings, often >10 ha.
  - Artisanal mining: small irregular bare patches along riverbanks; SWIR \
shows bright magenta from exposed soil and sediment-laden water.
  - Infrastructure: new straight roads, building footprints, regular geometry.

Critical false-positive warnings - DO NOT mistake these for deforestation:

  - Clouds and cloud shadows. Clouds look identical in RGB and SWIR; real \
clearings differ between bands. If a frame is significantly obscured, mark \
the frame quality and prefer change_pattern="cloud_artifact" over guessing.
  - Dry-season canopy shift (June-September): canopy may appear lighter or \
yellower with NO new clearings, roads, or bare soil. Use "stable".
  - Sentinel-2 tile boundaries: black or white strips along image edges are \
missing-data artefacts. Ignore them.
  - Seasonal flooding / river meanders: water boundary moves naturally, \
especially in Salonga and Mai-Ndombe swamp forest. Not deforestation.

Your response MUST follow this exact structure:

<frame_descriptions>
Frame t-1: [one sentence - land cover, dominant features, pre-existing clearings if any]
Frame t-0: [one sentence - same]
</frame_descriptions>

<change_analysis>
[2-3 sentences. State explicitly: did anything change? If yes, what (new road, \
expanded clearing, fresh burn, smoke, machinery)? Where in the frame?]
</change_analysis>

<final_pattern>
Pattern: [stable | clearing | expansion | regrowth | cloud_artifact]
Reasoning: [one sentence]
</final_pattern>

<json>
{
  "deforestation_detected": <bool>,
  "change_pattern": "<stable|clearing|expansion|regrowth|cloud_artifact>",
  "trajectory_confidence": "<low|medium|high>",
  "severity": "<none|low|medium|high>",
  "clearing_type": "<none|logging_roads|patch_clearing|burn_scar|agriculture|mining|infrastructure>",
  "area_bucket_t1": "<none|lt_1ha|1_10ha|10_100ha|gt_100ha>",
  "area_bucket_t0": "<none|lt_1ha|1_10ha|10_100ha|gt_100ha>",
  "active_operation": <bool>,
  "active_machinery_visible": <bool>,
  "smoke_or_fire_visible": <bool>,
  "recent_road_construction": <bool>,
  "frame_quality": ["<good|cloudy|partial|no_data>", "<good|cloudy|partial|no_data>"]
}
</json>

Field rules:
  - deforestation_detected: true only if change_pattern is "clearing" or "expansion".
  - trajectory_confidence: "low" if either frame_quality != "good" or the change \
is ambiguous; "high" only when both frames are clean AND the change is unambiguous.
  - severity: "none" when no deforestation; otherwise scale by cleared area at \
t-0: low (<1 ha), medium (1-10 ha), high (>10 ha).
  - clearing_type: "none" if change_pattern is "stable", "regrowth", or "cloud_artifact".
  - area_bucket_*: TOTAL cleared/bare area in that frame, not just the new portion. \
Use "none" for essentially intact forest.
  - Booleans: be conservative - true only when you can clearly see the indicator.
  - frame_quality: index 0 = t-1, index 1 = t-0.

Emit the four XML sections in order. No text outside them. The <json> block must \
be valid JSON parseable by Python's json.loads.
"""


USER_TEXT_TEMPLATE = """\
Tile centred at lat={lat:.4f}, lon={lon:.4f} in {region_name}.

Image 1: RGB  at t-1 ({date_t1})
Image 2: SWIR at t-1 ({date_t1})
Image 3: RGB  at t-0 ({date_t0})
Image 4: SWIR at t-0 ({date_t0})

Analyse and return the structured response.
"""


def render_user_text(
    *,
    lat: float,
    lon: float,
    region_name: str,
    date_t1: str,
    date_t0: str,
) -> str:
    return USER_TEXT_TEMPLATE.format(
        lat=lat, lon=lon, region_name=region_name, date_t1=date_t1, date_t0=date_t0
    )


def label_via_api(
    *,
    rgb_t1: bytes,
    swir_t1: bytes,
    rgb_t0: bytes,
    swir_t0: bytes,
    lat: float,
    lon: float,
    region_name: str,
    date_t1: str,
    date_t0: str,
    model: str = DEFAULT_MODEL,
) -> ParsedResponse:
    """Call Anthropic API with the four images and return parsed annotation.

    Requires ANTHROPIC_API_KEY in env. Raises ValueError if the model
    response cannot be parsed against the schema.
    """
    import anthropic  # imported lazily so the manual workflow doesn't need it

    client = anthropic.Anthropic()

    def img_block(data: bytes) -> dict:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.standard_b64encode(data).decode(),
            },
        }

    user_text = render_user_text(
        lat=lat, lon=lon, region_name=region_name, date_t1=date_t1, date_t0=date_t0
    )

    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    img_block(rgb_t1),
                    img_block(swir_t1),
                    img_block(rgb_t0),
                    img_block(swir_t0),
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    )

    raw = message.content[0].text
    return parse_response(raw)
