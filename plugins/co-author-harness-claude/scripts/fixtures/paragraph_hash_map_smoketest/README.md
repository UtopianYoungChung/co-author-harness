# paragraph_hash_map smoketest (v0.8.0 P2.1c)

Minimal consumer layout: `minimal_project/manuscript/main.md` (three paragraphs).

Release gate (`scripts/release-gate.sh` Phase 0.69) runs `paragraph_hash_map.py --project-root minimal_project` twice and requires byte-identical stdout (hash determinism).
