# Developer communication


Developers question scan results for good reasons: unfamiliar tools, large counts, and a history
of noisy scanners. Answer with evidence from **their own pipeline**, separate what is real from
what is noise, and give one concrete next step. Never argue from authority ("the policy says
so").


## Method


1. **Measure before replying.** Count findings by:
  - severity;
  - scanner (SAST, SCA, secrets, IaC);
  - location file (manifest or module);
  - configuration or scope (release vs test/lint/debug);
  - new versus existing.


  One table beats paragraphs.
2. **Name the tool and what it analyses.** Dependency scanning is SCA: it matches resolved
  package versions against advisories. SAST analyses source code. They are not comparable to each
  other, or to a binary/mobile scanner.
3. **Acknowledge real limitations explicitly.** Examples:
  - The scanner does not know whether a vulnerable code path is reachable on the target platform.
  - Test and tooling classpaths are reported.
  - The MR widget truncates the list.
4. **Give the path forward:**
  - fix whatever is in the shipped artifact;
  - dismiss confirmed non-applicable findings with a reason (who may dismiss);
  - request an exception for structural cases;
  - name the owner and the expected timeline.
5. **Correct yourself publicly** if an earlier answer was wrong.


## Templates


Fill in the `<…>` placeholders with measured values. Keep the tone factual.


### "Are these 5,000 findings legit? Other tools found nothing."


> The <N> findings come from dependency scanning (SCA), not from code analysis. It lists every
> library version resolved by your build and matches it against public advisories. SonarQube
> (code quality/SAST) and <binary scanner> look at different things, so their silence does not
> contradict this.
>
> Breakdown for pipeline <link>:
>
> | Scope | Findings |
> |---|---|
> | test classpaths | <n> |
> | lint/tooling | <n> |
> | debug-only | <n> |
> | **release (shipped)** | **<n>** |
>
> The same library also appears once per module (<m> modules), which multiplies the count.
>
> Please start with the <n> release findings. For findings in tooling you never ship, mark them
> *Not applicable* with a short reason, or ask <security contact> to do it. We are also looking at
> narrowing the scanned configurations centrally.


### "Does it even support <ecosystem/platform>?"


> Yes, for <ecosystem>. It resolves your <build tool> dependency graph (job `<resolution job>`)
> and scans the result. In your pipeline it resolved <n> modules, and package `<x>` appears at
> `<file>`. What it does not do is decide whether a vulnerable function is reachable on
> <platform>. That judgement stays with you, and a dismissal with a reason records it.


### "This CVE doesn't apply to us (e.g. a server-side TLS issue on a mobile client)"


> Agreed that it is likely not exploitable in your context. The finding is correct that the
> vulnerable version is in your graph (via `<path>`). Two options:
>
> 1. Upgrade or constrain the transitive version (`<suggestion>`), which removes it permanently.
> 2. Dismiss it as *Not applicable* with that reasoning. A Maintainer or Security Manager can do
>    this, so it stays reviewed.
>
> If the same pattern repeats across projects, we can add a scoped exception with an expiry.


### "Why did my vulnerable dependency not show up?"


> We traced it:
>
> - resolution <succeeded/failed> (`<job>`);
> - the package <is/is not> in the graph;
> - the scan job <succeeded/failed: reason>;
> - the report <was/was not> ingested.
>
> Root cause: <cause>. Fix: <who does what>. After that, a new pipeline on the MR will show it.


### "What did you put in place to make it work for <platform>?"


> Centrally, without changes to your repository:
>
> - <resolution image with JDKs …>;
> - <internal registry/index pinned>;
> - <artifact limit raised>.
>
> On your side: <only if needed, e.g. CI-safe default for local.properties>. Verified on pipeline
> <link>.


### Scan job failed in my MR, is it blocking?


> The job is `allow_failure`, so it does not fail your pipeline. <If gates are on: with no
> report, the security gate requires approval from <approvers>.> The cause is <signature> and
> the fix is <fix>, owned by <owner>.


## Do not


- Promise that findings will disappear without a change on someone's side.
- Dismiss findings on the developer's behalf without a recorded reason.
- Quote raw logs containing secrets, internal hostnames or tokens. Redact them.
- Blame the developer for a platform-side cause. Own it and give the timeline.
