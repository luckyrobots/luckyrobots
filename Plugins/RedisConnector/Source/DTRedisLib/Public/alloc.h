// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#ifndef HIREDIS_ALLOC_H
#define HIREDIS_ALLOC_H

#include <stddef.h> /* for size_t */

#ifdef __cplusplus
extern "C" {
#endif

/* Structure pointing to our actually configured allocators */
typedef struct hiredisAllocFuncs {
    void *(*mallocFn)(size_t);
    void *(*callocFn)(size_t,size_t);
    void *(*reallocFn)(void*,size_t);
    char *(*strdupFn)(const char*);
    void (*freeFn)(void*);
} hiredisAllocFuncs;

hiredisAllocFuncs hiredisSetAllocators(hiredisAllocFuncs *ha);
void hiredisResetAllocators(void);

#ifndef _WIN32

/* Hiredis' configured allocator function pointer struct */
extern hiredisAllocFuncs hiredisAllocFns;

static inline void *hi_malloc(size_t size) {
    return hiredisAllocFns.mallocFn(size);
}

static inline void *hi_calloc(size_t nmemb, size_t size) {
    return hiredisAllocFns.callocFn(nmemb, size);
}

static inline void *hi_realloc(void *ptr, size_t size) {
    return hiredisAllocFns.reallocFn(ptr, size);
}

static inline char *hi_strdup(const char *str) {
    return hiredisAllocFns.strdupFn(str);
}

static inline void hi_free(void *ptr) {
    hiredisAllocFns.freeFn(ptr);
}

#else

void *hi_malloc(size_t size);
void *hi_calloc(size_t nmemb, size_t size);
void *hi_realloc(void *ptr, size_t size);
char *hi_strdup(const char *str);
void hi_free(void *ptr);

#endif

#ifdef __cplusplus
}
#endif

#endif /* HIREDIS_ALLOC_H */
