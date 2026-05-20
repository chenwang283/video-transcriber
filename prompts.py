"""Prompts for the two-call Claude pipeline."""

PART_1_PROMPT = """The following is a piece of educational content — it may be a session transcript, mp4, slide deck, or other format. Before any problem or pattern analysis is performed, your only job here is to read it and produce a completed Session Context block that accurately describes what kind of session this is and how it is structured.
Analyze the content and answer the following questions. For each answer, cite specific evidence from the content that led you to that conclusion — quote or closely paraphrase where possible. If evidence is insufficient to answer a question confidently, say so explicitly rather than guessing.
Questions to answer:
Session type — Which of the following best describes this session, and why?
Concept/lecture: tutor or video explains and demonstrates foundational material with little to no student problem-solving
Technique introduction: tutor introduces a specific tool, method, or shortcut and demonstrates it on examples
Practice and correction: student attempts problems, tutor corrects errors and thought process, student reattempts
Mixed: combines more than one of the above — describe the breakdown and sequence
Session goal — What was the explicit purpose of this session? What was the student supposed to be able to do by the end that they couldn't do at the start?
Content domain — What subject and specific topic does this session cover?
Pedagogical flow — How does the session move? Describe the sequence of what happens (e.g., tutor explains → student tries → tutor corrects → student reattempts, or tutor demos → student observes → student tries independently).
Deliberate error structure — At any point, does the session intentionally allow or encourage the student to attempt something with incomplete information, make an error, and then use that error as a teaching moment? If yes: at what points does this happen, what information was withheld, and what was the student expected to get wrong?
Error interpretation rule — Given the structure you identified, how should student errors be interpreted during analysis? Which errors are likely lesson-induced by design, and which are more likely to reflect genuine underlying student weaknesses?
Known student baseline — Does the content reveal anything about what the tutor already knew about the student's weaknesses or gaps before the session started? This may appear in how the tutor frames problems, what they choose to emphasize, or explicit comments about past performance.
Output: Compile your answers into a single Session Context block written in plain prose, clearly organized by the seven points above. This block will be passed directly into a subsequent prompt for problem and pattern analysis — write it to be self-contained and specific enough that someone with no access to the original content can use it to accurately interpret student behavior during analysis."""


PART_2_PROMPT_TEMPLATE = """This session follows a deliberate pedagogical structure: [session context input]

# SAT Tutoring Session Report — Generator Prompt

The session context for this tutoring session has been provided above. Use it throughout all analysis to tell the difference between lesson-induced errors and real student weaknesses, and to read student behavior in light of how the session was structured.

---

## Who this report is for

A parent or a video creator who has never tutored. They need to understand:
- What the student was doing wrong before the session
- Why it was wrong
- What the tutor changed
- Whether the change worked

If a tutor needs more detail later, the citations make the report fact-checkable. But the report itself must read cleanly to someone with zero tutoring background.

---

## Style rules (non-negotiable)

**1. 6th grade reading level.**
If you must use an SAT-specific term (Command of Evidence, inference, Bluebook, Test Innovators, transposon, etc.), define it in plain English the first time you use it. Example: *"Command of Evidence questions ask the student to pick the line of text that best supports a claim."*

**2. Concrete over abstract.**
Replace vague words with what they actually look like in behavior.
- Bad: "The student struggles with focus."
- Good: "The student picks the first answer that sounds right instead of checking the rest."
- Bad: "The student lacks confidence in elimination."
- Good: "The student keeps wrong answers on the table instead of crossing them out."

**3. Short. Active. Direct.**
- Short sentences. Short paragraphs.
- Active voice. ("The tutor stopped the student" — not "The student was stopped by the tutor.")
- No hedging: cut "may have," "seems to," "potentially," "arguably."
- No filler: if a sentence doesn't change what the reader understands, delete it.

**4. No academic jargon.**
Cut: synthesis, metacognition, comprehension, scaffolding, engagement, automaticity. Say what actually happened instead.

**5. One example per slot unless a second adds new information.**
A second example only earns its place if it shows a different failure mode, a different question type, or a different aspect of the same issue. If two examples say the same thing in different words, pick the more relevant one and drop the other. 

**6. Neutral pronouns.**
Refer to the student as "the student" or "they/them/their." Do not assume gender. This applies to every sentence in the output, including the examples inside tactical cards.

**7. Full context.**
Any analysis done by an AI for examples, strategic problems, tactical problems, tutor-introduced solutions, etc. should provide enough context so that anyone reading this can understand the tutoring done and the implications of the problems/solutions. 
---

## Definitions (use these exactly)

**Strategic problem** — A pattern the student does across many questions. The "what they're doing wrong" at a high level.

**Tactical problem** — One specific moment in the session that shows the strategic problem.

**Strategic solution** — The new process the tutor taught to fix the pattern.

**Tactical example (of solution)** — One specific moment where the student used the new process.

### Error origin (badges)
- **Organic** — The student would have made this error even if the tutor had never said anything. It's a real habit or gap. This is the highest-priority signal.
- **Lesson-Induced** — The student made this error because the tutor hadn't taught the fix yet. The tutor expected it. It does not mean the student has a deep weakness.
- **Mixed** — Mostly lesson-induced, but with a real sub-problem inside it. Call out the real sub-problem separately.

### Evidence source (badges)
- **Student Side** — Something the student said or did.
- **Tutor Diagnostic** — Something the tutor said or did *after* seeing the student's mistake, to name or probe it.
- **Tutor Setup** — Something the tutor deliberately structured or held back so the student would predictably stumble. Only used for lesson-induced errors.

### Evidence type (badges)
- **Observable** — Directly quoted or closely paraphrased from the transcript. On the record.
- **Inference** — Read from context (tutor framing, sequencing, word choice). When using this, cite the specific observable fact it's based on and say what the inferential step is.

---

## How to find strategic issues

A strategic issue is a pattern. To find one, look for the same root habit showing up in two or more places in the transcript. The root can show up as:
1. An in-session error or wrong answer.
2. A behavior signal — hesitation, "I don't know," holding on to a wrong answer, jumping to the answer choices, etc.
3. A tutor framing choice — what the tutor chose to teach first, a tutor-flagged prior weakness, what the tutor demonstrated instead of letting the student try.

Use all three. Don't only count moments where the student wrote a wrong letter on the page.

---

## Output structure (follow exactly)

Output a markdown file. Use the structure below. Do not add extra sections. Do not rename headers.

```
# SAT [Subject] Session Report

**Student:** [name or "Not stated"]
**Date:** [date or "Not stated"]
**Duration:** [duration or "Not stated"]
**Topics covered:** [comma-separated list]

---

## Label key

**Error origin** — `Organic` (real habit) · `Lesson-Induced` (expected by lesson) · `Mixed` (lesson-induced with a real sub-problem inside)

**Evidence source** — `Student Side` (student said/did) · `Tutor Diagnostic` (tutor named the problem after seeing it) · `Tutor Setup` (tutor planned the stumble)

**Evidence type** — `Observable` (quoted/paraphrased from transcript) · `Inference` (read from context — must cite the observable fact behind it)

---

## Strategic Issue 1: [Name]

### 1. Before — How the student was solving these questions

[A bullet list describing the student's default process — what they actually did, step by step, before the tutor stepped in. 3–5 bullets. One short sentence each. Just the steps. No judgment yet. *Style: 6th grade reading level. Define any SAT term the first time you use it. Neutral pronouns ("the student" / "they"). No hedging words.*]

### 2. Why that default doesn't work

[One sentence stating the core failure in plain English.  *6th grade reading level wording. Concrete behavior, not abstract nouns. No hedging.*]

**Example: [short label for the moment]**
`Origin: [badge]`

- **Student Side** · `[Observable | Inference]`
  > *"[direct quote]"* `[timestamp]`
  [One sentence of context if needed. *Neutral pronouns. No hedging.*]

- **Tutor Diagnostic** (or **Tutor Setup**) · `[Observable | Inference]`
  > *"[direct quote]"* `[timestamp]`
  [One sentence of context if needed. *Neutral pronouns. No hedging.*]

- **Genuine sub-component** (only if origin is Mixed)
  [One paragraph naming the real sub-problem inside this mostly-lesson-induced moment. *Concrete behavior, not abstract nouns.*]

[Only add a second example if it shows a different failure mode, different question type, or different aspect. Otherwise stop here.]

### 3. What the tutor changed

[A numbered list of the steps in the new process the tutor taught. These steps for the new process should be generalizable for every tactical example found under each strategic issue; a strategic solution. Each step is one short sentence. Include every distinct step the tutor specified — no more, no less. *6th grade level wording. Active voice. Define any SAT term the first time it appears here if not already defined above.*]

### 4. After — The student using the new process

**Example: [short label for the moment]**

- **Student Side** · `[Observable | Inference]`
  > *"[direct quote]"* `[timestamp]`
  [One short sentence of what changed in their process compared to the Before. *6th grade. Neutral pronouns. Show the change, don't just claim it. No hedging.*]

- **Tutor Diagnostic** · `[Observable | Inference]`
  > *"[direct quote]"* `[timestamp]`
  [One short sentence of context if needed. *Neutral pronouns. No hedging.*]

[Only add a second example if it adds new information. If the session contains no example of the student using the solution successfully, write exactly: *"The session did not contain a clear example of the student applying this solution on their own."* Do not invent one.]

---

## Strategic Issue 2: [Name]

[Same four-part structure.]

---

[Repeat for each strategic issue. Order strategic issues by how much of the session they took up — the biggest one first.]

---

## Footer

**Student:** [name] · **Date:** [date] · **Duration:** [duration]

All quotes are cited with timestamps from the transcript.
```

---

## Citation format

Every quote uses this exact format:

> *"the quoted words"* `[MM:SS]` or `[HH:MM:SS]`

- Italic for the quote.
- Backtick-wrapped timestamp right after the closing quote mark.
- Use the timestamp from the transcript. If the transcript uses a different time format, match it.
- Closely paraphrase only when a direct quote would be too long. Mark paraphrases by dropping the italics but keeping the timestamp.

---

## Quality bar

Before you submit, check each of these:

1. **Every claim is cited.** Every "the student did X" or "the tutor said Y" has a quote or paraphrase with a timestamp.
2. **No claim without evidence.** If you can't cite it, cut it.
3. **One example per slot unless a second adds new information.** Re-read your tactical examples. If two say the same thing, delete the weaker one.
4. **6th grade reading level.** Read each sentence out loud. If a 12-year-old wouldn't follow it, rewrite it.
5. **Every SAT-specific term is defined the first time.** Search the document for jargon. Define or replace.
6. **Before and After are clearly different.** The reader should be able to look at section 1 and section 4 and see what changed in the student's process. If they look the same, you haven't shown the change.
7. **Lesson-induced vs. organic is honest.** Per the session context's error interpretation rule, don't label a lesson-induced stumble as organic. Don't label a real weakness as lesson-induced just because it came up after a strategy was taught.
8. **Neutral pronouns throughout.** Search for "she," "her," "he," "his," "him." Replace with "the student" or "they/them/their." No exceptions.
9. **If a section is short, leave it short.** Don't pad. A real session has uneven sections.

---

## Things to avoid

- **No "For Parent Communication" callout boxes.** The whole report is parent-readable.
- **No vague nouns** (engagement, focus, comprehension, synthesis, confidence). Replace with the specific behavior. "Confidence" → "the student crosses out wrong answers and commits."
- **No hedging** ("may have," "seems," "potentially," "arguably"). State what the evidence shows.
- **No invented examples.** If the session didn't show the student using the solution, say so. Do not fabricate an "After" moment.
- **No collapsing distinct tactical moments into one.** If two moments are genuinely different, they each get their own example block — subject to the "second example must add new information" rule.
- **No editorializing observable evidence.** For observable evidence, describe input and output. Save the "why" for inferences, and label them. """