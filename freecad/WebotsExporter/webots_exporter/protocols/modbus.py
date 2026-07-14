import os
from pathlib import Path
from webots_exporter.datamodel import ProtocolConfig
from webots_exporter.protocols.base import BaseProtocolWriter

class ModbusProtocolWriter(BaseProtocolWriter):
    def write(self, export_dir: str, robot_name: str, joints: list[str], config: ProtocolConfig) -> None:
        controller_dir = Path(export_dir) / "controllers" / f"{robot_name}_ctrl"
        controller_dir.mkdir(parents=True, exist_ok=True)
        
        ip = config.modbus_ip or "0.0.0.0"
        port = config.modbus_port or 502
        
        # Write controller file
        controller_path = controller_dir / f"{robot_name}_ctrl.py"
        joints_repr = repr(joints)
        
        controller_code = f"""import sys
import time
import threading

try:
    from pymodbus.server import StartTcpServer
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
except ImportError:
    print("Error: pymodbus package is not installed.")
    print("Please install it using: pip install pymodbus")
    sys.exit(1)

from controller import Robot, Motor

# FR-004: Polling rate in milliseconds
POLLING_RATE_MS = 500
IP = "{ip}"
PORT = {port}

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

motors_list = list(motors.keys())
motors_count = len(motors_list)

# Container for thread-safe error propagation
fatal_error_container = {{'error': None}}

class CustomHoldingRegisters(ModbusSequentialDataBlock):
    def setValues(self, address, values):
        offset = address - self.address
        for i, val in enumerate(values):
            reg_idx = offset + i
            if reg_idx >= motors_count:
                # FR-014: write to unknown/unmapped register
                err_msg = f"Fatal Error: Modbus command write to unmapped register address {{reg_idx}}."
                fatal_error_container['error'] = ValueError(err_msg)
        super().setValues(address, values)

def float_to_int16(val, scale=1000):
    scaled = int(round(val * scale))
    scaled = max(-32768, min(32767, scaled))
    if scaled < 0:
        scaled = 65536 + scaled
    return scaled

def int16_to_float(register_val, scale=1000):
    if register_val >= 32768:
        scaled = register_val - 65536
    else:
        scaled = register_val
    return float(scaled) / scale

# Setup Modbus server datastore
hr_block = CustomHoldingRegisters(0, [0] * 100)
ir_block = ModbusSequentialDataBlock(0, [0] * 100)

store = ModbusSlaveContext(
    hr=hr_block,
    ir=ir_block
)
context = ModbusServerContext(slaves=store, single=True)

def run_server():
    try:
        StartTcpServer(context=context, address=(IP, PORT))
    except Exception as e:
        print(f"Modbus server exception: {{e}}")
        fatal_error_container['error'] = e

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
print(f"[{{robot.getName()}}] Modbus TCP Server started on {{IP}}:{{PORT}}")

last_publish_time = 0
prev_holding_vals = [0] * motors_count

while robot.step(timestep) != -1:
    if fatal_error_container['error'] is not None:
        raise fatal_error_container['error']
        
    # Read holding registers (targets)
    holding_vals = store.getValues(3, 0, count=motors_count)
    for idx, val in enumerate(holding_vals):
        if val != prev_holding_vals[idx]:
            joint_name = motors_list[idx]
            target_pos = int16_to_float(val)
            motors[joint_name].setPosition(target_pos)
            prev_holding_vals[idx] = val
            
    # Publish telemetry to input registers
    current_time_ms = int(time.time() * 1000)
    if current_time_ms - last_publish_time >= POLLING_RATE_MS:
        telemetry_vals = []
        for name in joint_names:
            sensor = sensors.get(name)
            if sensor is not None:
                val = float_to_int16(sensor.getValue())
            else:
                val = 0
            telemetry_vals.append(val)
        store.setValues(4, 0, telemetry_vals)
        last_publish_time = current_time_ms
"""
        controller_path.write_text(controller_code, encoding="utf-8")
        
        # Generate register map markdown content
        holding_rows = []
        input_rows = []
        for idx, joint in enumerate(joints):
            holding_rows.append(f"| 4000{idx+1} | {idx} | {joint} | Target Position for {joint} |")
            input_rows.append(f"| 3000{idx+1} | {idx} | {joint} | Telemetry position for {joint} |")
            
        map_content = f"""# Modbus TCP Register Map - {robot_name}

All values are scaled by **1000** and stored as **Signed 16-bit Integers**.
To command a joint to `1.57` radians, write `1570` to the holding register.
To read a joint telemetry of `-0.5` radians, the input register will read `65036` (which is `-500` in signed 16-bit).

## Holding Registers (4xxxx) - Target Positions

| Register Address | Offset | Joint Name | Description |
|---|---|---|---|
{"\n".join(holding_rows)}

## Input Registers (3xxxx) - Telemetry (Sensors)

| Register Address | Offset | Joint Name | Description |
|---|---|---|---|
{"\n".join(input_rows)}
"""
        map_path = controller_dir / "register_map.md"
        map_path.write_text(map_content, encoding="utf-8")

    def get_dependency_notice(self, robot_name: str, controller_dir: str) -> str:
        return "pip install pymodbus"
