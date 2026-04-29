# DÉMONSTRATION — Système de Propriété Réseau

## Vue d'ensemble

Ce document explique comment démontrer les 7 points clés du système de propriété réseau pour la bataille distribuée.

### Les 7 Points à Démontrer

1. ✅ **Un jeu demande la propriété réseau avant une action**
2. ✅ **Le propriétaire envoie la propriété et l'état de la ressource**
3. ✅ **Le demandeur vérifie si l'action est possible à la réception**
4. ✅ **Il réalise la mise à jour la scène locale de façon visuelle**
5. ✅ **Il transmet la mise à jour pour les participants distants**
6. ✅ **La réception de la mise jour modifie la scène du participant distant**
7. ✅ **Le jeu produit un déroulement cohérent qui est démontrable**

---

## Tags de Logs Disponibles

### Handshake Réseau
```
[DEMO-SHAKE] — Échange HELLO/READY entre pairs
Exemple: "[DEMO-SHAKE] Peer 0 envoie HELLO"
        "[DEMO-SHAKE] Peer 1 reçu HELLO de peer 0 (1/2 pairs)"
        "[DEMO-SHAKE] ✓ Handshake complet (peer 1) !"
```

### Décisions et Actions IA
```
[DEMO-DECIDE] — Décision de l'IA pour une unité
[DEMO-ACTION] — Exécution d'une action (mouvement, attaque)
Exemple: "[DEMO-DECIDE] IA ROUGE décide pour unit #5 (K@(100,50))"
        "[DEMO-ACTION] Exécution: unit #5 déplacé vers (105,50)"
```

### Demande de Propriété
```
[DEMO-REQ] — Demande de propriété réseau
[DEMO-OWN] — Accord/Refus de propriété
Exemple: "[DEMO-REQ] Peer 0: DEMANDE propriété unit #7"
        "[DEMO-OWN] ✓ Peer 1: ACCORDE propriété unit #7 à peer 0"
        "[DEMO-OWN] ✗ Peer 1: REFUSE propriété unit #7 (propriétaire: peer 1)"
```

### Synchronisation Réseau
```
[DEMO-NET]      — Broadcast de l'état via le processus C
[DEMO-BROADCAST]— Envoi de l'état local via Python
[DEMO-SYNC]     — Réception et application de l'état distant
Exemple: "[DEMO-NET] Peer 0: BROADCAST unit #5 @(105.0,50.0) HP=45 owner=0"
        "[DEMO-BROADCAST] Peer 0: BROADCAST unit #5 @(105,50) HP=45"
        "[DEMO-SYNC] Peer 1: reçu état unite #5 @(105.0,50.0) owner=0"
        "[DEMO-SYNC] ✓ Propriété ACQUISE: unit #7 (peer 1 → 0)"
```

---

## Scénario de Démonstration

### Prérequis
- Deux machines ou deux terminaux avec forwarding réseau
- Compilé: `cd c_network && make clean && make`
- Python 3.9+

### Étape 1: Lancer le Processus Réseau (Peer 0)

**Terminal 1 — Machine A ou localhost:**
```bash
cd c_network
./c_net 0 127.0.0.1:5556
# Résultat attendu:
# [main] Demarrage — peer_id=0
# [main] Port local : 5555
# [DEMO-SHAKE] Peer 0 envoie HELLO
# ... attend le pair 1
```

### Étape 2: Lancer le Processus Réseau (Peer 1)

**Terminal 2 — Machine B ou localhost (port 5556):**
```bash
cd c_network
NET_PORT=5556 ./c_net 1 127.0.0.1:5555
# Résultat attendu:
# [main] Demarrage — peer_id=1
# [main] Port local : 5556
# [DEMO-SHAKE] Peer 1 envoie HELLO
# [DEMO-SHAKE] Peer 1 reçu HELLO de peer 0 (1/2 pairs)
# ... puis peu après:
# [DEMO-SHAKE] ✓ Handshake complet (peer 1) !
```

**Terminal 1 — Devrait afficher:**
```
[DEMO-SHAKE] Peer 0 reçu HELLO de peer 1 (1/2 pairs)
[DEMO-SHAKE] Peer 0 envoie READY à peer 1
[DEMO-SHAKE] ✓ Handshake complet (peer 0) !
```

### Étape 3: Lancer le Jeu (Peer 0 — Équipe Rouge)

**Terminal 3 — Machine A ou localhost:**
```bash
cd p_game
python3 main.py run stest1 smart_ia brain_dead \
  --distributed \
  --local-team R \
  --p2p-port 5555 \
  --terminal

# Résultat attendu (logs de démarrage):
# [RUN] Scenario: stest1
#       Mode: Réparti (Équipe locale: R)
# [engine] Équipe R initialise...
# [NETWORK] Bridge SHM initialisé (peer_id=0)
# [engine] En attente de la connexion de l'adversaire...
# ... (en attente que peer 1 soit prêt)
```

### Étape 4: Lancer le Jeu (Peer 1 — Équipe Bleue)

**Terminal 4 — Machine B ou localhost (port 5556):**
```bash
cd p_game
NET_PORT=5556 python3 main.py run stest1 brain_dead smart_ia \
  --distributed \
  --local-team B \
  --p2p-port 5556 \
  --terminal

# Les jeux démarrent ensemble et affichent les logs de démonstration
```

### Étape 5: Observer les Logs

Pendant la bataille, vous verrez (sur Terminal 1 & 2 — processus C):
```
[DEMO-SHAKE] — Phase de handshake (voir ci-dessus)
[DEMO-NET] Peer 0: BROADCAST unit #0 @(100.0,50.0) HP=50 owner=0
[DEMO-NET] Peer 0: DEMANDE propriété unit #10
```

Pendant la bataille (Terminals 3 & 4 — processus Python):
```
[DEMO-DECIDE] IA ROUGE décide pour unit #0 (C@(100,50))
[DEMO-ACTION] Exécution: unit #0 déplacé vers (105,50)
[DEMO-BROADCAST] Peer 0: BROADCAST unit #0 @(105,50) HP=50
[DEMO-REQ] Peer 1: DEMANDE propriété unit #7
[DEMO-SYNC] Peer 1: reçu état unite #0 @(105.0,50.0) owner=0
```

---

## Validation des 7 Points

### Point 1: Un jeu demande la propriété réseau avant une action
**Recherchez:** `[DEMO-REQ]` and `[DEMO-DECIDE]`
```
[DEMO-DECIDE] IA ROUGE décide pour unit #5 ...
[DEMO-REQ] Peer 0: DEMANDE propriété unit #5
```

### Point 2: Le propriétaire envoie la propriété et l'état de la ressource
**Recherchez:** `[DEMO-OWN] ✓ ... ACCORDE`
```
[DEMO-OWN] ✓ Peer 1: ACCORDE propriété unit #5 à peer 0
[DEMO-NET] Peer 1: BROADCAST unit #5 @(100.0,50.0) HP=50 owner=0
```

### Point 3: Le demandeur vérifie si l'action est possible à la réception
**Recherchez:** `[DEMO-SYNC] ✓ Propriété ACQUISE`
```
[DEMO-SYNC] ✓ Propriété ACQUISE: unit #5 (peer 1 → 0)
```

### Point 4: Il réalise la mise à jour la scène locale de façon visuelle
**Observable dans:** L'affichage terminal/GUI (unit bouge, couleur change)
```
[DEMO-ACTION] Exécution: unit #5 déplacé vers (105,50)
(L'unité apparaît à sa nouvelle position)
```

### Point 5: Il transmet la mise à jour pour les participants distants
**Recherchez:** `[DEMO-BROADCAST]`
```
[DEMO-BROADCAST] Peer 0: BROADCAST unit #5 @(105,50) HP=50
```

### Point 6: La réception de la mise jour modifie la scène du participant distant
**Recherchez:** `[DEMO-SYNC] Peer 1: reçu état unite`
```
[DEMO-SYNC] Peer 1: reçu état unite #5 @(105.0,50.0) owner=0
(L'unité distante se synchronise à la même position)
```

### Point 7: Le jeu produit un déroulement cohérent qui est démontrable
**Validation globale:**
- Les deux instances Python affichent les mêmes unités aux mêmes positions
- Les stats (HP) sont synchronisées
- Les morts sont propagées rapidement
- Pas de désynchronisation visuelle persistante (sauf délai réseau)

---

## Commandes Rapides

### Démonstration locale (2 pairs sur localhost)

**Terminal 1:**
```bash
cd c_network && ./c_net 0 127.0.0.1:5556 &
cd p_game && python3 main.py run stest7 smart_ia brain_dead \
  --distributed --local-team R --terminal
```

**Terminal 2:**
```bash
cd c_network && NET_PORT=5556 ./c_net 1 127.0.0.1:5555 &
cd p_game && NET_PORT=5556 python3 main.py run stest7 brain_dead smart_ia \
  --distributed --local-team B --terminal
```

### Capturer les logs pour rapport

```bash
# Terminal 1 (Peer 0)
./c_net 0 127.0.0.1:5556 2>&1 | tee logs_peer0_c.txt
python3 main.py run stest7 smart_ia brain_dead ... 2>&1 | tee logs_peer0_py.txt

# Terminal 2 (Peer 1)
NET_PORT=5556 ./c_net 1 127.0.0.1:5555 2>&1 | tee logs_peer1_c.txt
NET_PORT=5556 python3 main.py run stest7 brain_dead smart_ia ... 2>&1 | tee logs_peer1_py.txt

# Analyse globale
grep -E "DEMO-" logs_peer*.txt | sort
```

---

## Données de Présentation

### Fichiers Clés à Montrer

1. **c_network/protocol.c** — Gestion des messages (MSG_OWN_REQUEST, MSG_OWN_GRANT)
2. **p_game/network_bridge.py** — Synchronisation SHM et demandes
3. **p_game/battle/engine.py** — Décisions et actions de l'IA
4. **shared/protocol.h** — Définitions partagées

### Code à Mettre en Évidence

**Demande de propriété (Python):**
```python
if getattr(unit, 'pending_ownership_request', False):
    slot.id    = uid
    slot.dirty = 2  # Marque comme demande
```

**Accord de propriété (C):**
```c
if (local_unit->owner_peer == local_state->my_peer_id) {
    printf("[DEMO-OWN] ✓ Peer %d: ACCORDE propriété unite %d à peer %d\n",
           local_state->my_peer_id, uid, msg->sender_id);
    local_unit->owner_peer = msg->sender_id;
    net_send_to(msg->sender_id, &grant);  // Envoie MSG_OWN_GRANT
}
```

**Synchronisation de réception (Python):**
```python
old_owner = unit.owner_id
unit.owner_id = slot.owner_peer
unit.is_local = (unit.owner_id == my_peer)

if unit.is_local and old_owner != my_peer:
    print(f"[DEMO-SYNC] ✓ Propriété ACQUISE: unit #{uid}")
```

---

## Troubleshooting

### Les logs [DEMO-SHAKE] ne s'affichent pas
- Vérifier que les deux processus C se trouvent en réseau
- Vérifier les adresses IP/ports: `netstat -tuln | grep 555`

### Les logs [DEMO-SYNC] n'apparaissent qu'une fois
- Normal : les mises à jour réseau sont delta-codées
- On ne voit les logs que si l'état change

### Les unités ne se synchronisent pas
- Vérifier que `python_ready=1` dans la SHM
- Vérifier les processus: `ps aux | grep -E "c_net|main.py"`

### Les demandes de propriété restent bloquées
- Vérifier que les unités ont `is_local=True` ou `is_local=False` cohérent
- Vérifier `dirty=2` dans la SHM

---

## Points Importants pour la Présentation

1. **Montrer les logs en temps réel** (pas de captures statiques si possible)
2. **Pointer les étapes 1→7** dans l'ordre pendant la démonstration
3. **Montrer la synchronisation visuelle** (terminal ou GUI) en même temps que les logs
4. **Montrer un conflit résolu** (par ex. si deux pairs demandent la même unité)
5. **Quantifier la cohérence** (1 tick = ~16ms, logs < 100ms de latence)

