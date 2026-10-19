# University Identity & Single Sign-On (SSO) Integration Requirements
# متطلبات الربط مع موفر الهوية الموحد (SSO) وإدارة هوية الطلبة

This document defines the identity architecture, federation protocols, token claims, and safety boundaries required to connect a partner university Identity Provider (IdP) to Morshidi.

---

## 1. Core Identity Invariants
## المبادئ الأساسية لإدارة الهوية والمصادقة

1. **The University IdP is the Sole Authority on Identity**:  
   Morshidi never stores or manages passwords for students or faculty members. User authentication happens entirely within the university’s governed Identity Provider (e.g. Microsoft Entra ID, Google Workspace for Education, Keycloak, or Shibboleth/SimpleSAMLphp).

2. **Strict Preservation of Identity Strings (Leading Zeros)**:  
   Student identification numbers (e.g., `020990001` or `20210045`) **must always be treated as immutable text strings**, never as integers. Stripping leading zeros creates catastrophic identity collisions and is strictly prevented in Morshidi.

3. **Fail-Closed Identity Conflict Prevention**:  
   If an incoming SSO assertion attempts to bind a university student ID to an existing Morshidi profile that belongs to a different subject, or if an email matches a conflicting identity across tenants, the transaction **fails closed immediately** (`IDENTITY_CONFLICT`). Silent account merging or automatic identity aliasing is strictly forbidden.

---

## 2. Supported SSO Protocols

Morshidi supports two industry-standard enterprise federation protocols, plus an institutional Token-Exchange flow for custom university portals:

```
+-----------------------------------------------------------------------------------+
|                            Supported Federation Options                           |
+------------------------------------+----------------------------------------------+
| 1. OpenID Connect (OIDC)           | Recommended for modern cloud & mobile apps.  |
|    - Flow: Auth Code Flow + PKCE   | Discovery URL: /.well-known/openid-config    |
+------------------------------------+----------------------------------------------+
| 2. SAML 2.0 Web Browser SSO        | Common in legacy institutional SIS systems.  |
|    - Binding: HTTP-POST Binding    | Signed Assertions + Response Encryption      |
+------------------------------------+----------------------------------------------+
| 3. University Token Exchange       | Direct API exchange for embedded portals     |
|    - Flow: POST /auth/uni-login    | Transient university ticket exchanged server |
+------------------------------------+----------------------------------------------+
```

---

## 3. Required Token Claims & Attributes

Whether via OIDC ID Token or SAML 2.0 Attribute Statement, the Identity Provider must provide the following claims:

| Claim Key (OIDC) | SAML 2.0 Attribute | Type | Requirement | Description |
| :--- | :--- | :--- | :--- | :--- |
| `sub` | `NameID` (Persistent) | String | **Mandatory** | Unique, stable, immutable identifier for the user in the university directory. |
| `student_id` | `urn:mace:dir:attribute-def:employeeNumber` | String | **Mandatory** *(for students)* | Official university student registration number (must preserve leading zeros). |
| `email` | `urn:oid:0.9.2342.19200300.100.1.3` | String | **Mandatory** | Official institutional email address (`@uni.edu.jo`). |
| `name` | `urn:oid:2.5.4.3` | String | **Mandatory** | Student full name (Arabic or English). |
| `roles` | `urn:oid:2.5.4.11` | Array[String] | **Mandatory** | Institutional roles: `STUDENT`, `ACADEMIC_ADVISOR`, `FACULTY_DEAN`, `REGISTRAR_ADMIN`. |
| `faculty_code` | `urn:morshidi:faculty` | String | Optional | College/Faculty code (e.g., `IT`, `ENGINEERING`). |
| `major_code` | `urn:morshidi:major` | String | Optional | Program/Major code (e.g., `CS`, `AI`, `SE`). |

---

## 4. OIDC Configuration Specification

For universities configuring Microsoft Entra ID, Okta, or Google Workspace:

1. **Redirect URI / Callback URL**:  
   `https://morshidi.vercel.app/api/auth/callback/{tenant_key}`  
   (For local development: `http://localhost:3000/api/auth/callback/{tenant_key}`)

2. **Scanned Discovery Endpoint**:  
   The university IT team provides the OpenID Connect metadata document:  
   `https://login.university.edu/.well-known/openid-configuration`

3. **Grant Types Allowed**:  
   `authorization_code`, `refresh_token`.

4. **PKCE Enforcement**:  
   Code Challenge Method: `S256` (SHA-256) is mandatory.

---

## 5. SAML 2.0 Configuration Specification

For universities using Shibboleth, ADFS, or SimpleSAMLphp:

1. **Entity ID (Issuer)**:  
   `https://morshidi.edu/auth/saml/{tenant_key}`

2. **Assertion Consumer Service (ACS) URL**:  
   `https://morshidi.onrender.com/api/v1/auth/saml/acs/{tenant_key}`  
   Binding: `urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST`

3. **Signature & Encryption**:  
   - Response Signing: **Required**
   - Assertion Signing: **Required**
   - Signing Algorithm: `RSA-SHA256` (SHA-1 is rejected)
   - Clock Drift Tolerance: `120 seconds`

---

## 6. Student Linking & Conflict Resolution Workflow

```
[ Incoming SSO Assertion ]
         │
         ▼
[ Step 1: Validate Signature & Expiry ] ──(Invalid)──> [ Fail Closed: 401 UNAUTHORIZED ]
         │
         ▼
[ Step 2: Validate Required Claims ] ──(Missing sub/email)──> [ Fail Closed: 400 MALFORMED_CLAIM ]
         │
         ▼
[ Step 3: Check student_university_identities ]
         ├── Existing link for (tenant_key, external_subject)?
         │     ├── YES: Ensure student_id matches recorded mapping.
         │     │         └── If mismatch -> [ Fail Closed: IDENTITY_CONFLICT ]
         │     └── NO: Proceed to new link verification.
         │
         ▼
[ Step 4: Verify student_id uniqueness across tenant ]
         ├── Is student_id already claimed by another subject?
         │     ├── YES -> [ Fail Closed: IDENTITY_AMBIGUOUS / CONFLICT ]
         │     └── NO  -> [ Establish Verified Link: ACTIVE ]
         │
         ▼
[ Step 5: Issue Short-Lived Morshidi Session ]
```

---

## 7. Security Best Practices for Campus IT

- **Token Lifespans**:
  - Access Token TTL: `15 to 60 minutes`
  - Refresh Token TTL: `24 hours`
  - Absolute Session Max: `7 days`
- **Zero Secret Exposure**:
  - The client secret or private key used for federation is stored exclusively in Morshidi's encrypted secrets vault (or environment variable reference) and **never** in client-side code or public repositories.
- **Immediate Revocation**:
  - If a student is suspended or expelled in the SIS, the university IdP revokes the student's directory account. On the next token refresh or session check (within 15 minutes), Morshidi terminates the active session.

