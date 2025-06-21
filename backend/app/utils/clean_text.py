def normalize_text(text: str) -> str:
    import emoji
    text = re.sub(r"http\S+|www\S+", "", text)
    text = emoji.replace_emoji(text, replace="")
    text = re.sub(r"[\x00-\x1F]+", "", text)  # remove control chars
    text = re.sub(r"\s+", " ", text).strip()
    return text