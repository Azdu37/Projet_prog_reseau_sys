from ia.base_general import General
from math import sqrt
import math

def normalize(x, y):
    mag = math.hypot(x, y)
    if mag < 1e-6:
        return 0.0, 0.0
    return x / mag, y / mag

class Smart_IA(General):
    """
    SmartBehaviour_IA - Version agressive

    Stratégie : attaque et mouvement optimisés
    - Crossbowman : garder la distance + kiter
    - Kninght : attaque agressive + viser les arbalétriers
    - Pikeman : contrer les chevaliers + attaque agressive
    """
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "Smart_IA"

    def avoid(self, unit, dist, min_dist, avoid_type, intent):
        """
        Se déplacer vers intent mais éviter les unités de type avoid_type.
        Si une unité avoid_type est trop proche (< min_dist), garder la distance.
        Retourne True si une action a été effectuée, False sinon.
        """
        ux, uy = unit.position
        ix, iy = intent
        intent_x = ix - ux
        intent_y = iy - uy
        intent_x, intent_y = normalize(intent_x, intent_y)

        avoid_x = 0.0
        avoid_y = 0.0
        avg_x = 0.0
        avg_y = 0.0
        count = 0
        min_dist_2 = min_dist ** 2

        for enemy in self.enemy_units:
            if not enemy.is_alive or enemy.type != avoid_type:
                continue
            if not self.map.is_in_tile(enemy, unit.position, dist):
                continue
            dx = ux - enemy.position[0]
            dy = uy - enemy.position[1]
            d2 = dx * dx + dy * dy

            # Si trop proche, garder la distance immédiatement
            if d2 < min_dist_2:
                return self.keep_dist_from(unit, enemy, min_dist)

            if d2 < (dist + enemy.size + unit.size) ** 2:
                dx, dy = normalize(dx, dy)
                weight = 1.0 / max(d2, 1)
                avoid_x += dx * weight
                avoid_y += dy * weight
                avg_x += enemy.position[0]
                avg_y += enemy.position[1]
                count += 1

        if count == 0:
            return False

        avg_x /= count
        avg_y /= count
        avoid_x, avoid_y = normalize(avoid_x, avoid_y)

        # Vérifier l'alignement
        dot = intent_x * avoid_x + intent_y * avoid_y
        if dot < -0.5:
            # Si l'évitement est en sens inverse de l'intention, faire un sidestep
            avoid_x, avoid_y = -avoid_y, avoid_x
            side = (ux - avg_x) * avoid_x + (uy - avg_y) * avoid_y
            if side < 0:
                avoid_x, avoid_y = -avoid_x, -avoid_y

        # Combiner intention et évitement
        final_x = intent_x + avoid_x * 0.5
        final_y = intent_y + avoid_y * 0.5
        final_x, final_y = normalize(final_x, final_y)

        new_x = ux + final_x * unit.speed
        new_y = uy + final_y * unit.speed
        self.move_unit(unit, (new_x, new_y))
        return True
    
    def keep_dist_from(self, unit, enemy, dist):
        """Garder la distance par rapport à un ennemi"""
        dx = unit.position[0] - enemy.position[0]
        dy = unit.position[1] - enemy.position[1]
        dx, dy = normalize(dx, dy)
        self.move_unit(unit, (dx * unit.speed + unit.position[0], dy * unit.speed + unit.position[1]))
        return True
    
    def attack_in_range(self, unit):
        """
        Attaque si un ennemi est à portée
        Choisit l'ennemi le plus dangereux
        """
        ennemies = self.get_enemy_units()
        if not ennemies:
            return False
        # Trouver les ennemies à portée
        ennemies_portee = [e for e in ennemies if e.is_alive and unit.is_in_range(e)]
        if not ennemies_portee:
            return False

        # Choisir l'ennemi le plus dangereux
        cible = max(ennemies_portee, key=lambda e: self.threat_score(e))
        self.attack(unit,cible)
        return True

    def attack_near_aggressive(self, unit, target_type=None):
        """
        Attaque l'ennemi le plus proche
        Peut cibler un type spécifique si précisé
        """
        ennemies = self.get_enemy_units()
        if not ennemies:
            return False
        #filtre type_target
        if target_type:
            ennemies = [e for e in ennemies if e.type == target_type and e.is_alive]
        else: 
            ennemies = [e for e in ennemies if e.is_alive]

        if not ennemies:
            return False
        # trouve enemie plus proche
        proche = min(ennemies, key=lambda e: unit.distance_to(e))
        
        if unit.is_in_range(proche):
            # unit.attack(proche)
            self.attack(unit, proche)
            return True
        
        return False

    def threat_score(self, enemy):
        
        #Score de menace: damage / hp

        if not enemy:
            return -1
        
        hp = max(1, getattr(enemy, 'current_hp', 100))

        dmg = sum(enemy.attacks.values()) if hasattr(enemy, 'attacks') else 1

        return dmg / hp 

    def clamp_position(self, pos):
        #assure position dans map
        x, y = pos
        x = max(0, min(x, self.map.p - 1))
        y = max(0, min(y, self.map.q - 1))
        return (x, y)
    
    def focus_crossbowman(self, unit):
        # concenter sủ crowwbowman
        enemies = self.get_enemy_units()
        crossbowman = [e for e in enemies if e.type == "C" and e.is_alive]
        
        if not crossbowman:
            return None

        crossbowman_proche = min(crossbowman, key = lambda e:  unit.distance_to(e)) if crossbowman else None
        
        return crossbowman_proche

    def C_behaviour(self, unit):
        """
        Comportement Arbalétrier: attaque + kiting
        """
        my_unit = self.get_my_units()
        if not my_unit:
            return
        
        ennemies = self.get_enemy_units()
        if not ennemies:
            return
        
        enemie_proche = min(ennemies, key=lambda e: unit.distance_to(e))
        if not enemie_proche or not enemie_proche.is_alive:
            return

        current_dist = unit.distance_to(enemie_proche)
        safe_distance = max(1.5, unit.range*0.6)

        enemy_C = len([e for e in ennemies if e.type == "C" and e.is_alive])
        my_C = len([u for u in my_unit if u.type == "C" and u.is_alive])

        crossbowman_target = self.focus_crossbowman(unit)
        if crossbowman_target and unit.is_in_range(crossbowman_target):
            if my_C >= enemy_C:
                self.attack(unit,crossbowman_target)
                return
        
        # Priority 1 attack in range
        if unit.is_in_range(enemie_proche):
            self.attack(unit, enemie_proche)
            return

         # Priority 2: kite si elle est proche
        if current_dist < safe_distance:
            if current_dist < safe_distance * 0.5:
                self.keep_dist_from(unit, enemie_proche, safe_distance)
                return
            
            # utilise avoid pour kite Knight và Pikeman
            ux, uy = unit.position
            retreat_x = ux + (ux - enemie_proche.position[0])
            retreat_y = uy + (uy - enemie_proche.position[1])
            retreat_pos = self.clamp_position((retreat_x, retreat_y))
            
            if self.avoid(unit, dist=safe_distance, min_dist=safe_distance*0.5, avoid_type="K", intent=retreat_pos):
                return
            if self.avoid(unit, dist=safe_distance, min_dist=safe_distance*0.5, avoid_type="P", intent=retreat_pos):
                return
            

            dx = unit.position[0] - enemie_proche.position[0]
            dy = unit.position[1] - enemie_proche.position[1]
            dx_norm, dy_norm = normalize(dx, dy)
            
            step = 1.5
            new_x = unit.position[0] + dx_norm * step
            new_y = unit.position[1] + dy_norm * step
            safe_pos = self.clamp_position((new_x, new_y))
            
            self.move_unit(unit, safe_pos)
            return
        # Priority 3: chase si elle est distance
        safe_pos = self.clamp_position(enemie_proche.position)
        self.move_unit(unit, safe_pos)

    def K_behaviour(self, unit):
        """
        - Priority 1 : attaquer les Crossbowman ennemis (contrer la distance)
        - Priority 2 : attaquer l'ennemi le plus proche (agressif)
        """
        # Priority 1 : attaquer les crossbowman ennemis
        if self.attack_in_range(unit):
            return

        # Essayer d'attaquer les crossbowman même hors de portée
        ennemis = self.get_enemy_units()

        if not ennemis:
            return
        
        my_unit = self.get_my_units()
        crossbowman = [e for e in ennemis if e.type == "C" and e.is_alive]
        
        if len(crossbowman) > 0:
            if self.attack_near_iftype(unit, "C"):
                return
            target = min(ennemis, key=lambda e: unit.distance_to(e))
            # safe_pos = self.clamp_position(target.position)
            # self.move_unit(unit, safe_pos)
            # return

            # utilise avoid pour kite pikeman
            if self.avoid(unit, dist=5, min_dist=3, avoid_type="P", intent=target.position):
                return
            
            tx, ty = target.position
            ux, uy = unit.position
            dx, dy = normalize(tx - ux, ty - uy)
            new_x = ux + dx * unit.speed
            new_y = uy + dy * unit.speed
            self.move_unit(unit, self.clamp_position((new_x, new_y)))
            return
        
        # if crossbowman:
        #     # Rush vers crossbowman
        #     target = min(crossbowman, key=lambda e: unit.distance_to(e))
        #     if unit.is_in_range(target):
        #         unit.attack(target)
        #     else:
        #         safe_pos = self.clamp_position(target.position)
        #         self.move_unit(unit, safe_pos)
        #     return
        
        
        # Priority 2 : fallback - attaquer le plus proche
        enemie_proche = min(ennemis, key=lambda e: unit.distance_to(e)) if ennemis else None
        if enemie_proche:
            if unit.is_in_range(enemie_proche):
                self.attack(unit, enemie_proche)
            else:
                safe_pos = self.clamp_position(enemie_proche.position)
                self.move_unit(unit, safe_pos)

    def P_behaviour(self, unit):
        """
        attack kninght
        - Priority 1 : attaquer les knight ennemis 
        - Priority 2 : attaquer ennemi le plus proche
        """
        # Priority 1 : attack knight
        # if self.attack_in_range(unit):
        #     return

        ennemis = self.get_enemy_units()
        knight = [e for e in ennemis if e.type == "K" and e.is_alive]

        if knight:
            target = min(knight, key=lambda e: unit.distance_to(e))
            if unit.is_in_range(target):
                self.attack(unit,target)
                return
            # else:
            #     safe_pos = self.clamp_position(target.position)
            #     self.move_unit(unit, safe_pos)
            # return

            if self.avoid(unit, dist=8, min_dist=5, avoid_type="C", intent=target.position):
                return
            

            tx, ty = target.position
            ux, uy = unit.position
            dx, dy = normalize(tx - ux, ty - uy)
            new_x = ux + dx * unit.speed
            new_y = uy + dy * unit.speed
            self.move_unit(unit, self.clamp_position((new_x, new_y)))
            return

        # Priority 2 : attack enemie proche
        enemie_proche = min(ennemis, key=lambda e: unit.distance_to(e)) if ennemis else None
        if enemie_proche:
            if unit.is_in_range(enemie_proche):
                self.attack(unit, enemie_proche)
            else:
                safe_pos = self.clamp_position(enemie_proche.position)
                self.move_unit(unit, safe_pos)

    def L_behaviour(self, unit):
        """Pas d'aventages specials, attack le plus proche"""
        self.attack_near(unit)


    def S_behaviour(self, unit):
        """
        Skirmisher: kite + attack C > S > P > K 
        """
        ennemies = self.get_enemy_units()
        if not ennemies:
            return

        enemie_proche = min(ennemies, key=lambda e: unit.distance_to(e))
        if not enemie_proche or not enemie_proche.is_alive:
            return

        current_dist = unit.distance_to(enemie_proche)
        safe_distance = max(1.2, unit.range * 0.7)

        enemie_priority = ['C', 'S', 'P', 'K']
        enemies_in_range = [e for e in ennemies if e.is_alive and unit.is_in_range(e)]

        for type in enemie_priority:
            candidat = [e for e in enemies_in_range if e.type == type]
            if candidat:
                target = min(candidat, key=lambda e: (e.current_hp, unit.distance_to(e)))
                self.attack(unit, target)
                return

        if current_dist < safe_distance:
            if current_dist < safe_distance * 0.5:
                self.keep_dist_from(unit, enemie_proche, safe_distance)
                return

            retreat_x = unit.position[0] + (unit.position[0] - enemie_proche.position[0])
            retreat_y = unit.position[1] + (unit.position[1] - enemie_proche.position[1])
            retreat_pos = self.clamp_position((retreat_x, retreat_y))
            
            # kite kninght et pikeman
            for avoid_type in ["K", "P"]:
                if self.avoid(unit, dist=safe_distance, min_dist=safe_distance*0.5, avoid_type=avoid_type, intent=retreat_pos):
                    return

            dx, dy = unit.position[0] - enemie_proche.position[0], unit.position[1] - enemie_proche.position[1]
            dx_norm, dy_norm = normalize(dx, dy)
            step = 1.2
            safe_pos = self.clamp_position((unit.position[0] + dx_norm * step, unit.position[1] + dy_norm * step))
            self.move_unit(unit, safe_pos)
            return
        
        safe_pos = self.clamp_position(enemie_proche.position)
        self.move_unit(unit, safe_pos)
    
    def play_turn(self, unit ,turn):
        if not unit.is_alive:
            return
        
        if unit.type == "C":
            self.C_behaviour(unit)
        elif unit.type == "K":
            self.K_behaviour(unit)
        elif unit.type == "P":
            self.P_behaviour(unit)
        elif unit.type == "L":
            self.L_behaviour(unit)
        else:
            self.attack_near(unit) 