#ifndef LMB_XPC_H
#define LMB_XPC_H

#include <sys/types.h>
#include <xpc/xpc.h>

/* Native-only access to an existing private-on-iOS symbol. Match the public
 * XPC signature exactly; do not redeclare the unavailable SDK identifier or
 * alter availability macros. The Mach-O name is unmangled despite ObjC++.
 * This declaration does not prove availability/semantics on a real device. */
#ifdef __cplusplus
extern "C"
#endif
pid_t LMBXPCConnectionGetPID(xpc_connection_t connection)
    __asm__("_xpc_connection_get_pid");

#endif
