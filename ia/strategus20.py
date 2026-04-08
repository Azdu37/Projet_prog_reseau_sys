from ia.base_general import General
from math import sqrt, ceil
from ia.tacticus20 import Behaviour3

class Strategus20(Behaviour3):
    def __init__(self, team, game_map):
        super().__init__(team, game_map)
        self.name = "Strategus 2.0"
        
        # {unit: group_id} et {unit: (offset_x, offset_y)}
        self.unit_groups = {} 
        self.unit_offsets = {}
        self.formation_valid = False
        
        # Pour faire avancer le front petit à petit (comme un rouleau compresseur)
        self.front_line_x = None 

    def split_units(self, units, n):
        """Divise une liste en n parties"""
        if not units: return [[] for _ in range(n)]
        k, m = divmod(len(units), n)
        return [units[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]

    def create_formation_grid(self):
        """Assigne les groupes et les places fixes"""
        self.unit_groups.clear()
        self.unit_offsets.clear()
        
        my_units = self.get_my_units()
        if not my_units: return

        # Si c'est la première fois, on initialise la ligne de front à notre position moyenne X
        if self.front_line_x is None:
             avg_x = sum(u.position[0] for u in my_units) / len(my_units)
             self.front_line_x = avg_x

        
        # Les plus petit Y  début  liste.
        # Les plus grand Y  à la fin.
        
        Ks = sorted([u for u in my_units if u.type == 'K'], key=lambda u: u.position[1])
        Cs = sorted([u for u in my_units if u.type == 'C'], key=lambda u: u.position[1])
        Ps = sorted([u for u in my_units if u.type == 'P'], key=lambda u: u.position[1])
        Ls = sorted([u for u in my_units if u.type == 'L'], key=lambda u: u.position[1])
        Ss = sorted([u for u in my_units if u.type == 'S'], key=lambda u: u.position[1])

        k_groups = self.split_units(Ks, 3)
        c_groups = self.split_units(Cs, 3)
        p_groups = self.split_units(Ps, 3)
        l_groups = self.split_units(Ls, 3)
        s_groups = self.split_units(Ss, 3)

        for i in range(3):
            # K devant (0), P milieu (2), C derrière (4) l et s 
            self.assign_block_local(k_groups[i], group_id=i, row_start=0)
            self.assign_block_local(p_groups[i], group_id=i, row_start=2)
            self.assign_block_local(c_groups[i], group_id=i, row_start=4)
            self.assign_block_local(l_groups[i], group_id=i, row_start=6)
            self.assign_block_local(s_groups[i], group_id=i, row_start=8)

        self.formation_valid = True

    def assign_block_local(self, units, group_id, row_start):
        if not units: return
        
        cols = 4 # var pour  blocs
        
        # Petit tri local X, Y pour que le placement soit propre visuellement dans le carré
        units_sorted = sorted(units, key=lambda u: (u.position[1], u.position[0]))
        
        for idx, unit in enumerate(units_sorted):
            r = idx // cols  
            c = idx % cols   
            
            offset_depth = (row_start * 1.5) + (r * 1.5)
            offset_width = (c * 1.5) - ((cols * 1.5)/2) # Centré
            
            self.unit_groups[unit] = group_id
            self.unit_offsets[unit] = (offset_depth, offset_width)

    def play_turn(self, unit, turn):
        
        if turn < 1500:
            if not self.formation_valid:
                self.create_formation_grid()

            # LOGIQUE DE COMBAT
            #visibles = self.get_visibles_enemies(unit)
            #if visibles:
                # Si c'est un archer, il tire, sinon il bouge/attaque
             #   if unit.type == "C":
              #      closest = self.find_closest_enemy(unit)
               #     if closest and unit.is_in_range(closest):
                #        self.attack_near(closest)
                 #       return
                
                #self.attack_near(unit) 
                #return

            # 2. --- LOGIQUE DE MOUVEMENT SUR RAILS ---
            
            if unit not in self.unit_groups:
                return 

            group_id = self.unit_groups[unit] 
            off_depth, off_width = self.unit_offsets[unit]

            #  sens dattaque
            my_x_avg = self.front_line_x
            enemy_units = self.get_enemy_units()
            
            target_x = self.map.p / 2 # Centre 
            if enemy_units:
                target_x = sum(u.position[0] for u in enemy_units) / len(enemy_units)
            
            direction = 1 if target_x > my_x_avg else -1

            # Ligne de Front avance lentement
            dist_to_enemy = abs(target_x - self.front_line_x)
            if dist_to_enemy > 10: 
                current_front = self.front_line_x + (direction * 0.5) 
            else:
                current_front = self.front_line_x 

            lane_height = self.map.q / 4
            
            # Voie 0 : 1/4, Voie 1 : 1/2, Voie 2 : 3/4
            base_y = lane_height * (group_id + 1)

            # POSITION FINALE
            dest_x = current_front - (off_depth * direction)
            dest_y = base_y + off_width

            self.move_unit(unit, (dest_x, dest_y))
            
            # Petit hack pour avancer corda 
            if unit == self.get_my_units()[0] and dist_to_enemy > 15:
                self.front_line_x += (direction * 0.8)
        else:
            #IL attaque comme tacticus20
            if unit.type == "C":
                self.C_behaviour(unit) 
            elif unit.type == "K":
                self.K_behaviour(unit) 
            elif unit.type == "P":
                self.P_behaviour(unit) 
            elif unit.type == "L":
                self.L_behaviour(unit)
            elif unit.type == "S":
                self.S_behaviour(unit)
            else:
                self.attack_near(unit)
       

