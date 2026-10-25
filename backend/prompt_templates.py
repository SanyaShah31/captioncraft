"""
Prompt templates and formatting guidelines for CaptionCraft AI.
Provides structured system prompts, persona framing, tone definitions,
platform formatting guides, and JSON schema instructions.
"""

from typing import List, Dict, Any, Optional

# Supported social media platforms
PLATFORMS = [
    "Instagram",
    "Twitter / X",
    "LinkedIn",
    "TikTok",
    "Facebook",
    "Pinterest",
    "YouTube Shorts",
    "Threads"
]

# Supported caption tones
TONES = [
    "Aesthetic",
    "Funny",
    "Romantic",
    "Professional",
    "Inspirational",
    "Emotional",
    "Minimal",
    "Savage"
]

# Supported lengths
LENGTHS = ["Short", "Medium", "Long"]

# Tone specifications for deep contextual guidance
TONE_INSTRUCTIONS: Dict[str, str] = {
    "Funny": "Infuse clever wit, self-deprecating humor, sharp sarcasm, or relatable everyday ironies. Make the reader smile or chuckle out loud.",
    "Aesthetic": "Craft dreamy, poetic, soft, and atmospheric vibes. Use graceful imagery, subtle mood phrasing, often lowercase-chic or delicate phrasing.",
    "Romantic": "Warm, tender, soulful, heartfelt, and deeply affectionate. Evoke feelings of love, nostalgia, intimacy, or admiration.",
    "Professional": "Polished, insightful, authoritative, and industry-savvy. Position the speaker as an expert, thought leader, or constructive collaborator.",
    "Inspirational": "Empowering, uplifting, and motivational. Focus on resilience, ambition, lessons learned, and encouraging the audience to reach their potential.",
    "Emotional": "Vulnerable, authentic, introspective, and heartfelt. Resonate with genuine human feelings, deep reflections, and empathy.",
    "Minimal": "Ultra-concise, punchy, high-impact. Zero fluff, 1 or 2 striking sentences, maximum memorability.",
    "Savage": "Bold, unapologetic, sassy, fiery, and full of attitude. Unfiltered confidence, fierce comebacks, and swagger."
}

# Platform formatting and cultural conventions
PLATFORM_GUIDELINES: Dict[str, str] = {
    "Instagram": "Optimized for visual storytelling. Put the strongest hook on line 1 before the '...more' cut-off. Use clean line breaks and aesthetic spacing.",
    "Twitter / X": "Strictly punchy, concise, and shareable. Under 280 characters. High viral quote/repost appeal.",
    "LinkedIn": "Structured thought-leadership format. Strong hook, well-spaced lines for scanability, career/industry relevance, ending with a constructive open question.",
    "TikTok": "High-energy, trend-conscious, punchy hook designed to drive comments, debate, or video saves.",
    "Facebook": "Conversational, community-oriented, warm, asking relatable questions that prompt family and friends to reply.",
    "Pinterest": "Searchable, lifestyle-oriented, aspirational, focusing on tips, aesthetics, DIY, or inspiration.",
    "YouTube Shorts": "Fast-paced, hook-heavy, direct context that supports rapid video consumption.",
    "Threads": "Casual, conversational, real-time thoughts, conversational banter, or witty hot takes."
}

# Length constraints
LENGTH_CONSTRAINTS: Dict[str, str] = {
    "Short": "1 to 2 punchy sentences (~10 to 25 words).",
    "Medium": "3 to 5 engaging sentences (~30 to 70 words) with a hook, body, and subtle takeaway.",
    "Long": "6 to 9 rich sentences (~80 to 150 words) written as an engaging mini-story with a hook, narrative context, and a call-to-action."
}

SYSTEM_INSTRUCTION = """You are CaptionCraft AI, a world-class social media strategist, viral copywriter, and multimodal AI caption generator.
Your goal is to craft 5 unique, diverse, and authentic captions tailored to the user's specific inputs, tone, platform, and audience.

Rules:
1. Always generate exactly 5 distinct options with varying angles:
   - Option 1: The Viral Hook (attention-grabbing, high CTR)
   - Option 2: The Core Aesthetic / Emotional Vibe (mood-driven)
   - Option 3: The Storyteller / Value Drop (relatable or informative)
   - Option 4: The Witty / Conversational Take (provocative or playful)
   - Option 5: The Clean Minimalist (punchy and direct)
2. Follow the requested Tone, Platform conventions, and Length strictly.
3. If hashtags are requested, supply relevant, trending, and non-spammy tags (without '#' in the raw array or with '#', be consistent).
4. If emojis are requested, incorporate them naturally without over-cluttering.
5. You must output strictly valid JSON conforming to the requested schema. Do not wrap with conversational filler.
"""

JSON_SCHEMA_FORMAT = """{
  "captions": [
    {
      "caption": "Full formatted caption text ready to paste",
      "hook": "The punchy opening sentence",
      "vibe_label": "Short label (e.g., Viral Hook, Pure Aesthetic, Conversational)",
      "hashtags": ["tag1", "tag2", "tag3"],
      "emojis": ["✨", "🔥"],
      "cta": "Suggested call to action or engagement prompt"
    }
  ]
}"""

def build_text_to_caption_prompt(
    topic: str,
    tone: str,
    platform: str,
    length: str,
    include_hashtags: bool = True,
    hashtag_count: int = 5,
    include_emojis: bool = True,
    audience: Optional[str] = None,
    extra_notes: Optional[str] = None
) -> str:
    """Builds a structured prompt for Text-to-Caption generation."""
    tone_desc = TONE_INSTRUCTIONS.get(tone, tone)
    platform_desc = PLATFORM_GUIDELINES.get(platform, platform)
    length_desc = LENGTH_CONSTRAINTS.get(length, length)

    hashtag_instr = f"Include {hashtag_count} carefully selected, high-relevance hashtags." if include_hashtags else "Do not include any hashtags."
    emoji_instr = "Incorporate well-placed, expressive emojis naturally." if include_emojis else "Do NOT include any emojis."
    audience_instr = f"Target Audience: {audience}" if audience else "Target Audience: General social media users"
    notes_instr = f"Additional Directives: {extra_notes}" if extra_notes else ""

    prompt = f"""Generate 5 unique social media captions based on the following creative brief:

[TOPIC / CONTEXT]
{topic}

[SPECIFICATIONS]
- Platform: {platform} ({platform_desc})
- Tone: {tone} ({tone_desc})
- Length: {length} ({length_desc})
- {audience_instr}
- Hashtags: {hashtag_instr}
- Emojis: {emoji_instr}
{notes_instr}

[OUTPUT FORMAT]
Respond ONLY with a valid JSON object matching this exact structure:
{JSON_SCHEMA_FORMAT}
Ensure the JSON is strictly parseable and contains 5 distinct caption objects.
"""
    return prompt


def build_image_to_caption_prompt(
    tone: str,
    platform: str,
    length: str,
    include_hashtags: bool = True,
    hashtag_count: int = 5,
    include_emojis: bool = True,
    user_context: Optional[str] = None,
    audience: Optional[str] = None
) -> str:
    """Builds a structured prompt for Image-to-Caption generation."""
    tone_desc = TONE_INSTRUCTIONS.get(tone, tone)
    platform_desc = PLATFORM_GUIDELINES.get(platform, platform)
    length_desc = LENGTH_CONSTRAINTS.get(length, length)

    hashtag_instr = f"Include {hashtag_count} relevant hashtags." if include_hashtags else "Do not include hashtags."
    emoji_instr = "Include suitable emojis." if include_emojis else "Do not include emojis."
    context_str = f"Creator's Note / Intended Message: {user_context}" if user_context else "No extra notes provided. Infer the vibe, focal points, lighting, and narrative from the image."
    audience_instr = f"Target Audience: {audience}" if audience else ""

    prompt = f"""Examine this uploaded image carefully. Analyze its visual subjects, focal points, color palette, lighting, emotional mood, aesthetic atmosphere, and implicit narrative.

Generate 5 unique, highly engaging captions tailored to this visual:

[SPECIFICATIONS]
- Platform: {platform} ({platform_desc})
- Tone: {tone} ({tone_desc})
- Length: {length} ({length_desc})
- {context_str}
{audience_instr}
- Hashtags: {hashtag_instr}
- Emojis: {emoji_instr}

[CAPTION ANGLE REQUIREMENTS]
1. Visual Highlight (describing the key focal element poetically or wittily)
2. Mood & Vibe (reflecting the emotional energy and aesthetic)
3. Relatable / Personal Take (as if the creator is sharing a genuine moment)
4. Thought / Micro-Story (expanding on what happened before/after the photo)
5. Short & Punchy (minimalist, scroll-stopping)

[OUTPUT FORMAT]
Respond ONLY with a valid JSON object matching this exact structure:
{JSON_SCHEMA_FORMAT}
Ensure the JSON is strictly parseable and contains exactly 5 caption objects.
"""
    return prompt


def build_emoji_to_caption_prompt(
    emojis: str,
    tone: str,
    platform: str,
    length: str,
    emoji_only_mode: bool = False,
    user_context: Optional[str] = None,
    include_hashtags: bool = True,
    hashtag_count: int = 5
) -> str:
    """Builds a structured prompt for Emoji-to-Caption generation."""
    tone_desc = TONE_INSTRUCTIONS.get(tone, tone)
    platform_desc = PLATFORM_GUIDELINES.get(platform, platform)
    length_desc = LENGTH_CONSTRAINTS.get(length, length)

    context_str = f"Contextual Idea: {user_context}" if user_context else "Decode the mood, storyline, and subtext conveyed by the emoji combination."
    hashtag_instr = f"Include {hashtag_count} hashtags." if include_hashtags else "No hashtags."

    if emoji_only_mode:
        mode_instr = """EMOJI-ONLY MODE ACTIVATED:
Each caption must consist primarily of creative, thematic sequences of emojis, accompanied by an ultra-short micro-tagline (maximum 3 to 6 words) or purely inventive emoji-story combinations that convey a full narrative without long sentences."""
    else:
        mode_instr = f"""Translate the feelings, symbolism, and narrative suggested by these emojis into rich, expressive text captions fitting the {tone} tone and {length} length."""

    prompt = f"""The user has selected the following emoji sequence:
{emojis}

[CREATIVE DIRECTIVE]
{mode_instr}
{context_str}

[SPECIFICATIONS]
- Platform: {platform} ({platform_desc})
- Tone: {tone} ({tone_desc})
- Length: {length} ({length_desc})
- Hashtags: {hashtag_instr}

[OUTPUT FORMAT]
Respond ONLY with a valid JSON object matching this exact structure:
{JSON_SCHEMA_FORMAT}
Ensure the JSON is strictly parseable and contains 5 distinct caption objects.
"""
    return prompt
