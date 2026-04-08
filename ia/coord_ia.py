from ia.base_general import General

class CoordIA(General):
    """
     Phase 1 : Toutes les unités attaquent les Knights ennemis (casser la frontline)
    Phase 2 : Les Knights chassent les Crossbows, les Crossbows tirent à portée,
                les Pikes combattent les Pikes
    Pas de percée de frontline, pas de suicide
    """
    
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "coordia"

    def play_turn(self, unit=None, turn=0):
        self.initialize()

        if not unit or not unit.is_alive:
            return

        enemy_knights = [e for e in self.enemy_units if e.is_alive and e.type == 'K']
        enemy_pikeman = [e for e in self.enemy_units if e.is_alive and e.type == 'P']
        enemy_crossbowman = [e for e in self.enemy_units if e.is_alive and e.type == 'C']
        enemy_skirmisher = [e for e in self.enemy_units if e.is_alive and e.type == 'S']

        enemies = [e for e in self.enemy_units if e.is_alive]
        if not enemies:
            return

        # target = min(enemies, key=lambda e: unit.distance_to(e))

        target = None

        # Casser la fronline
        if enemy_knights:
            target = min(enemy_knights, key=lambda k: unit.distance_to(k))

            if unit.distance_to(target) > 30 and enemy_pikeman:
                pike_target = min(enemy_pikeman, key=lambda p: unit.distance_to(p))
                if unit.distance_to(pike_target) < unit.distance_to(target):
                    target = pike_target
        # else:
        #     target = min(enemies, key=lambda e: unit.distance_to(e))
        else:
            if unit.type == 'K':
                if enemy_crossbowman:
                    target = min(enemy_crossbowman, key=lambda c: unit.distance_to(c))
                elif enemy_pikeman:
                    target = min(enemy_pikeman, key=lambda p: unit.distance_to(p))

            elif unit.type == 'C':
                enemies_in_range = [
                    e for e in self.enemy_units
                    if e.is_alive and unit.is_in_range(e)
                ]
                if enemies_in_range:
                    target = min(
                        enemies_in_range,
                        key=lambda e: (e.current_hp, unit.distance_to(e))
                    )

            elif unit.type == 'P':
                if enemy_pikeman:
                    target = min(enemy_pikeman, key=lambda p: unit.distance_to(p))
                elif enemy_crossbowman:
                    target = min(enemy_crossbowman, key=lambda c: unit.distance_to(c))
            
            elif unit.type == "L":
                if enemy_knights:
                    target = min(enemy_knights, key=lambda k: unit.distance_to(k))
                else:
                    target = min(enemies, key=lambda e: unit.distance_to(e))

            elif unit.type == "S":
                # skirmisher attack crossbowman enemie, skirmisher enemie et apres pikeman, knight
                enemies_in_range = [
                    e for e in self.enemy_units
                    if e.is_alive and unit.is_in_range(e)
                ]
                priority = ['C', 'S', 'P', 'K']
                for t in priority:
                    candidat = [e for e in enemies_in_range if e.type == t]
                    if candidat:
                        target = min(candidat, key=lambda e: (e.current_hp, unit.distance_to(e)))
                        break
                    
        if not target:
            all_enemies = [e for e in self.enemy_units if e.is_alive]
            if all_enemies:
                target = min(all_enemies, key=lambda e: unit.distance_to(e))

        if not target:
            return


        # if unit.is_in_range(target):
        #     self.attack(unit, target)
        # else:
        #     self.move_unit(unit, target.position)

        if unit.type == 'C':
            # trouve enemie Kninght, Pikeman
            enemie_melee = [e for e in self.enemy_units if e.is_alive and e.range == 0]
            if enemie_melee:
                enemie_proche = min(enemie_melee, key=lambda e: unit.distance_to(e))
                if unit.distance_to(enemie_proche) < unit.range * 0.75:
                    self.keep_dist(unit, unit.range * 0.75)

            if unit.is_in_range(target):
                self.attack(unit, target)
            else:
                self.attack_near(unit)
        else:
            if unit.is_in_range(target):
                self.attack(unit, target)
            else:
                self.move_unit(unit, target.position)
