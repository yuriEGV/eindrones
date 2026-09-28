"""
FLYBRIDGE — Sistema Operativo Bio-Inspirado de Prevención y Verificación de Incendios Forestales
Combina la inferencia neuromórfica NeuroFly en Nodos Arbóreos Ignífugos con una estación
Drone-in-a-Box alojada en dependencias de las autoridades (Bomberos, Carabineros, CONAF).
"""

from .core import FlybridgeNervousSystem
from .tree_node import TreeNodeModel, BasinGateway, LoRaCompactPacket, NeuroFlyEdgeInference
from .docking_station import AuthorityFacility, VerifierDroneAgent, DroneInABoxStation
from .authority_dispatch import AuthorityDispatchCoordinator
from .mission_server import CentralMissionServer

__version__ = "1.0.0"

__all__ = [
    "FlybridgeNervousSystem",
    "TreeNodeModel",
    "BasinGateway",
    "LoRaCompactPacket",
    "NeuroFlyEdgeInference",
    "AuthorityFacility",
    "VerifierDroneAgent",
    "DroneInABoxStation",
    "AuthorityDispatchCoordinator",
    "CentralMissionServer"
]
