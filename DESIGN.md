# Design & Architecture Plan
## CSI 3480 Final Project — Indirect Prompt Injection: Attack and Defense

**Group:** [number] — Jas (Builder), [name] (Attacker), [name] (Defender)
**Course:** CSI 3480 Security and Privacy in Computing, Fall 2026
**Status:** Planning draft. Items marked **[DECIDE]** need a team decision before building.

> This is a planning document, not report text. It defines what we are building and
> who owns what. The report is written separately, in our own words, when the work is done.

---

## 1. One-sentence project statement

We build an AI email assistant that reads untrusted content (web pages and files),
demonstrate that hidden instructions in that content can hijack it into performing a
sensitive action (sending email), and then design and prove defenses that stop the hijack —
all inside an isolated environment we control.

This mirrors the structure of the instructor's suggested topics: study an attack in a
controlled environment, then demonstrate detection, prevention, and mitigation.

---

## 2. Threat model and scope

Being explicit about scope is what keeps this an authorized research project rather than
anything else. Every test runs against **our own agent, our own test accounts, our own
sandbox.** Nothing targets a real person, a real inbox, or a live third-party service.

**In scope**
- A single AI agent we wrote, running locally in an isolated environment.
- Untrusted inputs: a web page we host locally, and a file we provide.
- One sensitive action the attacker tries to trigger: **sending an email.**
- The attacker's goal: make the agent send an email it was never asked to send
  (e.g. exfiltrate the contents of a file to an address chosen by the injected text).

**Out of scope (state this explicitly in the report)**
- No real email providers, no real recipients, no production AI products.
- No targeting of anyone's personal assistant or any live system.
- Email "sending" is simulated/logged in the sandbox, not delivered to the open internet.
  **[DECIDE]** confirm we stub the send so nothing actually leaves the sandbox.

**The trust boundary (the single most important idea in the project)**
- Instructions from the **user** are trusted.
- Text the agent **reads from a web page or file** is untrusted data, never commands.
- The vulnerability exists precisely when the agent confuses the two.

---

## 3. System architecture

### 3.1 Pipeline

```
User gives the agent a task
        |
        v
[ Input layer ]  read_webpage() / read_file()
   returns: content + source label (USER vs CONTENT)
        |
        v
[ SLOT 1: detection ]  defender inspects untrusted content, may veto   <-- defender
        |
        v
[ Brain ]  LLM decides what action the task requires
        |
        v
[ SLOT 2: action gate ]  nothing reaches a sensitive action
   without passing through here                                        <-- defender
        |
        v
[ Action layer ]  send_email()  (the sensitive sink)
```

### 3.2 Components and responsibilities

| Component | What it does | Owner |
|---|---|---|
| Input layer | `read_webpage()`, `read_file()`. Each returns content **plus a source label**. | Builder |
| Brain | The LLM call. Takes the task + labeled content, decides the action. | Builder |
| Action layer | `send_email()` kept as an isolated function the brain **requests**, never calls directly. | Builder |
| Slot 1 (detection) | Inspects untrusted content before the brain acts; flags likely injection. | Defender |
| Slot 2 (action gate) | Sits between brain and action layer; blocks/kneecaps unauthorized sends. | Defender |
| Attack suite | A set of malicious web pages / files, organized by technique. | Attacker |
| Evaluation harness | Runs every attack against the agent, records outcome. | Attacker |
| Front end (optional) | Visualizes a message being read, flagged, blocked or allowed. | Defender |

### 3.3 The design rule that makes defense possible

The brain must **request** a send, not perform one. The gap between "brain wants to send"
and "email is sent" is Slot 2. If the brain can call `send_email()` directly, the defender
has nowhere to stand and the structural defense is impossible. Builder owns getting this
separation right from day one.

### 3.4 Source labeling

Every piece of text carries where it came from (`USER` or `CONTENT`). The whole vulnerability
is the agent treating `CONTENT` as if it were `USER`. Tracking this from the start makes both
defenses easier and gives us the core of the methodology section.

---

## 4. Defense design (two layers)

Detection alone is the weakest defense and the demo must not pretend otherwise. We build
**defense in depth:** a detector that catches the obvious, and a structural gate that holds
even when the detector is fooled.

**Layer 1 — Detection (Slot 1).** Inspects untrusted content and flags likely injection.
Honest finding to aim for: it catches straightforward attacks and **misses obfuscated
variants.** That limitation is a feature of the result, not a failure.

**Layer 2 — Structural (Slot 2).** Does not try to recognize attacks. Removes the agent's
ability to be hijacked. Pick **one** to implement well **[DECIDE]**:
- Separation: the agent never executes instructions found in `CONTENT`, only from `USER`.
- Confirmation: any send requires explicit human approval before it fires.
- Least privilege: the send action is simply unavailable in the context that read untrusted content.

The strong result: "detection missed attack X; the structural layer stopped it anyway."

---

## 5. Open decisions — **[DECIDE]** with the team

1. **Which LLM powers the brain?**
   - Local model (e.g. an Ollama model in the Kali VM): fully self-contained, reproducible
     from the ZIP, no accounts or keys, nothing leaves the sandbox. **Recommended** for a
     security project — it makes the "isolated environment" claim real and the ZIP runnable
     by the grader.
   - Hosted API: easier to get good behavior, but needs a key, costs money, and sends content
     out of the sandbox, which undercuts the isolation story. Only if a local model can't
     follow instructions well enough.
2. **The structural defense** — which of the three in section 4.
3. **Send is stubbed** — confirm `send_email()` logs to a file / local sink and never delivers.
4. **Front end** — build the React visualizer or not. High payoff for the competition vote,
   zero security value. Decide based on time, not points.
5. **Attack delivery** — host the malicious web page on a local server, and provide the
   malicious file directly. Confirm both are served from inside the sandbox.

---

## 6. Evaluation methodology (this is what makes it a *project*, not a demo)

The scientific core is a measured before/after. Define it now:

- **Metric:** attack success rate = (attacks that triggered an unauthorized send) / (attacks tried).
- **Procedure:**
  1. Run the full attack suite against the **baseline** agent (no defenses). Record success rate.
  2. Turn on **detection only.** Re-run. Record.
  3. Turn on **detection + structural.** Re-run. Record.
- **Expected shape of result:** baseline high, detection lower but not zero, detection+structural near zero.
- **Attack suite categories** (Attacker develops these, against our own agent):
  - direct instruction override
  - obfuscated / disguised instructions
  - instructions split across the content
  - content posing as a system or user message
  Organize the suite by category so the results table shows *which* defense stops *which* class.

This table is the centerpiece of both the report and the presentation.

---

## 7. Role ownership (end to end)

Each person owns their code, their report sections, and their part of the demo, so the
contribution section is honest and everyone can answer questions on their own work.

| | Builder (Jas) | Attacker | Defender |
|---|---|---|---|
| Builds | agent, input/action layers, both slots as stubs | attack suite + eval harness | detection + structural defense, front end |
| Owns in report | methodology/implementation, architecture diagram | problem statement, attack results | defense design, before/after results |
| Presents | how the agent works | the attack and why it works | the defenses and the measured outcome |

**Dependency risk:** Builder is the blocker. Ship a minimal agent (one read, one labeled
input, a stubbed send) in week 1 so Attacker and Defender can start. Polish after.

---

## 8. Timeline (today = Oct 12; Exam 2 = Nov 30; term ends Dec 13)

| Week | Builder | Attacker | Defender |
|---|---|---|---|
| 1 (Oct 13–19) | minimal agent + slots stubbed, interface contract written | research attack categories | research defense categories |
| 2 (Oct 20–26) | finish read_webpage/read_file + send stub + source labels | build first attacks vs baseline | design both defense layers |
| 3 (Oct 27–Nov 2) | harden interfaces, support the other two | full attack suite, baseline results | implement detection (slot 1) |
| 4 (Nov 3–9) | freeze the agent interface | re-run vs detection | implement structural (slot 2) + start front end |
| 5 (Nov 10–16) | help integrate | final eval runs, results table | finish front end, before/after |
| ~Nov 17–30 | light — Exam 2 is Nov 30 | write sections | write sections |
| after Exam 2 | assemble report, slides, ZIP; rehearse demo | | |

Interface contract (section 3) must be written and shared in week 1. Changing it later breaks
the other two.

---

## 9. Report section map (structure only — prose is written later, in our own words)

| # | Section | Primary owner |
|---|---|---|
| 1 | Group info | all |
| 2 | Title | all |
| 3 | Introduction (why this topic) | all |
| 4 | Problem statement | Attacker |
| 5 | Methodology / implementation | Builder |
| 6 | Diagram / demonstration | Builder + Attacker |
| 7 | Individual contributions | all |
| 8 | Challenges and solutions | each on their own part |
| 9 | References | all |
| — | AI-use transparency statement | all (see section 11) |

---

## 10. Deliverables checklist (the ZIP)

- [ ] `GroupNumber_FinalProject.zip`
- [ ] All source: agent, attack suite, defenses, eval harness, front end
- [ ] README: what it is, prerequisites (LLM model, libraries), step-by-step run instructions
- [ ] Datasets / sample malicious files and pages used in testing
- [ ] Report (.docx or .pdf) with group number and all member names
- [ ] Slides (.ppt/.pptx/.pdf) with group number and all member names
- [ ] Results table (baseline / detection / detection+structural)

---

## 11. AI use and academic integrity

- The syllabus bars AI from **implementing any portion** of the project. The code is ours.
- Each member must be able to explain their own code and answer questions on it in the demo.
- A transparency statement is required: name any AI tool used and exactly how (e.g. concept
  explanation, planning, this design document), and state that implementation was done by us.
- Using AI to understand prompt injection and defense concepts is permitted; using it to write
  the agent, the attacks, or the defenses is not.
