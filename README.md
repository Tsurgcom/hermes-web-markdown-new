# Hermes Web Markdown New

A small Hermes Agent web-extraction backend for [`markdown.new`](https://markdown.new/).

> **⚠️ third-party service.** `markdown.new` is **not Cloudflare official** —
> despite the domain, it is an independent project run by Fatih Elbeyoglu
> ([elbeyoglu.com](https://elbeyoglu.com/)). Every URL you extract — and the
> full fetched page content returned — **passes through their server**. Do
> not use it for authenticated, private, or sensitive pages.

It gives Hermes agents a keyless `web_extract` path that converts web pages into Markdown while retaining the normal Hermes web-provider response shape.

## Install and enable everywhere

**Recommended** — use Hermes's own plugin manager (no shell scripts piped over the network):

```bash
hermes plugins install Tsurgcom/hermes-web-markdown-new --enable
hermes config set web.backend ddgs
hermes config set web.extract_backend markdown-new
```

For the default profile **plus every named profile** under `~/.hermes/profiles/`, use the bundled installer — but run it *without* piping: download, review, then execute.

```bash
curl -fsSL -o install-all-profiles.sh \
  https://raw.githubusercontent.com/Tsurgcom/hermes-web-markdown-new/main/install-all-profiles.sh

# Review what it does first (it is short — ~60 lines):
less install-all-profiles.sh

# Preview the exact commands without changing anything:
DRY_RUN=1 bash install-all-profiles.sh

# Apply:
bash install-all-profiles.sh
```

> **Note:** there is deliberately no one-liner that pipes a downloaded
> script straight into a shell in this README. That pattern trips every
> command-approval gate and security scanner (including Hermes's own
> smart-approval and plugin security scan); the download-and-review form
> above is the same install with the risk removed.

The installer refuses to run as root and fails fast if the `hermes` CLI is missing. For a non-default Hermes home:

```bash
HERMES_HOME=/path/to/.hermes bash install-all-profiles.sh
```

It also configures:

```yaml
web:
  backend: ddgs
  extract_backend: markdown-new
```

Start a new Hermes session, or restart each gateway, after installation.

For one profile only (no script involved):

```bash
hermes -p ariadne plugins install Tsurgcom/hermes-web-markdown-new --enable
hermes -p ariadne config set web.backend ddgs
hermes -p ariadne config set web.extract_backend markdown-new
```

## What it provides

- provider name: `markdown-new`;
- extraction only — web search remains delegated to the configured search backend, normally `ddgs`;
- no API key or account required by this plugin;
- per-URL error results instead of aborting an entire batch;
- title/body parsing compatible with the normal Hermes web extraction envelope;
- explicit handling for HTTP 403 and 429 responses, with one bounded retry on transient 429/5xx;
- strict URL validation, a response size cap, and request timeouts (see `SECURITY.md`).

## How agents use it

The model-facing tool is Hermes's normal **`web_extract`** tool. This repository is the provider behind that tool; it is not a replacement CLI.

Agents should call `web_extract` directly:

```text
web_search  → discover URLs
web_extract → fetch and convert URLs through markdown.new
```

They should not ask the operator to run a shell command, `curl`, or a custom wrapper for ordinary page extraction.

## Limitations

`markdown.new` is an external conversion service. It can refuse pages, rate-limit requests, or fail on JavaScript-heavy/private content. The provider returns those failures as structured per-URL errors. Do not treat a failed extraction as evidence that a page does not exist.

## Security

See [`SECURITY.md`](SECURITY.md). Short version: keyless, holds no secrets, never spawns a shell, talks to exactly one HTTPS host, validates every URL, and caps response size and time.

## Tests

```bash
python -m pytest tests -q
```

Tests run standalone (a `conftest.py` stubs the Hermes runtime import) and also inside a Hermes checkout.

## License

MIT. See [`LICENSE`](LICENSE).
