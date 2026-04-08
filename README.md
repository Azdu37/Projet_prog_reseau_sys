# 🏰 MedievAIl – BAIttle GenerAIl

**Projet Python 2025–2026**  
Simulation automatique de batailles médiévales avec IA inspirée d’Age of Empires II.

Le but : créer un moteur de combat où des généraux IA commandent des armées sur une carte en temps réel, avec des stratégies variées.

Voici les différentes touches à utiliser :
En mode terminal : 

  zqsd ou flèches -> déplacement
  p -> pause
  c -> passer au mode graphique
  tab -> genere un rapport de bataille
  t -> sauvegarde rapide

En mode graphique :

  zqsd -> deplacement
  SHIFT -> deplacement rapide
  p -> Pause
  Molette -> zoom
  m -> dezoom global
  fleche haut ou bas -> accelerer ou ralentir la vitesse de jeu
  c -> quicksave
  v -> quickload

  f3 -> affichage d'infos supplémentaires
  f9 -> passer en mode terminal
  h -> affichage hitbox
  t -> affichage target
  r -> affichage range
  x -> affichage sprites
  l -> affichage ligne de vue
  tab -> genere un rapport de bataille
---

## 📂 Structure du projet

```plaintext
medievail/
├── core/                  # Logique du moteur de jeu
│   ├── map.py             # Gestion de la carte
│   ├── unit.py            # Classes des unités
│   ├── battle.py          # Boucle de combat
│   ├── physics.py         # Calcul des déplacements et collisions
│   └── utils.py           # Fonctions utilitaires
├── ai/                    # IA des généraux
│   ├── brain_dead.py      # IA passive (aucune stratégie)
│   ├── daft.py            # IA basique (attaque la cible la plus proche)
│   ├── smart_general.py   # IA avancée avec stratégie
│   └── base_general.py    # Classe mère pour toutes les IA
├── data/                  # Données des unités
│   └── units.json         # Statistiques des unités (HP, attaque, armure…)
├── scenarios/             # Scénarios de bataille
│   ├── lanchester.py      # Exemple scénario loi de Lanchester
│   ├── mirror_battle.py   # Bataille symétrique
│   └── ...                # Autres scénarios
├── cli/                   # Interface en ligne de commande
│   └── main.py
├── visuals/               # Affichage
│   ├── terminal_view.py   # Affichage ASCII
│   └── isometric_view.py  # Affichage 2.5D
├── tournament/            # Gestion des tournois IA
│   └── manager.py
└── tests/                 # Tests unitaires
