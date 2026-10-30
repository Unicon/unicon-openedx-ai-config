# Things the code review skill missed; to be improved.

These things were missed on Fable medium.

## https://github.com/javoconsultant/frontend-app-authoring/pull/4

- Fetch requests send course_keys as too long URL param instead of just sending the search param
- Fetch requests need to account for pagination to get all the correct courses (halfway caught by AI)
- Disabled tags don't become enabled when the user clicks on a different competency on the left without refreshing


## https://github.com/AShatsila/frontend-app-authoring/pull/9
src/taxonomy/competency-management/CompetencyAssociationsContext.tsx
    }
    const ruleKey = lastRealRuleKeyIn(groupId, index, systemDefaultProfile);
    setFocus(ruleKey !== null ? { groupId, ruleKey } : null);
    setDuplicateRejected(false);
@jesperhodge
jesperhodge
19 hours ago
I'm not sure why changing focus and setting duplicates as rejected discard the placeholder rule box. Is that an unintended side effect that is used here?

usePlaceholderState.ts has a discardPlaceholder function. Could you use that instead, passing in the desired new focus?
Could you have a look at usePlaceholderState and see if you can find a more explicit way to remove a placeholder than to change these two states?
