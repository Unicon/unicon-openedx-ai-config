# openedx/openedx-core issue #672: [FE] Create & View Competency Criteria

State: OPEN. updated_at: 2026-09-21T19:34:32Z

---

**Blocked by:** \#665 (the create-criterion endpoint), gated by \#666 (the dominance check); \#681 (the endpoint that returns a competency's groups and criteria); and \#773 (the endpoint for the platform's default competency rule profile).

## User Story

- As a course author, I want to see what a competency is already earned by across the courses I have access to, as soon as I select it, in order to start from what already exists instead of guessing.  
- As a course author, I want to select a gradable subsection in the content panel and have it added to the rule box that is in focus, in order to define what a learner must complete, and at what score, to demonstrate this competency.  
- As a course author, I want to click a bottom-tier group to put it in focus, in order to choose which combination of content my next selections count toward when a competency has more than one.  
- As a course author, I want to click a rule box inside that group to put it in focus, in order to choose the score my next selections are measured against when a group holds more than one rule.  
- As a course author, I want the associations panel to move focus to a course's own bottom-tier group and rule box when I expand that course in the content panel, in order to keep working in the content panel instead of stopping to find and click the matching group first.  
- As a course author, I want selecting a subsection from a course that has no groups yet to build the group structure for me, in order to add content from a new course without assembling the hierarchy by hand.  
- As a course author, I want to see which subsections this competency already uses, in order to avoid re-adding content I have already associated.

[Figma Design](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=1885-45211&t=ORazFlejYyhm4dqw-1)

<img width="1423" height="1031" alt="Image" src="https://github.com/user-attachments/assets/053e9ad7-5649-4709-956f-131095aae454" />

## Acceptance Criteria

```
Scenario: Selecting a competency shows what it is earned by in the courses I can see
  Given a competency already has associations in one or more courses
  And the content-search lookup returns those courses for me
  When I select that competency
  Then the associations panel shows a course-level group for each of those courses, with every bottom-tier group, rule box, and criterion beneath it
  And each bottom-tier group states in readable words whether it requires any one or all of the rule boxes inside it
  And each rule box shows the score it requires and the content already associated with it

Scenario: A course-level group for a course I cannot see is not shown
  Given a competency has an association in a course that the content-search lookup does not return for me
  When I select that competency
  Then no course-level group is shown for that course, and nothing beneath it is shown
  And it is not shown with a missing, blank, or placeholder course name instead

Scenario: A course I can see but cannot write to offers no way to add content
  Given a competency has an association in a course I can see via content search but do not have studio write access to
  When I browse that course's subsections in the content panel
  Then subsections already associated with this competency are still marked as such
  And no subsection in that course offers a control to select it

Scenario: Selecting a competency that has no associations yet
  Given a competency has no associations
  When I select that competency
  Then the associations panel shows no course-level groups
  And it shows an empty-state message inviting me to make a content selection, with no group or rule box card shown

Scenario: A competency whose associations are all in courses I cannot see
  Given every association a competency has is in a course that the content-search lookup does not return for me
  When I select that competency
  Then the associations panel shows no course-level groups, the same as a competency that has no associations at all

Scenario: The competency's associations fail to load
  Given I select a competency
  When the associations panel's data fails to load
  Then I am shown an error in the panel
  And the panel does not look like the competency has no associations

Scenario: A bottom-tier group's combining choice and a rule box's score are shown but not editable here
  Given a competency has associations in a course I can see
  When I view a bottom-tier group and the rule boxes inside it
  Then I can read whether the group requires any one or all of its rule boxes, and what score each rule box requires
  And neither of those values offers a control to change it

Scenario: A rule box following the system default renders identically to one with an explicit override
  Given a rule box whose score comes from the system default profile, and another rule box whose score is an explicit override, both currently showing the same value
  When I view both rule boxes
  Then nothing on the page distinguishes one from the other
  And the only way to tell them apart is to inspect the underlying data directly, for example the criterion's fields in the network response, not anything rendered on the page

Scenario: Sibling bottom-tier groups in one course show how they combine
  Given a course-level group holds more than one bottom-tier group
  When I view that course's section
  Then a connector is shown between each adjacent pair of those bottom-tier groups
  And every one of those connectors shows the same combining choice, because it is one choice for the whole course rather than a separate choice per pair

Scenario: A course section collapses and expands independently of the others
  Given the associations panel shows two or more course-level groups
  When I collapse one of them
  Then its bottom-tier groups, rule boxes, and chips are hidden, while its header stays visible
  And every other course-level group's expanded or collapsed state is unaffected
  When I expand it again
  Then its content is shown exactly as it was before I collapsed it

Scenario: Add a subsection to the rule box in focus
  Given a bottom-tier group is in focus in the associations panel, and a rule box within it is in focus
  And the course that group belongs to is expanded in the content panel
  When I select a gradable subsection in that course
  Then that subsection is added to the bottom-tier group in focus as a criterion, carrying the rule of the rule box in focus
  And it appears as a chip in that rule box

Scenario: Put a different bottom-tier group in focus
  Given the competency I am editing has more than one bottom-tier group
  When I click one of them
  Then that group is in focus and is visually distinguished from the others
  And no other bottom-tier group is distinguished at the same time
  And subsections I select afterwards are added to it

Scenario: Put a different rule box in focus
  Given the bottom-tier group in focus holds more than one rule box
  When I click one of them
  Then that rule box is in focus and is visually distinguished from the others in that group
  And the bottom-tier group containing it is distinguished from the other bottom-tier groups
  And no other rule box is distinguished at the same time
  And subsections I select afterwards carry that rule box's rule

Scenario: A single bottom-tier group is in focus without clicking
  Given the competency I am editing has exactly one bottom-tier group across the courses I can see
  When I view the associations panel
  Then that group is in focus
  And I can select a gradable subsection without clicking to put the group in focus first

Scenario: A single rule box is in focus without clicking
  Given the bottom-tier group in focus holds exactly one rule box
  When I view that group
  Then that rule box is in focus
  And I can select a gradable subsection without clicking to put the rule box in focus first

Scenario: Expanding a course that already has groups moves focus to that course
  Given a bottom-tier group belonging to some other course is in focus
  And the course I am about to expand already has one or more bottom-tier groups for this competency
  When I expand that course in the content panel
  Then focus moves to one of that course's own bottom-tier groups, and to one of the rule boxes within that group
  And both are visible in the associations panel without further scrolling or clicking
  And expanding the same course again, with the same groups and rule boxes present, puts the same group and the same rule box in focus

Scenario: Add a subsection after focus has moved to the expanded course
  Given I have expanded a course that already has bottom-tier groups for this competency, whether one or several, each holding one or more rule boxes with any number of existing criteria
  And focus has moved to one of that course's bottom-tier groups and to a rule box within it
  When I select a gradable subsection from that course
  Then that subsection is added to the bottom-tier group in focus, carrying the rule of the rule box in focus
  And no additional group or rule box is created

Scenario: Expanding a course that has no groups leaves focus where it is
  Given a bottom-tier group and a rule box within it are in focus
  And the course I am about to expand has no bottom-tier group for this competency
  When I expand that course in the content panel
  Then focus stays on the group and rule box it was already on

Scenario: Add a subsection from a course that has no groups yet
  Given I have expanded a course that has no groups for this competency yet
  When I select a gradable subsection in that course
  Then a course-level group headed with that course's name appears in the associations panel, containing one new bottom-tier group with a single rule box
  And that rule box shows the system default rule, because no rule has been set for it
  And the selected subsection appears in that rule box as its only chip
  And the new bottom-tier group and its rule box are in focus and visible without further scrolling or clicking

Scenario: Subsections this competency already uses are marked
  Given a gradable subsection is already a criterion under the competency I am editing, in any of its groups or rule boxes
  When I browse to that subsection in the content panel
  Then it is visibly marked as already associated, distinct from subsections that are not

Scenario: Selecting an already-associated subsection does not create a duplicate
  Given a gradable subsection is already a criterion under the competency I am editing
  When I select that subsection again
  Then no second criterion is created for it
  And I can tell from the panel that it is already associated with this competency, rather than seeing an unexplained failure

Scenario: A rule box with no content yet
  Given a rule box has no criteria
  When I view it in the associations panel
  Then it shows an empty state indicating that no content has been selected into it yet

Scenario: The association cannot be created
  Given a bottom-tier group and a rule box within it are in focus
  When I select a gradable subsection and the system cannot create the association, including because it would break a competency dominance rule
  Then no chip appears in that rule box
  And I am shown an error telling me the content could not be associated
```

## Description

The page has two panels. The associations panel at the top, labeled "Competency Criteria Associations," shows how the selected competency is currently earned. The content panel below it, labeled "Courses & Content," lists courses as independently expandable nodes; expanding one reveals its gradable subsections.

Associations are displayed in four levels. A course-level group, headed "From within `<Course Name>` ...," holds everything drawn from one course; a course has at most one course-level group per competency. Inside it are one or more bottom-tier groups, each rendered as a "By completing \[any/all\] of the following" bracket, with a connector between each adjacent pair when a course has more than one. Inside a bottom-tier group are one or more rule boxes, each a row reading "With a score of X% or higher ...". Inside a rule box are the criteria, one chip per associated subsection. This ticket, \#671, and \#671's sibling ticket use "bottom-tier group" and "rule box" throughout rather than the signed-off design's own terms; see Context for the one place those terms cause a naming quirk worth knowing about.

Only three of those four levels are stored. A rule box is a display grouping, not a backend entity: it is the set of criteria in one bottom-tier group that share the same rule, so a single group can show several rule boxes at different scores, each holding one or more chips. Focus applies at two levels: exactly one bottom-tier group is in focus, and within it exactly one rule box. Together they determine where the next selected subsection lands and what score it is measured at.

Everything a persisted group or rule box displays is read-only here. See Technical Details for what is owned elsewhere.

What an author sees is bounded by their content-search access. The panel resolves course and subsection display names through content search, which the platform filters per user: global staff get everything, a narrower author gets only courses where they hold org-level or course-level access. A course-level group whose course that lookup does not return is not displayed at all, rather than displayed with a name the panel cannot resolve. For this page's expected user that usually means seeing everything, but it is not guaranteed. Being able to see a course-level group is separate from being able to add to it: the taxonomy governing this competency can be unavailable to that course's org, or the author's role can be one of the newer read-only authoring roles, either of which fails the `oel_tagging.can_tag_object` composite \#665 already checks. See Technical Details for how the select control and the already-associated marking account for both.

When focus moves automatically to a course's last bottom-tier group and the last rule box within it, those are default targets, not computed best matches for what the author intended. The author redirects focus by clicking a different group or a different rule box.

## Technical Details

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking, not to bind them.
### In short

- **Fetching is driven by the query key, not by an effect.** The competency's tag id is part of the cache key, so selecting a different competency swaps the data on its own. Do not watch the selection and call `refetch` by hand; that double-fetches and flashes the previous competency's data. Before any competency is selected the query is switched off rather than fired with a missing id.
- **Four panel states, not two.** Still loading, failed to load, loaded with nothing, and loaded with content. A failed load must not look like an empty panel, or the author concludes the competency is unused and starts adding content that is already there. "Loaded with nothing" renders a plain message, not a placeholder card: a not-yet-saved card only ever appears inside a course section that already exists, and a competency with no course-level groups has none.
- **Collapsing a course section is display only.** It does not clear or move focus; it just stops rendering whatever was focused there until the section is expanded again, the same graceful degradation the rule box list tolerates when its focused rule key matches nothing rendered.
- **The stored course name on the groups payload is deliberately unused.** It was captured when the group was created and does not follow a later course rename. Both course and subsection names come from the content search lookup, which the platform scopes per user, and that one lookup therefore also decides what renders: a course it does not return is not shown at all, rather than shown with a name the panel cannot resolve. No course section can be drawn until it comes back.
- **The fetch is unfiltered; only the display is scoped.** \#681 returns everything associated with the competency across the instance. A subsection belongs to exactly one course, so if a subsection is browsable at all then its course is visible and so is any existing association for it. There is no hidden duplicate to protect against, which is why the already-associated set and the duplicate guard are built from the one displayed view rather than a second fetch.
- **Focus is one value with two parts, written whole.** A rule box only means anything inside a particular group, so the two are stored as a pair and every action writes both parts at once. Written separately, the page can briefly hold a group belonging to one course together with a rule box that exists only in another, and the next selection lands somewhere the author did not intend. Both parts start unset, which is the state a competency with no visible associations stays in, and no focus write in this ticket leaves a part unset again. \#671 gives an unset part a second meaning and supplies its own writers; nothing here needs a branch for that, but nothing here may crash on it either.
- **Focus is written by actions, never recomputed from the page.** Four things write it here: clicking a group, clicking a rule box, expanding a course, and a create call returning; \#671 adds two more. A value recomputed on every render re-runs whenever any input changes and would silently override the author's click the next time unrelated state moved. The initial write is likewise a one-time write rather than a formula.
- **A rule box's identity is the rule itself.** It is not stored, so the backend can hand out no identifier for it, and a browser-generated one would differ on every refetch and lose focus. Identity also has to stay separate from order: order derives from the lowest criterion `id` in the box, which is recomputed from the current criteria on every request and points at a different box the moment its lowest-numbered criterion is removed.
- **One derivation, used by both the renderer and the focus resolver.** Which rule boxes exist, what order they appear in, and which bottom-tier group counts as "the last" in a course each live in a single helper that both callers use. Worked out separately, focus could point at a box that is not the one the author sees last, or at one that is not rendered at all, and nothing in review would catch the difference.
- **Always display the effective rule, never the stored override alone.** There is deliberately no visual distinction between a box showing the inherited default and one showing an override: no design draws one, and the backend actively erases the difference, converting an override back into a profile reference whenever it matches the applicable default. UI built on "does this criterion have an override" would flicker between two states for a value the author never changed.
- **The two operators these cards show come from two different stored rows.** A group card's any/all is the `logic_operator` on that group's own row; a connector's Or/And is the `logic_operator` on the shared course-level parent. Same column, different depth, different label set, so a helper that reads "the operator" without saying which row it reads will be wrong roughly half the time. Every connector under one course-level group reads that single value, so re-rendering after a change updates them all for free — do not give each connector its own copy, and do not write an effect that copies one into the others.
- **Read-only is the absence of a change handler, not a separate flag.** The combining-logic control and the score field each take an optional handler and render editable with it, plain text without it. This ticket never passes one. That leaves one question to answer at each call site instead of two values that can disagree.
- **Seeing a course and being allowed to add content to it are separate questions, and this ticket answers both.** Content search decides which courses appear on the page. Studio's permission-validation API settles whether the author may add to one: the page asks the backend, for every course it is currently showing, whether the user holds `courses.manage_tags`, and offers the select control only where the answer is yes. That action is the authorization-service counterpart of the `oel_tagging.can_tag_object` composite \#665's endpoint enforces server-side. A course the author can see but not write to still renders and is still marked when already associated, but offers nothing to click. The answer is exposed as `canEditCourse(courseId)` on this ticket's provider, so \#671 and the companion ticket read the same value instead of each fetching their own.
- **Creating an association is one request, not three.** The backend rejects groups that contain nothing, so a browser-driven "create the group, then fill it" sequence would fail on its first call. When focus is unset or on a group belonging to another course, the create call names no target group and no rule, and the backend reuses or creates that course's course-level group, adds a bottom-tier group under it, assigns the default rule, and puts the criterion inside.
<details>
<summary>Implementation specifics</summary>

- **Response fields are camelCase, request fields are not.** Every read hook in this MFE normalizes its response through `camelCaseObject` from `@edx/frontend-platform`, so anything read back from \#681 or from a create response is `competencyCriteriaGroupId`, `objectId`, `ruleTypeOverride`, and so on, never the API's own snake\_case. Request bodies still go out exactly as the API expects, in snake\_case. Apply this consistently rather than mixing the two conventions.  
- **Read hook.** `useCompetencyCriteriaGroups(tagId)` in `src/taxonomy/competency-management/data/apiHooks.ts`, a `useQuery` calling `getCompetencyCriteriaGroups(tagId)` in `data/api.ts`, hitting \#681. Gate it with `enabled: tagId !== undefined` so it never fires before a competency is selected.  
- **Default rule profile.** `useDefaultCompetencyRuleProfile()` in `data/apiHooks.ts`, calling `getDefaultCompetencyRuleProfile()` in `data/api.ts`, against \#773's endpoint. The provider runs it alongside the groups query. Its value is needed twice: to resolve a profile-referencing criterion into the rule that identifies its rule box, and to supply the rule a not-yet-saved rule box displays, which \#671 reads from the same hook.  
- **Display name lookup.** Add `useContentDisplayNames(courseIds, objectIds)` to `data/apiHooks.ts`, wrapping `useGetContentHits`, already a public export of `@src/search-manager`. Pass a filter naming exactly the ids being resolved, pass `attributesToRetrieve` limited to the identifier and the display name so the response stays small, and pass `false` for the `enabled` argument while the id list is empty so it does not fire before the groups have loaded. Do not read `search-manager`'s cache entry directly and do not ask \#670 to supply this data: the filter differs from \#670's own tree query, so this is a second, narrow request rather than a shared one, and that's the right trade for keeping the two panels uncoupled.  
- **Where the permission answer comes from.** Add `useCourseTaggingPermissions(courseIds: string[])` to `data/apiHooks.ts`. Build a `PermissionValidationQuery` whose keys are the course ids themselves and whose values are `{ action: COURSE_PERMISSIONS.MANAGE_TAGS, scope: courseId }`, de-duplicated and sorted so the React Query key is stable, then pass it to `useUserPermissions` from `@src/authz/data/apiHooks`. That hook sends the whole map as a single POST to `api/authz/v1/permissions/validate/me` and matches each answer back to its key by action and scope, so one request covers every course. `src/authz` has no `index.ts`; deep-import from `@src/authz/data/apiHooks` and `@src/authz/constants`, as `src/advanced-settings/AdvancedSettings.tsx` does. Do not create one.  
- **Add the action constant.** `COURSE_PERMISSIONS` in `src/authz/constants.ts` does not list the tagging action yet. Add `MANAGE_TAGS: 'courses.manage_tags'` to it. Do not add a factory to `src/authz/permissionHelpers.ts`: every factory there returns a fixed set of keys for a single course, and this page's query is a variable-length list of courses, so build the map inside the hook.  
- **Reading the rollout flag.** Take `enableAuthzCourseAuthoring` from `useWaffleFlags()` in `@src/data/apiHooks`, called with no course id so it returns the Studio-wide value. The `useWaffleFlags(courseId)` form is per-course, and this page spans many courses at once. `authz.enable_course_authoring` is a `CourseWaffleFlag` on the backend and can be overridden for an individual course, and this page will not see such an override. That is acceptable: the flag is a rollout switch, and \#665's endpoint remains authoritative either way.  
- **Loading semantics.** `useUserPermissions` disables itself with React Query's `skipToken` rather than the `enabled` option, so while it is disabled its own `isLoading` stays true forever. Compute this hook's loading flag as `isWaffleFlagsLoading || (isAuthzEnabled && courseIds.length > 0 && isPending)`, mirroring `useCourseUserPermissions` in `src/authz/hooks.ts`, and never read `isLoading` from `useUserPermissions` directly.  
- **What `canEditCourse(courseId)` returns.** False while the waffle flags are still loading, true when `enableAuthzCourseAuthoring` is false, and `data?.[courseId] ?? false` otherwise. Returning false while an answer is outstanding means a control appears once its course's answer arrives, rather than appearing and then vanishing.  
- **Which courses get asked about.** The provider passes the union of two sets it already holds: the course ids of the visible course-level groups, and the course ids the content panel has expanded, collected from the `notifyCourseExpanded` calls this ticket adds to \#670's per-course chevron. A subsection row only exists inside an expanded course, so no select control is reachable for a course outside that union. Expanding a course that has no group yet grows the list and costs one additional request, which React Query caches per distinct list.  
- **Where `canEditCourse` lives.** On the provider's context value, not in `utils.ts`. Its answer is fetched from the backend, so it cannot be a pure helper. \#671 and the companion ticket keep calling `canEditCourse(courseId)` unchanged; they read it from the provider context instead of importing it from `utils.ts`.  
- **What this gate does and does not cover.** In authorization mode `openedx-platform` treats holding `courses.manage_tags` on a course as sufficient to tag any object in it, dropping the taxonomy-availability half of the legacy composite; its own tagging view does the same. This gate therefore matches the platform's existing posture rather than introducing a new one. It is advisory: \#665's endpoint is the authority, and the page must still handle a 403 from it through the error surfacing this ticket already specifies.  
- **One map, two answers.** Build a single map from identifier to display name in `utils.ts` from the `useGetContentHits` response, joining courses on the string course key, matching \#681's `course_key` field against `useGetContentHits`'s `contextKey`, and subsections on `objectId`. Do not derive visibility separately from naming: a course with no entry in that map is simultaneously unnamed and out of scope, and computing the two against different structures is how they drift apart.  
- **Visible course-level groups.** Derive `visibleCourseGroups` once, as the course-level groups whose `course_key` is a key in that map, and use it for everything the panel renders and for the already-associated set below: what `CourseGroupList` iterates, whether the panel is empty, and each section's header text. Nothing that renders, and nothing that checks for an existing association, should read the raw \#681 payload's course-level groups directly.  
- **A course with no entry is hidden, with no fallback.** Do not fall back to the course name \#681 returns, and do not render the section with a blank or placeholder header. An unresolved course means the whole course-level group and everything under it is absent from the panel.  
- **A subsection with no entry keeps a neutral label.** Different from the course case on purpose. At the course level a missing entry is an access fact; inside a course the author can already see, a missing subsection means deleted content or index lag, not a permission boundary. Hiding the chip would make a rule box look emptier than it is, or empty when ADR 0002 guarantees a persisted group is not, and it would leave the author unable to see a criterion that still blocks them from adding that subsection again. Show a neutral label instead.  
- **Query key factory.** A `competencyQueryKeys` object, composed the same way as `taxonomyQueryKeys` in `src/taxonomy/data/apiHooks.ts`, with `all`, `competency(tagId)`, and `competencyCriteriaGroups(tagId)` built from each other, so invalidating one competency clears everything under it. Keep it in `data/apiHooks.ts` alongside the hooks, matching the taxonomy feature, unless \#670 already created a dedicated query-keys file.  
- **Do not keep previous data across competencies.** Leave React Query's default behavior, which drops to the loading state when the key changes. Keeping the previous result visible while a new one loads would render one competency's associations under another competency's heading.  
- **No cache configuration needed beyond the defaults.** The app-wide `QueryClient`'s standard stale time, plus the create mutation invalidating this query on success, are the whole cache story here; no manual refetch belongs anywhere in this feature.  
- **Panel states.** `CourseGroupList` owns all four states, and the loading state covers all three queries: the groups query, the default rule profile query, and the content-name lookup. The name lookup decides which course sections exist, so the panel cannot render its structure ahead of it; doing so would flash sections that are then removed once the lookup resolves. Loading renders a spinner; a failure of any of the three renders an inline alert inside the panel, not a toast, since a toast dismisses and leaves an empty-looking panel behind. The empty branch tests `visibleCourseGroups.length`, never the raw payload's group count, which is what makes "every association is in a course I cannot see" render identically to "this competency has no associations," without a second code path deciding it. A failed load must never render as either.  
- **Course section.** `CourseGroupSection` renders one visible course-level group: its "From within `<Course Name>`" header, named from the display-name map, and beneath it that course's bottom-tier group cards in the order produced by the shared ordering helper, with a `GroupConnector` between each adjacent pair.  
- **Collapse toggle.** `CourseGroupSection` holds its own `isCollapsed` boolean in local component state, defaulting to `false` (expanded), toggled by a chevron in its header. While collapsed, simply don't render that section's group cards at all. If the collapsed section holds the focused group or rule box, nothing renders as focused, the same graceful degradation `RuleBoxList` already relies on when its focused rule key matches nothing rendered; no cleanup or focus-reassignment logic is needed.  
- **Bottom-tier group card.** `CriteriaGroupBox` renders one group's "By completing \[any/all\] of the following" bracket, using `LogicOperatorSelect` bound to that group's own `logicOperator` with no change handler, plus its focused state and click handler, and `RuleBoxList` for its contents. It does not render any add control; \#671 adds those to this component.  
- **Rule box.** `RuleBox` takes the rule to display as a prop rather than reading it from a criterion, so the same component serves a persisted box (given the box's effective rule) and, once \#671 exists, a not-yet-saved box (given the system default). It renders `ScoreThresholdField` with no change handler, the chips passed to it, a focused flag, a click handler, and scrolls into view when it becomes focused.  
- **Operator control.** One `LogicOperatorSelect` component used at both depths with different label sets: "any"/"all" on the group card, "Or"/"And" on the connector. Compose it from Paragon's `SelectMenu` and `MenuItem`, following `src/taxonomy/TaxonomyListPage.tsx`. Its `onChange` prop is optional; without it, render the current value as plain text rather than a disabled control.  
- **Score field.** `ScoreThresholdField` always renders a closed-state label, "With a score of `{value}`% `{suffix}`," where `suffix` is "or higher" for `gte`, "or lower" for `lte`, and empty for `eq`. When given an `onChange`, clicking the label opens a popover (the design's "Competency Completion Rule") holding an operator picker and the percentage field, both editable: a Paragon `SelectMenu` over the three permitted operators (`gte`/`eq`/`lte`, shown as "\>=" / "=" / "\<=") and a `Form.Control type="number"` with `min={0} max={100} step={1}` displaying `Math.round(rulePayload.value * 100)`. The field accepts whole-number percentages only: no decimals, no non-numeric characters, and no value outside 0-100 — in practice two digits, except 100 itself, which is the one valid three-digit value. Either control changing calls back with the full `{ op, value: entered / 100, scale: 'percent' }`, converting the displayed percentage to the fraction the backend expects; nowhere else in either consuming ticket does this conversion happen a second time. Without an `onChange`, only the closed-state label renders, as plain text, with no popover to open. `src/grading-settings/credit-section/index.jsx` does the same fraction-to-percentage round trip for the number; `src/taxonomy/TaxonomyListPage.tsx` is the operator `SelectMenu` precedent already used elsewhere in this ticket for `LogicOperatorSelect`. It also takes an optional `getInlineValidationMessage`, following the prop of the same name on `src/taxonomy/tree-table/EditableCell.tsx`, so that the two tickets which make it editable can each refuse a value without this component knowing what makes a value invalid.  
- **Connector rendering.** `GroupConnector` draws the connector between two adjacent sibling bottom-tier groups, bound to their shared course-level group's `logicOperator`, with no change handler. For a course-level group with N rendered bottom-tier group children, render N-1 connectors.  
- **The provider takes `tagId`.** The page passes the selected competency's tag id into `CompetencyAssociationsProvider`, which runs both read queries and supplies `tagId` to the create mutation, so there is one source for it rather than several components each holding their own copy.  
- **Reset on competency change.** Render the provider with `key={tagId}` rather than an effect that clears focus when `tagId` changes. This also keeps working unmodified as later tickets add more state to the provider.  
- **Context file.** `src/taxonomy/competency-management/CompetencyAssociationsContext.tsx` exports a provider and a `useCompetencyAssociations()` hook. Value shape: `{ focus, focusGroup, focusRuleBox, notifyCourseExpanded, associateSubsection, ruleBoxesForGroup, associatedObjectIds, canEditCourse }`, where `focus` is `{ groupId: number | null; ruleKey: string | null }` and `canEditCourse` is `(courseId: string) => boolean`, backed by `useCourseTaggingPermissions` over the union of the visible course-level groups' course ids and the content panel's expanded course ids. Follow the shape of `src/taxonomy/tree-table/TreeTableContext.tsx` and `src/course-outline/CourseOutlineContext.tsx`: a `createContext` with a complete no-op default so consumers never need a null check.  
- **The two focus writers take real identifiers only.** `focusGroup(groupId)` writes `{ groupId, ruleKey: lastRealRuleKeyIn(groupId) }`, and `focusRuleBox(groupId, ruleKey)` writes both fields together, so clicking a rule box in a group that is not currently in focus moves both levels in one click. Neither accepts `null`; \#671 supplies its own writers for the not-yet-saved cases, which write the pair directly. Never expose a setter that writes one field alone.  
- **Clicking the group already in focus is a no-op.** Do not re-resolve its default rule box, or clicking the group heading would silently throw away the rule box the author had selected inside it.  
- **`notifyCourseExpanded(courseId)` contract.** Called only when the author expands a single course node via its own chevron. Not on collapse, and not by the page-level "Expand All" control. Document this on the function, because the constraint cannot be enforced from the provider side.  
- **Course identifier.** `notifyCourseExpanded(courseId)` takes the course's string course key (`course_key`, e.g. `course-v1:Org+Course+Run`), the same identifier \#670's course tree, the corrected \#681 course-level group's `course_key` field, and `useGetContentHits`'s `contextKey` all use, matching the convention already established elsewhere in this app for a `courseId` value: `src/authz/hooks.test.ts` and `src/CourseAuthoringContext.tsx` both type and use `courseId` as this same string course key, never the integer primary key. No translation between them is needed.  
- **`associateSubsection(objectId, courseId)` on the provider.** The content panel's select control calls this one function and passes nothing else. All of the target selection below happens inside it, so the content panel never reads focus, `ruleBoxesForGroup`, or `associatedObjectIds`, and \#671 has exactly one place to add its two extra cases.  
- **Rule identity key.** Put `ruleKeyOf(criterion, systemDefaultProfile)` in `src/taxonomy/competency-management/utils.ts`, building the key from the criterion's effective rule with fields in a fixed order, for example `grade:gte:0.75:percent`. Do not build the key by stringifying the payload object: `JSON.stringify` preserves key insertion order, so two identical rules whose keys arrived in different orders would produce different keys and split into two rule boxes.  
- **Effective rule.** `effectiveRuleOf(criterion, systemDefaultProfile)` in `utils.ts` returns the criterion's own `ruleTypeOverride` and `rulePayloadOverride` when set, and the system default profile's `ruleType` and `rulePayload` otherwise. `ruleKeyOf` is defined in terms of it.  
- **Rule box derivation.** `ruleBoxesForGroup(groupId)` groups that group's criteria by `ruleKeyOf`, returning each box's key, its display rule, and its criteria, sorted by the lowest criterion `id` in the box, with the rule key as tie-break so the sort is total. `CompetencyCriterion` has no `ordering` column of its own, unlike `CompetencyCriteriaGroup`, so this sort uses `id`, a field \#681 already returns, rather than a dedicated per-box value the backend would need to supply. Identity stays on the rule key regardless: sort by criterion id, identify by the rule. `lastRealRuleKeyIn(groupId)` returns the last key. It never returns `null` for a persisted group, because ADR 0002 forbids persisting a group with nothing in it, so every persisted group holds at least one criterion and therefore at least one rule box.  
- **Group tree indexing.** `utils.ts` also holds the indexer that turns \#681's flat `groups` and `criteria` arrays into parent-to-children and group-to-criteria maps, which every derivation above reads.  
- **Bottom-tier group resolution.** `lastBottomTierGroupForCourse(groupsTree, courseId)` returns a group id or `null`, sorting sibling groups by ADR 0002's `ordering` ascending with `id` ascending as tie-break. The associations panel renders the group cards in that same order by calling the same helper.  
- **Group tree depth.** The tree from \#681 is depth 0 the competency root, never rendered, depth 1 the course-level group carrying `course_key`, depth 2 the bottom-tier group holding criteria. Rule boxes sit between depth 2 and the criteria in the display only. This matches the maximum authoring depth of 3 recorded in ADR 0002\.  
- **Resolve every profile-referencing criterion against the system default only.** ADR 0002 describes taxonomy-scoped profiles, and \#633 builds a taxonomy-scoped effective-profile endpoint, but neither is used here.  
- **Initial focus.** One `useEffect` guarded by a `useRef` boolean so it runs at most once per competency, resetting with the provider: when the groups query and the name lookup have both resolved, if exactly one bottom-tier group exists across the visible course-level groups, call `focusGroup` on it. Count `visibleCourseGroups`, not the raw payload: counting the raw payload would focus a group that isn't rendered when the competency's only group is in a hidden course, and would withhold focus from the one group the author can see when a second group exists in a hidden course. The guard resets automatically whenever the provider itself remounts under a new `key={tagId}`, which is what lets this run again for the next competency rather than skipping its initialization. Do not implement initial focus as a derived expression over the group count, because that flips focus back to unset the moment \#671 adds a second group.  
- **Empty-competency focus needs no special case.** When there are no visible course-level groups, whether because none exist or because all of them are hidden, "exactly one bottom-tier group exists" is false, nothing is written, and focus stays at its starting value of unset group and unset rule box, which renders as the panel's empty-state message. Don't add a branch for it. The other two paths that move focus need no equivalent guard either: an author can only click a group that is rendered, and can only expand a course the content panel lists, which is drawn from the same per-user search data, so neither can reach a hidden group.  
- **Identifier types, and the one place they do not match.** Group and criterion ids are plain numeric primary keys, so `focus.groupId` is `number | null`. The competency's tag id is different: it arrives from the route as a string, while every consumer wants a number. Leaving it a string would put a string in the query key while an equivalent number appears elsewhere, giving one competency two cache entries, and would make any `===` comparison against an id from the API silently false.  
- **Reading the competency from the route.** The page reads the tag id from the `/competencytaxonomy/<taxonomy id>/competencytag/<tag id>` route with `useParams`, converts it to a number immediately, exactly as `src/taxonomy/taxonomy-detail/TaxonomyDetailPage.jsx` does, and passes the number everywhere: as `key={tagId}` on the provider and as the `tagId` argument to the read hooks. The `key` is still required even though switching competencies is a navigation: React Router reuses the same element when only a route parameter changes, so the page does not remount on its own and its state would otherwise carry over to the next competency. The create call does not need the taxonomy id from the first route segment, because the tag already determines its taxonomy. Declaring the route itself belongs to whichever ticket creates this page; this ticket only reads the parameter.  
- **API function.** `createCompetencyCriterion(tagId, { object_id, group_id?, rule_type_override?, rule_payload_override? })` in `src/taxonomy/competency-management/data/api.ts`, posting to the criteria endpoint defined by \#665. Follow the conventions in `src/taxonomy/data/api.ts`: a `getApiBaseUrl()` returning `getConfig().STUDIO_BASE_URL`, URLs built through an `apiUrls` object, and requests through `getAuthenticatedHttpClient()`. Do not add a `logic_operator` field: nothing in this ticket can populate it, and \#671 adds both the field and the only case that sends it.  
- **`competency_rule_profile_id` is never sent.** The backend assigns it at creation from the page's own scope, per ADR 0002\. Sending nothing is correct; sending an explicit null is a different thing and should be avoided.  
- **Target selection at create time.** Inside `associateSubsection`, if `focus.groupId` is a real group whose course matches the selected subsection's course, send `group_id: focus.groupId` together with the focused rule box's rule as `rule_type_override` and `rule_payload_override`. In every other case, whether focus is unset or on a real group belonging to a different course, omit `group_id` and both rule fields entirely. \#671 adds the two cases that arise when a not-yet-saved card is in focus.  
- **Rule fields on the create call.** Send `rule_type_override` and `rule_payload_override` together or not at all, and pass the payload through unchanged: the Grade payload carries a fraction between 0.0 and 1.0 while the rule box displays a percentage, and `ScoreThresholdField` is the only place that converts. Sending the focused box's rule is safe and does not pin the criterion to a literal value: the backend normalizes an override that matches what it would have assigned anyway back into a reference to the shared profile.  
- **Mutation hook.** `useCreateCompetencyCriterion` in `src/taxonomy/competency-management/data/apiHooks.ts`, modeled on `useCreateTag` in `src/taxonomy/data/apiHooks.ts`. Unlike `useCreateTag`, its `onSuccess` must invalidate the \#681 groups query without suppressing the refetch, because the new criterion and any new groups have to appear immediately.  
- **Focus after a successful create.** Write both parts of focus from what the request itself established, not from the local tree: the group id comes from the response's `competencyCriteriaGroupId`, and the rule key is `ruleKeyOf` applied to the rule the request sent, or to the system default rule when the request sent no rule fields. Do not call `lastRealRuleKeyIn` here. The refetch has not landed yet, so for a brand-new group it would return `null` and leave focus indistinguishable from a not-yet-saved rule box. Focus therefore points at a group not yet in the tree for one render, which is harmless: nothing renders as focused, and the card scrolls into view when it mounts.  
- **Already-associated set.** Derive `associatedObjectIds` as a `Set` in a `useMemo` over `visibleCourseGroups`, flattened across every group and rule box in it, using each criterion's `objectId`. This is deliberately the same visible set the panel renders, not the raw \#681 payload: a subsection can only ever belong to one course, so if it's browsable in the content panel at all, its course is visible, and so is any existing association for that same subsection. There's no hidden duplicate this set needs to protect against.  
- **Duplicate guard.** Check `associatedObjectIds` at the top of `associateSubsection` and return early with an informational toast. The backend rejects a duplicate tag-and-object pair whichever group is targeted, so this check is not what makes the rule true; it exists so the author is told the subsection is already associated instead of seeing a failed request, and the backend rejection remains the backstop for a race.  
- **Scrolling into view.** Scroll only the innermost focused element: the focused rule box if there is one, otherwise the focused group. Scrolling the rule box brings its group into view as an ancestor, so scrolling both is redundant and produces a visible double jump. Use `ref.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })` in an effect on the active flag, with `block: 'nearest'` so an already-visible target does not move the page. `src/library-authoring/LibraryBlock/LibraryBlock.tsx` is the closest existing example. jsdom does not implement `scrollIntoView`, so tests must stub `Element.prototype.scrollIntoView`.  
- **Error surfacing.** Use `showToast` from `useToastContext` (`src/generic/toast-context`) in the mutation's `onError`. A rejection caused by the dominance validation in \#666 is not distinguishable on the wire today and gets the same generic message. The inline `Alert` pattern in `src/taxonomy/tree-table/SaveErrorAlert.tsx` is the alternative if a persistent banner is preferred; that same pattern is what the panel's own failed-load state uses, described above.  
- **All user-facing strings** go through `defineMessages` in the feature's `messages.ts`, per this MFE's i18n convention.  
- **Module boundaries.** Import other features only through their `index.ts`, and do not import upward from `competency-management` into `taxonomy`. Nothing here touches `openedx-core`, so its import-layering and DEPR rules do not apply.  
- **Out of scope, owned elsewhere.** Adding a not-yet-saved bottom-tier group or rule box, the two add controls that create them, rendering either kind of not-yet-saved card, editing the combining choice or the score on one, and the extra branches those cases add to the create request all belong to \#671. Changing the combining choice on a persisted group, or the score on a persisted rule box, belongs to a sibling ticket that has no GitHub issue number yet. Deleting a group is \#709 and deleting an association is \#710, together with any removal-confirmation dialog and any in-use or learner-status warning unrelated to dominance blocking. Proactively preventing a dominance-ineligible selection before the author attempts it is a separate stub companion ticket, blocked on backend work this ticket does not build. The content panel's own browse, search, and course tree belong to \#670; this ticket adds the select control and the already-associated marking to rows \#670 renders. Renaming a group has no authoring control in this design and is not built. `competency_rule_profile_id` is always omitted; no ticket currently populates it directly. Associating a competency with a whole course by its final grade is not part of this ticket; only gradable subsections are associated, even though the original design material named both as MVP goals. Resolving a criterion's rule against a taxonomy-scoped rule profile rather than the system default is out of scope, regardless of ADR 0002 describing taxonomy-scoped profiles as existing in this phase; \#633 is where that endpoint is built.  
- **Test cases to cover.**  
  - A competency whose associations are all in unresolved courses renders identically to a competency with no associations, and still leaves focus unset.  
  - Selecting a competency with no associations renders the empty-state message, not a card, and leaves focus unset.  
  - The panel does not render any course section until the groups query, the default rule profile query, and the content-name lookup have all resolved.  
  - Switching from a competency with associations to one without clears focus rather than leaving it pointed at the previous competency's group.  
  - The groups query does not fire before a competency is selected.  
  - The tag id read from the route is converted to a number before use.  
  - A course or subsection name comes from the content search lookup, not from \#681's stored course name; a subsection with no lookup result shows a neutral label rather than being hidden.  
  - The already-associated set and the duplicate guard are built from the same visible course-level groups the panel renders, not the raw \#681 payload.  
  - A persisted group's combining choice and a persisted rule box's score both render as text with no interactive control.  
  - A criterion with no override displays the system default profile's score; one with an override displays the override's score; the two are visually identical.  
  - A course-level group with three sibling bottom-tier groups renders two connectors, both showing that course-level group's operator.  
  - Every course section defaults to expanded; collapsing one hides its group cards and leaves every other section's state unchanged; expanding it again shows the same content as before.  
  - Collapsing a section holding the focused group or rule box renders nothing as focused, without throwing.  
  - A subsection in a course the author can see but cannot write to is marked when already associated but offers no select control; the same subsection in a course they can write to offers one.  
  - An empty course-id list issues no permission request and reports not-loading.  
  - With `enableAuthzCourseAuthoring` off, every visible subsection offers a select control, with no call to the permissions endpoint at all.  
  - With the flag on and a course's answer `allowed: false`, that course's subsections still render and still mark already-associated content, but offer no select control on any of them.  
  - A course id absent from the permissions response resolves `canEditCourse` to false, not to a thrown error.  
  - Expanding a second course re-issues the permissions query with both course ids and does not lose the first course's already-resolved answer.  
  - Two course-level groups rendered together each show their own operator on their own connectors.  
  - Two criteria in one group with the same rule render as one rule box; two with different rules render as two.  
  - Rule box order is unchanged after a refetch.  
  - `RuleBoxList` renders no box as focused when the focused rule key matches none of its boxes, rather than throwing.  
  - Expanding a course focuses the last group by `ordering` and its last rule box, and expanding the same course again focuses the same pair.  
  - Expanding a course with no groups leaves both levels unchanged.  
  - Clicking a rule box in a different group moves both levels; clicking the group already in focus leaves its rule box alone.  
  - A click beats a preceding auto-focus and is not reverted by a later re-render.  
  - Selecting a subsection with a same-rule group in focus sends `group_id` and the focused box's rule; selecting from a course with no groups sends neither, and afterwards focus points at the group id from the response together with the system default's rule key.  
  - Selecting an already-associated subsection makes no request.  
  - A failed create leaves the rule box's chips unchanged and shows the error.

**Files to create and modify.** Every path under `src/taxonomy/competency-management/` is provisional: that directory does not exist yet in `frontend-app-authoring` and is created by \#670 and this ticket. Confirm the real names once \#670 lands, and extend the files it created rather than adding parallel ones. Paths in the tables below are relative to that directory.

</details>
<details>
<summary>New files</summary>

| File | Purpose |
| :---- | :---- |
| `CompetencyAssociationsContext.tsx` | The page-level provider and `useCompetencyAssociations()` hook: the focus pair and its two writers, `notifyCourseExpanded`, `associateSubsection`, `ruleBoxesForGroup`, `associatedObjectIds`, and `canEditCourse`, backed by `useCourseTaggingPermissions` over the visible course-group course ids plus the expanded content-panel course ids. |
| `CompetencyAssociationsContext.test.tsx` | Initial focus, auto-focus on course expand, click precedence over auto-focus, and focus after a successful create. |
| `utils.ts` | The group-tree indexer over \#681's flat arrays, the display-name map, `visibleCourseGroups`, the associated-object-id collection, `effectiveRuleOf`, `ruleKeyOf`, `ruleBoxesForGroup`, `lastRealRuleKeyIn`, and `lastBottomTierGroupForCourse`. `canEditCourse` is fetched, not a pure helper, so it lives on the provider instead (see `CompetencyAssociationsContext.tsx` above). |
| `utils.test.ts` | Tree indexing, display-name map and visibility, effective-rule resolution, rule key stability, rule box grouping and ordering, and sibling group ordering. |
| `criteria-groups/CourseGroupList.tsx` | The panel's four states, and maps `visibleCourseGroups` to `CourseGroupSection`; emptiness is decided on that visible list. |
| `criteria-groups/CourseGroupSection.tsx` | One visible course-level group: its named header, its own collapse toggle, its group cards in shared-helper order, and a `GroupConnector` between each adjacent pair. |
| `criteria-groups/CriteriaGroupBox.tsx` | One bottom-tier group card: its read-only any/all control, its focused state and click handler, and its `RuleBoxList`. |
| `criteria-groups/RuleBoxList.tsx` | Derives a bottom-tier group's rule boxes and renders one `RuleBox` per box, with its focus state and its chips. |
| `criteria-groups/RuleBox.tsx` | One rule box: the rule it is given, its chips, its focus state, and scroll-into-view when focused. |
| `criteria-groups/LogicOperatorSelect.tsx` | The shared operator control, with any/all labels on a group card and And/Or labels on a connector, editable only when given an `onChange`. |
| `criteria-groups/GroupConnector.tsx` | The connector drawn between two adjacent sibling bottom-tier groups, bound to their shared course-level group's operator. |
| `criteria-groups/ScoreThresholdField.tsx` | The closed-state score label and its editable popover, and the only place the percentage/fraction conversion happens. |
| `criteria-groups/CriterionChipList.tsx` | The chips inside one rule box, including the empty state for a rule box with no criteria. |
| `criteria-groups/CriterionChip.tsx` | One chip: the associated subsection's display name. |
| `criteria-groups/CourseGroupList.test.tsx` | The four panel states and the two emptiness cases. |
| `criteria-groups/CourseGroupSection.test.tsx` | Header naming, card ordering, connector count and shared value, and independent collapse. |
| `criteria-groups/RuleBoxList.test.tsx` | Rule box derivation and ordering, chip distribution, the empty state, and an unmatched focus key. |
| `criteria-groups/RuleBox.test.tsx` | Override and default scores rendering identically, read-only rendering, and scroll-into-view on focus. |

</details>
<details>
<summary>Files that may already exist from \#670; create if it has not, otherwise extend</summary>

| File | Nature of modification |
| :---- | :---- |
| `data/api.ts` | Add `getCompetencyCriteriaGroups`, `getDefaultCompetencyRuleProfile`, and `createCompetencyCriterion`. |
| `data/apiHooks.ts` | Add the `competencyQueryKeys` factory, `useCompetencyCriteriaGroups`, `useDefaultCompetencyRuleProfile`, `useContentDisplayNames` wrapping `useGetContentHits` from `@src/search-manager`, `useCourseTaggingPermissions` batching a `courses.manage_tags` check across the page's course ids through `@src/authz`, and `useCreateCompetencyCriterion`, invalidating the groups query on success. |
| `data/types.ts` | Add the course-level and bottom-tier group response types, `CompetencyCriterion`, `GradeRulePayload`, the rule profile type, the derived `RuleBox` type, and the create-request payload type. |
| `messages.ts` | Add strings for the panel's loading and failed-load states, the "From within" header, the collapse/expand toggle's accessible label, the any/all and And/Or labels, the score display, the empty rule box state, the association error, and the already-associated notice. |

</details>
<details>
<summary>Modified files</summary>

| File | Nature of modification |
| :---- | :---- |
| The competency associations page component from \#670 | Wrap both panels in `CompetencyAssociationsProvider`; read the tag id from the route and convert it to a number; pass it to the provider and set `key={tagId}` on it. |
| The associations panel component from \#670 | Render `CourseGroupList` in place of its current contents. |
| The content panel component from \#670 | Call `notifyCourseExpanded` from the per-course chevron only; add the subsection select control, offered only for a subsection whose course the author has studio write access to, which calls `associateSubsection`; and the already-associated marking, shown regardless of write access. |
| `src/authz/constants.ts` | Add `MANAGE_TAGS: 'courses.manage_tags'` to `COURSE_PERMISSIONS`. |

</details>


<details>
<summary>Context</summary>

- Parent design: \#648. Foundation this builds on: \#670, which creates the page, the associations and content panels, and the course-search / browse-to-subsection tree.  
- Siblings on the same page: \#671 adds the two controls that create a not-yet-saved group or rule box and makes those cards' fields editable; a sibling ticket with no GitHub issue number yet makes the combining choice and the score editable on a persisted row; \#709 deletes a group and \#710 deletes an association; a stub companion ticket, blocked on backend work, will own proactively preventing dominance-ineligible selections.  
- ADR `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` in `openedx-core` is the source for five facts this ticket relies on, all applied in Technical Details above: a criterion points at one tag-to-subsection association and belongs to exactly one bottom-tier group; the group tree is three levels deep with a rule box as a display grouping rather than a stored level; the backend rejects a group with no criteria; a criterion carries either a shared rule profile or its own complete override but never both and never neither; and sibling groups carry an `ordering` field that sequences them. The ADR is also the source for the Grade rule payload being `{op, value, scale}`, with `op` limited to `gte`, `lte`, and `eq` and `value` a fraction between 0.0 and 1.0.  
- At most one course-level group can exist per competency and course. That constraint comes from \#665, not from the ADR.  
- The design spike \#708 is the source of the design vocabulary and of the connectors between sibling bottom-tier groups being one shared value rather than independent per-pair choices.  
- The associations panel's own button for adding a bottom-tier group is labeled "+ Rule Group," but it creates a bottom-tier group, not a course-level group. \#665 calls the same object a leaf group. That button belongs to \#671.  
- \#773 provides the endpoint for the platform's default competency rule profile this page depends on. See Technical Details for where it is used.  
- There is no group-create endpoint and no UI action that creates a course-level group directly. \#665 creates whatever part of the hierarchy is missing as a side effect of creating the first criterion.  
- Frontend prior art in the same feature area: `src/taxonomy/tree-table/TreeTableContext.tsx` and `src/course-outline/CourseOutlineContext.tsx` for the context shape, `src/taxonomy/tree-table/EditableCell.tsx` for the `getInlineValidationMessage` prop this ticket mirrors on `ScoreThresholdField`, `src/taxonomy/TaxonomyListPage.tsx` for Paragon's `SelectMenu` and `MenuItem`, `src/grading-settings/credit-section/index.jsx` for a percentage input backed by a stored fraction, `src/taxonomy/data/apiHooks.ts` for the create-mutation pattern and query-key-factory convention, `src/taxonomy/data/api.ts` for the API-module conventions, `src/taxonomy/tree-table/SaveErrorAlert.tsx` and `src/generic/toast-context` for error surfacing, `src/library-authoring/data/apiHooks.ts` for the `enabled:` query-gating convention, `src/taxonomy/taxonomy-detail/TaxonomyDetailPage.jsx` for reading and converting a route parameter, `src/library-authoring/LibraryBlock/LibraryBlock.tsx` for scrolling a newly relevant element into view, and `src/search-manager`'s `useGetContentHits` for the course and subsection display-name lookup, which the platform scopes per user.  
- `src/authz/hooks.ts` and `src/authz/data/apiHooks.ts` for Studio's permission-validation pattern and its waffle-flag fallback, `src/advanced-settings/AdvancedSettings.tsx` for calling `useUserPermissions` directly with an inline query rather than through the single-course wrapper, and `src/content-tags-drawer/` for `canTagObject`, the same permission this page's gate mirrors, as the tags drawer already consumes it per object.
</details>
