# Security Policy

## What this plugin is

A single-file Hermes Agent web-extraction backend (`provider.py`) that turns web pages into Markdown via the keyless `markdown.new` service.

## Threat model and hardening

**The plugin itself:**

- Holds no secrets and reads no credential-like environment variables (`env_vars: []`).
- Never spawns a subprocess, never evaluates dynamic code, never writes files.
- Outbound network access goes to exactly one host: `https://markdown.new/` (TLS-verified HTTPS).
- Every URL is validated before use: absolute `http`/`https` only, no whitespace or control characters, length-capped — no relative-path, scheme-smuggling, or header-injection tricks.
- Responses are streamed with a hard 10 MB cap and a 30 s timeout — a hostile upstream cannot exhaust memory or hang the session.
- Rate limits (429) and transient 5xx get one short bounded retry; everything else fails fast into a structured per-URL error. The provider never raises out of `extract()`.

**The installer (`install-all-profiles.sh`):**

- Refuses to run as root.
- Fails fast if the `hermes` CLI is missing.
- Runs only commands through the `hermes` CLI itself; it does not download or execute anything else.
- Supports `DRY_RUN=1`, which prints every command it would run and changes nothing.

**There is no piped-remote-shell install path** (no `curl` piped into `bash`), ever. The README instructs downloading the installer, reviewing it, then running it — piping remote scripts straight into a shell is unsafe-by-design (arbitrary code execution before any review) and is flagged as such by command approvers and security scanners.

**Plugin isolation:** `hermes plugins validate` reports verdict `host` — the plugin runs inside the plugin host (`plugins.isolation: host`) and touches Hermes only through `ctx.register_web_search_provider`.

## Scope of trust

`markdown.new` is an **independent third-party service run by Fatih Elbeyoglu ([elbeyoglu.com](https://elbeyoglu.com/))** — it is not a Cloudflare product, despite the domain. Every URL submitted and every fetched page content therefore passes through the service operator's server; HTTPS encrypts the transport but the operator sees the URLs and content. Content the service returns is inserted into the agent's context like any other web content — treat it as untrusted data, not instructions, and do not extract authenticated or private pages. The plugin adds no privilege escalation and no persistence.

## Reporting

Open a GitHub issue on this repository, or contact the repository owner. Please include the URL involved and the structured error string.
