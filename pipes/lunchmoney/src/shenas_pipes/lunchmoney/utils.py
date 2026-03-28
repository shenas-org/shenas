import re

import pendulum


def resolve_start_date(value: str) -> str:
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value
    match = re.fullmatch(r"(\d+)\s+days?\s+ago", value.strip())
    if match:
        return pendulum.now().subtract(days=int(match.group(1))).to_date_string()
    raise ValueError(f"Cannot parse start_date: {value!r}. Use 'YYYY-MM-DD' or 'N days ago'.")
