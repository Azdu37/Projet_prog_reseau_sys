import os,random,math
from battle.unit import Unit

class Scenario:
    def __init__(self):
        pass
    
    def Rectangle(self, x, y, type_unit, number_of_points, left_or_right=0,number_of_lines=None):
        """ Génère un rectangle d'unités """
        number_of_lines = number_of_lines or math.ceil(math.sqrt(number_of_points)) # Si non précisé, on fait un carré
        units = []
        p = 3*Unit().get_by_type(type_unit, None, None).size # Espacement entre les unités suffisant pour éviter les collisions
        for i in range(number_of_points):
            # Calcul des indices de ligne et de colonne
            col_index = i // number_of_lines
            line_index = i % number_of_lines
            
            # Calcul des coordonnées
            if left_or_right == 0:  # x avance vers la droite
                current_x = x + (col_index * p)
            else:  # x avance vers la gauche
                current_x = x - (col_index * p)
            # y recule vers le bas
            current_y = y + (line_index * p)
            
            units.append([current_x, current_y,type_unit])
        return units
            
        

    def get_list_by_name(self, name = "stest1"):
        """ Renvoie une liste dont chaque element est : [x, y, type_unite]"""
        if "lanchester" in name:
            with open(f"data/lanchester/{name}.txt", "r") as f:
                data = f.read().split("\n")
        elif "save" in name:
            with open(f"data/save/{name}.txt", "r") as f:
                data = f.read().split("\n")
        elif "data" in name:
            with open(f"data/savedata/{name}.txt", "r") as f:
                data = f.read().split("\n")
        else:
            with open(f"data/scenario/{name}.txt", "r") as f:
                data = f.read().split("\n")
        
        
        line = data[0].split(',')
        size = [int(line[0]), int(line[1])]

        units = []

        for line in data[1:]:
            line = line.split(',')
            if len(line) < 3:
                continue
            unit = [float(line[0]), float(line[1]), line[2]]
            units.append(unit)

        return (size, units)
    
    def create_scenario(self, scenario_name,size,step, list_units): #list_units = [[x,y,type,number in one collumn],...]
        """ Génère automatiquement un scénario en fonction des paramètres donnés """
        self.delete_scenario(scenario_name)
        with open(f"data/scenario/{scenario_name}.txt", "w") as f:
            f.write(f"{size[0]},{size[1]}\n")
            for unit in list_units:
                step = step or 3*Unit().get_by_type(unit[2], None, None).size
                for k in range(unit[3]):
                    f.write(f"{unit[0]},{unit[1]+k*step},{unit[2]}\n")
    
    def delete_scenario(self, scenario_name):
        """ Supprime un scénario donné """
        if "lanchester" in scenario_name:
            if os.path.exists("data/lanchester/{scenario_name}.txt"):
                os.remove(f"data/lanchester/{scenario_name}.txt")
        elif "save" in scenario_name:
            if os.path.exists("data/save/{scenario_name}.txt"):
                os.remove(f"data/save/{scenario_name}.txt")
        elif "data" in scenario_name:
            if os.path.exists("data/savedata/{scenario_name}.txt"):
                os.remove(f"data/savedata/{scenario_name}.txt")
        else:
            if os.path.exists("data/scenario/{scenario_name}.txt"):
                os.remove(f"data/scenario/{scenario_name}.txt")

    def list_scenarios(self):
        """ Renvoie la liste des scénarios disponibles """
        files = os.listdir("data/scenario")
        scenarios = [f[:-4] for f in files if f.endswith(".txt")]
        files = os.listdir("data/lanchester")
        scenarios_lanchester = [f[:-4] for f in files if f.endswith(".txt")]
        files = os.listdir("data/save")
        save = [f[:-4] for f in files if f.endswith(".txt")]
        files = os.listdir("data/savedata")
        save_data = [f[:-4] for f in files if f.endswith(".txt")]
        return (scenarios, scenarios_lanchester, save, save_data)

    def create_lanchester_scenario_N(self, scenario_name, size, unit_red_type, unit_blue_type, n_red, n_blue):
        """ Génère un scénario de type Lanchester avec deux types d'unités potentiellement différents """
        self.delete_scenario(scenario_name)
        with open(f"data/lanchester/{scenario_name}_lanchester.txt", "w") as f:
            f.write(f"{size[0]},{size[1]}\n")
            
            # Red units on the left half
            for unit_red in self.Rectangle(10, 10, unit_red_type, n_red, left_or_right=0,
                                           number_of_lines=max(1, n_red // 4)):
                f.write(f"{unit_red[0]},{unit_red[1]},{unit_red[2]}\n")
                
            # Blue units on the right half
            for unit_blue in self.Rectangle(size[0] - 10, 10, unit_blue_type, n_blue, left_or_right=1,
                                            number_of_lines=max(1, n_blue // 4)):
                f.write(f"{unit_blue[0]},{unit_blue[1]},{unit_blue[2]}\n")
    
    def create_lanchester_scenario_proportion(self, scenario_name, size,unit_type, density_red, density_blue):
        """ Génère un scénario de type Lanchester """
        self.delete_scenario(self, scenario_name)
        with open(f"data/lanchester/{scenario_name}_lanchester.txt", "w") as f:
            f.write(f"{size[0]},{size[1]}\n")
            # Red units on the left half
            for x in range(2, size[0]//2,2):
                for y in range(0,size[1],2):
                    if random.random() < density_red:
                        f.write(f"{x},{y},{unit_type}\n")  # Assuming 'K' is a unit type
            # Blue units on the right half
            for x in range(size[0]//2, size[0],2):
                for y in range(2,size[1],2):
                    if random.random() < density_blue:
                        f.write(f"{x},{y},{unit_type}\n")  # Assuming 'K' is a unit type

#Scenario().delete_scenario("stest1_lanchester")
#Scenario().delete_scenario("stest2")
#Scenario().create_scenario("stest2", (150,100),3, [[5,5,"C",5],[10,2,"K",10],[15,2,"P",15]])
#Scenario().create_scenario("stest4", (100,100),None, [[10,10,"C",30],[30,10,"K",20],[20,10,"P",30]])
#Scenario().create_lanchester_scenario_proportion("stest1", (100,100), "K", 0.025, 0.05)

#Scenario().delete_scenario("stest2_lanchester")
#Scenario().create_lanchester_scenario_proportion("stest2", (100,100), "C", 0.05, 0.1)

#Scenario().create_lanchester_scenario_N("stest3", (100,100), "K", 80, 80)