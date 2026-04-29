from collections import defaultdict
import random
import os
from math import sqrt, atan2
from battle.unit import Unit
from battle.projectile import Projectile
from battle.scenario import Scenario


class Map:
    def __init__(self, p=50, q=50):
        """Initialise une carte de taille p x q"""
        self.p = p
        self.q = q
        self.map = defaultdict(lambda: None, {})
        self.projectiles = []
        self.engine = None

    def distance(self, pos1, pos2):
        """Calcule la distance entre deux positions"""
        return sqrt((pos1[0] - pos2[0]) ** 2 + abs(pos1[1] - pos2[1]) ** 2)

    def distance_2(self, pos1, pos2):
        """Calcule la distance entre deux positions"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return dx * dx + dy * dy

    def is_in_tile(self, unit, tile_pos, tile_size):
        """checks if unit touching a (2*tile_size)**2 square centered on tile_pos"""
        ux, uy = unit.position
        tx, ty = tile_pos

        # Check overlap in X and Y separately
        margin = tile_size + unit.size
        return (ty - margin < uy < ty + margin) and (tx - margin < ux < tx + margin)

    marge = 1.01  # Facteur de marge pour la détection de collision (pour éviter que les unités se touchent de trop près)

    def add_unit(self, x, y, type, team):
        """Permet d'ajouter une unité à la carte aux coordonnées (x, y)"""
        unit = Unit().get_by_type(type, team, (x, y))
        if unit.size <= x < self.p - unit.size and unit.size <= y < self.q - unit.size:
            for pos, other_unit in self.map.items():
                if other_unit is not None:
                    dist = self.distance((x, y), pos)
                    if dist < self.marge * (unit.size + other_unit.size):
                        return  # Collision détecté, n'ajoute pas l'unité
            self.map[(x, y)] = Unit().get_by_type(type, team, (x, y))

    #def get_unit(self, x, y):
    #    """Permet de récupérer l'unité à la position (x, y)"""
    #    return self.map.get((x, y), None)

    def remove_unit(self, x, y):
        """Permet de retirer l'unité à la position (x, y)"""
        if (x, y) in self.map:
            self.map.pop((x, y), None)

    def remove_unit_instance(self, unit):
        """Retire une unite precise de la carte."""
        self.map.pop(unit.position, None)
        for pos, other_unit in list(self.map.items()):
            if other_unit is unit:
                self.map.pop(pos, None)

    def load(self, scenario_name):
        """"Charge une carte depuis un scénario donné ou un fichier de sauvegarde"""

        if "lanchester" in scenario_name:
            self.load_lanchester(scenario_name)
        elif "save" in scenario_name:
            self.load_file(scenario_name)
        else:
            self.load_scenario(scenario_name)

    def load_scenario(self, scenario_name):
        """"Charge une carte depuis un scénario donné"""

        size, scenario = Scenario().get_list_by_name(scenario_name)
        newp, newq = size
        self.p, self.q = newp, newq
        for x, y, type in scenario:
            self.add_unit(x, y, type, 'R')
            self.add_unit(self.p - x, y, type, 'B')

    def load_lanchester(self, scenario_name):
        """"Charge une carte depuis un scénario de type lanchester donné"""

        size, scenario = Scenario().get_list_by_name(scenario_name)
        newp, newq = size
        self.p, self.q = newp, newq
        for x, y, type in scenario:
            if x < self.p // 2:
                self.add_unit(x, y, type, 'R')
            else:
                self.add_unit(x, y, type, 'B')

    #############################
    # Partie Gestion de Fichier #
    #############################

    def load_file(self, name="autosave"):
        self.marge = 0  # Désactive la marge de collision lors du chargement
        """"Charge une carte depuis un fichier texte"""
        name = name[:-5] if name.endswith("_save") else name
        with open(f"data/save/{name}_save.txt", "r") as f:
            data = f.read().split("\n")

            line = data[0].split(',')
            self.p, self.q = int(line[0]), int(line[1])

            for line in data[1:]:
                line = line.split(',')
                if len(line) < 4:
                    continue
                self.add_unit(float(line[0]), float(line[1]), line[2], line[3])

        if os.path.exists(f"data/savedata/{name}_data.txt"):
            with open(f"data/savedata/{name}_data.txt", "r") as f:
                data = f.read().split("\n")

                for line in data:
                    line = line.split(',')
                    if len(line) < 7:
                        continue
                    pos = (float(line[0]), float(line[1]))
                    self.map[pos].current_hp = float(line[2])
                    self.map[pos].is_alive = line[4].lower() == "true"
                    self.map[pos].state = line[5]
                    self.map[pos].time_until_next_attack = float(line[6])

                for line in data:
                    line = line.split(',')
                    if len(line) < 9:
                        continue
                    pos = (float(line[0]), float(line[1]))
                    if float(line[7]) == -1 and float(line[8]) == -1:
                        self.map[pos].target = None
                    else:
                        self.map[pos].target = self.map.pop((float(line[7]), float(line[8])), None)
        self.marge = 1.01  # Réactive la marge de collision après le chargement

    def save_file(self, scenario="stest1", ia1="major_daft", ia2="major_daft", name="autosave"):
        """Sauvegarde la carte actuelle dans un fichier texte"""
        with open(f"data/save/{name}_save.txt", "w") as f:
            f.write(f"{self.p},{self.q}\n")
            for (x, y), unit in self.map.items():
                f.write(f"{x},{y},{unit.type},{unit.team}\n")

        with open(f"data/savedata/{name}_engine_data.txt", "w") as f:
            f.write(f"{scenario},{ia1},{ia2}\n")

        with open(f"data/savedata/{name}_data.txt", "w") as f:
            for (x, y), unit in self.map.items():
                if unit.target is not None:
                    a, b = unit.target.position[0], unit.target.position[1]
                else:
                    a, b = -1, -1
                f.write(
                    f"{x},{y},{unit.current_hp},{unit.is_alive},{unit.state},{unit.time_until_next_attack},{a},{b}\n")

    def __repr__(self):
        return f"Map({repr(self.map)})"

    #############################
    #  Partie Mouvement Unités  #
    #############################

    def maj_unit_posi(self, unit, dest):
        """changement de position sur map"""
        self.map.pop(unit.position, None)  # Retire l'unité de sa position actuelle
        self.map[dest] = unit  # Place l'unité à sa nouvelle position
        unit.position = dest  # MaJ attribue de unit

    def move_unit(self, unit, dest, depth=0, R=1 / 60):

        """Permet de déplacer une unité dans la direction de dest, légalement avec résolution des collisions"""

        if unit.state == "attacking":
            unit.direction = (0, 0)
            return False

        if depth > 3:  # recurtion depth limit
            #print(depth)
            unit.direction = (0, 0)  # mettre a jour la direction
            return None

        unit_position_x = unit.position[0]
        unit_position_y = unit.position[1]
        speed = unit.speed * R

        """if unit.destination == dest:
            dir_x = unit.direction[0]
            dir_y = unit.direction[1]
            x_step = speed * dir_x
            y_step = speed * dir_y
            
            next_x = unit_position_x + x_step
            next_y = unit_position_y + y_step

            next_pos = (next_x, next_y)
            coll_dir = self.collision(unit, next_pos, depth)
            if coll_dir != (0, 0):  # Collision detected

                intended_dir = (dir_x , dir_y)

                self.collision_resolution( unit, intended_dir, coll_dir, depth)
            else:
                next_x = unit_position_x + x_step
                next_y = unit_position_y + y_step
                next_pos = (next_x, next_y)
                self.maj_unit_posi(unit, next_pos)
            return None
        
        unit.destination = dest"""
        """if unit.state == "reloading":
            speed /= 2"""

        dist_2 = self.distance_2(unit.position, dest)

        if dist_2 < 1e-8:  #  <---- /!\ Precision**2 de la fonction /!\
            unit.direction = (0, 0)
            return None

        # Calcul de déplacement
        dist = sqrt(dist_2)
        dir_x = (dest[0] - unit_position_x) / dist
        dir_y = (dest[1] - unit_position_y) / dist

        x_step = speed * dir_x
        y_step = speed * dir_y

        next_x = unit_position_x + x_step
        next_y = unit_position_y + y_step

        next_pos = (next_x, next_y)

        coll_dir = self.collision(unit, next_pos, depth)
        if coll_dir != (0, 0):  # Collision detected

            intended_dir = (dir_x, dir_y)

            self.collision_resolution(unit, intended_dir, coll_dir, depth)
        else:
            next_x = unit_position_x + x_step
            next_y = unit_position_y + y_step
            next_pos = (next_x, next_y)
            self.maj_unit_posi(unit, next_pos)

            unit.state = "moving"
            unit.direction = (dir_x, dir_y)  # mettre a jour la direction
            if depth == 0:
                angle = atan2(dir_y, dir_x) + 3.15
                unit.orientation = (round(angle * 8 / 6.28) + 3) % 8
        return None

    def collision_resolution(self, unit, intended_dir, coll_dir, depth):
        """Calcule nouvelle destination, rappel move_unit avec depth+1 """
        speed = unit.speed

        dir_x, dir_y = intended_dir
        cx, cy = coll_dir

        dot = dir_x * cx + dir_y * cy
        var_condi = 0.98  #Arbitrairement choisi (a discuter)

        if abs(dot) > var_condi:  # collision frontal              # normalement jamais proche de +1
            #[? a remplacer par condition heuristique ?]

            if unit.team == 'B':  # rotaion anti-symetrique pour chaque equipe, sinon c'est pas fairplay
                new_x = dir_y * speed
                new_y = -dir_x * speed
            else:
                new_x = -dir_y * speed
                new_y = dir_x * speed

            self.move_unit(unit, (unit.position[0] + new_x, unit.position[1] + new_y), depth + 1)
            return None

        else:
            """if dot > 1e-2: # essay de traverser une unit (
                #nouveau vect de colision (Symétrie Transversale du vect de collision par rapposrt au vect de direction du move)
                proj_x = dir_x*dot
                proj_y = dir_y*dot
                cx = -2 * proj_x + cx
                cy = -2 * proj_y + cy"""

            new_x = (dir_x + cx)
            new_y = (dir_y + cy)
            mag = sqrt(new_x ** 2 + new_y ** 2)
            new_y *= speed / mag
            new_x *= speed / mag
            self.move_unit(unit, (unit.position[0] + new_x * 0.9, unit.position[1] + new_y * 0.9), depth + 1)
            return None

    def collision(self, unit, dest, depth):
        r"""
        Vérifie si une unité entrerait en collision avec une autre unité à la destination donnée
        renvoie (dx,dy) direction normalisée de la collision, sinon renvoie (0,0), convention du signe : (point_contact → dest)
            / \ Push feature : en cas de collisions la fonction appel move_unit
           / ! \ sur l'unité detectée (si equipe =)
          /_____\ dans la direction [ -1 * (dx, dy) ] et avec depth += 1
        """

        # Vérifie chaque unité sur la carte
        is_in_tile = self.is_in_tile
        dest_x = dest[0]
        dest_y = dest[1]
        unit_size = unit.size
        unit_team = unit.team
        for pos, other_unit in self.map.items():

            # Ignore: l'unité elle-même/ les unités mortes / les autres types d'objets sur la map / les unités hors d'un carré qui encadre unit
            if other_unit is unit or not other_unit.is_alive or not is_in_tile(other_unit, dest, unit.size):
                continue

            dist_2 = self.distance_2(dest, pos)

            if dist_2 < (unit_size + other_unit.size) ** 2:
                # Calcul du vecteur direction de la collision
                # (de la destination vers l'autre unité)
                dx = dest_x - other_unit.position[0]
                dy = dest_y - other_unit.position[1]

                # Éviter le vecteur nul 
                if dx == 0 and dy == 0:
                    dx, dy = 0, 1  #arbitrairement j'ai choisi de considerer ca comme une colision depuis le SUD
                    return dx, dy

                #magnitude = sqrt(dist_2)
                magnitude_ap = other_unit.size + unit_size - 0.004730380396617299
                dx /= magnitude_ap
                dy /= magnitude_ap

                #push mechanics
                if depth < 3 and other_unit.team == unit_team:
                    r = (unit_size / other_unit.size)
                    other_unit_dest = (other_unit.position[0] - (dx * r), other_unit.position[1] - (dy * r))
                    self.move_unit(other_unit, other_unit_dest, depth + 1)
                return dx, dy  # Collision détectée avec sa direction

        # Vérifier si la destination est hors de la carte
        if dest[0] < 0 or dest[0] >= self.p or dest[1] < 0 or dest[1] >= self.q:
            #     N:(0,1) / S:(0,-1) / E(1,0) / W(-1,0)
            #  quatre coins
            if dest[0] < 0 and dest[1] < 0: return 0.7071, 0.7071  # (SW)
            if dest[0] > self.p and dest[1] < 0: return - 0.7071, 0.7071  # (SE)
            if dest[0] < 0 and dest[1] >= self.q: return 0.7071, - 0.7071  # (NW)
            if dest[0] > self.p and dest[1] >= self.q: return - 0.7071, - 0.7071  # (NE)
            # les quatres bord
            if dest[0] < 0 or dest[0] >= self.p: return (1, 0) if dest[0] < 0 else (-1, 0)  # (E ou W)
            if dest[1] < 0 or dest[1] >= self.q: return (0, 1) if dest[1] < 0 else (-1, 0)  # (N ou S)
        return 0, 0  # Pas de collision

    ########################################################
    #  Partie Projectiles et fonction attack(unit,target)  #
    ########################################################

    def attack2(self, unit, target):
        # En mode réparti, seules les unités locales déclenchent réellement les attaques
        if hasattr(unit, 'is_local') and not unit.is_local:
            return None
        engine = getattr(self, "engine", None)
        if engine is not None and getattr(engine, "is_distributed", False) and target.owner_id != engine.get_local_peer_id():
            if not engine.request_network_ownership(target):
                return engine.queue_network_action(unit, target, "attack")
        if not unit.can_attack(target):
            return None  # Ne peut pas attaquer
        if unit.time_before_next_attack > 0:
            unit.state = "attacking"
            angle = atan2(target.position[1] - unit.position[1], target.position[0] - unit.position[0]) + 3.15
            unit.orientation = (round(angle * 8 / 6.28) + 3) % 8
            return False
        # commence l'attaque
        unit.state = "attacking"
        unit.target = target

        angle = atan2(target.position[1] - unit.position[1], target.position[0] - unit.position[0]) + 3.15
        unit.orientation = (round(angle * 8 / 6.28) + 3) % 8

        if unit.type == 'C' or unit.type == 'S':
            unit.time_until_next_attack = unit.reload_time
            self.fire_projectile(unit, target)
            unit.time_reset()
            return None

        unit.time_reset()
        target.take_damage(unit)

        # set cooldown

        return

    def fire_projectile(self, shooter, target):
        type = shooter.type

        if target.direction == (0, 0):

            target_pos = target.position
            if random.random() < 0.15:
                rng = random.uniform(1.2, 2.5) * random.choice([-1, 1])
                target_pos = (
                    target_pos[0] + rng,
                    target_pos[1] + rng * random.choice([-1, 1])
                )
            if type == 'C':
                return self.add_Arrow(shooter, target_pos, self.distance(shooter.position, target_pos))
            if type == 'S':
                return self.add_Lance(shooter, target_pos, self.distance(shooter.position, target_pos))
        bx, by = target.position
        fx, fy = shooter.position

        # Calcul des vecteurs de vitesse de la cible
        dx, dy = target.direction
        target_vx = dx * target.speed
        target_vy = dy * target.speed

        # Vecteur (Target - Shooter)
        rel_x = bx - fx
        rel_y = by - fy

        # Vitesse de la flèche
        if type == 'C':
            Projectile_speed = 10  # Doit être > target.speed pour garantir l'interception
        if type == 'S':
            Projectile_speed = 7  #calcule diff par unité
        # Équation quadratique : a*t² + b*t + c = 0
        a = target_vx ** 2 + target_vy ** 2 - Projectile_speed ** 2
        b = 2 * (rel_x * target_vx + rel_y * target_vy)
        c = rel_x ** 2 + rel_y ** 2

        discriminant = b ** 2 - 4 * a * c
        t = None

        if discriminant >= 0:
            sqrt_disc = sqrt(discriminant)
            t1 = (-b - sqrt_disc) / (2 * a)
            t2 = (-b + sqrt_disc) / (2 * a)

            # On cherche le plus petit temps positif
            times = [t for t in [t1, t2] if t > 0]
            if times:
                t = min(times)

        # Si pas de solution
        if t is None:
            # On vise la position actuelle par défaut
            target_pos = (bx, by)
        else:
            # Calcul de la position future
            target_pos = (bx + target_vx * t, by + target_vy * t)
        if random.random() < 0.25:
            rng = random.uniform(1.2, 3) * random.choice([-1, 1])
            target_pos = (
                target_pos[0] + rng,
                target_pos[1] + rng * random.choice([-1, 1])
            )

        if type == 'C':
            return self.add_Arrow(shooter, target_pos, self.distance(shooter.position, target_pos))
        if type == 'S':
            return self.add_Lance(shooter, target_pos, self.distance(shooter.position, target_pos))

    def maj_proj_posi(self, proj, dest):
        """changement de position de projectiles sur map"""
        # Place le projectile à sa nouvelle position

        proj.position = dest
        proj.travel_dist += proj.speed / 60

    def add_Arrow(self, shooter, target_pos, distance):
        """Permet d'ajouter une flèche à la carte aux coordonnées (x, y)"""
        self.projectiles.append(Projectile().arrow(shooter, target_pos, distance))

    def add_Lance(self, shooter, target_pos, distance):
        """Permet d'ajouter une flèche à la carte aux coordonnées (x, y)"""
        self.projectiles.append(Projectile().lance(shooter, target_pos, distance))

    def update_projectiles(self):
        """checks for hits. if none, continues trajectory"""
        projectiles_to_remove = []

        for projectile in self.projectiles:
            if getattr(projectile, "consumed", False):
                projectiles_to_remove.append(projectile)
                continue
            if getattr(projectile, "pending_hit", None) is not None:
                continue

            # Calcul de déplacement
            if self.hit(projectile) or projectile.travel_dist >= projectile.range:
                projectiles_to_remove.append(projectile)
                continue

            x_step = projectile.speed * projectile.direction[0] / 60
            y_step = projectile.speed * projectile.direction[1] / 60

            next_x = projectile.position[0] + x_step
            next_y = projectile.position[1] + y_step

            next_pos = (next_x, next_y)
            self.maj_proj_posi(projectile, next_pos)

        for proj in projectiles_to_remove:
            self.destroy_projectile(proj)

    def destroy_projectile(self, projectile):
        self.projectiles.remove(projectile)

    def hit(self, projectile):
        px, py = projectile.position
        for (x, y), unit in self.map.items():
            # Ignore: l'unité elle-même/ les unités mortes / les autres types d'objets sur la map / les unités hors d'un carré 5*5 centré sur le projectile 
            if abs(x - px) > 2 or abs(y - py) > 2:
                continue
            if not unit.is_alive or unit.team == projectile.shooter.team:
                continue

            dist_2 = self.distance_2((px, py), (x, y))

            if dist_2 < (unit.size) ** 2:
                # En mode réparti, seule une munition tirée par une unité locale applique les dégâts
                if not hasattr(projectile.shooter, 'is_local') or projectile.shooter.is_local:
                    engine = getattr(self, "engine", None)
                    if engine is not None and getattr(engine, "is_distributed", False) and unit.owner_id != engine.get_local_peer_id():
                        if not engine.request_network_ownership(unit):
                            projectile.pending_hit = unit
                            engine.queue_network_action(projectile.shooter, unit, "projectile_hit", {"projectile": projectile})
                            return False
                    unit.take_damage(projectile.shooter)
                return True

        return False

    def get_unit(self, x, y):
        """Permet de récupérer l'unité à la position (x, y)"""
        return self.map.get((x, y), None)

    def get_projectiles(self):
        return [obj for obj in self.map.values() if isinstance(obj, Projectile)]
