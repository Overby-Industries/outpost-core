"""outpost-core: systems software for surface outposts and repair depots."""
from .advisory import contention_to_advisory
from .docking import Contention, DockRequest, DockingCoordinator, Port, Schedule, Slot
from .node import OutpostNode
from .power import Load, PowerBudget

__all__ = ["Contention", "DockRequest", "DockingCoordinator", "Load", "OutpostNode",
           "Port", "PowerBudget", "Schedule", "Slot", "contention_to_advisory"]
__version__ = "0.1.0"
