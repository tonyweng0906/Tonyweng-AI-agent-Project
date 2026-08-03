def select_source_ids(
    requested_source_ids: list[str],
    allowed_source_ids: list[str],
) -> list[str]:
    """Keep unique source IDs that came from retrieved context."""
    allowed = set(allowed_source_ids)
    selected = []

    for source_id in requested_source_ids:
        cleaned_source_id = str(source_id).strip()

        if (
            cleaned_source_id in allowed
            and cleaned_source_id not in selected
        ):
            selected.append(cleaned_source_id)

    return selected

