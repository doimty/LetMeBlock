#ifndef LMB_HOSTS_H
#define LMB_HOSTS_H

#include <stdio.h>
#include <string.h>

#define LMB_SYSTEM_HOSTS_PATH "/etc/hosts"
#define LMB_SECONDARY_HOSTS_PATH "/etc/hosts.lmb"

typedef FILE *(*LMBOpenFunction)(const char *, const char *);
typedef const char *(*LMBPathFunction)(const char *);

/* Mapping is deliberately lazy: jbroot's cached C strings need no free. */
static inline FILE *LMBOpenManagedHosts(const char *mode,
                                      LMBOpenFunction openFile,
                                      LMBPathFunction managedPath) {
    const char *path = managedPath(LMB_SYSTEM_HOSTS_PATH);
    FILE *result = path ? openFile(path, mode) : NULL;
    if (result) return result;
    path = managedPath(LMB_SECONDARY_HOSTS_PATH);
    return path ? openFile(path, mode) : NULL;
}

/* Only the exact raw system path is intercepted. Keep the original mode,
 * cached FILE ownership and libc's final errno; do not inspect file contents. */
static inline FILE *LMBOpenHosts(const char *path, const char *mode, FILE *cached,
                               LMBOpenFunction openFile,
                               LMBPathFunction managedPath) {
    if (path && strcmp(path, LMB_SYSTEM_HOSTS_PATH) == 0) {
        if (cached) return cached;
        FILE *result = LMBOpenManagedHosts(mode, openFile, managedPath);
        if (result) return result;
    }
    return openFile(path, mode);
}

#endif
