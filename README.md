# FreeCAD Webots Exporter Addon

An addon for FreeCAD 1.0+ to export native assemblies into Webots simulation files (`.wbt` / `.proto`). It preserves kinematic tree hierarchies, transforms, shapes, and materials, and supports auto-generating simulation-ready controller stubs for various automation and robotic protocols.

## Features

- **Assembly-to-World/Proto Export**: Converts FreeCAD assemblies and sub-assemblies into physical Webots nodes.
- **Spatial Transforms**: Preserves relative translation and rotation between parts, aligns axes, and converts scale from millimeters to meters.
- **Visual & Collision Geometry**: Exports shapes to OBJ format, decimes meshes based on configurable deflection/quality settings, and generates optimized primitive or convex-hull bounds.
- **Multi-Material Support**: Retains diffuse colors, transparencies, and textures utilizing MTL files.
- **Controller Protocol Export**: Generates functional Python controller stubs mapping assembly joints to interfaces.

## Supported Protocols

| Protocol | Output Files | Dependencies | Default Connection / Settings |
|---|---|---|---|
| **TCP Socket** | `<robot>_ctrl.py` | None | `127.0.0.1:5005` (JSON commands & telemetry) |
| **ROS 2** | `<robot>_ctrl.py`, `<robot>.urdf` | `rclpy` | Subscribes to `/<robot>/joint_commands` (`sensor_msgs/JointState`) and individual `/<robot>/command/<joint>` (`std_msgs/Float64`) topics. Publishes `/robot_description` parameter/topic and `/<robot>/joint_states` (`sensor_msgs/JointState`). |
| **Modbus TCP** | `<robot>_ctrl.py`, `register_map.md` | `pymodbus` | `0.0.0.0:502` / User-space port. Target positions mapped to Holding Registers (4xxxx), telemetry to Input Registers (3xxxx), scaled by 1000. |
| **OPC UA** | `<robot>_ctrl.py`, `mapping.csv` | `asyncua` | `opc.tcp://127.0.0.1:4840`. Subscribes to node IDs mapped in `mapping.csv`. |
| **Python GUI** | `<robot>_ctrl.py`, `gui_jogger.py` | None | Tkinter-based interactive jogging slider/button panel communicating over TCP. |

## Installation

1. Copy this repository directory (or symlink it) to your FreeCAD Addon directory:
   - Linux: `~/.local/share/FreeCAD/Mod/` or inside your Flatpak FreeCAD sandbox directory.
2. Restart FreeCAD.
3. Open the **Webots Exporter** workbench or use the workbench toolbar to configure your export.

## License

This project is licensed under the [MIT License](LICENSE).
