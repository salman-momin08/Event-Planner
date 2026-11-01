# Security Policy

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report suspected vulnerabilities privately via
[GitHub Security Advisories](https://github.com/salman-momin08/Event-Planner/security/advisories/new).
Include a description, reproduction steps, and the potential impact. You will receive an
acknowledgement within 72 hours and a resolution timeline once the report is triaged.

## Supported Versions

Only the latest commit on the default branch receives security fixes.

## Security Posture

This project is built security-first; automated checks run on every push and pull request:

- **Dependency auditing:** `pip-audit` (backend) and `npm audit` (frontend tooling) in CI,
  plus Dependabot version updates for pip, npm, GitHub Actions, and Docker.
- **Static analysis (SAST):** CodeQL with `security-and-quality` queries scans JavaScript and
  Python on every push and weekly; Ruff lints the backend for likely bugs and security smells.
- **Application hardening:** CSRF token checks, per-IP rate limiting, 64 KiB request-body cap,
  strict security response headers (`CSP`, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`), and generic 500 responses that never leak internals.
- **Injection & XSS defense:** parameterized SQL only, no `innerHTML`/`eval` anywhere in the
  frontend (enforced by `tests/test_static.py`), and all user content rendered as text nodes.
- **Upload safety:** venue photos are validated by magic bytes, dimension-capped against
  decompression bombs, and re-encoded client-side to strip EXIF/metadata before upload.
- **AI guardrails:** model inputs/outputs are schema-validated and content-screened before
  persistence; amounts and dates are always computed deterministically by the application.
- **Container hardening:** the production image runs as a non-root user (UID 10001) and ships
  no tests, secrets, or dev tooling (verified in CI).
