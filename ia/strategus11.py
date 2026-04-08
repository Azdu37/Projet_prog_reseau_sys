from ia.base_general import General
from ia.tacticus20 import Behaviour3
class Strategus10(Behaviour3):
    """ each unit type behaves in a certain way """
    """ C maintains distance with all enemy units if possible, attacks units in range and moves towards closest enemy """
    """ K attacks enemys in range, moves towards nearest C if possible """
    """ P attacks enemys in range, moves towards nearest K if possible """
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "strategus 1.0"
        self.squads= []

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

    def make_grid(self,unit,n,max_leng):
        master = self.squads[n]
        sq_size = len(master.squad)
        if unit in master.squad:
            if sq_size<max_leng:
                pass
                

            
    def stay_under(self, slave, master,dist):

        mx, my = master.position
        dy = my + dist
        
        dest=(mx, dy )
        return self.move_unit(slave, dest)
    
    def stay_behind(self, slave, master,dist):
        "maintains slave position relative to master and adds squad member if not already in squad"
        
        mx, my = master.position
        if slave.team == 'R':
            dx = mx - dist
            if slave not in master.squad and self.is_in_tile(slave,(dx, my),0.3):
                master.squad.append(slave)
            dest=(dx, my )
        else:
            dx = mx + slave.size + master.size + dist
            if slave not in master.squad and self.is_in_tile(slave,(dx, my),0.3):
                master.squad.append(slave)
            dest=(dx, my )
        return self.move_unit(slave, dest) 



