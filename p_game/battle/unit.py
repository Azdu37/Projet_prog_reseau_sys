import json
import os
import math

class Unit:
    #on crée une variable dans laquelle on met le contenu de units.json ; agit comme une mémoire cache qui nous évite d'avoir à rouvrir le fichier chaque fois qu'on a besoin de piocher des données dedans
    UNIT_CONFIG = {}

    def __init__(self, hp=None, attacks=None, armors=None, pierce_armor=None, range=None, range_min = None, line_of_sight=None,
                 speed=None, build_time=None, attack_delay=None, reload_time=None,team=None, type=None, position=(None,None)):
        #On différencie les HP max, des HP actuels
        self.type = type
        self.max_hp = hp
        self.current_hp = hp
        self.pierce_armor = pierce_armor
        self.range = range
        self.range_min = range_min
        self.line_of_sight = line_of_sight
        self.speed = speed
        self.attack_delay = attack_delay
        self.size = None
        self.build_time = build_time
        self.reload_time = reload_time
        self.position = position  # (x,y)
        self.destination = None
        self.team = team
        # Ownership réseau (défini par le moteur en mode réparti)
        self.is_local = False  # True si l'unité est pilotée localement
        self.network_owner = None  # Optionnel: identifiant/équipe propriétaire
        self.unit_id = 0       # Identifiant unique réseau
        self.owner_id = 0      # Identifiant du propriétaire (R=1, B=2)
        self.squad = []
        self.squad.append(self)
        self.get_hit = 0

        #l'état de l'unité
        self.is_alive = True
        self.state = "idle"  # idle, moving, attacking, dead
        self.target = None  # cible actuelle de l'unité

        #stats avancées
        self.attacks = attacks
        self.armors = armors
        self.direction = (0,0)
        self.orientation = 0
        # atack timming
        self.time_until_next_attack = 0
        self.time_before_next_attack = self.attack_delay
        
    #charge le fichier units.json
    def load_unit_data(self):
        path = "data/units.json"
        if not os.path.exists(path):
            print(f"ERREUR : Le fichier {path} est introuvable.")
            return
        with open(path, 'r') as f:  #permet de s'assurer la fermeture du fichier meme en cas de crash
            self.UNIT_CONFIG = json.load(f)
        # print(f"Unités chargées depuis {path}.")

    #méthode permettant de créer les objets unités
    def get_by_type(self, type, team, position):
        # Chargement automatique si UNIT_CONFIG vide
        if self.UNIT_CONFIG == {}:
            self.load_unit_data()

        # Récupération des données dans UNIT_CONFIG
        data = self.UNIT_CONFIG[type]
        stats = data["stats"]

        self.type = type
        self.team = team
        self.position = position

        # Stats vitales
        self.max_hp = stats["hp"]
        self.current_hp = stats["hp"]
        self.is_alive = True
        self.state = "alive"

        # Stats avancées
        self.attacks = data["attacks"]
        self.armors = data["armors"]
        self.pierce_armor = stats["pierceArmor"]

        # Stats physiques
        self.range = stats["range"]
        try :
            self.range_min = stats["range_min"]
        except:
            self.range_min = 0
        self.line_of_sight = stats["lineOfSight"]
        self.speed = stats["speed"]
        self.size = stats["size"]

        # Temps
        self.build_time = stats["buildTimeSeconds"]
        self.attack_delay = stats["attackDelay"]
        self.reload_time = stats["reloadTimeSeconds"]
        self.time_until_next_attack = 0
        self.time_before_next_attack = self.attack_delay
        self.target = None

        self.direction= None
        return self

    #---DEFINITION DES METHODES---
    def is_dead(self):
        return self.current_hp <= 0


    def take_damage(self, attacker):
        """ - sommer les dommages subis dans une variable
         - soustraire ces dommages aux points de vie
         - vérifier si le soldat est mort"""

        # verification si l'attaquant est vivant
        assert isinstance(attacker, Unit), "L'attaquant doit être une instance de la classe Unit"

        #création de la variable
        total_damage = 0

        #création d'une boucle qui parcourt chaque entrée du dictionnaire "attacks" de l'attacker :
        for attack_type, attack_value in attacker.attacks.items():
            # Si le defenseur est du meme type que le type d'attaque
            if attack_type in self.armors:
                #calcul de la somme d'après la formule
                total_damage += max(0, attack_value - self.armors[attack_type])
        #soustraction aux points de vie
        total_damage=max(1,total_damage)
        self.current_hp -= total_damage
        self.get_hit = 0.2
        # HP n'est jamais negatif
        if self.current_hp < 0:
            self.current_hp = 0

        return total_damage

    def is_in_tile(self, unit, tile_size):
        """checks if unit touching a (2*tile_size)**2 square centered on tile_pos"""
        ux, uy = unit.position
        tx, ty = self.position

        # Check overlap in X and Y separately
        margin = tile_size + self.size +0.1
        return (tx - margin < ux < tx + margin) and (ty - margin < uy < ty + margin)
        

    # distance entre deux unités
    def distance_to(self, other_unit):
        assert isinstance(other_unit, Unit), "L'autre unité doit être une instance de la classe Unit"
        # calcul de la distance euclidienne entre les deux unités
        dx = self.position[0] - other_unit.position[0]
        dy = self.position[1] - other_unit.position[1]
        distance = math.sqrt((dx * dx + dy * dy))
        return distance
    
    
    def distance_to_2(self, other_unit):
        assert isinstance(other_unit, Unit), "L'autre unité doit être une instance de la classe Unit"
        # calcul de la distance euclidienne entre les deux unités
        dx = self.position[0] - other_unit.position[0]
        dy = self.position[1] - other_unit.position[1]
        distance_2 = (dx * dx + dy * dy)
        return distance_2

    # Vérifiez la portée d'attaque
    def is_in_range(self, other_unit):
        if self.is_in_tile(other_unit, self.range+1):
            distance_2 = self.distance_to_2(other_unit)
            return distance_2 <= (self.range + self.size + other_unit.size + 0.1)**2 and distance_2 >= (self.range_min + self.size + other_unit.size)**2
        return False
    
    def is_in_LOS(self,other_unit):
        if self.is_in_tile(other_unit, self.line_of_sight):
            distance_2 = self.distance_to_2(other_unit)
            return distance_2 <= (self.line_of_sight + self.size + other_unit.size)**2
        return False

    # Vérifiez si l'unité peut attaquer
    def can_attack(self, other_unit):
        if not self.is_alive:
            return False
        if not other_unit.is_alive:
            return False
        if self.team == other_unit.team:
            return False
        if not self.is_in_range(other_unit):
            return False
        if self.time_until_next_attack > 0:
            return False
        return True

    # Attack unite 
    """def attack(self, other_unit):
        if not self.can_attack(other_unit):
            return 0  # Ne peut pas attaquer

        # commence l'attaque
        self.state = "attacking"

        damage_dealt = other_unit.take_damage(self)

        # set cooldown
        self.time_until_next_attack = self.reload_time
        return damage_dealt"""
    def time_reset(self):
            self.time_until_next_attack = self.reload_time
            self.time_before_next_attack = self.attack_delay
        # update time 
    def update(self, time_passed):
            # Si l'unité est morte, elle ne peut rien faire
            if self.is_dead():
                self.is_alive = False
                self.state = "dead"
                self.target = None

            if self.state =="attacking":
                self.direction = (0,0)
                self.time_before_next_attack -= time_passed
                if self.time_before_next_attack <= 0:
                    self.time_before_next_attack = 0
                    self.state="idle"

            if self.time_until_next_attack > 0:
                #self.state = "reloading"
                self.time_until_next_attack -= time_passed
                if self.time_until_next_attack < 0:
                    self.time_until_next_attack = 0
            if self.state != "moving":
                self.direction = (0,0)
            else:
                # si l'unite n'est pas morte, on peut ajouter d'autres comportements ici
                if self.state not in ["moving", "attacking" , "reloading"]:
                    self.state = "idle"
                    self.target = None
