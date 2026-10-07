#ifndef TEST_SUBSTRATE_H
#define TEST_SUBSTRATE_H
typedef const void *MSImageRef;
void *MSFindSymbol(MSImageRef image, const char *name);
MSImageRef MSGetImageByName(const char *name);
#endif
