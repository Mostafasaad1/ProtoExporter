from typing import Any
from pathlib import Path
from webots_exporter.datamodel import ProtocolConfig
from webots_exporter.protocols.base import BaseProtocolWriter, normalize_joint_info

class TCPProtocolWriter(BaseProtocolWriter):
    def write(self, export_dir: str, robot_name: str, joints: list[Any], config: ProtocolConfig, peripherals: list[tuple[str, str]] = None) -> None:
        controller_dir = Path(export_dir) / "controllers" / f"{robot_name}_ctrl"
        controller_dir.mkdir(parents=True, exist_ok=True)
        
        normalized_joints = [normalize_joint_info(j) for j in joints]
        joint_names = [j["name"] for j in normalized_joints]
        joint_configs = [
            {
                "name": j["name"],
                "min": round(j["min_stop"], 4),
                "max": round(j["max_stop"], 4),
            }
            for j in normalized_joints
        ]
        
        # Write controller file
        controller_path = controller_dir / f"{robot_name}_ctrl.py"
        joints_repr = repr(joint_names)
        joint_configs_repr = repr(joint_configs)
        peripherals = peripherals or []
        peripherals_repr = repr(peripherals)
        
        controller_code = f"""import socket
import json
import time
from controller import Robot, Motor, GPS, InertialUnit, Camera, Lidar

# FR-004: Polling rate in milliseconds
POLLING_RATE_MS = 500
PORT = 5005

robot = Robot()
timestep = int(robot.getBasicTimeStep())

# List of known joints
motor_names = {joints_repr}
joint_configs = {joint_configs_repr}
motors = {{}}

for cfg in joint_configs:
    name = cfg["name"]
    min_val = cfg["min"]
    max_val = cfg["max"]
    init_pos = max(min_val, min(max_val, 0.0)) if (min_val != 0.0 or max_val != 0.0) else 0.0
    
    device_name = f"{{name}}_motor"
    dev = robot.getDevice(device_name)
    if dev is None:
        print(f"Warning: device {{device_name}} not found")
    else:
        motors[name] = dev
        dev.setPosition(init_pos)


# Initialize joint sensors
joint_sensors = {{}}
for name in motor_names:
    sensor_dev = robot.getDevice(f"{{name}}_sensor")
    if sensor_dev is not None:
        joint_sensors[name] = sensor_dev
        sensor_dev.enable(timestep)

# Initialize peripheral sensors
peripheral_data = {peripherals_repr}
peripheral_sensors = {{}}
for name, sensor_type in peripheral_data:
    dev = robot.getDevice(name)
    if dev is not None:
        peripheral_sensors[name] = dev
        dev.enable(timestep)

# Setup non-blocking server socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', PORT))
server.listen(1)
server.setblocking(False)

print(f"[{{robot.getName()}}] TCP Server listening on 127.0.0.1:{{PORT}}")

client_conn = None
buffer = ""
last_publish_time = 0

def get_sensor_value(dev):
    if isinstance(dev, GPS):
        return dev.getValues()
    elif isinstance(dev, InertialUnit):
        return dev.getRollPitchYaw()
    elif isinstance(dev, Camera):
        return f"Camera image (width: {{dev.getWidth()}}, height: {{dev.getHeight()}})"
    elif isinstance(dev, Lidar):
        return f"Lidar range data ({{dev.getNumberOfPoints()}} points)"
    elif hasattr(dev, "getValue"):
        return dev.getValue()
    return None

while robot.step(timestep) != -1:
    # Accept client connection non-blocking
    if client_conn is None:
        try:
            client_conn, addr = server.accept()
            client_conn.setblocking(False)
            print(f"Client connected from {{addr}}")
            buffer = ""
        except BlockingIOError:
            pass

    # Read incoming commands non-blocking
    if client_conn is not None:
        try:
            data = client_conn.recv(1024).decode('utf-8')
            if not data:
                print("Client disconnected")
                client_conn.close()
                client_conn = None
            else:
                buffer += data
                if '\\n' in buffer:
                    lines = buffer.split('\\n')
                    for line in lines[:-1]:
                        if not line.strip():
                            continue
                        try:
                            cmd = json.loads(line)
                            for joint_name, pos in cmd.items():
                                # FR-014: raise fatal error and halt if joint name is unrecognized
                                if joint_name not in motor_names:
                                    msg = f"Fatal Error: Unknown joint '{{joint_name}}' in command '{{line}}' received from TCP Client."
                                    print(msg)
                                    raise ValueError(msg)
                                if joint_name in motors:
                                    motors[joint_name].setPosition(float(pos))
                        except json.JSONDecodeError:
                            pass
                    buffer = lines[-1]
        except BlockingIOError:
            pass
        except Exception as e:
            if isinstance(e, ValueError) and "Fatal Error" in str(e):
                raise e
            print(f"Error reading client socket: {{e}}")
            client_conn.close()
            client_conn = None

    # Write telemetry to client (joint sensors and peripheral sensors)
    if client_conn is not None:
        try:
            current_time_ms = int(time.time() * 1000)
            if current_time_ms - last_publish_time >= POLLING_RATE_MS:
                telemetry_data = {{}}
                for name, sensor in joint_sensors.items():
                    telemetry_data[name] = get_sensor_value(sensor)
                for name, sensor in peripheral_sensors.items():
                    telemetry_data[name] = get_sensor_value(sensor)
                client_conn.sendall((json.dumps(telemetry_data) + '\\n').encode('utf-8'))
                last_publish_time = current_time_ms
        except Exception as e:
            print(f"Error writing telemetry to client: {{e}}")
            client_conn.close()
            client_conn = None
"""
        controller_path.write_text(controller_code, encoding="utf-8")
        
        # Write client example file
        client_path = controller_dir / "client_example.py"
        client_code = f"""import socket
import json
import time

PORT = 5005
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('127.0.0.1', PORT))
    print("Connected to robot controller.")
    
    # Command joints to 0.5 rad
    cmd1 = {{joint: 0.5 for joint in {joints_repr}}}
    print(f"Sending: {{cmd1}}")
    s.sendall((json.dumps(cmd1) + '\\n').encode('utf-8'))
    
    # Listen to a few lines of telemetry
    for _ in range(5):
        data = s.recv(1024).decode('utf-8')
        if data:
            print("Received telemetry:", data.strip())
        time.sleep(0.5)
    
    # Command joints back to 0.0 rad
    cmd2 = {{joint: 0.0 for joint in {joints_repr}}}
    print(f"Sending: {{cmd2}}")
    s.sendall((json.dumps(cmd2) + '\\n').encode('utf-8'))
    
except Exception as e:
    print(f"Connection error: {{e}}")
finally:
    s.close()
"""
        client_path.write_text(client_code, encoding="utf-8")

    def get_dependency_notice(self, robot_name: str, controller_dir: str) -> str:
        return ""
