# ia/registry.py
from ia.basic_ia import Basic_IA
from ia.smart_ia import Smart_IA
from ia.brain_dead import Brain_DEAD
from ia.daft import MajorDaft
from ia.tacticus10 import Behaviour
from ia.tacticus11 import Behaviour1
from ia.tacticus12 import Behaviour2
from ia.tacticus20 import Behaviour3
from ia.coord_ia import CoordIA
from ia.coord1_ia import CoordIA1
from ia.strategus20 import Strategus20
from ia.strategus10 import Strategus10

"""
Registry of available AI classes 
All names are stored in lowercase without spaces or special characters.
"""

AI_REGISTRY = {
    "smartia": Smart_IA,
    "braindead": Brain_DEAD,
    "majordaft": MajorDaft,
    "daft": MajorDaft,
    "strategus20" : Strategus20,
    "tacticus20": Behaviour3,
    "basicia": Basic_IA,
    "strategus10" : Strategus10,

}
""""
    "coordia1": CoordIA1,
    "braindead": Brain_DEAD,
    "majordaft": MajorDaft,
    "tacticus10" : Behaviour,
    "tacticus11" : Behaviour1,
    "tacticus12" : Behaviour2,
    "tacticus20" : Behaviour3,
    "strategus20" : Strategus20,
    "strategus10" : Strategus10,"""

#

# ia pour lanchester
