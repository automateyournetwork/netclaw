#!/usr/bin/env bash
# Render the NCFED Internet-Draft: kramdown-rfc markdown -> RFCXML v3 + text.
#
# Output (canonical, committed):
#   rendered/${DRAFT}.xml   — RFCXML v3, the Datatracker submission file
#   rendered/${DRAFT}.txt   — text render of the same content
#
# kdrfc's v2 intermediates land next to the source; they are removed after a
# successful render so the only draft files in this directory stay the .md.
set -euo pipefail
cd "$(dirname "$0")"

DRAFT="draft-capobianco-ncfed-00"

# The apt ruby3.0 that /usr/local/bin/kdrfc's shebang points at was removed by
# the 26.04 upgrade; the working gem lives in the user install for ruby3.3.
GEM_BIN="$HOME/.local/share/gem/ruby/3.3.0/bin"
[ -x "$GEM_BIN/kdrfc" ] && export PATH="$GEM_BIN:$PATH"
command -v kdrfc >/dev/null || { echo "kdrfc not found — gem install --user-install kramdown-rfc" >&2; exit 1; }
command -v xml2rfc >/dev/null || { echo "xml2rfc not found — pip install xml2rfc" >&2; exit 1; }

kdrfc "${DRAFT}.md"
xml2rfc --v2v3 "${DRAFT}.xml" -o "rendered/${DRAFT}.xml"

# ---- idnits cleanup (kramdown-rfc / xml2rfc --v2v3 artifacts) --------------
# xml2rfc's v2->v3 pass and kramdown-rfc's output introduce three things the
# IETF idnits v3 checker flags but that carry no content:
#   * <?line N?> source-position processing instructions (LINE_PI warning);
#   * empty <organization/> elements for authors with no affiliation
#     (EMPTY_AUTHOR_ORGANIZATION warning);
#   * an outer <references><name>References</name>...</references> wrapper around
#     the Normative/Informative sections, which makes references[0].name neither
#     Normative nor Informative (INVALID_REFERENCES_NAME error).
# Strip all three from the canonical XML so the submission is idnits-clean, then
# render the text from the cleaned XML so both artifacts match.
python3 - "rendered/${DRAFT}.xml" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
s = re.sub(r"[ \t]*<\?line \d+\?>\n?", "", s)          # drop <?line?> PIs
s = re.sub(r"[ \t]*<organization\s*/>\n?", "", s)      # drop empty <organization/>
s = re.sub(r"[ \t]*<organization>\s*</organization>\n?", "", s)
# Unwrap the combined-references container so the two sections are top-level
# siblings named "Normative References" / "Informative References". Remove the
# outer open tag + its <name>, then the matching close (always the LAST
# </references> in the document, since the wrapper encloses the other two).
s, n_open = re.subn(r'[ \t]*<references anchor="sec-combined-references">\n'
                    r'[ \t]*<name>References</name>\n', "", s)
assert n_open == 1, f"combined-references open tag: expected 1, removed {n_open}"
idx = s.rfind("</references>")
assert idx != -1, "no </references> close tag found"
line_start = s.rfind("\n", 0, idx) + 1
line_end = s.find("\n", idx) + 1
s = s[:line_start] + s[line_end:]
open(p, "w", encoding="utf-8").write(s)
print("idnits cleanup applied")
PY

xml2rfc "rendered/${DRAFT}.xml" --text -o "rendered/${DRAFT}.txt"
rm -f "${DRAFT}.xml" "${DRAFT}.txt"

echo ""
echo "Rendered: rendered/${DRAFT}.xml (submit this) + rendered/${DRAFT}.txt"
