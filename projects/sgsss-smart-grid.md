# SGSSS: Solar Grid Smart System & CleanTech IoT Hub

**Domain:** CleanTech, Microgrid Energy Management, Embedded IoT  
**Repository:** [https://github.com/prak05/SGSSS](https://github.com/prak05/SGSSS)  

---

## 📌 Executive Overview
Distributed solar photovoltaic (PV) systems frequently experience localized curtailment and grid instability due to uncoordinated reverse power flow into distribution transformers. Without real-time telemetry, rooftop solar systems cannot dynamically adjust output during low local demand.

**SGSSS (Solar Grid Smart System)** is an integrated embedded hardware and telemetry software platform that monitors PV generation, load consumption, battery state of charge (SoC), and grid parameters to optimize self-consumption and prevent grid overload.

---

## ⚡ Technical Architecture & Engineering Stack
- **Hardware & Firmware:** ESP32 microcontrollers, INA219 current/voltage sensors, relays, FreeRTOS, Embedded C.
- **Data Engineering & Telemetry:** Python, MQTT broker, InfluxDB time-series database, Grafana visualization dashboards.
- **Edge Analytics:** On-device threshold detection and automatic battery-to-grid switching algorithms.

---

## 📊 Key Highlights & Operational Metrics
- **Real-Time Telemetry:** Sub-second sampling of solar irradiation, voltage fluctuations, and inverter efficiency.
- **Automated Load Shedding:** Switches non-critical domestic loads during sudden solar intermittency to preserve battery life.
