#!/bin/bash
# =============================================================================
# test_network.sh — Test de connexion C-to-C entre deux machines
#
# Ce script gère TOUT automatiquement sur UNE machine.
# Lancer simultanément sur les deux PC.
#
# Usage (dans WSL) :
#   ./scripts/test_network.sh <mon_peer_id> <ip_du_pair>
#
# Exemples :
#   PC A : ./scripts/test_network.sh 0 192.168.1.20
#   PC B : ./scripts/test_network.sh 1 192.168.1.10
#
# Test solo (une seule machine pour vérifier IPC uniquement) :
#   ./scripts/test_network.sh --solo
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."
C_DIR="$ROOT/c_network"

# ── Couleurs ─────────────────────────────────────────────────────────────────
GRN='\033[0;32m'; RED='\033[0;31m'; YLW='\033[0;33m'
BLD='\033[1m'; RST='\033[0m'
ok()   { echo -e "  ${GRN}[OK]${RST}   $*"; }
fail() { echo -e "  ${RED}[FAIL]${RST} $*"; }
info() { echo -e "  ${YLW}[>>]${RST}  $*"; }
sep()  { echo -e "${BLD}────────────────────────────────────────${RST}"; }

# ── Mode solo (test IPC uniquement, sans réseau) ──────────────────────────────
if [ "${1:-}" = "--solo" ]; then
    echo ""
    echo -e "${BLD}========================================${RST}"
    echo -e "${BLD}  TEST SOLO -- IPC uniquement (WSL)  ${RST}"
    echo -e "${BLD}========================================${RST}"
    echo ""

    cd "$C_DIR"

    # Nettoyage préalable
    make clean-ipc -s 2>/dev/null || true

    # Compilation
    info "Compilation..."
    if make c_net test_ipc -s 2>&1; then
        ok "Compilation reussie"
    else
        fail "Compilation echouee"
        exit 1
    fi
    echo ""

    sep
    echo -e "${BLD}ETAPE 1 — Lancement de c_net (cree la shm)${RST}"
    sep
    ./c_net 0 127.0.0.1 &
    C_PID=$!
    sleep 1
    if kill -0 "$C_PID" 2>/dev/null; then
        ok "c_net demarre (PID=$C_PID)"
    else
        fail "c_net s'est arrete immediatement"
        exit 1
    fi
    echo ""

    sep
    echo -e "${BLD}ETAPE 2 — Ecriture dans la shm (./test_ipc ecrire)${RST}"
    sep
    info "Ecriture de 3 unites dirty dans la shm..."
    ./test_ipc ecrire 0
    echo ""

    sep
    echo -e "${BLD}ETAPE 3 — Verification lecture (./test_ipc lire)${RST}"
    sep
    sleep 1
    ./test_ipc lire
    echo ""

    # Nettoyage
    kill "$C_PID" 2>/dev/null
    make clean-ipc -s 2>/dev/null || true
    echo ""
    echo -e "${GRN}${BLD}Test solo termine.${RST}"
    echo -e "  Pour un test reseau reel, lance depuis les 2 PC simultanément :"
    echo -e "  ${YLW}PC A :${RST} ./scripts/test_network.sh 0 <IP_PC_B>"
    echo -e "  ${YLW}PC B :${RST} ./scripts/test_network.sh 1 <IP_PC_A>"
    exit 0
fi

# ── Mode réseau (deux machines) ───────────────────────────────────────────────
PEER_ID="${1:-}"
REMOTE_IP="${2:-}"

if [ -z "$PEER_ID" ] || [ -z "$REMOTE_IP" ]; then
    echo "Usage : $0 <mon_peer_id> <ip_du_pair>"
    echo "        $0 --solo   (test IPC local, sans reseau)"
    echo ""
    echo "Exemple a 2 PC :"
    echo "  PC A : $0 0 192.168.1.20"
    echo "  PC B : $0 1 192.168.1.10"
    exit 1
fi

echo ""
echo -e "${BLD}=========================================${RST}"
echo -e "${BLD}  TEST C-TO-C -- Connexion reseau${RST}"
echo -e "${BLD}=========================================${RST}"
echo -e "  Peer ID   : ${BLD}$PEER_ID${RST}"
echo -e "  IP distant: ${BLD}$REMOTE_IP:9000${RST}  (UDP)"
echo ""

cd "$C_DIR"

# ── ETAPE 1 : Nettoyage ───────────────────────────────────────────────────────
sep
echo -e "${BLD}ETAPE 1 — Nettoyage ressources IPC precedentes${RST}"
sep
make clean-ipc -s 2>/dev/null || true
ok "Nettoyage effectue"
echo ""

# ── ETAPE 2 : Compilation ─────────────────────────────────────────────────────
sep
echo -e "${BLD}ETAPE 2 — Compilation${RST}"
sep
if make c_net test_ipc -s 2>&1; then
    ok "c_net et test_ipc compiles"
else
    fail "Erreur de compilation"
    exit 1
fi
echo ""

# ── ETAPE 3 : Lancement de c_net ─────────────────────────────────────────────
sep
echo -e "${BLD}ETAPE 3 — Lancement de c_net en arriere-plan${RST}"
sep
info "Demarrage : ./c_net $PEER_ID $REMOTE_IP"
./c_net "$PEER_ID" "$REMOTE_IP" &
C_PID=$!

sleep 1
if kill -0 "$C_PID" 2>/dev/null; then
    ok "c_net demarre (PID=$C_PID)"
    ok "Socket UDP ecoute sur port 9000"
    ok "Pair distant enregistre : $REMOTE_IP:9000"
else
    fail "c_net a plante au demarrage. Verifiez les erreurs ci-dessus."
    exit 1
fi
echo ""

# ── ETAPE 4 : Ecriture dans la shm ───────────────────────────────────────────
sep
echo -e "${BLD}ETAPE 4 — Simulation jeu : ecriture d'unites DIRTY en shm${RST}"
sep
info "Ecriture de 3 unites (dirty=1 pour les unites de ce peer)..."
echo ""
./test_ipc ecrire "$PEER_ID"
echo ""
ok "Unites dirty ecrites → c_net va les envoyer en UDP vers $REMOTE_IP"
echo ""

# ── ETAPE 5 : Attente reception ───────────────────────────────────────────────
sep
echo -e "${BLD}ETAPE 5 — Attente des paquets UDP de l'autre PC${RST}"
sep
echo ""
info "L'autre PC doit AUSSI lancer ce script maintenant !"
info "Les logs de c_net vont s'afficher ci-dessous en temps reel..."
echo ""
echo -e "${YLW}--- Logs c_net (10 secondes) ---${RST}"
sleep 10
echo -e "${YLW}--- Fin des logs ---${RST}"
echo ""

# ── ETAPE 6 : Verification reception ─────────────────────────────────────────
sep
echo -e "${BLD}ETAPE 6 — Verification de la shm (donnees recues du reseau)${RST}"
sep
echo ""
./test_ipc lire
echo ""

# ── ETAPE 7 : Surveillance continue (optionnel) ───────────────────────────────
echo ""
read -r -t 5 -p "Lancer la surveillance continue ? [o/N] " CHOIX || CHOIX="N"
echo ""
if [ "${CHOIX,,}" = "o" ]; then
    info "Surveillance en cours (Ctrl+C pour arreter)..."
    echo ""
    ./test_ipc boucle
fi

# ── Nettoyage ─────────────────────────────────────────────────────────────────
sep
echo -e "${BLD}NETTOYAGE${RST}"
sep
kill "$C_PID" 2>/dev/null && ok "c_net arrete (PID=$C_PID)" || true
make clean-ipc -s 2>/dev/null && ok "Ressources IPC supprimees" || true
echo ""
echo -e "${GRN}${BLD}Test termine.${RST}"
echo ""
echo "  Interpreation des resultats :"
echo "  - Les unites marquees '<< RESEAU' dans le tableau = recues via UDP"
echo "  - Pas d'unites distantes = l'autre PC n'a pas envoye, ou pare-feu bloque"
echo ""
