"""
Point d'entrée principal du jeu
"""

import argparse
import sys
import os

from battle.engine import Engine
from ia.registry import AI_REGISTRY

# Ensure relative data paths resolve from the project directory.
# On se place dans le dossier contenant main.py
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Création des dossiers nécessaires
for path in ["data/scenario", "data/save", "data/savedata"]:
    if not os.path.exists(path):
        os.makedirs(path)

import subprocess
import network_bridge
import time

class BattleCLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="MedievAIl - BAIttle GenerAIl")
        self.subparsers = self.parser.add_subparsers(dest="command")

        # Commande: run
        run_parser = self.subparsers.add_parser("run", help="Lancer une simulation")
        run_parser.add_argument("scenario", help="Nom du scénario")
        run_parser.add_argument("ia1", help="Nom de l'IA équipe Rouge ('R')")
        run_parser.add_argument("ia2", help="Nom de l'IA équipe Bleue ('B')")
        run_parser.add_argument("-t", "--terminal", action="store_true", help="Affichage terminal (ASCII)")
        run_parser.add_argument("--no-terminal", action="store_true", help="Pas d'affichage")
        run_parser.add_argument("--datafile", help="Fichier de sortie pour les données")
        run_parser.add_argument("--distributed", action="store_true", help="Activer le mode réparti")
        run_parser.add_argument("--local-team", choices=['R', 'B'], help="Équipe locale en mode réparti")
        run_parser.add_argument("--observer", action="store_true", help="Mode observateur (aucune IA locale)")
        run_parser.add_argument("--session", help="Identifiant de session réseau (relay/room)")
        run_parser.add_argument("--peer", help="Paramètre pair/endpoint réseau")
        run_parser.add_argument("--p2p-port", type=int, default=5555, help="Port P2P local")

        # Commande: load
        load_parser = self.subparsers.add_parser("load", help="Charger une sauvegarde")
        load_parser.add_argument("save_name", help="Nom du fichier de sauvegarde")

    def run(self):
        # Si aucun argument n'est passé, on peut mettre des arguments par défaut pour le debug
        if len(sys.argv) == 1:
            print("Usage: python3 main.py run <scenario> <ia1> <ia2> [options]")
            print("Exemple: python3 main.py run stest7 majordaft brain_dead")
            return

        args = self.parser.parse_args()
        if args.command == "run":
            self.cmd_run(args)
        elif args.command == "load":
            self.cmd_load(args)
        else:
            self.parser.print_help()

    def cmd_run(self, args):
        print(f"[RUN] Scenario: {args.scenario}")
        # Observer implique distribué sans équipe locale
        if args.observer:
            args.distributed = True
            args.local_team = None
        if args.distributed:
            mode = "Observateur" if args.observer else "Réparti"
            print(f"      Mode: {mode} (Équipe locale: {args.local_team})")
        else:
            print(f"      ias: {args.ia1} vs {args.ia2}")

        if args.no_terminal:
            view_type = 0
        elif args.terminal:
            view_type = 1
        else:
            view_type = 2

        engine = Engine(args.scenario, args.ia1, args.ia2, view_type, 
                        is_distributed=args.distributed, 
                        local_team=args.local_team)
        
        if args.distributed:
            # 0=ROUGE, 1=BLEU (comme pour le programme C)
            player_id = 0 if args.local_team == 'R' else (1 if args.local_team == 'B' else 0)
            
            # 2. Init network bridge (POSIX)
            network_bridge.init(player_id)
            network_bridge.start_listener(engine.apply_remote_update)
            
            print(f"[NETWORK] Bridge initialisé (peer_id={player_id})")
            time.sleep(0.3)

        try:
            engine.start()
        finally:
            if args.distributed:
                network_bridge.shutdown()

    def cmd_load(self, args):
        # Implémentation simplifiée du chargement
        print(f"[LOAD] Chargement de {args.save_name}")
        # En attendant une implémentation plus complète dans Engine
        pass

if __name__ == "__main__":
    BattleCLI().run()
