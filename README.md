# MedievAIl — BAIttle GenerAIl · Répartition réseau

**Projet Programmation Réseau & Système — INSA 2025-2026**

Simulation de batailles médiévales où des IAs s'affrontent sur une carte partagée en réseau, sans serveur central.

---

## Objectif du projet

Étendre le jeu MedievAIl (projet Python précédent) pour permettre à **plusieurs IAs de combattre en réseau** sur une architecture **entièrement répartie** (peer-to-peer, aucun serveur).

Chaque participant :
- Dispose d'une **copie locale** de la bataille
- Gère sa propre **IA combattante**
- Observe les actions des autres IAs en **temps réel** (best-effort)

### Principe clé : la propriété réseau

La cohérence est garantie par un mécanisme de **propriété réseau cessible** :
- Chaque entité du jeu (unité, case, objet) a un **propriétaire réseau unique** à un instant donné
- Pour interagir avec une entité distante, une IA doit **demander la propriété** à son détenteur actuel
- Le propriétaire transmet la **propriété + l'état cohérent** de la ressource
- Cela résout les conflits de concurrence sans serveur

---

## Architecture

Le projet impose **deux processus séparés** communiquant via IPC :

```
┌─────────────────────┐         IPC (SHM + sém.)         ┌──────────────────────┐
│   Processus Python  │ ◄──────────────────────────────► │   Processus C        │
│                     │                                   │                      │
│  • Moteur de jeu    │                                   │  • Sockets réseau    │
│  • IA               │                                   │  • Envoi/réception   │
│  • Affichage        │                                   │  • Protocoles        │
│  • Logique métier   │                                   │  • Threads           │
└─────────────────────┘                                   └──────────────────────┘
                                                                   │
                                                          UDP/TCP  │
                                                                   ▼
                                                          ┌──────────────────┐
                                                          │  Pairs distants  │
                                                          │  (autres joueurs)│
                                                          └──────────────────┘
```

---

## Structure du projet

```
.
├── README.md                  # Ce fichier
├── Répartition IAs 25 26.pdf  # Sujet complet du projet
│
├── shared/                    # Contrat partagé C ↔ Python
│   └── protocol.h             # Structures de données (layout mémoire identique)
│
├── c_network/                 # Processus C — réseau & IPC
│   ├── Makefile
│   ├── main.c                 # Point d'entrée du processus C
│   ├── ipc.c / ipc.h          # Mémoire partagée POSIX + sémaphore
│   ├── network.c / network.h  # Sockets réseau (UDP/TCP)
│   └── protocol.c / protocol.h# Sérialisation des messages réseau
│
├── p_game/                    # Processus Python — jeu & IA
│   ├── main.py                # Point d'entrée du jeu
│   ├── shared_state.py        # Miroir Python des structures C (ctypes)
│   ├── network_bridge.py      # Pont Python vers la mémoire partagée
│   ├── battle/                # Moteur de jeu
│   │   ├── engine.py          # Boucle de jeu principale
│   │   ├── map.py             # Gestion de la carte et collisions
│   │   ├── unit.py            # Unités de combat
│   │   ├── projectile.py      # Projectiles (flèches, lances)
│   │   └── scenario.py        # Chargement des scénarios
│   ├── ia/                    # IAs disponibles
│   │   ├── base_general.py    # Classe mère de toutes les IAs
│   │   ├── smart_ia.py        # IA avancée
│   │   ├── basic_ia.py        # IA basique
│   │   └── ...                # Autres IAs
│   ├── visuals/               # Affichage
│   │   ├── gui_view.py        # Vue graphique 2.5D (Pygame)
│   │   └── terminal_view.py   # Vue ASCII terminal
│   └── data/                  # Assets (sprites, scénarios, sauvegardes)
│
└── scripts/                   # Scripts utilitaires
    ├── launch.sh              # Lancement des deux processus
    └── test_network.sh        # Tests IPC C ↔ Python
```

---

## Livrables — Version 1 (partage best-effort)

Partage de scène en temps réel **sans garantie de cohérence** :

| # | Exigence | Description |
|---|----------|-------------|
| 1 | Placement initial | Chaque joueur place ses unités dans la scène à son arrivée |
| 2 | Envoi immédiat | L'IA envoie une mise à jour dès qu'elle modifie la scène |
| 3 | Réception distante | La mise à jour modifie la scène du joueur distant |
| 4 | Concurrence sauvage | Un nouvel arrivant place ses ressources sans synchronisation |
| 5 | Incohérences visibles | On accepte les incohérences (remplacement brutal, etc.) |
| 6 | Interaction croisée | L'IA locale peut interagir avec les unités de l'IA distante |
| 7 | Best-effort | La simulation tourne au mieux, décalages temporels acceptés |

---

## Livrables — Version 2 (cohérence par propriété réseau)

Ajout de la **propriété réseau** pour garantir la cohérence :

| # | Exigence | Description |
|---|----------|-------------|
| 1 | Demande de propriété | Le jeu demande la propriété réseau avant toute action |
| 2 | Transfert propriété + état | Le propriétaire envoie la propriété et l'état courant |
| 3 | Vérification | Le demandeur vérifie si l'action est possible à réception |
| 4 | Mise à jour locale | Il met à jour la scène locale de façon visuelle |
| 5 | Propagation | Il transmet la mise à jour aux participants distants |
| 6 | Application distante | La réception modifie la scène du participant distant |
| 7 | Cohérence démontrable | Le déroulement du jeu est cohérent et démontrable |

---

## Lancement

### Prérequis

- Python 3.10+
- GCC (C11)
- Pygame (`pip install pygame`)
- Système POSIX (Linux/macOS) — support de `shm_open`, `sem_open`, `mmap`

### Jeu solo (sans réseau)

```bash
cd p_game
python3 main.py run stest6 smartia majordaft
```

### Compilation du processus C

```bash
make -C c_network
```

### Test IPC C ↔ Python

```bash
bash scripts/test_network.sh
```

### Lancement réseau (2 joueurs)

```bash
bash scripts/launch.sh IP COULEUR IA
```

---

## Contrôles

### Mode terminal
| Touche | Action |
|--------|--------|
| `Z/Q/S/D` ou flèches | Déplacement caméra |
| `P` | Pause |
| `C` | Passer en mode graphique |
| `Tab` | Générer un rapport de bataille |
| `T` | Sauvegarde rapide |

### Mode graphique (2.5D)
| Touche | Action |
|--------|--------|
| `Z/Q/S/D` | Déplacement caméra |
| `Shift` | Déplacement rapide |
| `P` | Pause |
| `Molette` | Zoom |
| `M` | Dézoom global |
| `↑/↓` | Vitesse de jeu |
| `C` | Sauvegarde rapide |
| `V` | Chargement rapide |
| `F3` | Infos supplémentaires |
| `F9` | Revenir en mode terminal |
| `H/T/R/X/L` | Debug : hitbox / cibles / portée / sprites / ligne de vue |

---

## Contraintes techniques

- **Réseau entièrement en C** via l'API socket
- **Deux processus obligatoires** : Python (jeu) + C (réseau)
- **Communication inter-processus** : mémoire partagée POSIX + sémaphores
- **Pas de serveur** : architecture entièrement peer-to-peer
- **Pas de tours** : les IAs agissent en continu, sans attendre de tour de jeu

---

## Axes d'amélioration (bonus)

- **Passage à l'échelle** : supporter > 2 joueurs, mesurer les performances
- **Sécurité** : chiffrement TLS, signatures des messages, anti-rejeu
- **Multi-plateforme** : support Windows (Winsock, `CreateFileMapping`)
- **Monde infini** : génération procédurale via graines partagées
- **Alliances et trahisons** : règles de coopération/compétition avancées
