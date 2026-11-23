#!/usr/bin/env bash
set -euo pipefail
payload=$(realpath "$1")
output=$(realpath -m "$2")
version=$3
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
install -d "$output" "$stage/DEBIAN" "$stage/opt/engineering-memory" "$stage/usr/bin"
cp -a "$payload/." "$stage/opt/engineering-memory/"
ln -s /opt/engineering-memory/engineering-memory "$stage/usr/bin/engineering-memory"
# Hash package-owned paths, modes and symlink destinations independently of build timestamps.
# The package installs with root ownership. The launcher verifies that ownership on disk.
build=$(cd "$stage" && find opt/engineering-memory usr/bin/engineering-memory -print0 | LC_ALL=C sort -zu |
  tar --format=gnu --mtime=@0 --owner=0 --group=0 --numeric-owner \
    --null --no-recursion --hard-dereference -T - -cf - | sha256sum)
cat > "$stage/DEBIAN/control" <<EOF
Package: engineering-memory
Version: $version
Architecture: amd64
X-Engineering-Memory-Build: ${build%% *}
Depends: libc6 (>= 2.39)
Maintainer: Engineering Memory maintainers
Description: Private conversation history, retained and recallable
EOF
dpkg-deb --root-owner-group --build "$stage" "$output/engineering-memory_${version}_amd64.deb"
