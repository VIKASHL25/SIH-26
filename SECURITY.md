# 🛡️ Digital Twin Defense-in-Depth Security Policy & Architecture

## Overview

This repository implements a **Defense-in-Depth Security Model** for the DRDO / SIH MALE UAV Aero Piston Engine Digital Twin Framework. The security architecture ensures that each system layer provides autonomous security boundaries, so no single component failure compromises the overall platform.

---

## 🔒 Implemented Security Controls

### 1. Transport Layer Security (TLS / WSS)
- **Developer Certificate Generator**: `scripts/generate_dev_cert.py` generates self-signed 2048-bit RSA TLS certificates (`certs/server.crt` and `certs/server.key`).
- **Encrypted Streams**: Supports HTTPS and Secure WebSockets (`wss://`) for the Ground Control Station (GCS) telemetry dashboard.
- **Production Note**: In operational military deployments, the API Gateway sits behind the defense network's PKI-issued certificates rather than self-signed certificates.

### 2. Service-to-Service Internal Authentication
- **Shared Internal Secret**: Microservices validate the `X-Internal-Key` header against `INTERNAL_SERVICE_KEY` defined in `.env`.
- **401 Unauthorized Enforcement**: All operational endpoints across the 4 internal microservices (Ports 8001, 8002, 8003, 8004) reject unauthorized or missing key requests with `HTTP 401`.
- **Production Upgrade Path**: Mutual TLS (mTLS) with X.509 client certificates is the planned production upgrade path for zero-trust microservice mesh isolation.

### 3. API Gateway Rate Limiting & Abuse Protection
- **Gateway Rate Limiting**: In-memory sliding-window rate limiting per client IP (60 requests/minute) enforced on high-risk endpoints (`/api/simulation/step` and `/api/simulation/inject_fault`), returning `HTTP 429 Too Many Requests`.

### 4. CAN Frame Message Integrity
- **Checksum Verification**: `can_layer/can_codec.py` appends a 1-byte XOR/CRC integrity checksum to encoded CAN payloads and verifies it upon decoding.
- **Tamper Detection**: Frames failing checksum verification trigger a `[SECURITY AUDIT]` log event and are immediately dropped.
- **Production Note**: Demonstration pattern. Operational defense systems use CAN-FD SECURE (ISO 21434 / AUTOSAR SecOC) MAC headers or bus-level Intrusion Detection Systems (IDS).

### 5. Secrets Hygiene & Environment Isolation
- **Git Exclusions**: `.env` and `certs/` are explicitly listed in `.gitignore`.
- **Zero Hardcoded Credentials**: Connection strings (`MONGO_URL`) and internal keys are read dynamically from environment variables using `python-dotenv`. `.env.example` provides safe templates.

### 6. Model Integrity & Traceability
- **SHA-256 Model Fingerprinting**: At startup, `backend/model_loader.py` computes SHA-256 hashes for all 4 trained AI/ML models (`Isolation Forest`, `XGBoost Health Regressor`, `Multiclass Fault Classifier`, `ExtraTrees RUL Estimator`).
- **Integrity Validation**: Hashes are verified against `models/model_hashes.json`. Discrepancies trigger `CRITICAL: [SECURITY WARNING] Model file integrity mismatch!` alerts.
- **Prediction Traceability**: Prediction outputs include `"metadata": {"model_hashes": ...}` ensuring auditability to exact verified model artifact versions.

---

## 🗺️ Roadmap & Out-of-Scope Items

The following items are explicitly out of scope for current implementation:

1. **Telemetry Input Validation & Clamping**: Explicitly excluded per project specification; raw telemetry passed as-is.
2. **User Authentication & Role-Based Access Control (RBAC)**: JWT/OAuth2 user authentication and GCS operator role management.
3. **Mutual TLS (mTLS)**: Full X.509 client certificate authentication between all internal microservices.
4. **Hardware Security Modules (HSM)**: Cryptographic key storage using hardware security chips (TPM 2.0 / HSM).
5. **Automated CAN-FD SecOC**: AUTOSAR Secure On-Board Communication for bus-level message authentication codes.
6. **Bus Intrusion Detection System (IDS)**: Deep neural network anomaly detection on CAN arbitration timings.
