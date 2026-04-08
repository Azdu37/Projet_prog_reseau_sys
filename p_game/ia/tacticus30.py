from ia.base_general import General

class Behaviour4(General):
    """ 
    Comportement "Phalange" :
    - C : Focus fire (tous sur la même cible) et maintient la distance.
    - P : Reste à proximité des C pour les protéger (intercepte les ennemis proches).
    - K : Chasse l'unité ennemie la plus faible (low HP) pour réduire le nombre d'attaquants.
    """
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "tacticus 3.0"

    def get_lowest_hp_enemy(self):
        """ Trouve l'ennemi avec le moins de points de vie """
        enemies = [u for u in self.enemy_units if u.is_alive]
        if not enemies:
            return None
        return min(enemies, key=lambda u: u.current_hp)

    def get_team_center(self, unit_type):
        """ Calcule la position moyenne d'un type d'unité """
        my_units = [u for u in self.my_units_dict[unit_type] if u.is_alive]
        if not my_units:
            return None
        avg_x = sum(u.position[0] for u in my_units) / len(my_units)
        avg_y = sum(u.position[1] for u in my_units) / len(my_units)
        return (avg_x, avg_y)

    def C_behaviour(self, C):
        """ Focus fire : Les C attaquent la cible la plus faible en priorité """
        target = self.get_lowest_hp_enemy()
        self.keep_dist(C, C.range - 0.5)
        
        if target and C.is_in_range(target):
            C.attack(target)
        else:
            self.attack_near(C)

    def P_behaviour(self, P):
        """ Protection : Les P restent près des C """
        center_C = self.get_team_center("C")
        closest_enemy = self.find_closest_enemy(P)

        # Si un ennemi est trop proche des Crossbows, on l'intercepte
        if closest_enemy and center_C:
            dist_enemy_to_archers = self.map.distance(closest_enemy.position, center_C)
            if dist_enemy_to_archers < 3:
                if P.is_in_range(closest_enemy):
                    P.attack(closest_enemy)
                else:
                    self.move_unit(P, closest_enemy.position)
                return

        # Sinon, on escorte le groupe de Crossbows
        if center_C:
            if self.map.distance(P.position, center_C) > 2:
                self.move_unit(P, center_C)
            else:
                self.attack_near(P)
        else:
            self.attack_near(P)

    def K_behaviour(self, K):
        """ Assassin : Les K cherchent l'unité la plus faible, peu importe son type """
        weakest = self.get_lowest_hp_enemy()
        
        if weakest:
            if K.is_in_range(weakest):
                K.attack(weakest)
            else:
                self.move_unit(K, weakest.position)
        else:
            self.attack_near(K)

    def play_turn(self, unit,turn):
        if not unit.is_alive:
            return

        if unit.type == "C":
            self.C_behaviour(unit)
        elif unit.type == "K":
            self.K_behaviour(unit)
        elif unit.type == "P":
            self.P_behaviour(unit)