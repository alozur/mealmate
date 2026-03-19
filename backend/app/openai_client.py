import json
from datetime import date

from openai import AsyncOpenAI

from app.database import settings
from app.schemas import ProfileResponse

SYSTEM_PROMPT = """You are a professional nutritionist and meal planner. You create weekly meal plans \
(Monday to Saturday) with lunch and dinner for each day. Breakfast is fixed and not \
included in your plans.

You must generate meals that are SHARED - the same recipe for all people eating \
together, but with DIFFERENT portion sizes to meet each person's individual \
nutritional targets.

IMPORTANT RULES:
- Generate exactly 12 meals: 2 per day (lunch + dinner) x 6 days (Mon-Sat)
- Each meal must include: name, description, full recipe steps, prep time, cook time, \
  complete ingredient list with quantities, and per-person portion/macro breakdown
- Vary cuisines and proteins throughout the week (avoid repetition)
- Keep recipes practical for home cooking (30-60 min total time preferred)
- Ingredients should be commonly available at regular grocery stores
- Categorize each ingredient into one of: produce, protein, dairy, grains, pantry, \
  spices, frozen, beverages, condiments

You MUST respond with valid JSON matching the exact schema provided."""

RESPONSE_SCHEMA = """\
Respond with a JSON object with this exact structure:
{
  "meals": [
    {
      "day_of_week": 1,
      "meal_type": "lunch",
      "name": "Meal Name",
      "description": "Brief description",
      "recipe_steps": ["Step 1...", "Step 2..."],
      "prep_time_min": 15,
      "cook_time_min": 20,
      "ingredients": [
        {"name": "Chicken breast", "quantity": "500", "unit": "g", "category": "protein"}
      ],
      "portions": [
        {
          "profile_name": "PersonName",
          "serving_size": "1.5 portions",
          "calories": 650,
          "protein_g": 55,
          "carbs_g": 45,
          "fat_g": 22
        }
      ]
    }
  ]
}

day_of_week: 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
meal_type: "lunch" or "dinner"
category: one of "produce", "protein", "dairy", "grains", "pantry", "spices", "frozen", "beverages", "condiments"
"""


def _build_profiles_text(profiles: list[ProfileResponse]) -> str:
    lines = []
    for p in profiles:
        restrictions = ", ".join(p.restrictions) if p.restrictions else "None"
        lines.append(
            f"**{p.name}**:\n"
            f"- Goal: {p.goal}\n"
            f"- Daily targets: {p.calorie_target} kcal, {p.protein_target}g protein, "
            f"{p.carbs_target}g carbs, {p.fat_target}g fat\n"
            f"- Dietary restrictions: {restrictions}"
        )
    return "\n\n".join(lines)


async def generate_weekly_plan(
    profiles: list[ProfileResponse], week_start: date
) -> dict:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    week_end = date.fromordinal(week_start.toordinal() + 5)
    profiles_text = _build_profiles_text(profiles)

    user_prompt = f"""Generate a weekly meal plan for {len(profiles)} people with the following profiles:

{profiles_text}

Week: {week_start.strftime("%A %B %d, %Y")} to {week_end.strftime("%A %B %d, %Y")}

Remember: Same meals for everyone, but adjust portion sizes so each person's lunch+dinner \
combined gets them approximately to their remaining daily targets (after a ~400-500 kcal \
fixed breakfast). Split roughly 40% lunch / 60% dinner for calorie distribution.

{RESPONSE_SCHEMA}"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    content = response.choices[0].message.content
    return json.loads(content)


async def regenerate_single_meal(
    profiles: list[ProfileResponse],
    existing_meals: list[str],
    day_of_week: int,
    meal_type: str,
    old_meal_name: str,
) -> dict:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    day_names = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
    }
    profiles_text = _build_profiles_text(profiles)
    existing_list = "\n".join(f"- {m}" for m in existing_meals)

    user_prompt = f"""I need to regenerate ONE meal in an existing weekly plan. Here is the context:

Existing meals this week (do NOT repeat these):
{existing_list}

Meal to replace:
- Day: {day_names.get(day_of_week, "Unknown")} {meal_type}
- Previous meal was: {old_meal_name}

Generate a DIFFERENT meal for this slot. Use the same JSON format but return only ONE meal.

Profiles:
{profiles_text}

{RESPONSE_SCHEMA}

IMPORTANT: Return a JSON object with a "meals" array containing exactly 1 meal."""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.9,
    )

    content = response.choices[0].message.content
    return json.loads(content)
