import os
from pathlib import Path
from webots_exporter.datamodel import ProtocolConfig
from webots_exporter.protocols.base import BaseProtocolWriter

class GUIProtocolWriter(BaseProtocolWriter):
    def write(self, export_dir: str, robot_name: str, joints: list[str], config: ProtocolConfig, peripherals: list[tuple[str, str]] = None) -> None:
        controller_dir = Path(export_dir) / "controllers" / f"{robot_name}_ctrl"
        controller_dir.mkdir(parents=True, exist_ok=True)
        
        # Write controller file
        controller_path = controller_dir / f"{robot_name}_ctrl.py"
        joints_repr = repr(joints)
        peripherals = peripherals or []
        peripherals_repr = repr(peripherals)
        
        controller_code = f"""import socket
import json
import subprocess
import sys
import time
from controller import Robot, Motor, GPS, InertialUnit, Camera, Lidar

# FR-004: Polling rate in milliseconds
POLLING_RATE_MS = 100
PORT = 5005

robot = Robot()
timestep = int(robot.getBasicTimeStep())

# List of known joints
motor_names = {joints_repr}
motors = {{}}
sensors = {{}}

for name in motor_names:
    motor_dev = robot.getDevice(f"{{name}}_motor")
    if motor_dev is not None:
        motors[name] = motor_dev
        motor_dev.setPosition(0.0)
    
    sensor_dev = robot.getDevice(f"{{name}}_sensor")
    if sensor_dev is not None:
        sensors[name] = sensor_dev
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

print(f"[{{robot.getName()}}] Bidirectional TCP Server listening on 127.0.0.1:{{PORT}}")

# Launch the Tkinter GUI subprocess
try:
    subprocess.Popen([sys.executable, 'gui_jogger.py'])
    print(f"[{{robot.getName()}}] Launched Tkinter GUI Jogger subprocess.")
except Exception as e:
    print(f"Error launching GUI Jogger subprocess: {{e}}")

client_conn = None
buffer = ""
last_publish_time = 0

def get_sensor_value(dev):
    if isinstance(dev, GPS):
        vals = dev.getValues()
        return [round(v, 4) for v in vals] if vals else None
    elif isinstance(dev, InertialUnit):
        vals = dev.getRollPitchYaw()
        return [round(v, 4) for v in vals] if vals else None
    elif isinstance(dev, Camera):
        return f"Camera ({{dev.getWidth()}}x{{dev.getHeight()}})"
    elif isinstance(dev, Lidar):
        return f"Lidar ({{dev.getNumberOfPoints()}} pts)"
    elif hasattr(dev, "getValue"):
        return round(dev.getValue(), 4)
    return None

while robot.step(timestep) != -1:
    # Accept client connection non-blocking
    if client_conn is None:
        try:
            client_conn, addr = server.accept()
            client_conn.setblocking(False)
            print(f"GUI connected from {{addr}}")
            buffer = ""
        except BlockingIOError:
            pass

    # Read incoming commands non-blocking
    if client_conn is not None:
        try:
            data = client_conn.recv(1024).decode('utf-8')
            if not data:
                print("GUI disconnected")
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
                                    msg = f"Fatal Error: Unknown joint '{{joint_name}}' in command '{{line}}' received from GUI."
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
            print(f"Error reading GUI socket: {{e}}")
            client_conn.close()
            client_conn = None

    # Write telemetry to client
    if client_conn is not None:
        try:
            current_time_ms = int(time.time() * 1000)
            if current_time_ms - last_publish_time >= POLLING_RATE_MS:
                telemetry_data = {{}}
                for name, sensor in sensors.items():
                    telemetry_data[name] = sensor.getValue()
                for name, sensor in peripheral_sensors.items():
                    telemetry_data[name] = get_sensor_value(sensor)
                client_conn.sendall((json.dumps(telemetry_data) + '\\n').encode('utf-8'))
                last_publish_time = current_time_ms
        except Exception as e:
            print(f"Error writing telemetry to GUI: {{e}}")
            client_conn.close()
            client_conn = None
"""
        controller_path.write_text(controller_code, encoding="utf-8")
        
        # Write gui_jogger.py file
        gui_path = controller_dir / "gui_jogger.py"
        gui_code = f"""import tkinter as tk
from tkinter import ttk
import socket
import json
import threading
import time
import sys

PORT = 5005
JOINTS = {joints_repr}
PERIPHERALS = {peripherals_repr}

class JoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Jogging Panel")
        self.root.geometry("550x550")
        
        # Connection status label
        self.status_lbl = tk.Label(root, text="Connecting to Webots...", fg="orange", font=("Arial", 12, "bold"))
        self.status_lbl.pack(pady=10)
        
        # Container frame
        self.frame = tk.Frame(root)
        self.frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        # Joints configuration section
        self.joints_lf = tk.LabelFrame(self.frame, text="Actuated Joints", font=("Arial", 10, "bold"), padx=10, pady=5)
        self.joints_lf.pack(fill=tk.BOTH, expand=True, pady=5)

        self.joint_widgets = {{}}
        for joint in JOINTS:
            lf = tk.Frame(self.joints_lf)
            lf.pack(fill=tk.X, pady=5)
            
            # Name
            name_lbl = tk.Label(lf, text=f"{{joint}}:", width=15, anchor="w", font=("Arial", 9, "bold"))
            name_lbl.pack(side=tk.LEFT)

            # Telemetry display
            val_lbl = tk.Label(lf, text="Current: 0.000 rad", width=18, anchor="w", font=("Courier", 10))
            val_lbl.pack(side=tk.LEFT)
            
            # Slider/Scale
            scale = tk.Scale(lf, from_=-3.14, to=3.14, resolution=0.01, orient=tk.HORIZONTAL,
                             command=lambda val, j=joint: self.on_slider_move(j, val))
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
            
            # Jog Buttons
            dec_btn = tk.Button(lf, text="-", width=3, command=lambda j=joint, s=scale: self.jog(j, s, -0.1))
            dec_btn.pack(side=tk.LEFT, padx=2)
            
            inc_btn = tk.Button(lf, text="+", width=3, command=lambda j=joint, s=scale: self.jog(j, s, 0.1))
            inc_btn.pack(side=tk.LEFT, padx=2)
            
            self.joint_widgets[joint] = {{"label": val_lbl, "scale": scale}}
            
        # Peripherals section
        self.peripheral_widgets = {{}}
        if PERIPHERALS:
            self.periph_lf = tk.LabelFrame(self.frame, text="Peripheral Sensors", font=("Arial", 10, "bold"), padx=10, pady=5)
            self.periph_lf.pack(fill=tk.BOTH, expand=True, pady=10)
            for name, stype in PERIPHERALS:
                row_f = tk.Frame(self.periph_lf)
                row_f.pack(fill=tk.X, pady=2)
                name_lbl = tk.Label(row_f, text=f"{{name}} ({{stype}}):", width=25, anchor="w", font=("Arial", 9, "bold"))
                name_lbl.pack(side=tk.LEFT)
                val_lbl = tk.Label(row_f, text="N/A", anchor="w", font=("Courier", 9))
                val_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.peripheral_widgets[name] = val_lbl

        self.socket = None
        self.connected = False
        
        # Network thread
        threading.Thread(target=self.network_loop, daemon=True).start()
        
    def on_slider_move(self, joint, value):
        if self.connected:
            self.send_command({{joint: float(value)}})
            
    def jog(self, joint, scale, delta):
        new_val = scale.get() + delta
        new_val = max(scale.cget("from"), min(scale.cget("to"), new_val))
        scale.set(new_val)
        self.on_slider_move(joint, new_val)
        
    def send_command(self, cmd):
        try:
            self.socket.sendall((json.dumps(cmd) + '\\n').encode('utf-8'))
        except Exception as e:
            print(f"Error sending command: {{e}}")
            
    def network_loop(self):
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('127.0.0.1', PORT))
                self.socket = s
                self.connected = True
                self.status_lbl.config(text="CONNECTED", fg="green")
                
                buffer = ""
                while True:
                    data = s.recv(1024).decode('utf-8')
                    if not data:
                        break
                    buffer += data
                    if '\\n' in buffer:
                        lines = buffer.split('\\n')
                        for line in lines[:-1]:
                            if not line.strip():
                                continue
                            try:
                                telemetry = json.loads(line)
                                self.root.after(0, self.update_ui, telemetry)
                            except json.JSONDecodeError:
                                pass
                        buffer = lines[-1]
            except Exception as e:
                self.connected = False
                self.status_lbl.config(text="Disconnected - Retrying...", fg="red")
                time.sleep(2)
                
    def update_ui(self, telemetry):
        for name, val in telemetry.items():
            if name in self.joint_widgets:
                self.joint_widgets[name]["label"].config(text=f"Current: {{float(val):.3f}} rad")
            elif name in self.peripheral_widgets:
                self.peripheral_widgets[name].config(text=str(val))

if __name__ == '__main__':
    root = tk.Tk()
    app = JoggerApp(root)
    root.mainloop()
"""
        gui_path.write_text(gui_code, encoding="utf-8")

    def get_dependency_notice(self, robot_name: str, controller_dir: str) -> str:
        return ""
