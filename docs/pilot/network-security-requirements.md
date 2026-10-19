# Network & Security Architecture Requirements
# متطلبات الشبكة وأمن المعلومات لربط أنظمة الجامعات

This document outlines the network configurations, transport encryption standards, IP allowlisting requirements, and advanced security protections enforced by Morshidi when communicating with University Student Information Systems.

---

## 1. Network Topology & Communication Direction
## المخطط الشبكي واتجاه الاتصالات

```
   [ University Campus / SIS Gateway ]                     [ Morshidi Cloud Engine ]
+───────────────────────────────────────+               +───────────────────────────+
|                                       |               |                           |
|  - University SIS REST API            |<──────────────| - SIS Integration Service |
|    (Inbound Port 443 HTTPS)           |   Outbound    |   (Egress via TLS 1.3)    |
|                                       |   REST Calls  |                           |
|                                       |               |                           |
|  - Campus Webhook Dispatcher          |──────────────>| - Webhook Inbound Receiver|
|    (Outbound Port 443 HTTPS)          |   Inbound     |   (POST /webhooks/...)    |
|                                       |   Events      |                           |
+───────────────────────────────────────+               +───────────────────────────+
```

1. **Outbound Calls (Morshidi -> University)**:  
   Morshidi initiates outbound HTTPS requests to the university's exposed SIS Gateway URL to query catalog, offerings, student records, and submit registrations.
2. **Inbound Calls (University -> Morshidi)**:  
   The university SIS dispatches signed webhook events to Morshidi's webhook receiver endpoint.

---

## 2. Transport Layer Security (TLS) Standards

- **Protocol Version**: TLS 1.3 is strongly recommended; TLS 1.2 is the absolute minimum. TLS 1.0, 1.1, and plaintext HTTP are unconditionally blocked.
- **Certificate Authority**: The University SIS API endpoint must present a valid X.509 certificate issued by a globally recognized public Certificate Authority (e.g. DigiCert, Let's Encrypt, Sectigo). Self-signed certificates are rejected in production.
- **Cipher Suites Approved**:
  - `TLS_AES_256_GCM_SHA384`
  - `TLS_CHACHA20_POLY1305_SHA256`
  - `TLS_AES_128_GCM_SHA256`
  - `ECDHE-ECDSA-AES256-GCM-SHA384`
  - `ECDHE-RSA-AES256-GCM-SHA384`

---

## 3. Strict SSRF Defense Architecture
## نظام الحماية الصارم من هجمات تزوير الطلبات (SSRF)

To prevent internal network traversal, port scanning, or cloud metadata exfiltration, Morshidi’s integration adapter evaluates **every target URL** through a deterministic multi-stage security pipeline (`validate_target_url` in `sis_integration/security.py`) before initiating any connection.

### 3.1 Prohibited Address Ranges
Morshidi strictly forbids connections to:
- **Private RFC 1918 Networks**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.
- **Loopback Addresses**: `127.0.0.0/8`, `::1`.
- **Link-Local Addresses**: `169.254.0.0/16`, `fe80::/10`.
- **Cloud Metadata Services**: `169.254.169.254`, `metadata.google.internal`, `169.254.169.2`.
- **Broadcast & Multicast**: `224.0.0.0/4`, `255.255.255.255`.

### 3.2 DNS Rebinding Protection
To prevent DNS rebinding attacks where a domain resolves to a public IP first and then switches to an internal IP:
- Hostnames are resolved to IP addresses prior to connection.
- The resolved IP is verified against the prohibited ranges.
- The HTTP client pins the validated IP for the duration of the request.

---

## 4. IP Allowlisting for Campus Firewalls
## القائمة البيضاء لعناوين IP لجدار الحماية الجامعي

University IT departments configuring border firewalls or API Gateways (WAF) should allow inbound HTTPS (Port 443) traffic from Morshidi egress IP ranges:

### Morshidi Egress Addresses (Production):
- `52.28.182.100/32`
- `52.28.182.101/32`
- `18.196.220.50/32`

*(For dedicated staging or VPN-connected pilot instances, institutional IT coordinates with `security@morshidi.edu` for static IP reservation).*

---

## 5. Secret & Credential Protection

1. **Zero Plaintext Secrets in Database**:  
   Integration credentials (such as API bearer tokens, OAuth client secrets, or webhook HMAC keys) are **never stored as plaintext** in the database table `university_integration_configs`.
2. **Environment & Vault References (`secret_env_ref`)**:  
   Configurations reference environment variables (e.g., `ZARQA_UNI_SERVICE_KEY`) or cloud secrets manager paths.
3. **Response Masking**:  
   The institutional API, UI dashboards, and logs mask all credentials. The API returns status `CONFIGURED` or `MISSING` with a 4-character SHA-256 fingerprint (e.g. `****3a8f`), never exposing the actual token.

---

## 6. Rate Limiting & Backoff Governance

- **Default Quota**: 600 requests per minute (RPM) per university tenant.
- **Burst Allowance**: 100 requests per 10-second window.
- **Backoff Protocol**:  
  When receiving HTTP status `429 Too Many Requests`, Morshidi honors the `Retry-After` header. If absent, Morshidi applies truncated exponential backoff with jitter:
  $$\text{WaitTime} = \min(60, 2^{\text{retry}} + \text{jitter})$$

---

## 7. Audit Logging & Compliance Monitoring

All integration events are recorded in an append-only audit trail (`university_integration_audit_log`):
- Timestamp, Actor (System / User ID)
- Action: `CONFIG_UPDATED`, `SYNC_TRIGGERED`, `WEBHOOK_RECEIVED`, `RECONCILIATION_RUN`
- Status: `SUCCESS`, `FAILURE`
- Zero credentials or private student grades are logged in the audit details JSON.

