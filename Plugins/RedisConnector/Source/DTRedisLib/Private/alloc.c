// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#include "fmacros.h"
#include "alloc.h"
#include <string.h>
#include <stdlib.h>

hiredisAllocFuncs hiredisAllocFns = {
    .mallocFn = malloc,
    .callocFn = calloc,
    .reallocFn = realloc,
    .strdupFn = strdup,
    .freeFn = free,
};

/* Override hiredis' allocators with ones supplied by the user */
hiredisAllocFuncs hiredisSetAllocators(hiredisAllocFuncs *override) {
    hiredisAllocFuncs orig = hiredisAllocFns;

    hiredisAllocFns = *override;

    return orig;
}

/* Reset allocators to use libc defaults */
void hiredisResetAllocators(void) {
    hiredisAllocFns = (hiredisAllocFuncs) {
        .mallocFn = malloc,
        .callocFn = calloc,
        .reallocFn = realloc,
        .strdupFn = strdup,
        .freeFn = free,
    };
}

#ifdef _WIN32

void *hi_malloc(size_t size) {
    return hiredisAllocFns.mallocFn(size);
}

void *hi_calloc(size_t nmemb, size_t size) {
    return hiredisAllocFns.callocFn(nmemb, size);
}

void *hi_realloc(void *ptr, size_t size) {
    return hiredisAllocFns.reallocFn(ptr, size);
}

char *hi_strdup(const char *str) {
    return hiredisAllocFns.strdupFn(str);
}

void hi_free(void *ptr) {
    hiredisAllocFns.freeFn(ptr);
}

#endif
