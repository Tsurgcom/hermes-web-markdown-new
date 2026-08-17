#!/usr/bin/env bash
set -euo pipefail

# Install and enable the plugin in the default profile and every named profile.
REPO="${HERMES_MARKDOWN_NEW_REPO:-Tsurgcom/hermes-web-markdown-new}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DRY_RUN="${DRY_RUN:-0}"

profiles=(default)
profiles_dir="$HERMES_HOME/profiles"
if [[ -d "$profiles_dir" ]]; then
  for profile_dir in "$profiles_dir"/*; do
    [[ -d "$profile_dir" ]] || continue
    profiles+=("${profile_dir##*/}")
  done
fi

if [[ "$DRY_RUN" == "1" ]]; then
  printf '*** DRY RUN: no plugins will be installed, enabled, or configured. ***\n'
else
  printf '*** LIVE RUN: plugins will be installed/enabled and profiles configured. ***\n'
fi

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '+ '
    printf '%q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

for profile in "${profiles[@]}"; do
  args=()
  plugin_home="$HERMES_HOME/plugins/web-markdown-new"
  if [[ "$profile" != "default" ]]; then
    args=(-p "$profile")
    plugin_home="$profiles_dir/$profile/plugins/web-markdown-new"
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '\n== %s (DRY RUN) ==\n' "$profile"
  else
    printf '\n== %s (LIVE) ==\n' "$profile"
  fi
  if [[ -f "$plugin_home/plugin.yaml" ]]; then
    run hermes "${args[@]}" plugins enable web-markdown-new --no-allow-tool-override
  else
    run hermes "${args[@]}" plugins install "$REPO" --enable
  fi
  run hermes "${args[@]}" config set web.backend ddgs
  run hermes "${args[@]}" config set web.extract_backend markdown-new
done

if [[ "$DRY_RUN" == "1" ]]; then
  printf '\n*** DRY RUN COMPLETE: no changes were made. ***\n'
  printf 'Run the same command without DRY_RUN=1 to apply these changes.\n'
else
  printf '\nInstalled and enabled web-markdown-new for %d profile(s).\n' "${#profiles[@]}"
  printf 'Start a new Hermes session (or restart the gateway) for the plugin to load.\n'
fi
