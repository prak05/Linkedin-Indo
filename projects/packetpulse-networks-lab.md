# PacketPulse Networks Lab: Low-Level C Socket Programming & Network Protocols

**Domain:** Computer Networking, Network Systems, POSIX Socket Programming  
**Repository:** [https://github.com/prak05/PacketPulse-Networks-Lab](https://github.com/prak05/PacketPulse-Networks-Lab)  

---

## 📌 Executive Overview
Network reliability and distributed communication depend on deterministic implementations of transport protocols, framing mechanisms, and socket lifecycle management.

**PacketPulse-Networks-Lab** is an engineering testbed implementing low-level client-server network applications, automatic repeat request (ARQ) flow control algorithms, and traffic analysis routines in pure C.

---

## ⚡ Technical Architecture & Protocol Suite
- **POSIX Sockets:** High-concurrency TCP stream and UDP datagram sockets (`socket()`, `bind()`, `listen()`, `accept()`, `send()`, `recv()`).
- **Flow & Error Control Algorithms:** Stop-and-Wait ARQ, Go-Back-N ARQ, Selective Repeat ARQ, and Hamming code error detection/correction.
- **Network Protocol Simulations:** Distance Vector Routing (Bellman-Ford), Link State Routing (Dijkstra), sliding window mechanisms.
- **Traffic Analysis:** Packet sniffing and Wireshark capture validation.

---

## 📊 Key Highlights
- **Deterministic Timeout Handling:** Emulated packet loss and frame corruption with socket timeout alarms (`select()` and `setsockopt`).
- **Multi-Client TCP Servers:** Concurrency via `fork()` process isolation and non-blocking I/O.
