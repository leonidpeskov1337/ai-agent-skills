# Report template


Keep the report short. Link to the evidence instead of pasting it, and redact secrets.


```markdown
## <Title: symptom or change>


**Mode:** investigation | change | design | exception review | survey | developer Q&A
**GitLab:** <version, offering> · **Delivery:** <mechanism> · **Scope examined:** <groups/projects, time window>


### Summary
<2–4 sentences: what is happening, why, who acts.>


### Evidence
| # | Observation | Source |
|---|---|---|
| 1 | <fact> | <job/pipeline/GraphQL/commit link> |


### Causes (ranked)
| Rank | Cause | Confidence | Owner | Evidence |
|---|---|---|---|---|
| 1 | <cause> | high/med/low | project/platform/infra/admin/product | #1, #3 |


### Fix
| Action | Owner | Blast radius | Risk | Rollback | Verification |
|---|---|---|---|---|---|
| <exact change> | <who> | <projects affected> | <risk> | <how to undo> | <what proves it worked> |


### Not verified / assumptions
- <item and how to verify it>


### Follow-ups
- <docs update, upstream issue, survey re-run date>
```


For an **estate survey**, replace the Evidence and Causes sections with one table:


| Class | Jobs | Projects | Owner | Example | Action |
|---|---|---|---|---|---|


For an **exception review**, state the decision (approve, narrow or reject), give the exact
corrected entry, and give the reason for each change.
