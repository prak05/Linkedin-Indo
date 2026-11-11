# The C Lab Lifesaver (OS Edition): Kernel CPU Scheduling & POSIX IPC

**Domain:** Operating Systems, Kernel Engineering, Concurrency & Synchronization  
**Repository:** [https://github.com/prak05/The-C-Lab-Lifesaver-OS-Edition-](https://github.com/prak05/The-C-Lab-Lifesaver-OS-Edition-)  

---

## 📌 Executive Overview
Operating systems bridge abstract user code with raw physical hardware by managing kernel processes, CPU dispatch cycles, memory paging, and concurrent inter-process communication.

**The-C-Lab-Lifesaver-OS-Edition-** provides standard POSIX C implementations of core operating system mechanics, process schedulers, synchronization primitives, and deadlock prevention algorithms.

---

## ⚡ Technical Architecture & OS Concepts
- **CPU Scheduling Algorithms:** First-Come First-Served (FCFS), Shortest Job First (SJF preemptive & non-preemptive), Round Robin (RR) with dynamic time quantum, Priority Scheduling.
- **Process Synchronization:** POSIX Mutexes, Named/Unnamed Semaphores, Producer-Consumer and Reader-Writer classic problems.
- **Deadlock Management:** Banker's Algorithm for Resource Allocation and Safety Verification.
- **Memory Management & Page Replacement:** FIFO, Least Recently Used (LRU), Optimal Page Replacement algorithms.
- **Inter-Process Communication:** Shared memory (`shmget`, `shmat`), message queues, and pipes.

---

## 📊 Key Highlights
- **Mathematical Scheduling Metrics:** Computes precise Average Turnaround Time (TAT) and Average Waiting Time (WT) per schedule.
- **Race Condition Immunity:** Verified race-free critical section execution via atomic semaphore locks.
