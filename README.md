# Hermes Web Markdown New

A small Hermes Agent web-extraction backend for [Cloudflare `markdown.new`](https://markdown.new/).

It gives Hermes agents a keyless `web_extract` path that converts web pages into Markdown while retaining the normal Hermes web-provider response shape.

## What it provides

- provider name: `markdown-new`;
- extraction only — web search remains delegated to the configured search backend, normally `ddgs`;
- no API key or account required by this plugin;
- per-URL error results instead of aborting an entire batch;
- title/body parsing compatible with the normal Hermes web extraction envelope;
- explicit handling for HTTP 403 and 429 responses.

## Hermes setup

Install the plugin into the profile or global Hermes plugin directory, then enable it:

```bash
hermes plugins enable web-markdown-new
hermes config set web.backend ddgs
hermes config set web.extract_backend markdown-new
```

For a profile:

```bash
hermes -p ariadne plugins enable web-markdown-new
hermes -p ariadne config set web.extract_backend markdown-new
```

The model-facing tool is Hermes's normal **`web_extract`** tool. This repository is the provider behind that tool; it is not a replacement CLI.

## Agent policy

Agents should call `web_extract` directly. They should not ask the operator to run a shell command, `curl`, or a custom wrapper for ordinary page extraction. Search and extraction remain separate: use `web_search` to discover URLs and `web_extract` to fetch page content.

## Limitations

`markdown.new` is an external conversion service. It can refuse pages, rate-limit requests, or fail on JavaScript-heavy/private content. The provider returns those failures as structured per-URL errors. Do not treat a failed extraction as evidence that a page does not exist.

## License

MIT. See [`LICENSE`](LICENSE).
