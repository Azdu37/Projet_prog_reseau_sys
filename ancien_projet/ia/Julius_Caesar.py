from ia.base_general import General 
from ia.daft import MajorDaft

class Jules_Cesar(General):
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "Julious Caesar"
        self.units_by_type = {}

    def initialize(self):

        return super().initialize()

    def stay_under(self, slave, master,dist):
        mx, my = master.position
        dy = my + slave.size + master.size + dist
        dest=(mx, dy )
        return self.move_unit(slave, dest)

    def hold_colomn(self, formation, dist):
        
        for i in range(len(formation)-1):
            
            self.stay_under(formation[i+1],formation[i],dist)
    
    def stay_behind(self, slave, master,dist):
        mx, my = master.position
        if slave.team == 'R':
            dx = mx - slave.size - master.size - dist
            dest=(dx, my )
        else:
            dx = mx + slave.size + master.size + dist
            dest=(dx, my )
        
        return self.move_unit(slave, dest)        
    

    def play_turn(self,time):
        if time< 1500:
            self.my_units_dict['K']
            self.hold_colomn(self.my_units_dict['K'],1)
        
        for unit in self.my_units:

            MajorDaft.attack_near(self,unit)
            