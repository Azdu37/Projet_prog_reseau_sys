from math import sqrt,ceil
from battle.unit import Unit

class General:
    def __init__(self, team, game_map):
        """
        :param team: 'B' ou 'R' (Blue ou Red)
        :param game_map: L'instance de la classe Map
        """
        self.team = team
        self.map = game_map
        self.name = "Generic General"

        self.my_units= None
        self.enemy_units=None
        self.enemy_units_dict = {}
        self.my_units_dict = {}
    
    # ============================================================================
    # GESTION DES UNITÉS - Récupération et vérification
    # ============================================================================
    def initialize(self):
        "initialise les dictionaires d'unités"
        self.my_units = self.get_my_units()
        self.enemy_units = self.get_enemy_units()
        
        for type in ('K','C','P','L','S'):
            self.my_units_dict[type]=self.get_units_bytype(type)
        
        for type in ('K','C','P','L','S'):
            self.enemy_units_dict[type]=self.get_enemy_units_bytype(type)
        
    
    def _is_alive(self, unit: Unit)-> bool:
        """Vérifie si une unité est vivante"""
        if unit is None:
            return False
        if hasattr(unit, "is_alive"):
            return bool(getattr(unit, "is_alive"))
        if hasattr(unit, "is_dead"):
            try:
                return not unit.is_dead()
            except Exception:
                return True
        return True
    
    def get_my_units(self):
        """Récupère toutes les unités vivantes de mon équipe sur la carte"""
        my_units = []
        # parcourt les valeurs du dict de la map
        #  self.map.map est le dictionnaire {(x,y): Unit}
        for unit in self.map.map.values():
            if unit and isinstance(unit, Unit) and unit.team == self.team and unit.is_alive:
                my_units.append(unit)
        return my_units
    
    def get_enemy_units(self):
        """Récupère toutes les unités vivantes ennemies"""
        enemy_units = []
        for unit in self.map.map.values():
            if unit and isinstance(unit, Unit) and unit.team != self.team and unit.is_alive:
                enemy_units.append(unit)
        return enemy_units
    
    def get_units_bytype(self,type):
        """Récupère toutes les unités de type 'type' vivantes de mon équipe sur la carte"""
        my_typed_units = []
        for unit in self.map.map.values():
            if unit and unit.team == self.team and unit.is_alive and unit.type==type:
                my_typed_units.append(unit)
        return my_typed_units
    
    def get_enemy_units_bytype(self,type):
        """Récupère toutes les unités de type 'type' vivantes enemie sur la carte"""
        my_typed_units = []
        for unit in self.map.map.values():
            if unit and unit.team != self.team and unit.is_alive and unit.type==type:
                my_typed_units.append(unit)
        return my_typed_units
    
    # ============================================================================
    # GESTION DE LA CARTE - Ajout, retrait et déplacement d'unités
    # ============================================================================
    
    def move_unit(self, unit: Unit, dest):
        """Déplace une unité vers une destination donnée"""
        return self.map.move_unit(unit, dest)
    
    def move_unit_indir(self, unit: Unit, dir):
        x, y=unit.position
        dx, dy=dir
        if dir==(0,0):
            return False #c'est bizarre
        nx= x + dx*4
        ny= y + dy*4
        self.move_unit(unit,(nx,ny))
        return True
    
    def get_unit_in_range(self, unit:Unit, radius: float):
        """Retourne une liste des unités ennemies dans le rayon donné autour de l'unité spécifiée"""
        enemies_in_range = []
        for enemie in self.get_enemy_units():
            if unit.distance_to_2(enemie) <= radius**2:
                enemies_in_range.append(enemie)
        return enemies_in_range
    
    def get_visibles_enemies(self, enemie: Unit):
        return self.get_unit_in_range(enemie, enemie.line_of_sight) 

    # ============================================================================
    # SÉLECTION DE CIBLES - Recherche d'ennemis à attaquer
    # ============================================================================

    def find_closest_enemy(self, unit, dist=None):
        """Trouve l'unite ennemie la plus proche d'une unité donnée"""
        closest = None
        min_dist2 = float('inf') 
        enemies = self.enemy_units
        dist2_fn = unit.distance_to_2
        for enemy in  enemies:
            if not enemy.is_alive:
                continue
            if dist is not None and not self.is_in_tile(unit, enemy.position, dist):
                continue
            dist2 = dist2_fn(enemy)  
            if dist2 < min_dist2:
                min_dist2 = dist2
                closest = enemy
                
        return closest
    
    def is_in_tile(self,unit,position,tile_size):
        ux, uy = unit.position
        tx, ty = position

        # Check overlap in X and Y separately
        margin = tile_size + unit.size 
        return  ((ty - margin < uy < ty + margin) and (tx - margin < ux < tx + margin) )
    
        
    def find_lowest_hp_enemy(self, enemies=None):
        """Trouve l'unité ennemie avec le moins de points de vie"""
        enemies = self.get_enemy_units() if enemies is None else enemies
        return min(enemies, key=lambda e: e.current_hp, default=None)
    
    def keep_dist(self,unit,dist):
        enemie = self.find_closest_enemy(unit,dist)
        if enemie is None:
            return False
        if self.map.distance_2(unit.position , enemie.position) < (dist + enemie.size + unit.size)**2 :
            dir_x= unit.position[0] - enemie.position[0]
            dir_y= unit.position[1] - enemie.position[1]
            move_atr= (dir_x + unit.position[0] , dir_y + unit.position[1])
            self.move_unit(unit , move_atr)
            return True
        return False

    def attack(self,unit,target):
        return self.map.attack2(unit , target)
    
    def attack_in_range(self,unit):
        """
        attacks units in range
        """
        enemy= self.find_closest_enemy(unit)
            
        if enemy is None or enemy.is_dead():
            return False
        
        if unit.is_in_range(enemy):

            self.attack(unit, enemy)
            return True


        return False
    
    def attack_in_LOS(self,unit):
        """
        BRAIN DEAD's main method  -modified returns-
        """
        if unit.is_dead():
            return False
        
  
        enemy= self.find_closest_enemy(unit,unit.line_of_sight)
            
        if enemy is None:
            return False
        
        if unit.is_in_LOS(enemy):
            if unit.range_min !=0 and self.keep_dist(unit,unit.range_min+0.8) :
                return enemy
            # si l'unite est a  portée, attaque
            if unit.is_in_range(enemy):
                self.attack(unit ,enemy)
                return True
            
            self.map.move_unit(unit, enemy.position)
            return True

        return False
    

    def attack_near(self, unit,B=False):
        """
        Attaque l'unité ennemie la plus proche, ou se déplace vers elle.
        """
        if not unit.is_alive:
            return None
        
        enemy = self.find_closest_enemy(unit)
        if enemy is None or not enemy.is_alive:
            return None
        
        # si l'unite est deja en portée, attaque
        if unit.is_in_range(enemy):
            self.attack(unit, enemy)
            return enemy

        # sinon, se deplacer vers l'enemie
        
        #self.sic(unit, enemies)
        if B == False:
            if unit.range_min !=0 and self.keep_dist(unit,unit.range_min+0.8) :
                return enemy
            self.map.move_unit(unit, enemy.position)

        return enemy
    

    def attack_near_iftype(self, unit, type):
        """
        Attaque l'unité ennemie la plus proche si elle est de type "type" , ou se déplace vers elle.
        """
        if not unit.is_alive:
            return False
        
        enemy = self.find_closest_enemy(unit)
        if enemy is None or not enemy.is_alive or enemy.type != type:
            return False
        
        # si l'unite est deja en portée, attaque
        if unit.is_in_range(enemy):
            self.attack(unit, enemy)
            return True

        # sinon, se deplacer vers l'enemie
        
        #self.sic(unit, enemies)
 
        self.map.move_unit(unit, enemy.position)
        return True
    
    def find_best_enemies(self, unit: Unit, n: int =3, distance_weight: float = 0.5):
        """
        Retourne une liste des n ennemis 'meilleurs' à cibler, triés par un score heuristique.
        Ici, score est un calcul base sur l'offense, les points de vie et la distance :
        Score = (offense / hp) + distance_weight * (1 / (1 + distance))
        n : nombre d'ennemis à retourner
        distance_weight : poids de la distance dans le score
        on utilise Heuristics pour évaluer les cibles.
        """
        enemies = self.get_enemy_units()
        if not enemies:
            return []

        # fonction score pour calculer le score d'un ennemi
        def score(enemy: Unit) -> float:
            # calcul de l'offense et des hp
            attacks = getattr(enemy, "attacks", {})
            offense = sum(attacks.values()) if isinstance(attacks, dict) else 0
            
            hp = max(1.0, getattr(enemy, "current_hp", getattr(enemy, "max_hp", 1.0)))
            base = offense / hp
            
            try:
                dist = unit.distance_to(enemy)
            except Exception:
                dist = float("inf")
            proximity = 1.0 / (1.0 + dist)
            return base + distance_weight * proximity

        #sorted_enemies = sorted(enemies, key=score, reverse=True)
        sorted_enemies = enemies.copy()
        sorted_enemies.sort(key=score, reverse=True)
        return sorted_enemies[:max(0, n)]

    def find_best_target(self, enemie: Unit):
        """Trouver la meilleur enemie"""
        best_enemies = self.find_best_enemies(enemie, n=1)
        return best_enemies[0] if best_enemies else None 

        if closest_enemy:
            if unit.is_in_range(closest_enemy):
                
                unit.attack(closest_enemy)
            else:
                # Utilise la méthode sic (interception) pour se déplacer vers l'ennemi
               # self.sic(unit, closest_enemy)
               self.map.move_unit(unit,closest_enemy.position)
        return None
    
    

    def sic(self, falcon, bandit):
        """Déplace une unité (falcon) sur une trajectoire de collision avec une autre unité (bandit), si impossible trajectoire de meilleur approche"""
        """ET Retourn une estimation du nombre de tours qu'il faut pour atteindre la cible 
        (0 -> impossible d'intercepter,  1+ -> cible atteignable/atteinte ) """
        
        ### REMARQUE: changer la vitesse des unites dans move_unit change les valeurs de 't' proportionnellement, peut ettre rectifier avec R ###
        R = 1   #   = R de move_unit
        
        fx, fy = falcon.position
        f_speed = falcon.speed *R
        
        bx, by= bandit.position
        b_speed = bandit.speed *R

        if bandit.direction==None: #direction d'unité mal initialisé considerer immobile (direction doit etre (0,0) au debut)
            self.map.move_unit (falcon,(bx,by))
            return ceil( sqrt( (fx-bx)**2 + (fy-by)**2 )/f_speed)

        dx ,dy= bandit.direction

        if dx==0 and dy==0: #bandit immobile
            if self.map.distance((fx,fy),(bx,by))<=(bandit.size+falcon.size):
                return 1
            self.map.move_unit (falcon,(bx,by))
            return ceil( sqrt( (fx-bx)**2 + (fy-by)**2 )/f_speed)
        
        # Vecteur de falcon-bandit
        rx = bx - fx
        ry = by - fy

        #si la directon de bandit et le vecteur f-b sont alligner il suffit de se deplacer directment a la position bandit
        nrx=rx/sqrt( (fx-bx)**2 + (fy-by)**2)
        nry=ry/sqrt( (fx-bx)**2 + (fy-by)**2)
       
        if ((nrx-dx<1e-3 and nrx-dx>-1e-3)and(nry-dy<1e-3 and nry-dy>-1e-3)): #  (falcon)-> <-(bandit)
            self.map.move_unit(falcon,bandit.position)
            return ceil( sqrt( (fx-bx)**2 + (fy-by)**2 )/f_speed+b_speed)
       
        if ((nrx+dx<1e-3 and nrx+dx>-1e-3)and(nry+dy<1e-3 and nry+dy>-1e-3)): #  (falcon)-> (bandit)->
            self.map.move_unit(falcon,bandit.position)
            return max(0, ceil(sqrt((fx-bx)**2 + (fy-by)**2) / f_speed - b_speed))
        

       # Coefficients de l'équation quadratique a*t² + b*t + c = 0
        a = (b_speed*dx)**2 + (b_speed*dy)**2 - f_speed**2
        b = 2 * (rx * b_speed*dx + ry * b_speed*dy)
        c = rx**2 + ry**2         
        
        discriminant = b**2 - 4*a*c

        t = None
        if discriminant >= 0:
            # Il y a une solution réelle
            sqrt_disc = sqrt(discriminant)
            if a != 0:
                t1 = (-b - sqrt_disc) / (2*a)
                t2 = (-b + sqrt_disc) / (2*a)
            
              # Prendre le temps positif le plus petit
                if t1 > 1e-4 and t2 > 1e-4:   
                   t = min(t1, t2)

                elif t1 > 1e-4:
                   t = t1

                elif t2 > 1e-4:
                   t = t2

            else:
               # Cas dégénéré (a = 0) - équation linéaire
                if b != 0:
                    t = -c / b
                    if t < 1e-4: # closest approach if exact interception impossible ()
                        W = (b_speed*dx)**2 + (b_speed*dy)**2
                        if W > 1e-4:
                            t_ca = -(rx*(b_speed*dx) + ry*(b_speed*dy)) / W
                        if t_ca < 1e-4:
                            t_ca = 0
                        else:
                            t_ca = 0
                        t = t_ca
        if t is None:
            W = (b_speed*dx)**2 + (b_speed*dy)**2
            if W > 1e-4:
                t_ca = -(rx*(b_speed*dx) + ry*(b_speed*dy)) / W
                if t_ca < 0: t_ca = 0
                t = t_ca
            else:
                t = 0

        dest_x = bx + (b_speed*dx) * t
        dest_y = by + (b_speed*dy) * t
        self.map.move_unit(falcon, (dest_x, dest_y))
        return ceil(t)
        

    def update_perception(self):
        """Met a jour la perception de l'ia en recupererant les unites ennemies et alliees"""
        self.my_units = self.get_my_units()
        self.enemy_units = self.get_enemy_units()
    
    def evalute_battle_state(self):
        """Retourne une state de battle winning/ losing/ even"""
        my_hp = sum(unit.current_hp for unit in self.get_my_units())
        enemy_hp = sum(enemie.current_hp for enemie in self.get_enemy_units())
        if my_hp>enemy_hp*1.3:
            """si my hp est plus de 30% superieur a enemy hp on est winning"""
            return "winning"
        elif enemy_hp>my_hp*1.3:
            return "losing"
        else: 
            return "even"
        
    def decide_global_stragety(self):
        """Decide une stragety global pour l'ia en fonction de evalute_battle_state"""
        state = self.evalute_battle_state()
        if state == "winning":
            self.strategy = "attack"
        elif state == "lossing":
            self.strategy  = "defend"
        else: 
            self.strategy = "blanced"    
    
    def play_turn(self,unit, turn):
        """
        Méthode à surcharger par les classes filles.
        C'est ici que l'IA prend ses décisions à chaque tour.
        """
        raise NotImplementedError("Cette méthode doit être implémentée par les sous-classes")

