from typing import Any
from .datamodel import WbVec3, JointType
from .exceptions import JointParsingError


FREECAD_TO_WEBOTS_JOINT = {
    "Revolute": JointType.HINGE,
    "Slider": JointType.SLIDER,
    "Ball": JointType.BALL,
    "Spherical": JointType.BALL,
    "Cylindrical": JointType.CYLINDRICAL,
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

    ref1 = getattr(fc_joint, "Reference1", None)
    ref2 = getattr(fc_joint, "Reference2", None)
    placement1 = getattr(fc_joint, "Placement1", None)
    placement2 = getattr(fc_joint, "Placement2", None)

    anchor = WbVec3()
    axis = WbVec3(0, 0, 1)  # Default axis is Z-axis

    if ref1 and isinstance(ref1, (list, tuple)) and len(ref1) > 0 and placement1 is not None:
        part = ref1[0]
        if hasattr(part, "Placement"):
            try:
                # Compute the joint connector's world-space placement.
                # All Webots Solids have translation=0, so the world frame IS the
                # parent Solid's frame.  World-space anchor/axis is therefore correct.
                global_placement = part.Placement.multiply(placement1)
                pos = global_placement.Base
                anchor = WbVec3.from_mm(pos.x, pos.y, pos.z)

                import FreeCAD
                local_z = FreeCAD.Vector(0, 0, 1)
                global_z = global_placement.Rotation.multVec(local_z)
                axis = WbVec3(global_z.x, global_z.y, global_z.z)
            except Exception:
                pass
    else:
        # Fallback to Placement of joint
        origin = getattr(fc_joint, "Placement", None)
        if origin is not None:
            base = getattr(origin, "Base", None)
            if base is not None:
                anchor = WbVec3.from_mm(base.x, base.y, base.z)
            rotation = getattr(origin, "Rotation", None)
            if rotation is not None:
                try:
                    import FreeCAD
                    local_z = FreeCAD.Vector(0, 0, 1)
                    global_z = rotation.multVec(local_z)
                    axis = WbVec3(global_z.x, global_z.y, global_z.z)
                except Exception:
                    pass

    import math

    min_stop_rot = 0.0
    max_stop_rot = 0.0
    min_stop_trans = 0.0
    max_stop_trans = 0.0

    enable_min_rot = True
    if hasattr(fc_joint, "EnableAngleMin"):
        enable_min_rot = bool(fc_joint.EnableAngleMin)
    elif hasattr(fc_joint, "EnableMinAngle"):
        enable_min_rot = bool(fc_joint.EnableMinAngle)

    enable_max_rot = True
    if hasattr(fc_joint, "EnableAngleMax"):
        enable_max_rot = bool(fc_joint.EnableAngleMax)
    elif hasattr(fc_joint, "EnableMaxAngle"):
        enable_max_rot = bool(fc_joint.EnableMaxAngle)

    if enable_min_rot:
        val = getattr(fc_joint, "AngleMin", getattr(fc_joint, "MinAngle", None))
        if val is not None:
            raw_val = getattr(val, "Value", val)
            if isinstance(raw_val, (int, float)):
                min_stop_rot = math.radians(raw_val)

    if enable_max_rot:
        val = getattr(fc_joint, "AngleMax", getattr(fc_joint, "MaxAngle", None))
        if val is not None:
            raw_val = getattr(val, "Value", val)
            if isinstance(raw_val, (int, float)):
                max_stop_rot = math.radians(raw_val)

    enable_min_trans = True
    if hasattr(fc_joint, "EnableLengthMin"):
        enable_min_trans = bool(fc_joint.EnableLengthMin)
    elif hasattr(fc_joint, "EnableMinLength"):
        enable_min_trans = bool(fc_joint.EnableMinLength)
    elif hasattr(fc_joint, "EnableDistanceMin"):
        enable_min_trans = bool(fc_joint.EnableDistanceMin)

    enable_max_trans = True
    if hasattr(fc_joint, "EnableLengthMax"):
        enable_max_trans = bool(fc_joint.EnableLengthMax)
    elif hasattr(fc_joint, "EnableMaxLength"):
        enable_max_trans = bool(fc_joint.EnableMaxLength)
    elif hasattr(fc_joint, "EnableDistanceMax"):
        enable_max_trans = bool(fc_joint.EnableDistanceMax)

    if enable_min_trans:
        val = getattr(fc_joint, "LengthMin", getattr(fc_joint, "MinLength", getattr(fc_joint, "DistanceMin", None)))
        if val is not None:
            raw_val = getattr(val, "Value", val)
            if isinstance(raw_val, (int, float)):
                min_stop_trans = raw_val / 1000.0

    if enable_max_trans:
        val = getattr(fc_joint, "LengthMax", getattr(fc_joint, "MaxLength", getattr(fc_joint, "DistanceMax", None)))
        if val is not None:
            raw_val = getattr(val, "Value", val)
            if isinstance(raw_val, (int, float)):
                max_stop_trans = raw_val / 1000.0

    if min_stop_rot > max_stop_rot:
        min_stop_rot, max_stop_rot = max_stop_rot, min_stop_rot

    if min_stop_trans > max_stop_trans:
        min_stop_trans, max_stop_trans = max_stop_trans, min_stop_trans

    actuated = False
    sensed = False
    if hasattr(fc_joint, "WebotsActuated"):
        actuated = bool(fc_joint.WebotsActuated)
    elif hasattr(fc_joint, "Actuated"):
        actuated = bool(fc_joint.Actuated)
        
    if hasattr(fc_joint, "WebotsSensed"):
        sensed = bool(fc_joint.WebotsSensed)
    elif hasattr(fc_joint, "Sensed"):
        sensed = bool(fc_joint.Sensed)

    return {
        "name": name,
        "joint_type": wb_type,
        "anchor": anchor,
        "axis": axis,
        "min_stop_rot": min_stop_rot,
        "max_stop_rot": max_stop_rot,
        "min_stop_trans": min_stop_trans,
        "max_stop_trans": max_stop_trans,
        "actuated": actuated,
        "sensed": sensed,
    }
