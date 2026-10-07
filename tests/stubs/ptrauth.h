#ifndef TEST_PTRAUTH_H
#define TEST_PTRAUTH_H
#define ptrauth_key_function_pointer 7
void *testStrip(void *pointer, int key);
void *testSign(void *pointer, int key, unsigned long discriminator);
#define ptrauth_strip(pointer, key) testStrip((pointer), (key))
#define ptrauth_sign_unauthenticated(pointer, key, discriminator) \
    testSign((pointer), (key), (discriminator))
#endif
