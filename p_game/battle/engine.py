

from battle.map import Map
import time
import sys, os

if os.name != 'nt':
    import termios
    import tty
from collections import deque
from random import randint
from statistics import mean

from ia.registry import AI_REGISTRY

def fix_string(string):
    """Transforme une chaîne de caractères en une version "fixe" (minuscules, sans espaces ou caractères spéciaux)"""
    str_void = ""
    bad_chars = [' ', '-', '_', '.', ',', ';', ':', '!', '?', '/', '\\', '|', '@', '#', '$', '%', '^', '&', '*', '(', ')', '[', ']', '{', '}', '<', '>', '~', '`', '"', "'"]
    for char in string:
        if char in bad_chars:
            continue
        str_void += char.lower()
    return str_void


def get_key():
    """
    Retourne une touche pressée sans bloquer.
    Fonctionne sous Windows et Linux/Mac.
    """
    # 1) Windows
    if os.name == 'nt':
        import msvcrt
        if msvcrt.kbhit():
            try:
                ch = msvcrt.getch()
                if ch in (b'\x00', b'\xe0'):  # Touche spéciale
                    ch = msvcrt.getch()
                return ch.decode('utf-8', errors='ignore')
            except:
                return None
        return None
    # 2) Linux / Mac
    else:
        import select
        keys = ""
        try:
            fd = sys.stdin.fileno()
            while select.select([fd], [], [], 0)[0]:
                keys += os.read(fd, 1).decode('utf-8', errors='ignore')
        except:
            return None
        if keys:
            return keys
        return None


def randomize_order(units):
    """Mélange l'ordre des unités pour le scénario"""
    for i in range(len(units) - 1, 0, -1):
        j = randint(0, i)
        units[i], units[j] = units[j], units[i]


class Engine:
    def __init__(self, scenario, ia1, ia2, view_type, is_distributed=False, local_team=None):

        self.scenario_name = scenario
        self.is_distributed = is_distributed
        self.local_team = local_team
        self.observer_mode = bool(is_distributed and (local_team is None))
        self.ia1_name = fix_string(ia1)
        self.ia2_name = fix_string(ia2)

        self.game_map = None
        self.units = []
        self.projectiles = []
        self.game_pause = False
        self.current_turn = 0
        self.is_running = False
        self.winner = None
        self.view = None
        self.pressed_keys = set()
        self.real_tps = 0
        # Historique des t/s des dernières turns (max 10)
        self.tab_game_tps = deque(maxlen=10)
        self.tab_tps_affichage = deque(maxlen=120)

        self.star_execution_time = None
        self.ia_thinking_time = {'R': 0.0, 'B': 0.0}
        self.initial_units_count = {'R': 0, 'B': 0}
        self.history = {'turns': [], 'red_units': [], 'blue_units': []}

        # Vue
        self.view_type = view_type
        # frame rate controles
        self.max_fps = 60  # <-- FPS MAX pas besoin de plus ca fait trop de fluctuation sinon
        self.min_fps = 10  # <-- FPS MIN
        self.min_frame_delay = 1 / self.max_fps 
        self.max_frame_delay = 1 / self.min_fps
        # tick rate / limit
        self.tps = 60  # <-- target TPS: Vitesse du jeu [= 60 pour un time scale =1 ] /!\ la moyenne reste toujours sous cette valeur... /!\
        self.turn_time_target = 1.0 / self.tps  # en secondes
        self.star_execution_time = None
        self.turn_time = 0

        self.max_turns = 40000
        self.turn_fps = 0
        self.time_turn = 0
        self.units = []

    def initialize_units(self):
        """charge la liste d'unite"""
        uid = 0
        for (x, y) in self.game_map.map:
            u = self.game_map.get_unit(x, y)
            u.unit_id = uid
            uid += 1
            u.direction = (0, 0)
            # Définition du propriétaire réseau local
            if self.is_distributed:
                u.is_local = (self.local_team is not None and u.team == self.local_team)
                u.network_owner = self.local_team if u.is_local else (('R' if u.team == 'R' else 'B') if self.local_team is not None else None)
            else:
                u.is_local = True
                u.network_owner = u.team
            # 0=R, 1=B
            u.owner_id = 0 if u.team == 'R' else 1
            self.units.append(u)

    def all_units(self):
        return self.units

    def find_unit(self, unit_id):
        for u in self.units:
            if getattr(u, 'unit_id', None) == unit_id:
                return u
        return None

    def load_scenario(self):
        """Charge le scénario depuis le fichier"""

        print(f"Loading scenario: {self.scenario_name}")
        self.game_map = Map()
        Map.load(self.game_map, self.scenario_name)


    def initialize_ai(self):
        """Initialise les deux IA (ou seulement la locale en mode réparti)"""
        if self.is_distributed:
            print(f"Mode réparti actif. Équipe locale : {self.local_team}")
            # Mode observateur: aucune IA locale
            if self.local_team is None:
                # Utilise une IA inerte côté Python; aucun play_turn ne sera appelé en observer
                null_ai_key = 'braindead'
                self.ia1 = AI_REGISTRY.get(null_ai_key)("R", self.game_map)
                self.ia2 = AI_REGISTRY.get(null_ai_key)("B", self.game_map)
            elif self.local_team == 'R':
                if self.ia1_name not in AI_REGISTRY:
                    raise ValueError(f"IA '{self.ia1_name}' non reconnue.")
                self.ia1 = AI_REGISTRY[self.ia1_name]("R", self.game_map)
                # IA distante remplacée par une IA inerte (contrôle via réseau)
                self.ia2 = AI_REGISTRY.get('braindead')("B", self.game_map)
            elif self.local_team == 'B':
                if self.ia2_name not in AI_REGISTRY:
                    raise ValueError(f"IA '{self.ia2_name}' non reconnue.")
                self.ia2 = AI_REGISTRY[self.ia2_name]("B", self.game_map)
                self.ia1 = AI_REGISTRY.get('braindead')("R", self.game_map)
            else:
                raise ValueError(f"Équipe locale '{self.local_team}' invalide en mode réparti.")
        else:
            if self.ia1_name not in AI_REGISTRY:
                raise ValueError(f"IA '{self.ia1_name}' non reconnue.")
            if self.ia2_name not in AI_REGISTRY:
                raise ValueError(f"IA '{self.ia2_name}' non reconnue.")  
            
            self.ia1 = AI_REGISTRY[self.ia1_name]("R", self.game_map)
            self.ia2 = AI_REGISTRY[self.ia2_name]("B", self.game_map)

        self.ia1.initialize()
        self.ia2.initialize()
        
        print(f"Initializing AIs: {self.ia1.name} vs {self.ia2.name}")
        pass
    
    
    def start(self):
        """Démarre la simulation de bataille"""
        print("=== Starting Battle ===")

        # Initialisation du mode de terminal pour Linux/Mac
        old_settings = None
        if os.name != 'nt' and sys.stdin.isatty():
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

        try:
            # Initialisation
            self.load_scenario()
            self.initialize_ai()

            if self.view_type > 0:
                self.initialize_view()
            self.initialize_units()

            self.is_running = True
            self.star_execution_time = time.time()

            randomize_order(self.units)

            # Boucle principale
            self.game_loop()
        finally:
            # Restauration du mode de terminal
            if old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        # Fin de partie
        return self.end_battle()

    def game_loop(self):
        """Boucle principale du jeu"""
 
        view_frame_time = max(1 / 100, 2 / (self.max_fps + self.min_fps))  # <-- 1/FPS au demarrage
        self.turn_time_target = 1.0 / self.tps  # en secondes
        max_turn_time = self.turn_time_target

        next_view_time = time.time()

        while self.is_running and self.current_turn < self.max_turns:
            turn_start = time.time()

            if not self.game_pause:
                ######################################################
                #####             - FPS throttling -          ########
                #####      " C'est moche mais ca marche "     ########
                ######################################################
                # FPS jamais au dessus de  TPS
                # FPS jamais au dessus de  max_fps
                # FPS jamais en dessous de min_fps, sauf si TPS < min_fps
                if self.view_type > 1 and self.current_turn % 5 == 0:

                    if self.real_tps == 0: tps =60
                    else: tps = self.real_tps
                    if self.tps <= 0:
                        self.tps =0
                        perf =1
                    else: perf = tps / (self.tps)  # stabilise autour de tps cible

                    #self.turn_time_target = 1.0 / max(self.tps,1)
                    #print(perf)

                    view_frame_time= max(min(( view_frame_time / perf), self.max_frame_delay), self.min_frame_delay)

                    self.turn_time_target = max(min(( self.turn_time_target * perf), 1/(self.tps+3)), 1/(self.tps+30))


                    view_frame_time =max( 1/tps , view_frame_time)   #fps jamais > tps
                    self.turn_fps = 1 / view_frame_time
                    max_turn_time = self.turn_time_target

                    #print(1/max_turn_time)
                    ##################################################################

                self.process_turn()
                # 1. Gérer les entrées
                if self.view_type == 1:
                    self.handle_input()
                # 2. Mettre à jour l'affichage
                if turn_start >= next_view_time and self.view_type > 0:
                    next_view_time = turn_start + view_frame_time
                    self.update_view()
                # 3. Vérifier les conditions de victoire
                self.check_victory()
                # 4. Passer au tour suivant
                self.current_turn += 1
                # 5 mets a jour les unités
                self.update_units(1 / 60)
                self.update_projectiles()
                if self.is_distributed:
                    self.push_local_state()
                # 5. Contrôle du turn rate
                self.turn_time = time.time() - turn_start
                if self.view and self.turn_time < max_turn_time:
                    time.sleep(max_turn_time - self.turn_time)
                turn_time_plusp = time.time() - turn_start
                if turn_time_plusp != 0:
                    self.tab_game_tps.append((1.0 / turn_time_plusp))
                    self.tab_tps_affichage.append(1.0 / turn_time_plusp)
                self.real_tps = (sum(self.tab_game_tps) / len(self.tab_game_tps)) if self.tab_game_tps else 0
                self.time_turn = time.time()


            else:
                if self.view_type == 1: self.handle_input()
                if turn_start >= next_view_time:
                    next_view_time = turn_start + view_frame_time
                    if self.view_type > 0:
                        self.update_view()
                turn_time = time.time() - turn_start
                if self.view and turn_time < max_turn_time:
                    time.sleep(max_turn_time - turn_time)
                turn_time_plusp = time.time() - turn_start
                if turn_time_plusp != 0:
                    self.tab_game_tps.append((1.0 / turn_time_plusp))



        
    def update_units(self,time_per_tick):
        for unit in self.units:
            unit.update(time_per_tick)

    def update_projectiles(self):
            self.game_map.update_projectiles()

    def handle_input(self):
        key_input = get_key()
        if key_input is None:
            self.pressed_keys.clear()
            return

        # on mes les flèches vers ZQSD pour simplifier
        if key_input.startswith('\x1b'):
            mapping = {'\x1b[A': 'z', '\x1b[B': 's', '\x1b[D': 'q', '\x1b[C': 'd'}
            if key_input in mapping:
                key_input = mapping[key_input]
            else:
                return

        for char in key_input:
            key = char.lower()
            if key == '\t': key = 'tab'

            if key in self.pressed_keys:
                continue
            self.pressed_keys.add(key)

            if key == 'z':
                self.view.move(0, -1)
            elif key == 's':
                self.view.move(0, 1)
            elif key == 'q':
                self.view.move(-10, 0)
            elif key == 'd':
                self.view.move(10, 0)
            elif key == 'p':
                self.game_pause = not self.game_pause
            elif key == 'c':
                self.change_view(2)
            elif key == 'tab':
                self.rapport_in_game()
            elif key == 't':
                self.game_map.save_file(self.scenario_name, self.ia1.name, self.ia2.name)
            elif key == 'y':
                self.stop()
                name = "autosave"
                name = name[:-5] if name.endswith("_save") else name
                if os.path.exists(f"data/savedata/{name}_engine_data.txt"):
                    with open(f"data/savedata/{name}_engine_data.txt", "r") as f:
                        data = f.read().split("\n")
                        line = data[0].split(',')
                        scenario, ia1, ia2 = str(line[0]), str(line[1]), str(line[2])
                else:
                    scenario, ia1, ia2 = "stest1", "major_daft", "major_daft"
                    name = "stest1"

                print(f"[LOAD] Loading saved battle from: {name}_save")
                print(f"      ias: {ia1} vs {ia2}")
                view_type = 2
                engine = Engine(name, ia1, ia2, view_type, is_distributed=self.is_distributed, local_team=self.local_team)
                engine.start()
        pass



    def process_turn(self):
        """Traite un tour de jeu (déplacements, combats, etc.)"""
        # 0. Synchronisation entrante (mises à jour distantes via thread network_bridge)
        red_alive = 0
        blue_alive = 0
        
        for unit in self.units:
            if not unit.is_alive:
                continue
            
            # Stockage de l'état précédent pour détection de changement
            
            if unit.team == 'R':
                red_alive += 1
                if not self.is_distributed or self.local_team == 'R':
                    self.ia1.play_turn(unit, self.current_turn)
            elif unit.team == 'B':
                blue_alive += 1
                if not self.is_distributed or self.local_team == 'B':
                    self.ia2.play_turn(unit, self.current_turn)
            
            # Détection de changement d'état (mouvement ou combat)

        # Objective 2 : Immediate update broadcast on local change

        # Enregistre l'historique pour Lanchester (tous les 10 tours pour ne pas trop alourdir)
        if "lanchester" in self.scenario_name.lower() and self.current_turn % 10 == 0:
            self.history['turns'].append(self.current_turn)
            self.history['red_units'].append(red_alive)
            self.history['blue_units'].append(blue_alive)
        
        pass

    def push_local_state(self):
        """Diffuser l'état local via le pont réseau"""
        import network_bridge
        network_bridge.push_local_update(self)

    def apply_remote_update(self, state):
        """Version 1: overwrite remote units with received values. No conflict resolution."""
        if not isinstance(state, dict) or "units" not in state:
            return

        for u in state["units"]:
            # Ne pas appliquer si on est l'owner (déjà mis à jour localement)
            # player_id: R=0, B=1
            my_id = 0 if self.local_team == 'R' else (1 if self.local_team == 'B' else -1)
            if u["owner_id"] == my_id and my_id != -1:
                continue

            existing = self.find_unit(u["unit_id"])
            if existing:
                new_pos = (u["x"], u["y"])
                old_pos = existing.position
                if old_pos != new_pos:
                    if self.game_map.get_unit(*old_pos) is existing:
                        self.game_map.maj_unit_posi(existing, new_pos)
                    else:
                        self.game_map.map.pop(old_pos, None)
                        self.game_map.map[new_pos] = existing
                        existing.position = new_pos
                existing.current_hp = u["hp"]
                existing.is_alive = existing.current_hp > 0
                existing.direction = (0, 0)
                existing.destination = None
                existing.target = None
                existing.time_until_next_attack = 0
                existing.time_before_next_attack = existing.attack_delay
                existing.state = 'idle' if existing.is_alive else 'dead'
            else:
                # Facultatif pour V1: ajouter l'unit? si elle n'existe pas
                pass
                # Facultatif pour V1: ajouter l'unité si elle n'existe pas
                pass

    def request_network_ownership(self, unit):
        """Demande la propriété réseau d'une unité (protocole de cohérence rudimentaire)."""
        if not self.is_distributed:
            return False
        try:
            import network_bridge
            if hasattr(network_bridge, 'request_ownership'):
                return bool(network_bridge.request_ownership(unit))
        except Exception:
            pass
        # Fallback local (optimiste)
        if unit.team == self.local_team:
            unit.is_local = True
            unit.network_owner = self.local_team
            return True
        return False

    def cede_network_ownership(self, unit, new_owner_team=None):
        """Cède la propriété réseau d'une unité."""
        if not self.is_distributed:
            return False
        try:
            import network_bridge
            if hasattr(network_bridge, 'cede_ownership'):
                return bool(network_bridge.cede_ownership(unit, new_owner_team))
        except Exception:
            pass
        # Fallback local
        unit.is_local = (unit.team == self.local_team and self.local_team is not None)
        unit.network_owner = self.local_team if unit.is_local else new_owner_team
        return True

    def change_view(self, view_type):
        """Change la vue du jeu (terminal ou GUI)"""
        self.view_type = view_type

        self.initialize_view()
        self.update_view()
    def initialize_view(self):
        """Initialise la vue appropriée (terminal ou GUI)"""
        import visuals.terminal_view as term
        import visuals.gui_view as gui
        match self.view_type:
            case 0:
                print("No view, this is a problem")
            case 1:
                self.view = term.Terminal_view(self.game_map.p, self.game_map.q)
            case 2:
                self.view = gui.GUI_view(self.game_map.p, self.game_map.q)

    def update_view(self):
        """Met à jour l'affichage pour refléter l'état actuel"""
        a = self.view.display(self.game_map, self.get_game_info())
        if self.view_type == 2:
            if a["change_view"]:
                self.change_view(a["change_view"])

            if a['pause']:
                self.game_pause = not self.game_pause
            if a["quit"]:
                self.end_battle()
            if a["quicksave"]:
                self.game_map.save_file(self.scenario_name, self.ia1.name, self.ia2.name)
            
            if a["quickload"]:
                self.stop()
                name="autosave"
                name=name[:-5] if name.endswith("_save") else name
                if os.path.exists(f"data/savedata/{name}_engine_data.txt"):
                    with open(f"data/savedata/{name}_engine_data.txt", "r") as f:
                        data = f.read().split("\n")
                        line = data[0].split(',')
                        scenario,ia1,ia2 = str(line[0]) ,str(line[1]),str(line[2])
                else:
                    scenario,ia1,ia2 = "stest1","major_daft","major_daft"
                    name="stest1"
                    
                print(f"[LOAD] Loading saved battle from: {name}_save")
                print(f"      ias: {ia1} vs {ia2}")
                view_type = 2
                engine = Engine(name, ia1, ia2, view_type, is_distributed=self.is_distributed, local_team=self.local_team)
                engine.start()

            if a["increase_speed"]:
                self.tps += 10
                print(self.tps)
                pass

            if a["decrease_speed"]:
                self.tps -= 10
                print(self.tps)

                pass
            if a["generate_rapport"]:
                self.rapport_in_game()

        pass



    def get_game_info(self):
        """Retourne les informations de jeu à afficher"""

        return {
            'turn': self.current_turn,
            'ia1': self.ia1.name,
            'ia2': self.ia2.name,
            'game_pause': self.game_pause,
            'units_ia1': len([u for u in self.units if u.team == 'R' and u.is_alive]),
            #'units_ia1_hp': sum(u.current_hp for u in self.units if u.team == 'R' and u.is_alive),

            'units_ia2': len([u for u in self.units if u.team == 'B' and u.is_alive]),
            #'units_ia2_hp': sum(u.current_hp for u in self.units if u.team == 'B' and u.is_alive),
            'target_tps' : self.tps,
            'real_tps': mean(self.tab_tps_affichage) if self.tab_tps_affichage else 0,
            'turn_fps': round(self.turn_fps),
            'time_from_start': f'{(time.time() - self.star_execution_time):.2f}s',
            'in_game_time': f'{(self.current_turn / 60):.2f}s',
            'performance': f'{round(self.real_tps*100 / 60)}%',
            'time_delta': f'{((self.current_turn / 60)-(time.time() - self.star_execution_time)):.2f}s',
        }


    def check_victory(self):
        """Vérifie les conditions de victoire"""
        #  Toutes les unités d'un camp détruites

        units_team1 = len([u for u in self.units if u.team == 'R' and u.is_alive])
        units_team2 = len([u for u in self.units if u.team == 'B' and u.is_alive])

        # selection du winner gagne si tout les adverse sont mort
        if units_team1 == 0 and units_team2 == 0:
            self.winner = None
            self.is_running = False
        elif units_team1 == 0:
            self.winner = self.ia2
            self.is_running = False
        elif units_team2 == 0:
            self.winner = self.ia1
            self.is_running = False

        if self.current_turn > self.max_turns:
            self.winner = None
            self.is_running = False
        pass


    def end_battle(self):
        """Termine la bataille et affiche les résultats"""
        if self.view == 1: self.update_view()

        # Rapport Lanchester si applicable



        print("\n=== Battle Ended ===")
        if self.winner:
            print(f"Winner: {self.winner.name, self.winner.team}")
        else:
            print("Draw or max turns reached")
        print(f"Total turns: {self.current_turn}")
        print(
            f"temps d'éxécution totale {time.time() - self.star_execution_time:.2f}, ce qui fait {self.current_turn / (time.time() - self.star_execution_time):.2f} tps en moyenne")
        # 125.81309372244759  fps pour le gui
        # 394.581443523516 fps pour le terminal
        # 1027.9418369857085 fps pour le no terminal
        return None

#peut être utile plus tard
 #           return {'turn': self.current_turn,'scenario': str(self.scenario_name),'ia1': str(self.ia1.name), 'ia2': str(self.ia2.name), 'units_ia1': len([u for u in self.units if u.team == 'R' and u.is_alive]),'units_ia2': len([u for u in self.units if u.team == 'B' and u.is_alive]),'real_tps': self.real_tps,'time_from_start': time.time() - self.star_execution_time,'winner_ia': str(self.winner.name) if self.winner else "draw",'winner_team': str(self.winner.team) if self.winner else None }

        

    def pause(self):
        """Met en pause la simulation"""
        self.is_running = False

    def resume(self):
        """Reprend la simulation"""
        self.is_running = True

    def stop(self):
        """Arrête complètement la simulation"""
        self.is_running = False

    def rapport_lanchester(self):
        """Génère un rapport spécifique pour les scénarios Lanchester."""
        info = self.get_game_info()
        filename = f"lanchester_report_{int(time.time())}.html"

        # On s'assure que le dernier tour est enregistré
        if not self.history['turns'] or self.history['turns'][-1] != self.current_turn:
            red_alive = len([u for u in self.units if u.team == 'R' and u.is_alive])
            blue_alive = len([u for u in self.units if u.team == 'B' and u.is_alive])
            self.history['turns'].append(self.current_turn)
            self.history['red_units'].append(red_alive)
            self.history['blue_units'].append(blue_alive)

        report_data = {
            'scenario': self.scenario_name,
            'turn': self.current_turn,
            'ia1': info['ia1'],
            'ia2': info['ia2'],
            'winner': self.winner.name if self.winner else "Égalité",
            'history': self.history,
            'initial_red': self.history['red_units'][0] if self.history['red_units'] else 0,
            'initial_blue': self.history['blue_units'][0] if self.history['blue_units'] else 0,
            'final_red': self.history['red_units'][-1] if self.history['red_units'] else 0,
            'final_blue': self.history['blue_units'][-1] if self.history['blue_units'] else 0,
        }

        generate_report('lanchester', report_data, filename)

    def rapport_in_game(self):
        """Génère un rapport HTML détaillé de l'état actuel du jeu."""
        info = self.get_game_info()
        filename = f"game_report_{info['turn']}.html"

        teams_data = {}
        teams = {'R': 'Rouge', 'B': 'Bleue'}
        for team_code, team_name in teams.items():
            team_units = [u for u in self.units if u.team == team_code]
            alive_units = [u for u in team_units if u.is_alive]

            total_hp = sum(u.current_hp for u in alive_units)
            max_hp = sum(u.max_hp for u in alive_units)
            hp_percent = (total_hp / max_hp * 100) if max_hp > 0 else 0

            unit_types = {}
            for u in alive_units:
                if u.type not in unit_types:
                    unit_types[u.type] = {'count': 0, 'hp': 0, 'max_hp': 0}
                unit_types[u.type]['count'] += 1
                unit_types[u.type]['hp'] += u.current_hp
                unit_types[u.type]['max_hp'] += u.max_hp

            types_stats = {}
            for u_type, stats in unit_types.items():
                avg_hp = stats['hp'] / stats['count']
                type_hp_percent = (stats['hp'] / stats['max_hp'] * 100)
                types_stats[u_type] = {
                    'count': stats['count'],
                    'avg_hp': avg_hp,
                    'percent': type_hp_percent
                }

            teams_data[team_code] = {
                'name': team_name,
                'alive_count': len(alive_units),
                'total_count': len(team_units),
                'total_hp': total_hp,
                'max_hp': max_hp,
                'hp_percent': hp_percent,
                'types': types_stats
            }

        units_list = []
        for u in self.units:
            units_list.append({
                'team_code': u.team,
                'type': u.type,
                'hp': u.current_hp,
                'max_hp': u.max_hp,
                'hp_percent': (u.current_hp / u.max_hp * 100) if u.max_hp > 0 else 0,
                'pos_x': u.position[0],
                'pos_y': u.position[1],
                'is_alive': u.is_alive
            })

        report_data = {
            'turn': info['turn'],
            'in_game_time': info['in_game_time'],
            'ia1': info['ia1'],
            'ia2': info['ia2'],
            'performance': info['performance'],
            'real_tps': info['real_tps'],
            'teams': teams_data,
            'units': units_list
        }

        generate_report('battle', report_data, filename)

        if self.view_type == 1:  # Terminal view
            print("Appuyez sur Entrée pour reprendre...")
            input()
