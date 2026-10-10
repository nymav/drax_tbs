"""Bounded local-model calls. Provider failures never become fabricated answers."""

from urllib.parse import urlparse
import requests
import json
import re
from app import config
import threading

_MODEL_SLOT = threading.BoundedSemaphore(1)


class GeneratedAnswer(str):
    def __new__(cls, text, claims, budget):
        instance = super().__new__(cls, text)
        instance.claims = claims
        instance.budget = budget
        return instance


class ModelUnavailable(Exception):
    pass


def local_url():
    url = config.LMSTUDIO_API
    parsed = urlparse(url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.scheme != "http":
        raise ModelUnavailable("DRAX only accepts a local model endpoint.")
    return url


def available_models():
    try:
        response = requests.get(
            local_url().replace("/chat/completions", "") + "/models", timeout=3, allow_redirects=False
        )
        response.raise_for_status()
        return [item["id"] for item in response.json().get("data", []) if isinstance(item.get("id"), str)]
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise ModelUnavailable("Start LM Studio and load a chat model to enable tutoring.") from exc


def response_schema(prompt, mode, evidence=None):
    references = {
        "type": "array",
        "items": {
            "type": "string",
            "enum": sorted(evidence)
            if evidence is not None
            else sorted(set(re.findall(r"\[(S\d+)\]", prompt))) or ["S1"],
        },
        "minItems": 1,
    }
    properties = {"answer": {"type": "string", "enum": [""]}, "source_ids": references}
    if mode == "tutor":
        properties["next_question"] = {"type": "string"}
    elif mode == "quizzer":
        properties = {
            "questions": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {"question": {"type": "string"}, "answer": {"type": "string"}},
                    "required": ["question", "answer"],
                    "additionalProperties": False,
                },
            },
            "source_ids": references,
        }
    properties["claims"] = {
        "type": "array",
        "minItems": 1,
        "maxItems": 2 if mode == "summarizer" else 3 if mode == "quizzer" else 4,
        "items": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "source_id": references["items"],
                "quote": {"type": "string", "minLength": 8},
            },
            "required": ["claim", "source_id", "quote"],
            "additionalProperties": False,
        },
    }
    if evidence:
        alternatives = []
        for identity, text in evidence.items():
            quotes = [
                sentence.strip()[:180] for sentence in re.split(r"(?<=[.!?])\s+", text) if len(sentence.strip()) >= 8
            ]
            if not quotes:
                continue
            alternatives.append(
                {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "source_id": {"type": "string", "enum": [identity]},
                        "quote": {"type": "string", "enum": quotes},
                    },
                    "required": ["claim", "source_id", "quote"],
                    "additionalProperties": False,
                }
            )
        if alternatives:
            # Grammar couples each allowed quote to its actual source, preventing
            # a valid quote from being assigned to an unrelated source ID.
            properties["claims"]["items"] = {"anyOf": alternatives}
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def format_response(output, mode):
    if not isinstance(output, dict):
        raise ValueError("Invalid structured answer")
    references = output.get("source_ids", [])
    if not isinstance(references, list) or not references or not all(isinstance(r, str) for r in references):
        raise ValueError("Missing source references")
    if mode == "quizzer":
        questions = output.get("questions")
        if not isinstance(questions, list) or len(questions) != 3:
            raise ValueError("Practice needs three questions")
        for question in questions:
            if not isinstance(question, dict) or not all(
                isinstance(question.get(key), str) and question[key].strip() for key in ["question", "answer"]
            ):
                raise ValueError("Practice needs an answer key")
            if (
                not re.match(
                    r"(?i)^(what|how|why|which|describe|explain|compare|define|name|list|when|where|can|does|is)\b",
                    question["question"].strip(),
                )
                and "?" not in question["question"]
            ):
                raise ValueError("Practice output is not a question")
        text = "\n\n".join(f"{i}. {q['question']}" for i, q in enumerate(questions, 1))
        text += "\n\nAnswer key\n\n" + "\n\n".join(f"{i}. {q['answer']}" for i, q in enumerate(questions, 1))
    else:
        text = output.get("answer", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Empty structured answer")
        text = text.strip()
        if mode == "tutor":
            question = output.get("next_question", "")
            if not isinstance(question, str) or not question.strip():
                raise ValueError("Guided learning needs a follow-up question")
            text += "\n\nYour turn: " + question.strip()
    return text + "\n\nSources: " + " ".join(f"[{reference}]" for reference in references)


def loaded_context(model):
    origin = local_url().split("/v1/")[0]
    try:
        response = requests.get(origin + "/api/v1/models", timeout=3, allow_redirects=False)
        response.raise_for_status()
        for item in response.json().get("models", []):
            if item.get("key") == model:
                instances = item.get("loaded_instances", [])
                if instances:
                    return int(instances[0]["config"]["context_length"])
    except (requests.RequestException, ValueError, KeyError, TypeError):
        pass
    try:
        import lmstudio as lms

        parsed = urlparse(local_url())
        with lms.Client(api_host=f"{parsed.hostname}:{parsed.port or 80}") as client:
            loaded = next((m for m in client.llm.list_loaded() if m.identifier == model), None)
            if loaded:
                return loaded.get_context_length()
    except Exception:
        pass
    raise ModelUnavailable(
        "Cannot read the loaded model context. Start LM Studio's local server and load a chat model."
    )


def validate_claims(output, prompt, evidence=None):
    # Quotes establish source membership, not semantic entailment.
    sources = dict(re.findall(r"\[(S\d+)\] Page \d+: (.*?)(?=\n\n\[S|\nLearner request:|$)", prompt, re.S))
    if evidence is not None:
        sources = evidence
    claims = output.get("claims", [])
    if not claims:
        raise ValueError("Missing claim-level evidence")

    def normalize(text):
        return " ".join(text.split())

    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("quote"), str) or len(claim["quote"].strip()) < 8:
            raise ValueError("Invalid claim quote")
        if normalize(claim["quote"]) not in normalize(sources.get(claim.get("source_id"), "")):
            raise ValueError("Claim quote is not in its cited passage")


def ask_local_llm(prompt, system_message, max_tokens=1200, mode=None, evidence=None):
    if not _MODEL_SLOT.acquire(timeout=5):
        raise ModelUnavailable("The local model is busy. Retry shortly.")
    try:
        from filelock import FileLock, Timeout

        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(config.DATA_DIR / "model.lock", timeout=5):
                return _ask(prompt, system_message, max_tokens, mode, evidence)
        except Timeout as exc:
            raise ModelUnavailable("The local model is busy. Retry shortly.") from exc
    finally:
        _MODEL_SLOT.release()


def _ask(prompt, system_message, max_tokens=1200, mode=None, evidence=None):
    try:
        model = config.LMSTUDIO_MODEL or next(iter(available_models()), None)
        if not model:
            raise ModelUnavailable("No local model is loaded.")
        context = loaded_context(model)
        # UTF-8 bytes are a conservative upper bound for byte-level tokenizers;
        # reserve output plus chat framing, rather than guessing chars/4.
        prompt, input_bound, max_tokens = budget_prompt(
            prompt, system_message, context, max_tokens, counter=lambda text: count_tokens(model, system_message, text)
        )
        response = requests.post(
            local_url(),
            json={
                "model": model,
                "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": max_tokens,
                "stream": False,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "drax_" + (mode or "answer"),
                        "strict": True,
                        "schema": response_schema(prompt, mode, evidence),
                    },
                },
            },
            timeout=(5, 90),
            allow_redirects=False,
        )
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        if choice.get("finish_reason") == "length":
            raise ModelUnavailable(
                "The model response was truncated. Ask a narrower question or increase the loaded model context."
            )
        answer = choice["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Empty model output")
        output = json.loads(answer)
        validate_claims(output, prompt, evidence)
        claims = output["claims"]
        if not all(isinstance(c.get("claim"), str) and c["claim"].strip() for c in claims):
            raise ValueError("Empty claim")
        output["source_ids"] = list(dict.fromkeys(c["source_id"] for c in claims))
        if mode == "quizzer":
            supported = {c["claim"]: c["source_id"] for c in claims}
            for question in output.get("questions", []):
                if question.get("answer") not in supported:
                    raise ValueError("Practice answer missing claim evidence")
                question["answer"] += " [" + supported[question["answer"]] + "]"
        else:
            # Render only explicitly evidenced claims, discarding uncited free prose.
            output["answer"] = "\n\n".join(c["claim"] + " [" + c["source_id"] + "]" for c in claims)
        return GeneratedAnswer(
            format_response(output, mode),
            claims,
            {
                "loaded_context": context,
                "input_upper_bound": input_bound,
                "output_limit": max_tokens,
                "counting": "loaded tokenizer with 128-token reserve; conservative UTF-8 fallback if SDK unavailable",
            },
        )
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModelUnavailable(
            "The local model did not return a usable answer. Showing source passages instead."
        ) from exc


def budget_prompt(prompt, system_message, context, requested_output, counter=None):
    def count(text):
        return counter(text) if counter else len((text + system_message).encode("utf-8")) + 256

    output = min(requested_output, max(256, context // 4))
    parts = prompt.split("Sources:\n", 1)
    if len(parts) == 2 and "\nLearner request:" in parts[1]:
        evidence, request = parts[1].rsplit("\nLearner request:", 1)
        passages = re.split(r"\n\n(?=\[S\d+\])", evidence)
        while len(passages) > 1 and len((prompt + system_message).encode("utf-8")) + 256 + output > context:
            passages.pop()
            prompt = parts[0] + "Sources:\n" + "\n\n".join(passages) + "\nLearner request:" + request
    bound = len((prompt + system_message).encode("utf-8")) + 256
    output = min(output, context - bound)
    if output < 256:
        raise ModelUnavailable("Selected evidence exceeds the loaded context. Narrow the page range or question.")
    return prompt, bound, output


def count_tokens(model, system, prompt):
    try:
        import lmstudio as lms

        parsed = urlparse(local_url())
        with lms.Client(api_host=f"{parsed.hostname}:{parsed.port or 80}") as client:
            loaded = next((m for m in client.llm.list_loaded() if m.identifier == model), None)
            if not loaded:
                raise ValueError("Model unloaded during request")
            chat = lms.Chat.from_history(
                {"messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
            )
            return len(loaded.tokenize(loaded.apply_prompt_template(chat))) + 128
    except Exception:
        # Local SDK unavailable: conservative count, never chars/4 guesswork.
        return len((system + prompt).encode("utf-8")) + 256
