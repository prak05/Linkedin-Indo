# LexiFlux Compiler Lab: Compiler Design, Lexical Analyzers & LR Parsers

**Domain:** Compiler Engineering, Formal Language Theory, Systems Programming  
**Repository:** [https://github.com/prak05/LexiFlux-Compiler-Lab](https://github.com/prak05/LexiFlux-Compiler-Lab)  

---

## 📌 Executive Overview
Compiler construction represents one of the foundational disciplines of computer science, translating high-level human-readable languages into efficient, deterministic machine instructions through distinct lexical, syntactical, and intermediate phases.

**LexiFlux-Compiler-Lab** is a comprehensive systems laboratory repository implementing lexical tokenizers, context-free grammar parsers, abstract syntax tree (AST) generators, and intermediate code representation.

---

## ⚡ Technical Architecture & Compiler Toolchain
- **Lexical Analysis:** Flex (Fast Lexical Analyzer Generator) and handwritten finite automata (DFA/NFA) for tokenizing keywords, identifiers, and literals.
- **Syntax Analysis:** Yacc / Bison (LALR(1) parser generators), recursive descent parsers, operator precedence parsers.
- **Intermediate Code & Optimization:** Three-address code (TAC) generation, quadruples, triples, and constant folding.
- **Implementation Language:** ANSI C / C99, Makefiles, GCC.

---

## 📊 Key Highlights & Grammar Coverage
- **Complete Expression Grammars:** Strict precedence resolution for arithmetic, logical, and relational operators.
- **Syntax Error Recovery:** Deterministic panic-mode recovery providing informative error line numbers.
- **Symbol Table Engineering:** Hash-bucket symbol table with scope hierarchy management.
