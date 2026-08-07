from abc import ABC, abstractmethod
from typing import Any, Union
from webots_exporter.datamodel import ProtocolConfig, JointType

def normalize_joint_info(j: Any) -> dict[str, Any]:
    """
    Normalizes joint representation into a standard dictionary containing:
    name, joint_type, min_stop, max_stop, min_stop_rot, max_stop_rot, min_stop_trans, max_stop_trans, actuated, sensed.
    """
    if isinstance(j, str):
        return {
            "name": j,
            "joint_type": JointType.HINGE,
            "min_stop": 0.0,
            "max_stop": 0.0,
            "min_stop_rot": 0.0,
            "max_stop_rot": 0.0,
            "min_stop_trans": 0.0,
            "max_stop_trans": 0.0,
            "actuated": True,
            "sensed": True,
        }
    elif isinstance(j, dict):
        jt = j.get("joint_type", JointType.HINGE)
        if isinstance(jt, str):
            try:
                jt = JointType(jt)
            except ValueError:
                jt = JointType.HINGE
        return {
            "name": j.get("name", ""),
            "joint_type": jt,
            "min_stop": float(j.get("min_stop", 0.0)),
            "max_stop": float(j.get("max_stop", 0.0)),
            "min_stop_rot": float(j.get("min_stop_rot", 0.0)),
            "max_stop_rot": float(j.get("max_stop_rot", 0.0)),
            "min_stop_trans": float(j.get("min_stop_trans", 0.0)),
            "max_stop_trans": float(j.get("max_stop_trans", 0.0)),
            "actuated": bool(j.get("actuated", True)),
            "sensed": bool(j.get("sensed", True)),
        }
    elif hasattr(j, "name"):
        jt = getattr(j, "joint_type", JointType.HINGE)
        return {
            "name": getattr(j, "name", ""),
            "joint_type": jt,
            "min_stop": float(getattr(j, "min_stop", 0.0)),
            "max_stop": float(getattr(j, "max_stop", 0.0)),
            "min_stop_rot": float(getattr(j, "min_stop_rot", 0.0)),
            "max_stop_rot": float(getattr(j, "max_stop_rot", 0.0)),
            "min_stop_trans": float(getattr(j, "min_stop_trans", 0.0)),
            "max_stop_trans": float(getattr(j, "max_stop_trans", 0.0)),
            "actuated": bool(getattr(j, "actuated", True)),
            "sensed": bool(getattr(j, "sensed", True)),
        }
    return {
        "name": str(j),
        "joint_type": JointType.HINGE,
        "min_stop": 0.0,
        "max_stop": 0.0,
        "min_stop_rot": 0.0,
        "max_stop_rot": 0.0,
        "min_stop_trans": 0.0,
        "max_stop_trans": 0.0,
        "actuated": True,
        "sensed": True,
    }


class BaseProtocolWriter(ABC):
    @abstractmethod
    def write(self, export_dir: str, robot_name: str, joints: Union[list[str], list[Any]], config: ProtocolConfig, peripherals: list[tuple[str, str]] = None) -> None:
        """
        Generates the necessary files in export_dir/controllers/<robot_name>_ctrl/
        """
        pass

    @abstractmethod
    def get_dependency_notice(self, robot_name: str, controller_dir: str) -> str:
        """
        Returns the dependency notice or instructions.
        """
        pass

