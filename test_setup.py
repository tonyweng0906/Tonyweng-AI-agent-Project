import os

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY was not found. "
        "Check that the .env file exists in the project root."
    )

client = OpenAI(api_key=api_key)

df = pd.DataFrame(
    [
        {
            "coach_name": "Coach Amy",
            "specialty": "Beginner training",
        }
    ]
)

print("Environment setup successful.")
print(df)