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

The session context for this tutoring session has been provided above. Use it throughout all analysis to distinguish lesson-induced errors from genuine student weaknesses and to interpret student behavior in the context of how this session was structured.
Your task is to analyze the tutoring data provided and produce a structured HTML report. The primary level of detail must be sufficient for a different tutor — one who has never worked with this student — to fully understand the student's problems and the tutor's solutions on both a strategic and tactical level. Each strategic section must also include a brief parent-facing distillation that simplifies the concepts for a non-technical audience with no mathematical background.

DEFINITIONS — USE THESE EXACTLY
Strategy: Your overarching plan and direction to achieve a specific goal — the "what" and the "why."
Tactic: The specific, short-term actions and executions you take to implement that strategy — the "how."
Error origin:
Organic: The error reflects a genuine, pre-existing student habit, reasoning gap, or comprehension pattern. It would appear regardless of whether a new technique had been introduced at that point in the session. Highest-priority signal for coaching.
Lesson-Induced: The error occurred because a specific technique, concept, or piece of information had not yet been taught at that point in the session. The mistake was expected by the lesson design and does not on its own indicate a persistent student weakness.
Mixed: The root error is lesson-induced, but the moment contains a genuine sub-component — a behavior the student exhibited that would persist even if the technique were known. Always extract and label the genuine sub-component separately within the tactical card.
Evidence source:
Student Side: What the student said or did that revealed the problem — their direct output, statement, or behavior.
Tutor Diagnostic: What the tutor said or did after observing the student's output — how the tutor identified, named, or probed the problem before introducing a solution.
Tutor Setup: Applies to lesson-induced errors only. What the tutor deliberately structured or withheld so the student would encounter a predictable failure point.
Evidence type:
Observable: Directly quoted or closely paraphrased from the data. The behavior or statement is on the record.
Inference: Derived from surrounding context — the tutor's framing, lesson structure, word choice, or sequencing — rather than a direct statement. When using inference, always cite the specific observable fact that supports it and label it clearly.

EVIDENCE SOURCES — DRAW FROM ALL THREE
When identifying strategic issues and their tactical instances, draw simultaneously from:
In-session errors and struggles — moments where the student got something wrong, expressed confusion, gave an incorrect answer, or demonstrated a gap.
Student behavioral signals — reactions to questions, self-assessments, expressions of confidence or limitation, emotional responses, moments of hesitation or complete cessation of effort.
Tutor structural and framing choices — how the tutor sequenced the lesson, what the tutor's justification for each technique reveals about prior student weaknesses, how the tutor framed the value of each method, what problems the lesson was designed to address before the session began.
Do not limit analysis to in-session errors only. Behavioral signals and tutor framing are equally valid diagnostic evidence.

ANALYSIS PROCESS
Step 1 — Identify strategic issues.
A strategic issue is a pattern of related problems sharing the same underlying root — a recurring habit, gap, or belief that explains multiple specific instances. Name and define each strategic issue precisely. There is no fixed number; identify as many as the data supports.
For each strategic issue:
Strategic Problem: Define the overarching issue, its scope, and the evidence that it exists. Cite evidence from all three sources above. Label each piece of evidence as observable or inference.
Strategic Solution: Describe what the tutor did at a systemic level to address this issue — not individual fixes, but the overarching approach. Be specific about actual tutor actions, framing choices, and sequencing decisions. If the session contains no strategic solution for a given issue, note that explicitly.
Parent Distillation: A plain-English summary of this strategic issue and its solution for a non-technical parent audience. No jargon, no timestamps, no badges. Use analogies where helpful.
Step 2 — For each strategic issue, identify tactical problems.
A tactical problem is a specific, discrete instance that is evidence of the overarching strategic issue. For each:
State the tactical problem precisely.
Classify its error origin: organic, lesson-induced, or mixed.
If mixed: identify and separately flag the genuine sub-component within the card.
Student-side evidence: What the student said or did. Quote or closely paraphrase with timestamp or location reference.
Tutor-side evidence: For organic errors, cite the tutor's diagnostic response (what the tutor said or did after observing the error, before the solution). For lesson-induced errors, cite the tutor's setup (what the tutor deliberately structured or withheld). Include both if both are present.
Label all evidence as observable or inference.
Tactical solution: What specific action did the tutor take to address this instance? Describe the exact technique, explanation, or demonstration — not a generic summary.
For observable evidence: focus on input/output behavior — what the student or tutor said or did. Do not explain why unless inference is required.
For inferred evidence: cite the specific observable fact that supports the inference and state the inferential step explicitly.

OUTPUT FORMAT
Produce a complete, self-contained HTML file. The visual design must follow this hierarchy:
Page level: Clean off-white background. Maximum-width centered container. Serif body font for prose; sans-serif for labels, badges, and metadata.
Title block: Report title and session metadata (subject, student name if available, speaker roles, session duration if available) at the top of the page.
Label key: Immediately after the title, before any analysis. Displayed as a multi-column grid — one column per badge category. Three categories: Error Origin, Evidence Source, Evidence Type. Each badge is shown with its color and a full definition sentence explaining how that label is decided and when it is used. Badges are small, pill-shaped, color-coded inline labels. Each category uses a distinct color family; badges within a category are visually distinct from each other. The key must be complete enough that a reader encountering the report cold can understand every label without external reference.
Strategic issue sections: Each begins with a full-width, visually prominent section header (dark background, light text) that clearly separates it from adjacent sections. Inside each section, in order:
Strategic Problem block — warm-tinted background (light orange/amber), colored left border. Contains the strategic problem definition and all supporting evidence with badges.
Strategic Solution block — cool-tinted background (light green), colored left border. Contains the tutor's systemic response, specific and detailed.
Parent Distillation box — visually distinct from the tutor-level content above. Dashed or dotted border, different tint (light blue). Clearly labeled (e.g., "FOR PARENT COMMUNICATION"). Plain English only — no badges, no timestamps, no jargon.
Tactical group — a labeled sub-section below the parent box, containing all tactical cards for this strategic issue.
Tactical cards: Each tactical problem is its own bordered card. Card header contains the tactical problem title and origin badge; the header is visually distinct from the card body (e.g., lightly shaded). Card body contains, in order:
Student-side evidence row: source badge + evidence type badge + italic quote block with timestamp + brief contextual note if needed.
Tutor-side evidence row(s): source badge (diagnostic or setup) + evidence type badge + quote or description.
Sub-component block if mixed: amber/yellow tint, clearly labeled "Genuine Sub-Component."
Tactical solution block: green tint, colored left border, labeled "Tactical Solution." Contains the specific technique or action the tutor used.
Quote blocks: Italic text, subtle left border, slightly shaded background. Timestamps inline in lighter monospace style.
Footer: Repeat session metadata. Note that all claims are cited and all evidence is labeled.

CONTENT AND QUALITY REQUIREMENTS
Prefer more information over less. If a tactical moment has multiple dimensions, include all of them.
Every claim must be supported by cited evidence. Never make an assertion without pointing to a specific moment in the data.
Do not collapse distinct tactical problems into one because they share surface similarity. Each discrete instance deserves its own card.
Do not limit tactical problems to moments where the student made an explicit error. Include moments that reveal a strategic pattern through behavioral signals or tutor framing, even if no error occurred.
Strategic solutions must be specific: describe exactly what the tutor did, not the general category of intervention.
Parent distillations must be genuinely simplified — no technical terms, no timestamps, no badges. Accessible to someone with no mathematical or pedagogical background.
For observable evidence: describe what happened (input and output). Do not editorialize about why unless inference is needed.
For inferential evidence: always cite the specific observable fact the inference is drawn from, state the inferential step, and label it as inference.
The report must be detailed enough that a different tutor who has never worked with this student could read it and immediately understand: what the student's strategic problems are, which specific instances demonstrate each problem, what the original tutor did to address each problem at both the strategic and tactical level, and which student behaviors are genuine patterns versus artifacts of the lesson design.

Output ONLY the raw HTML — no markdown code fences, no preamble, no explanation. Start with <!DOCTYPE html> and end with </html>."""
