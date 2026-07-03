# Open edX architecture principles

How a principal architect thinks about Open edX. This is not a description of the code
(see `architecture-overview.md` and `architecture-taxonomies-and-competencies.md` for
that) and not a rulebook. It is the reasoning underneath the rules: the values Open edX
consistently optimizes for, why, and how to carry them into work the existing docs do not
cover. Use it to make architecture judgments, not just to recall facts.

## The one idea underneath everything

In a large, long-lived, distributed system built by many independent teams, the dominant
cost is not construction. It is coordination and change over time. Every public API, event
schema, feature flag, and data column is a commitment to people who cannot read your source,
attend your standup, or redeploy on your schedule. So Open edX consistently pays higher
cost upfront, explicit boundaries, named contracts, deliberate identifiers, in exchange for
the freedom to change internals later without breaking neighbors. Two phrasings of the same
value recur across the OEPs: boundaries are worth more than convenience, and the cost of a
change is paid by everyone downstream. When a decision is hard, ask who pays for it later
and whether they consented. That question resolves most of them.

## Boundaries and contracts

- **A public API is a contract; internals are free.** Each app exposes one public surface
  (`api.py` per OEP-49) and everything cross-app goes through it. This is the dependency
  rule of clean architecture stated in Django terms: callers depend on a stable interface,
  never on your models or queries, so you can rewrite the inside without a ripple outside.
  Treat the boundary as the thing you protect and the internals as the thing you keep cheap
  to change. `.importlinter` enforces this mechanically; never loosen a rule to pass a build.

- **Do not leak your persistence layer across a boundary.** Return plain data objects, not
  querysets or ORM instances (OEP-49's `data.py` pattern). A queryset handed to a caller
  drags the database into unrelated code paths and couples them to your schema. A frozen
  value object cannot mutate under them. This is the anti-corruption layer of domain-driven
  design: the shape you expose is a deliberate choice, not an accident of your tables.

- **Dependencies point one way, and the arrow is load-bearing.** `openedx-core` never
  imports from `openedx-platform`; the applets inside `openedx_content` layer from a public
  `api` facade down to `publishing`, with peers forbidden from importing each other. One-way
  dependencies are what let a lower layer be extracted, versioned, and reasoned about on its
  own. A cycle is not a style problem; it fuses two things into one that can no longer move
  independently.

- **Version numbers and deprecation are how you talk to the future.** Semantic versioning
  (OEP-47) encodes a promise: a major bump means "this will break you," a patch means "this
  is safe." The DEPR process (OEP-21) gives breaking changes a runway, not a cutover:
  announce, wait, run old and new in parallel, then remove. Breaking a non-UNSTABLE API
  silently is not a shortcut. It just transfers the cost to every downstream consumer without
  their consent. Recommend the DEPR path; never edit a stable contract in place.

## Bounded contexts and modularity

- **The applets are bounded contexts; treat them as such.** Open edX does not brand itself
  domain-driven, but the applet pattern is DDD in practice: each is a cohesive slice of the
  domain with its own language and a guarded boundary. Respect the language (a
  `PublishableEntity`, a `Container`, a `Draft` pointer mean specific things) and keep the
  model of one context from bleeding into another. When you feel the urge to reach past an
  applet's API into its internals, that urge is the boundary telling you the API is missing
  something. Fix the API, do not tunnel under it.

- **High cohesion, low coupling, decided by rate of change.** Things that change together
  belong together; things that change for different reasons and at different speeds belong
  apart. This is the real test behind "should this be a new applet, a new top-level app, or
  a new repo." Keeping top-level packages separate preserves the option to extract them
  later, and that option has value even when you never exercise it.

- **Prefer composition and configuration to inheritance and hardcoding.** Extend the core
  through related models and one-to-one links, not concrete subclassing, so the core stays
  introspectable without the plugin's code loaded. The stated ideal (OEP-57) is a small
  kernel that is mostly a collection of extension frameworks; baked-in features are named as
  debt, not design. When you add behavior, ask whether it belongs in the core or hangs off a
  seam the core already offers.

## Extensibility as a first-class value

- **Design the seam before the extension exists.** Retrofitting extension points under
  pressure is far harder than anticipating them (OEP-50). The alternative to a good seam is
  a community that forks the core, and forks are divergent, unmigratable, and unsupported.
  A well-placed hook is a gift to people you will never meet.

- **Know the difference between a notification and a transformation.** Events (Django
  signals) are fire-and-forget: the producer does not know or care who listens. Filters are
  ordered pipelines: each stage transforms the previous stage's output, so ordering is part
  of the contract (OEP-50). Conflating them produces subtle, hard-to-debug behavior. Pick the
  one whose coupling matches the intent.

- **A hook signature is a public contract too.** Once plugins depend on it, changing it
  silently breaks every one of them at once, with no local signal to their authors. Extend
  hook contracts the same careful way you extend any API.

- **Keep the framework thin; push policy to the caller.** OEP-50 deliberately refused to bake
  Celery into the hooks framework even though async dispatch is recommended, because a central
  hard dependency creates serialization traps and couples everyone to one strategy. A good
  framework decides as little as it can and lets callers choose.

## Distributed-systems discipline

- **Decouple services with asynchronous events, not synchronous calls.** Pub/sub over the
  event bus (OEP-52) removes blocking RPC dependencies and lets producers and consumers evolve
  independently. This is the structural move from a monolith to a system that can scale and
  fail in parts rather than all at once.

- **Abstract the transport, own the schema.** The event bus can swap Kafka for Redis without
  touching producers or consumers; what is locked is the event schema, not the wire. Put your
  stability at the contract boundary, not in the infrastructure, so you can replace the
  plumbing without a migration of everyone else.

- **Treat eventual consistency as a design constraint, not an edge case.** In an event-driven
  system, "the data will be right in a moment" is the normal state, not a bug to paper over
  (OEP-52). Accept it at design time: idempotent consumers, ordering assumptions made explicit,
  reconciliation where it matters.

- **Decouple release from deployment, and shrink the blast radius of change.** Ship code dark
  behind a toggle and turn it on separately (OEP-17), so deploying bytes and changing behavior
  are different acts on different timelines. Canary releases, beta cohorts, and kill switches
  are one pattern: reduce mean time to recovery by exposing change to few before many. And a
  toggle is temporary by design; a flag that can never be removed is debt wearing the costume
  of flexibility. Give it an expiry.

## Data is the most expensive thing to change

- **Design the schema for the people who read it later, not just today's write path.**
  Analytics, BI, and migration engineers are first-class stakeholders in a data model (OEP-38).
  A badly named column costs an hour to define and many hours downstream. Get it right before
  the table has rows, because after that every change is a migration with a backfill.

- **Separate the internal key from the external reference.** Numeric primary keys are for
  performance and stay inside; UUIDs are stable external references that cross service
  boundaries; the client-meaningful `key` is its own thing (see the identifier-conventions
  ADR and `id_fields.py`). Never join across services on mutable fields like email or
  username. Picking the right identifier for a job is a boundary decision, not a detail.

## How to think: a short decision framework

1. **Recover the real requirement, then find the smallest correct change.** No unrequested
   abstraction, flexibility, or error handling for impossible cases. Reuse before rebuild:
   existing helpers and public APIs, then the stdlib, then Django or DRF, then a dependency,
   before new code. Complexity has to earn its place.
2. **Place it by rate of change and by contract.** Which layer, which applet, which side of a
   public API. If the placement forces a new cross-layer import, that is a design signal, not
   a linter annoyance.
3. **Name what the change commits you to.** Public API impact and whether it needs DEPR, a new
   model and its PII annotations, a migration, an event or filter contract, backward
   compatibility. Surface these at design time so they are scoped in, not discovered mid-build.
4. **Generate genuine alternatives before recommending one.** At least three real options with
   their tradeoffs (complexity, risk, reuse, migration cost, blast radius), then one
   recommendation that is the simplest correct design, justified against the rejected ones.
5. **Write the decision down when it is broad and durable.** A choice that many people will
   live with, and that is expensive to reverse, warrants an ADR in proposed status. The
   artifact carries the "why" to contributors who were not in the room. Recommend the ADR;
   do not silently make the call for them.

## What world-class looks like here

Elegant is not clever. In this codebase elegant means small, cohesive, and boring at the
boundary: a public API a stranger can use correctly on the first read, internals free to
change, no coupling that was not chosen on purpose. You are not optimizing your own throughput.
You are optimizing the whole community's ability to keep changing this system for years without
stepping on each other. When two designs are equally correct, prefer the one that is easier to
delete, easier to explain, and cheaper for the next person to change.
