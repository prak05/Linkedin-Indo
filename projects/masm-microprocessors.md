# MASM x86 Assembly Laboratory: Microprocessor Arithmetic & Interrupts

**Domain:** Low-Level Microprocessor Architecture, x86 Assembly, Hardware Systems  
**Repository:** [https://github.com/prak05/MASM](https://github.com/prak05/MASM)  

---

## 📌 Executive Overview
Gaining an intimate understanding of the hardware-software boundary requires direct programming of processor registers, segment registers, memory addressing modes, and BIOS/DOS interrupt service routines.

**MASM** contains a comprehensive suite of 16-bit and 32-bit x86 assembly language programs developed using the Microsoft Macro Assembler (MASM) for the Intel 8086/x86 microprocessor architecture.

---

## ⚡ Technical Architecture & Assembly Primitives
- **Processor Register Management:** General-purpose registers (AX, BX, CX, DX), pointer/index registers (SP, BP, SI, DI), and flag register inspection.
- **Arithmetic & Logic Routines:** Multi-byte addition, BCD arithmetic, signed multiplication/division, bitwise rotations and shifts.
- **Interrupt Handling:** DOS interrupt `INT 21h` subroutines for buffered string input/output, display rendering, and system clock reads.
- **Environment:** MASM 6.11 / DOSBox emulation environment.

---

## 📊 Key Highlights
- **Optimized Instruction Footprint:** Minimal clock cycle consumption through efficient register reuse.
- **Hardware-Level Precision:** Direct handling of carry flags, parity flags, and zero-detect branches.
