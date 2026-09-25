import re
import unicodedata
import pandas as pd


def normalize_text(value):
    if pd.isna(value):
        return ""

    value = str(value)
    value = unicodedata.normalize("NFKC", value)
    value = value.lower()

    # Keep unicode letters/numbers, remove punctuation
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)

    # Normalize whitespace
    value = re.sub(r"\s+", " ", value).strip()

    return value


def normalize_dataframe(df):
    df = df.copy()

    df["name_norm"] = df["business_name"].map(normalize_text)
    df["address_norm"] = df["business_address"].map(normalize_text)
    df["country_norm"] = df["country"].map(normalize_text)

    return df
