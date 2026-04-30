"""Classify text chunks by semantic type: definition, derivation, example, equation, text."""

import re

# LaTeX math patterns
MATH_PATTERNS = [
    r"\\begin\{equation\}",
    r"\\begin\{align\}",
    r"\\begin\{eqnarray\}",
    r"\$\$[^$]+\$\$",
    r"\\\[.*?\\\]",
    r"\$[^$]+\$",
    r"\\frac\{",
    r"\\nabla",
    r"\\partial",
    r"\\int",
    r"\\sum",
    r"\\oint",
]

# Patterns suggesting a definition
DEFINITION_PATTERNS = [
    r"\b(?:is defined as|defined as|by definition|we define)\b",
    r"\b(?:Definition[:\s])",
    r"\b(?:A\s+\w+\s+is\s+(?:a|an|the))\b",
    r"\b(?:called\s+(?:a|an|the))\b",
]

# Patterns suggesting a derivation
DERIVATION_PATTERNS = [
    r"\b(?:therefore|hence|thus|consequently|it follows that)\b",
    r"\b(?:substituting|substitute|yields|gives|we obtain|we get)\b",
    r"\b(?:from\s+equation|from\s+Eq\.|using\s+equation)\b",
    r"\b(?:integrating|differentiating|taking\s+the\s+derivative)\b",
    r"\b(?:solving\s+for|rearranging)\b",
]

# Patterns suggesting a worked example
EXAMPLE_PATTERNS = [
    r"\b(?:Example[:\s])",
    r"\b(?:Worked\s+Example)\b",
    r"\b(?:Problem[:\s]\d+)",
    r"^\s*(?:\d+[.)]\s+)",  # Numbered steps
]

# Standalone equation patterns (plain text)
EQUATION_PATTERNS = [
    r"[A-Za-z]\s*=\s*[^=]+\b(?:N|J|W|V|A|T|kg|m|s|C|F|H|Ω)\b",  # F = ma style
    r"\b[A-Z][\w]*\s*['']*\s*=\s*[\d\w\s+\-*/^().,]+",  # Variable = expression
]


def classify_chunk(content: str) -> str:
    """Classify a text chunk into one of: equation, definition, derivation, example, text."""
    # Check for equation-heavy content
    math_score = sum(1 for p in MATH_PATTERNS if re.search(p, content, re.IGNORECASE))
    eq_score = sum(1 for p in EQUATION_PATTERNS if re.search(p, content))

    if math_score >= 2 or eq_score >= 3:
        return "equation"

    # Check for definition
    def_score = sum(
        1 for p in DEFINITION_PATTERNS if re.search(p, content, re.IGNORECASE)
    )
    if def_score >= 1:
        return "definition"

    # Check for example
    ex_score = sum(1 for p in EXAMPLE_PATTERNS if re.search(p, content))
    if ex_score >= 1:
        return "example"

    # Check for derivation
    der_score = sum(
        1 for p in DERIVATION_PATTERNS if re.search(p, content, re.IGNORECASE)
    )
    if der_score >= 2:
        return "derivation"

    return "text"


def classify_query(query: str) -> dict:
    """Classify a user query to guide retrieval weighting.
    Returns dict with booleans for math_query, definition_query, derivation_query.
    """
    math_score = sum(1 for p in MATH_PATTERNS if re.search(p, query, re.IGNORECASE))
    plain_eq = sum(1 for p in EQUATION_PATTERNS if re.search(p, query))

    return {
        "is_math_query": (math_score >= 1 or plain_eq >= 1),
        "is_definition_query": bool(
            re.search(
                r"\b(?:what\s+is|define|definition|meaning\s+of)\b",
                query,
                re.IGNORECASE,
            )
        ),
        "is_derivation_query": bool(
            re.search(
                r"\b(?:derive|derivation|how\s+(?:do|does|is)|show\s+that|prove)\b",
                query,
                re.IGNORECASE,
            )
        ),
    }
