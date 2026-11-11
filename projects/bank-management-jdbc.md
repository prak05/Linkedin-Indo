# Bank Management System (JDBC): 3-Tier Enterprise Core Architecture

**Domain:** Enterprise Application Architecture, Database Connectivity, Financial Systems  
**Repository:** [https://github.com/prak05/Bank-Management-System-JDBC](https://github.com/prak05/Bank-Management-System-JDBC)  

---

## 📌 Executive Overview
Financial core systems require absolute transactional atomicity (ACID), cryptographic credential hashing, and structured multi-tier separation between presentation, business rules, and persistent storage.

**Bank-Management-System-JDBC** is a 3-tier enterprise banking platform developed in Java and JDBC, providing secure customer account creation, balance inquiries, funds transfers, and administrative auditing.

---

## ⚡ Technical Architecture & Stack
- **Architecture:** 3-Tier Enterprise Pattern (Presentation Layer, Business Logic Layer / Service, Data Access Object / DAO Pattern).
- **Database Engine:** Oracle / MySQL with JDBC connection pooling and parameterized prepared statements.
- **Transaction Safety:** Explicit transaction boundaries (`connection.setAutoCommit(false)`, `commit()`, `rollback()` on exceptions).
- **Core Technology:** Java SE, JDBC, SQL.

---

## 📊 Key Highlights
- **Atomic Money Transfer:** Guarantees simultaneous debit and credit within a single isolated database transaction.
- **Zero SQL Injection:** 100% parameterization of queries across all DAO operations.
- **Role-Based Access Control:** Distinct privilege separation between customer account holders and bank tellers/managers.
