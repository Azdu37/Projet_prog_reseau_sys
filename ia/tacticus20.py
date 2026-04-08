from ia.base_general import General
import math

def normalize(x, y):
    mag = math.hypot(x, y)
    if mag < 1e-6:
        return 0.0, 0.0
    return x / mag, y / mag

class Behaviour3(General):
    """ each unit type behaves in a certain way """
    """ C maintains distance with all enemy units if possible, attacks units in range and moves towards closest enemy """
    """ K attacks enemys in range, moves towards nearest C while trying to avoid Ps in an area and keeps a min dist with any P if possible """
    """ P attacks enemys in range, moves towards nearest K  while trying to avoid Cs in an area and keeps a min dist with any C if possible """
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "tacticus 2.0"

    def attack_in_range(self,unit):
        """
        attacks units in range
        """
        enemy= self.find_closest_enemy(unit)
            
        if enemy is None or enemy.is_dead():
            return False
        
        if unit.is_in_range(enemy):

            self.attack(unit,enemy)
            return True


        return False


    def avoid(self, unit, dist, min_dist, type, intent,r):
        """avoids units of type that are in a dist**2 area while trying to move to 'intent', 
           trys to keep dist if such a unit is found in a min_dist**2 area """
        ux, uy = unit.position
        ix, iy = intent

        # Intended movement direction
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
            if enemy.is_dead() or enemy.type != type:
                continue
            if not self.map.is_in_tile(enemy, unit.position, dist):
                continue

            dx = ux - enemy.position[0]
            dy = uy - enemy.position[1]
            d2 = dx * dx + dy * dy

            if d2 < min_dist_2:
                return self.keep_dist_from(unit, enemy, min_dist)

            if d2 < (dist + enemy.size + unit.size) ** 2:
                dx, dy = normalize(dx, dy)
                weight = 1 / d2

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

        # Alignment check
        dot = intent_x * avoid_x + intent_y * avoid_y

        # If avoidance directly blocks intent sidestep
        if dot < -1:
            # perpendicular direction
            avoid_x, avoid_y = -avoid_y, avoid_x

            # choose side based on enemy center
            side = (ux - avg_x) * avoid_x + (uy - avg_y) * avoid_y
            if side < 0:
                avoid_x, avoid_y = -avoid_x, -avoid_y

        # Blend intent and avoidance
        final_x = intent_x + avoid_x*r
        final_y = intent_y + avoid_y*r
        final_x, final_y = normalize(final_x, final_y)

        new_x = ux + final_x * unit.speed
        new_y = uy + final_y * unit.speed

        self.move_unit(unit, (new_x, new_y))
        return True
    
    def N_S(self, unit, type):
        r=0
        for enemy in self.enemy_units:
            if enemy.is_dead() or enemy.type==type:
                continue
            if enemy.position[1] < unit.position[1]:
                r+=1
            else:
                r-=1 
        return r
    
    def E_W(self, unit, type):
        r=0
        for enemy in self.enemy_units:
            if enemy.is_dead() or enemy.type==type:
                continue
            if enemy.position[0] < unit.position[0]:
                r+=1
            else:
                r-=1 
        return r

    
    def keep_dist_from(self, unit, enemy,dist):
        
        dir_x= (unit.position[1] - enemy.position[1]) /dist
        dir_y= (unit.position[0] - enemy.position[0] )/dist 

        self.move_unit(unit , (dir_x *unit.speed + unit.position[0] , dir_y*unit.speed + unit.position[1]))
        return True
    
 
    
    def C_behaviour(self , C):
        """attack nearest enemey and trys to maintain a distance"""

        if self.keep_dist(C , C.range - 0.5):
            self.attack_in_range(C)
        else:
            self.attack_near(C)
        

    def K_behaviour(self , K):
        """move to closest CrossBow, attacks units in range, avoids pikes"""
        self.attack_in_range(K)


        closest_C = min(
            (u for u in self.enemy_units_dict["C"] if u.is_alive),
            key=lambda u: self.map.distance_2(K.position, u.position),
            default=None
            )
        if closest_C == None:
            self.attack_near(K)
            return None
        
        if self.avoid(K ,80 , 1.3 ,'P',closest_C.position,0.75)==False:
            self.move_unit(K, closest_C.position)
            return None
 
         
    def P_behaviour(self , P):
        """move to closest Pike, attacks units in LOS, avoids CrossBows"""
        self.attack_in_range(P)
 
        closest_K = min(
            (u for u in self.enemy_units_dict["K"] if u.is_alive),
            key=lambda u: self.map.distance_2(P.position, u.position),
            default=None
            )

        if closest_K is None:
            self.attack_near(P)
            return None
        if self.avoid(P ,20,0 ,'C',closest_K.position,0.8)==False:
            self.move_unit(P, closest_K.position)
            return None
            
            

       
    def initialize(self):
        return super().initialize()

    def play_turn(self , unit, turn):
         
        if unit.type == "C":
            self.C_behaviour(unit)
    

        elif unit.type == "K":
            self.K_behaviour(unit)


        elif unit.type == "P":
            self.P_behaviour(unit)

        elif unit.type == "L":
            self.P_behaviour(unit)

        elif unit.type == "S":
            self.S_behaviour(unit)  
        
    def L_behaviour(self, L):
            """Pas d'aventages special, attack le plus proche"""
            self.attack_near(L)

    def S_behaviour(self, S):
        """move to closest CrossBow, attacks units in range, avoids pikes"""
        self.attack_in_range(S)
        if self.keep_dist(S , S.range - 0.4):
            return self.attack_in_range(S)
        closest_C = min(
            (u for u in self.enemy_units_dict["C"] if u.is_alive),
            key=lambda u: self.map.distance_2(S.position, u.position),
            default=None
            )
        if closest_C == None:
            self.attack_near(S)
            return None
        
        if self.avoid(S , 50 , 7 ,'K',closest_C.position,0.5)==False:
            self.move_unit(S, closest_C.position)
            return None
 
        return None

    
             