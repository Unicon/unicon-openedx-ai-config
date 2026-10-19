# Comments on issue #665 (as of 2026-10-11)


---
**thelmick-unicon** at 2026-07-24T14:57:34Z:

The discussion period for this ticket is now complete, and we appreciate all the feedback. We'll be moving forward with development based on the current ticket pending final Axim sign-off. That said, the conversation doesn't have to stop. If you still have feedback, please continue to add to this ticket. We'll review anything new and determine whether it fits within the current timeline or makes more sense as its own ticket for future work. Thanks again for helping make this better!

@ormsbee This is ready for your review. Thank you!

---
**ormsbee** at 2026-08-31T03:00:47Z:

Minor issue that doesn't need to hold up ticket acceptance (because it's trivial to change in the PR): My understanding is that based on our [REST API conventions](https://openedx.atlassian.net/wiki/spaces/AC/pages/18350757/Open+edX+REST+API+Conventions), the URL should be `/api/cbe/v1/...`

However, I notice that `openedx_tagging` does use `rest_api` in its URLs, which I thought was always meant to just be a source file convention, not a URL convention. @bradenmacdonald, @feanil: Do you folks have context on what happened there?

I guess a very minor other quibble is that I don't really see a point in the indirection of having `urls.py` and also a `rest_api/v1/urls.py`, when that's the only kind of URL this app has. But that likewise shouldn't block this work from proceeding.

---
**bradenmacdonald** at 2026-08-31T16:46:02Z:

@ormsbee The new guidelines for URLs are ~~WIP~~ at https://github.com/openedx/openedx-platform/pull/39003 but yes, `/api/cbe/v1/` would be correct. (However, if there are learner-facing endpoints as well, then a decision needs to be made as to whether `/api/cbe/v1/` is a combined learner-author-instructor API namespace or if it should be split into `/api/cbe_authoring/v1` and `/api/cbe_learning/v1` or similar; the Studio-vs-LMS domain should not be used for this purpose going forward).



> However, I notice that `openedx_tagging` does use `rest_api` in its URLs, which I thought was always meant to just be a source file convention, not a URL convention. [@bradenmacdonald](https://github.com/bradenmacdonald), [@feanil](https://github.com/feanil): Do you folks have context on what happened there?

As far as I know, it's only a file convention. There is a URL path [here](https://github.com/openedx/openedx-core/blob/e6a604dab0f2be0984c5900ca49c84a4ba696db6/projects/urls.py#L9) but I believe that's only for test/dev purposes, and can be changed anytime. The platform itself [mounts the tagging API at `/api/content_tagging/v1`](https://github.com/openedx/openedx-platform/blob/ca007c33a74eb44c524d39c3d989aaecc3d0e50f/cms/urls.py#L361) which is [a re-export of `openedx_tagging`'s REST API with some additions](https://github.com/openedx/openedx-platform/blob/ca007c33a74eb44c524d39c3d989aaecc3d0e50f/openedx/core/djangoapps/content_tagging/rest_api/v1/urls.py).

So: I recommend updating this ticket to remove any reference to `rest_api/` being in the URL (it's OK in the python file path), and make sure we've thought about authoring vs. learning API URLs if that's even relevant here.

---
**mgwozdz-unicon** at 2026-09-02T23:41:38Z:

@ormsbee @bradenmacdonald I'm thinking of going with `/api/cbe/v1/...` with intentions of it being a combined learner-author-instructor API namespace. I've given @thelmick-unicon an updated draft of this ticket description that fixes the URL path everywhere.

---
**alezconsultant** at 2026-09-11T11:06:45Z:

@mgwozdz-unicon

Correct me if I'm wrong, but it seems there is an inconsistency between [ADR-0002](https://github.com/openedx/openedx-core/blob/main/docs/openedx_learning/decisions/0002-competency-criteria-model.rst) and AC-12 ( Scenario: Reject duplicate association, a different existing leaf group targeted).

ADR-0002 allows us to create associations with multiple groups for the same competency and object, while AC-12 forbids this. Is this restriction specific to this ticket only?

---
**jesperhodge** at 2026-09-11T13:52:10Z:

> [@ormsbee](https://github.com/ormsbee) [@bradenmacdonald](https://github.com/bradenmacdonald) I'm thinking of going with `/api/cbe/v1/...` with intentions of it being a combined learner-author-instructor API namespace. I've given [@thelmick-unicon](https://github.com/thelmick-unicon) an updated draft of this ticket description that fixes the URL path everywhere.

@mgwozdz-unicon if this is a rest api endpoint, our convention would be `cbe/rest_api/v1/` , though if there's a reason to make `cbe` a subfolder underneath rest_api in this instance specifically, I think that's okay. We distinguish between `rest_api` and `api.py`, with api.py being not a web api but a python interface with functions and classes that are designed to be accessible outside of the djangoapp.
If you are not talking about adding a rest api but about this python interface, I think adding `/v1` would need some justification and would be somewhat confusing since that's the rest api convention. In that case I'd just do `/api/cbe/`. But my guess is that this is about adding a rest api, right?

---
**mgwozdz-unicon** at 2026-09-11T14:24:45Z:

> [@mgwozdz-unicon](https://github.com/mgwozdz-unicon)
> 
> Correct me if I'm wrong, but it seems there is an inconsistency between [ADR-0002](https://github.com/openedx/openedx-core/blob/main/docs/openedx_learning/decisions/0002-competency-criteria-model.rst) and AC-12 ( Scenario: Reject duplicate association, a different existing leaf group targeted).
> 
> ADR-0002 allows us to create associations with multiple groups for the same competency and object, while AC-12 forbids this. Is this restriction specific to this ticket only?

@alezconsultant Let's change the AC to fix this one. It looks like AC-11 (same group re-targeted) and AC-13 (duplicate via the derive-or-create path) already cover what we want rejected per ADR-0002. We can update AC-12 to something like this:

```
Scenario: Group supplied, targeting a different existing leaf group already used by this tag/object pair
  Given a CompetencyCriterion already exists associating object_id X with tag_id T, attached to leaf group G
  And a sibling leaf group G2 also exists for tag_id T under the same course-level group as G
  When a POST request to competency T's endpoint supplies group_id G2 together with the same object_id X
  Then the response returns status code 201
  And no CompetencyCriteriaGroup rows are created at any level
  And a second CompetencyCriterion is created, associated with G2
  And the tag_id/object_id association now participates in both G and G2
```

@thelmick-unicon can you update AC-12 in the ticket to the scenario above?


---
**mgwozdz-unicon** at 2026-09-11T14:36:00Z:

> [@mgwozdz-unicon](https://github.com/mgwozdz-unicon) if this is a rest api endpoint, our convention would be `cbe/rest_api/v1/` , though if there's a reason to make `cbe` a subfolder underneath rest_api in this instance specifically, I think that's okay. We distinguish between `rest_api` and `api.py`, with api.py being not a web api but a python interface with functions and classes that are designed to be accessible outside of the djangoapp. If you are not talking about adding a rest api but about this python interface, I think adding `/v1` would need some justification and would be somewhat confusing since that's the rest api convention. In that case I'd just do `/api/cbe/`. But my guess is that this is about adding a rest api, right?

@jesperhodge Per Braden's comment above (https://github.com/openedx/openedx-core/issues/665#issuecomment-5481494101), `rest_api` is a source-file convention, not a URL one. `/api/cbe/v1/...` is the correct URL. The file path is whatever's already on the branch, or a new `rest_api/v1/` if there isn't one yet.

---
**alezconsultant** at 2026-09-14T22:50:01Z:

@mgwozdz-unicon @thelmick-unicon 
I change name  `competency_criteria_group_id` → `group_id` and `competency_rule_profile_id` → `rule_profile_id` to make it unified across ticket. The consolidated serializer uses this names for both the request and the
response body. Also it seems that 
```
Scenario: Create a criterion with no rule fields supplied
  Given a competency and a valid gradeable-subsection object_id
  When a POST request creates a criterion with no competency_rule_profile_id, rule_type_override, or rule_payload_override supplied
  Then the response returns status code 201
  And the created criterion's "competency_rule_profile_id", "rule_type_override", and "rule_payload_override" are all null
  And this all-null state is valid, signaling that the system default competency rule profile applies
```
should be updated to better reflect logic, since we have database constraints to prevent state in which all 3 fields are null.

---
**thelmick-unicon** at 2026-09-15T14:30:34Z:

@alezconsultant Primary ticket text has been updated with the name changes and the new AC.

---
**jesperhodge** at 2026-09-30T15:51:10Z:

PR: https://github.com/jesperhodge/openedx-core/pull/14
