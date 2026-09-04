/*
 * 가짜 util/atomic.h — PC 에는 인터럽트가 없으므로 블록을 그대로 둔다.
 * ATOMIC_BLOCK(x) { ... } 가 { ... } 로 남는다.
 */

#ifndef FAKE_UTIL_ATOMIC_H
#define FAKE_UTIL_ATOMIC_H

#define ATOMIC_RESTORESTATE
#define ATOMIC_FORCEON
#define ATOMIC_BLOCK(type)

#endif /* FAKE_UTIL_ATOMIC_H */
