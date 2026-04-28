#ifndef IPC_H
#define IPC_H

/*
 * ipc.h — Interface de communication entre Python et le processus C
 *
 * La mémoire partagée contient un GameState.
 * Python y écrit l'état du jeu, le C le lit pour l'envoyer en réseau.
 * Le C y écrit les mises à jour reçues du réseau, Python les lit.
 *
 * Synchronisation V1 : un mutex POSIX protège l'unique GameState partagé.
 * Le second sémaphore est conservé pour compatibilité avec les scripts.
 */

#include "../shared/protocol.h"

/* ─────────────────────────────────────────────
 * Initialisation / fermeture
 * ───────────────────────────────────────────── */

/**
 * ipc_init - Ouvre (ou crée) la mémoire partagée et les sémaphores.
 *
 * @param shm_name      Nom du segment shm  (ex: SHM_NAME)
 * @param sem_w_name    Nom du mutex SHM principal (ex: SEM_WRITE_NAME)
 * @param sem_r_name    Nom du sémaphore réservé compatibilité (ex: SEM_READ_NAME)
 * @param create        1 = créer + initialiser, 0 = juste ouvrir
 * @return 0 si succès, -1 si erreur (errno positionné)
 */
int ipc_init(const char *shm_name,
             const char *sem_w_name,
             const char *sem_r_name,
             int create);

/**
 * ipc_close - Détache la mémoire partagée et ferme les sémaphores.
 *             Si create=1 à l'init, supprime aussi les ressources.
 */
void ipc_close(void);

/* ─────────────────────────────────────────────
 * Lecture / écriture thread-safe
 * ───────────────────────────────────────────── */

/**
 * ipc_read_state - Copie le GameState de la shm dans *out*.
 *                  Protégé par le mutex SHM.
 * @return 0 si succès, -1 si erreur
 */
int ipc_read_state(GameState *out);

/**
 * ipc_write_state - Copie *in* dans la shm.
 *                   Protégé par le mutex SHM.
 * @return 0 si succès, -1 si erreur
 */
int ipc_write_state(const GameState *in);

#endif /* IPC_H */
