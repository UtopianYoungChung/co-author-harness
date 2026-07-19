# Lifecycle component architecture

**Status:** Target component architecture. Components marked **planned** are
not active capabilities until `references/capabilities.yaml` says otherwise.

```mermaid
C4Component
  title Co-Author Harness - Lifecycle Components

  Container(validation, "Validation Toolchain", "Python", "Deterministic gate authority")
  ContainerDb(project, "Project Workspace", "Files and JSON", "State and evidence")
  System_Ext(knowledge, "Knowledge Services", "External capability providers")

  Container_Boundary(plugin, "Plugin Runtime Bundle") {
    Component(registry, "Capability Registry (WP0)", "Versioned YAML contract", "Declares status, entrypoint, ownership, outputs, and tests")
    Component(facade, "Workflow Facade (current, degraded)", "Skills and commands", "Exposes draft, iterate, finalize, and bounded review services")
    Component(planner, "Lifecycle Coordinator (current, degraded)", "Planner plus canonical FSM", "Owns project-state transitions")
    Component(dispatcher, "Role Dispatcher", "Agent contracts", "Dispatches Generator, Evaluator, and Reflector")
    Component(policy, "Contract Kernel (WP0 foundation)", "Schemas and policy resolvers", "Resolves lifecycle, role, artifact, and grounding rules")
    Component(transaction, "Transaction Manager (current, degraded)", "Receipt protocol", "Prepares, emits, verifies, dispatches, and consumes")
    Component(enforcement, "Host Enforcement Adapter (current, degraded)", "Hooks and scoped authorization", "Blocks bypass attempts as defense in depth")
    Component(evidence, "Evidence Binder (current, degraded)", "F6-F9, G4, milestone bindings", "Connects claims to exact artifacts and rounds")
    Component(centroid, "Centroid Service (planned)", "Runner and schemas", "Performs bounded register analysis and proposals")
    Component(connectors, "Knowledge Adapters (partial)", "Graph, Wiki, advisor, and source adapters", "Expose provider-aware capability contracts")
  }

  Rel(facade, registry, "Discovers callable capabilities")
  Rel(facade, planner, "Requests governed work")
  Rel(planner, policy, "Resolves authoritative transition rules")
  Rel(planner, transaction, "Starts one dispatch transaction")
  Rel(transaction, validation, "Runs receipt and preflight gates")
  Rel(transaction, dispatcher, "Dispatches after successful preflight")
  Rel(dispatcher, project, "Writes role-authorized artifacts")
  Rel(planner, evidence, "Binds accepted lifecycle evidence")
  Rel(evidence, validation, "Requests evidence and terminal validation")
  Rel(enforcement, validation, "Checks host actions")
  Rel(facade, centroid, "Invokes only when registry status permits")
  Rel(planner, connectors, "Calls configured external capabilities")
  Rel(connectors, knowledge, "Queries or requests governed mutation")
```

## Required dependency direction

`capability registry -> workflow facade -> lifecycle coordinator -> contract
kernel -> transaction manager -> deterministic gates -> role-owned artifact ->
evidence binding -> human approval -> atomic Planner state transition`.

No receipt-bound input may change between receipt emission and dispatch.
