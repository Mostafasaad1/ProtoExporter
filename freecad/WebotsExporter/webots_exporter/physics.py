from typing import Any, Optional
from .datamodel import WbPhysics, WbVec3
from .exceptions import PhysicsError
from .datamodel import WBT_SCALE


class PhysicsCalculator:
    def compute(self, fc_shape: Any) -> Optional[WbPhysics]:
        mass = getattr(fc_shape, "Mass", None)
        volume = getattr(fc_shape, "Volume", None)
        com = getattr(fc_shape, "CenterOfMass", None)

        if mass is None:
            return None

        try:
            mass_val = float(mass)
        except (TypeError, ValueError):
            raise PhysicsError(f"Invalid mass value: {mass}")

        if volume is not None:
            try:
                vol_val = float(volume)
                if vol_val > 0 and abs(mass_val - vol_val) / vol_val < 1e-4:
                    mass_val *= 1e-6
            except (TypeError, ValueError):
                pass

        com_vec = WbVec3()
        if com is not None:
            try:
                com_vec = WbVec3.from_mm(float(com.x), float(com.y), float(com.z))
            except (AttributeError, TypeError, ValueError):
                pass

        return WbPhysics(mass=mass_val, center_of_mass=com_vec, density=-1.0)
