#ifndef ML_RESOURCE_BARRIER_H
#define ML_RESOURCE_BARRIER_H

/* Publish fully initialized immutable resource data before its shared pointer.
 * ARMv5 uses the write-buffer drain already used by arm-mcr.h; ARMv7 has DMB.
 * Avoid GCC's out-of-line __sync_synchronize, absent from the ARMv5 toolchain. */
static inline void resource_publish_barrier(void)
{
#if defined(__ARM_ARCH) && __ARM_ARCH >= 7
    __asm__ volatile ("dmb sy" ::: "memory");
#elif defined(__arm__)
    unsigned zero = 0;
    __asm__ volatile ("mcr p15, 0, %0, c7, c10, 4" :: "r"(zero) : "memory");
#else
    __asm__ volatile ("" ::: "memory");
#endif
}

#endif
