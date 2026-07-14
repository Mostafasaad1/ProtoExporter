import os
from pathlib import Path
from webots_exporter.datamodel import ProtocolConfig
from webots_exporter.protocols.base import BaseProtocolWriter

class ROS2ProtocolWriter(BaseProtocolWriter):
    def write(self, export_dir: str, robot_name: str, joints: list[str], config: ProtocolConfig) -> None:
        controller_dir = Path(export_dir) / "controllers" / f"{robot_name}_ctrl"
        controller_dir.mkdir(parents=True, exist_ok=True)
        
        # Write controller file
        controller_path = controller_dir / f"{robot_name}_ctrl.py"
        joints_repr = repr(joints)
        
        controller_code = f"""import sys
import time
try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Float64, String
    from sensor_msgs.msg import JointState
    from rclpy.qos import QoSProfile, DurabilityPolicy
except ImportError:
    print("Error: rclpy or standard ROS 2 message packages not found.")
    print("Please make sure you have sourced your ROS 2 installation and rclpy is available.")
    sys.exit(1)

from controller import Robot, Motor

class WebotsRos2Controller(Node):
    def __init__(self, robot, motors, sensors, joint_names):
        super().__init__('webots_ros2_controller')
        self.robot = robot
        self.motors = motors
        self.sensors = sensors
        self.joint_names = joint_names
        
        # Load local URDF file
        import os
        urdf_content = ""
        urdf_path = os.path.join(os.path.dirname(__file__), f"{{robot.getName()}}.urdf")
        if os.path.exists(urdf_path):
            try:
                with open(urdf_path, 'r', encoding='utf-8') as f:
                    urdf_content = f.read()
            except Exception as e:
                self.get_logger().error(f"Failed to read URDF: {{e}}")
                
        if urdf_content:
            self.declare_parameter('robot_description', urdf_content)
            qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
            self.urdf_pub = self.create_publisher(String, 'robot_description', qos)
            urdf_msg = String()
            urdf_msg.data = urdf_content
            self.urdf_pub.publish(urdf_msg)
            self.get_logger().info("Published a dummy URDF-Like description on topic /robot_description")
            
        # FR-008: Publish JointState telemetry
        self.joint_state_pub = self.create_publisher(JointState, f'/{{robot.getName()}}/joint_states', 10)
        
        # Subscriptions for commands
        self.subs = {{}}
        for name in motors.keys():
            topic = f'/{{robot.getName()}}/command/{{name}}'
            # Bind the joint name via default argument
            self.subs[name] = self.create_subscription(
                Float64,
                topic,
                self._make_cmd_callback(name),
                10
            )
            self.get_logger().info(f"Subscribed to command topic: {{topic}}")
            
        # Global joint commands topic carrying names and positions
        self.global_sub = self.create_subscription(
            JointState,
            f'/{{robot.getName()}}/joint_commands',
            self.global_command_callback,
            10
        )
        
    def _make_cmd_callback(self, joint_name):
        return lambda msg: self.command_callback(joint_name, msg)
        
    def command_callback(self, joint_name, msg):
        if joint_name not in self.motors:
            # FR-014: Fatal error if joint is unknown
            err_msg = f"Fatal Error: Unknown joint '{{joint_name}}' commanded via topic."
            self.get_logger().fatal(err_msg)
            rclpy.shutdown()
            raise ValueError(err_msg)
        self.motors[joint_name].setPosition(msg.data)
        
    def global_command_callback(self, msg):
        for name, pos in zip(msg.name, msg.position):
            if name not in self.motors:
                # FR-014: Fatal error if joint is unknown
                err_msg = f"Fatal Error: Unknown joint '{{name}}' commanded via global topic."
                self.get_logger().fatal(err_msg)
                rclpy.shutdown()
                raise ValueError(err_msg)
            self.motors[name].setPosition(pos)

    def publish_telemetry(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        names = []
        positions = []
        for name, sensor in self.sensors.items():
            names.append(name)
            positions.append(sensor.getValue())
            
        msg.name = names
        msg.position = positions
        self.joint_state_pub.publish(msg)

def main():
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())
    
    # Initialize rclpy
    rclpy.init(args=None)
    
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
            
    node = WebotsRos2Controller(robot, motors, sensors, joint_names)
    
    POLLING_RATE_MS = 500
    last_publish_time = 0
    
    while robot.step(timestep) != -1:
        # Spin ROS 2 callbacks non-blocking
        rclpy.spin_once(node, timeout_sec=0.0)
        
        # Publish telemetry
        current_time_ms = int(time.time() * 1000)
        if current_time_ms - last_publish_time >= POLLING_RATE_MS:
            node.publish_telemetry()
            last_publish_time = current_time_ms
            
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
"""
        controller_path.write_text(controller_code, encoding="utf-8")
        
        # Write dummy URDF file
        urdf_path = controller_dir / f"{robot_name}.urdf"
        urdf_lines = [
            '<?xml version="1.0"?>',
            f'<robot name="{robot_name}">',
            '  <link name="base_link"/>'
        ]
        
        parent_link = "base_link"
        for idx, joint in enumerate(joints):
            child_link = f"link_{idx+1}"
            urdf_lines.append(f'  <link name="{child_link}"/>')
            urdf_lines.append(f'  <joint name="{joint}" type="revolute">')
            urdf_lines.append(f'    <parent link="{parent_link}"/>')
            urdf_lines.append(f'    <child link="{child_link}"/>')
            urdf_lines.append('    <limit lower="-3.14" upper="3.14" effort="10" velocity="1"/>')
            urdf_lines.append('  </joint>')
            parent_link = child_link
            
        urdf_lines.append('</robot>')
        urdf_path.write_text("\n".join(urdf_lines), encoding="utf-8")

    def get_dependency_notice(self, robot_name: str, controller_dir: str) -> str:
        return (
            "Requires ROS 2 and rclpy.\n\n"
            "To command the robot joints using the ROS 2 joint state publisher GUI, run the following single command in a sourced ROS 2 terminal while the Webots simulation is running:\n\n"
            f"     ros2 run joint_state_publisher_gui joint_state_publisher_gui --ros-args -p robot_description_node:=/webots_ros2_controller -r joint_states:=/{robot_name}/joint_commands"
        )
