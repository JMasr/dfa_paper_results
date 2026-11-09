#!/bin/bash
# Render the HTML/SVG figures to tight, single-page PDFs for \includegraphics.
#
#   ./build_figs.sh            render every fig_*.html in this directory
#   ./build_figs.sh fig_cards  render one (with or without .html)
#
# Each HTML sets an exact @page size and a body clipped to it, so the print is a
# single page at the figure's own dimensions; pdfcrop then trims any hairline
# margin. Output: <name>.pdf beside the source. Requires chromium + pdfcrop.
set -u
cd "$(dirname "$0")"
CHROME=$(command -v chromium || command -v chromium-browser || command -v google-chrome)
[ -n "$CHROME" ] || { echo "no chromium on PATH"; exit 1; }
command -v pdfcrop >/dev/null || { echo "no pdfcrop (texlive-extra-utils)"; exit 1; }

# A throwaway profile dir keeps chromium from touching the real one.
PROFILE=$(mktemp -d)
trap 'rm -rf "$PROFILE"' EXIT
FAIL=0

render () {
  local name="${1%.html}"
  local src="$name.html"
  [ -f "$src" ] || { echo "  missing $src"; FAIL=1; return; }
  local raw="$name.raw.pdf"

  "$CHROME" --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
    --user-data-dir="$PROFILE" \
    --print-to-pdf="$raw" "file://$PWD/$src" >/dev/null 2>&1

  [ -f "$raw" ] || { echo "  FAILED to render $src"; FAIL=1; return; }

  local pages
  pages=$(pdfinfo "$raw" 2>/dev/null | awk '/^Pages/{print $2}')
  if [ "${pages:-0}" != "1" ]; then
    echo "  WARNING $src produced $pages pages (content overflows @page); keeping page 1"
    # keep only the first page so the figure never carries a blank second page
    if command -v pdfseparate >/dev/null; then
      pdfseparate -f 1 -l 1 "$raw" "$name.p1.pdf" >/dev/null 2>&1 && mv "$name.p1.pdf" "$raw"
    fi
    FAIL=1
  fi

  pdfcrop --margins 2 "$raw" "$name.pdf" >/dev/null 2>&1
  rm -f "$raw"
  local sz
  sz=$(pdfinfo "$name.pdf" 2>/dev/null | awk '/^Page size/{print $3"x"$5" pt"}')
  echo "  $name.pdf   ($sz)"
}

if [ $# -ge 1 ]; then
  render "$1"
else
  shopt -s nullglob
  for f in fig*.html; do echo "rendering $f"; render "$f"; done
fi

[ "$FAIL" -eq 0 ] && echo "OK: all figures single-page." || echo "ATTENTION: see warnings above."
exit $FAIL
