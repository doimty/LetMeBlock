#ifndef LMB_PATHS_H
#define LMB_PATHS_H

#include "LMBHosts.h"

#if defined(THEOS_PACKAGE_SCHEME_ROOTHIDE)
#include <roothide.h>

static inline const char *LMBManagedPath(const char *path) {
    return jbroot(path);
}
#else
#include <rootless.h>

/* Legacy locations and precedence are intentionally unchanged. */
static inline const char *LMBManagedPath(const char *path) {
    return strcmp(path, LMB_SYSTEM_HOSTS_PATH) == 0
        ? "/var/jb/etc/hosts" : ROOT_PATH("/etc/hosts.lmb");
}
#endif

#endif
