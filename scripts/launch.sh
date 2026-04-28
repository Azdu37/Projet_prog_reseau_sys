#!/bin/bash
# =============================================================================
# launch.sh — Lance le processus C réseau + le jeu Python (mode réparti)
#
# Architecture : Python ↔ SHM ↔ C ↔ UDP ↔ C ↔ SHM ↔ Python
#
# Usage :
#   ./scripts/launch.sh <IP_ADVERSAIRE> <COULEUR> <MON_IA> [SCENARIO] [--terminal|--no-terminal]
# =============================================================================
set -e

C_PID=""

cleanup() {
    if [ -n "$C_PID" ] && kill -0 "$C_PID" 2>/dev/null; then
        echo ""
        echo "▶ Nettoyage..."
        kill "$C_PID" 2>/dev/null && echo "  ✓ Processus C arrêté." || true
    fi
    if [ -n "${ROOT:-}" ] && [ -d "$ROOT/c_network" ]; then
        cd "$ROOT/c_network"
        make clean-ipc -s > /dev/null 2>&1 || true
        echo "  ✓ SHM purgée."
    fi
}

trap cleanup EXIT

if [ "$#" -lt 3 ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║ Usage: ./scripts/launch.sh <IP_ADVERSAIRE> <COULEUR> <MON_IA>  ║"
    echo "║        [SCENARIO] [--terminal|--no-terminal]                   ║"
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
shift 3

SCENARIO="stest7"
PY_VIEW_ARGS=()

if [ "$#" -gt 0 ] && [[ "$1" != -* ]]; then
    SCENARIO="$1"
    shift
fi

while [ "$#" -gt 0 ]; do
    case "$1" in
        --terminal|-t)
            PY_VIEW_ARGS+=("--terminal")
            ;;
        --no-terminal)
            PY_VIEW_ARGS+=("--no-terminal")
            ;;
        *)
            echo "ERREUR: option inconnue '$1'. Utilisez --terminal ou --no-terminal."
            exit 1
            ;;
    esac
    shift
done

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
if [ "${#PY_VIEW_ARGS[@]}" -gt 0 ]; then
echo "║  🖥️  AFFICHAGE: ${PY_VIEW_ARGS[*]}"
else
echo "║  🖥️  AFFICHAGE: graphique (pygame)"
fi
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

# ── Étape 3 : Jeu Python ────────────────────────────────────────────────────
echo ""
echo "▶ [3/3] Lancement du jeu Python..."
echo ""

cd "$ROOT/p_game"
python3 main.py run "$SCENARIO" "$IA_ROUGE" "$IA_BLEUE" \
    --distributed --local-team "$LOCAL_TEAM" "${PY_VIEW_ARGS[@]}"

echo ""
echo "✓ Terminé."
