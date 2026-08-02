from pathlib import Path
from unittest.mock import MagicMock
import pytest

from webots_exporter.datamodel import WbSolidNode, WbJointNode, JointType
from webots_exporter.render import WbtRenderer
from webots_exporter.gui.task_panel import ExportOptions
from webots_exporter.exporter import WebotsExporter


def test_export_options_metadata_fields():
    opts = ExportOptions(
        output_dir="/tmp",
        custom_description="Custom test robot",
        doc_url="https://example.com/docs",
        license="MIT",
    )
    assert opts.custom_description == "Custom test robot"
    assert opts.doc_url == "https://example.com/docs"
    assert opts.license == "MIT"


def test_render_proto_metadata_headers():
    renderer = WbtRenderer()
    root_solid = WbSolidNode(name="Base")

    rendered = renderer.render_proto(
        proto_name="TestRobot",
        root_solid=root_solid,
        description="Line 1 of description\nLine 2 of description",
        doc_url="https://example.com/doc",
        license="Apache 2.0",
    )

    assert "# license: Apache 2.0" in rendered
    assert "# documentation url: https://example.com/doc" in rendered
    assert "# description: Line 1 of description" in rendered
    assert "# Line 2 of description" in rendered
    assert "PROTO TestRobot [" in rendered


def test_collect_tree_stats_and_proto_description(tmp_path):
    exporter = WebotsExporter(
        output_dir=tmp_path,
        world_name="test_robot",
        custom_description="A test robot model",
    )

    joint1 = WbJointNode(name="j1", actuated=True, sensed=True)
    joint2 = WbJointNode(name="j2", actuated=True, sensed=False)

    child_solid = WbSolidNode(name="Arm", child_joints=[joint2])
    joint1.child = child_solid

    root_solid = WbSolidNode(name="Base", child_joints=[joint1])

    num_joints, num_actuators, num_sensors = exporter._collect_tree_stats(root_solid)
    assert num_joints == 2
    assert num_actuators == 2
    assert num_sensors == 1

    desc = exporter._build_proto_description(root_solid)
    assert "A test robot model" in desc
    assert "Auto-generated PROTO model containing 2 joints, 2 actuators, 1 sensor, and 1 controller." in desc


def test_collect_tree_stats_omits_zero_counts(tmp_path):
    exporter = WebotsExporter(
        output_dir=tmp_path,
        world_name="passive_body",
    )

    root_solid = WbSolidNode(name="StaticBox")

    num_joints, num_actuators, num_sensors = exporter._collect_tree_stats(root_solid)
    assert num_joints == 0
    assert num_actuators == 0
    assert num_sensors == 0

    desc = exporter._build_proto_description(root_solid)
    assert desc == ""
