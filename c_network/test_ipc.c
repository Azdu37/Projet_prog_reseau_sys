/*
 * test_ipc.c — Test de la couche IPC + vérification réseau
 *
 * Modes :
 *   ./test_ipc          → écrire 3 unités dirty dans la shm (simule Python)
 *   ./test_ipc lire     → lire et afficher la shm actuelle (vérifier réception)
 *   ./test_ipc boucle   → lire la shm en continu toutes les 500ms
 *
 * Pré-requis : ./c_net doit être lancé en premier (il crée la shm).
 *
 * Compilation : make test_ipc
 *               ou : gcc -Wall -g -I../shared -o test_ipc test_ipc.c ipc.c -lrt -lpthread
 */

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "ipc.h"

/* ── Affiche proprement un GameState ─────────────────────────────────────── */
static void afficher_etat(const GameState *s, const char *titre)
{
    printf("\n=== %s ===\n", titre);
    printf("  magic      = 0x%08X  %s\n",
           s->magic, s->magic == PROTOCOL_MAGIC ? "[OK]" : "[ERREUR! magic invalide]");
    printf("  version    = %d\n",   s->version);
    printf("  peer_id    = %d\n",   s->my_peer_id);
    printf("  tick       = %u\n",   s->tick);
    printf("  unites     = %d\n\n", s->unit_count);

    if (s->unit_count == 0) {
        printf("  (aucune unite dans la shm)\n");
        return;
    }

    printf("  %-4s  %-5s  %-5s  %-6s  %-6s  %-6s  %-6s  %-5s  %-5s\n",
           "ID", "team", "peer", "x", "y", "hp", "hp_max", "alive", "dirty");
    printf("  %-4s  %-5s  %-5s  %-6s  %-6s  %-6s  %-6s  %-5s  %-5s\n",
           "----","-----","-----","------","------","------","------","-----","-----");

    for (int i = 0; i < s->unit_count; i++) {
        const UnitState *u = &s->units[i];
        /* Marqueur visuel : "< RESEAU" si l'unité appartient à un autre pair */
        const char *tag = (u->owner_peer != s->my_peer_id) ? "  << RESEAU" : "";
        printf("  %-4d  %-5d  %-5d  %-6.1f  %-6.1f  %-6d  %-6d  %-5d  %-5d%s\n",
               u->id, u->team, u->owner_peer,
               u->x, u->y, u->hp, u->hp_max,
               u->alive, u->dirty, tag);
    }
}

/* ── MODE ECRITURE : simule Python qui push des unités dirty ─────────────── */
static int mode_ecriture(int my_peer_id)
{
    printf("=== Mode ECRITURE (peer_id=%d) ===\n", my_peer_id);
    printf("Simulation Python : ecriture de 3 unites DIRTY dans la shm.\n");
    printf("c_net va les detecter et les envoyer via UDP au pair distant.\n\n");

    GameState state = {0};
    state.magic      = PROTOCOL_MAGIC;
    state.version    = PROTOCOL_VERSION;
    state.my_peer_id = (uint8_t)my_peer_id;
    state.tick       = 42;
    state.unit_count = 3;

    /* Unité 0 : appartient à ce PC, sera envoyée */
    state.units[0] = (UnitState){
        .id = 0, .team = (uint8_t)my_peer_id,
        .owner_peer = (uint8_t)my_peer_id,
        .alive = 1, .dirty = 1,
        .x = 5.0f, .y = 3.0f, .hp = 100, .hp_max = 100,
    };

    /* Unité 1 : appartient à ce PC, sera envoyée */
    state.units[1] = (UnitState){
        .id = 1, .team = (uint8_t)my_peer_id,
        .owner_peer = (uint8_t)my_peer_id,
        .alive = 1, .dirty = 1,
        .x = 7.0f, .y = 2.0f, .hp = 60, .hp_max = 60,
    };

    /* Unité 2 : appartient à l'autre peer (ne sera PAS envoyée par ce PC) */
    int autre_peer = (my_peer_id == 0) ? 1 : 0;
    state.units[2] = (UnitState){
        .id = 2, .team = (uint8_t)autre_peer,
        .owner_peer = (uint8_t)autre_peer,
        .alive = 1, .dirty = 0,
        .x = 10.0f, .y = 8.0f, .hp = 80, .hp_max = 100,
    };

    afficher_etat(&state, "Etat a ecrire");

    if (ipc_write_state(&state) < 0) {
        fprintf(stderr, "[FAIL] ipc_write_state\n");
        ipc_close();
        return 1;
    }

    printf("\n[OK] Ecrit dans la shm.\n");
    printf("     c_net va maintenant envoyer les unites dirty (id=0, id=1) en UDP.\n");
    printf("     Sur l'autre PC, lancez : ./test_ipc lire\n");

    ipc_close();
    return 0;
}

/* ── MODE LECTURE : affiche ce qui est dans la shm (mises-à-jour réseau) ── */
static int mode_lecture(void)
{
    printf("=== Mode LECTURE ===\n");
    printf("Affichage de la shm actuelle (ce que c_net a recu du reseau).\n");

    GameState state = {0};
    if (ipc_read_state(&state) < 0) {
        fprintf(stderr, "[FAIL] ipc_read_state\n");
        ipc_close();
        return 1;
    }

    afficher_etat(&state, "Etat actuel dans la shm");

    /* Compte les unités reçues du réseau */
    int nb_reseau = 0;
    for (int i = 0; i < state.unit_count; i++) {
        if (state.units[i].owner_peer != state.my_peer_id)
            nb_reseau++;
    }

    printf("\n");
    if (nb_reseau > 0)
        printf("[OK] %d unite(s) recue(s) du reseau distant !\n", nb_reseau);
    else
        printf("[INFO] Aucune unite distante pour l'instant.\n");

    ipc_close();
    return 0;
}

/* ── MODE BOUCLE : lit la shm en continu jusqu'à Ctrl+C ─────────────────── */
static int mode_boucle(void)
{
    printf("=== Mode BOUCLE (Ctrl+C pour arreter) ===\n\n");
    int iteration = 0;

    while (1) {
        if (ipc_init(SHM_NAME, SEM_WRITE_NAME, SEM_READ_NAME, 0) < 0) {
            fprintf(stderr, "[!] shm non disponible, attente...\n");
            sleep(1);
            continue;
        }

        GameState state = {0};
        if (ipc_read_state(&state) == 0) {
            int nb_reseau = 0;
            for (int i = 0; i < state.unit_count; i++)
                if (state.units[i].owner_peer != state.my_peer_id) nb_reseau++;

            printf("\r[it=%d] tick=%-6u unites=%-3d dont %d reseau    ",
                   ++iteration, state.tick, state.unit_count, nb_reseau);
            fflush(stdout);

            /* Affiche détail complet si on a reçu des unités réseau */
            if (nb_reseau > 0) {
                printf("\n");
                afficher_etat(&state, "Reception reseau detectee !");
            }
        }
        ipc_close();
        usleep(500000); /* 500ms */
    }
    return 0;
}

/* ── Point d'entrée ──────────────────────────────────────────────────────── */
int main(int argc, char *argv[])
{
    const char *mode    = (argc > 1) ? argv[1] : "ecrire";
    int         peer_id = (argc > 2) ? atoi(argv[2]) : 0;

    /* Mode boucle : pas besoin de c_net au préalable, elle gère l'absence */
    if (strcmp(mode, "boucle") == 0)
        return mode_boucle();

    /* Tous les autres modes : c_net doit être lancé */
    if (ipc_init(SHM_NAME, SEM_WRITE_NAME, SEM_READ_NAME, 0) < 0) {
        fprintf(stderr,
            "[FAIL] shm '%s' non accessible.\n"
            "       Lance d'abord : ./c_net <peer_id> <ip_pair> &\n",
            SHM_NAME);
        return 1;
    }

    if (strcmp(mode, "lire") == 0)
        return mode_lecture();

    if (strcmp(mode, "ecrire") == 0)
        return mode_ecriture(peer_id);

    fprintf(stderr,
        "Usage : %s [ecrire [peer_id] | lire | boucle]\n"
        "  ecrire <id>  Ecrit 3 unites dirty dans la shm (simule Python)\n"
        "  lire         Affiche la shm (verifie reception reseau)\n"
        "  boucle       Surveille la shm en continu\n",
        argv[0]);
    ipc_close();
    return 1;
}
