# GUIDE DE PRÉSENTATION — Système de Propriété Réseau

**Date:** 29 Avril 2026  
**Projet:** MedievAIl — Réseau & Système  
**Pour montrer les 7 points clés devant le jury**

---

## 📊 Vue d'Ensemble (2 minutes)

### Starts with this slide:
**"7 Points du Système de Propriété Réseau"**

```
1️⃣ Un jeu demande la propriété réseau avant une action
2️⃣ Le propriétaire envoie la propriété et l'état de la ressource
3️⃣ Le demandeur vérifie si l'action est possible à la réception
4️⃣ Il réalise la mise à jour la scène locale de façon visuelle
5️⃣ Il transmet la mise à jour pour les participants distants
6️⃣ La réception de la mise jour modifie la scène du participant distant
7️⃣ Le jeu produit un déroulement cohérent qui est démontrable
```

### Architecture (avec diagramme)
```
┌──────────────────┐  IPC (SHM)  ┌──────────────────┐
│ Jeu Python P0    │ ◄────────► │ Réseau C - P0    │
│ (Équipe Rouge)   │             │ (Port 5555)      │
└──────────────────┘             └──────────────────┘
                                        │ UDP
                                        ▼
                                   ┌──────────────┐
                                   │ Internet/LAN │
                                   └──────────────┘
                                        │ UDP
                                        ▼
┌──────────────────┐  IPC (SHM)  ┌──────────────────┐
│ Jeu Python P1    │ ◄────────► │ Réseau C - P1    │
│ (Équipe Bleue)   │             │ (Port 5556)      │
└──────────────────┘             └──────────────────┘
```

---

## 🎯 DÉMONSTRATION EN DIRECT (8 minutes)

### Prérequis
- ✅ Code compilé: `cd c_network && make`
- ✅ Python 3.9+ avec dépendances
- ✅ Deux terminaux (ou deux machines en réseau)

### Commande 1️⃣: Lancer Processus Réseau Peer 0

**Terminal 1 — Processus Réseau:**
```bash
cd c_network
./c_net 0 127.0.0.1:5556
```

**Attendez:** `[DEMO-SHAKE] Peer 0 envoie HELLO`

### Commande 2️⃣: Lancer Processus Réseau Peer 1

**Terminal 2 — Processus Réseau:**
```bash
cd c_network
NET_PORT=5556 ./c_net 1 127.0.0.1:5555
```

**Attendez:**
```
[DEMO-SHAKE] Peer 1 envoie HELLO
[DEMO-SHAKE] Peer 1 reçu HELLO de peer 0
[DEMO-SHAKE] ✓ Handshake complet (peer 1) !
```

**Terminal 1 devrait afficher:**
```
[DEMO-SHAKE] ✓ Handshake complet (peer 0) !
```

### Commande 3️⃣: Lancer Jeu Peer 0

**Terminal 3 — Jeu P0:**
```bash
cd p_game
python3 main.py run stest7 smart_ia brain_dead \
  --distributed --local-team R --terminal
```

**Attendez:** Message de synchronisation

### Commande 4️⃣: Lancer Jeu Peer 1

**Terminal 4 — Jeu P1:**
```bash
cd p_game
NET_PORT=5556 python3 main.py run stest7 brain_dead smart_ia \
  --distributed --local-team B --terminal
```

**À partir d'ici les logs de démonstration s'affichent:**

---

## 🔍 QU'OBSERVER PENDANT LA BATAILLE

### Point 1: IA Demande Propriété
```
Terminal 3/4: [DEMO-REQ] Peer X: DEMANDE propriété unit #N
Terminal 3/4: [DEMO-DECIDE] IA décide pour unit #N
```
✅ **Preuve:** L'IA ne joue que si elle est propriétaire (sinon elle demande)

### Point 2: Propriétaire Envoie Propriété
```
Terminal 1/2: [DEMO-OWN] ✓ Peer X: ACCORDE propriété unite #N à peer Y
Terminal 1/2: [DEMO-NET] Peer X: BROADCAST unit #N @(...) owner=Y
```
✅ **Preuve:** L'accord contient le nouvel owner ET l'état complet

### Point 3: Demandeur Vérifie et Accepte
```
Terminal 1/2: [DEMO-OWN] ✓ Peer Y: REÇOIT propriété unite #N de peer X
Terminal 3/4: [DEMO-SYNC] ✓ Propriété ACQUISE: unit #N (peer X → Y)
```
✅ **Preuve:** Propriété transférée atomiquement, Y devient local owner

### Point 4: Mise à Jour Visuelle Locale
```
Terminal 3: Unit se déplace sur l'écran
Terminal 4: Unit correspondante se synchronise avec la même position
```
✅ **Preuve:** Affichage terminal montre les units à leur position correcte

### Point 5: Transmission pour Distants
```
Terminal 3/4: [DEMO-BROADCAST] Peer X: BROADCAST unit #N @(x,y) HP=H
Terminal 1/2: [DEMO-NET] Peer X: BROADCAST unit #N @(x,y) HP=H owner=X
```
✅ **Preuve:** État local envoyé via SHM → C → UDP

### Point 6: Réception Modifie Distants
```
Terminal 1/2: [DEMO-SYNC] Peer Y: reçu état unite #N @(x,y) owner=X
Terminal 3/4: [DEMO-SYNC] Peer Y: reçu état unite #N @(x,y) owner=X
```
✅ **Preuve:** Pair distant se synchronise avec position/HP/propriétaire

### Point 7: Déroulement Cohérent
```
FLUX COMPLET VISIBLE:
T=100ms [DEMO-DECIDE] IA ROUGE décide unit #5
T=102ms [DEMO-ACTION] Exécution unit #5
T=105ms [DEMO-BROADCAST] Envoi état local
T=110ms [DEMO-NET] Broadcast réseau
T=125ms [DEMO-SYNC] Réception côté pair 1
→ Aucune race condition, ordre préservé
```
✅ **Preuve:** Logs temps-réel montrent séquence atomique

---

## 📁 FICHIERS À MONTRER AU JURY

### 1. Architecture (5 min)
- **Diagramme:** `README.md` section Architecture
- **Structure:** `ls -la` pour montrer séparation C/Python

### 2. Implémentation (10 min)

#### Demande de Propriété
**Montrer:** [p_game/network_bridge.py](p_game/network_bridge.py#L310)
```python
if getattr(unit, 'pending_ownership_request', False):
    slot.id    = uid
    slot.dirty = 2  # Marque comme demande de propriété
```

#### Accord de Propriété
**Montrer:** [c_network/protocol.c](c_network/protocol.c#L165)
```c
case MSG_OWN_REQUEST: {
    if (local_unit->owner_peer == local_state->my_peer_id) {
        printf("[DEMO-OWN] ✓ Accorde propriété...\n");
        net_send_to(msg->sender_id, &grant);  // Envoie MSG_OWN_GRANT
    }
}
```

#### Synchronisation
**Montrer:** [p_game/network_bridge.py](p_game/network_bridge.py#L280)
```python
unit.owner_id = slot.owner_peer
unit.is_local = (unit.owner_id == my_peer)
if unit.is_local and old_owner != my_peer:
    print(f"[DEMO-SYNC] ✓ Propriété ACQUISE: unit #{uid}")
```

### 3. Logs de Démonstration (15 min)

**Capturer les logs:**
```bash
# Terminal 1
./c_network/c_net 0 127.0.0.1:5556 2>&1 | tee logs_p0_c.txt

# Terminal 2
NET_PORT=5556 ./c_network/c_net 1 127.0.0.1:5555 2>&1 | tee logs_p1_c.txt

# Terminal 3
python3 main.py run stest7 smart_ia brain_dead ... 2>&1 | tee logs_p0_py.txt

# Terminal 4
NET_PORT=5556 python3 main.py run stest7 brain_dead smart_ia ... 2>&1 | tee logs_p1_py.txt
```

**Analyser après:**
```bash
cat logs_*_*.txt | grep DEMO- | sort -t: -k3 -n
```

### 4. Documentation Complète
- **DEMO.md** — Guide détaillé de démonstration
- **RAPPORT.md** — Rapport technique d'implémentation
- **verify_implementation.sh** — Validation automatique

---

## ⏱️ TIMING RECOMMANDÉ

| Étape | Durée | Quoi Faire |
|-------|-------|-----------|
| 0️⃣ Intro | 2 min | Expliquer les 7 points |
| 1️⃣ Architecture | 2 min | Montrer diagramme et code clé |
| 2️⃣ Démarrage | 3 min | Lancer P0 C, P1 C (attendre handshake) |
| 3️⃣ Jeu | 5 min | Lancer P0 Jeu, P1 Jeu (observer logs) |
| 4️⃣ Analyse | 5 min | Montrer les 7 points dans les logs |
| 5️⃣ Q/R | 3 min | Répondre aux questions |

---

## 🎯 RÉPONSES AUX QUESTIONS PROBABLES

### Q: "Pourquoi pas de serveur central?"
**R:** P2P scalable, pas de point de défaillance unique. Chaque pair décide en fonction de la propriété locale.

### Q: "Comment évitez-vous les race conditions?"
**R:** MSG_OWN_REQUEST/GRANT atomiques. Propriétaire valide et transfère en une seule transaction.

### Q: "Quel est le latency?"
**R:** ~10-100ms (UDP + SHM). Affichage se synchronise au tick suivant (~16ms).

### Q: "Que se passe si le réseau est perdu?"
**R:** Fallback local: chacun possède ses propres unités. Rejoin synchronise après rétablissement.

### Q: "Les logs vont où?"
**R:** `stdout`. Capturés avec `2>&1 | tee logs.txt` ou filtrés avec `grep DEMO-`.

---

## ✅ CHECKLIST DE PRÉSENTATION

- [ ] Code compilé: `cd c_network && make`
- [ ] 2+ terminaux ouverts ou 2 machines en réseau
- [ ] Lancer demo.sh OU faire étapes manuellement
- [ ] Monitorer Terminal 1-2 pour [DEMO-SHAKE], [DEMO-NET], [DEMO-OWN]
- [ ] Monitorer Terminal 3-4 pour [DEMO-DECIDE], [DEMO-ACTION], [DEMO-BROADCAST], [DEMO-SYNC]
- [ ] Montrer les fichiers code clés
- [ ] Pointer chaque point dans les logs en temps réel
- [ ] Valider avec `verify_implementation.sh` avant présentation

---

## 🎓 RESSOURCES SUPPLÉMENTAIRES

**Pour le jury:**
- [README.md](README.md) — Overview du projet
- [RAPPORT.md](RAPPORT.md) — Rapport technique complet
- [DEMO.md](DEMO.md) — Guide détaillé de démonstration

**Pour validation:**
```bash
./verify_implementation.sh  # Passe automatiquement les 7 points
```

**Pour rejouer la démo:**
```bash
bash scripts/launch.sh      # Lance les processus
# ou manuellement avec les 4 commandes ci-dessus
```

---

## 🚀 TL;DR — Lancer la Démo en 2 minutes

```bash
# Terminal 1 (Processus réseau pair 0)
cd c_network && ./c_net 0 127.0.0.1:5556

# Terminal 2 (Processus réseau pair 1)
cd c_network && NET_PORT=5556 ./c_net 1 127.0.0.1:5555

# Terminal 3 (Jeu pair 0 — Équipe Rouge)
cd p_game && python3 main.py run stest7 smart_ia brain_dead \
  --distributed --local-team R --terminal

# Terminal 4 (Jeu pair 1 — Équipe Bleue)
cd p_game && NET_PORT=5556 python3 main.py run stest7 brain_dead smart_ia \
  --distributed --local-team B --terminal
```

**Observez les logs `[DEMO-*]` pour suivre les 7 points.**

