#!/usr/bin/env bash
set -euo pipefail

version='@VERSION@'

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

confirm() {
  local reply
  printf '%s [y/N] ' "$1"
  read -r reply && [[ "${reply,,}" == y || "${reply,,}" == yes ]]
}

query_installation() {
  local status
  if dpkg-query -W -f='${db:Status-Status}\t${Version}\t${X-Engineering-Memory-Build}' engineering-memory 2>/dev/null; then
    return 0
  else
    status=$?
    [[ $status -eq 1 ]] || fail "Could not read the Engineering Memory package status."
  fi
}

payload_paths() {
  local path
  while IFS= read -r path; do
    case "$path" in
      /opt/engineering-memory|/opt/engineering-memory/*|/usr/bin/engineering-memory)
        printf '%s\0' "${path#/}" ;;
    esac
  done
}

installed_build_matches() {
  local paths digest
  [[ "$1" =~ ^[0-9a-f]{64}$ ]] || return 1
  paths=$(dpkg-query -L engineering-memory) || return 1
  # Hash only package-owned paths, including modes and symlink destinations.
  # build-deb.sh records root ownership. Use actual ownership on the installed side.
  digest=$(payload_paths <<< "$paths" | LC_ALL=C sort -zu |
    tar -C / --format=gnu --mtime=@0 --numeric-owner \
      --null --no-recursion --hard-dereference -T - -cf - | sha256sum) || return 1
  [[ "${digest%% *}" == "$1" ]]
}

run_setup() {
  /usr/bin/engineering-memory setup "$@" ||
    fail "Guided setup failed. Resolve the reported problem and run the installer again. Retry can reuse your saved settings."
}

silent=false
if [[ ${1-} == --non-interactive ]]; then
  silent=true
  shift
fi
[[ $# -eq 1 ]] || fail "Usage: bash $0 [--non-interactive] ./engineering-memory_${version}_amd64.deb"
(( EUID != 0 )) || fail "Run the installer as your regular user without sudo."
if ! $silent; then
  [[ -t 0 && -t 1 ]] || fail "Run the installer in an interactive terminal."
fi

package=$(realpath -e -- "$1") || fail "Could not find the local package."
filename="engineering-memory_${version}_amd64.deb"
[[ -f "$package" && "${package##*/}" == "$filename" ]] ||
  fail "Select the $filename package for this installer."

sidecar="$package.sha256"
checksum_pattern='^([[:xdigit:]]{64})  (.+)$'
[[ -f "$sidecar" ]] || fail "Download the matching package checksum file."
mapfile -t checksum_lines < "$sidecar"
if [[ ${#checksum_lines[@]} -ne 1 || ! "${checksum_lines[0]}" =~ $checksum_pattern ||
      "${BASH_REMATCH[2]}" != "$filename" ]]; then
  fail "The package checksum file does not match $filename."
fi
expected="${BASH_REMATCH[1],,}"
verify_checksum() {
  local actual
  actual=$(sha256sum < "$package") || fail "Could not read the package checksum."
  [[ "${actual%% *}" == "$expected" ]] || fail "The package checksum does not match."
}
verify_checksum

build=$(dpkg-deb --field "$package" X-Engineering-Memory-Build) || fail "Could not read the package build identity."
[[ "$(dpkg-deb --field "$package" Package)" == engineering-memory &&
   "$(dpkg-deb --field "$package" Architecture)" == amd64 &&
   "$(dpkg-deb --field "$package" Version)" == "$version" &&
   "$build" =~ ^[0-9a-f]{64}$ ]] ||
  fail "The package metadata does not match this installer."

installed=$(query_installation)
IFS=$'\t' read -r state installed_version installed_build <<< "$installed"
if test -L /opt/engineering-memory; then
  fail "The installation directory is redirected. Correct it before retrying."
fi

reinstall=()
case "$state" in
  ''|not-installed|config-files)
    if test -e /opt/engineering-memory || test -L /usr/bin/engineering-memory || test -e /usr/bin/engineering-memory; then
      $silent && fail "Installation files have no package record. Run the launcher interactively to confirm repair."
      confirm "Repair the installation by installing $version over its remaining package files?" || exit 0
    fi
    ;;
  *)
    [[ -n "$installed_version" ]] || fail "The installed version is unknown. Review the dpkg package state before retrying."
    if dpkg --compare-versions "$installed_version" gt "$version"; then
      fail "Engineering Memory $installed_version is newer than $version. Use a matching or newer verified package."
    fi

    if [[ "$state" != installed ]] || ! installed_build_matches "$installed_build" 2>/dev/null; then
      $silent && fail "The installation is incomplete or its build cannot be verified. Run the launcher interactively to confirm repair."
      confirm "Repair the installation of $installed_version with package $version?" || exit 0
      reinstall=(--reinstall)
    elif dpkg --compare-versions "$installed_version" lt "$version"; then
      if $silent; then
        printf 'Update Engineering Memory from %s to %s.\n' "$installed_version" "$version"
      else
        confirm "Update Engineering Memory from $installed_version to $version?" || exit 0
      fi
    elif [[ "$installed_build" != "$build" ]]; then
      $silent && fail "A different build of $version is installed. Run the launcher interactively to confirm replacement."
      confirm "Replace the installed build with a different build of $version?" || exit 0
      reinstall=(--reinstall)
    else
      printf 'Engineering Memory %s with this build is already installed.\n' "$version"
      $silent && exit 0
      confirm "Open the existing settings and MCP configuration?" || exit 0
      current=$(query_installation)
      [[ "$current" == "$installed" ]] && installed_build_matches "$build" 2>/dev/null ||
        fail "The installed package changed. Run the installer again."
      run_setup --configure-only
      exit
    fi
    ;;
esac

current=$(query_installation)
[[ "$current" == "$installed" ]] || fail "The installed package changed. Run the installer again."
verify_checksum
apt_args=(apt-get install "${reinstall[@]}" --no-allow-downgrades -y -- "$package")
if $silent; then
  sudo -n "${apt_args[@]}" </dev/null ||
    fail "Package installation failed. Check noninteractive sudo access and the apt error, then retry."
else
  sudo "${apt_args[@]}" ||
    fail "Package installation failed. Resolve the apt error and run the installer again."
fi

current=$(query_installation)
[[ "$current" == "installed"$'\t'"$version"$'\t'"$build" ]] &&
  installed_build_matches "$build" 2>/dev/null ||
  fail "The installed package version, build or contents could not be verified. Check the package installation and retry."

if ! $silent; then
  run_setup
fi
