# SysForge Systems Lab: Two-Pass Assemblers, Macro Processors & Loaders

**Domain:** Systems Programming, Low-Level Software Engineering, Computer Architecture  
**Repository:** [https://github.com/prak05/SysForge-Systems-Lab](https://github.com/prak05/SysForge-Systems-Lab)  

---

## 📌 Executive Overview
Understanding system software—how mnemonic assembly translates to object code, how macros expand, and how object modules link and relocate into main memory—is fundamental to low-level engineering.

**SysForge-Systems-Lab** provides clean, robust C implementations of foundational system software for the hypothetical SIC/XE (Simplified Instructional Computer) architecture.

---

## ⚡ Technical Architecture & Systems Components
- **Two-Pass Assembler:** Pass 1 generates symbol table (SYMTAB) and location counters (LOCCTR); Pass 2 synthesizes text records, modification records, and end records.
- **One-Pass & Two-Pass Macro Processors:** Definition table (DEFTAB), Name table (NAMTAB), Argument table (ARGTAB) with nested macro expansion.
- **Loaders & Linkers:** Direct-linking loaders, relocating loaders using bitmasks and relocation bits, and absolute loaders.
- **Core Technology:** C, POSIX APIs, Standard I/O.

---

## 📊 Key Highlights
- **Spec-Compliant Object Files:** Generates standard SIC/XE Header (H), Text (T), Modification (M), and End (E) records.
- **Zero Memory Leaks:** Rigorously valgrind-tested pointer-safe C data structures.
