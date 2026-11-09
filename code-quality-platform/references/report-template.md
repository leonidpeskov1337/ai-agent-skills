# Report template


```text
Mode:            Create | Harden | Troubleshoot | Fix | Roll out | Communicate
Scope:           repos / pipelines / jobs examined (links)
Assumptions:     intake items that were unknown


Findings (ranked):
 1. <cause> — confidence high|medium|low
    Evidence: <job link, log line, artifact field>
    Owner: platform | consumer | runner/infra | GitLab | policy
 2. ...


Fix:
 Change:        <branch, MR link, files>
 Tests:         <command + counts>, regression test added: yes/no
 Blast radius:  <contexts changed / provably unchanged>
 Rollback:      <how>


Release / propagation:
 Platform release:       <version | pending>
 Intermediate component: <version | pending>
 Developer action:       <bump X to Y>


Unverified:      <what could not be checked and why>
```


Keep the final message short; put detail in the MR description or docs. Never claim a command
passed unless it was executed successfully.
