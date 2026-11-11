# QueryCore DBMS Lab & Oracle SQL Playbook: Enterprise Relational Engineering

**Domain:** Database Management Systems, Enterprise Relational Engineering, PL/SQL  
**Repository:** [https://github.com/prak05/QueryCore-DBMS-Lab](https://github.com/prak05/QueryCore-DBMS-Lab)  
**Related Repo:** [https://github.com/prak05/OracleCore-SQL-Playbook](https://github.com/prak05/OracleCore-SQL-Playbook)  

---

## 📌 Executive Overview
Enterprise database systems require rigorous normalization (up to BCNF/4NF), strict ACID transaction isolation, and high-performance server-side procedural logic to maintain relational integrity at scale.

**QueryCore-DBMS-Lab** is a comprehensive database engineering suite encompassing relational algebra proofs, complex SQL queries, and enterprise PL/SQL stored procedures, packages, triggers, and cursors.

---

## ⚡ Technical Architecture & Database Stack
- **Procedural Logic:** Oracle PL/SQL, explicit cursors with `FOR UPDATE` locks, parameterized cursors, row-level `BEFORE`/`AFTER` triggers.
- **Schema Design:** Boyce-Codd Normal Form (BCNF), 3NF decomposition, foreign key cascading constraints.
- **Transaction Controls:** `SAVEPOINT`, `COMMIT`, `ROLLBACK`, deadlock avoidance patterns.
- **Engines:** Oracle Database 19c / 21c, MySQL, PostgreSQL.

---

## 📊 Key Highlights & Enterprise Patterns
- **Audit Logging Triggers:** Automated shadow tables recording historical DML operations and user timestamps.
- **Optimized Analytical Queries:** Window functions (`ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`), recursive Common Table Expressions (CTEs), and indexed joins.
