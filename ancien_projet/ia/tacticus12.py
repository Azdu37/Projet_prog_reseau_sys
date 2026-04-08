from ia.base_general import General

class Behaviour2(General):
    """ each unit type behaves in a certain way """
    """ C maintains distance with all enemy units if possible, attacks units in range and moves towards closest enemy """
    """ K moves towards nearest C if possible, if any enemy in range stops and attacks """
    """ P moves towards nearest K if possible, if any enemy in range stops and attacks """
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "tacticus 1.2"
    
    def C_behaviour(self , C):
        """attack nearest enemey and trys to maintain a distance"""

        #self.keep_dist(C , C.range - 0.5)
        self.attack_near(C, self.keep_dist(C , C.range - 0.5))
        

    def K_behaviour(self , K):
        """move to closest CrossBow, attacks units in LOS"""

        closest_C = min(
        (u for u in self.enemy_units_dict["C"] if u.is_alive),
        key=lambda u: self.map.distance(K.position, u.position),
        default=None
        )
        
        if self.attack_in_range(K):
            return

        if closest_C is None:
            self.attack_near(K) 
        else:
            self.move_unit(K, closest_C.position)

         
    def P_behaviour(self , P):
        """move to closest Pike, attacks units in LOS"""

        closest_K = min(
        (u for u in self.enemy_units_dict["K"] if u.is_alive),
        key=lambda u: self.map.distance(P.position, u.position),
        default=None
        )
        
        if self.attack_in_range(P):
            return
            
        if closest_K is None:
            self.attack_near(P) 
        else:
            self.move_unit(P, closest_K.position)


       
    def initialize(self):
        return super().initialize()

    def play_turn(self , unit, turn):
          
        if unit.type == "C":
            self.C_behaviour(unit)
    

        if unit.type == "K":
            self.K_behaviour(unit)


        if unit.type == "P":
            self.P_behaviour(unit)

        if unit.type == "L":
            self.attack_near(unit)

        if unit.type == "S":
            self.S_behaviour(unit)  # <---- attack les CrossBows comme Knite

        
    def L_behaviour(self, L):
            """Pas d'aventages special, attack le plus proche"""
            self.attack_near(L)

            
    def S_behaviour(self , S):
            """move to closest CrossBow, attacks units in LOS"""

            closest_C = min(
            (u for u in self.enemy_units_dict["C"] if u.is_alive),
            key=lambda u: self.map.distance(S.position, u.position),
            default=None
            )
            
            self.attack_in_range(S)
            self.keep_dist(S , S.range - 0.4)

            if closest_C is None:
                self.C_behaviour(S) 
            else:
                self.move_unit(S, closest_C.position)

    
   