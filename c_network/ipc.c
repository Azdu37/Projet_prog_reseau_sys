/*
 * ipc.c — Mémoire partagée POSIX + sémaphores
 *
 * Permet au processus C et à Python de partager un GameState
 * via un segment de mémoire partagée nommé (shm_open / mmap).
 *
 * Compilation : gcc ... -lrt -lpthread
 * (sous WSL / Linux uniquement)
 */

#include "ipc.h"

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>          /* O_CREAT, O_RDWR */
#include <sys/mman.h>       /* shm_open, mmap   */
#include <sys/stat.h>
#include <semaphore.h>
#include <unistd.h>

/* ─────────────────────────────────────────────
 * État interne du module
 * ───────────────────────────────────────────── */
static GameState *g_shm    = NULL;   /* pointeur vers la shm mappée  */
static int        g_shm_fd = -1;     /* descripteur du segment shm   */
static sem_t     *g_sem_w  = NULL;   /* sémaphore écriture (Python→C)*/
static sem_t     *g_sem_r  = NULL;   /* sémaphore lecture  (C→Python)*/
static int        g_owner  = 0;      /* 1 = on a créé les ressources */

/* Noms mémorisés pour le cleanup */
static char g_shm_name[64];
static char g_sem_w_name[64];
static char g_sem_r_name[64];

/* ─────────────────────────────────────────────
 * ipc_init
 * ───────────────────────────────────────────── */
int ipc_init(const char *shm_name,
             const char *sem_w_name,
             const char *sem_r_name,
             int create)
{
    int flags = O_RDWR | (create ? O_CREAT : 0);

    /* --- Mémoire partagée --- */
    g_shm_fd = shm_open(shm_name, flags, 0666);
    if (g_shm_fd < 0) {
        perror("[ipc] shm_open");
        return -1;
    }

    if (create) {
        /* Fixe la taille du segment */
        if (ftruncate(g_shm_fd, sizeof(GameState)) < 0) {
            perror("[ipc] ftruncate");
            close(g_shm_fd);
            return -1;
        }
    }

    /* Mappe le segment en mémoire */
    g_shm = mmap(NULL, sizeof(GameState),
                 PROT_READ | PROT_WRITE,
                 MAP_SHARED, g_shm_fd, 0);
    if (g_shm == MAP_FAILED) {
        perror("[ipc] mmap");
        close(g_shm_fd);
        return -1;
    }

    if (create) {
        /* Initialise l'état avec le magic number */
        memset(g_shm, 0, sizeof(GameState));
        g_shm->magic   = PROTOCOL_MAGIC;
        g_shm->version = PROTOCOL_VERSION;
    } else {
        /* Vérifie que la shm est bien initialisée */
        if (g_shm->magic != PROTOCOL_MAGIC) {
            fprintf(stderr, "[ipc] magic mismatch: 0x%08X\n", g_shm->magic);
            munmap(g_shm, sizeof(GameState));
            close(g_shm_fd);
            return -1;
        }
    }

    /* --- Sémaphores --- */
    int sem_flags = O_CREAT;
    g_sem_w = sem_open(sem_w_name, sem_flags, 0666, 1); /* init à 1 = libre */
    if (g_sem_w == SEM_FAILED) {
        perror("[ipc] sem_open write");
        munmap(g_shm, sizeof(GameState));
        close(g_shm_fd);
        return -1;
    }

    g_sem_r = sem_open(sem_r_name, sem_flags, 0666, 1);
    if (g_sem_r == SEM_FAILED) {
        perror("[ipc] sem_open read");
        sem_close(g_sem_w);
        munmap(g_shm, sizeof(GameState));
        close(g_shm_fd);
        return -1;
    }

    /* Sauvegarde les noms pour le cleanup */
    strncpy(g_shm_name,   shm_name,   sizeof(g_shm_name)   - 1);
    strncpy(g_sem_w_name, sem_w_name, sizeof(g_sem_w_name) - 1);
    strncpy(g_sem_r_name, sem_r_name, sizeof(g_sem_r_name) - 1);
    g_owner = create;

    printf("[ipc] initialisé (shm=%s, create=%d)\n", shm_name, create);
    return 0;
}

/* ─────────────────────────────────────────────
 * ipc_read_state
 * Lit le GameState depuis la shm (protégé par sem_r)
 * ───────────────────────────────────────────── */
int ipc_read_state(GameState *out)
{
    if (!g_shm || !g_sem_r) return -1;

    sem_wait(g_sem_r);                   /* attente si Python écrit   */
    memcpy(out, g_shm, sizeof(GameState));
    sem_post(g_sem_r);                   /* libère le sémaphore       */
    return 0;
}

/* ─────────────────────────────────────────────
 * ipc_write_state
 * Écrit un GameState dans la shm (protégé par sem_w)
 * ───────────────────────────────────────────── */
int ipc_write_state(const GameState *in)
{
    if (!g_shm || !g_sem_w) return -1;

    sem_wait(g_sem_w);                   /* attente si Python lit     */
    memcpy(g_shm, in, sizeof(GameState));
    sem_post(g_sem_w);
    return 0;
}

/* ─────────────────────────────────────────────
 * ipc_close
 * ───────────────────────────────────────────── */
void ipc_close(void)
{
    if (g_shm && g_shm != MAP_FAILED) {
        munmap(g_shm, sizeof(GameState));
        g_shm = NULL;
    }
    if (g_shm_fd >= 0) {
        close(g_shm_fd);
        g_shm_fd = -1;
    }
    if (g_sem_w && g_sem_w != SEM_FAILED) {
        sem_close(g_sem_w);
        g_sem_w = NULL;
    }
    if (g_sem_r && g_sem_r != SEM_FAILED) {
        sem_close(g_sem_r);
        g_sem_r = NULL;
    }

    /* Si on est le créateur, on supprime les ressources système */
    if (g_owner) {
        shm_unlink(g_shm_name);
        sem_unlink(g_sem_w_name);
        sem_unlink(g_sem_r_name);
        printf("[ipc] ressources supprimées\n");
    }
}
