# FreeCAD to Webots Exporter - Official Manual

Welcome to the comprehensive guide for the **FreeCAD Webots Exporter**. This addon is a professional engineering integration tool designed to bridge the gap between computer-aided design (CAD) in FreeCAD and robot simulation in Webots. 

This guide will walk you through installation, basic usage, and provide a deep dive into every feature—especially the powerful communication and controller protocols.

---

## Table of Contents
1. [Installation](#1-installation)
2. [Launching the Exporter](#2-launching-the-exporter)
3. [General Settings](#3-general-settings)
   - [Output Directory](#output-directory)
   - [Collision Strategy](#collision-strategy)
   - [Mesh Visual Quality](#mesh-visual-quality)
4. [Joint Motors & Sensors Configuration](#4-joint-motors--sensors-configuration)
5. [Communication Interfaces (Controller Protocols)](#5-communication-interfaces-controller-protocols)
   - [TCP Socket](#tcp-socket)
   - [ROS 2](#ros-2)
   - [Modbus TCP](#modbus-tcp)
   - [OPC UA Client](#opc-ua-client)
   - [Python GUI](#python-gui)
6. [Executing the Export & Next Steps](#6-executing-the-export--next-steps)

---

## 1. Installation

1. Clone or download this repository.
2. Copy or symlink the `freecad-webots-exporter` directory into your FreeCAD Mod directory:
   - **Linux**: `~/.local/share/FreeCAD/Mod/`
   - **Windows**: `%APPDATA%\FreeCAD\Mod\`
   - **macOS**: `~/Library/Application Support/FreeCAD/Mod/`
3. Restart FreeCAD.

## 2. Launching the Exporter

1. Open your FreeCAD project containing the fully constrained Assembly you wish to export.
2. In the FreeCAD Workbench drop-down menu (usually at the top), select **Webots Exporter**.
3. Click the **Export to Webots** button on the toolbar to open the Exporter Task Panel.

> **Note:** The exporter will automatically detect your assembly. If multiple assemblies exist, ensure you have the desired one selected in the Tree View before launching the task panel.

---

## 3. General Settings

The top section of the Task Panel provides essential settings for the physical and visual representation of your robot in Webots.

### Output Directory
Select the destination folder where the Webots project files will be generated. The exporter will automatically create a sub-folder named after your FreeCAD Assembly (e.g., `my_robot_assembly/`). This folder will contain the `protos/`, `controllers/`, and generated metadata.

### Collision Strategy
This setting determines how the physical collision boundaries are calculated for Webots. Complex CAD meshes cause severe lag in physics simulations if used directly for collisions.
- **Auto**: (Recommended) The plugin will attempt to find the best fit, falling back to bounding boxes or simplified shapes if needed.
- **Primitives Only**: Replaces shapes with the closest fitting basic geometries (Cylinders, Boxes, Spheres). This yields the highest physics performance.
- **Decimated Mesh Only**: Uses heavily simplified versions of your visual meshes for collisions.
- **Convex Hull**: Wraps your complex shapes in a tight convex boundary. Excellent for complex links that need accurate, yet performant, collision detection.

### Mesh Visual Quality
A slider (1% to 100%) that controls the decimation level of the visual OBJ meshes. 
- Lowering this value reduces file size and improves rendering performance in Webots.
- 50% is generally a good balance of retaining CAD fidelity while optimizing the polygon count.

---

## 4. Joint Motors & Sensors Configuration

Before configuring communication, you must define which joints in your FreeCAD assembly are active components. The plugin automatically lists all recognized FreeCAD joints in a table.

- **Actuated Checkbox**: Marks the joint as a Motor in Webots. It will be able to receive position, velocity, or torque commands.
- **Sensed Checkbox**: Marks the joint as a Position Sensor in Webots. It will broadcast its current state (angle/position).
- **Helper Buttons**: Use **Select All Actuators** and **Select All Sensors** for quick bulk selection.

### Sensor and Peripheral Mapping
Beyond kinematics joints, the exporter automatically scans the assembly hierarchy for peripheral sensor parts based on naming prefixes (case-insensitive):
- **Camera** (parts prefixed with `camera_`): Mapped to a native Webots `Camera` node. The exporter automatically generates visual field-of-view (`fieldOfView 1.047`), and default image dimensions (`width 640`, `height 480`) directly into the `.proto` file.
- **Lidar** (parts prefixed with `lidar_`): Mapped to a native Webots `Lidar` node. The exporter automatically sets standard configuration fields including `horizontalResolution 512`, `fieldOfView 6.28`, `verticalFieldOfView 0.2`, and `numberOfLayers 16`.
- **GPS** (parts prefixed with `gps_`): Mapped to a Webots case-sensitive `GPS` node.
- **InertialUnit** (parts prefixed with `imu_`): Mapped to a Webots `InertialUnit` node.

These peripherals are traversed during kinematically structured tree compilation and passed to the generated python controller files.

---

## 5. Communication Interfaces (Controller Protocols)

This is the most powerful feature of the exporter. Rather than forcing you to write Webots Python controllers from scratch, the exporter can automatically generate fully-functional, protocol-aware controller stubs. 

Select a protocol from the **Controller Protocol** dropdown menu. Depending on your choice, dynamic configuration fields will appear, and specific assets will be exported.

### TCP Socket
**Best for**: Custom lightweight integrations, remote AI training, and minimal-dependency workflows.
- **How it works**: Generates a Python controller (`<robot>_ctrl.py`) that opens a TCP socket server. External programs can connect to this socket to send JSON commands (setting motor positions) and read JSON telemetry.
- **Sensor Telemetry**: Telemetry packets streamed at `POLLING_RATE_MS` contain joint sensor states alongside serialized peripheral readings:
  - `GPS`: Serialized as a 3-element float array `[x, y, z]`.
  - `InertialUnit`: Serialized as a 3-element float array `[roll, pitch, yaw]`.
  - `Camera` / `Lidar`: Transmitted as string status indicators (e.g. `"active"` or `"disabled"`) to conserve socket bandwidth.
- **Generated Assets**: `<robot>_ctrl.py`
- **Dependencies**: None.

### ROS 2
**Best for**: Advanced robotics research, MoveIt! integration, and autonomous navigation.
- **How it works**: Generates a controller node that natively bridges Webots into the ROS 2 ecosystem. It automatically publishes the `robot_description` and `joint_states` telemetry. It listens to standard ROS 2 command topics to drive the simulation.
- **Sensor Telemetry**: In addition to publishing `/robot_name/joint_states`, it declares specific publishers and publishes real-time sensor data over the following topics:
  - **Camera**: Published on `/robot_name/sensor_name/image` using `sensor_msgs/msg/Image` (raw `bgra8` format).
  - **Lidar**: Published on `/robot_name/sensor_name/laser_scan` using `sensor_msgs/msg/LaserScan`.
  - **GPS**: Published on `/robot_name/sensor_name/point` using `geometry_msgs/msg/PointStamped`.
  - **InertialUnit (IMU)**: Published on `/robot_name/sensor_name/imu` using `sensor_msgs/msg/Imu` (with populated orientation quaternions).
- **Generated Assets**: `<robot>_ctrl.py`, `<robot>.urdf` (Auto-generated URDF for ROS tools).
- **Dependencies**: `rclpy` (Requires ROS 2 environment sourced before running Webots).

### Modbus TCP
**Best for**: Industrial automation, PLC programming, and factory floor digital twins.
- **How it works**: Hosts a Modbus TCP server directly inside the Webots simulation. Webots joint sensors are mapped to Modbus Input Registers (3xxxx), and motor targets are mapped to Holding Registers (4xxxx).
- **Sensor Telemetry**: Peripheral sensors are mapped dynamically to Input Registers starting immediately after the joint sensors:
  - `GPS` / `InertialUnit`: Each allocates 3 consecutive 16-bit registers mapping X/Y/Z or Roll/Pitch/Yaw values (converted to signed integers with precision scaling).
  - `Camera` / `Lidar`: Maps to 1 register acting as an active status flag.
  - Scalar sensors: Map to 1 register.
- **Configuration Fields**: 
  - **Modbus Bind IP**: Typically `0.0.0.0` to allow external PLC connections, or `127.0.0.1` for local testing.
  - **Modbus Bind Port**: Default is `502` (Note: Ports below 1024 may require administrator/sudo privileges).
- **Generated Assets**: `<robot>_ctrl.py`, `register_map.md` (A document detailing exactly which registers correspond to which joints and peripheral sensors).
- **Dependencies**: `pymodbus` (`pip install pymodbus`).

### OPC UA Client
**Best for**: Enterprise SCADA systems, Industry 4.0 applications, and large-scale IoT networks.
- **How it works**: The Webots controller acts as an OPC UA Client that connects to an external OPC UA Server. It writes joint/sensor data to specific server nodes and reads command data from target nodes.
- **Sensor Telemetry**: The generated `mapping.csv` defines both command inputs and telemetry mappings (for both joints and active peripheral sensors) to corresponding node IDs on the OPC UA server. Telemetry is written asynchronously at the polling rate.
- **Configuration Fields**:
  - **OPC UA Server URI**: The address of your target server (e.g., `opc.tcp://127.0.0.1:4840`).
  - **OPC UA CSV Node Map**: A required CSV file that maps your FreeCAD joint names to the specific Node IDs on your OPC UA Server. 
    - *CSV Format*: `NodeID, JointName` (e.g., `ns=2;i=2, Base_Joint`). The GUI will validate this file against your current assembly joints and warn you of any mismatches.
- **Generated Assets**: `<robot>_ctrl.py`, `mapping.csv` (Copied for reference).
- **Dependencies**: `asyncua` (`pip install asyncua`).

### Python GUI
**Best for**: Quick prototyping, manual debugging, and kinematic testing without external code.
- **How it works**: Generates a secondary Python script that opens a lightweight Tkinter window containing sliders for every actuated joint, and readouts for every sensed joint.
- **Sensor Telemetry**: Renders a dedicated "Peripheral Sensors" panel at the bottom of the jogging dashboard showing real-time readouts (coordinates, orientations, or status strings) for all active peripherals.
- **Generated Assets**: `<robot>_ctrl.py`, `gui_jogger.py`
- **Dependencies**: None.
- **Usage**: Once the simulation is running, execute `python gui_jogger.py` from a terminal to manually drive the robot.

---

## 6. Executing the Export & Next Steps

Once all settings are configured:
1. Click **OK** at the bottom of the Task Panel.
2. The exporter will process the kinematics, decimate the meshes, compute the collisions, and write the protocols.
3. A success dialog will appear, listing the output path and reminding you of any Python dependencies (like `pymodbus` or `asyncua`) required to run your generated controller.

### Using the Exported Files in Webots
1. Open Webots.
2. Go to **File -> Open World** and navigate to your `output_dir`. (Or create a new world).
3. Click the **Add Node (+)** button, go to **PROTO nodes (Current Project)**, and select your newly exported robot.
4. Ensure the `controller` field of the robot node is set to the generated `<robot>_ctrl` script.
5. Hit **Play** in Webots, and launch your respective external client (ROS 2, PLC, or custom script) to take control!
