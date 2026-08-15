# FreeCAD Webots Exporter Addon

![ProtoExporter Showcase](Assests/bar_img.png)

https://github.com/user-attachments/assets/f6b0dc60-91cf-4dbd-b89a-c01e08f89751

The FreeCAD Webots Exporter is a professional engineering integration tool designed to bridge the gap between computer-aided design (CAD) in FreeCAD 1.0+ and robot simulation in Webots. It automates the transition of native assembly models into fully-articulated, simulation-ready Webots PROTO nodes, preserving complex kinematics, physical properties, high-fidelity materials, and peripheral sensor configurations.

By automating kinematics extraction, mesh optimization, volumetric collision fitting, and communication interface generation, this tool eliminates manual rebuilding of CAD assemblies in simulation editors, reducing model setup times from days to minutes.

---

## Video Demonstrations

| Feature / Protocol | Video Demo |
|---|---|
| **Export Workflow Guide** | https://github.com/user-attachments/assets/f6b0dc60-91cf-4dbd-b89a-c01e08f89751 |
| **ROS 2 Interface & Telemetry** | https://github.com/user-attachments/assets/784dbd23-2d8d-4cf9-8bbe-b35decb3a7dd |
| **OPC UA Server Control** | https://github.com/user-attachments/assets/5781dd5f-61a0-4b1f-96fc-ad4bbb260412 |
| **Python GUI Jogger** | https://github.com/user-attachments/assets/a3d65469-924f-4079-956c-a306f444912b |
| **TCP Socket Stream** | https://github.com/user-attachments/assets/0ccaafbd-bec5-425b-9f61-f2e2cc21fb76 |

---

## Core Capabilities

- **Assembly-to-PROTO Translation**: Converts hierarchical FreeCAD assemblies and sub-assemblies into native Webots `Solid` and `Joint` PROTO structures.
- **Hierarchical Kinematics Introspection**: Automatically constructs Webots joint trees from FreeCAD constraints, resolving complex parent-child links, rotational/translational limits, and world-space anchor points.
- **Fixed-Joint Subtree Contraction**: Automatically merges fixed-joint subgraphs using Union-Find topology analysis to optimize physics performance and solver stability.
- **Sensor and Peripheral Mapping**: Automatically detects and maps peripheral parts prefixed with `camera_`, `lidar_`, `gps_`, or `imu_` into native Webots sensors (`Camera`, `Lidar`, `GPS`, `InertialUnit`), injecting standard parameters (resolution, FOV, range, etc.) directly into the PROTO file.
- **Intelligent Mesh Processing & Collision Fitting**: Exports visual shapes to OBJ/MTL formats, applies configurable decimation (1%–100%) to optimize mesh complexity, and constructs corresponding bounding volumes (primitives or `scipy`-calculated convex hulls) for physical collisions.
- **Multi-Material Fidelity**: Preserves original CAD appearance details, including face-by-face diffuse colors, transparencies, and texture references directly into Webots appearance definitions.
- **Automated Controller Interfaces**: Generates self-contained Python controller stubs for instant connection to standard middleware and automation systems, streaming both joint states and peripheral sensor telemetry.

---

## Supported Controller Protocols

For downstream control, the exporter generates ready-to-run controller stubs alongside the PROTO definition:

| Protocol | Generated Assets | Demo Video | Dependencies | Description |
|---|---|---|---|---|
| **TCP Socket** | `<robot>_ctrl.py` | [Watch Demo](https://github.com/user-attachments/assets/0ccaafbd-bec5-425b-9f61-f2e2cc21fb76) | None | Low-latency JSON-based command and telemetry stream over TCP, publishing joint states and serialized peripheral readings (GPS/IMU arrays, high-bandwidth status flags). |
| **ROS 2** | `<robot>_ctrl.py`, `<robot>.urdf` | [Watch Demo](https://github.com/user-attachments/assets/784dbd23-2d8d-4cf9-8bbe-b35decb3a7dd) | `rclpy` | Automatically publishes dynamic `robot_description` and `joint_states` telemetry. Subscribes to standard command topics, and publishes active peripheral sensors to native ROS 2 topics (`sensor_msgs/Image`, `sensor_msgs/LaserScan`, `geometry_msgs/PointStamped`, `sensor_msgs/Imu`). |
| **Modbus TCP** | `<robot>_ctrl.py`, `register_map.md` | — | `pymodbus` | Direct mapping of joint states and peripheral telemetry to Modbus Input Registers (3xxxx) and targets to Holding Registers (4xxxx) for industrial PLC integration. |
| **OPC UA** | `<robot>_ctrl.py`, `mapping.csv` | [Watch Demo](https://github.com/user-attachments/assets/5781dd5f-61a0-4b1f-96fc-ad4bbb260412) | `asyncua` | Server-client OPC UA variable mapping to monitor/control joints and read peripheral telemetry directly from industrial SCADA systems. |
| **Python GUI** | `<robot>_ctrl.py`, `gui_jogger.py` | [Watch Demo](https://github.com/user-attachments/assets/a3d65469-924f-4079-956c-a306f444912b) | None | Lightweight Tkinter dashboard to manually jog joint positions and monitor joint and peripheral telemetry in real-time. |

---

## Installation

1. Copy or symlink this directory into your FreeCAD Mod directory:
   - **Linux**: `~/.local/share/FreeCAD/Mod/`
   - **Windows**: `%APPDATA%\FreeCAD\Mod\`
   - **macOS**: `~/Library/Application Support/FreeCAD/Mod/`
2. Restart FreeCAD.
3. Access the workbench via the Workbench Selector (**Webots Exporter**) and click **Export to Webots**.

---

## Usage Guide

For complete documentation on installation, GUI parameters, collision strategies, joint actuation settings, and protocol configurations, check out the [Official Wiki Manual](WIKI_MANUAL.md).

---

## License

This software is released under the MIT License. Refer to the [LICENSE](LICENSE) file for details.


