import anthropic
from anthropic import beta_tool
from django.conf import settings

from events.models import Fighter, Ranking

SYSTEM_PROMPT = """You are a neutral MMA analyst writing brief commentary for a \
fan-facing UFC website. For the given upcoming bout, use the available tools to \
look up each fighter's profile and current UFC ranking, then write a short \
(3-5 sentence) neutral analysis of the matchup.

Strict rules:
- Do not declare a winner or favorite. Do not use betting language: no odds, \
no percentages, no "X is likely to win", no "pick" or "prediction".
- You may describe factual edges neutrally, e.g. "enters with a ranking edge", \
but always as descriptive commentary, never as a forecast of the outcome.
- If ranking or record data is sparse or missing, say so plainly rather than \
speculating or inventing details.
- Do not mention that you used tools or how you gathered information."""


@beta_tool
def get_fighter_profile(fighter_slug: str) -> str:
    """Look up a fighter's cached profile (name, nickname, record, country).

    Args:
        fighter_slug: The fighter's slug identifier, e.g. "jon-jones".
    """
    try:
        fighter = Fighter.objects.get(slug=fighter_slug)
    except Fighter.DoesNotExist:
        return f"No cached profile found for fighter slug '{fighter_slug}'."
    parts = [fighter.name]
    if fighter.nickname:
        parts.append(f'"{fighter.nickname}"')
    if fighter.record:
        parts.append(f"record: {fighter.record}")
    if fighter.country:
        parts.append(f"from {fighter.country}")
    return ", ".join(parts)


@beta_tool
def get_fighter_ranking(fighter_slug: str) -> str:
    """Look up a fighter's current UFC ranking(s), if any.

    Args:
        fighter_slug: The fighter's slug identifier, e.g. "jon-jones".
    """
    rankings = Ranking.objects.filter(fighter__slug=fighter_slug)
    if not rankings.exists():
        return f"No current UFC ranking on file for '{fighter_slug}'."
    lines = []
    for r in rankings:
        if r.is_champion:
            lines.append(f"{r.division}: champion")
        elif r.rank:
            lines.append(f"{r.division}: ranked #{r.rank}")
        else:
            lines.append(f"{r.division}: {r.rank_text or 'unranked'}")
    return "; ".join(lines)


def generate_analysis(bout):
    client = anthropic.Anthropic()
    user_prompt = (
        f"Event: {bout.event.name}\n"
        f"Weight class: {bout.weight_class or 'unknown'}\n"
        f"Title fight: {'yes' if bout.is_title_fight else 'no'}\n"
        f"Fighter A: {bout.fighter_one.name} (slug: {bout.fighter_one.slug})\n"
        f"Fighter B: {bout.fighter_two.name} (slug: {bout.fighter_two.slug})\n\n"
        "Use the available tools to look up each fighter's profile and current "
        "ranking, then write the analysis."
    )
    kwargs = dict(
        model=settings.INTELLIGENCE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[get_fighter_profile, get_fighter_ranking],
        messages=[{"role": "user", "content": user_prompt}],
    )
    try:
        runner = client.beta.messages.tool_runner(output_config={"effort": "low"}, **kwargs)
    except TypeError:
        runner = client.beta.messages.tool_runner(**kwargs)

    last_message = None
    for message in runner:
        last_message = message
    if last_message is None:
        raise RuntimeError("Claude tool_runner produced no messages for this bout")
    for block in last_message.content:
        if block.type == "text":
            return block.text
    raise RuntimeError("Claude's final message contained no text block")
