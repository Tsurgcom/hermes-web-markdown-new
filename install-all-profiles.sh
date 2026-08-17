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

  printf '\n== %s ==\n' "$profile"
  if [[ -f "$plugin_home/plugin.yaml" ]]; then
    run hermes "${args[@]}" plugins enable web-markdown-new --no-allow-tool-override
  else
    run hermes "${args[@]}" plugins install "$REPO" --enable
  fi
  run hermes "${args[@]}" config set web.backend ddgs
  run hermes "${args[@]}" config set web.extract_backend markdown-new
done

printf '\nInstalled and enabled web-markdown-new for %d profile(s).\n' "${#profiles[@]}"
printf 'Start a new Hermes session (or restart the gateway) for the plugin to load.\n'
