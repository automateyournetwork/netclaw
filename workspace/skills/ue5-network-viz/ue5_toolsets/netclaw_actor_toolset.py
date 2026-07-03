"""
NetClaw Actor Toolset for Unreal Engine 5.8 MCP

This Python toolset exposes actor spawning, material, and transform tools
for 3D network topology visualization.

INSTALLATION:
1. Copy this file to your UE5 project: Content/Python/netclaw_actor_toolset.py
2. Enable Python plugin: Edit > Plugins > "Python Editor Script Plugin" > Enable
3. Restart UE5 Editor
4. Run in console: ModelContextProtocol.RefreshTools
5. Verify with: list_toolsets (should show NetClawActorToolset)

Copyright 2025 NetClaw Project - MIT License
"""

import unreal
from toolset_registry import tool_call


@unreal.uclass()
class NetClawActorToolset(unreal.ToolsetDefinition):
    """Provides tools for spawning and managing network device actors,
    applying materials for health visualization, and controlling camera."""

    # =========================================================================
    # ACTOR SPAWNING
    # =========================================================================

    @staticmethod
    @tool_call
    def spawn_device_actor(
        device_name: str,
        device_type: str,
        x: float,
        y: float,
        z: float,
        scale: float = 100.0
    ) -> str:
        """Spawn a static mesh actor representing a network device.

        Args:
            device_name: Unique identifier for the device (e.g., "router-1")
            device_type: Type of device - "router", "switch", "firewall", "server", "endpoint", "ap"
            x: X coordinate in world space (Unreal units)
            y: Y coordinate in world space (Unreal units)
            z: Z coordinate in world space (Unreal units)
            scale: Uniform scale factor (default 100.0)

        Returns:
            Actor name/path if successful, empty string on failure
        """
        # Map device type to mesh
        mesh_paths = {
            "router": "/Engine/BasicShapes/Cube.Cube",
            "switch": "/Engine/BasicShapes/Cube.Cube",
            "firewall": "/Engine/BasicShapes/Cube.Cube",
            "server": "/Engine/BasicShapes/Cube.Cube",
            "endpoint": "/Engine/BasicShapes/Sphere.Sphere",
            "ap": "/Engine/BasicShapes/Sphere.Sphere",
            "unknown": "/Engine/BasicShapes/Cube.Cube"
        }

        mesh_path = mesh_paths.get(device_type.lower(), mesh_paths["unknown"])
        mesh = unreal.load_asset(mesh_path)

        if not mesh:
            unreal.log_error(f"Failed to load mesh: {mesh_path}")
            return ""

        # Get editor subsystem for spawning
        editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

        # Spawn static mesh actor
        location = unreal.Vector(x, y, z)
        rotation = unreal.Rotator(0, 0, 0)

        actor = editor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor,
            location,
            rotation
        )

        if actor:
            # Set the mesh
            mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
            if mesh_component:
                mesh_component.set_static_mesh(mesh)

            # Set scale
            actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))

            # Set label/name for identification
            actor.set_actor_label(f"NetClaw_{device_name}")

            # Add tag for bulk operations
            actor.tags.append("NetClawDevice")
            actor.tags.append(f"DeviceType_{device_type}")

            return actor.get_actor_label()

        return ""

    @staticmethod
    @tool_call
    def spawn_link_actor(
        link_name: str,
        start_x: float,
        start_y: float,
        start_z: float,
        end_x: float,
        end_y: float,
        end_z: float,
        thickness: float = 10.0
    ) -> str:
        """Spawn a cylinder actor representing a network link between devices.

        Args:
            link_name: Unique identifier for the link (e.g., "router1_to_switch1")
            start_x: Start X coordinate
            start_y: Start Y coordinate
            start_z: Start Z coordinate
            end_x: End X coordinate
            end_y: End Y coordinate
            end_z: End Z coordinate
            thickness: Cylinder radius (default 10.0)

        Returns:
            Actor name/path if successful, empty string on failure
        """
        import math

        mesh = unreal.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
        if not mesh:
            return ""

        editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

        # Calculate midpoint
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        mid_z = (start_z + end_z) / 2

        # Calculate length
        dx = end_x - start_x
        dy = end_y - start_y
        dz = end_z - start_z
        length = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Calculate rotation to align cylinder
        # Cylinder default orientation is along Z axis
        pitch = math.degrees(math.atan2(math.sqrt(dx*dx + dy*dy), dz))
        yaw = math.degrees(math.atan2(dy, dx))

        location = unreal.Vector(mid_x, mid_y, mid_z)
        rotation = unreal.Rotator(pitch - 90, yaw, 0)

        actor = editor_subsystem.spawn_actor_from_class(
            unreal.StaticMeshActor,
            location,
            rotation
        )

        if actor:
            mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
            if mesh_component:
                mesh_component.set_static_mesh(mesh)

            # Scale: X and Y for thickness, Z for length
            # Default cylinder is 100 units tall
            scale_z = length / 100.0
            scale_xy = thickness / 50.0  # Default cylinder radius is 50
            actor.set_actor_scale3d(unreal.Vector(scale_xy, scale_xy, scale_z))

            actor.set_actor_label(f"NetClaw_Link_{link_name}")
            actor.tags.append("NetClawLink")

            return actor.get_actor_label()

        return ""

    @staticmethod
    @tool_call
    def set_actor_transform(
        actor_label: str,
        x: float,
        y: float,
        z: float,
        scale: float = -1.0
    ) -> bool:
        """Move an existing actor to a new position.

        Args:
            actor_label: The actor's label (e.g., "NetClaw_router-1")
            x: New X coordinate
            y: New Y coordinate
            z: New Z coordinate
            scale: New uniform scale (-1 to keep current)

        Returns:
            True if successful
        """
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()

        for actor in actors:
            if actor.get_actor_label() == actor_label:
                actor.set_actor_location(unreal.Vector(x, y, z), False, False)
                if scale > 0:
                    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
                return True

        return False

    @staticmethod
    @tool_call
    def destroy_actor(actor_label: str) -> bool:
        """Destroy an actor by its label.

        Args:
            actor_label: The actor's label to destroy

        Returns:
            True if destroyed
        """
        editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = editor_subsystem.get_all_level_actors()

        for actor in actors:
            if actor.get_actor_label() == actor_label:
                editor_subsystem.destroy_actor(actor)
                return True

        return False

    # =========================================================================
    # MATERIAL & COLOR
    # =========================================================================

    @staticmethod
    @tool_call
    def apply_color_to_actor(
        actor_label: str,
        r: float,
        g: float,
        b: float,
        a: float = 1.0
    ) -> bool:
        """Apply a solid color material to an actor.

        Args:
            actor_label: The actor's label
            r: Red component (0.0-1.0)
            g: Green component (0.0-1.0)
            b: Blue component (0.0-1.0)
            a: Alpha/opacity (0.0-1.0, default 1.0)

        Returns:
            True if successful
        """
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()

        for actor in actors:
            if actor.get_actor_label() == actor_label:
                mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
                if mesh_component:
                    # Create dynamic material instance
                    base_material = unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial")
                    if base_material:
                        dyn_material = unreal.KismetMaterialLibrary.create_dynamic_material_instance(
                            unreal.EditorLevelLibrary.get_editor_world(),
                            base_material
                        )
                        if dyn_material:
                            # Set color parameter (assumes material has BaseColor param)
                            color = unreal.LinearColor(r, g, b, a)
                            dyn_material.set_vector_parameter_value("BaseColor", color)
                            mesh_component.set_material(0, dyn_material)
                            return True

        return False

    @staticmethod
    @tool_call
    def apply_device_color_by_type(actor_label: str, device_type: str) -> bool:
        """Apply standard NetClaw color based on device type.

        Args:
            actor_label: The actor's label
            device_type: "router", "switch", "firewall", "server", "endpoint", "ap"

        Returns:
            True if successful
        """
        # NetClaw standard colors (RGB 0-1 range)
        colors = {
            "router": (0.2, 0.4, 0.8),      # Blue
            "switch": (0.2, 0.7, 0.3),      # Green
            "firewall": (0.8, 0.2, 0.2),    # Red
            "server": (0.5, 0.3, 0.7),      # Purple
            "endpoint": (0.6, 0.6, 0.6),    # Gray
            "ap": (0.2, 0.7, 0.7),          # Cyan
            "unknown": (0.5, 0.5, 0.5)      # Medium gray
        }

        r, g, b = colors.get(device_type.lower(), colors["unknown"])
        return NetClawActorToolset.apply_color_to_actor(actor_label, r, g, b)

    @staticmethod
    @tool_call
    def apply_health_color(actor_label: str, health_state: str) -> bool:
        """Apply color based on device health state.

        Args:
            actor_label: The actor's label
            health_state: "healthy", "warning", "critical", "unreachable"

        Returns:
            True if successful
        """
        colors = {
            "healthy": (0.2, 0.8, 0.2),     # Green
            "warning": (1.0, 0.6, 0.0),     # Orange
            "critical": (1.0, 0.0, 0.0),    # Bright Red
            "unreachable": (0.4, 0.0, 0.0)  # Dark Red
        }

        r, g, b = colors.get(health_state.lower(), (0.5, 0.5, 0.5))
        return NetClawActorToolset.apply_color_to_actor(actor_label, r, g, b)

    # =========================================================================
    # SCENE MANAGEMENT
    # =========================================================================

    @staticmethod
    @tool_call
    def clear_netclaw_actors() -> int:
        """Remove all actors tagged as NetClaw devices or links.

        Returns:
            Number of actors destroyed
        """
        editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = editor_subsystem.get_all_level_actors()

        count = 0
        for actor in actors:
            label = actor.get_actor_label()
            if label.startswith("NetClaw_"):
                editor_subsystem.destroy_actor(actor)
                count += 1

        return count

    @staticmethod
    @tool_call
    def list_netclaw_actors() -> list:
        """Get list of all NetClaw actors in the scene.

        Returns:
            List of actor labels
        """
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()

        netclaw_actors = []
        for actor in actors:
            label = actor.get_actor_label()
            if label.startswith("NetClaw_"):
                netclaw_actors.append(label)

        return netclaw_actors

    @staticmethod
    @tool_call
    def get_scene_bounds() -> dict:
        """Get the bounding box of all NetClaw actors.

        Returns:
            Dictionary with min_x, max_x, min_y, max_y, min_z, max_z
        """
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()

        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')

        count = 0
        for actor in actors:
            if actor.get_actor_label().startswith("NetClaw_"):
                loc = actor.get_actor_location()
                min_x = min(min_x, loc.x)
                max_x = max(max_x, loc.x)
                min_y = min(min_y, loc.y)
                max_y = max(max_y, loc.y)
                min_z = min(min_z, loc.z)
                max_z = max(max_z, loc.z)
                count += 1

        if count == 0:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "min_z": 0, "max_z": 0}

        return {
            "min_x": min_x, "max_x": max_x,
            "min_y": min_y, "max_y": max_y,
            "min_z": min_z, "max_z": max_z
        }

    # =========================================================================
    # CAMERA CONTROL
    # =========================================================================

    @staticmethod
    @tool_call
    def focus_camera_on_actor(actor_label: str, distance: float = 500.0) -> bool:
        """Move the editor viewport camera to focus on an actor.

        Args:
            actor_label: The actor to focus on
            distance: Distance from actor (default 500)

        Returns:
            True if successful
        """
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()

        for actor in actors:
            if actor.get_actor_label() == actor_label:
                loc = actor.get_actor_location()

                # Set camera above and behind, looking at actor
                cam_loc = unreal.Vector(loc.x - distance, loc.y - distance, loc.z + distance)

                # Focus viewport on actor
                unreal.EditorLevelLibrary.pilot_level_actor(actor)
                return True

        return False

    @staticmethod
    @tool_call
    def set_camera_location(x: float, y: float, z: float, pitch: float = -45.0, yaw: float = 45.0) -> bool:
        """Set the editor viewport camera position and rotation.

        Args:
            x: Camera X position
            y: Camera Y position
            z: Camera Z position
            pitch: Camera pitch in degrees (default -45, looking down)
            yaw: Camera yaw in degrees (default 45)

        Returns:
            True if successful
        """
        # Get viewport client
        viewport = unreal.UnrealEditorSubsystem.get_level_viewport_camera_info()
        if viewport:
            location = unreal.Vector(x, y, z)
            rotation = unreal.Rotator(pitch, yaw, 0)
            unreal.UnrealEditorSubsystem.set_level_viewport_camera_info(location, rotation)
            return True

        return False

    @staticmethod
    @tool_call
    def camera_overview() -> bool:
        """Position camera for an overview of all NetClaw actors.

        Returns:
            True if successful
        """
        bounds = NetClawActorToolset.get_scene_bounds()

        # Calculate center
        center_x = (bounds["min_x"] + bounds["max_x"]) / 2
        center_y = (bounds["min_y"] + bounds["max_y"]) / 2
        center_z = (bounds["min_z"] + bounds["max_z"]) / 2

        # Calculate distance based on scene size
        width = max(bounds["max_x"] - bounds["min_x"], bounds["max_y"] - bounds["min_y"])
        distance = max(width * 1.5, 1000)

        # Position camera above and at an angle
        return NetClawActorToolset.set_camera_location(
            center_x - distance * 0.7,
            center_y - distance * 0.7,
            center_z + distance,
            pitch=-45.0,
            yaw=45.0
        )

    # =========================================================================
    # TEXT LABELS
    # =========================================================================

    @staticmethod
    @tool_call
    def add_text_label(
        label_name: str,
        text: str,
        x: float,
        y: float,
        z: float,
        size: float = 150.0
    ) -> str:
        """Add a 3D text label in the scene.

        Args:
            label_name: Unique identifier for the label
            text: Text to display
            x: X position
            y: Y position
            z: Z position
            size: Text world size (default 150 — readable at typical topology
                scale; scale to roughly scene_bounding_box_diagonal / 20 for
                very small or very large scenes)

        Returns:
            Actor label if successful
        """
        editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

        location = unreal.Vector(x, y, z)
        rotation = unreal.Rotator(0, 0, 0)

        actor = editor_subsystem.spawn_actor_from_class(
            unreal.TextRenderActor,
            location,
            rotation
        )

        if actor:
            text_component = actor.get_component_by_class(unreal.TextRenderComponent)
            if text_component:
                text_component.set_text(text)
                text_component.set_world_size(size)
                # Make text face camera (billboard style)
                text_component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)

            # TextRenderActor spawns with an editor-only billboard/sprite
            # child (the "Tt" icon) that renders as a black box alongside the
            # real text in editor viewport screenshots. Hide it so only the
            # text itself is visible.
            for comp in actor.get_components_by_class(unreal.BillboardComponent):
                comp.set_visibility(False)
                comp.set_hidden_in_game(True)

            actor.set_actor_label(f"NetClaw_Label_{label_name}")
            actor.tags.append("NetClawLabel")

            return actor.get_actor_label()

        return ""
