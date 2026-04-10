from ia.base_general import General

class void(General):
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "void"

        
       
    def initialize(self):
        return super().initialize()

    def play_turn(self, unit, turn):
        pass
