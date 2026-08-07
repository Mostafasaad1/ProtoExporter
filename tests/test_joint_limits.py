from unittest.mock import MagicMock
from pathlib import Path
from webots_exporter.joint_introspect import dump_joint_properties
from webots_exporter.datamodel import WbJointNode, JointType, ProtocolConfig
from webots_exporter.protocols.gui import GUIProtocolWriter
from webots_exporter.protocols.ros2 import ROS2ProtocolWriter
from webots_exporter.protocols.base import normalize_joint_info


def test_normalize_joint_info_formats():
    # String test
    info1 = normalize_joint_info("joint1")
    assert info1["name"] == "joint1"
    assert info1["min_stop"] == 0.0
    assert info1["max_stop"] == 0.0

    # Dict test
    info2 = normalize_joint_info({
        "name": "joint2",
        "joint_type": "Slider",
        "min_stop": -0.5,
        "max_stop": 0.5,
    })
    assert info2["name"] == "joint2"
    assert info2["joint_type"] == JointType.SLIDER
    assert info2["min_stop"] == -0.5
    assert info2["max_stop"] == 0.5

    # Object test
    node = WbJointNode(
        name="joint3",
        joint_type=JointType.HINGE,
        min_stop=-1.2,
        max_stop=1.2,
    )
    info3 = normalize_joint_info(node)
    assert info3["name"] == "joint3"
    assert info3["min_stop"] == -1.2
    assert info3["max_stop"] == 1.2


def test_dump_joint_properties_swaps_inverted_limits():
    fc_joint = MagicMock()
    fc_joint.Label = "revolute_joint"
    fc_joint.Type = "Revolute"
    fc_joint.EnableAngleMin = True
    fc_joint.EnableAngleMax = True
    # Inverted limits: min = 90 deg, max = -90 deg
    fc_joint.AngleMin = 90.0
    fc_joint.AngleMax = -90.0

    props = dump_joint_properties(fc_joint)
    # Normalized so min <= max
    assert props["min_stop_rot"] < props["max_stop_rot"]
    assert abs(props["min_stop_rot"] - (-1.570796)) < 1e-3
    assert abs(props["max_stop_rot"] - 1.570796) < 1e-3


def test_gui_protocol_writer_generates_parsed_limits(tmp_path):
    writer = GUIProtocolWriter()
    joints = [
        WbJointNode(name="shoulder", joint_type=JointType.HINGE, min_stop=-0.7854, max_stop=0.7854),
        WbJointNode(name="prism", joint_type=JointType.SLIDER, min_stop=-0.2, max_stop=0.2),
    ]
    config = ProtocolConfig()

    writer.write(str(tmp_path), "test_robot", joints, config)

    controller_dir = tmp_path / "controllers" / "test_robot_ctrl"
    gui_jogger_path = controller_dir / "gui_jogger.py"
    assert gui_jogger_path.exists()

    code = gui_jogger_path.read_text()
    assert "'name': 'shoulder'" in code
    assert "'min': -0.7854" in code
    assert "'max': 0.7854" in code
    assert "'unit': 'rad'" in code

    assert "'name': 'prism'" in code
    assert "'min': -0.2" in code
    assert "'max': 0.2" in code
    assert "'unit': 'm'" in code


def test_ros2_protocol_writer_generates_urdf_limits(tmp_path):
    writer = ROS2ProtocolWriter()
    joints = [
        WbJointNode(name="arm_joint", joint_type=JointType.HINGE, min_stop=-1.57, max_stop=1.57),
        WbJointNode(name="linear_joint", joint_type=JointType.SLIDER, min_stop=-0.05, max_stop=0.05),
    ]
    config = ProtocolConfig()

    writer.write(str(tmp_path), "test_robot", joints, config)

    controller_dir = tmp_path / "controllers" / "test_robot_ctrl"
    urdf_path = controller_dir / "test_robot.urdf"
    assert urdf_path.exists()

    urdf_text = urdf_path.read_text()
    assert '<joint name="arm_joint" type="revolute">' in urdf_text
    assert '<limit lower="-1.57" upper="1.57" effort="10" velocity="1"/>' in urdf_text

    assert '<joint name="linear_joint" type="prismatic">' in urdf_text
    assert '<limit lower="-0.05" upper="0.05" effort="10" velocity="1"/>' in urdf_text
