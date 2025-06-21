from app.services import vector_store, lmstudio, embedding
from app.models.chat_model import ChatQuery, ChatResponse
from pathlib import Path
import json

# Few-shot examples removed - no longer needed

# ——— Load role‐specific prompt templates ———
ROLE_PROMPTS = {
    "strict": (
        "Answer ONLY using the textbook context provided. "
        "If the answer is not in the textbook context, say 'This information is not available in the provided textbook content.'"
    ),
    "default": (
        "Answer the question using the textbook context when available. "
        "If the textbook context doesn't contain the answer, you may provide general knowledge to help the user, "
        "but clearly indicate when you're drawing from general knowledge vs. the textbook."
    )
}

# ——— Global system instruction ———
SYSTEM_INSTRUCTION = (
    "You are a highly knowledgeable AI assistant trained on academic textbooks.\n"
    "If textbook context is provided, answer strictly from it. "
    "Otherwise you may answer any general question helpfully.\n"
)

def get_rag_response(query: ChatQuery) -> ChatResponse:
    # 1) Determine response mode based on role
    role_key = query.role.lower().strip()
    if role_key not in ["strict", "default"]:
        role_key = "default"  # fallback to default if invalid role

    # 2) Detect list‐style queries
    q_lower = query.query.lower()
    if any(kw in q_lower for kw in ("list", "bullet", "enumerate", "what are the")):
        list_instr = "Format your answer as a bulleted list.\n"
    else:
        list_instr = ""

    # 3) If no PDF, use general knowledge (only for default mode)
    if not query.pdf_id:
        if role_key == "strict":
            return ChatResponse(
                answer="No textbook is loaded. Please upload a textbook to get answers from it.",
                citations=[]
            )
        else:  # default mode
            prompt = (
                f"{SYSTEM_INSTRUCTION}"
                f"{list_instr}"
                f"User: {query.query}\n"
                "AI:"
            )
            ans = lmstudio.ask_local_llm(prompt)
            return ChatResponse(answer=ans.strip(), citations=[])

    try:
        print("📩 Received:", query.dict())

        # 4) RAG retrieval
        vec = embedding.get_embeddings([query.query])[0]
        docs_meta = vector_store.query_vectors(query.pdf_id, vec, k=8)
        docs = docs_meta.get("documents", [[]])[0]
        metas = docs_meta.get("metadatas", [[]])[0]

        # 5) If no relevant content found in textbook
        if not docs or all(not d.strip() for d in docs):
            if role_key == "strict":
                return ChatResponse(
                    answer="This information is not available in the provided textbook content.",
                    citations=[]
                )
            else:  # default mode - provide general knowledge
                prompt = (
                    f"{SYSTEM_INSTRUCTION}"
                    f"{list_instr}"
                    f"The textbook doesn't contain information about this topic, so I'll provide general knowledge:\n\n"
                    f"User: {query.query}\n"
                    "AI:"
                )
                ans = lmstudio.ask_local_llm(prompt)
                return ChatResponse(answer=ans.strip(), citations=[])

        # 6) Build the chapter TOC snippet from metadata
        first_meta = metas[0] if metas else {}
        toc = first_meta.get("chapters", [])
        toc_note = ""
        if first_meta.get("title"):
            toc_note += f"Title: {first_meta['title']}\n"
        if toc:
            toc_note += "Chapters:\n"
            for ch in toc:
                toc_note += f"- {ch['title']} (page {ch['page']})\n"
            toc_note += "\n"

        # 7) Grab the role prompt
        role_prompt = ROLE_PROMPTS.get(role_key, ROLE_PROMPTS["default"])

        # 8) Build context for prompt

        # 9) Assemble full prompt based on role
        context = "\n\n".join(docs)
        
        if role_key == "strict":
            # Strict mode: only textbook content
            prompt_parts = [
                SYSTEM_INSTRUCTION,
                ROLE_PROMPTS["strict"],
                toc_note,
                "Textbook content:",
                context,
                f"Question: {query.query}",
                "Answer based ONLY on the textbook content above:"
            ]
        else:
            # Default mode: textbook + general knowledge if needed
            prompt_parts = [
                SYSTEM_INSTRUCTION,
                ROLE_PROMPTS["default"],
                toc_note,
                "Textbook content:",
                context,
                f"Question: {query.query}",
                "Answer using the textbook content above. If the textbook doesn't contain the answer, "
                "you may provide general knowledge but clearly indicate the source:"
            ]
        
        if list_instr:
            prompt_parts.insert(-1, list_instr)
        
        prompt = "\n".join(filter(None, prompt_parts))

        print("🧠 Final prompt:", prompt[:200].replace("\n", " "))
        answer = lmstudio.ask_local_llm(prompt)

        # 10) Collect page citations
        pages = [m.get("page") for m in metas if m and m.get("page") is not None]
        citations = [f"page {p}" for p in pages]

        return ChatResponse(answer=answer.strip(), citations=citations)

    except Exception as e:
        print("[RAG ERROR]", e)
        # Fallback based on role
        if role_key == "strict":
            return ChatResponse(
                answer="An error occurred while searching the textbook. Please try again.",
                citations=[]
            )
        else:  # default mode
            fallback = (
                f"{SYSTEM_INSTRUCTION}"
                f"{list_instr}"
                f"User: {query.query}\nAI:"
            )
            ans = lmstudio.ask_local_llm(fallback)
            return ChatResponse(answer=ans.strip(), citations=[])