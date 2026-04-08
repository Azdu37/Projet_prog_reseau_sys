from collections import defaultdict
from battle.map import Map
from battle.unit import Unit
from rich.console import Console
from rich.control import Control
from rich.columns import Table

console = Console()

"""
    Utilisation :

Initialisation -> 
    (width, height) sont les dimensions de la map

Move -> 
    Permet de deplacer la zone de la map affichee
    dx et dy sont les deplacements a effectuer (reponse d'un ZQSD)

Display -> 
    A besoin d'une instance de map et l'affiche

"""

class Terminal_view:
    def __init__(self, width, height):
        MAX_WIDTH = console.size[0]
        MAX_HEIGHT = console.size[1]-10
        # Taille max affichable dans le terminal
        self.max_size : tuple[int, int] = (min(width, MAX_WIDTH), min(height, MAX_HEIGHT))
        # Taille reelle de la map
        self.size_map : tuple[int, int] = (width, height)
        # Decalage d'affichage (mouvements ZQSD)
        self.offset : list[int, int] = [(self.size_map[0] - self.max_size[0])//2, (self.size_map[1] - self.max_size[1])//2]

        self.display_battle_info = True

        console.clear()


    def move(self, dx : int, dy : int):
        """Permet de deplacer l'affichage de la map (appel apres detection de ZQSD)"""
        # dx > 0 -> vers la droite
        # dx < 0 -> vers la gauche
        # dy > 0 -> vers le bas
        # dy < 0 -> vers le haut
        self.offset[0] = min(max(self.offset[0] + dx, 0), self.size_map[0] - self.max_size[0])
        self.offset[1] = min(max(self.offset[1] + dy, 0), self.size_map[1] - self.max_size[1])

    def display(self, map : Map, battle_infos : dict):
        """Affiche la map"""

        # On recupere la grille avec une unite max par case
        grid = self.map2grid(map)
        # On clear le terminal
        console.control(Control.home())

        # On affiche les infos de bataille
        console.rule(f"Turn : {battle_infos['turn']}")
        if self.display_battle_info:
            table = Table(show_header=False, expand=True, box=None)
            table.add_column(justify="left")
            table.add_column(justify="right")
            table.add_row(f"[red]{battle_infos['ia1']}[/]", f"[blue]{battle_infos['ia2']}[/]")
            table.add_row(f"[red]nb_units_team1 : {battle_infos['units_ia1']}[/]", f"[blue]nb_units_team2 : {battle_infos['units_ia2']}[/]")
            console.print(table)
        
        # on affiche la map
        for y in range(min(map.q, self.max_size[1])):
            for x in range(min(map.p, self.max_size[0])):
                if battle_infos['game_pause'] and y == min(map.q, self.max_size[1])//2 and x == min(map.p, self.max_size[0])//2-2:
                    console.print("PAUSE", style='bold green', end='')
                    break
                unit = grid[y][x]  # tab de tab avec une unité seulement par case
                if unit:
                    # Si armee rouge
                    if unit.team == 'R':
                        console.print(unit.type, style='bold red', end='')

                    # Si armée bleu
                    elif unit.team == 'B':
                        console.print(unit.type, style='bold blue', end='')
                # Si rien
                else:
                    print(" ", end="")
            print()
        
        table = Table(show_header=False, expand=True, box=None)
        table.add_column(justify="left")
        table.add_column(justify="right")
        table.add_row(f"TPS : {battle_infos['real_tps']}", f"Time_from_start : {battle_infos['time_from_start']}")
        console.print(table)
        
        return True
        


    def map2grid(self, map : Map):
        """Transforme le dictionnaire en grille affichable en terminal"""
        """La troupe affichee sera la derniere modifiee de la map"""
        grid : list[list[Unit]] = [[None for _ in range(min(self.size_map[0], self.max_size[0]))] for _ in range(min(self.size_map[1], self.max_size[1]))]
        for (x, y) in map.map:
            if map.get_unit(x, y).is_alive:
                x_proj = (round(x) - self.offset[0])//2
                y_proj = (round(y) - self.offset[1])//2
                if x_proj < self.max_size[0] and x_proj >= 0 and y_proj < self.max_size[1] and y_proj >= 0:
                    grid[y_proj][x_proj] = map.get_unit(x, y)
        return grid

