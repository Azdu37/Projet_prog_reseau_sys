

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

NO_PEER_ID = 255

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
        self.winner_team = None
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
        self.pending_network_actions = {}
        self.network_trace = []

    def initialize_units(self):
        """charge la liste d'unite"""
        uid = 0
        for (x, y), u in list(self.game_map.map.items()):
            u.unit_id = uid
            uid += 1
            u.direction = (0, 0)
            # V1: pas de propriété réseau cessible. On garde seulement l'équipe
            # qui pilote l'unité pour savoir ce que ce processus a le droit de jouer.
            if self.is_distributed:
                u.is_local = (self.local_team is not None and u.team == self.local_team)
                u.network_owner = 0 if u.team == 'R' else 1
            else:
                u.is_local = True
                u.network_owner = u.team
            # 0=R, 1=B
            u.owner_id = 0 if u.team == 'R' else 1
            u.lock_owner_peer = NO_PEER_ID
            u.pending_request_peer = NO_PEER_ID
            u.network_version = 1
            u.network_force_dirty = True
            u.network_request_out = False
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
        self.game_map.engine = self
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
            self.initialize_units()
            self.initialize_ai()

            if self.view_type > 0:
                self.initialize_view()

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
                # 3. Mettre à jour les unités et projectiles
                self.update_units(1 / 60)
                self.update_projectiles()
                # 4. Échange réseau (envoyer notre état + recevoir l'état distant)
                if self.is_distributed:
                    self.network_exchange()
                # 5. Vérifier les conditions de victoire (après réseau)
                self.check_victory()
                # 6. Passer au tour suivant
                self.current_turn += 1
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
            # Retirer les unités mortes de la carte pour qu'elles disparaissent
            if not unit.is_alive:
                self.game_map.remove_unit_instance(unit)

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
        red_alive = 0
        blue_alive = 0
        my_peer = self.get_local_peer_id()
        
        for unit in self.units:
            if not unit.is_alive:
                continue

            if unit.team == 'R':
                red_alive += 1
                if (not self.is_distributed or self.local_team == 'R') and not self.is_temporarily_locked_by_remote(unit, my_peer):
                    self.ia1.play_turn(unit, self.current_turn)
            elif unit.team == 'B':
                blue_alive += 1
                if (not self.is_distributed or self.local_team == 'B') and not self.is_temporarily_locked_by_remote(unit, my_peer):
                    self.ia2.play_turn(unit, self.current_turn)

        # Enregistre l'historique pour Lanchester (tous les 10 tours pour ne pas trop alourdir)
        if "lanchester" in self.scenario_name.lower() and self.current_turn % 10 == 0:
            self.history['turns'].append(self.current_turn)
            self.history['red_units'].append(red_alive)
            self.history['blue_units'].append(blue_alive)
        
        pass

    def network_exchange(self):
        """Échange réseau : envoie notre état + reçoit l'état distant via SHM/C/UDP."""
        import network_bridge
        network_bridge.exchange_state(self)

    def request_network_ownership(self, unit):
        if not self.is_distributed:
            return True
        my_peer = self.get_local_peer_id()
        if my_peer is None:
            return False
        if unit.owner_id == my_peer or getattr(unit, "lock_owner_peer", NO_PEER_ID) == my_peer:
            return True
        unit.network_request_out = True
        return False

    def cede_network_ownership(self, unit, new_owner_team=None):
        if not self.is_distributed:
            return True
        import network_bridge
        requester_peer = new_owner_team if new_owner_team is not None else getattr(unit, "pending_request_peer", NO_PEER_ID)
        if requester_peer == NO_PEER_ID:
            return False
        network_bridge.grant_temporary_ownership(unit, requester_peer)
        unit.network_force_dirty = True
        return True

    def get_local_peer_id(self):
        if not self.is_distributed or self.local_team is None:
            return None
        return 0 if self.local_team == 'R' else 1

    def is_temporarily_locked_by_remote(self, unit, my_peer=None):
        if my_peer is None:
            my_peer = self.get_local_peer_id()
        lock_owner = getattr(unit, "lock_owner_peer", NO_PEER_ID)
        return my_peer is not None and lock_owner not in (NO_PEER_ID, my_peer)

    def queue_network_action(self, actor, target, action_type, payload=None):
        my_peer = self.get_local_peer_id()
        if my_peer is None:
            return False
        if target.unit_id not in self.pending_network_actions:
            self.pending_network_actions[target.unit_id] = {
                "actor_id": actor.unit_id,
                "target_id": target.unit_id,
                "action_type": action_type,
                "payload": payload or {},
                "requester_peer": my_peer,
            }
            target.network_request_out = True
            self.network_trace.append((self.current_turn, "request", target.unit_id, my_peer))
            print(f"[V2] Peer {my_peer} demande la propriete temporaire de l'unite #{target.unit_id}.")
        return False

    def process_pending_network_actions(self):
        if not self.pending_network_actions:
            return

        import network_bridge

        my_peer = self.get_local_peer_id()
        done = []
        for target_id, action in list(self.pending_network_actions.items()):
            actor = self.find_unit(action["actor_id"])
            target = self.find_unit(action["target_id"])
            projectile = action["payload"].get("projectile") if action["payload"] else None
            if actor is None or target is None or not actor.is_alive or not target.is_alive:
                if projectile is not None:
                    projectile.consumed = True
                done.append(target_id)
                continue
            if getattr(target, "lock_owner_peer", NO_PEER_ID) != my_peer:
                continue

            if action["action_type"] == "attack":
                if not actor.can_attack(target):
                    print(f"[V2] Action refusee apres grant: l'unite #{actor.unit_id} ne peut plus attaquer #{target.unit_id}.")
                    network_bridge.commit_unit_state(target)
                    target.network_force_dirty = True
                    done.append(target_id)
                    continue
                actor.state = "attacking"
                actor.target = target
                actor.time_reset()
                target.take_damage(actor)
                network_bridge.commit_unit_state(target)
                target.network_force_dirty = True
                self.network_trace.append((self.current_turn, "commit", target.unit_id, int(target.current_hp)))
                print(f"[V2] Commit coherent: unite #{target.unit_id} mise a jour a hp={int(target.current_hp)}.")
                done.append(target_id)
            elif action["action_type"] == "projectile_hit":
                if projectile is not None:
                    projectile.consumed = True
                target.take_damage(actor)
                network_bridge.commit_unit_state(target)
                target.network_force_dirty = True
                self.network_trace.append((self.current_turn, "commit", target.unit_id, int(target.current_hp)))
                print(f"[V2] Commit coherent projectile: unite #{target.unit_id} mise a jour a hp={int(target.current_hp)}.")
                done.append(target_id)

        for target_id in done:
            self.pending_network_actions.pop(target_id, None)

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

        visible_units = [u for u in self.game_map.map.values() if u is not None]
        return {
            'turn': self.current_turn,
            'ia1': self.ia1.name,
            'ia2': self.ia2.name,
            'game_pause': self.game_pause,
            'units_ia1': len([u for u in visible_units if u.team == 'R' and u.is_alive]),
            #'units_ia1_hp': sum(u.current_hp for u in self.units if u.team == 'R' and u.is_alive),

            'units_ia2': len([u for u in visible_units if u.team == 'B' and u.is_alive]),
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

        winner_team = None
        battle_finished = False

        # selection du winner gagne si tout les adverse sont mort
        if units_team1 == 0 and units_team2 == 0:
            battle_finished = True
        elif units_team1 == 0:
            winner_team = 'B'
            battle_finished = True
        elif units_team2 == 0:
            winner_team = 'R'
            battle_finished = True

        if self.current_turn >= self.max_turns:
            winner_team = None
            battle_finished = True

        if not battle_finished:
            self.winner_team = None
            return

        self.winner_team = winner_team
        self.winner = self.ia1 if winner_team == 'R' else self.ia2 if winner_team == 'B' else None
        self.is_running = False
        pass


    def end_battle(self):
        """Termine la bataille et affiche les résultats"""
        if self.view == 1: self.update_view()

        # Rapport Lanchester si applicable



        print("\n=== Battle Ended ===")
        if self.winner_team:
            team_name = "ROUGE" if self.winner_team == 'R' else "BLEU"
            print(f"Winner: {team_name} ({self.winner_team})")
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
        visible_units = [u for u in self.game_map.map.values() if u is not None]
        for team_code, team_name in teams.items():
            team_units = [u for u in visible_units if u.team == team_code]
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
        for u in visible_units:
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
