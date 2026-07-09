# RTOS & Real-Time Systems

## Real-time concepts
- **Real-time = correctness depends on timing**, not raw speed. Meet deadlines predictably, not "fast on average".
- **Hard real-time**: missed deadline = system failure (airbag, motor commutation, pacemaker). Must be provably bounded.
- **Soft real-time**: occasional miss degrades quality but is tolerable (audio, UI, telemetry).
- **Determinism**: same inputs -> same timing. Enemies: dynamic allocation, unbounded loops, priority inversion, cache/DMA contention, interrupt jitter.
- Key metrics: **latency** (event -> response), **jitter** (latency variation), **WCET** (worst-case execution time). Schedulability needs WCET bounds; profile worst case, not average.
- Rate-monotonic: shorter period -> higher priority; schedulable if total CPU utilization below the RMS bound (~69% for many tasks, higher with harmonic periods).

## Tasks & scheduler
- A **task/thread** = independent function with its own stack + priority + state (Ready/Running/Blocked/Suspended). Written as `void task(void*){ for(;;){ ... } }` — never returns.
- **Preemptive priority scheduler**: highest-priority Ready task always runs; a higher-prio task becoming Ready **preempts** immediately (context switch saves/restores registers + stack pointer).
- Equal priority -> round-robin time-slicing (if enabled) on tick boundaries.
- Context switch triggered by: tick ISR, a task blocking (delay/queue/semaphore), or a higher-prio task being unblocked from an ISR.
- The **idle task** (lowest prio) runs when nothing else is Ready — hook it for sleep/low-power.

## FreeRTOS core APIs
```c
xTaskCreate(task, "name", stackWords, param, prio, &handle);
vTaskDelay(pdMS_TO_TICKS(100));           // relative sleep
vTaskDelayUntil(&last, pdMS_TO_TICKS(10));// fixed period, no drift
xQueueSend(q, &item, timeout);  xQueueReceive(q, &buf, timeout);
xSemaphoreTake(sem, timeout);   xSemaphoreGive(sem);
xSemaphoreCreateMutex();  // priority inheritance
// ISR-safe variants end in FromISR + higher-prio-woken flag:
xQueueSendFromISR(q,&item,&hpTaskWoken);
portYIELD_FROM_ISR(hpTaskWoken);
```
- Tick rate `configTICK_RATE_HZ` (e.g. 1000 = 1ms tick). Delays are in ticks; sub-tick timing needs a hardware timer.

## Synchronization
- **Mutex**: mutual exclusion for a shared resource; ownership + **priority inheritance**. Take/give from the **same task** only. Not usable from an ISR.
- **Binary semaphore**: signaling (event/ISR -> task). No ownership; give from ISR, take in task. Use for "deferred interrupt handling".
- **Counting semaphore**: manage N identical resources or count events.
- **Queue**: pass copies of data between tasks or ISR->task; blocks sender when full / receiver when empty. The primary, safest IPC — prefer over shared globals.
- **Critical section**: `taskENTER_CRITICAL()`/`taskEXIT_CRITICAL()` disables interrupts (or raises BASEPRI) — keep extremely short; it kills real-time responsiveness while held.
- **Notifications** (`xTaskNotify`): lighter/faster than a binary semaphore or queue for 1:1 signaling.

## Priority inversion + inheritance
- **Priority inversion**: low-prio task L holds a mutex; high-prio task H blocks waiting for it; a medium-prio task M preempts L, so H waits on M indefinitely (the Mars Pathfinder bug).
- **Priority inheritance**: while H waits on L's mutex, L is temporarily boosted to H's priority so it finishes and releases quickly. FreeRTOS mutexes do this; binary semaphores do NOT.
- **Priority ceiling**: task takes the highest priority of any task that can use the resource — bounds inversion further.
- Avoid: don't share a mutex across widely separated priorities; keep critical sections tiny.

## ISR-to-task (deferred handling)
- ISR does the minimum (read hardware, clear flag) then signals a task via `...FromISR` (semaphore give / queue send / task notify). The task (higher prio) wakes and does the real work.
- `portYIELD_FROM_ISR(woken)` forces an immediate context switch on ISR exit if it unblocked a higher-prio task — otherwise the response waits for the next tick.
- ISR priority must be at or below `configMAX_SYSCALL_INTERRUPT_PRIORITY` to call FreeRTOS `FromISR` APIs safely; higher-prio ISRs must not call the kernel.

## Stacks & memory
- **Each task has its own stack** (sized in words at create time). Overflow corrupts adjacent memory / another task. Enable `configCHECK_FOR_STACK_OVERFLOW` (2) + `uxTaskGetStackHighWaterMark` to right-size.
- Kernel objects allocated via `pvPortMalloc` — pick a heap scheme: heap_1 (no free), heap_4 (coalescing, common), heap_5 (multi-region). For hard real-time / certification use **static allocation** (`xTaskCreateStatic`, `configSUPPORT_STATIC_ALLOCATION`) — no heap at all.
- ISRs use the main/system stack (Cortex-M MSP), separate from task stacks (PSP).

## Timing
- Tick ISR drives delays, timeouts, round-robin. Finer resolution -> hardware timer + input capture, or a tickless high-res timer.
- `vTaskDelay` = "sleep at least N ticks from now" (drifts with jitter). `vTaskDelayUntil` = "wake every N ticks" (no accumulated drift) — use for periodic sampling/control loops.
- Software timers (`xTimerCreate`) run callbacks in the timer service task — callbacks must not block.
- **Tickless idle** for low power: kernel stops the periodic tick during long idle and sleeps the MCU, waking on the next scheduled event — cuts battery drain without losing timekeeping.

## Design guidelines
- **Assign priorities by deadline/period**, not by "importance": tighter deadline -> higher priority (rate-monotonic). Reserve the top priorities for the shortest, most time-critical handlers.
- Keep the number of priority levels small and deliberate; too many makes analysis hard. Group tasks: fast periodic control, event-driven, background/housekeeping, idle.
- One responsibility per task; communicate via queues, not shared globals. Bound every wait with a timeout so a stuck peer can't hang a task forever.
- Every task must eventually **block** (delay, queue, sem) so lower-priority work and the idle/watchdog task get to run.

## Kernel objects & patterns
- **Event groups**: wait on / set combinations of bits (`xEventGroupWaitBits`) — sync a task on several conditions at once.
- **Stream/message buffers**: efficient single-reader/single-writer byte or variable-length message transport (great for ISR -> task data streams like UART RX).
- **Gatekeeper task** pattern: one task owns a shared resource (e.g. a display or log); others send requests via its queue — removes the need for a mutex and serializes access cleanly.

## Gotchas -> Fix
- **Priority inversion** stalls a high-prio task. Fix: use a mutex (priority inheritance), not a binary semaphore, for shared resources; shrink critical sections.
- **Stack overflow** -> random corruption/hardfault. Fix: enable overflow check hook, measure high-water mark, size for worst-case + ISR nesting.
- **Starving low-prio tasks**: a high-prio task never blocks, so lower ones never run (watchdog not fed). Fix: every task must block on something (delay/queue/sem); no busy-wait spin at high priority.
- **Blocking API in an ISR** (`xQueueSend` instead of `...FromISR`, or `vTaskDelay`): corrupts kernel state. Fix: only `FromISR` variants in ISRs; never delay in an ISR.
- **Calling kernel API from a too-high-priority ISR**: undefined behavior. Fix: keep such ISR priority <= `configMAX_SYSCALL_INTERRUPT_PRIORITY`.
- **Unbounded queue growth / producer faster than consumer**: memory blowup or blocked producer stalls the system. Fix: bound queue length, drop or back-pressure, size for burst.
- **Sharing data via globals without protection**: torn reads/races. Fix: pass by queue, or guard with mutex/critical section; mark ISR-shared as `volatile`.
- **`vTaskDelay` used for periodic loop** drifts and jitters. Fix: `vTaskDelayUntil`.
- **Mutex taken in one task, given in another**: breaks ownership/inheritance. Fix: use a semaphore for cross-task signaling; mutex give/take in the same task.
- **Long critical section / interrupts disabled too long**: blows real-time deadlines, increases latency/jitter. Fix: minimize; defer work to tasks.
- **Forgetting `portYIELD_FROM_ISR`**: response delayed until next tick. Fix: yield when the ISR unblocks a higher-prio task.
- **Deadlock** from taking two mutexes in different orders. Fix: global lock ordering, or timeouts on takes.
