#ifndef LMB_NATIVE_H
#define LMB_NATIVE_H

/* Original glue using public compiler APIs and Substrate declarations only.
 * No PSHeader implementation is incorporated into the native build. */
#ifdef __OBJC__
#import <Foundation/Foundation.h>
#endif
#include <substrate.h>
#include <stddef.h>

#ifndef __has_feature
#define __has_feature(x) 0
#endif
#if __has_feature(ptrauth_calls)
#include <ptrauth.h>
#endif

static inline void *LMBFindSymbolReadable(MSImageRef image, const char *name) {
    /* Do not let a missing target image become a global symbol search. */
    if (!image || !name) return NULL;
    void *symbol = MSFindSymbol(image, name);
    if (!symbol) return NULL;
#if __has_feature(ptrauth_calls)
    return ptrauth_strip(symbol, ptrauth_key_function_pointer);
#else
    return symbol;
#endif
}

static inline void *LMBFindSymbolCallable(MSImageRef image, const char *name) {
    void *symbol = LMBFindSymbolReadable(image, name);
    if (!symbol) return NULL;
#if __has_feature(ptrauth_calls)
    return ptrauth_sign_unauthenticated(symbol, ptrauth_key_function_pointer, 0);
#else
    return symbol;
#endif
}

/* Native deployment is iOS 15+, but keep this check explicit and SDK-native. */
#define LMB_IOS12_OR_NEWER @available(iOS 12.0, *)

#endif
