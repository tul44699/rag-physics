SYSTEM_PROMPT = """\
You are a physics tutor. Answer using only the Source Material below. \
{profile_context}

Rules:
1. Write all math inside \\(...\\) (inline) or $$...$$ (display). \
Never use Unicode math — write \\sqrt not √, \\rho not ρ, \\partial not ∂. \
Use _ for subscripts: \\(F_{{net}}\\) not \\(F{{net}}\\). \
Do not nest \\( inside \\(.
2. Every claim must cite a source. If the context does not cover the question, \
say what is missing instead of guessing.
3. Do not make up equations, numbers, or references.
4. Cite with [N] in the text, then list [N] textbook_name p.page_number in a \
Sources section. Copy names and page numbers exactly from the Source Material.
5. Only answer physics questions. Redirect everything else."""


def build_profile_context(profile: dict, understanding_level: str | None = None) -> str:
    level = understanding_level or profile.get("understanding_level", "intermediate")
    parts = [f"The student is at a {level} level."]
    course = profile.get("course")
    if course:
        parts.append(f"Course: {course}.")
    weaknesses = profile.get("weak_areas")
    if weaknesses:
        parts.append(f"Weak areas: {', '.join(weaknesses[:3])}.")
    style = profile.get("learning_style")
    if style:
        parts.append(f"Style: {style}.")
    return " ".join(parts)


def build_system_prompt(profile: dict, understanding_level: str | None = None) -> str:
    return SYSTEM_PROMPT.format(
        profile_context=build_profile_context(profile, understanding_level)
    )


TASK_INSTRUCTIONS = {
    "qa": (
        "Explain the concept step by step, from fundamentals to specifics. "
        "Use an example if helpful."
    ),
    "lookup": "Answer in one sentence. No explanation.",
    "flashcards": (
        "Create exactly 6 flashcards from the most important concepts. "
        "Every front must be a question ending with ?. Every back must be a short answer. "
        "Include source_n with the [N] number from the Source Material used for each card. "
        "Cover material from all sources, not just one section."
    ),
    "study_guide": (
        "Create a study guide covering key concepts, important equations "
        "with explanations, common mistakes, and practice questions with answers."
    ),
    "chapter_summary": (
        "Summarize the chapter: core concepts, essential formulas, and common mistakes."
    ),
    "follow_up": (
        "This is a follow-up. Answer directly based on the conversation above. "
        "Do not repeat the full format from earlier — be conversational."
    ),
}


def get_task_instructions(task: str) -> str:
    return TASK_INSTRUCTIONS.get(task, TASK_INSTRUCTIONS["qa"])


def build_user_prompt(
    prompt: str,
    task: str,
    context: str,
    eq_context: str,
    history_text: str,
) -> str:
    parts: list[str] = []

    if history_text.strip():
        parts.append(f"## Conversation\n{history_text}")

    instruction = get_task_instructions(task)
    parts.append(f"## Task\n{instruction}")

    if context.strip():
        parts.append(f"## Source Material\n{context}")

    if eq_context.strip():
        parts.append(eq_context)

    parts.append(f"## Question\n{prompt}")

    return "\n\n".join(parts)
