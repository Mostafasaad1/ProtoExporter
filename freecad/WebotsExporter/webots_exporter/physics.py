from typing import Any, Optional
from .datamodel import WbPhysics, WbVec3
from .exceptions import PhysicsError
from .datamodel import WBT_SCALE


class PhysicsCalculator:
    def compute(self, fc_shape: Any) -> Optional[WbPhysics]:
        mass = getattr(fc_shape, "Mass", None)
        com = getattr(fc_shape, "CenterOfMass", None)

        if mass is None:
            return None

        try:
            mass_val = float(mass)
        except (TypeError, ValueError):
            raise PhysicsError(f"Invalid mass value: {mass}")

        com_vec = WbVec3()
        if com is not None:
            try:
                com_vec = WbVec3.from_mm(float(com.x), float(com.y), float(com.z))
            except (AttributeError, TypeError, ValueError):
                pass

        return WbPhysics(mass=mass_val, center_of_mass=com_vec, density=-1.0)
