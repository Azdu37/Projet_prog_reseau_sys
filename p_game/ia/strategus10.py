from ia.base_general import General
from ia.tacticus20 import Behaviour3
class Strategus10(Behaviour3):
    """ each unit type behaves in a certain, way after forming 3 blobs of units, S and K in flancks, reste in Center """
    """ C maintains distance with all enemy units if possible, attacks units in range if none goes closer to freindly P if none closest friendly C if none attacks near """
    """ K attacks enemys in range, moves towards nearest C while trying to avoid Ps in an area and keeps a min dist with any P if possible """
    """ P attacks enemys in range, moves towards nearest K if possible avoids C"""
    """ S same as K but keeps distance"""
    """ L orbits around closest C, attacks in LOS,"""
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "strategus 1.0"
        self.squads= []

    def play_turn(self , unit, turn):
        x =self.map.p
        y =self.map.q
        game_size=x*y      
 
        #self.update_squad(unit) 
        if unit.type == "C":
            if len(self.squads) < 1:
                self.squads.append(unit)
            if unit == self.squads[0]:
                return self.C_behaviour(unit)
            
            #print (len(unit.squad))
            self.keep_dist(unit, unit.range-0.5)

            if turn*10> game_size:
                        
                P=self.find_closest_friendly_type(unit,"P")

                if not self.attack_in_LOS(unit):
                    if P is None:
                        return self.C_behaviour(unit)
                        
                    self.orbit_around(unit,P,3)
            else:
                if unit.team == 'R':
                    return self.move_unit(unit, ( x/4 , y/2))
                else:
                    return self.move_unit(unit, ( x - x/4 , y/2))

        elif unit.type == "S":
            
            if turn*10 > game_size:

                return self.S_behaviour(unit)
            elif turn*10 < game_size:
                if unit.team == 'B':
                    if unit.position[1] <y/2:
                        return self.move_unit(unit, (x - x/4 , y/2 -30))
                    else:
                        return self.move_unit(unit, ( x - x/4 , y/2 +30))
                else:
                    if unit.position[1] <y/2:
                        return self.move_unit(unit, (x/4 , y/2 -30))
                    else:
                        return self.move_unit(unit,( x/4 , y/2 +30))

    
        elif unit.type == "K": #deso les tabu
            S=self.find_closest_friendly_type(unit,"S")
            if S is None:
                if turn*10 < game_size:
                    if unit.team == 'B':
                        if unit.position[1] <y/2:
                            return self.move_unit(unit, (x - x/4 , y/2 -30))
                        else:
                            return self.move_unit(unit, ( x - x/4 , y/2 +30))
                    else:
                        if unit.position[1] <y/2:
                            return self.move_unit(unit, (x/4 , y/2 -30))
                        else:
                            return self.move_unit(unit,( x/4 , y/2 +30))
                else: return self.K_behaviour(unit)
            if not self.attack_in_LOS(unit):
                return self.orbit_around(unit,S, 3.5)
            


        elif unit.type == "P":
            
            if turn*10> game_size:
                self.P_behaviour(unit)
            elif not   self.attack_in_LOS(unit):
                C=self.find_closest_friendly_type(unit,"C")
                if C is None:
                    if unit.team == 'R':
                        return self.move_unit(unit, ( x/4 , y/2))
                    else:
                        return self.move_unit(unit, ( x - x/4 , y/2))
                self.orbit_around(unit,C, 7)
            
         
        elif unit.type == "L":
            if self.attack_in_LOS(unit):
                return
            C=self.find_closest_friendly_type(unit,"C")
            if C is None:
                return self.attack_near(unit)
            self.orbit_around(unit, C, 4.5)
                    

        #if unit.type == "S":
        #    self.K_behaviour(unit)  # <---- attack les CrossBows comme Knit

    def update_squad(self, unit):
        unit.squad = list(filter(lambda m: m.is_alive and self.is_in_tile(unit,m.position,6), unit.squad))

        
    def C_behaviour(self , C):
        """attack nearest enemey and trys to maintain a distance"""

        if self.keep_dist(C , C.range - 0.5):
            self.attack_in_range(C)
        else:
            self.attack_near(C)
    def make_squad_C(self,unit):
        self.squads.append(unit)

    
    def orbit_around(self, unit,master,dist):
        dir_x= unit.position[0] - master.position[0]
        dir_y= unit.position[1] - master.position[1]
        if (dir_x**2 + dir_y**2) > (dist + master.size + unit.size)**2 :

            move_atr= ( unit.position[0] - dir_x , unit.position[1] - dir_y)
            self.move_unit(unit , move_atr)
            return False
        elif (dir_x**2 + dir_y**2) < (dist + master.size + unit.size )**2:
            #print(master.direction)
            return self.move_unit(unit,( unit.position[0] +  dir_y , unit.position[1]-  dir_x ) )
        elif master.direction != (0,0): self.move_unit_indir(unit, master.direction)
            

    
    def find_closest_friendly_type(self, unit,type):
        closest = None
        min_dist2 = float('inf') 
        dist2_fn = unit.distance_to_2
        for t_unit in self.my_units_dict[type]:
                if not t_unit.is_alive:
                    continue
                dist2 = dist2_fn(t_unit)  
                if dist2 < min_dist2:
                    min_dist2 = dist2
                    closest = t_unit
        return closest
    
    def stay_behind_closest_type(self,unit,type):
        him = self.find_closest_friendly_type(unit,type)
        if him is None:
            return False
        self.stay_behind(unit,him,2)
        

