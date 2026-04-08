from ia.base_general import General
import math


def normalize(x, y):
    mag = math.hypot(x, y)
    if mag < 1e-6:
        return 0.0, 0.0
    return x / mag, y / mag
class Basic_IA(General):
    """
    knight attaque les ennemis à portée selon l’ordre C > P > K (HP le plus bas dans chaque type).

    pikeman attaque les ennemis à portée selon l’ordre K > C > P (HP le plus bas dans chaque type).

    crossbowman : Kite + attaque selon l’ordre C > K > P (HP le plus bas dans chaque type).
    """
    
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "Basic_IA"
    
    def execute_tatics(self):
        """
        Tactique BASIC:
        - Si winning: attaque agressivement
        - Si losing: focus sur targets faibles
        - Si even: attaque normalement
        """
        state = self.evalute_battle_state()
        
        for unit in self.get_my_units():
            if state == "losing":
                # se concentrer sur les ennemis faibles pour des kills rapides
                visible = self.get_visible_enemies(unit)
                if visible:
                    target = self.find_lowest_hp_enemy(visible)
                    self._attack_or_move(unit, target)
            else:
                # Attaque normale (closest enemy)
                self.attack_near(unit)
    
    def find_best_target_in_range(self, unit, priority_order):
        """
        priority_order : liste des types d’unités par ordre de priorité, par exemple ['C', 'P', 'K'].
        Pour chaque type, l’unité ayant les HP les plus bas est prioritaire.
        """
        for enemy_type in priority_order:
            enemies = [e for e in self.enemy_units 
                      if e.is_alive and e.type == enemy_type and unit.is_in_range(e)]
            if enemies:
                # trouve les enemies faible
                return min(enemies, key=lambda e: e.current_hp)
        return None
    
    def C_behaviour(self, unit):
        # crossbowman : Kite + attaque selon l’ordre C > K > P (HP le plus bas dans chaque type).
        # kite si il y a kninght et pikeman proche
        if self.keep_dist(unit, unit.range - 0.5):
            target = self.find_best_target_in_range(unit, ['C', 'S', 'K' 'L', 'P'])
        
            if target:
                self.attack(unit, target)
        else:
            target = self.find_best_target_in_range(unit, ['C', 'S', 'K' 'L', 'P'])
            if target:
                self.attack(unit, target)
            else:
                # si ils sont pas dans range, attack enemie proche 
                self.attack_near(unit)


    def K_behaviour(self, unit):
        #  knight attaque les ennemis à portée selon l’ordre C > P > K (HP le plus bas dans chaque type).
        target = self.find_best_target_in_range(unit, ['C', 'S', 'L', 'P', 'K'])
        
        if target:
            self.attack(unit, target)
            return

        # self.attack_near(unit)

        # crossbowman_proche = [e for e in self.enemy_units if e.is_alive and e.type == 'C']
        # if crossbowman_proche:
        #     closest_C = min(crossbowman_proche, key=lambda e: unit.distance_to(e))
        #     self.move_unit(unit, closest_C.position)
        #     return

        targets = [e for e in self.enemy_units if e.is_alive and e.type in ['C', 'S']]
        if targets:
            closest_range = min(targets, key=lambda e: unit.distance_to(e))
            blocker = [e for e in self.enemy_units if e.is_alive and e.type in ['L', 'P'] and e.distance_to(unit) < closest_range.distance_to(unit)]
            if blocker:
                target_block = min(blocker, key=lambda b: unit.distance_to(b))
                self.move_unit(unit, target_block.position)
                return
            self.move_unit(unit, closest_range.position)
            return
        # aucun crossbowman, attack enemie proche
        self.attack_near(unit)

    
    def P_behaviour(self, unit):
        # target = self.find_closest_enemy(unit)
        target = self.find_best_target_in_range(unit, ['K','L', 'S', 'C', 'P'])
        
        if target and unit.is_in_range(target):
            self.attack(unit, target)
            return
        
        # trouver kninght proche
        # enemie_knight = [e for e in self.enemy_units if e.is_alive and e.type == 'K']
        # if enemie_knight:
        #     closest_K = min(enemie_knight, key=lambda e: unit.distance_to(e))
        #     self.move_unit(unit, closest_K.position)
        #     return

        target = [e for e in self.enemy_units if e.is_alive and e.type in ['K', 'L']]
        if target:
            closest_target = min(target, key=lambda e: unit.distance_to(e))
            self.move_unit(unit, closest_target.position)
            return
        
        self.attack_near(unit)

    def L_behaviour(self, unit):
        """Pas d'aventages specials, attack le plus proche"""
        self.attack_near(unit)

    def S_behaviour(self, unit):
        #kite et attack crosbowman
        if self.keep_dist(unit, unit.range-0.5):
            target = self.find_best_target_in_range(unit, ['C', 'S', 'P', 'K'])
            if target:
                self.attack(unit, target)
                return
        # else:
        target = self.find_best_target_in_range(unit, ['C', 'S', 'P', 'K'])
        if target:
            self.attack(unit, target)
        else:
            self.attack_near(unit)
            

    def play_turn(self, unit, turn=0):
        self.initialize()

        if not unit or not unit.is_alive:
            return

        if unit.type == 'C':
            self.C_behaviour(unit)
        elif unit.type == 'K':
            self.K_behaviour(unit)
        elif unit.type == 'P':
            self.P_behaviour(unit)
        elif unit.type == "L":
            self.L_behaviour(unit)
        elif unit.type =="S":
            self.S_behaviour(unit)
        else:
            self.attack_near(unit)