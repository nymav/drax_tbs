"""Bounded local-model calls. Provider failures never become fabricated answers."""

from urllib.parse import urlparse
import requests
import json
import re
from app import config


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


def response_schema(prompt, mode):
    references = {
        "type": "array",
        "items": {"type": "string", "enum": sorted(set(re.findall(r"\[(S\d+)\]", prompt))) or ["S1"]},
        "minItems": 1,
    }
    properties = {"answer": {"type": "string"}, "source_ids": references}
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


def ask_local_llm(prompt, system_message, max_tokens=1200, mode=None):
    try:
        model = config.LMSTUDIO_MODEL or next(iter(available_models()), None)
        if not model:
            raise ModelUnavailable("No local model is loaded.")
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
                        "schema": response_schema(prompt, mode),
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
        return format_response(json.loads(answer), mode)
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModelUnavailable(
            "The local model did not return a usable answer. Showing source passages instead."
        ) from exc
