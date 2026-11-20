#!/usr/bin/env bash
set -euo pipefail

version='@VERSION@'

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

[[ $# -eq 1 ]] || fail "Usage: bash $0 ./engineering-memory_${version}_amd64.deb"
(( EUID != 0 )) || fail "Run the installer as your regular user without sudo."
[[ -t 0 && -t 1 ]] || fail "Run the installer in an interactive terminal."

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
actual=$(sha256sum < "$package")
[[ "${actual%% *}" == "$expected" ]] || fail "The package checksum does not match."

[[ "$(dpkg-deb --field "$package" Package)" == engineering-memory &&
   "$(dpkg-deb --field "$package" Architecture)" == amd64 &&
   "$(dpkg-deb --field "$package" Version)" == "$version" ]] ||
  fail "The package metadata does not match this installer."

status_format='${db:Status-Status} ${Version}'
installed=$(dpkg-query -W -f="$status_format" engineering-memory 2>/dev/null || true)
if [[ "$installed" == "installed "* ]] &&
   dpkg --compare-versions "${installed#installed }" gt "$version"; then
  fail "Engineering Memory ${installed#installed } is newer than $version. Use a clean workstation or review the installed package before retrying."
fi

sudo apt-get install --reinstall -y -- "$package" ||
  fail "Package installation failed. Resolve the apt error and run the installer again."
[[ "$(dpkg-query -W -f="$status_format" engineering-memory)" == "installed $version" ]] ||
  fail "The installed version does not match $version. Check the package installation and retry."

/usr/bin/engineering-memory setup ||
  fail "Guided setup failed. Resolve the reported problem and run the installer again. Retry can reuse your saved settings."
