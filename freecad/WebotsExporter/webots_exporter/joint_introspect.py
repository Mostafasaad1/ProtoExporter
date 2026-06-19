from typing import Any
from .datamodel import WbVec3, WbAxisAngle, JointType
from .exceptions import JointParsingError


FREECAD_TO_WEBOTS_JOINT = {
    "Revolute": JointType.HINGE,
    "Slider": JointType.SLIDER,
    "Ball": JointType.BALL,
    "Cylindrical": JointType.HINGE,
    "Screw": JointType.SLIDER,
    "Fixed": JointType.FIXED,
}


def dump_joint_properties(fc_joint: Any) -> dict[str, Any]:
    name = getattr(fc_joint, "Label", "")
    
    fc_type = getattr(fc_joint, "Type", "")
    if not fc_type and hasattr(fc_joint, "JointType"):
        fc_type = fc_joint.JointType
    if not fc_type and hasattr(fc_joint, "TypeId"):
        type_id = fc_joint.TypeId
        if type_id.startswith("Assembly::Joint"):
            fc_type = type_id[len("Assembly::Joint"):]
            
    wb_type = FREECAD_TO_WEBOTS_JOINT.get(fc_type)
    if wb_type is None:
        raise JointParsingError(f"Unsupported joint type: {fc_type or type(fc_joint)}")

    origin = getattr(fc_joint, "Placement", None)
    anchor = WbVec3()
    axis = WbAxisAngle()

    if origin is not None:
        base = getattr(origin, "Base", None)
        if base is not None:
            anchor = WbVec3.from_mm(base.x, base.y, base.z)

        rotation = getattr(origin, "Rotation", None)
        if rotation is not None:
            q = rotation.Q if hasattr(rotation, "Q") else None
            if q is not None:
                axis = _quat_to_axis_angle(q)

    return {
        "name": name,
        "joint_type": wb_type,
        "anchor": anchor,
        "axis": axis,
    }


def _quat_to_axis_angle(q: Any) -> WbAxisAngle:
    _check = q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]
    angle = 2.0 * _acos_clamped(q[3])
    s = (1.0 - q[3] * q[3]) ** 0.5
    if s < 1e-6:
        return WbAxisAngle(1, 0, 0, angle)
    return WbAxisAngle(q[0] / s, q[1] / s, q[2] / s, angle)


def _acos_clamped(v: float) -> float:
    import math
    return math.acos(max(-1.0, min(1.0, v)))
