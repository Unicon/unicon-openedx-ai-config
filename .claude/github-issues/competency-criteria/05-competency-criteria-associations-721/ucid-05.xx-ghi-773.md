# [BE] Read the rule profiles an instance defines

GitHub: https://github.com/openedx/openedx-core/issues/773 (#773, OPEN)
Cached: 2026-09-21

## User Story

As a user of the Competency Management page, I want the Competency Management page to be aware of the rule profiles an instance defines, in order to know what the instance currently requires for mastery before deciding whether a criterion should follow that rule or override it.

## Acceptance Criteria

```
# Reading the rule

Scenario: Read the rule an instance currently requires for mastery
  Given an instance whose only rule profile is the instance-wide default
  And a signed-in caller
  When the caller requests the rule profiles
  Then the caller receives a collection containing that one profile
  And the profile reports the rule learners are evaluated against
  And the profile reports that it applies instance-wide rather than to one taxonomy, course, or organization
  And the profile carries a reference by which a criterion can later be pointed at it

Scenario: Report a rule complete enough for a caller to act on without guessing
  Given an instance whose instance-wide default requires a grade at or above a given fraction
  When the caller requests the rule profiles
  Then the profile reports which kind of rule it evaluates, the comparison it applies,
       and the threshold it compares against
  And the threshold is reported together with the scale it is expressed on,
       so a caller cannot read the fraction as a percentage or the percentage as a fraction

# Staying correct once narrower profiles exist

Scenario: Tell the instance-wide default apart from a narrower profile
  Given an instance with a rule profile scoped to a single taxonomy alongside the instance-wide default
  When the caller requests the rule profiles
  Then every returned profile reports the scope it applies to
  And the caller can identify the instance-wide default from the scope each profile reports,
       without depending on how many profiles were returned or on the order they arrived in
 # Verified via a unit test creating the taxonomy-scoped row directly as a fixture: no create
  # endpoint exists yet to reach this state through a live call, so this is not Postman-testable.

Scenario: Read a collection larger than one response carries
  Given more rule profiles exist than a single response carries at once
  When the caller requests the rule profiles
  Then the caller receives part of the collection together with a way to request the remainder
  And requesting the remainder yields the profiles not already returned, with none repeated and none skipped
 # Verified via a unit test creating enough rows directly as fixtures to exceed one page: no
  # create endpoint exists yet to reach this state through a live call, so this is not
  # Postman-testable.

Scenario: Return the profiles in a stable order
  Given an instance with several rule profiles
  When the caller requests the rule profiles twice, with no profile changing in between
  Then the profiles arrive in the same order both times
 # Verified via a unit test creating several rows directly as fixtures: no create endpoint
  # exists yet to reach this state through a live call, so this is not Postman-testable.

# What the collection leaves out

Scenario: Leave archived profiles out of the collection
  Given an instance with an archived rule profile alongside the instance-wide default
  When the caller requests the rule profiles
  Then the archived profile is not among those returned
  And the instance-wide default is returned
 # Verified via a unit test creating an archived row directly as a fixture: no archive endpoint
  # exists yet to reach this state through a live call, so this is not Postman-testable.

Scenario: Keep the instance's internal scope bookkeeping out of the response
  Given an instance with the instance-wide default rule profile
  When the caller requests the rule profiles
  Then the response describes each profile's scope in terms a caller outside this system can act on
  And it does not expose the internal value the system uses to enforce one profile per scope

# Empty and refused cases

Scenario: Report an instance with no rule profiles as empty rather than as a failure
  Given an instance where no rule profile exists
  When the caller requests the rule profiles
  Then the caller receives an empty collection
  And the request is not reported as having failed
  # This is the scenario that fails if the endpoint was built as a single-object read.
 # Verified via a unit test against a database with no seeded row: #613's migration seeds this
  # row on every real deployment, so this state is not reachable on a live instance and is not
  # Postman-testable.

Scenario: Let a signed-in caller who is not platform staff read the instance-wide default
  Given an instance whose only rule profile is the instance-wide default
  And a signed-in caller who is not platform staff, such as a course author
  When the caller requests the rule profiles
  Then the caller receives a collection containing the instance-wide default
  # This is the scenario that fails if reading is limited to taxonomy administrators. The
  # Competency Management page is used by course authors (#672), and it cannot show a
  # criterion's "score of X% or higher" without reading the instance-wide default.

Scenario: Refuse a scoped profile to a caller who cannot view the taxonomy it is scoped to
  Given a rule profile scoped to a disabled taxonomy
  And a signed-in caller who is not platform staff
  When the permission to read that profile is checked for that caller
  Then the permission is refused
 # Verified via a unit test of the permission predicate, with the taxonomy-scoped row created
  # directly as a fixture: no create endpoint exists yet to reach this state through a live
  # call, so this is not Postman-testable.

Scenario: Refuse a caller the system cannot identify
  Given a caller the system cannot identify
  When the caller requests the rule profiles
  Then the request is refused
  And no rule profile is returned
```

## Description

What nothing exposes is the rule the profile holds: no caller can read the comparison and the threshold that mastery currently requires, so nothing can report it, record it, or judge whether the shared default suits a given criterion.

The instance-wide default is the only rule profile this phase creates, and it is seeded rather than authored. Profiles scoped to a taxonomy, a course, or an organization exist in the data model, but no authoring flow creates one yet.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; the notes below exist to save the implementer some thinking.

### In short

**What the endpoint is.** A single collection route, `rule_profiles/`, returning every non-archived `CompetencyRuleProfile` the requester may read, in the standard paginated envelope with the profiles under `results`. There is no scope filter and no separate route for the system default. Today the instance holds exactly one profile, the seeded system default, so the collection has one element. The endpoint is still a collection in every respect, and a client that treats it as a singleton will be wrong the day a second scope is enabled.

**How a client tells the profiles apart.** Each row carries a derived `scope_type` field, so a client identifies a profile by value rather than by its position in the list. The derivation recognizes all four scope kinds from the outset, so it never has to be edited when a scope is enabled. The lookup that finds the system default queries the three scope columns for null; it never matches on the `scope_code` string, because ADR 0002 Decision 3 states that column embeds internal identifier references, exists solely to enforce uniqueness, and is not intended to be exported or exposed outside this system.

**Why the response is paginated from the first commit.** ADR 0002 Decision 2's closing boundaries state that pagination is supported for authoring and list APIs. Beyond that, pagination is the one thing here that cannot be added later without breaking clients: an unpaginated list is a bare JSON array, and wrapping it in an envelope changes the top-level JSON type. Because this repository is a published library, the page sizes are pinned on the view rather than inherited from the consuming project, so the envelope and the page size are part of this contract instead of varying by deployment.

**What the response carries, and what it deliberately omits.** Each row carries an identifier, a scope type, the rule type, the rule payload, and whether the profile is archived. The identifier is the model's own primary key, because that is what the criterion-update endpoint accepts (\#759), and because the tagging app's REST API already exposes the primary key for taxonomies, which have no external identifier either. The archived flag is included even though today's active-only filter means it is always false, because `CompetencyRuleProfile` is exempt from hard deletion entirely per ADR 0002 Decision 7: archiving is the only way to take a profile out of use, archived rows are permanent and stay queryable, and a client must be able to tell one apart without a later contract change. Three things are omitted on purpose. `scope_code` is omitted for the reason above. The three raw scope columns are omitted because the course and organization references are internal foreign keys that mean nothing to an authoring client, and emitting them as always-null today would commit the contract to that representation before any caller needs it. An in-use indicator is omitted because the guardrail it serves fires when a profile is edited, and no write endpoint is in scope here.

**Why the collection is active-only, and why that is decided now.** Because archived profiles are never deleted, they accumulate permanently, so an unfiltered collection that included them would degrade without bound. Deciding this now also avoids a later behavior change: if the collection meant "everything" today and narrowed to "active" later, clients would notice. A parameter to include archived rows is a plausible future addition and is out of scope, as are scope filters; both are additive, because a client that sends no parameters keeps today's behavior.

**Who may read it, and how that gate composes with future scopes.** Anyone who can view the taxonomy a profile applies to may read that profile. Reading is gated on a new CBE permission whose predicate asks the tagging app's `oel_tagging.view_taxonomy` permission, passing the profile's taxonomy when the profile is taxonomy-scoped and no taxonomy otherwise. The instance-wide default has no taxonomy, and `view_taxonomy` with no taxonomy is granted to every caller, both in this repository's `can_view_taxonomy` ("anyone can list all taxonomies") and in the `openedx-platform` override of that permission. So every signed-in caller, including a course author who is not platform staff, can read the instance-wide default. That is the audience this endpoint needs: the Competency Management page is used by course authors (#672), it shows each criterion's threshold and groups criteria by rule, and a criterion that follows the default stores only a reference to the profile, not the threshold itself. Reading a criterion's competency tree (#681) is gated the same way, through `oel_tagging.view_tag`, which delegates to `view_taxonomy`. A rule profile holds only a rule and a threshold, no learner or course data. The predicate checks the permission through `user.has_perm` rather than importing the tagging predicate function, so that the `openedx-platform` override, registered with `rules.set_perm`, takes effect instead of this repository's default.

**What this ticket extends, and what it depends on.** The CBE REST package, the app-root URL configuration, the applet's public API module, and the mount that makes CBE reachable from Studio all already exist, established by \#664. This ticket adds one API function, one serializer, one viewset, one router registration, a pinned paginator, and the first CBE-local permission, plus tests. It adds no model, no migration, and no `openedx-platform` work of its own. It depends on \#613 for the `CompetencyRuleProfile` model and for the seeded system-default row, and it does not seed that row itself. If no row has been seeded, the endpoint reports an empty collection rather than an error, because a collection with no members is an empty collection and not a missing resource.

### Implementation specifics

- **Applet API function.** `get_competency_rule_profiles() -> QuerySet[CompetencyRuleProfile]` in `src/openedx_learning/applets/cbe/api.py`, added to that module's existing `__all__`, returning `CompetencyRuleProfile.objects.filter(archived=False).order_by("id")`. Returning a lazy queryset from a public API function follows `openedx_tagging.api.get_taxonomies`, which `TaxonomyView.get_queryset` consumes the same way, and it is what makes pagination work.  
- **The `competency_` name prefix is required.** The umbrella `src/openedx_learning/api.py` flattens every applet's API into one namespace shared with `learning_pathways`.  
- **Umbrella re-export needs no edit**, provided the umbrella wildcard-imports the applet API modules and the applet declares `__all__`. `src/openedx_content/api.py` is the working example, and its own comment records why the wildcard is safe.  
- **Deterministic ordering is mandatory, not cosmetic.** An unordered queryset produces inconsistent pages and triggers Django's `UnorderedObjectListWarning`. Order by `id` ascending, and do not order the system default first: a stable position would invite clients to identify profiles positionally, which is the assumption this endpoint exists to prevent.  
- **Serializer.** `CompetencyRuleProfileSerializer(serializers.ModelSerializer)` in `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py`, with `fields = ["id", "scope_type", "rule_type", "rule_payload", "archived"]` and every field read-only.  
- **`scope_type` derivation.** A `SerializerMethodField` returning `"system_default"` when all three scope columns are null, and otherwise `"taxonomy"`, `"course"`, or `"organization"` for whichever column is non-null. When a second scope kind is actually enabled, move that derivation onto the model so non-REST callers, in particular the profile-assignment computation in ADR 0002 Decision 4, share one definition; a single caller does not justify the move yet.  
- **Return `rule_payload` verbatim as stored, without normalizing it.** ADR 0002 Decision 3 fixes the threshold as a fraction between 0.0 and 1.0 inclusive, "matching the platform's existing fractional grade representation, not a 0-100 scale", while its own worked example pairs a value of `0.75` with a `scale` of `"percent"`. That ambiguity is why the scale must be reported alongside the threshold, and why this endpoint must not become a second definition of the payload contract. Cover the pairing in a test asserting the exact stored shape. If the seeded row turns out to omit `scale`, that is a defect in the seed and belongs to \#613; raise it rather than defaulting the key here.  
- **`scope_type` values are snake\_case lowercase, `rule_type` values are CamelCase** (`"Grade"`), because ADR 0002 defines them that way. Do not harmonize the two; the rule type's casing belongs to the model.  
- **Viewset.** `CompetencyRuleProfileView(mixins.ListModelMixin, GenericViewSet)` in `src/openedx_learning/applets/cbe/rest_api/v1/views.py`, with `serializer_class`, `permission_classes`, `pagination_class`, and a `get_queryset` returning `get_competency_rule_profiles()`. Use a viewset rather than a `ListAPIView` so that create and a by-identifier detail route can later be added as extra mixins with no change to the URL module.  
- **Set `authentication_classes` on the viewset class directly.** Do not import `view_auth_classes` from `openedx_tagging/rest_api/utils.py`, which is another app's REST internals rather than its public API.  
- **URL registration.** Add `router.register("rule_profiles", views.CompetencyRuleProfileView, basename="rule_profile")` to the router already defined in `src/openedx_learning/applets/cbe/rest_api/v1/urls.py`. Do not create a second router or a second URL module. The path segment is underscored, matching `object_tags` and `object_tag_counts` in `src/openedx_tagging/rest_api/v1/urls.py`.  
- **The client-visible path is inherited, not decided here.** \#664 mounts CBE at `api/cbe/rest_api/`, so this endpoint resolves to `api/cbe/rest_api/v1/rule_profiles/`. This ticket does not revisit that prefix.  
- **Pagination class.** `CompetencyRuleProfilePagination` in a new `src/openedx_learning/applets/cbe/rest_api/paginators.py`, subclassing `DefaultPagination` from `edx_rest_framework_extensions.paginators`, with explicit `page_size` and `max_page_size` rather than inheriting the consuming project's `DEFAULT_PAGINATION_CLASS`. The tagging app pins `TaxonomyPagination` and `TagsPagination` the same way. Keep the module at `rest_api/` rather than `rest_api/v1/`, matching the tagging app, because pagination is version-independent.  
- **Permission predicate.** `can_view_competency_rule_profile(user, profile=None) -> bool` in a new `src/openedx_learning/applets/cbe/rules.py`, returning `user.has_perm("oel_tagging.view_taxonomy", taxonomy)`, where `taxonomy` is `profile.competency_taxonomy` when a profile is given (itself `None` for any profile not scoped to a taxonomy), and `None` when no profile is given. Register it with `rules.add_perm`. `can_view_tag` in `src/openedx_tagging/rules.py` delegates to `view_taxonomy` the same way. Do not import `is_taxonomy_admin` or `can_view_taxonomy` and call them directly: a direct call bypasses the `openedx-platform` override of `view_taxonomy`.  
- **Permission scaffolding is new to CBE.** \#664 gates its endpoint by reusing the tagging app's `TaxonomyObjectPermissions` and `can_change_taxonomy` directly and explicitly introduces no CBE permission, so this ticket adds the applet's `rules.py` and its `rest_api/v1/permissions.py`. If either module exists by the time this is picked up, extend it rather than creating a parallel one.  
- **Rules autodiscovery requires an app-root module.** The rules autodiscovery app config imports `<app_package>.rules`, so `src/openedx_learning/rules.py` must exist and import the applet's rules module for the permission to register, mirroring how the umbrella API module pulls in its applets.  
- **DRF permission class.** `CompetencyRuleProfilePermissions(DjangoObjectPermissions)` in `src/openedx_learning/applets/cbe/rest_api/v1/permissions.py`, with a `perms_map` granting the read methods the view permission and an empty list for `OPTIONS`, matching `TaxonomyObjectPermissions`. The base class resolves the model through `view.get_queryset()`, which is lazy, so no query is issued during the permission check. An unidentified caller gets 401 and an identified but unpermitted caller gets 403 from DRF, with no CBE-specific handling.  
- **Mark the API unstable.** `README.rst` states that APIs not marked "UNSTABLE" are considered stable and that breaking them goes through the community deprecation process. Mark both `get_competency_rule_profiles` and the viewset UNSTABLE in their docstrings while the rule-profile family is incomplete, so the deferred create, update, and archive endpoints can adjust the shape without a deprecation cycle. There is no existing use of the marker anywhere in `src/`, so this establishes the pattern rather than copying one.  
- **Layering is a dependency, not a task here.** `openedx_learning` is registered in `.importlinter`'s `root_packages` and placed in the layering contract by \#613, and `lint-imports` must pass. Worth knowing: a top-level package absent from `root_packages` is silently exempt from every layering contract, so CBE imports would go unchecked with no failing build to reveal it.  
- **No PII annotation is needed.** There is no new model and no migration, so `make pii_check` is unaffected; annotations belong with the models in \#613.  
- **Tests** go in `tests/openedx_learning/applets/cbe/`, mirroring `tests/openedx_content/applets/`, split into `test_api.py`, `test_views.py`, and `test_rules.py` as `tests/openedx_tagging/` is split. This repository keeps every test under the top-level `tests/` tree and has none under `src/`. Migrations run in the test database, so the seeded system-default row is already present; do not write tests that assume an empty table.  
- **Specific cases to cover:**  
  - A permitted request returns one result whose scope type is the instance-wide one and whose payload matches the seeded row exactly, including its scale key.  
  - The response contains no `scope_code` key and no scope-column keys.  
  - The lookup still succeeds when a row's `scope_code` is unrelated to the query, which proves the null-column query rather than a string match is in use.  
  - A taxonomy-scoped row created directly in a fixture appears in the same collection alongside the default, with the taxonomy scope type and in identifier order. This is the actual proof that a second scope is additive.  
  - An archived row created in a fixture is excluded.  
  - An empty table reports an empty collection rather than a missing resource.  
  - A signed-in caller who is not staff receives the instance-wide default, and an unidentified caller is refused.  
  - The predicate refuses a non-staff caller for a taxonomy-scoped profile whose taxonomy is disabled, and allows a staff caller for the same profile. This proves the predicate delegates to `view_taxonomy` rather than allowing everyone.  
  - The response is the paginated envelope rather than a bare array.  
- **Out of scope, named so nobody builds it here:**  
  - Creating, updating, or archiving a profile.  
  - An in-use indicator on the response, whose definition is pinned to ADR 0003 Decision 4 on \#613 if it is ever added.  
  - Scope filters and scope reference fields. Until a scope reference field exists, a non-default row tells a client the kind of scope but not which object is scoped, so a client must not try to act on one.  
  - A by-identifier detail route.  
  - Filtering rows the caller may not read out of the collection. The list request checks the permission once with no profile, so it does not hide individual rows. No row other than the instance-wide default can be created yet; the work that makes scoped profiles creatable filters the queryset with the same predicate.  
  - An exception handler module, which the deferred write endpoints will need for their conflict response.  
  - Django admin registration.  
  - Seeding the system-default row, which is \#613's.

Files to create and modify **New files**

| File | Purpose |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/rest\_api/paginators.py | `CompetencyRuleProfilePagination` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/permissions.py | `CompetencyRuleProfilePermissions` |
| src/openedx\_learning/applets/cbe/rules.py | `can_view_competency_rule_profile` and its permission registration |
| src/openedx\_learning/rules.py | app-root rules module, imported by rules autodiscovery |
| tests/openedx\_learning/applets/cbe/test\_rules.py | permission predicate tests |

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | add `get_competency_rule_profiles()` and extend `__all__` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/serializers.py | add `CompetencyRuleProfileSerializer` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/views.py | add `CompetencyRuleProfileView` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/urls.py | register `rule_profiles` on the existing router |
| tests/openedx\_learning/applets/cbe/test\_api.py | add filtering, ordering, and null-scope lookup tests |
| tests/openedx\_learning/applets/cbe/test\_views.py | add response-shape, envelope, empty-collection, and refusal tests |

- Context ADR 0002, `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: Decision 3 for the profile's columns, the seeded all-null-scope system default, the check constraint, and `scope_code` being internal-only; Decision 2's closing boundaries for pagination on list APIs; Decision 7 for archive-only archiving.  
- ADR 0003, `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`, Decision 4: the pinned definition of a profile being in use.  
- ADR 0001, `docs/openedx_learning/decisions/0001-competency-criteria-location.rst`: why CBE code sits at `src/openedx_learning/applets/cbe/`, and how the umbrella app aggregates its applets.  
- `docs/openedx_content/decisions/0010-merge-authoring-apps-into-openedx-content.rst` for the applet convention and umbrella aggregation, with `src/openedx_content/api.py` as the working example.  
- `docs/openedx_content/decisions/0003-identifier-conventions.rst` for `id`, `uuid`, and `key`.  
- Prior art for a read-path list endpoint: `src/openedx_tagging/rest_api/v1/views.py`, `serializers.py`, `permissions.py`, and `urls.py`, plus `src/openedx_tagging/rest_api/paginators.py`; and `src/openedx_tagging/rules.py` for the taxonomy-administrator predicate and the permission-registration pattern.  
- \#613 and \#641 land the `CompetencyRuleProfile` model. \#613 seeds the system-default row via a data migration, validates the rule payload at the model layer, adds the profile's archived flag, and registers `openedx_learning` in the installed apps and the layering contract. This ticket depends on all of it.  
- \#664 established the CBE REST package, the app-root URL configuration, the applet's public API module, and the mount at `api/cbe/rest_api/`.  
- \#759 accepts a rule profile identifier from a caller, which is why this endpoint exposes one.

</details>
