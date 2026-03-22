from .beaconing import BEACONINGPattern
from .dns_tunneling import DNSTUNNELINGPattern
from .lateral_movement import LATERALMOVEMENTPattern
from .volume_anomaly import VOLUMEANOMALYPattern
from .time_anomaly import TIMEANOMALYPattern

# Instanciar singleton de los patrones heurísticos estáticos
PATTERNS = [
    BEACONINGPattern(),
    DNSTUNNELINGPattern(),
    LATERALMOVEMENTPattern(),
    VOLUMEANOMALYPattern(),
    TIMEANOMALYPattern()
]
