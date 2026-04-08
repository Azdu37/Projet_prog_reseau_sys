
from collections import defaultdict
from multiprocessing import Pool, cpu_count  # Import du module
from battle.engine import *
from ia.registry import AI_REGISTRY
import numpy as np
import time
from reports.reporter import generate_report


def fix_string(string):
    """Transforme une chaîne de caractères en une version "fixe" (minuscules, sans espaces ou caractères spéciaux)"""
    str_void = ""
    bad_chars = [' ', '-', '_', '.', ',', ';', ':', '!', '?', '/', '\\', '|', '@', '#', '$', '%', '^', '&', '*', '(',
                 ')', '[', ']', '{', '}', '<', '>', '~', '`', '"', "'"]
    for char in string:
        if char in bad_chars:
            continue
        str_void += char.lower()
    return str_void


# --- FONCTION WORKER (Doit être en dehors de la classe) ---
def run_match_wrapper(args):
    """
    Cette fonction est exécutée par chaque processus enfant (cœur CPU).
    args: tuple (scenario_name, ia1_name, ia2_name)
    """
    scenario, ia1, ia2 = args
    try:
        game = Engine(scenario, ia1, ia2, 0, True)
        result = game.start()
        return result
    except Exception as e:
        # En cas de crash d'une IA, on renvoie l'erreur pour ne pas bloquer le tournoi
        return {"error": str(e), "ia1": ia1, "ia2": ia2, "winner_ia": "Error"}


class TournamentManager:
    def __init__(self, matches_per_pair=2, generals=None, scenarios=None, out_file="tournament_report.html",
                 terminal=True, scenario_dir="data/scenario"):

        self.matches_per_pair = matches_per_pair
        self.out_file = out_file
        self.terminal = terminal
        self.stats_ia = {}
        self.res_dic_brut = defaultdict(list)
        self.res_dic_stat = defaultdict(list)

        self.available_generals = AI_REGISTRY
        self.total_execution_time = 0
        self.confrontation_matrix = {}

        # À adapter selon ta méthode réelle de découverte des scénarios
        # low
        
        self.available_scenarios = {"156u_KCPL_210": "156u_KCPL_210", "104u_KCPL_175": "104u_KCPL_175", "stest7": "st7",
                                    "stest13": "st12", "stest8": "st8", }
        """self.available_scenarios = {
            # 6 scénarios dont le nom commence par un nombre (à choisir parmi ceux qui existent)
            "30u_150_KCP": "30u_150_KCP",
            "52u_KCPL_100": "52u_KCPL_100",
            "100u_chaos": "100u_chaos",
            "104u_KCPL_175": "104u_KCPL_175",
            "150u_gpt_gamebreaker": "150u_gpt_gamebreaker",
            "156u_KCPL_210": "156u_KCPL_210",

            # stest demandés : 7,3,8,6,11,13
            "stest7": "st7",
            "stest3": "st3",
            "stest8": "st8",
            "stest6": "st6",
            "stest11": "st11",
            "stest13": "st12",
        }"""

        # self.available_scenarios = {"stest1": "st1", "stest2": "st2"}
        # self.available_scenarios = {"stest7": "st7", "stest12": "st12", "100u_chaos": "100u_chaos"}


        # Filtrage des IAs
        if not generals or generals == ["all"]:
            self.generals = list(self.available_generals.keys())
        else:
            self.generals = generals

        # Filtrage des scénarios
        if not scenarios or scenarios == ["all"]:
            self.scenarios = list(self.available_scenarios.keys())  # Correction ici pour avoir une liste
        else:
            self.scenarios = scenarios

        self.run_tournament()

    def run_tournament(self):
        # ... (La partie création des tasks/pairs reste identique) ...
        # Copiez le début de votre fonction jusqu'à "start_time = time.time()"

        # --- MODIFICATION ICI ---
        tasks = []
        pairs = []
        for ga in self.generals:
            for gb in self.generals:
                if ga != gb:
                    pairs.append((ga, gb))

        for scenario in self.scenarios:
            for ga, gb in pairs:
                for _ in range(self.matches_per_pair):
                    tasks.append((scenario, ga, gb))

        total_matches = len(tasks)
        nb_cores = cpu_count() - 1
        print(f"Matchs à jouer : {total_matches} sur {nb_cores} cœurs.")

        start_time = time.time()

        # On utilise imap_unordered pour avoir les résultats un par un
        with Pool(processes=nb_cores) as pool:
            # On crée un itérateur
            iterator = pool.imap_unordered(run_match_wrapper, tasks)

            # On boucle pour afficher la progression
            for i, result in enumerate(iterator):
                self.res_dic_brut[i] = result


                progression = ((i + 1) / total_matches) * 100
                elapsed = time.time() - start_time
                remaining = (elapsed / (i + 1)) * (total_matches - (i + 1)) if (i + 1) > 0 else 0
                print(
                    f"\rProgression : {progression:.2f}% | Matchs : {i + 1}/{total_matches} | Temps : {elapsed:.1f}s | Restant : {remaining:.1f}s",
                      end="", flush=True)


                # Affichage d'une barre de progression dynamique

        print("\n=== TOUS LES MATCHS SONT TERMINÉS ===")

        self.total_execution_time = time.time() - start_time
        self.end_tournament()

    def stat_tournaments(self):
        # Initialisation des structures de données pour les stats par IA et par paire
        self.stats_ia = {
            ia: {"wins": 0, "losses": 0, "draws": 0, "total_matches": 0, "total_turns": 0, "total_units_left": 0,
                 "total_time": 0, "total_tps": 0.0} for ia in self.generals}
        # Matrice de confrontation : matrix[ia1][ia2] = {"wins": 0, "losses": 0, "draws": 0}
        self.confrontation_matrix = {ia1: {ia2: {"wins": 0, "losses": 0, "draws": 0} for ia2 in self.generals} for ia1
                                     in self.generals}

        real_tps = []
        time_per_match = []
        number_turns = []
        for match in self.res_dic_brut.values():
            if not match or "error" in match:
                continue

            ia1 = fix_string(match["ia1"])
            ia2 = fix_string(match["ia2"])
            winner = fix_string(match["winner_ia"])
            turns = match["turn"]
            duration = match["time_from_start"]
            units1 = match["units_ia1"]
            units2 = match["units_ia2"]
            tps = match.get("real_tps", 0)

            real_tps.append(tps)
            time_per_match.append(duration)
            number_turns.append(turns)

            # Mise à jour des stats globales par IA
            self.stats_ia[ia1]["total_matches"] += 1
            self.stats_ia[ia2]["total_matches"] += 1
            self.stats_ia[ia1]["total_turns"] += turns
            self.stats_ia[ia2]["total_turns"] += turns
            self.stats_ia[ia1]["total_time"] += duration
            self.stats_ia[ia2]["total_time"] += duration
            self.stats_ia[ia1]["total_tps"] += tps
            self.stats_ia[ia2]["total_tps"] += tps
            if winner == ia1:
                self.stats_ia[ia1]["wins"] += 1
                self.stats_ia[ia2]["losses"] += 1
                self.stats_ia[ia1]["total_units_left"] += units1
                self.confrontation_matrix[ia1][ia2]["wins"] += 1
                self.confrontation_matrix[ia2][ia1]["losses"] += 1
            elif winner == ia2:
                self.stats_ia[ia2]["wins"] += 1
                self.stats_ia[ia1]["losses"] += 1
                self.stats_ia[ia2]["total_units_left"] += units2
                self.confrontation_matrix[ia2][ia1]["wins"] += 1
                self.confrontation_matrix[ia1][ia2]["losses"] += 1
            else:
                self.stats_ia[ia1]["draws"] += 1
                self.stats_ia[ia2]["draws"] += 1
                self.confrontation_matrix[ia1][ia2]["draws"] += 1
                self.confrontation_matrix[ia2][ia1]["draws"] += 1

        if real_tps:
            self.res_dic_stat["real_tps_avg"] = sum(real_tps) / len(real_tps)
            self.res_dic_stat["real_tps_sigma"] = np.std(real_tps)
            self.res_dic_stat["time_per_match_avg"] = sum(time_per_match) / len(time_per_match)
            self.res_dic_stat["number_turns_avg"] = sum(number_turns) / len(number_turns)

        self.res_dic_stat["total_time"] = self.total_execution_time
        return self.res_dic_stat

    def end_tournament(self):
        # Récupération des stats du tournoi
        stats = self.stat_tournaments()

        report_data = {
            "total_execution_time": self.total_execution_time,
            "generals": self.generals,
            "scenarios_count": len(self.scenarios),
            "matches_per_pair": self.matches_per_pair,
            "stats_summary": stats,
            "stats_ia": self.stats_ia,
            "confrontation_matrix": self.confrontation_matrix,
            "res_dic_brut": self.res_dic_brut
        }

        generate_report('tournament', report_data, self.out_file)
        return None
