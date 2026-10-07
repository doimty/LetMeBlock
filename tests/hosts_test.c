#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "include/LMBPaths.h"

static char tokens[4];
/* Opaque identities only; never dereference these fake FILE pointers. */
static FILE *streams[] = {(FILE *)(void *)&tokens[0], (FILE *)(void *)&tokens[1],
                          (FILE *)(void *)&tokens[2], (FILE *)(void *)&tokens[3]};
static const char *mapped[] = {"/private/test-jb/etc/hosts", "/private/test-jb/etc/hosts.lmb"};
static const char *opened[4];
static const char *modes[4];
static int calls, maps, succeeds, missingMap, injectedErrors[4];

const char *jbroot(const char *path) {
    maps++;
    int index = strcmp(path, LMB_SYSTEM_HOSTS_PATH) == 0 ? 0 : 1;
    assert(index == 0 || strcmp(path, LMB_SECONDARY_HOSTS_PATH) == 0);
    return (missingMap & (1 << index)) ? NULL : mapped[index];
}

static FILE *fakeOpen(const char *path, const char *mode) {
    assert(calls < 4);
    int index = calls++;
    opened[index] = path;
    modes[index] = mode;
    if (index == succeeds) return streams[index];
    errno = injectedErrors[index];
    return NULL;
}

static void reset(int success) {
    calls = maps = missingMap = 0;
    succeeds = success;
    memset(opened, 0, sizeof(opened));
    memset(modes, 0, sizeof(modes));
    injectedErrors[0] = ENOENT;
    injectedErrors[1] = EACCES;
    injectedErrors[2] = EIO;
    injectedErrors[3] = EPERM;
    errno = 0;
}

static void assertOrder(int count, const char *mode) {
    assert(calls == count);
    for (int i = 0; i < count; ++i) {
        const char *expected = i < 2 ? mapped[i] : LMB_SYSTEM_HOSTS_PATH;
        assert(strcmp(opened[i], expected) == 0);
        assert(mode ? modes[i] && strcmp(modes[i], mode) == 0 : modes[i] == NULL);
    }
}

int main(void) {
    const char *mode = "rb";
    int errors[] = {ENOENT, EACCES, EPERM, EIO};
    for (unsigned e = 0; e < sizeof(errors) / sizeof(errors[0]); ++e) {
        for (int success = 0; success <= 2; ++success) {
            reset(success);
            injectedErrors[0] = injectedErrors[1] = errors[e];
            FILE *result = LMBOpenHosts("/etc/hosts", mode, NULL, fakeOpen, LMBManagedPath);
            assert(result == streams[success]);
            assertOrder(success + 1, mode);
            assert(maps == (success == 0 ? 1 : 2));
        }
    }
    reset(-1);
    assert(LMBOpenHosts("/etc/hosts", mode, NULL, fakeOpen, LMBManagedPath) == NULL);
    assertOrder(3, mode);
    assert(errno == EIO); /* errno from raw fallback, not the first failure. */

    const char *pass[] = {NULL, "", "/etc/hosts.lmb", "/etc/hosts/", "/etc/HOSTS",
                          "/private/etc/hosts", "/tmp/etc/hosts", mapped[0]};
    for (unsigned i = 0; i < sizeof(pass) / sizeof(pass[0]); ++i) {
        reset(0);
        assert(LMBOpenHosts(pass[i], mode, streams[3], fakeOpen, LMBManagedPath) == streams[0]);
        assert(calls == 1 && maps == 0 && opened[0] == pass[i] && modes[0] == mode);
        reset(-1);
        injectedErrors[0] = EFAULT;
        assert(LMBOpenHosts(pass[i], mode, NULL, fakeOpen, LMBManagedPath) == NULL);
        assert(errno == EFAULT && calls == 1 && maps == 0);
    }

    const char *allModes[] = {"r", "rb", "r+", "w", "invalid", NULL};
    for (unsigned i = 0; i < sizeof(allModes) / sizeof(allModes[0]); ++i) {
        reset(2);
        assert(LMBOpenHosts("/etc/hosts", allModes[i], NULL, fakeOpen, LMBManagedPath) == streams[2]);
        assertOrder(3, allModes[i]);
        reset(-1);
        errno = EBUSY;
        assert(LMBOpenHosts("/etc/hosts", allModes[i], streams[3], fakeOpen, LMBManagedPath) == streams[3]);
        assert(calls == 0 && maps == 0 && errno == EBUSY);
    }

    /* Constructor caches only managed candidates, never raw system hosts. */
    for (int success = 0; success <= 1; ++success) {
        reset(success);
        FILE *cached = LMBOpenManagedHosts("r", fakeOpen, LMBManagedPath);
        assert(cached == streams[success]);
        assertOrder(success + 1, "r");
        reset(-1);
        assert(LMBOpenHosts("/etc/hosts", "r+", cached, fakeOpen, LMBManagedPath) == cached);
        assert(calls == 0 && maps == 0);
    }
    reset(2); /* Raw would open, but ctor must not try or cache it. */
    FILE *cached = LMBOpenManagedHosts("r", fakeOpen, LMBManagedPath);
    assert(!cached && calls == 2);
    reset(2);
    assert(LMBOpenHosts("/etc/hosts", "r", cached, fakeOpen, LMBManagedPath) == streams[2]);
    assertOrder(3, "r");
    assert(!cached); /* Hook fallback does not replace the constructor cache. */
    reset(0);
    mapped[0] = "/private/other-jb/etc/hosts";
    assert(LMBOpenHosts("/etc/hosts", "r", cached, fakeOpen, LMBManagedPath) == streams[0]);
    assert(strcmp(opened[0], mapped[0]) == 0 && maps == 1);

    reset(0);
    missingMap = 1;
    assert(LMBOpenManagedHosts("r", fakeOpen, LMBManagedPath) == streams[0]);
    assert(calls == 1 && maps == 2 && strcmp(opened[0], mapped[1]) == 0);
    reset(0);
    missingMap = 3;
    assert(LMBOpenManagedHosts("r", fakeOpen, LMBManagedPath) == NULL);
    assert(calls == 0 && maps == 2);
    assert(LMBOpenHosts("/etc/hosts", "r", NULL, fakeOpen, LMBManagedPath) == streams[0]);
    assert(calls == 1 && maps == 4 && strcmp(opened[0], "/etc/hosts") == 0);
    puts("hosts: priority/errors/passthrough/modes/preopen/cache/mapping passed");
    return 0;
}
