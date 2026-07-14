import shutil
from pathlib import Path
from webots_exporter.datamodel import ProtocolConfig
from webots_exporter.protocols.base import BaseProtocolWriter

class OPCUAProtocolWriter(BaseProtocolWriter):
    def write(self, export_dir: str, robot_name: str, joints: list[str], config: ProtocolConfig) -> None:
        controller_dir = Path(export_dir) / "controllers" / f"{robot_name}_ctrl"
        controller_dir.mkdir(parents=True, exist_ok=True)
        
        server_url = config.opcua_server or "opc.tcp://127.0.0.1:4840"
        
        # Copy or generate CSV mapping file
        dest_csv_path = controller_dir / "mapping.csv"
        if config.opcua_csv_path:
            src_path = Path(config.opcua_csv_path)
            if src_path.exists() and src_path.is_file():
                shutil.copy(src_path, dest_csv_path)
            else:
                self._generate_default_csv(dest_csv_path, joints)
        else:
            self._generate_default_csv(dest_csv_path, joints)
            
        # Write controller file
        controller_path = controller_dir / f"{robot_name}_ctrl.py"
        joints_repr = repr(joints)
        
        controller_code = f"""import sys
import os
import csv
import asyncio
import threading
import time

try:
    from asyncua import Client
except ImportError:
    print("Error: asyncua package is not installed.")
    print("Please install it using: pip install asyncua")
    sys.exit(1)

from controller import Robot, Motor

SERVER_URL = "{server_url}"
CSV_PATH = "mapping.csv"
POLLING_RATE_MS = 500

robot = Robot()
timestep = int(robot.getBasicTimeStep())

# Get devices
joint_names = {joints_repr}
motors = {{}}
sensors = {{}}

for name in joint_names:
    motor_dev = robot.getDevice(f"{{name}}_motor")
    if motor_dev is not None:
        motors[name] = motor_dev
        motor_dev.setPosition(0.0)
    
    sensor_dev = robot.getDevice(f"{{name}}_sensor")
    if sensor_dev is not None:
        sensors[name] = sensor_dev
        sensor_dev.enable(timestep)

# Load CSV mappings
joint_to_node = {{}}
if os.path.exists(CSV_PATH):
    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header and len(header) >= 2:
            if "joint" not in header[0].lower() and "node" not in header[1].lower():
                # Process the header row itself if it is not a descriptor
                joint_name, node_id = header[0].strip(), header[1].strip()
                if joint_name in motors:
                    joint_to_node[joint_name] = node_id
                else:
                    # FR-010: Gracefully skip unknown rows
                    print(f"Warning: CSV contains mapping for unknown joint '{{joint_name}}'. Skipping.")
            
            for row in reader:
                if len(row) < 2:
                    continue
                joint_name, node_id = row[0].strip(), row[1].strip()
                if joint_name in motors:
                    joint_to_node[joint_name] = node_id
                else:
                    # FR-010: Gracefully skip unknown rows
                    print(f"Warning: CSV contains mapping for unknown joint '{{joint_name}}'. Skipping.")
else:
    print(f"Warning: OPC UA mapping file {{CSV_PATH}} not found.")

# Store for target positions
targets = {{name: 0.0 for name in motors.keys()}}
targets_lock = threading.Lock()

class SubscriptionHandler:
    def __init__(self, joint_name):
        self.joint_name = joint_name
        
    def datachange_notification(self, node, val, data):
        with targets_lock:
            targets[self.joint_name] = float(val)

async def opcua_client_loop():
    while True:
        try:
            print(f"Connecting to OPC UA Server at {{SERVER_URL}}...")
            async with Client(url=SERVER_URL) as client:
                print("Connected to OPC UA Server.")
                for joint_name, node_id in joint_to_node.items():
                    try:
                        node = client.get_node(node_id)
                        sub = await client.create_subscription(500, SubscriptionHandler(joint_name))
                        await sub.subscribe_data_change(node)
                        print(f"Subscribed joint '{{joint_name}}' to OPC UA Node '{{node_id}}'")
                    except Exception as e:
                        print(f"Error subscribing joint '{{joint_name}}' to Node '{{node_id}}': {{e}}")
                
                while True:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"OPC UA client connection error: {{e}}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(opcua_client_loop())

client_thread = threading.Thread(target=start_async_loop, daemon=True)
client_thread.start()

while robot.step(timestep) != -1:
    with targets_lock:
        for name, pos in targets.items():
            if name in motors:
                motors[name].setPosition(pos)
"""
        controller_path.write_text(controller_code, encoding="utf-8")

    def _generate_default_csv(self, dest_path: Path, joints: list[str]) -> None:
        lines = ["joint_name,node_id"]
        for joint in joints:
            lines.append(f"{joint},ns=2;s={joint}_Target")
        dest_path.write_text("\n".join(lines), encoding="utf-8")

    def get_dependency_notice(self, robot_name: str, controller_dir: str) -> str:
        return "pip install asyncua"
