from openai import OpenAI
from config import OPENAI_API_KEY, LLM_MODEL
from vectorstore import search

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a GDPR compliance assistant. Answer questions based ONLY on the provided context.
Rules:
- Cite sources using [Source: source_name, Chunk: N] notation after each claim.
- If the context is insufficient, say so explicitly.
- Do not make up information.
- If the user asks in a non-English language, respond in that same language.
{language_instruction}"""

RISK_SYSTEM_PROMPT = """You are a GDPR risk analyst. Given a project description and relevant GDPR knowledge context, produce a structured risk assessment.

You MUST respond in valid JSON format with this exact structure:
{{
  "overall_score": <1-10 integer>,
  "dimensions": {{
    "lawful_basis": {{"score": <1-10>, "summary": "<one sentence>"}},
    "data_minimization": {{"score": <1-10>, "summary": "<one sentence>"}},
    "consent_transparency": {{"score": <1-10>, "summary": "<one sentence>"}},
    "data_subject_rights": {{"score": <1-10>, "summary": "<one sentence>"}},
    "international_transfers": {{"score": <1-10>, "summary": "<one sentence>"}},
    "security_breach": {{"score": <1-10>, "summary": "<one sentence>"}},
    "special_categories": {{"score": <1-10>, "summary": "<one sentence>"}},
    "automated_decisions": {{"score": <1-10>, "summary": "<one sentence>"}}
  }},
  "risks": [
    {{
      "title": "<short title>",
      "level": "High|Medium|Low",
      "description": "<description>",
      "article": "<relevant GDPR article>",
      "source": "<source_name, Chunk N>",
      "recommendation": "<brief suggestion>"
    }}
  ],
  "top_priorities": ["<priority 1>", "<priority 2>", "<priority 3>"]
}}

Scoring guide (1=no risk, 10=critical risk):
- 1-3: Low risk, minor improvements needed
- 4-6: Medium risk, action required
- 7-9: High risk, urgent action needed
- 10: Critical, likely illegal under GDPR

Base your assessment ONLY on the provided context. Do NOT output anything outside the JSON.
{language_instruction}"""


def _build_context(docs: list[dict]) -> str:
    parts = []
    for i, d in enumerate(docs, 1):
        parts.append(f"[{i}] (Source: {d['source']}, Chunk: {d['chunk_index']})\n{d['text']}")
    return "\n\n".join(parts)


def chat(question: str, top_k: int = 5, metadata_filter: dict | None = None,
         history: list[dict] | None = None, language: str | None = None) -> dict:
    docs = search(question, top_k=top_k, metadata_filter=metadata_filter)
    context = _build_context(docs)

    lang_inst = f"Respond in {language}." if language else ""
    system = SYSTEM_PROMPT.format(language_instruction=lang_inst)

    messages = [{"role": "system", "content": system}]

    # Add conversation history for multi-turn context
    if history:
        for msg in history[-6:]:  # Keep last 3 exchanges to save tokens
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})

    try:
        resp = client.chat.completions.create(model=LLM_MODEL, messages=messages, temperature=0.2)
    except Exception as e:
        return {"answer": f"API error: {e}", "sources": []}
    return {
        "answer": resp.choices[0].message.content,
        "sources": [
            {
                "source": d["source"],
                "document_id": d["document_id"],
                "chunk_index": d["chunk_index"],
                "text": d["text"],
                "score": d["score"],
            }
            for d in docs
        ],
    }


def risk_analysis(project_description: str, top_k: int = 8, language: str | None = None) -> dict:
    query = f"GDPR compliance risks for: {project_description}"
    docs = search(query, top_k=top_k)
    context = _build_context(docs)

    lang_inst = f"Respond in {language}." if language else ""
    system = RISK_SYSTEM_PROMPT.format(language_instruction=lang_inst)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Context:\n{context}\n\nProject Description:\n{project_description}"},
    ]
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL, messages=messages, temperature=0.3,
            response_format={"type": "json_object"}
        )
        import json
        analysis = json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"analysis": f"API error: {e}", "sources": []}
    return {
        "analysis": analysis,
        "sources": [
            {
                "source": d["source"],
                "document_id": d["document_id"],
                "chunk_index": d["chunk_index"],
                "text": d["text"],
                "score": d["score"],
            }
            for d in docs
        ],
    }
