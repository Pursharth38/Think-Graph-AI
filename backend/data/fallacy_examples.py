# OWNED BY: fallacy-backend agent. All other agents READ ONLY (see CLAUDE.md).
"""
ThinkGraph AI — Few-Shot Fallacy Example Bank
=============================================

Curated, hand-written few-shot examples for the Gemini fallacy classifier
(:mod:`app.services.fallacy`). One or more worked examples per
:class:`app.models.graph.FallacyType`, drawn from / modelled on the UCAT /
OC / TSA exam corpus catalogued in ``docs/argument-patterns.md`` §2 and §7.2.

Why this file exists
--------------------
The classifier prompt is *few-shot*: we show the model fully-worked
input→output pairs so it learns (a) the exact JSON shape it must emit and
(b) what a *good*, node-grounded ``explanation`` looks like (one that names
the specific premises/conclusion, not a textbook definition).

Ordering is the priority order from argument-patterns.md §7.2. The two
conditional-logic fallacies — ``affirming_the_consequent`` and
``denying_the_antecedent`` — are by far the most frequent in this exam
domain (each ~15% of logical-inference questions), so they get the richest
coverage (multiple examples each).

Data shape
----------
Each entry is a :class:`FewShotExample` with:
  * ``source_text``  — the raw argument paragraph (what a student sees)
  * ``nodes``        — id → claim text for every node referenced (the graph
                       skeleton the classifier is given)
  * ``fallacy``      — the expected output dict, conforming exactly to the
                       :class:`app.models.graph.Fallacy` schema
                       (``node_ids`` / ``fallacy_type`` / ``explanation`` /
                       ``confidence``).

These are *positive* examples (the fallacy is present). The classifier is
also instructed — see the system prompt — that a structurally valid
argument must return an empty fallacy list, and the bank includes one
explicit NEGATIVE example (``NEGATIVE_EXAMPLE``) to anchor that behaviour.

`confidence` convention (mirrors Fallacy.confidence docstring):
  * >= 0.85 — textbook-clear, the inference is unambiguously fallacious
  * 0.5–0.85 — present but with some interpretive latitude
  * < 0.5   — *latent* / possible: the structure merely risks the fallacy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.graph import FallacyType


@dataclass(frozen=True)
class FewShotExample:
    """One worked input→output pair for the few-shot prompt."""

    fallacy_type: FallacyType
    source_text: str
    nodes: dict[str, str]
    fallacy: dict[str, Any]
    note: str = ""  # human-facing rationale; never sent to the model

    def prompt_input(self) -> dict[str, Any]:
        """The 'INPUT' half shown to the model (no answer leakage)."""
        return {
            "source_text": self.source_text,
            "nodes": [{"id": nid, "text": txt} for nid, txt in self.nodes.items()],
        }

    def prompt_output(self) -> dict[str, Any]:
        """The 'OUTPUT' half — exactly one Fallacy object, schema-shaped."""
        return {"fallacies": [self.fallacy]}


# ---------------------------------------------------------------------------
# 1. affirming_the_consequent  (PRIMARY TARGET — strongest coverage)
# ---------------------------------------------------------------------------
# Form:  P -> Q ;  Q ;  therefore P.   Invalid: Q can hold for other reasons.

AFFIRMING_THE_CONSEQUENT: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.affirming_the_consequent,
        source_text=(
            "Whoever stole the money must have had both an opportunity and a "
            "motive. Finn had both an opportunity and a motive, so Finn must "
            "have stolen the money."
        ),
        nodes={
            "P1": "Whoever stole the money had both an opportunity and a motive. (Rule: Stole -> Opportunity and Motive)",
            "P2": "Finn had both an opportunity and a motive.",
            "C1": "Finn must have stolen the money.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "affirming_the_consequent",
            "explanation": (
                "P1 only establishes that stealing the money REQUIRES opportunity and "
                "motive (Stole -> Opp & Motive). P2 affirms the consequent (Finn has "
                "opportunity & motive), and C1 leaps to 'Finn stole it'. But many "
                "innocent people can also have opportunity and motive, so having them "
                "does not prove Finn is the thief."
            ),
            "confidence": 0.95,
        },
        note="Q3 PT1 — the canonical AC item in this corpus.",
    ),
    FewShotExample(
        fallacy_type=FallacyType.affirming_the_consequent,
        source_text=(
            "Whenever the red light is flashing, it means the processor is "
            "overheating. The processor is overheating, so the red light must "
            "be flashing."
        ),
        nodes={
            "P1": "Whenever the red light flashes, the processor is overheating. (Flashing -> Overheating)",
            "P2": "The processor is overheating.",
            "C1": "The red light must be flashing.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "affirming_the_consequent",
            "explanation": (
                "P1 says flashing implies overheating (Flashing -> Overheating), not the "
                "reverse. P2 affirms the consequent (overheating) and C1 infers the "
                "antecedent (flashing). The processor could be overheating for some "
                "other reason while the light is off, so C1 does not follow from P1 and P2."
            ),
            "confidence": 0.94,
        },
        note="Q27 PT1 family — conditional with 'whenever'.",
    ),
    FewShotExample(
        fallacy_type=FallacyType.affirming_the_consequent,
        source_text=(
            "If it has rained, the grass is wet. The grass is wet this morning, "
            "so it must have rained overnight."
        ),
        nodes={
            "P1": "If it has rained, the grass is wet. (Rain -> WetGrass)",
            "P2": "The grass is wet this morning.",
            "C1": "It must have rained overnight.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "affirming_the_consequent",
            "explanation": (
                "P1 gives Rain -> WetGrass. P2 affirms the consequent (wet grass) and "
                "C1 concludes the antecedent (it rained). Wet grass has other possible "
                "causes — a sprinkler or dew — so observing wet grass cannot establish "
                "that it rained."
            ),
            "confidence": 0.9,
        },
        note="Generic textbook AC, kept for shape coverage.",
    ),
]


# ---------------------------------------------------------------------------
# 2. denying_the_antecedent  (PRIMARY TARGET — strongest coverage)
# ---------------------------------------------------------------------------
# Form:  P -> Q ;  not P ;  therefore not Q.  Invalid: Q may hold without P.

DENYING_THE_ANTECEDENT: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.denying_the_antecedent,
        source_text=(
            "Any student who did not perform in the Spring concert will "
            "definitely be chosen for the Autumn concert. I did perform in the "
            "Spring concert. So that means I definitely won't be chosen for Autumn."
        ),
        nodes={
            "P1": "Any student who did NOT perform in Spring will be chosen for Autumn. (NotSpring -> Autumn)",
            "P2": "I (Jarrah) did perform in the Spring concert. (i.e. NOT NotSpring)",
            "C1": "I definitely will not be chosen for the Autumn concert.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "denying_the_antecedent",
            "explanation": (
                "P1 is one-directional: NotSpring -> Autumn. P2 denies the antecedent "
                "(Jarrah DID perform in Spring) and C1 concludes the negated consequent "
                "(not chosen for Autumn). The rule only promises Autumn to non-performers; "
                "it says nothing about Spring performers, who may still be chosen for "
                "Autumn — so C1 is invalid."
            ),
            "confidence": 0.97,
        },
        note="Q23 PT1 — canonical DA item; matches gold ex_03.",
    ),
    FewShotExample(
        fallacy_type=FallacyType.denying_the_antecedent,
        source_text=(
            "Whenever the red light is flashing, the processor is overheating. "
            "The red light isn't flashing, so the processor must be fine."
        ),
        nodes={
            "P1": "Whenever the red light flashes, the processor is overheating. (Flashing -> Overheating)",
            "P2": "The red light is not flashing. (NOT Flashing)",
            "C1": "The processor must be fine (not overheating).",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "denying_the_antecedent",
            "explanation": (
                "P1 gives Flashing -> Overheating. P2 denies the antecedent (the light is "
                "not flashing) and C1 concludes the negated consequent (processor fine). "
                "The processor could be overheating for a reason that doesn't trigger the "
                "light, so 'no flashing' does not guarantee 'not overheating'."
            ),
            "confidence": 0.95,
        },
        note="Q27 PT1 — Yifan's negation reasoning.",
    ),
    FewShotExample(
        fallacy_type=FallacyType.denying_the_antecedent,
        source_text=(
            "If you study hard, you will pass the exam. Mia did not study hard, "
            "so she will not pass the exam."
        ),
        nodes={
            "P1": "If you study hard, you will pass. (StudyHard -> Pass)",
            "P2": "Mia did not study hard. (NOT StudyHard)",
            "C1": "Mia will not pass the exam.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "denying_the_antecedent",
            "explanation": (
                "P1 states StudyHard -> Pass. P2 denies the antecedent (Mia didn't study "
                "hard) and C1 negates the consequent (she won't pass). Studying hard is "
                "only one sufficient route to passing; Mia might pass anyway (easy exam, "
                "prior knowledge), so C1 does not follow."
            ),
            "confidence": 0.9,
        },
        note="Generic textbook DA for shape coverage.",
    ),
]


# ---------------------------------------------------------------------------
# 3. hasty_generalization
# ---------------------------------------------------------------------------

HASTY_GENERALIZATION: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.hasty_generalization,
        source_text=(
            "At our swimming carnival, six records were broken. Since there were "
            "ten qualifiers, more than half of our qualifiers must be record-breakers."
        ),
        nodes={
            "P1": "Six records were broken at the carnival.",
            "P2": "There were ten qualifiers.",
            "C1": "More than half of the qualifiers must be record-breakers.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "hasty_generalization",
            "explanation": (
                "C1 treats each of the six broken records (P1) as belonging to a distinct "
                "student. But one swimmer can break several records, so the six records in "
                "P1 could have been set by as few as one person. The jump from 'six "
                "records' to 'six different record-breakers, i.e. more than half of ten' "
                "generalises from a count of events to a count of people without warrant."
            ),
            "confidence": 0.85,
        },
        note="Q38 PT1 — Lisa's record-breakers; overlap of categories.",
    ),
    FewShotExample(
        fallacy_type=FallacyType.hasty_generalization,
        source_text=(
            "The two new students from Riverdale are both excellent at chess. "
            "Clearly, everyone from Riverdale is a strong chess player."
        ),
        nodes={
            "P1": "Two new students from Riverdale are excellent at chess.",
            "C1": "Everyone from Riverdale is a strong chess player.",
        },
        fallacy={
            "node_ids": ["P1", "C1"],
            "fallacy_type": "hasty_generalization",
            "explanation": (
                "C1 generalises to the whole population of Riverdale from the tiny, "
                "self-selected sample of two students in P1. Two cases cannot support a "
                "claim about 'everyone', so the inference from P1 to C1 is a hasty "
                "generalization."
            ),
            "confidence": 0.88,
        },
        note="Classic small-sample generalization.",
    ),
]


# ---------------------------------------------------------------------------
# 4. equivocation
# ---------------------------------------------------------------------------

EQUIVOCATION: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.equivocation,
        source_text=(
            "Prizes go to first, second and third place, and there is also a "
            "prize for a hole-in-one. So four different players will get prizes."
        ),
        nodes={
            "P1": "There are prizes for first, second and third place.",
            "P2": "There is also a prize for a hole-in-one.",
            "C1": "Four different players will get prizes.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "equivocation",
            "explanation": (
                "C1 slides from 'four prizes' (the four prize CATEGORIES in P1 and P2) to "
                "'four different players'. The term 'prize-winner' is used in two senses: "
                "a prize slot versus a distinct person. The hole-in-one scorer in P2 may "
                "already be one of the top-three finishers in P1, so the count of people "
                "need not equal the count of prizes."
            ),
            "confidence": 0.8,
        },
        note="Q9 PT1 — golf prizes; conflates prize-slots with distinct people.",
    ),
    FewShotExample(
        fallacy_type=FallacyType.equivocation,
        source_text=(
            "Cricket is the most popular sport in the country, and popularity is "
            "what produces champions. So our national cricket team is bound to "
            "dominate the world."
        ),
        nodes={
            "P1": "Cricket is the most popular sport in the country (widely watched and followed).",
            "P2": "Popularity is what produces champions.",
            "C1": "The national cricket team will dominate the world.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "equivocation",
            "explanation": (
                "'Popularity' shifts meaning between the premises. In P1 it means cultural "
                "saturation (how many people watch/follow). In P2 the causal claim only "
                "works if 'popularity' means competitive participation and selection "
                "pressure. C1 trades on the ambiguity, treating audience size as if it "
                "were the kind of popularity that builds champions."
            ),
            "confidence": 0.7,
        },
        note="docx Q5 — 'popularity' used in two senses.",
    ),
]


# ---------------------------------------------------------------------------
# 5. false_dichotomy
# ---------------------------------------------------------------------------

FALSE_DICHOTOMY: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.false_dichotomy,
        source_text=(
            "What is the point in spending time learning things when you can just "
            "look them up online? Schools should stop making students memorise facts."
        ),
        nodes={
            "P1": "You can look facts up online whenever you need them.",
            "C1": "Schools should stop making students memorise facts (learning vs looking-up is the only choice).",
        },
        fallacy={
            "node_ids": ["P1", "C1"],
            "fallacy_type": "false_dichotomy",
            "explanation": (
                "The argument frames only two options — memorise facts yourself, or look "
                "them up online (P1) — and concludes for the second (C1). It ignores a "
                "third possibility: a base of memorised knowledge is what lets you "
                "interpret, evaluate and even search the online information meaningfully. "
                "The two options are not exhaustive, so C1 is unwarranted."
            ),
            "confidence": 0.82,
        },
        note="Q35 PT1 — memorise vs look-up false either/or.",
    ),
    FewShotExample(
        fallacy_type=FallacyType.false_dichotomy,
        source_text=(
            "Either we ban all cars from the streets near the school, or children "
            "will keep getting hurt. We obviously can't accept children getting "
            "hurt, so all cars must be banned."
        ),
        nodes={
            "P1": "Either ban all cars near the school, or children will keep getting hurt.",
            "P2": "We cannot accept children getting hurt.",
            "C1": "All cars must be banned from streets near the school.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "false_dichotomy",
            "explanation": (
                "P1 presents a total ban and 'children keep getting hurt' as the only two "
                "outcomes. Combined with P2, this forces C1. But there are intermediate "
                "measures — speed limits, crossings, traffic wardens, drop-off zones — "
                "that could reduce harm without a full ban, so the either/or in P1 is false."
            ),
            "confidence": 0.85,
        },
        note="Q14-style — banning cars; ignores intermediate measures.",
    ),
]


# ---------------------------------------------------------------------------
# 6. slippery_slope
# ---------------------------------------------------------------------------

SLIPPERY_SLOPE: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.slippery_slope,
        source_text=(
            "The birth rate in several rich countries is falling, while older "
            "people there are living longer. By allowing birth rates to fall so "
            "much, these countries are storing up a serious social crisis for the "
            "future."
        ),
        nodes={
            "P1": "Birth rates in rich countries are falling.",
            "P2": "Older people there are living longer.",
            "SC1": "There will be more elderly needing care and fewer young people to provide it.",
            "C1": "These countries are storing up a serious future social crisis.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "SC1", "C1"],
            "fallacy_type": "slippery_slope",
            "explanation": (
                "The argument chains P1 and P2 through SC1 to the dramatic C1 (a 'serious "
                "social crisis') as if each step were inevitable. It never checks whether "
                "the intermediate steps must follow — immigration, automation, or policy "
                "could absorb the care burden in SC1 — so the slide from falling birth "
                "rates to crisis is asserted rather than established."
            ),
            "confidence": 0.6,
        },
        note="Q20 PT1 — latent slippery slope (note confidence in 0.5-0.85 band).",
    ),
    FewShotExample(
        fallacy_type=FallacyType.slippery_slope,
        source_text=(
            "If we let students retake one test, they'll demand to retake every "
            "test, then no one will ever take exams seriously, and eventually the "
            "whole school's standards will collapse."
        ),
        nodes={
            "P1": "We allow students to retake one test.",
            "SC1": "Students will demand to retake every test.",
            "SC2": "No one will take exams seriously.",
            "C1": "The whole school's standards will collapse.",
        },
        fallacy={
            "node_ids": ["P1", "SC1", "SC2", "C1"],
            "fallacy_type": "slippery_slope",
            "explanation": (
                "Each link — from one retake (P1) to demanding all retakes (SC1) to no one "
                "taking exams seriously (SC2) to total collapse (C1) — is presented as "
                "automatic. No reason is given why the first concession forces the next, so "
                "the cascade to C1 is an unsupported slippery slope."
            ),
            "confidence": 0.85,
        },
        note="Textbook multi-step slope; high confidence (explicit chain).",
    ),
]


# ---------------------------------------------------------------------------
# 7. circular_reasoning
# ---------------------------------------------------------------------------
# NOTE: Tier-1 of the classifier also detects circularity structurally from
# graph cycles; these few-shots cover the semantic ("restates the conclusion")
# variant that has no literal edge cycle.

CIRCULAR_REASONING: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.circular_reasoning,
        source_text=(
            "Schools should be held responsible when students do poorly, because "
            "the whole purpose of a school is to make sure its students do well."
        ),
        nodes={
            "P1": "The purpose of a school is to ensure its students do well.",
            "C1": "Schools should be held responsible when students do poorly.",
        },
        fallacy={
            "node_ids": ["P1", "C1"],
            "fallacy_type": "circular_reasoning",
            "explanation": (
                "P1 ('a school's purpose is to make sure students do well') simply restates "
                "C1 ('schools are responsible for poor performance') in different words. The "
                "premise assumes the very institutional responsibility it is supposed to "
                "prove, so P1 offers no independent support for C1."
            ),
            "confidence": 0.65,
        },
        note="docx Q4 — premise restates conclusion (no literal cycle).",
    ),
    FewShotExample(
        fallacy_type=FallacyType.circular_reasoning,
        source_text=(
            "This rule must be obeyed because it is the rule, and rules are there "
            "to be obeyed."
        ),
        nodes={
            "P1": "Rules are there to be obeyed.",
            "C1": "This rule must be obeyed.",
        },
        fallacy={
            "node_ids": ["P1", "C1"],
            "fallacy_type": "circular_reasoning",
            "explanation": (
                "C1 ('this rule must be obeyed') is justified by P1 ('rules are there to be "
                "obeyed'), which is just the general form of the same claim. The argument "
                "assumes its conclusion as its premise, providing no reason beyond the "
                "conclusion itself."
            ),
            "confidence": 0.8,
        },
        note="Textbook 'begging the question'.",
    ),
]


# ---------------------------------------------------------------------------
# 8. straw_man
# ---------------------------------------------------------------------------

STRAW_MAN: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.straw_man,
        source_text=(
            "Kenny: We should teach children some basic self-defence so they feel "
            "safer. Anna: I can't believe Kenny wants to turn our playground into a "
            "fight club where kids beat each other up. That's a terrible idea."
        ),
        nodes={
            "P1": "Kenny proposes teaching children basic self-defence so they feel safer.",
            "P2": "Anna restates the proposal as 'turning the playground into a fight club where kids beat each other up'.",
            "C1": "Anna concludes the proposal is a terrible idea.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "straw_man",
            "explanation": (
                "Anna's C1 attacks P2 — a distorted, worst-case caricature ('a fight club "
                "where kids beat each other up') — rather than Kenny's actual proposal in "
                "P1 (basic self-defence for safety). By refuting the exaggerated version "
                "instead of the real one, she commits a straw man."
            ),
            "confidence": 0.8,
        },
        note="docx Q12 — self-defence proposal distorted.",
    ),
]


# ---------------------------------------------------------------------------
# 9. ad_hominem
# ---------------------------------------------------------------------------

AD_HOMINEM: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.ad_hominem,
        source_text=(
            "Priya argued that the new bus route would cut traffic. But Priya "
            "failed her maths exam last year, so there's no reason to take her "
            "argument seriously."
        ),
        nodes={
            "P1": "Priya argues the new bus route would cut traffic.",
            "P2": "Priya failed her maths exam last year.",
            "C1": "Priya's argument should not be taken seriously.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "ad_hominem",
            "explanation": (
                "C1 dismisses Priya's claim in P1 by pointing to an irrelevant personal "
                "fact in P2 (she failed a maths exam). Her exam result has no bearing on "
                "whether the bus route reduces traffic, so attacking Priya rather than her "
                "argument is an ad hominem."
            ),
            "confidence": 0.85,
        },
        note="Distractor-style ad hominem (rare in corpus; §2 rank 9).",
    ),
]


# ---------------------------------------------------------------------------
# 10. tu_quoque
# ---------------------------------------------------------------------------

TU_QUOQUE: list[FewShotExample] = [
    FewShotExample(
        fallacy_type=FallacyType.tu_quoque,
        source_text=(
            "Dad told me I shouldn't stay up late because it's bad for my health. "
            "But Dad stays up late all the time, so his advice is worthless."
        ),
        nodes={
            "P1": "Dad argues that staying up late is bad for your health.",
            "P2": "Dad himself stays up late all the time.",
            "C1": "Dad's advice is worthless and can be ignored.",
        },
        fallacy={
            "node_ids": ["P1", "P2", "C1"],
            "fallacy_type": "tu_quoque",
            "explanation": (
                "C1 rejects the claim in P1 (staying up late harms health) purely because "
                "the speaker is guilty of the same behaviour in P2. Dad's own habits do "
                "not change whether the health claim is true, so dismissing it on 'you do "
                "it too' grounds is a tu quoque."
            ),
            "confidence": 0.85,
        },
        note="Distractor-style tu quoque (very rare in corpus; §2 rank 10).",
    ),
]


# ---------------------------------------------------------------------------
# Negative anchor — a valid argument with NO fallacy.
# ---------------------------------------------------------------------------
# Included so the classifier learns to return an empty list rather than
# hallucinate a fallacy in sound arguments (e.g. Type E constraint args,
# valid modus tollens, the wind-farm argument once A1 is granted).

NEGATIVE_EXAMPLE: dict[str, Any] = {
    "source_text": (
        "Whoever stole the money must have had both an opportunity and a motive. "
        "Sam had no motive at all, so Sam cannot have stolen the money."
    ),
    "nodes": [
        {"id": "P1", "text": "Whoever stole the money had opportunity and motive. (Stole -> Opp & Motive)"},
        {"id": "P2", "text": "Sam had no motive."},
        {"id": "C1", "text": "Sam cannot have stolen the money."},
    ],
    "fallacies": [],
    "note": (
        "Valid modus tollens via the contrapositive (no motive -> not the thief). "
        "Demonstrates the correct EMPTY-list output for a sound argument."
    ),
}


# ---------------------------------------------------------------------------
# Aggregation — priority order from argument-patterns.md §7.2.
# ---------------------------------------------------------------------------

EXAMPLES_BY_TYPE: dict[FallacyType, list[FewShotExample]] = {
    FallacyType.affirming_the_consequent: AFFIRMING_THE_CONSEQUENT,
    FallacyType.denying_the_antecedent: DENYING_THE_ANTECEDENT,
    FallacyType.hasty_generalization: HASTY_GENERALIZATION,
    FallacyType.equivocation: EQUIVOCATION,
    FallacyType.false_dichotomy: FALSE_DICHOTOMY,
    FallacyType.slippery_slope: SLIPPERY_SLOPE,
    FallacyType.circular_reasoning: CIRCULAR_REASONING,
    FallacyType.straw_man: STRAW_MAN,
    FallacyType.ad_hominem: AD_HOMINEM,
    FallacyType.tu_quoque: TU_QUOQUE,
}

#: Flat, priority-ordered list of every positive example. The prompt builder
#: walks this so the two conditional fallacies appear first / most often.
ALL_EXAMPLES: list[FewShotExample] = [
    ex for ftype in EXAMPLES_BY_TYPE for ex in EXAMPLES_BY_TYPE[ftype]
]

#: Snake_case taxonomy string list, for injecting into the prompt.
TAXONOMY: list[str] = [ftype.value for ftype in EXAMPLES_BY_TYPE]


def iter_examples() -> list[FewShotExample]:
    """Return every positive few-shot example in priority order."""
    return list(ALL_EXAMPLES)
