# [FE] Hide tag removal and tag adding for competency tags on Course Outline and Libraries

GitHub: https://github.com/openedx/openedx-core/issues/784 (#784, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want competency tags on my content to be shown without controls for removing or adding them, in order to not break competency configuration from a page that is not meant to manage it.

## Acceptance Criteria


```
Scenario: A competency tag is shown without a remove control
  Given a content object tagged with a competency
  When its tags are shown on the Course Outline page
  Then the competency is listed
  And no control for removing it is shown

Scenario: Ordinary tags keep their remove control
  Given a content object tagged from a taxonomy that is not a competency taxonomy
  When its tags are shown on the Course Outline page
  Then each of those tags is shown with its remove control as it is today

Scenario: An object carrying both kinds shows controls only for the ordinary tags
  Given a content object tagged with both a competency and an ordinary tag
  When its tags are shown
  Then the ordinary tag has a remove control
  And the competency does not

Scenario: Competency taxonomies are not offered for adding tags
  Given a content object
  When the author opens the control for adding a tag
  Then competency taxonomies are not offered as a choice
  And every other taxonomy is offered as it is today

Scenario: A competency tag is still readable
  Given a content object tagged with a competency
  When its tags are shown
  Then the competency's name is shown and legible
  And it is not visually presented as an error or a warning

Scenario: An author using a keyboard or screen reader is not offered the hidden controls
  Given a content object tagged with a competency
  When the author moves through the tag list using a keyboard
  Then no removal control for the competency receives focus
  And no removal control for it is announced
```

## Description

Course Outline show each tag with a remove control, plus an add-tag control for any taxonomy. Competency tags get no special treatment today, so an author can remove or add one from a page that knows nothing about the competency criteria built on it.

**Two payloads, two gating tickets.** Removing reads the per-object tag payload, gated by \#783. Adding reads the taxonomy list (`useTaxonomyList`), gated by \#618. The two halves are independent. This ticket uses the taxonomy type from the tagging payloads to disallow users from adding or removing tag associations from the Course Outline pages.

Figma Links:
Add [Course Outline competency tags](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=2972-25103).

Screenshots:

<img width="1600" height="1480" alt="Image" src="https://github.com/user-attachments/assets/39dc6f9c-d8f4-4acd-970d-6116f147f7f0" />

<img width="1600" height="1480" alt="Image" src="https://github.com/user-attachments/assets/ed827281-4fb8-42c3-a2db-752a971156c7" />


<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What is hidden and what is not.** The competency tag itself stays visible, because an author needs to see what a piece of content is tagged with. What disappears is the control for removing it, and competency taxonomies stop appearing in the list of taxonomies an author can add a tag from. Managing competency associations happens on the Competency Management page instead.

**How the frontend tells the two apart, per control.** The remove control gates on each tag's taxonomy type in the per-object tag payload, which \#783 adds. The add-tag control gates on each taxonomy's type in the taxonomy list payload, which \#618 adds. Gate on the type field in each case, rather than on a hardcoded taxonomy name or identifier.

**Hiding has to mean removed, not visually suppressed.** A control that is merely styled out of sight is still focusable by keyboard and still announced by a screen reader, and in this case it is still clickable, so it would remain a route to breaking competency configuration for exactly the authors least able to recover from it. The control must not be rendered.

### Implementation specifics

- **Gate the remove control on the taxonomy type field \#783 adds** to each tag in the per-object tag payload. Do not match on taxonomy name, and do not maintain a client-side list of competency taxonomy ids.  
- **Gate the add-tag taxonomy filtering on the taxonomy type \#618 adds to the taxonomy list payload** (`useTaxonomyList`), independent of \#783. Filter competency taxonomies out of that list so the author is not offered a taxonomy they cannot usefully pick. Leave every other taxonomy exactly as it is.  
- **Do not render the removal control** for a competency tag, rather than hiding it with CSS or disabling it. A disabled control is still discoverable and still communicates that the action ought to be possible.  
- **Handle the per-object payload not carrying the taxonomy type field.** Until \#783 is deployed, or against an older backend, the type may be absent from that payload. Treat absent as "not a competency" so the remove control behaves as it does today rather than hiding on every tag. The same applies to the add-tag list until \#618 is deployed.  
- **Do not add an explanatory tooltip or message** in this ticket. Telling the author where to manage competency tags instead is a reasonable idea and is not in the approved scope; raise it separately rather than inventing copy here.  
- **Tests:** a competency tag renders with no removal control in the DOM; an ordinary tag renders with one; a mixed object renders correctly; competency taxonomies are absent from the add-tag list; the competency's name is still rendered; a per-object payload with the type field absent renders today's remove controls; a keyboard traversal test asserting no removal control for a competency is focusable. 
- **Out of scope:** the backend field (\#783), the Competency Management page's own controls, and any confirmation dialog, which are \#785 and \#786.

### Files to modify

| File | Nature of modification |
| :---- | :---- |
| `content-tags-drawer/ContentTagsDrawer.tsx` / `ContentTagsDrawerHelper.jsx` | gate the remove control on the per-object payload's taxonomy type, and the add-tag taxonomy list on its own taxonomy type |
| the corresponding tests | rendered-without-control, mixed-object, add-list-filtered, absent-field-fallback, and keyboard-traversal tests, for Course Outline |

Context 

-  adds the taxonomy type to the per-object tag payload the remove control gates on. \#618 adds it to the taxonomy list payload the add-tag control gates on; confirm it has landed before starting that half.  
- The approved implementation approach on \#655, for why competency tags must not be removable from these pages.  
- \#680 and \#663 for the Competency Management surfaces where competency associations are managed instead.

</details>
