# Module Réseau C (C-to-C)

Ce dossier contient toute la logique réseau et IPC (mémoire partagée) pour synchroniser l'état du jeu entre différents PC participants.

> **⚠️ ATTENTION (Utilisateurs Windows)**
> La mémoire partagée et les sémaphores POSIX utilisés ici ne fonctionnent pas sur Windows natif. 
> Vous **devez absolument utiliser WSL** (ex: Ubuntu) pour compiler et lancer ce code !

---

## 🛠 Compilation

Pour compiler le programme principal en C :

```bash
cd c_network
make
```

Cela va générer un exécutable `c_net` et un exécutable `test_ipc`.

---

## 🚀 Utilisation : Lancement du réseau

L'exécutable doit être lancé sur chaque poste avec un **identifiant (peer id) unique**, suivi des adresses IP de tous les autres participants.

> **Syntaxe :** `./c_net <mon_peer_id> <ip_pair1> [<ip_pair2> ...]`

### Exemple de configuration à 2 PC :
- **PC A** (votre machine, identifiée comme peer 0) : vous devez pointer vers le PC B (ex IP: 192.168.1.2)
  ```bash
  ./c_net 0 192.168.1.2
  ```
- **PC B** (votre ami, identifié comme peer 1) : il doit pointer vers le PC A (ex IP: 192.168.1.1)
  ```bash
  ./c_net 1 192.168.1.1
  ```

*Note : la boucle réseau va attendre que la partie graphique (Python) crée la mémoire partagée et commence à écrire dedans. Côté C, le process ne fait "que" lire la mémoire locale, l'envoyer via des sockets UDP, et répercuter les informations entrantes sur la mémoire locale.*

---

## 🧪 Tester l'IPC (sans Python et sans Réseau)

Si vous voulez vérifier que la communication via la mémoire partagée fonctionne bien sur votre OS, sans avoir encore l'application Python complète :

```bash
# Compilation ciblée (si pas fait par le make)
gcc -Wall -g -I../shared -o test_ipc test_ipc.c ipc.c -lrt -lpthread

# Lancement du test
./test_ipc
```

Ce script simule Python : il ouvre un segment de mémoire (shm), y écrit l'état de 3 fausses unités, et relit ce segment juste après pour valider que ça fonctionne.

---

## 🧹 Nettoyage des ressources bloquées

Si le programme plante ou est arrêté brutalement de mauvaise manière, la mémoire partagée (`/dev/shm/battle_state`) ou les sémaphores peuvent rester ouverts indéfiniment en mode zombie, ce qui va bloquer un prochain lancement.

Pour tout nettoyer proprement, exécutez la commande Make suivante :

```bash
make clean-ipc
```

## Structure des sous-modules
- `ipc.c` / `ipc.h` : Logique de mémoire partagée et de sémaphores avec le process Python. C'est ici que C écrit et lit la synchronisation locale.
- `network.c` / `network.h` : Gestion des sockets UDP. Connecte ce poste aux autres "pairs" pour envoyer les unités.
- `protocol.c` / `protocol.h` : Intercepte les messages réseau (depuis l'udp) pour mettre à jour la mémoire locale selon la logique du jeu (ex: mettre à jour la position ou la HP d'une unité adverse).
- `main.c` : Point d'entrée à 60Hz. Lit les unités modifiées en local -> broadcast -> reçoit réseau -> mets à jour local...
