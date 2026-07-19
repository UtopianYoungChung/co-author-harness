# Co-Author Harness containers

**Status:** Target container architecture. `Plugin Runtime Bundle`, `Validation
Toolchain`, and `Verification and Release Pipeline` exist today. The repair
programme changes their contracts and connections rather than pretending they
are new deployable services.

```mermaid
C4Container
  title Co-Author Harness - Container Architecture

  Person(researcher, "Researcher / Maintainer", "Sole normative approval authority")

  Container_Ext(host, "Host Runtime", "Claude Code / Codex", "Loads and executes plugin surfaces")
  ContainerDb_Ext(project, "Project Workspace", "Files and JSON", "Project state and evidence")
  System_Ext(knowledge, "Knowledge Services", "Advisor, Wiki, graph, and source verifiers")
  System_Ext(gitRemote, "Git Remote and CI", "Protects main and runs shipment gates")

  System_Boundary(harness, "Co-Author Harness") {
    Container(plugin, "Plugin Runtime Bundle", "Skills, agents, policies, hooks", "User-facing orchestration and capabilities")
    Container(gates, "Validation Toolchain", "Python CLIs", "Receipts, preflight, lifecycle, evidence, and terminal gates")
    Container(release, "Verification and Release Pipeline", "Python and Bash", "Runs fixtures and builds provenance-bound packages")
    ContainerDb(distribution, "Immutable Distribution Artifact", ".plugin archive", "Versioned package with embedded provenance")
  }

  Rel(researcher, host, "Invokes work and approves checkpoints")
  Rel(host, plugin, "Loads commands, skills, agents, and hooks")
  Rel(plugin, gates, "Requests deterministic authorization")
  Rel(plugin, project, "Reads and writes role-authorized paths")
  Rel(gates, project, "Validates state, receipts, and evidence")
  Rel(plugin, knowledge, "Invokes capability-gated adapters")
  Rel(gitRemote, release, "Runs against exact committed main SHA")
  Rel(release, distribution, "Builds and records provenance")
  Rel(host, distribution, "Installs and verifies version plus hash")
```

## Deployment invariant

Version equality is necessary but insufficient. An installed host copy must
also match the immutable distribution artifact's provenance and content hash.
