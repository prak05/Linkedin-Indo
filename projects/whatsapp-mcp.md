# WhatsApp-MCP: Model Context Protocol Server for WhatsApp Agent Automation

**Domain:** Agent Tooling, Autonomous Communication, MCP Infrastructure  
**Repository:** [https://github.com/prak05/WhatsApp-MCP](https://github.com/prak05/WhatsApp-MCP)  

---

## 📌 Executive Overview
Anthropic's Model Context Protocol (MCP) defines an open standard for AI agents (like Claude Code, Antigravity, and Cursor) to interact with external tools, APIs, and data sources. Direct, reliable agent communication through WhatsApp enables instant human-in-the-loop approvals, emergency operational notifications, and team synchronization.

**WhatsApp-MCP** is an enterprise-grade MCP server implementation that exposes structured tools for sending WhatsApp messages, querying chat threads, receiving inbound messages, and managing real-time webhook alerts directly from autonomous AI agent sessions.

---

## ⚡ Technical Architecture & Engineering Stack
- **Protocol:** Model Context Protocol (MCP) specification via JSON-RPC 2.0 over standard I/O (stdio).
- **Core Runtime:** TypeScript, Node.js, Baileys WebSocket API for WhatsApp Web automation.
- **Security & Session Persistence:** Multi-device encrypted authentication credentials with local QR authorization and encrypted credential stores.

---

## 📊 Key Tools Exposed to AI Agents
- `send_message`: Dispatches formatted text notifications, code blocks, or alert summaries to specified phone numbers or groups.
- `search_messages`: Queries recent message history across chat threads for context extraction.
- `list_chats`: Returns active conversations and unread status.
