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


# =====================================================================
# Feature 3: Viral Caption Analyzer & Improver Templates
# =====================================================================

VIRAL_ANALYZER_SCHEMA = """{
  "overall_score": 82,
  "scores": {
    "hook_strength": {
      "score": 21,
      "max": 25,
      "reason": "Strong curiosity gap in opening line that hooks the audience before scrolling."
    },
    "readability": {
      "score": 18,
      "max": 20,
      "reason": "Clean formatting, scannable sentence lengths, and natural cadence."
    },
    "emotional_appeal": {
      "score": 16,
      "max": 20,
      "reason": "Evokes relatable sentiment and emotional connection."
    },
    "cta_effectiveness": {
      "score": 12,
      "max": 15,
      "reason": "Direct call to action that encourages comments or saves."
    },
    "platform_relevance": {
      "score": 15,
      "max": 20,
      "reason": "Aligns well with the conventions, hashtags, and culture of the selected platform."
    }
  },
  "verdict": "High engagement potential with punchy hook and clear message.",
  "strengths": [
    "Magnetic first line that stands out in busy feeds",
    "Effective pacing with natural line breaks",
    "Authentic tone that resonates with target audience"
  ],
  "weaknesses": [
    "Call to action could be slightly more specific",
    "Hashtag distribution could include more niche community tags"
  ],
  "suggestions": [
    "Ask a specific question in the final sentence to trigger comment debate",
    "Tighten the second sentence to accelerate reading velocity",
    "Add 2 high-intent niche hashtags for better algorithmic discovery"
  ]
}"""

IMPROVE_CAPTION_SCHEMA = """{
  "original_caption": "Text of the original caption",
  "improved_caption": "Complete improved caption ready to paste",
  "hook": "The improved opening hook sentence",
  "hashtags": ["tag1", "tag2", "tag3"],
  "emojis": ["✨", "🔥"],
  "cta": "Improved call to action",
  "improvement_summary": "Summary of enhancements made to boost CTR and retention",
  "changes_made": [
    "Shortened the hook by 4 words for higher punch",
    "Added mobile-scannable line breaks",
    "Strengthened the CTA from passive to active"
  ]
}"""


def build_viral_analyzer_prompt(
    caption: str,
    platform: str = "Instagram",
    tone: str = "Aesthetic"
) -> str:
    """Builds a structured prompt to evaluate caption engagement across 5 categories."""
    platform_desc = PLATFORM_GUIDELINES.get(platform, platform)
    tone_desc = TONE_INSTRUCTIONS.get(tone, tone)

    prompt = f"""You are CaptionCraft AI's Senior Viral Content Strategist and Social Algorithm Expert.
Carefully analyze this social media caption:

[CAPTION TO ANALYZE]
\"\"\"{caption}\"\"\"

[CONTEXT]
- Platform: {platform} ({platform_desc})
- Intended Tone: {tone} ({tone_desc})

[SCORING CRITERIA — 100 POINTS TOTAL]
Evaluate strictly across these 5 dimensions:
1. Hook Strength (Max 25 points): Does line 1 trigger curiosity, pattern interruption, or high CTR before the fold?
2. Readability (Max 20 points): Is the sentence length, white space, and visual rhythm effortless to consume on mobile?
3. Emotional Appeal (Max 20 points): Does it stimulate genuine emotion (relatability, inspiration, humor, curiosity)?
4. CTA Effectiveness (Max 15 points): Is the call to action clear, friction-free, and enticing for comments, shares, or saves?
5. Platform Relevance (Max 20 points): Does it strictly respect {platform} cultural norms, character dynamics, and hashtag usage?

Sum the 5 scores to calculate `overall_score` (0-100).

[OUTPUT FORMAT]
Respond ONLY with a valid JSON object matching this exact structure:
{VIRAL_ANALYZER_SCHEMA}
Ensure all keys are present and the JSON is strictly parseable.
"""
    return prompt


def build_caption_improvement_prompt(
    caption: str,
    action: str,
    platform: str = "Instagram",
    tone: str = "Creative"
) -> str:
    """Builds a structured prompt to rewrite/polish a caption based on a specific directive."""
    platform_desc = PLATFORM_GUIDELINES.get(platform, platform)
    tone_desc = TONE_INSTRUCTIONS.get(tone, tone)

    action_directives = {
        "engaging": "Make this caption significantly more magnetic, vibrant, and conversational. Elevate emotional resonance, punch up the narrative, and make it irresistible to react to.",
        "stronger_hook": "Completely transform the opening line into a viral, scroll-stopping hook that creates intense curiosity, asks a provocative question, or delivers a bold contrarian statement before the fold.",
        "shorter": "Ruthlessly edit this caption to be concise, punchy, and minimalist. Cut out all filler words and tighten sentence structure while preserving core essence and maximum impact.",
        "better_cta": "Craft a high-conversion, organic call to action. Prompt meaningful comments, debate, saves, or shares naturally without sounding pushy or salesy.",
        "platform_optimize": f"Optimally reformat and adjust this caption specifically for {platform}. Apply {platform}'s native formatting, white-space cadence, tag culture, and algorithm preferences."
    }

    directive = action_directives.get(action, action_directives["engaging"])

    prompt = f"""You are an elite copy editor and social media copywriter.
Take this caption and polish it according to the directive below:

[ORIGINAL CAPTION]
\"\"\"{caption}\"\"\"

[IMPROVEMENT DIRECTIVE]
{directive}

[TARGET SPECIFICATIONS]
- Platform: {platform} ({platform_desc})
- Tone: {tone} ({tone_desc})

[OUTPUT FORMAT]
Respond ONLY with a valid JSON object matching this exact structure:
{IMPROVE_CAPTION_SCHEMA}
Ensure all keys are populated and the JSON is strictly parseable.
"""
    return prompt


# =====================================================================
# Feature 4: One-Click Multi-Platform Generator Templates
# =====================================================================

MULTI_PLATFORM_SCHEMA = """{
  "platforms": {
    "Instagram": {
      "caption": "Full Instagram formatted caption with aesthetic spacing and line breaks",
      "hook": "Magnetic line 1 hook before ...more",
      "hashtags": ["aesthetic", "creator", "lifestyle", "dailyvibe", "growth"],
      "emojis": ["✨", "📸"],
      "cta": "Double tap if you feel this, and save for later! 👇",
      "char_count": 185,
      "platform_tip": "Placed the strongest hook on line 1 before the 125-char cutoff."
    },
    "Twitter / X": {
      "caption": "Punchy tweet under 280 characters with high quote-tweet appeal.",
      "hook": "Unfiltered truth: the best time to start was yesterday.",
      "hashtags": ["mindset"],
      "emojis": ["⚡"],
      "cta": "Retweet if you needed this reminder today.",
      "char_count": 142,
      "platform_tip": "Kept under 280 characters for viral retweet momentum."
    },
    "LinkedIn": {
      "caption": "Thought leadership post with structured spacing and professional reflection.\\n\\nKey insight for builders...\\n\\nWhat has been your experience?",
      "hook": "Most people think success is linear. Here is what 5 years taught me:",
      "hashtags": ["leadership", "innovation", "strategy"],
      "emojis": ["💡"],
      "cta": "What's one lesson you'd add? Let's discuss in the comments below.",
      "char_count": 420,
      "platform_tip": "Engineered with scannable one-sentence paragraphs for mobile feeds."
    },
    "TikTok": {
      "caption": "Wait till the end because this changed everything... 🤯 #lifehack #creators",
      "hook": "Stop scrolling if you need to hear this today:",
      "hashtags": ["fyp", "viral", "foryou", "contentcreator"],
      "emojis": ["🔥", "👀"],
      "cta": "Follow for part 2 and save this!",
      "char_count": 95,
      "platform_tip": "Fast-paced hook designed to boost 3-second video retention."
    },
    "Threads": {
      "caption": "A quick thought that's been lingering with me all morning... what's everyone's take on this?",
      "hook": "Hot take of the day:",
      "hashtags": [],
      "emojis": ["💭"],
      "cta": "Thoughts on this?",
      "char_count": 115,
      "platform_tip": "Casual, low-friction conversational prompt ideal for replies."
    }
  }
}"""


def build_multi_platform_prompt(
    topic: str,
    platforms: List[str],
    tone: str,
    length: str = "Medium",
    include_hashtags: bool = True,
    hashtag_count: int = 5,
    user_context: Optional[str] = None,
    audience: Optional[str] = None
) -> str:
    """Builds a structured prompt to generate platform-native captions for multiple platforms in one pass."""
    tone_desc = TONE_INSTRUCTIONS.get(tone, tone)
    length_desc = LENGTH_CONSTRAINTS.get(length, length)

    platform_notes = []
    for p in platforms:
        p_guide = PLATFORM_GUIDELINES.get(p, "")
        platform_notes.append(f"- {p}: {p_guide}")
    platform_spec_str = "\n".join(platform_notes)

    hashtag_instr = f"Include up to {hashtag_count} platform-appropriate hashtags." if include_hashtags else "Do not include hashtags."
    context_str = f"Creator Context / Notes: {user_context}" if user_context else ""
    aud_str = f"Target Audience: {audience}" if audience else ""

    prompt = f"""You are CaptionCraft AI's Omnichannel Content Strategist.
Generate distinct, platform-native social media captions based on this creative concept:

[TOPIC / CONCEPT]
{topic}
{context_str}
{aud_str}

[GLOBAL SETTINGS]
- Tone: {tone} ({tone_desc})
- Length: {length} ({length_desc})
- Hashtags: {hashtag_instr}

[PLATFORM GUIDELINES — GENERATE FOR EACH OF THESE REQUESTED PLATFORMS]
{platform_spec_str}

CRITICAL RULES:
1. Do NOT generate the same text with different tags. Each platform must receive an authentically written caption matching that platform's native voice, culture, and formatting.
2. Twitter / X MUST strictly be under 280 characters.
3. LinkedIn MUST feature professional line-spaced paragraphs and a discussion question.
4. Instagram MUST optimize for the line 1 hook before the fold.
5. TikTok MUST feature high energy and curiosity hooks.
6. Threads MUST be casual, conversational, and direct.

[OUTPUT FORMAT]
Respond ONLY with a valid JSON object matching this structure:
{{
  "platforms": {{
    {", ".join([f'"{p}": {{ "caption": "...", "hook": "...", "hashtags": ["..."], "emojis": ["..."], "cta": "...", "char_count": 0, "platform_tip": "..." }}' for p in platforms])}
  }}
}}
Ensure all requested platforms ({', '.join(platforms)}) are included as top-level keys under "platforms".
"""
    return prompt


# =====================================================================
# Feature 5: AI Multi-Image Carousel & Photo Dump Generator Templates
# =====================================================================

CAROUSEL_SCHEMA = """{
  "theme_title": "Visual Story Title",
  "master_caption": "Complete carousel post caption summarizing the journey, ready to paste into Instagram or LinkedIn.",
  "master_hashtags": ["carousel", "visualstory", "photojourney", "creative", "moments"],
  "master_cta": "Swipe through the full story and let me know your favorite slide in the comments! 📲",
  "slides": [
    {
      "slide_number": 1,
      "slide_type": "Cover Hook",
      "title": "Magnetic Cover Title (3-6 words)",
      "caption": "Opening slide narration that stops the scroll and hooks the reader to swipe right.",
      "overlay_text": "Short punchy text to overlay on image 1 (max 6 words)",
      "visual_connection": "How this connects to the subject, lighting, and mood of Photo 1"
    },
    {
      "slide_number": 2,
      "slide_type": "Story Progression",
      "title": "Milestone or Turning Point",
      "caption": "Narrative continuation exploring the context or emotional depth of the moment.",
      "overlay_text": "Key takeaway or micro-insight",
      "visual_connection": "Visual details spotted in Photo 2"
    },
    {
      "slide_number": 3,
      "slide_type": "Closing & CTA",
      "title": "The Takeaway",
      "caption": "Strong reflective conclusion inviting audience interaction.",
      "overlay_text": "Save this post 🔖",
      "visual_connection": "Final takeaway and closing mood of Photo 3"
    }
  ]
}"""


def build_carousel_storyteller_prompt(
    num_slides: int,
    tone: str,
    platform: str = "Instagram",
    topic_context: Optional[str] = None,
    audience: Optional[str] = None
) -> str:
    """Builds a structured prompt for multi-image visual carousel storytelling."""
    tone_desc = TONE_INSTRUCTIONS.get(tone, tone)
    platform_desc = PLATFORM_GUIDELINES.get(platform, platform)
    context_str = f"Creator's Story Notes: {topic_context}" if topic_context else "Infer the storyline and emotional arc from the sequence of photos."
    aud_str = f"Target Audience: {audience}" if audience else ""

    prompt = f"""You are CaptionCraft AI's Visual Storyteller and Carousel Director.
You have been provided with an ordered sequence of {num_slides} photos uploaded by the creator.

Carefully inspect all {num_slides} images in sequence. Analyze their visual progression, lighting, mood, subjects, and implicit emotional journey.

[SPECIFICATIONS]
- Platform: {platform} ({platform_desc})
- Tone: {tone} ({tone_desc})
- {context_str}
{aud_str}

[CAROUSEL STRUCTURE REQUIREMENTS]
Generate a seamless, high-engagement visual narrative across all {num_slides} slides:
- Slide 1 (Cover Hook): High-CTR title, scroll-stopping visual hook that creates intense curiosity to swipe.
- Slides 2 to {num_slides - 1} (Story Progression): Meaningful transitions, narrative milestones, micro-story beats, and suggested 3-6 word text overlays for each photo.
- Slide {num_slides} (Final CTA): Emotional punchline or high-value conclusion with an active engagement prompt (Save, Share, Comment, Follow).
- Master Post Caption: A cohesive post-level caption that ties the entire carousel together with formatted line breaks and top hashtags.

[OUTPUT FORMAT]
Respond ONLY with a valid JSON object matching this structure:
{CAROUSEL_SCHEMA}
Ensure the `slides` array contains exactly {num_slides} slide objects, matching the {num_slides} provided images in exact order.
"""
    return prompt


def build_carousel_single_slide_prompt(
    slide_index: int,
    total_slides: int,
    current_storyline: str,
    tone: str,
    platform: str = "Instagram"
) -> str:
    """Builds a prompt to regenerate a single slide within an existing carousel narrative."""
    tone_desc = TONE_INSTRUCTIONS.get(tone, tone)

    prompt = f"""You are CaptionCraft AI's Visual Storyteller.
Regenerate ONLY Slide #{slide_index} (out of {total_slides} total slides) for an ongoing social carousel.

[CURRENT STORYLINE CONTEXT]
{current_storyline}

[SPECIFICATIONS]
- Target Slide: #{slide_index} of {total_slides}
- Platform: {platform}
- Tone: {tone} ({tone_desc})

[OUTPUT FORMAT]
Respond ONLY with a valid JSON object matching this single slide structure:
{{
  "slide_number": {slide_index},
  "slide_type": "{'Cover Hook' if slide_index == 1 else ('Closing & CTA' if slide_index == total_slides else 'Story Progression')}",
  "title": "Fresh Headline (3-6 words)",
  "caption": "Polished, engaging narration tailored for this specific slide position.",
  "overlay_text": "Short punchy text overlay for the photo (max 6 words)",
  "visual_connection": "Why this narrative resonates with the image"
}}
"""
    return prompt
