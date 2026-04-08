from ia.base_general import General

class Brain_DEAD(General):
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "BrainDead"

        
    def initialize(self):
        return super().initialize()

    def play_turn(self,unit ,turn):
        self.attack_in_LOS(unit)

