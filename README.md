# Hermes Web Markdown New

A small Hermes Agent web-extraction backend for [Cloudflare `markdown.new`](https://markdown.new/).

It gives Hermes agents a keyless `web_extract` path that converts web pages into Markdown while retaining the normal Hermes web-provider response shape.

## Install and enable everywhere

Run this **one line**:

```bash
curl -fsSL https://raw.githubusercontent.com/Tsurgcom/hermes-web-markdown-new/main/install-all-profiles.sh | bash
```

By default, it installs and enables the plugin in:

- the default Hermes profile; and
- every profile directory under `~/.hermes/profiles/`.

It also configures:

```yaml
web:
  backend: ddgs
  extract_backend: markdown-new
```

Start a new Hermes session, or restart each gateway, after installation.

For a non-default Hermes home:

```bash
curl -fsSL https://raw.githubusercontent.com/Tsurgcom/hermes-web-markdown-new/main/install-all-profiles.sh | HERMES_HOME=/path/to/.hermes bash
```

Preview what the installer would do without changing anything. The output will explicitly say `DRY RUN` and end with `no changes were made`:

```bash
curl -fsSL https://raw.githubusercontent.com/Tsurgcom/hermes-web-markdown-new/main/install-all-profiles.sh | DRY_RUN=1 bash
```

## What it provides

- provider name: `markdown-new`;
- extraction only — web search remains delegated to the configured search backend, normally `ddgs`;
- no API key or account required by this plugin;
- per-URL error results instead of aborting an entire batch;
- title/body parsing compatible with the normal Hermes web extraction envelope;
- explicit handling for HTTP 403 and 429 responses.

## How agents use it

The model-facing tool is Hermes's normal **`web_extract`** tool. This repository is the provider behind that tool; it is not a replacement CLI.

Agents should call `web_extract` directly:

```text
web_search  → discover URLs
web_extract → fetch and convert URLs through markdown.new
```

They should not ask the operator to run a shell command, `curl`, or a custom wrapper for ordinary page extraction.

## Manual installation

The one-line installer is recommended. For one profile only:

```bash
hermes -p ariadne plugins install Tsurgcom/hermes-web-markdown-new --enable
hermes -p ariadne config set web.backend ddgs
hermes -p ariadne config set web.extract_backend markdown-new
```

## Limitations

`markdown.new` is an external conversion service. It can refuse pages, rate-limit requests, or fail on JavaScript-heavy/private content. The provider returns those failures as structured per-URL errors. Do not treat a failed extraction as evidence that a page does not exist.

## License

MIT. See [`LICENSE`](LICENSE).
