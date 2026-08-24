import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_prolog_rlm_input_and_lock_use_the_same_exact_revision():
    flake = (ROOT / "flake.nix").read_text(encoding="utf-8")
    match = re.search(
        r'prolog-rlm\.url\s*=\s*"github:lost-rob0t/prolog-rlm/([0-9a-f]{40})";',
        flake,
    )
    assert match is not None, "Prolog-RLM flake input must pin an exact revision"
    expected_revision = match.group(1)

    lock = json.loads((ROOT / "flake.lock").read_text(encoding="utf-8"))
    node_name = lock["nodes"]["root"]["inputs"]["prolog-rlm"]
    prolog_rlm = lock["nodes"][node_name]

    assert prolog_rlm["original"] == {
        "owner": "lost-rob0t",
        "repo": "prolog-rlm",
        "rev": expected_revision,
        "type": "github",
    }
    assert prolog_rlm["locked"]["rev"] == expected_revision
