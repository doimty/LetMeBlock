#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Exercise both compiler feature paths without pretending to execute PAC. */
#ifdef __has_feature
#undef __has_feature
#endif
#define __has_feature(x) LMB_TEST_PAC
#include "include/LMBNative.h"

static int imageObject, symbolObject, rawObject, callableObject;
static int findCalls, stripCalls, signCalls;
static void *lookupResult;

void *MSFindSymbol(MSImageRef image, const char *name) {
    assert(image == &imageObject && strcmp(name, "_target") == 0);
    findCalls++;
    return lookupResult;
}

void *testStrip(void *pointer, int key) {
    assert(pointer == &symbolObject && key == 7);
    stripCalls++;
    return &rawObject;
}

void *testSign(void *pointer, int key, unsigned long discriminator) {
    assert(pointer == &rawObject && key == 7 && discriminator == 0);
    signCalls++;
    return &callableObject;
}

int main(void) {
    assert(LMBFindSymbolCallable(NULL, "_target") == NULL);
    assert(LMBFindSymbolReadable(&imageObject, NULL) == NULL);
    assert(findCalls == 0 && stripCalls == 0 && signCalls == 0);
    lookupResult = NULL;
    assert(LMBFindSymbolCallable(&imageObject, "_target") == NULL);
    assert(LMBFindSymbolReadable(&imageObject, "_target") == NULL);
    assert(findCalls == 2 && stripCalls == 0 && signCalls == 0);
    lookupResult = &symbolObject;
#if LMB_TEST_PAC
    assert(LMBFindSymbolReadable(&imageObject, "_target") == &rawObject);
    assert(stripCalls == 1 && signCalls == 0);
    assert(LMBFindSymbolCallable(&imageObject, "_target") == &callableObject);
    assert(stripCalls == 2 && signCalls == 1);
#else
    assert(LMBFindSymbolReadable(&imageObject, "_target") == &symbolObject);
    assert(LMBFindSymbolCallable(&imageObject, "_target") == &symbolObject);
    assert(stripCalls == 0 && signCalls == 0);
#endif
    puts("symbols: null/readable/callable/PAC key and discriminator passed");
    return 0;
}
