# Co-Author Harness system context

**Status:** Target architecture approved for the repair programme. The diagram
shows the intended system boundary; capability availability remains governed by
`references/capabilities.yaml` and must not be inferred from this diagram.

```mermaid
C4Context
  title Co-Author Harness - System Context

  Person(researcher, "Researcher / Maintainer", "Directs work and supplies binding approvals")

  System(harness, "Co-Author Harness", "Governed academic-writing and review lifecycle")
  SystemDb_Ext(project, "Research Project Workspace", "Project state, deliverables, evidence, and sources")
  System_Ext(claudeHost, "Claude Code Host", "Runs the plugin and independently audits repairs")
  System_Ext(codexHost, "Codex Host", "Implements and verifies repairs")
  System_Ext(knowledge, "Knowledge Services", "Advisor, Wiki, graph, Zotero, and external verifiers")
  System_Ext(gitRelease, "Git, CI, and Distribution", "Verifies main and publishes immutable packages")

  Rel(researcher, codexHost, "Authorizes implementation and reviews results")
  Rel(researcher, claudeHost, "Requests independent review")
  Rel(codexHost, harness, "Repairs and tests")
  Rel(claudeHost, harness, "Loads and audits")
  Rel(harness, project, "Reads and writes governed artifacts", "Files and JSON")
  Rel(harness, knowledge, "Queries configured services", "Tool adapters")
  Rel(gitRelease, harness, "Tests, packages, and distributes committed source")
```

## Boundary rules

- The researcher is the sole normative approval authority.
- Codex and Claude are external maintainers, not product lifecycle roles.
- Source checkout, built archive, Claude installation, and Codex installation
  are distinct deployment instances.
- Project evidence and release evidence belong to different trust domains.
