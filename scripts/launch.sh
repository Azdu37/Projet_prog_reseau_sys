#!/bin/bash
# =============================================================================
# launch.sh — Lance le processus C réseau + le jeu Python (mode réparti)
#
# Architecture : Python ↔ SHM ↔ C ↔ UDP ↔ C ↔ SHM ↔ Python
#
# Usage :
#   ./scripts/launch.sh <IP_ADVERSAIRE> <COULEUR> <MON_IA> [SCENARIO]
# =============================================================================
set -e

if [ "$#" -lt 3 ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║ Usage: ./scripts/launch.sh <IP_ADVERSAIRE> <COULEUR> <MON_IA>  ║"
    echo "║                                                                ║"
    echo "║   <COULEUR> : ROUGE ou BLEU                                    ║"
    echo "║   <MON_IA>  : basicia, majordaft, braindead, etc.              ║"
    echo "║                                                                ║"
    echo "║ Exemple PC 1 : ./scripts/launch.sh 192.168.1.50 ROUGE basicia  ║"
    echo "║ Exemple PC 2 : ./scripts/launch.sh 192.168.1.10 BLEU  basicia  ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    exit 1
fi

REMOTE_IP="$1"
COULEUR=$(echo "$2" | tr '[:lower:]' '[:upper:]')
MON_IA="$(echo "$3" | tr '[:upper:]' '[:lower:]')"
SCENARIO="${4:-stest7}"

# ── Étape 0 : Vérification IA ──────────────────────────────────────────────
cd "$(dirname "$0")/../p_game"
if ! python3 -c "import sys; sys.path.append('.'); from ia.registry import AI_REGISTRY; exit(0 if '$MON_IA' in AI_REGISTRY else 1)"; then
    echo "ERREUR: L'IA '$MON_IA' n'existe pas."
    echo "IA disponibles : $(python3 -c "import sys; sys.path.append('.'); from ia.registry import AI_REGISTRY; print(', '.join(AI_REGISTRY.keys()))")"
    exit 1
fi
cd - > /dev/null

if [[ "$COULEUR" == "ROUGE" || "$COULEUR" == "R" ]]; then
    PEER_ID=0
    LOCAL_TEAM="R"
    IA_ROUGE="$MON_IA"
    IA_BLEUE="braindead"
    COULEUR_ADVERSE="BLEU"
elif [[ "$COULEUR" == "BLEU" || "$COULEUR" == "B" ]]; then
    PEER_ID=1
    LOCAL_TEAM="B"
    IA_ROUGE="braindead"
    IA_BLEUE="$MON_IA"
    COULEUR_ADVERSE="ROUGE"
else
    echo "ERREUR: Couleur '$COULEUR' invalide. Utilisez ROUGE ou BLEU."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

echo "╔═════════════════════════════════════════════════════════════╗"
echo "║          BATAILLE RÉSEAU — Python ↔ SHM ↔ C ↔ UDP          ║"
echo "╠═════════════════════════════════════════════════════════════╣"
echo "║  🎯 ÉQUIPE   : $COULEUR"
echo "║  🤖 IA       : $MON_IA"
echo "║  📡 ADVERSAIRE: $REMOTE_IP"
echo "║  🗺️  SCENARIO : $SCENARIO"
echo "║                                                             ║"
echo "║  ⚠️  L'autre joueur doit choisir l'Équipe $COULEUR_ADVERSE !  ║"
echo "╚═════════════════════════════════════════════════════════════╝"
echo ""

# ── Étape 1 : Nettoyage & Compilation du C ──────────────────────────────────
echo "▶ [1/3] Compilation du processus C réseau..."
cd "$ROOT/c_network"
make clean-ipc -s > /dev/null 2>&1 || true
make clean -s > /dev/null 2>&1 || true
make c_net -s
echo "  ✓ C compilé."

# ── Étape 2 : Lancement du processus C (SHM + UDP) ─────────────────────────
echo ""
echo "▶ [2/3] Lancement du routeur C (port 9000 UDP)..."
./c_net "$PEER_ID" "$REMOTE_IP" &
C_PID=$!
echo "  ✓ Processus C lancé (PID=$C_PID)."

echo "  ⏳ Attente de la SHM..."
sleep 1

if ! kill -0 "$C_PID" 2>/dev/null; then
    echo "  ✗ Le processus C a crashé !"
    exit 1
fi
echo "  ✓ SHM prête."

echo "  ⏳ Attente de l'autre PC avant de lancer le jeu..."
cd "$ROOT/p_game"
if ! python3 - <<'PY'
import ctypes
import os
import sys
import time

SHM_NAME = os.getenv("SHM_NAME", "/battle_state")

libc = ctypes.CDLL(None, use_errno=True)
libc.shm_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
libc.shm_open.restype = ctypes.c_int
libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                      ctypes.c_int, ctypes.c_int, ctypes.c_long]
libc.mmap.restype = ctypes.c_void_p
libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
libc.munmap.restype = ctypes.c_int
libc.close.argtypes = [ctypes.c_int]
libc.close.restype = ctypes.c_int

_PROT_READ = 0x1
_MAP_SHARED = 0x01

class UnitState(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_uint8),
        ("team", ctypes.c_uint8),
        ("owner_peer", ctypes.c_uint8),
        ("alive", ctypes.c_uint8),
        ("dirty", ctypes.c_uint8),
        ("_pad", ctypes.c_uint8 * 3),
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("hp", ctypes.c_uint16),
        ("hp_max", ctypes.c_uint16),
    ]

class GameStateC(ctypes.Structure):
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint16),
        ("unit_count", ctypes.c_uint8),
        ("my_peer_id", ctypes.c_uint8),
        ("tick", ctypes.c_uint32),
        ("both_ready", ctypes.c_uint8),
        ("_pad", ctypes.c_uint8 * 3),
        ("units", UnitState * 256),
    ]

fd = libc.shm_open(SHM_NAME.encode(), os.O_RDONLY, 0)
if fd < 0:
    err = ctypes.get_errno()
    raise OSError(err, f"shm_open({SHM_NAME})")

size = ctypes.sizeof(GameStateC)
addr = libc.mmap(None, size, _PROT_READ, _MAP_SHARED, fd, 0)
if addr in (ctypes.c_void_p(-1).value, None):
    err = ctypes.get_errno()
    libc.close(fd)
    raise OSError(err, "mmap")

try:
    state = ctypes.cast(addr, ctypes.POINTER(GameStateC)).contents
    deadline = time.time() + 120.0
    while time.time() < deadline:
        if state.both_ready:
            print("  ✓ Adversaire connecté.")
            sys.exit(0)
        time.sleep(0.25)
    print("  ✗ Timeout: l'adversaire ne s'est pas connecté.")
    sys.exit(1)
finally:
    libc.munmap(addr, size)
    libc.close(fd)
PY
then
    echo "  ✗ Abandon du lancement."
    kill "$C_PID" 2>/dev/null || true
    cd "$ROOT/c_network"
    make clean-ipc -s > /dev/null 2>&1 || true
    exit 1
fi

# ── Étape 3 : Jeu Python ────────────────────────────────────────────────────
echo ""
echo "▶ [3/3] Lancement du jeu Python..."
echo ""

python3 main.py run "$SCENARIO" "$IA_ROUGE" "$IA_BLEUE" \
    --distributed --local-team "$LOCAL_TEAM"

# ── Nettoyage ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Nettoyage..."
kill "$C_PID" 2>/dev/null && echo "  ✓ Processus C arrêté." || true
cd "$ROOT/c_network"
make clean-ipc -s > /dev/null 2>&1 || true
echo "  ✓ SHM purgée."
echo ""
echo "✓ Terminé."
