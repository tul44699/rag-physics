import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from embedding import embed_text

LATEX_PATTERNS = [
    (r"\\begin\{equation\*?\}(.+?)\\end\{equation\*?\}", True),
    (r"\\begin\{align\*?\}(.+?)\\end\{align\*?\}", True),
    (r"\$\$(.+?)\$\$", True),
    (r"\\\[(.+?)\\\]", True),
    (r"\$(.+?)\$", False),
]

_PHYSICS_VARS = {
    "F",
    "m",
    "a",
    "v",
    "t",
    "x",
    "E",
    "B",
    "q",
    "I",
    "V",
    "R",
    "C",
    "L",
    "P",
    "U",
    "K",
    "W",
    "T",
    "p",
    "ρ",
    "ε",
    "μ",
    "σ",
    "λ",
    "ω",
    "φ",
    "ψ",
    "π",
    "θ",
    "r",
    "J",
    "H",
    "D",
    "A",
    "S",
    "N",
    "n",
    "k",
    "G",
    "g",
    "h",
    "∇",
    "∂",
    "Ω",
}

_GARBAGE_PATTERNS = [
    re.compile(r"^\d+\s*=\s*\d+$"),
    re.compile(r"^[A-Z]\s*=\s*\d+\s*[A-Z]?$"),
    re.compile(r"^t\s*=\s*\d+\s*s$"),
    re.compile(r"^x\s*=\s*[-\d]+\s*m?$"),
    re.compile(r"^v\s*=\s*\d"),
]


def _is_garbage(plain: str, vars_used: set[str]) -> bool:
    """Reject non-equation text."""
    s = plain.strip()
    if len(s) < 4:
        return True
    if len(s) > 200:
        return True
    for pat in _GARBAGE_PATTERNS:
        if pat.fullmatch(s):
            return True
    if not vars_used:
        return True

    tokens = (
        s.replace("−", " ")
        .replace("=", " ")
        .replace("+", " ")
        .replace("−", " ")
        .replace("·", " ")
        .replace("×", " ")
        .split()
    )
    long_tokens = [t for t in tokens if re.match(r"^[a-zA-Z]{5,}$", t)]
    if len(long_tokens) > 3:
        return True

    camel_words = re.findall(r"[a-z][A-Z]", s)
    if len(camel_words) > 1:
        return True

    if re.search(r"[a-zA-Z]{3,}=|=[a-zA-Z]{3,}", s):
        return True

    for marker in [
        r"\b(?:when|where|and the|Plotted|Figure|shown|here|This is|Note that)\b",
        r"\b(?:After reading|you should be able|arrangement|component of|on the|axis)\b",
        r"\b(?:algebraically|substitut|magnitudeof)\b",
        r"\b(?:Wewrite|object|forceof)\b",
    ]:
        if re.search(marker, s):
            return True
    return False


def extract_equations(content: str) -> list[dict]:
    """Extract equations from text."""
    equations = []
    seen = set()

    for pattern, _ in LATEX_PATTERNS:
        for match in re.finditer(pattern, content, re.DOTALL):
            eq = match.group(1).strip()
            if len(eq) < 4 or eq in seen:
                continue
            seen.add(eq)
            plain = _latex_to_plain(eq)
            vars_used = _extract_variables(eq)
            if _is_garbage(plain, vars_used):
                continue
            equations.append(
                {
                    "latex": eq,
                    "plain_text": plain,
                    "variables": sorted(vars_used),
                }
            )

    for eq in _find_plain_equations(content):
        if eq in seen:
            continue
        seen.add(eq)
        vars_used = _extract_variables(eq)
        plain = eq.replace("−", "-").replace("×", "*").replace("·", "*")
        if _is_garbage(plain, vars_used):
            continue
        equations.append(
            {
                "latex": None,
                "plain_text": eq,
                "variables": sorted(vars_used),
            }
        )

    return equations


def _find_plain_equations(content: str) -> list[str]:
    """Find plain-text equations via variable=expression patterns."""
    results = []
    for line in content.split("\n"):
        line = line.strip().replace("$", "")
        if "=" not in line or len(line) < 6 or len(line) > 200:
            continue
        if not re.match(r"^[A-Za-zΔ∇∂]", line):
            continue
        if not any(
            v in line for v in ["m", "F", "v", "a", "x", "t", "E", "p", "g", "k", "T"]
        ):
            continue
        word_count = len(re.findall(r"[a-zA-Z]{3,}", line))
        if word_count > 8:
            continue
        results.append(line)
    return results


def _latex_to_plain(latex: str) -> str:
    """Convert LaTeX to plain text."""
    plain = latex
    for cmd, replacement in [
        (r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1)/(\2)"),
        (r"\\sqrt\{([^}]+)\}", r"sqrt(\1)"),
        (r"\\int", "∫"),
        (r"\\sum", "Σ"),
        (r"\\oint", "∮"),
        (r"\\partial", "∂"),
        (r"\\nabla", "∇"),
        (r"\\cdot", "·"),
        (r"\\times", "×"),
        (r"\\rightarrow", "→"),
        (r"\\infty", "∞"),
        (r"\\epsilon", "ε"),
        (r"\\varepsilon", "ε"),
        (r"\\mu", "μ"),
        (r"\\sigma", "σ"),
        (r"\\rho", "ρ"),
        (r"\\theta", "θ"),
        (r"\\phi", "φ"),
        (r"\\omega", "ω"),
        (r"\\lambda", "λ"),
        (r"\\pi", "π"),
        (r"\\alpha", "α"),
        (r"\\beta", "β"),
        (r"\\gamma", "γ"),
        (r"\\delta", "δ"),
        (r"\\Delta", "Δ"),
        (r"\\Phi", "Φ"),
        (r"\\Omega", "Ω"),
        (r"\\hat\{([^}]+)\}", r"\1̂"),
        (r"\\vec\{([^}]+)\}", r"\1⃗"),
        (r"\\mathbf\{([^}]+)\}", r"\1"),
        (r"\{|\}", ""),
        (r"\\ ", " "),
    ]:
        plain = re.sub(cmd, replacement, plain)
    return plain.strip()


def _extract_variables(expr: str) -> set[str]:
    """Extract physics variable names."""
    found = set()
    for var in _PHYSICS_VARS:
        if re.search(rf"\b{re.escape(var)}\b", expr):
            found.add(var)
    return found


def retrieve_equations(
    db: Session, query_text: str, textbook_ids: list[int] | None, top_k: int = 5
) -> list[dict]:
    """Retrieve equations by embedding similarity + variable overlap reranking."""
    vector = embed_text(query_text, is_query=True)
    query_vars = _extract_variables(query_text)

    filters = []
    params: dict[str, object] = {"vector": vector, "top_k": top_k}

    if textbook_ids:
        filters.append("e.textbook_id = ANY(:textbook_ids)")
        params["textbook_ids"] = textbook_ids

    where_clause = " AND ".join(filters) if filters else "TRUE"

    query_sql = text(f"""
        SELECT e.id, e.latex, e.plain_text, e.variables, e.chapter, e.page_start,
               tb.title AS textbook_title, tb.id AS textbook_id,
               (e.embedding <=> CAST(:vector AS vector)) AS distance
        FROM equations e
        JOIN textbooks tb ON tb.id = e.textbook_id
        WHERE {where_clause}
        ORDER BY e.embedding <=> CAST(:vector AS vector)
        LIMIT :top_k
    """)
    rows = db.execute(query_sql, params).mappings().all()
    results = [dict(row) for row in rows]

    if query_vars:
        for r in results:
            vars_list = r.get("variables") or []
            overlap = len(set(vars_list) & query_vars)
            r["_var_overlap"] = overlap
        results.sort(key=lambda r: (r.get("_var_overlap", 0), -1), reverse=True)

    return results
