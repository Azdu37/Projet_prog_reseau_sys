from ia.base_general import General
import math

def normalize(x, y):
    mag = math.hypot(x, y)
    if mag < 1e-6:
        return 0.0, 0.0
    return x / mag, y / mag

class CoordIA1(General):
    """
    priorité aux PV faibles, counter, dans la portée)
    - Knight: attaque dans la portée, avance vers les Crossbow ennemis, évite les Pikeman (vecteur d'évitement)
    - Pikeman: attaque dans la portée, avance vers les Knight ennemis, évite les Crossbow
    - Crossbowman: kite les melee, attaque le plus proche dans la portée, avance vers la cible si personne n'est là
    """

    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "coordia1"
        self.global_target = None
        self.last_update_turn = -1

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
        enemy = self.find_closest_enemy(unit)
        
        if enemy is None or not enemy.is_alive:
            return False
        
        if unit.is_in_range(enemy):
            self.attack(unit, enemy)
            return True
        
        return False
    
    def choisir_target(self):
        enemies = [e for e in self.enemy_units if e.is_alive]
        if not enemies:
            return None
        
        my_units = [u for u in self.my_units if u.is_alive]
        if not my_units:
            return None
        
        # best_target = min(enemies, key=lambda e: e.current_hp)
        # return best_target
    
        best_target = None
        best_score = -999999

        avg_x = sum(u.position[0] for u in my_units) / len(my_units)
        avg_y = sum(u.position[1] for u in my_units) / len(my_units)

        for enemy in enemies:
            score = 0

            #enemie HP faible
            hp_ratio = enemy.current_hp / enemy.max_hp
            score += (1 - hp_ratio) * 400

            #attaquer unit dans range
            units_can_hit = sum(1 for u in my_units if u.is_in_range(enemy))
            score += units_can_hit * 250

            #attaquer unit tres proche
            dist_to_center = math.hypot(enemy.position[0] - avg_x, enemy.position[1] - avg_y)
            score += max(0, 150 - dist_to_center)

            #attack crossbowman
            if enemy.type == 'C':
                score += 100

            if self.global_target and enemy == self.global_target and enemy.is_alive:
                score += 150

            if score > best_score:
                best_score = score
                best_target = enemy

        return best_target
    
    def play_turn(self, unit=None, turn=0):
        self.initialize()

        if not unit or not unit.is_alive:
            return

        # Mettre à jour la cible globale chaque tour
        if turn != self.last_update_turn:
            self.global_target = self.choisir_target()
            self.last_update_turn = turn

        if not self.global_target or not self.global_target.is_alive:
            self.global_target = self.choisir_target()

        enemies = [e for e in self.enemy_units if e.is_alive]
        if not enemies:
            return
        # crosbowman: kite + attaque dans range
        if unit.type == 'C':
            # Kite si des melee ennemis proches
            if self.keep_dist(unit, unit.range - 0.5):
                self.attack_in_range(unit)
            else:
                self.attack_near(unit)
            return
        
        # knight attaque dans range et avance vers Crossbow ennemi, évite Pikeman
        if unit.type == 'K':
            self.attack_in_range(unit)

            # Trouver le Crossbow le plus proche
            enemy_crossbowsman = [e for e in self.enemy_units if e.is_alive and e.type == 'C']
            if enemy_crossbowsman:
                crossbowman_proche = min(enemy_crossbowsman, key=lambda e: unit.distance_to(e))
                # Éviter Pikeman en avançant vers le Crossbow
                # if not self.avoid(unit, 50, 3, 'P', crossbowman_proche.position):
                #     self.move_unit(unit, crossbowman_proche.position)
                blocker = [e for e in self.enemy_units if e.is_alive and e.type in ['P', 'L', 'S'] and e.distance_to(unit) < crossbowman_proche.distance_to(unit)]
                if blocker:
                    target_block = min(blocker, key=lambda b: unit.distance_to(b))
                    if unit.is_in_range(target_block):
                        self.attack(unit, target_block)
                    else:
                        self.move_unit(unit, target_block.position)
                else:
                    self.move_unit(unit, crossbowman_proche.position)
            else:
                # Plus de Crossbow, utiliser attack_near
                self.attack_near(unit)
            return
        
        # pikeman attaque dans range et avance vers Knight ennemi, évite Crossbow
        if unit.type == 'P':
            self.attack_in_range(unit)

            # Trouver le Knight le plus proche
            enemie_knight = [e for e in self.enemy_units if e.is_alive and e.type == 'K']
            if enemie_knight:
                knight_proche = min(enemie_knight, key=lambda e: unit.distance_to(e))
                # Éviter les Crossbow en avançant vers le Knight
                if not self.avoid(unit, 20, 10, 'C', knight_proche.position):
                    self.move_unit(unit, knight_proche.position)
            else:
                # Plus de Knight, utiliser attack_near
                self.attack_near(unit)
            return

        if unit.type == 'L':
            enemy_knights = [e for e in self.enemy_units if e.is_alive and e.type == 'K']
            if enemy_knights:
                knight_proche = min(enemy_knights, key=lambda e: unit.distance_to(e))
                self.move_unit(unit, knight_proche.position)
                if unit.is_in_range(knight_proche):
                    self.attack(unit, knight_proche)
            else:
                self.attack_near(unit)
            return

        if unit.type == "S":
            if self.keep_dist(unit, unit.range - 0.5):
                # attack crossbowman, skirmisher, pikeman, knight hp faible
                priority = ['C', 'S', 'P', 'K']
                enemies_in_range = [e for e in self.enemy_units if e.is_alive and unit.is_in_range(e)]
                for t in priority:
                    candidates = [e for e in enemies_in_range if e.type == t]
                    if candidates:
                        target = min(candidates, key=lambda e: (e.current_hp, unit.distance_to(e)))
                        self.attack(unit, target)
                        return
            # si il n'y a pas dans range
            if self.global_target and self.global_target.is_alive:
                self.move_unit(unit, self.global_target.position)
            else:
                self.attack_near(unit)
            return

        # Fallback pour d'autres types d'unités
        self.attack_near(unit)
        
