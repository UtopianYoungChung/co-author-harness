# Cursor manifest retirement

**Decision:** `.cursor-plugin/plugin.json` is retired and must not exist in a
release candidate.

The file was an unmanaged host-specific metadata copy. It asserted package
identity, description, keywords, license, and a current version independently
of `.claude-plugin/plugin.json`, contradicting the repository's single version
authority. No release or loader gate consumed it, so its stale value could sit
beside a newer package without either plane detecting the disagreement.

Cursor remains a supported source-checkout editor surface; it reads the
repository instructions and package files directly. That use does not require
a second plugin manifest. Reintroducing `.cursor-plugin/plugin.json` would need
an explicit loader contract, mechanical parity with the authoritative manifest,
and a release-gated consumer. Until then, `scripts/version-check.py` refuses the
retired path.
