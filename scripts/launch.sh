#!/bin/bash
# =============================================================================
# launch.sh — Lance le processus C réseau + le jeu Python (mode réparti)
#
# Le but de ce script est d'être extrêmement simple à lancer sans se soucier
# de la plomberie réseau ou des identifiants complexes (0 ou 1).
# =============================================================================
set -e

if [ "$#" -lt 3 ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║ ERREUR : Il manque des arguments pour lancer le jeu !          ║"
    echo "╠════════════════════════════════════════════════════════════════╣"
    echo "║ Usage: ./scripts/launch.sh <IP_ADVERSAIRE> <COULEUR> <MON_IA>  ║"
    echo "║                                                                ║"
    echo "║ Options possibles :                                            ║"
    echo "║   <COULEUR> : ROUGE ou BLEU                                    ║"
    echo "║   <MON_IA>  : majordaft, braindead, ou autre IA                ║"
    echo "║                                                                ║"
    echo "║ Exemple PC 1 : ./scripts/launch.sh 192.168.1.50 ROUGE majordaft║"
    echo "║ Exemple PC 2 : ./scripts/launch.sh 192.168.1.10 BLEU  braindead║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    exit 1
fi

REMOTE_IP="$1"
COULEUR=$(echo "$2" | tr '[:lower:]' '[:upper:]')
MON_IA="$(echo "$3" | tr '[:upper:]' '[:lower:]')"
SCENARIO="${4:-stest7}"

# Détermination transparente des identifiants réseaux
if [[ "$COULEUR" == "ROUGE" || "$COULEUR" == "R" ]]; then
    PEER_ID=0
    LOCAL_TEAM="R"
    IA_ROUGE="$MON_IA"
    IA_BLEUE="braindead" # L'adversaire est géré par le réseau
    COULEUR_ADVERSE="BLEU"
elif [[ "$COULEUR" == "BLEU" || "$COULEUR" == "B" ]]; then
    PEER_ID=1
    LOCAL_TEAM="B"
    IA_ROUGE="braindead" # L'adversaire est géré par le réseau
    IA_BLEUE="$MON_IA"
    COULEUR_ADVERSE="ROUGE"
else
    echo "ERREUR: La couleur='$COULEUR' est invalide. Utilisez ROUGE ou BLEU."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

echo "╔═════════════════════════════════════════════════════════════╗"
echo "║          LANCEMENT DE LA BATAILLE RÉSEAU (UDP)              ║"
echo "╠═════════════════════════════════════════════════════════════╣"
echo "║                                                             ║"
echo "║  🎯 VOUS JOUEZ L'ÉQUIPE : $COULEUR "
echo "║  🤖 VOTRE INTELLIGENCE  : $MON_IA "
echo "║  📡 IP DE L'ADVERSAIRE  : $REMOTE_IP "
echo "║                                                             ║"
echo "║  ⚠️  ATTENTION, POUR QUE CELA FONCTIONNE :                  ║"
echo "║  L'autre joueur DOIT IMPÉRATIVEMENT choisir l'Équipe $COULEUR_ADVERSE !"
echo "║                                                             ║"
echo "╚═════════════════════════════════════════════════════════════╝"
echo ""

# ── Étape 1 : Compilation ────────────────────────────────────────────────────
echo "▶ [1/3] Compilation de la route réseau C..."
cd "$ROOT/c_network"
make c_net -s
echo "  ✓ C compilé avec succès."

# ── Étape 2 : Lancement de c_net ────────────────────────────────────────────
echo ""
echo "▶ [2/3] Démarrage du routeur sans fil (Port 9000 UDP)..."
./c_net "$PEER_ID" "$REMOTE_IP" > /dev/null 2>&1 &
C_PID=$!
echo "  ✓ Antenne réseau branchée."

echo "  ⏳ Initialisation de la mémoire partagée (RAM)..."
sleep 1

if ! kill -0 "$C_PID" 2>/dev/null; then
    echo "  ✗ Erreur fatale: l'antenne C s'est écrasée !"
    exit 1
fi
echo "  ✓ Mémoire prête."

# ── Étape 3 : Jeu Python ────────────────────────────────────────────────────
echo ""
echo "▶ [3/3] Démarrage de l'arène graphique..."
echo "  Scénario joué : $SCENARIO"
echo ""

cd "$ROOT/p_game"

# Note: Python ne génère pas de log parasites, on joue.
# --distributed indique qu'on diffuse nos infos sur le reseau via le pont
python3 main.py run "$SCENARIO" "$IA_ROUGE" "$IA_BLEUE" \
    --distributed --local-team "$LOCAL_TEAM"

# ── Nettoyage (Quand la fenetre pygame est fermée) ──────────────────────────
echo ""
echo "▶ Nettoyage du système..."
kill "$C_PID" 2>/dev/null && echo "  ✓ Antenne démontée." || true
cd "$ROOT/c_network"
make clean-ipc -s > /dev/null 2>&1 || true
echo "  ✓ Mémoire purgée."
echo ""
echo "✓ Simulation terminée. À bientôt !"