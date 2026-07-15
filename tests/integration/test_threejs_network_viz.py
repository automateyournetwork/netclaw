"""
Integration tests for the threejs-network-viz skill.

Unlike UE5/Blender, this skill's "live dependency" isn't a desktop engine —
it's a real browser actually executing the generated HTML/JS. These tests
render the generated scene in a real headless browser (via Playwright, if
installed) and assert on genuine runtime behavior (WebGL context created, no
JS errors, legend populated from real data) rather than mocking the one
thing that would make a rendering bug silently pass, matching the
never-mock-the-critical-dependency rule from ue5-network-viz/045's own tests.

Run:
    pytest tests/integration/test_threejs_network_viz.py -v

Requires:
    pip install playwright && playwright install chromium
Skips automatically if Playwright/Chromium isn't available.
"""

import sys
from pathlib import Path

import pytest

skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "threejs-network-viz"
sys.path.insert(0, str(skill_path))

from html_template import render_html  # noqa: E402
from scene_builder import build_scene_payload  # noqa: E402
from sources import from_cml, from_freeform, from_gns3  # noqa: E402

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Software-rendering flags so WebGL works in a GPU-less CI/sandbox container.
_HEADLESS_GL_ARGS = [
    "--use-angle=swiftshader",
    "--use-gl=angle",
    "--enable-unsafe-swiftshader",
    "--no-sandbox",
]

_CML_RAW = {
    "source": "cml-lab-integration-test",
    "devices": [
        {"hostname": "r1", "device_type": "router", "interfaces": [{"name": "Gi0/0"}]},
        {"hostname": "sw1", "device_type": "switch", "interfaces": [{"name": "Gi0/1"}]},
        {"hostname": "fw1", "interfaces": [], "status": "down"},
    ],
    "links": [
        {
            "source_device": "r1",
            "target_device": "sw1",
            "source_interface": "Gi0/0",
            "target_interface": "Gi0/1",
            "status": "healthy",
        },
        {"source_device": "sw1", "target_device": "fw1", "status": "down"},
    ],
}

def _render_and_open(tmp_path, payload) -> Path:
    html = render_html(payload)
    out_file = tmp_path / "scene.html"
    out_file.write_text(html, encoding="utf-8")
    return out_file


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright not installed")
def test_cml_topology_renders_without_errors_in_a_real_browser(tmp_path):
    payload = build_scene_payload(from_cml(_CML_RAW))
    scene_file = _render_and_open(tmp_path, payload)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=_HEADLESS_GL_ARGS)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(scene_file.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_timeout(1000)

        result = page.evaluate(
            """() => {
                const canvas = document.querySelector('#scene-container canvas');
                const legend = document.getElementById('legend');
                const gl = canvas ? (canvas.getContext('webgl2') || canvas.getContext('webgl')) : null;
                return {
                    hasCanvas: !!canvas,
                    webglOk: !!gl,
                    legendText: legend ? legend.innerText : '',
                };
            }"""
        )
        browser.close()

    assert errors == []
    assert result["hasCanvas"] is True
    assert result["webglOk"] is True
    assert "Router" in result["legendText"]
    assert "Switch" in result["legendText"]
    assert "Firewall" in result["legendText"]


def test_two_different_live_sources_use_identical_rendering_conventions():
    """User Story 2's independent test: a CML- and a GNS3-sourced topology
    must render using the same shape/color/label/legend conventions."""
    gns3_raw = {
        "source": "gns3-project-integration-test",
        "devices": [
            {"hostname": "core-rtr", "device_type": "router"},
            {"hostname": "dist-sw", "device_type": "switch"},
        ],
        "links": [{"source_device": "core-rtr", "target_device": "dist-sw", "status": "healthy"}],
    }

    cml_payload = build_scene_payload(from_cml(_CML_RAW))
    gns3_payload = build_scene_payload(from_gns3(gns3_raw))

    assert cml_payload["legend"] == gns3_payload["legend"]

    cml_router = next(d for d in cml_payload["devices"] if d["role"] == "router")
    gns3_router = next(d for d in gns3_payload["devices"] if d["role"] == "router")
    assert cml_router["color"] == gns3_router["color"]
    assert (
        cml_router["device_asset"]["procedural_shape"]
        == gns3_router["device_asset"]["procedural_shape"]
    )


def test_freeform_topology_uses_identical_conventions_to_a_live_source():
    """User Story 3's independent test: a freeform description must render
    using the same shape/color/label/legend conventions as a live source."""
    cml_payload = build_scene_payload(from_cml(_CML_RAW))
    freeform_payload = build_scene_payload(
        from_freeform("r1 is a router, sw1 is a switch, r1 connects to sw1")
    )

    assert cml_payload["legend"] == freeform_payload["legend"]

    cml_router = next(d for d in cml_payload["devices"] if d["role"] == "router")
    freeform_router = next(d for d in freeform_payload["devices"] if d["role"] == "router")
    assert cml_router["color"] == freeform_router["color"]
    assert (
        cml_router["device_asset"]["procedural_shape"]
        == freeform_router["device_asset"]["procedural_shape"]
    )
