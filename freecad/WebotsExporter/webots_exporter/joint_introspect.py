from typing import Any
from .datamodel import WbVec3, JointType
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

    ref1 = getattr(fc_joint, "Reference1", None)
    placement1 = getattr(fc_joint, "Placement1", None)
    
    anchor = WbVec3()
    axis = WbVec3(0, 0, 1) # Default axis is Z-axis

    if ref1 and isinstance(ref1, (list, tuple)) and len(ref1) > 0 and placement1 is not None:
        part = ref1[0]
        if hasattr(part, "Placement"):
            try:
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

    return {
        "name": name,
        "joint_type": wb_type,
        "anchor": anchor,
        "axis": axis,
    }
