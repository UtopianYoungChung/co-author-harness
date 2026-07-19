# Codex-Claude supervision flow

**Status:** Ratified by the researcher on 2026-07-19 and binding for this repair
programme through `docs/repair/mutual-supervision.md`. It governs package
repair, not academic manuscript production.

```mermaid
C4Dynamic
  title Co-Author Harness - Repair Work-Package Supervision

  Person(user, "Researcher / Authority", "Approves normative decisions")
  System_Ext(codex, "Codex", "Sole repair implementer")
  System_Ext(claude, "Claude", "Independent read-only auditor")
  System_Ext(gates, "Deterministic Gates", "Mechanical conformance authority")
  SystemDb_Ext(main, "Git main", "Only permitted committed history")

  Rel(user, codex, "1. Approves work-package scope")
  Rel(codex, claude, "2. Sends baseline and acceptance packet")
  Rel(claude, codex, "3. Returns adversarial pre-review")
  Rel(codex, gates, "4. Demonstrates failing regression")
  Rel(codex, gates, "5. Runs repaired targeted and root gates")
  Rel(codex, claude, "6. Sends exact diff and evidence")
  Rel(claude, codex, "7. Returns grounded findings")
  Rel(codex, main, "8. Commits test plus repair only when green")
  Rel(claude, main, "9. Audits exact committed SHA")
  Rel(codex, user, "10. Reports evidence and open decisions")
```

Mechanical disputes are decided by a minimal synthetic fixture authored by the
challenger and run unchanged by the implementer. Contract conflicts return to
the researcher; neither agent silently chooses a preferred authority.
