# Phase 2 Agent Implementation Guide

## Objective
Implement Phase 2 of the backend according to the SRS and the project progress report. Phase 2 must deliver the security primitives required before authentication and connection-registry work can begin.

This guide is intentionally explicit. Work module by module. Do not combine unrelated features into one change. After every module, add or update tests for every implemented behavior, then run the relevant test suite and report the results before moving to the next module.

---

## Ground truth from the requirements

The SRS requires the system to provide:
- secure login with username/password
- password hashing instead of plain-text storage
- role-based access control (admin/viewer)
- report execution and download access
- secure handling of database connection credentials
- JWT-based authentication support
- server-side enforcement of permissions
- secure, parameterized database access

The project progress report identifies Phase 2 as the Security Core and splits it into three modules:
1. Module 2.1: password hashing and JWT utilities
2. Module 2.2: encrypted credential handling and startup validation
3. Module 2.3: tests for the above modules

---

## Repository verification before implementation

Before editing code, verify the current state of the repository.

### Confirm the existing backend structure
The current repo already contains:
- [app/config.py](app/config.py): environment-based settings loader
- [app/core/errors.py](app/core/errors.py): AppError hierarchy and exception handlers
- [app/core/logging_config.py](app/core/logging_config.py): structured logging
- [app/db/mssql.py](app/db/mssql.py): database connection management
- [app/db/proc.py](app/db/proc.py): stored procedure/function caller
- [app/main.py](app/main.py): FastAPI entrypoint

### Confirm what is missing for Phase 2
The following Phase 2 implementation files do not exist yet and must be created:
- [app/core/security.py](app/core/security.py)
- [app/core/crypto.py](app/core/crypto.py)

The following tests do not exist yet and must be created:
- [tests/test_security.py](tests/test_security.py)
- [tests/test_crypto.py](tests/test_crypto.py)

### Baseline verification
Run the current test suite before changes:
- `pytest`

Expected result before Phase 2 work: the existing suite should pass, and the new Phase 2 tests should not yet exist.

---

## Working method

For each module:
1. Read the existing code around the relevant module.
2. Implement the smallest correct change that satisfies the module requirements.
3. Add tests for every implemented behavior.
4. Run the relevant tests.
5. Fix issues until tests pass.
6. Report the module outcome before starting the next module.

Do not add unrelated features. Do not bypass the existing error-handling style. Do not log secrets or tokens.

---

## Module 2.1: app/core/security.py

### Purpose
Create the core security primitives needed for authentication and future RBAC flows.

### Required implementation
Create [app/core/security.py](app/core/security.py) with the following functions:
- `hash_password(plain: str) -> str`
  - Use bcrypt.
  - Return a bcrypt hash string.
  - The implementation must not store plaintext passwords.
- `verify_password(plain: str, hashed: str) -> bool`
  - Use constant-time verification.
  - Return `True` for a correct password and `False` otherwise.
- `create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str`
  - Create a signed JWT.
  - Embed at least `sub` and `role` claims.
  - Use the expiration logic driven by `JWT_EXPIRE_MINUTES` from settings when no explicit value is passed.
  - Do not hardcode secrets; use the existing settings loader.
- `decode_access_token(token: str) -> dict[str, Any]`
  - Verify the JWT signature and expiry.
  - Return the decoded payload.
  - Raise the existing `AuthError` on bad signature, malformed token, or expired token.

### Architectural rules
- Reuse the existing configuration system from [app/config.py](app/config.py).
- Reuse the existing error type `AuthError` from [app/core/errors.py](app/core/errors.py).
- Keep the module focused on cryptographic primitives only.
- Do not log tokens, passwords, or secrets.
- Add docstrings and type hints for every function.

### Required tests
Create [tests/test_security.py](tests/test_security.py) with tests for:
1. `hash_password` produces a bcrypt hash and does not equal the plaintext input.
2. `verify_password` returns `True` for the correct password and `False` for the wrong password.
3. Two hashes of the same input are different because bcrypt includes a salt.
4. `create_access_token` and `decode_access_token` round-trip a subject and role correctly.
5. `decode_access_token` raises `AuthError` for an expired token.
6. `decode_access_token` raises `AuthError` for a tampered token.
7. No password, token, or secret is written to logs or error messages during failures.

### Verification commands
Run:
- `pytest tests/test_security.py`
- `pytest`

### Module completion checklist
Before moving on, confirm all of the following:
- the module exists and is imported correctly
- bcrypt-based hashing works
- JWT creation and decoding work
- invalid tokens raise `AuthError`
- test coverage exists for every implemented behavior
- the full suite still passes

### Module report format
After finishing this module, report:
- implemented functions
- files changed
- tests added
- pass/fail results
- any blockers or follow-up work

---

## Module 2.2: app/core/crypto.py

### Purpose
Create the symmetric-encryption primitives needed to protect database connection credentials.

### Required implementation
Create [app/core/crypto.py](app/core/crypto.py) with the following functions:
- `encrypt_secret(plain: str) -> bytes`
  - Encrypt a plaintext secret using a symmetric cipher.
  - Use the existing environment-based encryption key from settings.
  - Return bytes suitable for storage in a VARBINARY column.
- `decrypt_secret(blob: bytes) -> str`
  - Decrypt bytes and return the original plaintext string.
  - The function must only be used in the secure runtime path, not for logging or error output.
- Startup validation
  - Validate `CRED_ENCRYPTION_KEY` at startup and fail fast if the key is malformed.
  - The validation should occur before runtime operations begin.
  - Use a well-formed 32-byte url-safe base64 key format consistent with Fernet.

### Architectural rules
- Read the encryption key from the existing settings system in [app/config.py](app/config.py).
- Use a secure symmetric encryption mechanism available in the current dependencies (Fernet is the most straightforward and compatible with the SRS wording).
- Do not log plaintext secrets, ciphertext values, or keys.
- If configuration is invalid, raise a clear error during startup rather than letting a later report execution fail unexpectedly.
- Add docstrings and type hints for every function.

### Required tests
Create [tests/test_crypto.py](tests/test_crypto.py) with tests for:
1. `encrypt_secret` and `decrypt_secret` round-trip a plaintext secret correctly.
2. Ciphertext is not equal to plaintext.
3. A malformed encryption key raises an error during startup validation.
4. A valid encryption key passes startup validation.
5. No plaintext secret, key, or token is written to logs or error messages.

### Verification commands
Run:
- `pytest tests/test_crypto.py`
- `pytest`

### Module completion checklist
Before moving on, confirm all of the following:
- encryption and decryption round-trip successfully
- ciphertext is different from plaintext
- startup validation rejects malformed keys
- valid keys are accepted
- no secret or key is exposed in logs or errors
- the full suite still passes

### Module report format
After finishing this module, report:
- implemented functions
- files changed
- tests added
- pass/fail results
- any blockers or follow-up work

---

## Module 2.3: Tests and regression verification

### Purpose
Ensure the security core is fully covered and does not introduce regressions in the existing backend.

### Required work
- Confirm the new tests exist and are meaningful.
- Verify that the new code does not break the existing Phase 0 and Phase 1 functionality.
- Keep the repository suite green.

### Required tests
- [tests/test_security.py](tests/test_security.py)
- [tests/test_crypto.py](tests/test_crypto.py)
- existing suite under [tests](tests)

### Verification commands
Run:
- `pytest tests/test_security.py tests/test_crypto.py`
- `pytest`

### Module completion checklist
- both new test files pass
- the full repository suite passes
- no regressions appear in config, logging, errors, health, DB connection, or stored-procedure testing

---

## Final instructions to the agent

Do not start Phase 3 until Phase 2 is complete, tested, and verified.

When you finish, provide a concise but complete summary for each module in this format:

### Module 2.1 — Password Hashing & JWT
- Implemented functions:
- Tests added:
- Verification:
- Achievements:

### Module 2.2 — Credential Encryption
- Implemented functions:
- Tests added:
- Verification:
- Achievements:

### Module 2.3 — Tests & Regression Verification
- Tests added:
- Verification:
- Achievements:

Do not leave ambiguity. Every step must be implemented and verified before the next module begins.
