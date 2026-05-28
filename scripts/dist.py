"""Update formula/drummer.rb with the SHA256 of the latest wheel in dist/."""

import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DIST_DIR = REPO_ROOT / "dist"
FORMULA = REPO_ROOT / "formula" / "drummer.rb"
_SHA_RE = re.compile(r'(\s*sha256 ")[^"]*(")')


def main() -> None:
    wheels = sorted(DIST_DIR.glob("drummer-*.whl"))
    if not wheels:
        print("No wheel found in dist/. Run 'hatch build' first.", file=sys.stderr)
        sys.exit(1)

    wheel = wheels[-1]
    sha256 = hashlib.sha256(wheel.read_bytes()).hexdigest()

    formula_text = FORMULA.read_text()
    updated, n_subs = _SHA_RE.subn(rf"\g<1>{sha256}\g<2>", formula_text, count=1)
    if n_subs == 0:
        print("Warning: sha256 line not found in formula — no changes made.", file=sys.stderr)
        sys.exit(1)

    FORMULA.write_text(updated)

    print(f"Wheel:   {wheel.name}")
    print(f"SHA256:  {sha256}")
    print("Formula: formula/drummer.rb updated")
    print()
    print("Release checklist:")
    print("  [ ] Tag a release: git tag v<version> && git push origin v<version>")
    print("  [ ] Upload dist/*.whl as a GitHub release asset")
    print("  [ ] Update formula url to the release asset URL")
    print("  [ ] Copy formula/drummer.rb -> homebrew-drummer/Formula/drummer.rb")
    print("  [ ] Push tap repo")


if __name__ == "__main__":
    main()
