import pygame
from battle.map import Map
from battle.unit import Unit
from battle.projectile import Projectile
from random import randint
import os
import json



"""
zqsd -> deplacement
SHIFT -> deplacement rapide
m -> dezoom global
p -> Pause
f9 -> changement de type de vue
h -> affichage hitbox
t -> affichage target
r -> affichage range
x -> affichage sprites
l -> affichage ligne de vue
c -> quicksave
v -> quickload
Molette pour le zoom
fleche haut ou bas -> accelerer ou ralentir la vitesse de jeu
f3 -> affichage d'infos supplémentaires
tab -> Genere un rapport de bataille
"""

pygame.init()
infos = pygame.display.Info()
MAX_WIDTH = infos.current_w -100
MAX_HEIGHT = infos.current_h-150

TILE_W = 20
TILE_H = 20

SIZE_MINI_MAP = (200, 200)

SIZE_HEALTH_BAR = (15,3)

SIZE_PROJECTILE = 4

SIZE_PROJECTILE_JAVELOT = 7

with open("data/units_sprites/offset_img.json", "r") as f:
    SPRITES_OFFSET = json.load(f)

class GUI_view:
    def __init__(self, width: int = MAX_WIDTH, height: int = MAX_HEIGHT, tile_w: int = TILE_W, tile_h: int = TILE_H):
        pygame.init()
        self.max_size: tuple[int, int] = (min(width*tile_w, MAX_WIDTH), min(height*tile_h, MAX_HEIGHT))
        self.size_map: tuple[int, int] = (width, height)
        self.size_mini_map = SIZE_MINI_MAP
        self.offset = [(self.size_map[0] - self.max_size[0]/tile_w)//2, (self.size_map[1] - self.max_size[1]/tile_h)//2]
        self.old_offset = [0,0]
        self.tile_w = tile_w
        self.tile_h = tile_h
        self.units_sprites = {
        }
        self.sprites_offset = {
        }

        self.bg_img = pygame.image.load(f"data/bg1.png")
        self.size_bg = self.bg_img.get_size()
        self.bg_img_x = pygame.transform.flip(self.bg_img, 1, 0)
        self.bg_img_y = pygame.transform.flip(self.bg_img, 0, 1)
        self.bg_img_xy = pygame.transform.flip(self.bg_img, 1, 1)
        

        self.screen = pygame.display.set_mode(self.max_size)
        self.size_health_bar = SIZE_HEALTH_BAR
        self.size_projectile = SIZE_PROJECTILE
        self.size_projectile_javelot = SIZE_PROJECTILE_JAVELOT

        self.font = pygame.font.SysFont("monospace", 20, bold = True)
        self.big_font = pygame.font.SysFont("monospace", 100, bold = True)

        self.display_LOS = False
        self.display_range = False
        self.display_target_archers = False
        self.display_hitbox = True
        self.display_sprites = True
        self.display_more_infos = False

        self.zoom_factor = 1
        self.dezoom_limit = self.max_size[0] // self.size_map[0]/2 / TILE_W
        self.dezoom_activate = False

        self.all_units : list[Unit] = None

    def move(self, dx : int, dy : int):
        """Permet de deplacer l'affichage de la map (appel apres detection de ZQSD)"""
        # dx > 0 -> vers la droite
        # dx < 0 -> vers la gauche
        # dy > 0 -> vers le bas
        # dy < 0 -> vers le haut
        self.offset[0] = min(max(self.offset[0] + dx, -self.size_map[0]//2), round(1.5*self.size_map[0] - self.max_size[0]//self.tile_w))
        self.offset[1] = min(max(self.offset[1] + dy, 0), self.size_map[1] - self.max_size[1]//self.tile_h)

    def zoom(self, zoom_factor):
        # Rechargement des nouvelles tailles d'images
        self.size_health_bar = SIZE_HEALTH_BAR
        self.size_health_bar = (self.size_health_bar[0]*zoom_factor, self.size_health_bar[1]*zoom_factor)
        self.size_projectile = SIZE_PROJECTILE * zoom_factor
        self.size_projectile_javelot = SIZE_PROJECTILE_JAVELOT * zoom_factor
        
        self.units_sprites = {
        }
        self.sprites_offset = {
        }
        
        self.bg_img = pygame.image.load(f"data/bg1.png")
        self.size_bg = self.bg_img.get_size()
        self.size_bg = (int(self.size_bg[0]*zoom_factor), int(self.size_bg[1]*zoom_factor))
        self.bg_img = pygame.transform.scale(self.bg_img, self.size_bg)
        self.bg_img_x = pygame.transform.flip(self.bg_img, 1, 0)
        self.bg_img_y = pygame.transform.flip(self.bg_img, 0, 1)
        self.bg_img_xy = pygame.transform.flip(self.bg_img, 1, 1)
    

    def handle_input(self):
        keys = pygame.key.get_pressed()
        options_return = {
            "quit" : False,
            "pause" : False,
            "change_view" : False,
            "quicksave" : False,
            "quickload" : False,
            "increase_speed" : False,
            "decrease_speed" : False,
            "generate_rapport" : False
        }
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                options_return["quit"] == True
                pygame.quit()
                return options_return

            if event.type == pygame.MOUSEWHEEL:
                wheel_delta = event.y
                if wheel_delta != 0:
                    self.zoom_factor = max(self.dezoom_limit, self.zoom_factor+wheel_delta*0.1)
                    
                    tile = self.tile_w
                    self.tile_w = round(self.zoom_factor*TILE_W)
                    self.tile_h = round(self.zoom_factor*TILE_H)

                    self.offset[0] += (self.max_size[0] / 2) * (1/tile - 1/self.tile_w)
                    self.offset[1] += (self.max_size[1] / 2) * (1/tile - 1/self.tile_h)             

                    self.zoom(self.zoom_factor)
                   

            if event.type == pygame.KEYDOWN:        
                if event.key == pygame.K_m:
                    self.dezoom_activate = True
                    zoom_factor = self.dezoom_limit
                    self.tile_w = round(TILE_W*zoom_factor)
                    self.tile_h = round(TILE_H*zoom_factor)
                    self.old_offset = self.offset
                    self.offset = [(self.size_map[0] - self.max_size[0]/self.tile_w)//2, (self.size_map[1] - self.max_size[1]/self.tile_h)//2]
                    self.zoom(zoom_factor)

                elif event.key == pygame.K_p:
                    """ PAUSE """
                    options_return["pause"] = True

                elif event.key == pygame.K_F9:
                    """ CHANGE TO TERMINAL VIEW """
                    options_return["change_view"] = True
                    pygame.quit()

                elif event.key == pygame.K_l:
                    """ DISPLAY LOS """
                    self.display_LOS = not self.display_LOS

                elif event.key == pygame.K_r:
                    """ DISPLAY RANGE ARCHERS """
                    self.display_range = not self.display_range

                elif event.key == pygame.K_t:
                    """ DISPLAY TARGET ARCHERS """
                    self.display_target_archers = not self.display_target_archers

                elif event.key == pygame.K_h:
                    """ DISPLAY HITBOX """
                    self.display_hitbox = not self.display_hitbox
                
                elif event.key == pygame.K_x:
                    """ DISPLAY SPRITES """
                    self.display_sprites = not self.display_sprites

                elif event.key == pygame.K_c:
                    """ QUICKSAVE """
                    options_return["quicksave"] = True
                    
                elif event.key == pygame.K_v:
                    """ QUICKLOAD """
                    options_return["quickload"] = True

                elif event.key == pygame.K_UP:
                    """ INCREASE SPEED """
                    options_return["increase_speed"] = True

                elif event.key == pygame.K_DOWN:
                    """ DECREASE SPEED """
                    options_return["decrease_speed"] = True
                
                elif event.key == pygame.K_TAB:
                    """ GENERATE RAPPORT """
                    options_return["generate_rapport"] = True
                
                elif event.key == pygame.K_F3:
                    """ DISPLAY MORE INFOS """
                    self.display_more_infos = not self.display_more_infos


            if event.type == pygame.KEYUP:
                if event.key == pygame.K_m:
                    self.dezoom_activate = False
                    self.offset = self.old_offset
                    self.tile_w = round(self.zoom_factor*TILE_W)
                    self.tile_h = round(self.zoom_factor*TILE_H)
                    self.zoom(self.zoom_factor)

            
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            speed = 2
        else:
            speed = 1

        if keys[pygame.K_z]:
            self.move(0, -1*speed)
        elif keys[pygame.K_q]:
            self.move(-1*speed, 0)
        elif keys[pygame.K_s]:
            self.move(0, 1*speed)
        elif keys[pygame.K_d]:
            self.move(1*speed, 0)
        return options_return


    def display_background(self):
        """ Affichage arriere plan """
        for x in range(2*self.size_map[0]*self.tile_w // self.size_bg[0]+1):
            for y in range(2*self.size_map[1]*self.tile_h // self.size_bg[1]+1):
                if x%2 == 0:
                    if y%2 == 0:
                        self.screen.blit(self.bg_img, (self.size_bg[0]*(x-1)-self.offset[0]*self.tile_w, self.size_bg[1]*y-self.offset[1]*self.tile_h))
                    else:
                        self.screen.blit(self.bg_img_y, (self.size_bg[0]*(x-1)-self.offset[0]*self.tile_w, self.size_bg[1]*y-self.offset[1]*self.tile_h))
                else:
                    if y%2 == 0:
                        self.screen.blit(self.bg_img_x, (self.size_bg[0]*(x-1)-self.offset[0]*self.tile_w, self.size_bg[1]*y-self.offset[1]*self.tile_h))
                    else:
                        self.screen.blit(self.bg_img_xy, (self.size_bg[0]*(x-1)-self.offset[0]*self.tile_w, self.size_bg[1]*y-self.offset[1]*self.tile_h))
        
        # Affichage en noir des zones hors-map
        rect = [(0,0),(self.size_map[0],0),(self.size_map[0],self.size_map[1]),(0,self.size_map[1])]
        centre_position = [(rect[i][0]-self.size_map[0]//2, rect[i][1]-self.size_map[1]//2)for i in range(len(rect))]
        iso_pos = [(centre_position[i][0]-centre_position[i][1], (centre_position[i][0]+centre_position[i][1])/2)for i in range(len(centre_position))]
        proj_pos = [((iso_pos[i][0]+self.size_map[0]//2-self.offset[0])*self.tile_w, (iso_pos[i][1]+self.size_map[1]//2-self.offset[1])*self.tile_h)for i in range(len(iso_pos))]
        pygame.draw.polygon(self.screen, (0,0,0), [(0,0),proj_pos[0],proj_pos[3]])
        pygame.draw.polygon(self.screen, (0,0,0), [(0,0),proj_pos[0],(self.max_size[0],0)])
        pygame.draw.polygon(self.screen, (0,0,0), [(self.max_size[0],0),proj_pos[0],proj_pos[1]])
        pygame.draw.polygon(self.screen, (0,0,0), [(self.max_size[0],0),proj_pos[1],(self.max_size[0],self.max_size[1])])
        pygame.draw.polygon(self.screen, (0,0,0), [(self.max_size[0],self.max_size[1]),proj_pos[1],proj_pos[2]])
        pygame.draw.polygon(self.screen, (0,0,0), [(self.max_size[0],self.max_size[1]),proj_pos[2],(0,self.max_size[1])])
        pygame.draw.polygon(self.screen, (0,0,0), [(0,self.max_size[1]),proj_pos[2],proj_pos[3]])
        pygame.draw.polygon(self.screen, (0,0,0), [(0,self.max_size[1]),proj_pos[3],(0,0)])

                
    def display_projectiles(self, map : Map):
        for projectile in map.projectiles:
            centre_position = (projectile.position[0]-self.size_map[0]//2, projectile.position[1]-self.size_map[1]//2)
            iso_pos = (centre_position[0]-centre_position[1], (centre_position[0]+centre_position[1])/2)
            (proj_x, proj_y) = ((iso_pos[0]+self.size_map[0]//2-self.offset[0])*self.tile_w , (iso_pos[1]+self.size_map[1]//2-self.offset[1]-0.7)*self.tile_h)
            proj_dir_x = (projectile.direction[0] - projectile.direction[1])*0.707
            proj_dir_y = (projectile.direction[0] + projectile.direction[1])*0.707
            if(projectile.shooter.type == "C"): 
                pygame.draw.line(self.screen, (0,0,0), (proj_x, proj_y), (proj_x+proj_dir_x*self.size_projectile*2, proj_y+proj_dir_y*self.size_projectile*2), round(self.size_projectile/4),)
            elif (projectile.shooter.type == "S"):
                pygame.draw.line(self.screen, (50,50,50), (proj_x, proj_y), (proj_x+proj_dir_x*self.size_projectile_javelot*2.5, proj_y+proj_dir_y*self.size_projectile_javelot*2.5), round(self.size_projectile_javelot/4),)

    def display_units(self, map : Map, fps):
        """ Affichage unités """
        # On trie les unités pour qu'elle soit dans le bon ordre d'affichage isometrique
        self.all_units.sort(key=lambda u: u.position[0] + u.position[1])
        for unit in self.all_units: 
            (x, y) = unit.position
            if unit is None:
                continue

            # On choisi la couleur d'affichage
            if unit.is_alive:
                if unit.get_hit>0:
                    unit.get_hit -= 1/fps
                    color_display = ""
                else:
                    color_display = unit.team

                # On charge le sprite si il n'existe pas encore
                try:
                    self.units_sprites[f"{unit.type}{color_display}{unit.orientation}"]
                except:
                    zoom_factor = self.dezoom_limit if self.dezoom_activate else self.zoom_factor
                    
                    self.units_sprites[f"{unit.type}{color_display}{unit.orientation}"] = pygame.image.load(f"data/units_sprites/{unit.type}/{unit.type}{color_display}{unit.orientation}.png")
                    size = self.units_sprites[f"{unit.type}{color_display}{unit.orientation}"].get_size()
                    size = (int(size[0]*zoom_factor), int(size[1]*zoom_factor))
                    self.units_sprites[f"{unit.type}{color_display}{unit.orientation}"] = pygame.transform.scale(self.units_sprites[f"{unit.type}{color_display}{unit.orientation}"], size)
                    try:
                        self.sprites_offset[f"{unit.type}{unit.orientation}"]
                    except:
                        self.sprites_offset[f"{unit.type}{unit.orientation}"] = [round(SPRITES_OFFSET[f"{unit.type}{unit.orientation}"][0]*zoom_factor), round(SPRITES_OFFSET[f"{unit.type}{unit.orientation}"][1]*zoom_factor)]

                # On calcule la position de l'unit en iso
                centre_position = (x-self.size_map[0]//2, y-self.size_map[1]//2)
                iso_pos = (centre_position[0]-centre_position[1], (centre_position[0]+centre_position[1])/2)
                (proj_x, proj_y) = ((iso_pos[0]+self.size_map[0]//2-self.offset[0])*self.tile_w, (iso_pos[1]+self.size_map[1]//2-self.offset[1])*self.tile_h)
                
                color_bar = 'red' if unit.team == 'R' else 'blue'

                # display hitbox
                if self.display_hitbox:
                    # Dimensions de l'ovale
                    ovale_largeur = unit.size * self.tile_h * 2.8  # Largeur
                    ovale_hauteur = unit.size * self.tile_h * 1.5  # Hauteur
                    
                    # Calcul du rectangle englobant
                    rect_ovale = pygame.Rect(
                        proj_x - ovale_largeur//2,
                        proj_y - ovale_hauteur//2,
                        ovale_largeur,
                        ovale_hauteur
                    )
                    
                    # Dessiner l'ellipse
                    pygame.draw.ellipse(self.screen, color_bar, rect_ovale, 2)
                
                # display LOS
                if self.display_LOS:
                    # Dimensions de l'ovale
                    ovale_largeur = (unit.line_of_sight+unit.size) * self.tile_h * 2.8  # Largeur
                    ovale_hauteur = (unit.line_of_sight+unit.size) * self.tile_h * 1.5  # Hauteur
                    
                    # Calcul du rectangle englobant
                    rect_ovale = pygame.Rect(
                        proj_x - ovale_largeur//2,
                        proj_y - ovale_hauteur//2,
                        ovale_largeur,
                        ovale_hauteur
                    )
                    
                    # Dessiner l'ellipse
                    pygame.draw.ellipse(self.screen, (0,0,0), rect_ovale, 2)

                # display range
                if self.display_range:
                    # Dimensions de l'ovale
                    ovale_largeur = (unit.range+unit.size) * self.tile_h * 2.8  # Largeur
                    ovale_hauteur = (unit.range+unit.size) * self.tile_h * 1.5  # Hauteur
                    
                    # Calcul du rectangle englobant
                    rect_ovale = pygame.Rect(
                        proj_x - ovale_largeur//2,
                        proj_y - ovale_hauteur//2,
                        ovale_largeur,
                        ovale_hauteur
                    )
                    
                    # Dessiner l'ellipse
                    pygame.draw.ellipse(self.screen, color_bar, rect_ovale, 2)
                    if unit.range_min != 0:
                        # Dimensions de l'ovale
                        ovale_largeur = (unit.range_min+unit.size) * self.tile_h * 2.8  # Largeur
                        ovale_hauteur = (unit.range_min+unit.size) * self.tile_h * 1.5  # Hauteur
                        
                        # Calcul du rectangle englobant
                        rect_ovale = pygame.Rect(
                            proj_x - ovale_largeur//2,
                            proj_y - ovale_hauteur//2,
                            ovale_largeur,
                            ovale_hauteur
                        )
                        
                        # Dessiner l'ellipse
                        pygame.draw.ellipse(self.screen, (75,75,75), rect_ovale, 2)
                
                # display sprites
                if self.display_sprites:
                    self.screen.blit(self.units_sprites[f"{unit.type}{color_display}{unit.orientation}"], (proj_x-self.sprites_offset[f"{unit.type}{unit.orientation}"][0], proj_y-self.sprites_offset[f"{unit.type}{unit.orientation}"][1]))
                    
                    # display health bar
                    if unit.current_hp != unit.max_hp:
                        x_health_bar = proj_x - self.size_health_bar[0]//2
                        y_health_bar = proj_y - self.size_health_bar[1] - 5 - self.sprites_offset[f"{unit.type}{unit.orientation}"][1]
                        pygame.draw.rect(self.screen, 'black', (x_health_bar, y_health_bar, self.size_health_bar[0], self.size_health_bar[1]))
                        pygame.draw.rect(self.screen, color_bar, (x_health_bar, y_health_bar, unit.current_hp*self.size_health_bar[0]//unit.max_hp, self.size_health_bar[1]))

                

                # display target archers
                if self.display_target_archers:
                    if unit.range != 0 and unit.target is not None and unit.target.is_alive:
                        target_pos = (unit.target.position[0]-self.size_map[0]//2, unit.target.position[1]-self.size_map[1]//2)
                        target_iso = (target_pos[0]-target_pos[1], (target_pos[0]+target_pos[1])/2)
                        (target_proj_x, target_proj_y) = ((target_iso[0]+self.size_map[0]//2-self.offset[0])*self.tile_w, (target_iso[1]+self.size_map[1]//2-self.offset[1])*self.tile_h)
                        
                        pygame.draw.line(self.screen, color_bar, (proj_x, proj_y), (target_proj_x, target_proj_y))
            
            

    def display_mini_map(self, map : Map):
        """ Affichage mini map """
        # Calcul des coordonnées du rect en iso
        rect = [(0,0),(200,0),(200,200),(0,200)]
        centre_position = [(rect[i][0]-self.size_mini_map[0]//2, rect[i][1]-self.size_mini_map[1]//2)for i in range(len(rect))]
        iso_pos = [(centre_position[i][0]-centre_position[i][1], (centre_position[i][0]+centre_position[i][1])/2)for i in range(len(centre_position))]
        proj_pos = [(iso_pos[i][0]+self.max_size[0]-self.size_mini_map[0], iso_pos[i][1]+self.max_size[1]-self.size_mini_map[1]//2)for i in range(len(iso_pos))]
        
        # Fond vert
        pygame.draw.polygon(self.screen, (50, 200, 50), proj_pos)

        # Bordure marron (cadre)
        pygame.draw.polygon(self.screen, (100, 100, 50), proj_pos, 5)


        # Cercle de couleur pour chaque unité vivante
        for (x, y) in map.map:
            unit = map.get_unit(x, y)
            if unit.is_alive: 
                if unit.team == 'R':
                    color = 'red'
                else:
                    color = 'blue'

                adjust_pos = (x*self.size_mini_map[0]/self.size_map[0], y*self.size_mini_map[1]/self.size_map[1])
                centre_position = (adjust_pos[0]-self.size_map[0]//2, adjust_pos[1]-self.size_map[1]//2)
                iso_pos = (centre_position[0]-centre_position[1], (centre_position[0]+centre_position[1])/2)
                proj_pos = (iso_pos[0]+self.max_size[0]-self.size_mini_map[0], iso_pos[1]+self.size_map[1]//2+self.max_size[1]-self.size_mini_map[1])
                
                pygame.draw.circle(self.screen, color, proj_pos, 3)
        
        # Cadre blanc indiquant la position de l'affichage
        pygame.draw.rect(self.screen, (255, 255, 255), (self.offset[0]*self.size_mini_map[0]/self.size_map[0]+self.max_size[0]-1.5*self.size_mini_map[0], self.offset[1]*self.size_mini_map[1]/self.size_map[1]+self.max_size[1]-self.size_mini_map[1], self.size_mini_map[0]*self.max_size[0]/self.size_map[0]/self.tile_w, self.size_mini_map[1]*self.max_size[1]/self.size_map[1]/self.tile_h), 3)


    def display_game_infos(self, battle_infos):
        """ Affichage informations de partie """
        # # Turn
        # text = self.font.render(f"Turn : {battle_infos['turn']}", 1, "white")
        time = round(float(battle_infos['in_game_time'][:-1]))
        if time >= 60:
            minutes = time // 60
            sec = time % 60
            text = self.font.render(f"{minutes} min {sec}", 1, "white")
        else:
            text = self.font.render(f"{time}s", 1, "white")
        self.screen.blit(text, ((self.max_size[0] - text.get_size()[0])//2, 0))
        
        # Name IA 1
        text = self.font.render(battle_infos['ia1'], 1, "red")
        self.screen.blit(text, (0, 0))
        # Name IA 2
        text = self.font.render(battle_infos['ia2'], 1, "blue")
        self.screen.blit(text, (self.max_size[0]-text.get_size()[0], 0))

        # Tick rate (TPS)
        text = self.font.render(f"speed      : x{round(battle_infos['target_tps']/60,2)}", 1, "white")
        self.screen.blit(text, (0,  self.max_size[1]-text.get_size()[1]*3))

        # Informations supplémentaires
        if self.display_more_infos:
            # Nb units IA 1
            text = self.font.render(f"Total units : {battle_infos['units_ia1']}", 1, "red")
            self.screen.blit(text, (0, 30))
            # Nb units par type IA1
            text = self.font.render(f"Pikemen : {len([u for u in self.all_units if u.team == 'R' and u.is_alive and u.type == 'P'])}", 1, "red")
            self.screen.blit(text, (0, 75))
            text = self.font.render(f"Knights : {len([u for u in self.all_units if u.team == 'R' and u.is_alive and u.type == 'K'])}", 1, "red")
            self.screen.blit(text, (0, 100))
            text = self.font.render(f"Crossbowmen : {len([u for u in self.all_units if u.team == 'R' and u.is_alive and u.type == 'C'])}", 1, "red")
            self.screen.blit(text, (0, 125))
            text = self.font.render(f"Long Swordsmen : {len([u for u in self.all_units if u.team == 'R' and u.is_alive and u.type == 'L'])}", 1, "red")
            self.screen.blit(text, (0, 150))
            text = self.font.render(f"Elite Skirmishers : {len([u for u in self.all_units if u.team == 'R' and u.is_alive and u.type == 'S'])}", 1, "red")
            self.screen.blit(text, (0, 175))
            
            # Nb units IA 2
            text = self.font.render(f"Total units : {battle_infos['units_ia2']}", 1, "blue")
            self.screen.blit(text, (self.max_size[0]-text.get_size()[0], 30))
            # Nb units par type IA1
            text = self.font.render(f"Pikemen : {len([u for u in self.all_units if u.team == 'B' and u.is_alive and u.type == 'P'])}", 1, "blue")
            self.screen.blit(text, (self.max_size[0]-text.get_size()[0], 75))
            text = self.font.render(f"Knights : {len([u for u in self.all_units if u.team == 'B' and u.is_alive and u.type == 'K'])}", 1, "blue")
            self.screen.blit(text, (self.max_size[0]-text.get_size()[0], 100))
            text = self.font.render(f"Crossbowmen : {len([u for u in self.all_units if u.team == 'B' and u.is_alive and u.type == 'C'])}", 1, "blue")
            self.screen.blit(text, (self.max_size[0]-text.get_size()[0], 125))
            text = self.font.render(f"Long Swordsmen : {len([u for u in self.all_units if u.team == 'B' and u.is_alive and u.type == 'L'])}", 1, "blue")
            self.screen.blit(text, (self.max_size[0]-text.get_size()[0], 150))
            text = self.font.render(f"Elite Skirmishers : {len([u for u in self.all_units if u.team == 'B' and u.is_alive and u.type == 'S'])}", 1, "blue")
            self.screen.blit(text, (self.max_size[0]-text.get_size()[0], 175))

            # FPS
            text = self.font.render(f"fps     : {battle_infos['turn_fps']}", 1, "white")
            self.screen.blit(text, (0, self.max_size[1]-text.get_size()[1]*4))
            # Real speed
            text = self.font.render(f"real speed     : x{round(battle_infos['real_tps']/60,2)}", 1, "white")
            self.screen.blit(text, (0, self.max_size[1]-text.get_size()[1]*2))
            
            # # Time
            # text = self.font.render(f"In game time   : {battle_infos['in_game_time']}  scale : {battle_infos['performance']} ", 1, "white")
            # self.screen.blit(text, (0, self.max_size[1]-text.get_size()[1]*2))
            # text = self.font.render(f"Time from start: {battle_infos['time_from_start']}  dt    : {battle_infos['time_delta']}", 1, "white")
            # self.screen.blit(text, (0, self.max_size[1]-text.get_size()[1]*1))


        # Pause
        if battle_infos["game_pause"]:
            text = self.big_font.render("PAUSE", 1, "white")
            self.screen.blit(text, ((self.max_size[0]-text.get_size()[0])//2, (self.max_size[1]-text.get_size()[1])//2))


    def display(self, map: Map, battle_infos: dict):
        """ Return True si il faut continuer a afficher et False si il faut quitter le gui"""
        if self.all_units is None:
            self.all_units = []
            for (x, y) in map.map:
                self.all_units.append(map.get_unit(x, y))

        self.screen.fill((0,0,0))
        
        self.display_background()

        self.display_units(map, battle_infos["turn_fps"])

        self.display_projectiles(map)
        
        self.display_mini_map(map)
        
        self.display_game_infos(battle_infos)

        pygame.display.flip()

        return self.handle_input()
