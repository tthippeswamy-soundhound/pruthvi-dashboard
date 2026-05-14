from __future__ import annotations

from openai import AsyncOpenAI

DEFAULT_PROMPT = (
    "You are an expert analyst. Analyze the following transcript and provide:\n"
    "1. **Summary**: A concise summary of the key points\n"
    "2. **Sentiment**: The overall sentiment (positive, negative, neutral, mixed)\n"
    "3. **Key Topics**: Main topics discussed\n"
    "4. **Action Items**: Any action items or follow-ups mentioned\n"
    "5. **Notable Quotes**: Any significant or noteworthy statements\n\n"
    "Be concise but thorough."
)


async def analyze_transcript(
    transcript: str,
    api_key: str,
    prompt: str | None = None,
    model: str = "gpt-4o-mini",
) -> str:
    client = AsyncOpenAI(api_key=api_key)
    system_prompt = prompt or DEFAULT_PROMPT

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transcript:\n\n{transcript}"},
        ],
        max_tokens=1500,
        temperature=0.3,
    )
    return response.choices[0].message.content
