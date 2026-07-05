"""
Renders the single self-contained HTML file for a topology scene.

Inlines the vendored Three.js r147 core + OrbitControls + GLTFLoader (all
classic, non-module global scripts — research.md §1-2) as plain <script>
blocks, embeds the topology JSON payload from scene_builder.py, and ships a
runtime JS scene-construction engine that builds a true THREE.Group
device->interface hierarchy, TubeGeometry link cables anchored via
getWorldPosition(), procedural shapes by role, canvas-texture labels, and an
HTML/CSS legend overlay. Everything lives in one file with zero external
references — safe to open directly via file:// (FR-001).
"""

import json
from pathlib import Path

_VENDOR_DIR = Path(__file__).resolve().parent / "vendor" / "three"
_THREE_JS_PATH = _VENDOR_DIR / "core" / "three.js"
_ORBIT_CONTROLS_PATH = _VENDOR_DIR / "examples" / "js" / "controls" / "OrbitControls.js"
_GLTF_LOADER_PATH = _VENDOR_DIR / "examples" / "js" / "loaders" / "GLTFLoader.js"

_RUNTIME_JS = r"""
(function () {
  "use strict";

  var payload = JSON.parse(document.getElementById("topology-data").textContent);

  // ---------------------------------------------------------------------
  // Scene / camera / renderer / controls setup (standard three.js skeleton)
  // ---------------------------------------------------------------------
  var scene = new THREE.Scene();
  scene.background = new THREE.Color(0x11151c);

  var camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
  );
  camera.position.set(0, -60, 45);
  camera.up.set(0, 0, 1);

  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  document.getElementById("scene-container").appendChild(renderer.domElement);

  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0, 0);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  var dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
  dirLight.position.set(20, -30, 40);
  scene.add(dirLight);

  window.addEventListener("resize", function () {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // ---------------------------------------------------------------------
  // Label sprites (canvas-texture) — used for device/interface/link labels
  // ---------------------------------------------------------------------
  function makeLabelSprite(text, color) {
    var canvas = document.createElement("canvas");
    var ctx = canvas.getContext("2d");
    var fontSize = 48;
    ctx.font = fontSize + "px sans-serif";
    var textWidth = ctx.measureText(text).width;
    canvas.width = textWidth + 20;
    canvas.height = fontSize + 20;
    ctx.font = fontSize + "px sans-serif";
    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = color || "#ffffff";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 10, canvas.height / 2);

    var texture = new THREE.CanvasTexture(canvas);
    var material = new THREE.SpriteMaterial({ map: texture, depthTest: false });
    var sprite = new THREE.Sprite(material);
    var scale = 0.01;
    sprite.scale.set(canvas.width * scale, canvas.height * scale, 1);
    return sprite;
  }

  // ---------------------------------------------------------------------
  // Procedural device geometry by role/shape (FR-002)
  // ---------------------------------------------------------------------
  function proceduralGeometry(shapeName) {
    switch (shapeName) {
      case "cylinder":
        return new THREE.CylinderGeometry(0.5, 0.5, 0.9, 16);
      case "extruded_icon": {
        var shape = new THREE.Shape();
        shape.moveTo(-0.5, -0.5);
        shape.lineTo(0.5, -0.5);
        shape.lineTo(0.5, 0.5);
        shape.lineTo(-0.5, 0.5);
        shape.closePath();
        return new THREE.ExtrudeGeometry(shape, { depth: 0.3, bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.05 });
      }
      case "box":
      default:
        return new THREE.BoxGeometry(0.9, 0.9, 0.9);
    }
  }

  function decodeBase64ToArrayBuffer(base64) {
    var binary = atob(base64);
    var len = binary.length;
    var bytes = new Uint8Array(len);
    for (var i = 0; i < len; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  var gltfLoader = new THREE.GLTFLoader();

  function buildDeviceMesh(deviceGroup, deviceData) {
    var asset = deviceData.device_asset;
    if (asset.kind === "real_model" && asset.embedded_glb_base64) {
      // Real-stencil mode (User Story 5): decode the embedded base64 glTF/GLB
      // and parse it IN MEMORY — no fetch/XHR call, so this works on file://
      // (research.md §2).
      var arrayBuffer = decodeBase64ToArrayBuffer(asset.embedded_glb_base64);
      gltfLoader.parse(
        arrayBuffer,
        "",
        function (gltf) {
          gltf.scene.scale.set(1, 1, 1);
          deviceGroup.add(gltf.scene);
        },
        function (err) {
          console.error("GLTFLoader.parse failed for " + deviceData.hostname + ", falling back to box", err);
          var mesh = new THREE.Mesh(
            proceduralGeometry("box"),
            new THREE.MeshStandardMaterial({ color: deviceData.color })
          );
          deviceGroup.add(mesh);
        }
      );
      return;
    }

    var geometry = proceduralGeometry(asset.procedural_shape);
    var material = new THREE.MeshStandardMaterial({ color: deviceData.color });
    var mesh = new THREE.Mesh(geometry, material);
    deviceGroup.add(mesh);
  }

  // ---------------------------------------------------------------------
  // Build device -> interface hierarchy (FR-003: true parent-child groups)
  // ---------------------------------------------------------------------
  var deviceGroups = {};
  var interfaceObjects = {}; // "hostname::ifname" -> THREE.Object3D

  payload.devices.forEach(function (deviceData) {
    var deviceGroup = new THREE.Group();
    // Full transform, always all three components together (FR-009).
    deviceGroup.position.set(deviceData.position[0], deviceData.position[1], deviceData.position[2]);
    deviceGroup.rotation.set(deviceData.rotation[0], deviceData.rotation[1], deviceData.rotation[2]);
    deviceGroup.scale.set(deviceData.scale[0], deviceData.scale[1], deviceData.scale[2]);

    buildDeviceMesh(deviceGroup, deviceData);

    var label = makeLabelSprite(deviceData.hostname, "#ffffff");
    label.position.set(0, 0, 1.0);
    deviceGroup.add(label);

    deviceData.interfaces.forEach(function (ifaceData) {
      var ifaceGroup = new THREE.Group();
      ifaceGroup.position.set(
        ifaceData.local_offset[0],
        ifaceData.local_offset[1],
        ifaceData.local_offset[2]
      );
      var ifaceMesh = new THREE.Mesh(
        new THREE.SphereGeometry(0.12, 8, 8),
        new THREE.MeshStandardMaterial({ color: ifaceData.color || "#cccccc" })
      );
      ifaceGroup.add(ifaceMesh);

      var ifaceLabel = makeLabelSprite(ifaceData.name, "#dddddd");
      ifaceLabel.position.set(0, 0, 0.3);
      ifaceGroup.add(ifaceLabel);

      // True scene-graph parenting: the interface is a CHILD of the device
      // group, so repositioning the device moves it automatically — never a
      // precomputed world-space position (FR-003).
      deviceGroup.add(ifaceGroup);
      interfaceObjects[deviceData.hostname + "::" + ifaceData.name] = ifaceGroup;
    });

    scene.add(deviceGroup);
    deviceGroups[deviceData.hostname] = deviceGroup;
  });

  // ---------------------------------------------------------------------
  // Build links as TubeGeometry cables between resolved world positions
  // ---------------------------------------------------------------------
  var worldPos = new THREE.Vector3();

  function resolveEndpointWorldPosition(endpoint) {
    var key = endpoint.hostname + "::" + endpoint.interface_name;
    var obj = endpoint.interface_name ? interfaceObjects[key] : null;
    if (!obj) {
      obj = deviceGroups[endpoint.hostname];
    }
    if (!obj) {
      return null;
    }
    var v = new THREE.Vector3();
    obj.getWorldPosition(v);
    return v;
  }

  payload.links.forEach(function (linkData) {
    var a = resolveEndpointWorldPosition(linkData.endpoint_a);
    var b = resolveEndpointWorldPosition(linkData.endpoint_b);
    if (!a || !b) {
      return;
    }
    var curve = new THREE.CatmullRomCurve3([a, b]);
    var tubeGeometry = new THREE.TubeGeometry(curve, 8, 0.04, 8, false);
    var tubeMaterial = new THREE.MeshStandardMaterial({ color: linkData.color });
    var tube = new THREE.Mesh(tubeGeometry, tubeMaterial);
    scene.add(tube);

    var mid = a.clone().lerp(b, 0.5);
    var linkLabel = makeLabelSprite(linkData.label, "#eeeeee");
    linkLabel.position.copy(mid);
    scene.add(linkLabel);
  });

  // ---------------------------------------------------------------------
  // Legend (HTML/CSS overlay — part of the same generated page/scene)
  // ---------------------------------------------------------------------
  var legendEl = document.getElementById("legend");
  var legendHtml = "<strong>Roles</strong><br/>";
  payload.legend.roles.forEach(function (entry) {
    legendHtml +=
      '<span class="swatch" style="background:' +
      entry.color +
      '"></span>' +
      entry.label +
      " (" + entry.shape + ")<br/>";
  });
  legendHtml += "<br/><strong>State</strong><br/>";
  payload.legend.states.forEach(function (entry) {
    legendHtml +=
      '<span class="swatch" style="background:' +
      entry.color +
      '"></span>' +
      entry.label +
      "<br/>";
  });
  if (payload.fallback_report && payload.fallback_report.length > 0) {
    legendHtml += "<br/><strong>Real-stencil fallbacks</strong><br/>";
    payload.fallback_report.forEach(function (note) {
      legendHtml += note.hostname + " (" + note.role + "): " + note.reason + "<br/>";
    });
  }
  legendEl.innerHTML = legendHtml;

  // ---------------------------------------------------------------------
  // Render loop
  // ---------------------------------------------------------------------
  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();
})();
"""

_PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>NetClaw Topology - __SOURCE_LABEL__</title>
<style>
  html, body { margin: 0; padding: 0; overflow: hidden; background: #11151c; }
  #scene-container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
  #legend {
    position: absolute; top: 12px; left: 12px; z-index: 10;
    background: rgba(20, 24, 32, 0.85); color: #eee;
    font: 13px sans-serif; padding: 10px 14px; border-radius: 6px;
    max-height: 90vh; overflow-y: auto;
  }
  #legend .swatch {
    display: inline-block; width: 12px; height: 12px; margin-right: 6px;
    border-radius: 2px; vertical-align: middle;
  }
</style>
</head>
<body>
<div id="scene-container"></div>
<div id="legend"></div>
<script type="application/json" id="topology-data">__TOPOLOGY_JSON__</script>
<script>__THREE_JS__</script>
<script>__ORBIT_CONTROLS_JS__</script>
<script>__GLTF_LOADER_JS__</script>
<script>__RUNTIME_JS__</script>
</body>
</html>
"""


def render_html(payload: dict) -> str:
    """Render the single self-contained HTML file for the given scene payload."""
    three_js = _THREE_JS_PATH.read_text(encoding="utf-8")
    orbit_controls_js = _ORBIT_CONTROLS_PATH.read_text(encoding="utf-8")
    gltf_loader_js = _GLTF_LOADER_PATH.read_text(encoding="utf-8")
    # Escape "</" so no field value can prematurely close the embedding
    # <script> tag (e.g. a hostname/metadata value containing "</script>").
    topology_json = json.dumps(payload).replace("</", "<\\/")

    html = _PAGE_TEMPLATE
    html = html.replace("__SOURCE_LABEL__", payload.get("source_label", "topology"))
    html = html.replace("__TOPOLOGY_JSON__", topology_json)
    html = html.replace("__THREE_JS__", three_js)
    html = html.replace("__ORBIT_CONTROLS_JS__", orbit_controls_js)
    html = html.replace("__GLTF_LOADER_JS__", gltf_loader_js)
    html = html.replace("__RUNTIME_JS__", _RUNTIME_JS)
    return html
