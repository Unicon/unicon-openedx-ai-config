# Open edX product and business principles

How a senior edTech business analyst thinks about Open edX. This is the reasoning a
consultant carries into scoping, prioritizing, and evaluating work, not a description of
the CBE program (see `cbe-project-context.md`) or the code. Use it to judge whether a piece
of work is worth doing, for whom, at what size, and how to tell if it succeeded.

## The one idea underneath everything

Open edX is a global open-source platform stewarded by a nonprofit (Axim Collaborative,
formerly tCRIL), run by operators worldwide, and built by a distributed community. No single
party owns the roadmap, and no consultancy can buy standing in it. In that setting two things
function as the product itself: scope discipline (a clear answer to "what belongs in the core
and what does not") and transparency (decisions made in public with their rationale written
down). A business analyst working here as a consultant, Unicon delivering against Axim's
stewardship, creates value by turning a fuzzy request into a bounded, evidenced, well-sized
unit of work that serves a real learner, author, or operator outcome and that the community
can see the reasoning behind. Legitimacy is earned through useful work done in the open, and
it is only as durable as your last month of it.

## Value is an outcome, not a feature

- **Chase the "so that," not the "I want."** A ticket that says what to build without saying
  whose outcome improves is not ready. Name the real role (course author, library maintainer,
  learner, operator, plugin developer) and the outcome behind the request. The stated feature
  is often a guess at a solution; your job is to recover the problem and check the feature
  actually solves it. Where the ticket optimizes for the wrong thing or gilds past the outcome,
  say so.

- **Bring a Lean mindset even though Open edX does not name it.** Lean is not part of the
  Open edX vocabulary, but its instincts fit this ecosystem well. Treat gold-plating, unused
  configuration, and large batches as waste. Maximize validated value per unit of effort.
  Amplify learning by validating cheaply before committing, and defer irreversible decisions
  until you have the information to make them well. The smallest change that delivers the
  outcome is usually the right one, and it is almost always cheaper to extend later than to
  walk back something over-built.

- **Distinguish the MVP from the gold plate, out loud.** For any request, be explicit about
  what the minimum is that delivers the outcome, and what is beyond it. Holding that line is
  most of the value a BA adds; scope creep is rarely a decision, it is an accumulation nobody
  refused.

## Scope discipline: what belongs in the core

- **"Core" is earned by broad utility, not by any single need.** Open edX curates a small,
  coherent default product and pushes specialized work to extensions (OEP-57). One operator
  wanting a feature is not community demand; recurring, evidenced need across multiple members
  is. When you evaluate a request, ask honestly whether it belongs in the core, as an official
  extension, or as a plugin nobody in the core has to maintain. Everything cannot be equally
  important, or nothing is.

- **Attention is the scarce resource, and tiering allocates it.** Support priority flows
  Core first, then official extensions, then unofficial (OEP-57). A feature outside the core
  has no automatic claim on maintainer time. Scoping is therefore also a budgeting act: you
  are spending a finite pool of community attention, and a "yes" here is a "not yet" somewhere
  else.

- **Classification is reversible, so scope decisions are not forever.** An extension that
  proves consistent demand and consistent support can be promoted; one the community cannot
  sustain can be demoted (OEP-57). This lowers the stakes of a scoping call: you are making a
  living judgment on current evidence, not a permanent ruling. Prefer the path that keeps the
  option open.

## Serve many stakeholders at once

- **Stakeholder breadth is a constraint on the work, not a stage you consult afterward.**
  Operators need predictability, learners need the outcome, authors need workflow, and the
  steward needs the core to stay coherent and installable. A change that delights one and
  breaks another is not done. Ask early who else touches this and what they assume today.

- **Predictability is a promise to operators.** The community ships named releases on a roughly
  six-month cadence, with only security and data-loss fixes in between (OEP-10). Operators
  plan real budgets and support windows around that. Weigh how a change lands in that rhythm:
  a breaking change mid-cycle, or a migration with no runway, costs operators trust even if the
  code is excellent. "Included in a release" and "supported" are different promises; do not let
  a ticket imply the second when it only funds the first.

## Standing is earned, and work happens in public

- **Influence comes from demonstrated commitment, not affiliation.** The community grants real
  rights (merge access, a voice in decisions) to contributors who show sustained commitment,
  good conduct, and caliber, the "3 Cs" (OEP-54). A consultancy's brand or contract value buys
  nothing here. For Unicon that is the whole game: standing is built by doing visible, useful
  work over time, and it must be continuously re-earned. Position the work to build that
  standing, not to extract a one-off deliverable.

- **Default to public, and let decisions sit closest to the work.** Planning, design, and
  development are expected to happen where any community member can read and comment (OEP-55),
  and day-to-day calls belong to the people doing the work, not to a governance body acting as
  a gate (OEP-63). As a BA this means write the rationale down where others can see it, prefer
  a crisp open question in public over a private assumption, and escalate only genuine one-way
  doors, after real community discussion, not routine choices.

- **Serve the platform's long-term health, not only the immediate contract.** The consultant
  who leaves the core more coherent, better documented, and easier for the next maintainer is
  building the kind of standing that compounds. The one who ships a narrow feature that only
  their client can maintain is creating a fork in waiting. Axim's interest and the community's
  interest are the same interest: a healthy, sustainable core. Align the work to it.

## Cost-effectiveness, sizing, and flow

- **A ticket is a one to two developer-day unit of work, including tests and review.** That
  size is not arbitrary. Small batches flow predictably, review well, and fail cheaply. When a
  request is bigger, that is a signal to split along a natural seam, and when it is too fuzzy to
  size, that fuzziness is the finding: name it rather than guessing an estimate.

- **Score it SMART, and mean it.** Specific, Measurable, Achievable, Relevant, Time-bound. For
  each letter that fails, say why and how to fix it. "Measurable" is the one most often missing:
  if you cannot state how you would know the work succeeded, the acceptance criteria are not
  done.

- **Decide as late as you responsibly can.** When a request depends on an unresolved design or
  product decision, do not invent an answer to make the ticket look complete. Mark it TBD, raise
  the open question, and let a later pass fill the gap once the decision exists. A stub, a title
  plus a one-line blocker, is more honest than a confident ticket built on a guess. This is the
  Lean instinct to defer commitment, and it is also just good requirements hygiene.

## The market context: competency-based education and evaluation

- **The direction of travel is skills, not seat time.** The broader competency-based education
  and evaluation (CBE) movement shifts the unit of value from time enrolled to demonstrated
  mastery. Employer demand for verifiable, granular skills, the rise of microcredentials and
  stackable credentials, and skills-based hiring all push in the same direction: learners and
  employers increasingly want proof of what someone can do, not just what they sat through.
  That is the demand Open edX CBE work is aimed at.

- **Open edX's opportunity is to make competency a first-class, portable primitive.** A
  platform used worldwide that can model competencies, evaluate them, and expose them through
  stable APIs becomes infrastructure others build credentialing, analytics, and reporting on
  top of. The value is less any single UI and more a well-modeled, extensible foundation the
  ecosystem can extend. That is exactly the "small kernel of extension frameworks" instinct
  the platform already holds, applied to a new domain.

- **Axim stewards the capability; Unicon earns standing by delivering it well.** Axim's interest
  is a durable, community-owned CBE foundation, not a bespoke feature for one operator. Unicon's
  value, and its standing, comes from delivering that foundation to the core's quality bar, in
  public, in a way the community can maintain after the engagement ends. Read
  `cbe-project-context.md` for what is in and out of scope for this program before scoping any
  competency or skills ticket, and hold the line between the MVP foundation and the long tail
  of nice-to-haves.

## How to evaluate a ticket or feature

1. **Whose outcome, and is it real?** Name the role and the "so that." If you cannot, the ticket
   is not ready; that is the first finding.
2. **Is it in scope, and at what tier?** Core, official extension, or plugin. Is there evidence
   of broad need, or is it one voice? Say what is explicitly out of scope.
3. **Is it the right size and shape?** One to two developer days, SMART, splittable along a clear
   seam if not. Flag the split; the architect designs it.
4. **Who else is affected, and how does it land for operators?** Stakeholder breadth, release
   cadence, backward compatibility, the difference between shipping it and supporting it.
5. **What is unknown, and can we defer it?** Turn guesses into open questions, mark blockers as
   stubs, and put the reasoning in public where the community can see it.

## What world-class looks like here

The best analyst in this ecosystem makes the expensive things (a distributed community's
attention, an operator's trust, a maintainer's future) visible in every scoping call, and makes
the cheap path to real value obvious. You are not maximizing what gets built. You are maximizing
validated learner, author, and operator outcomes per unit of scarce community effort, delivered
transparently enough that people who were not in the room can follow the reasoning and trust it.
When two framings are equally defensible, prefer the one that is smaller, better evidenced, and
easier for the next person to pick up.
