# [BE] openedx-platform - Verify taxonomy_type passes through on Create & Import

GitHub: https://github.com/openedx/openedx-core/issues/629 (#629, CLOSED)
Cached: 2026-09-25

Part of #614. See parent for use case, acceptance criteria, and architecture rationale.

**Depends on:** openedx-core sub-issue #628

### Files to verify/modify

| File | Change |
| :---- | :---- |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py` | Verify `TaxonomyOrgView.create_import()` (lines 109–133) does not strip `taxonomy_type` before calling `super().create_import()`. Patch if it does. |

This may require no code changes — the intent is to confirm the field flows through
correctly once the openedx-core changes are in place.

#### Example Resolution Prompt

In `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py`, inspect
`TaxonomyOrgView.create_import()` (lines 109–133) and confirm that `taxonomy_type` is
not stripped from the request data before the `super().create_import()` call. If it is,
pass it through explicitly. Also verify the `create()` path does not strip the field.
No other changes are expected in this repo.
