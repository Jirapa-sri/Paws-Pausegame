#!/usr/bin/env python3
"""Local static + OpenAI vision proxy for Paws & Pause dog matching.

Usage:
  source .venv/bin/activate
  python match_server.py

Then open http://127.0.0.1:8765/game_demo.html
"""

from __future__ import annotations

import json
import math
import os
import re
import ssl
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)

HOST = os.getenv("MATCH_HOST", "127.0.0.1")
PORT = int(os.getenv("MATCH_PORT", "8765"))

# Prefer project models first - many keys no longer include gpt-4o-mini.
_DEFAULT_MODEL_FALLBACKS = (
    "gpt-5.6-luna",
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4o",
    "gpt-4o-mini",
)


def model_candidates() -> list[str]:
    preferred = [
        os.getenv("OPENAI_MATCH_MODEL", "").strip(),
        os.getenv("OPENAI_VISION_MODEL", "").strip(),
        os.getenv("OPENAI_LLM_MODEL", "").strip(),
        *_DEFAULT_MODEL_FALLBACKS,
    ]
    seen: set[str] = set()
    out: list[str] = []
    for name in preferred:
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


MODEL = model_candidates()[0]


def ssl_context() -> ssl.SSLContext:
    """Use certifi CA bundle so macOS Python can verify api.openai.com."""
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def openai_urlopen(req: urllib.request.Request, timeout: int = 90):
    return urllib.request.urlopen(req, timeout=timeout, context=ssl_context())


def friendly_error(err: BaseException) -> str:
    raw = str(err) or err.__class__.__name__
    low = raw.lower()
    if "insufficient permissions" in low or "missing scopes" in low or "model.request" in low:
        return (
            "This OpenAI API key cannot call models (missing model.request). "
            "In platform.openai.com create a new secret key with model access, "
            "or use an owner/writer key, put it in .env as OPENAI_API_KEY, then restart match_server.py."
        )
    if "does not have access to model" in low or "model_not_found" in low:
        return (
            "Your OpenAI project cannot use that model. "
            "Set OPENAI_MATCH_MODEL in .env to a model your project allows "
            "(this project already uses OPENAI_LLM_MODEL), then restart match_server.py."
        )
    if "certificate_verify_failed" in low or ("ssl" in low and "certificate" in low):
        return "Could not securely connect to OpenAI. Restart match_server.py and try again."
    if "timed out" in low or "timeout" in low:
        return "OpenAI took too long to reply. Check your internet and try again."
    if "failed to resolve" in low or "nodename nor servname" in low or "name or service not known" in low:
        return "No internet connection to OpenAI. Check your network and try again."
    if "tunnel connection failed" in low or "proxy" in low:
        return "Network/proxy blocked the OpenAI request. Try again off VPN or another network."
    # Strip noisy urllib wrappers like <urlopen error ...>
    cleaned = re.sub(r"^<urlopen error\s+(.*)>$", r"\1", raw.strip(), flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > 160:
        cleaned = cleaned[:157] + "..."
    return cleaned or "OpenAI request failed. Please try again."


def is_model_access_error(message: str) -> bool:
    low = (message or "").lower()
    return (
        "does not have access to model" in low
        or "model_not_found" in low
        or "invalid model" in low
        or ("model" in low and "not found" in low)
    )


def openai_chat_json(api_key: str, messages: list, *, max_tokens: int, temperature: float) -> dict:
    """Call chat completions with JSON mode, falling back across allowed models."""
    last_error = "OpenAI request failed"
    global MODEL
    for model in model_candidates():
        # Newer models (gpt-5.x / o-series) reject max_tokens; use max_completion_tokens.
        use_completion_tokens = bool(re.search(r"(gpt-5|o[1-9]|luna)", model, re.I))
        token_key = "max_completion_tokens" if use_completion_tokens else "max_tokens"
        bodies = [
            {
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": messages,
                token_key: max_tokens,
                "temperature": temperature,
            }
        ]
        # If we guessed wrong about the token param, retry once with the other key.
        alt_key = "max_tokens" if token_key == "max_completion_tokens" else "max_completion_tokens"
        bodies.append(
            {
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": messages,
                alt_key: max_tokens,
                "temperature": temperature,
            }
        )

        for body in bodies:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            try:
                with openai_urlopen(req, timeout=90) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                MODEL = model
                print(f"OpenAI vision call OK with model={model}")
                return payload
            except urllib.error.HTTPError as err:
                detail = err.read().decode("utf-8", errors="replace")
                try:
                    msg = json.loads(detail).get("error", {}).get("message") or detail
                except Exception:
                    msg = detail or str(err)
                last_error = msg
                low = msg.lower()
                if "max_tokens" in low and "max_completion_tokens" in low:
                    # Wrong token field for this model - try the alternate body.
                    continue
                if is_model_access_error(msg) or "insufficient permissions" in low or "model.request" in low:
                    print(f"Model unavailable ({model}): {msg}")
                    break
                raise RuntimeError(friendly_error(RuntimeError(msg))) from err
            except Exception as err:
                last_error = str(err)
                raise RuntimeError(friendly_error(err)) from err
    raise RuntimeError(friendly_error(RuntimeError(last_error)))

# Trait profiles for the game's adoptable breeds (adapted from my-app matching).
GAME_BREEDS = [
    {"id": "corgi", "name": "Corgi", "energy": 8, "sociability": 9, "playfulness": 9, "calmness": 5, "outdoor": 7, "affection": 9, "patience": 6, "trainability": 8},
    {"id": "golden-retriever", "name": "Golden Retriever", "energy": 8, "sociability": 10, "playfulness": 9, "calmness": 6, "outdoor": 9, "affection": 10, "patience": 8, "trainability": 9},
    {"id": "shiba-inu", "name": "Shiba Inu", "energy": 7, "sociability": 5, "playfulness": 7, "calmness": 7, "outdoor": 7, "affection": 6, "patience": 5, "trainability": 6},
    {"id": "pug", "name": "Pug", "energy": 4, "sociability": 10, "playfulness": 8, "calmness": 7, "outdoor": 4, "affection": 10, "patience": 7, "trainability": 5},
    {"id": "husky", "name": "Husky", "energy": 10, "sociability": 8, "playfulness": 9, "calmness": 3, "outdoor": 10, "affection": 7, "patience": 4, "trainability": 5},
    {"id": "dachshund", "name": "Dachshund", "energy": 6, "sociability": 7, "playfulness": 8, "calmness": 6, "outdoor": 6, "affection": 8, "patience": 5, "trainability": 5},
    {"id": "samoyed", "name": "Samoyed", "energy": 8, "sociability": 10, "playfulness": 9, "calmness": 5, "outdoor": 8, "affection": 10, "patience": 6, "trainability": 7},
    {"id": "beagle", "name": "Beagle", "energy": 8, "sociability": 9, "playfulness": 9, "calmness": 5, "outdoor": 8, "affection": 8, "patience": 6, "trainability": 6},
    {"id": "french-bulldog", "name": "French Bulldog", "energy": 4, "sociability": 9, "playfulness": 7, "calmness": 8, "outdoor": 4, "affection": 9, "patience": 7, "trainability": 6},
    {"id": "pomeranian", "name": "Pomeranian", "energy": 7, "sociability": 7, "playfulness": 8, "calmness": 5, "outdoor": 5, "affection": 8, "patience": 4, "trainability": 6},
    {"id": "mixed-rescue", "name": "Rescue Pup", "energy": 6, "sociability": 8, "playfulness": 8, "calmness": 7, "outdoor": 7, "affection": 10, "patience": 8, "trainability": 7},
]

TRAITS = ["energy", "sociability", "playfulness", "calmness", "outdoor", "affection", "patience", "trainability"]
BREED_NAMES = [b["name"] for b in GAME_BREEDS]
BREED_BY_NAME = {b["name"].lower(): b for b in GAME_BREEDS}


def trait_stats():
    stats = {}
    for trait in TRAITS:
        values = [b[trait] for b in GAME_BREEDS]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        stats[trait] = {"mean": mean, "std": math.sqrt(variance) or 1.0}
    return stats


TRAIT_STATS = trait_stats()


def normalize_api_key(raw: str | None) -> str:
    if not raw:
        return ""
    key = raw.strip()
    if len(key) >= 2 and key[0] in "\"'`[" and key[-1] in "\"'`]":
        key = key[1:-1].strip()
    return key


def api_key_error(raw: str | None) -> str | None:
    key = normalize_api_key(raw)
    if not key:
        return "Add OPENAI_API_KEY to .env, then restart match_server.py."
    if "paste-your" in key or "your-key-here" in key or len(key) < 50:
        return "Your .env still has placeholder text. Use a full OpenAI API key."
    if not key.startswith("sk-"):
        return "API key should start with sk-."
    return None


def get_top_match(personality: dict) -> dict:
    scored = []
    for breed in GAME_BREEDS:
        total = 0.0
        for trait in TRAITS:
            mean = TRAIT_STATS[trait]["mean"]
            std = TRAIT_STATS[trait]["std"]
            person_z = ((personality.get(trait, 5) or 5) - mean) / std
            breed_z = (breed[trait] - mean) / std
            total += abs(person_z - breed_z)
        score = max(0, round((1 - total / (len(TRAITS) * 0.75)) * 100))
        scored.append((score, breed))
    scored.sort(key=lambda x: x[0], reverse=True)
    score, breed = scored[0]
    return {"id": breed["id"], "name": breed["name"], "score": score}


def resolve_breed_name(ai_breed: str | None) -> dict:
    if not ai_breed:
        return BREED_BY_NAME["rescue pup"]
    normalized = ai_breed.strip().lower()
    if normalized in BREED_BY_NAME:
        return BREED_BY_NAME[normalized]
    for name, breed in BREED_BY_NAME.items():
        if name in normalized or normalized in name:
            return breed
    aliases = {
        "corgi": "corgi",
        "golden": "golden-retriever",
        "retriever": "golden-retriever",
        "shiba": "shiba-inu",
        "pug": "pug",
        "husky": "husky",
        "dachshund": "dachshund",
        "sausage": "dachshund",
        "samoyed": "samoyed",
        "beagle": "beagle",
        "french": "french-bulldog",
        "bulldog": "french-bulldog",
        "pomeranian": "pomeranian",
        "pom": "pomeranian",
        "mutt": "mixed-rescue",
        "mixed": "mixed-rescue",
        "rescue": "mixed-rescue",
    }
    for key, breed_id in aliases.items():
        if key in normalized:
            return next(b for b in GAME_BREEDS if b["id"] == breed_id)
    return BREED_BY_NAME["rescue pup"]


def parse_personality_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text or "")
    if not match:
        raise ValueError("Could not parse personality from AI response")
    return json.loads(match.group(0))


def openai_analyze(image: str, frames: list[str], api_key: str) -> dict:
    breed_list = ", ".join(BREED_NAMES)
    prompt = f"""You are matching a player photo to a spirit dog for the cozy game Paws & Pause.

Look at the person in the photo (photobooth strip and/or individual frames).
Infer their vibe/energy and score these traits from 1-10:
energy, sociability, playfulness, calmness, outdoor, affection, patience, trainability.

Also recommend one breed name that MUST be exactly one of:
{breed_list}

If a real dog is visible, identify it using the same breed list.

Return ONLY valid JSON:
{{
  "people": [
    {{
      "label": "short description",
      "appearance": "hair, clothing, vibe",
      "personality_message": "2 warm sentences about why this puppy fits them",
      "personality": {{
        "energy": 1-10, "sociability": 1-10, "playfulness": 1-10, "calmness": 1-10,
        "outdoor": 1-10, "affection": 1-10, "patience": 1-10, "trainability": 1-10
      }},
      "recommended_breed": "exact breed from list"
    }}
  ],
  "dogs": [
    {{
      "label": "short description",
      "breed": "exact breed from list",
      "personality_message": "2 warm sentences"
    }}
  ]
}}

Rules:
- people can be empty only if no human is visible
- dogs can be empty if no canine is visible
- at least one of people/dogs must have entries
- recommended_breed and breed must be exact catalog names
"""

    content = [
        {"type": "text", "text": prompt},
        {"type": "text", "text": "Photo strip / main image:"},
        {"type": "image_url", "image_url": {"url": image, "detail": "high"}},
    ]
    for i, frame in enumerate(frames[:4]):
        if not frame:
            continue
        content.append({"type": "text", "text": f"Individual frame {i + 1}:"})
        content.append({"type": "image_url", "image_url": {"url": frame, "detail": "high"}})

    payload = openai_chat_json(
        api_key,
        [{"role": "user", "content": content}],
        max_tokens=1800,
        temperature=0,
    )

    parsed = parse_personality_json(payload["choices"][0]["message"]["content"])
    people = parsed.get("people") or []
    dogs = parsed.get("dogs") or []

    results = []
    for i, entry in enumerate(people, start=1):
        personality = entry.get("personality") or {}
        # Trait z-score match (my-app style); AI recommended_breed is a soft hint only.
        match = get_top_match(personality)
        results.append(
            {
                "id": f"person-{i}",
                "type": "person",
                "label": entry.get("label") or f"Person {i}",
                "appearance": entry.get("appearance") or "",
                "message": entry.get("personality_message") or entry.get("summary") or "",
                "breedId": match["id"],
                "breedName": match["name"],
                "score": match["score"],
                "personality": personality,
            }
        )

    for i, entry in enumerate(dogs, start=1):
        breed = resolve_breed_name(entry.get("breed") or entry.get("identified_breed"))
        results.append(
            {
                "id": f"dog-{i}",
                "type": "dog",
                "label": entry.get("label") or f"Dog {i}",
                "appearance": entry.get("appearance") or "",
                "message": entry.get("personality_message") or entry.get("summary") or "",
                "breedId": breed["id"],
                "breedName": breed["name"],
                "score": 100,
                "personality": {},
            }
        )

    if not results:
        raise RuntimeError("AI found no person or dog in the photo. Try again with your face visible.")

    # Prefer a person spirit-match for adoption; fall back to identified dog.
    primary = next((r for r in results if r["type"] == "person"), results[0])
    return {"match": primary, "results": results, "subjectType": "both" if people and dogs else ("dogs" if dogs else "people")}


# Mii-style catalogs used by game_demo.html (must stay in sync).
CHAR_SKIN = ["#F7D9B6", "#F0C08A", "#D9A066", "#B87A4B", "#8C5A34", "#5C3A22"]
CHAR_HAIR = ["#3A2417", "#6B4423", "#B5651D", "#111111", "#8A5A3B", "#C98A4B"]
CHAR_OUTFIT = ["#3E7C74", "#D9705C", "#D98F2B", "#5A7FB0", "#8A6BAE", "#4A4A4A"]
CHAR_EYE = ["#3A2417", "#4A7DBF", "#6B8E6B", "#8A6BAE", "#111111", "#B5651D"]
CHAR_HAIRSTYLES = ["short", "long", "pigtails", "curly", "cap"]
CHAR_CLOTHING = ["tshirt", "dress", "overalls", "hoodie"]
CHAR_EYE_STYLES = ["round", "sleepy", "sparkle", "wink"]
CHAR_MOUTH = ["smile", "neutral", "open"]


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    raw = (value or "").strip().lstrip("#")
    if len(raw) != 6:
        return None
    try:
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError:
        return None


def nearest_hex(value: str | None, options: list[str]) -> str:
    rgb = _hex_to_rgb(value or "")
    if not rgb:
        return options[0]
    best = options[0]
    best_d = 1e18
    for opt in options:
        o = _hex_to_rgb(opt)
        if not o:
            continue
        d = (rgb[0] - o[0]) ** 2 + (rgb[1] - o[1]) ** 2 + (rgb[2] - o[2]) ** 2
        if d < best_d:
            best_d = d
            best = opt
    return best


def pick_option(value: str | None, options: list[str], default: str | None = None) -> str:
    if value and value in options:
        return value
    return default or options[0]


def sanitize_child(raw: dict | None) -> dict:
    data = raw or {}
    return {
        "skin": nearest_hex(data.get("skin"), CHAR_SKIN),
        "hair": nearest_hex(data.get("hair"), CHAR_HAIR),
        "outfit": nearest_hex(data.get("outfit"), CHAR_OUTFIT),
        "eyeColor": nearest_hex(data.get("eyeColor") or data.get("eye_color"), CHAR_EYE),
        "hairstyle": pick_option(data.get("hairstyle"), CHAR_HAIRSTYLES, "short"),
        "clothing": pick_option(data.get("clothing"), CHAR_CLOTHING, "tshirt"),
        "eyeStyle": pick_option(data.get("eyeStyle") or data.get("eye_style"), CHAR_EYE_STYLES, "round"),
        "mouthStyle": pick_option(data.get("mouthStyle") or data.get("mouth_style"), CHAR_MOUTH, "smile"),
    }


def openai_create_character(image: str, frames: list[str], api_key: str) -> dict:
    prompt = f"""You are creating a cozy Mii-style game avatar for Paws & Pause from a player selfie / photobooth strip.

Map the person's look to ONLY these catalog options (exact values required):

skin (hex): {", ".join(CHAR_SKIN)}
hair (hex): {", ".join(CHAR_HAIR)}
outfit (hex): {", ".join(CHAR_OUTFIT)}
eyeColor (hex): {", ".join(CHAR_EYE)}
hairstyle: {", ".join(CHAR_HAIRSTYLES)}
clothing: {", ".join(CHAR_CLOTHING)}
eyeStyle: {", ".join(CHAR_EYE_STYLES)}
mouthStyle: {", ".join(CHAR_MOUTH)}

Rules:
- Prefer the closest catalog colors to what you see
- Infer hairstyle / clothing / eye vibe from the photo; if unclear, pick a cozy default
- suggestedName: short friendly first name (max 12 letters). Prefer English, or Thai if that fits the player better. Not a celebrity name.
- title: short island role like "New Islander", "Harbor Wanderer", "Café Dreamer" (English)
- motto: one warm sentence for their Willow Isle ID card (English)
- summary: 1-2 sentences describing the Mii you built (English, clear and friendly)

Return ONLY valid JSON:
{{
  "suggestedName": "Juniper",
  "child": {{
    "skin": "#F0C08A",
    "hair": "#3A2417",
    "outfit": "#3E7C74",
    "hairstyle": "short",
    "clothing": "hoodie",
    "eyeStyle": "round",
    "eyeColor": "#3A2417",
    "mouthStyle": "smile"
  }},
  "idCard": {{
    "title": "New Islander",
    "motto": "Soft mornings and kinder days."
  }},
  "summary": "..."
}}
"""

    content = [
        {"type": "text", "text": prompt},
        {"type": "text", "text": "Photo strip / main image:"},
        {"type": "image_url", "image_url": {"url": image, "detail": "high"}},
    ]
    for i, frame in enumerate(frames[:4]):
        if not frame:
            continue
        content.append({"type": "text", "text": f"Individual frame {i + 1}:"})
        content.append({"type": "image_url", "image_url": {"url": frame, "detail": "high"}})

    payload = openai_chat_json(
        api_key,
        [{"role": "user", "content": content}],
        max_tokens=900,
        temperature=0.2,
    )

    parsed = parse_personality_json(payload["choices"][0]["message"]["content"])
    child = sanitize_child(parsed.get("child") or {})
    suggested = re.sub(r"[^\w\s\-'.]", "", str(parsed.get("suggestedName") or "Friend"), flags=re.UNICODE).strip() or "Friend"
    suggested = re.sub(r"\s+", " ", suggested)[:16]
    id_card = parsed.get("idCard") or parsed.get("id_card") or {}
    title = str(id_card.get("title") or "New Islander").strip()[:28] or "New Islander"
    motto = str(id_card.get("motto") or "Soft mornings and kinder days.").strip()[:90]
    summary = str(parsed.get("summary") or "Your Willow Isle look is ready.").strip()[:220]
    return {
        "suggestedName": suggested,
        "child": child,
        "idCard": {"title": title, "motto": motto},
        "summary": summary,
    }


TAROT_DECK = [
    ("The Sun", "warmth, clarity, play"),
    ("The Moon", "dreams, soft mystery"),
    ("The Star", "hope, gentle guidance"),
    ("The Fool", "new beginnings, curiosity"),
    ("Temperance", "balance, patience"),
    ("Strength", "quiet courage"),
    ("The Hermit", "reflection, cozy solitude"),
    ("Wheel of Fortune", "change, surprise luck"),
    ("The Magician", "craft, intention"),
    ("Ace of Cups", "kindness, friendship"),
    ("Ace of Wands", "spark, energy"),
    ("Two of Pentacles", "juggling, soft rhythm"),
]

NEWS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
]


def fetch_real_world_headline() -> dict:
    """Pick one real headline from a public news RSS feed."""
    import random
    import xml.etree.ElementTree as ET

    errors = []
    for url in NEWS_FEEDS:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "PawsPauseMorningBrief/1.0"},
                method="GET",
            )
            with openai_urlopen(req, timeout=12) as resp:
                xml_text = resp.read().decode("utf-8", errors="replace")
            root = ET.fromstring(xml_text)
            items = []
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = (item.findtext("description") or "").strip()
                desc = re.sub(r"<[^>]+>", "", desc)
                desc = re.sub(r"\s+", " ", desc).strip()
                if title:
                    items.append({"title": title, "url": link, "blurb": desc[:280]})
            if items:
                pick = random.choice(items[:12])
                source = "BBC" if "bbc" in url else ("NYT" if "nytimes" in url else "Reuters")
                return {
                    "title": pick["title"][:140],
                    "url": pick.get("url") or "",
                    "blurb": pick.get("blurb") or pick["title"],
                    "source": source,
                }
        except Exception as err:
            errors.append(f"{url}: {err}")
            continue
    return {
        "title": "Islanders pause for a quiet morning",
        "url": "",
        "blurb": "Could not reach live world news feeds, so Willow Isle shares a cozy placeholder headline.",
        "source": "Willow Isle Gazette",
        "offline": True,
        "errors": errors[:2],
    }


def local_morning_brief(day: int, player_name: str, headline: dict) -> dict:
    import random

    card, vibe = random.choice(TAROT_DECK)
    upright = random.random() > 0.22
    weather = random.choice(["clear", "soft", "rain"])
    mood_map = {
        "clear": "bright and open-hearted",
        "soft": "gentle and contemplative",
        "rain": "cozy and reflective",
    }
    island_bits = [
        "The café put out cinnamon rolls before sunrise.",
        "Mara found sea glass by the harbour path.",
        "A stray balloon drifted over the plaza.",
        "Theo tuned the concert lights for tonight.",
        "Ducklings practiced circles on the lake.",
        "Someone left a flower crown on the store porch.",
    ]
    mini = None
    if random.random() < 0.55:
        mini_by_weather = {
            "clear": {"id": "balloon-tap", "title": "Sky Balloon", "blurb": "Keep the plaza balloon aloft with quick taps."},
            "soft": {"id": "petal-catch", "title": "Petal Drift", "blurb": "Catch soft petals before they settle."},
            "rain": {"id": "puddle-hop", "title": "Puddle Hop", "blurb": "Splash the shiny puddles in order."},
        }
        mini = mini_by_weather[weather]
    return {
        "tarot": {
            "card": card,
            "upright": upright,
            "vibe": vibe,
            "reading": (
                f"{card} {'upright' if upright else 'reversed'} greets {player_name or 'you'}. "
                f"Today leans {mood_map[weather]} - follow the {vibe}."
            ),
        },
        "weather": weather,
        "mood": mood_map[weather],
        "islandNews": random.choice(island_bits) + f" Day {day} on Willow Isle feels {mood_map[weather]}.",
        "worldNews": {
            "title": headline.get("title") or "Quiet morning news",
            "summary": (
                f"One story from beyond the island ({headline.get('source', 'News')}): "
                f"{headline.get('blurb') or headline.get('title')}"
            )[:320],
            "source": headline.get("source") or "News",
            "url": headline.get("url") or "",
        },
        "miniEvent": mini,
    }


def openai_morning_brief(api_key: str, day: int, player_name: str, headline: dict) -> dict:
    import random

    card, vibe = random.choice(TAROT_DECK)
    upright = random.random() > 0.22
    prompt = f"""You are the cozy morning fortune teller for the game Paws & Pause on Willow Isle.

Player: {player_name or 'Friend'}
Day: {day}
Drawn tarot: {card} ({'upright' if upright else 'reversed'}) - vibe hint: {vibe}

Real-world headline (TRUE news - summarize only this one, do not invent facts):
Title: {headline.get('title')}
Source: {headline.get('source')}
Blurb: {headline.get('blurb')}

Return ONLY JSON:
{{
  "weather": "clear" | "soft" | "rain",
  "mood": "short mood phrase",
  "tarotReading": "2 warm sentences linking the card to today's island mood and weather",
  "islandNews": "1-2 sentences of cozy fictional Willow Isle news that fits the weather/mood",
  "worldSummary": "2 short sentences summarizing ONLY the real headline above for a cozy game bulletin",
  "miniEvent": null or {{ "id": "balloon-tap"|"petal-catch"|"puddle-hop", "title": "...", "blurb": "..." }}
}}

Rules:
- weather MUST be exactly clear, soft, or rain
- Link tarot tone to weather (sun/star/clear often clear; moon/hermit often soft; wheel/cups can be rain)
- miniEvent about 50% of the time; match id to weather (clear=balloon-tap, soft=petal-catch, rain=puddle-hop)
- Keep language friendly, English, no emojis
"""
    payload = openai_chat_json(
        api_key,
        [{"role": "user", "content": prompt}],
        max_tokens=700,
        temperature=0.7,
    )
    parsed = parse_personality_json(payload["choices"][0]["message"]["content"])
    weather = str(parsed.get("weather") or "soft").strip().lower()
    if weather not in ("clear", "soft", "rain"):
        weather = "soft"
    mini = parsed.get("miniEvent")
    if mini is False:
        mini = None
    if isinstance(mini, dict):
        mid = str(mini.get("id") or "")
        if mid not in ("balloon-tap", "petal-catch", "puddle-hop"):
            mid = {"clear": "balloon-tap", "soft": "petal-catch", "rain": "puddle-hop"}[weather]
        mini = {
            "id": mid,
            "title": str(mini.get("title") or "Morning Mini Event")[:40],
            "blurb": str(mini.get("blurb") or "A small island happening.")[:120],
        }
    else:
        mini = None
    return {
        "tarot": {
            "card": card,
            "upright": upright,
            "vibe": vibe,
            "reading": str(parsed.get("tarotReading") or f"{card} sets a {weather} day.").strip()[:320],
        },
        "weather": weather,
        "mood": str(parsed.get("mood") or "soft-hearted").strip()[:60],
        "islandNews": str(parsed.get("islandNews") or "The island wakes gently.").strip()[:320],
        "worldNews": {
            "title": headline.get("title") or "World news",
            "summary": str(parsed.get("worldSummary") or headline.get("blurb") or "").strip()[:360],
            "source": headline.get("source") or "News",
            "url": headline.get("url") or "",
        },
        "miniEvent": mini,
    }


def build_morning_brief(api_key: str, day: int, player_name: str) -> dict:
    headline = fetch_real_world_headline()
    if not api_key:
        return local_morning_brief(day, player_name, headline)
    try:
        return openai_morning_brief(api_key, day, player_name, headline)
    except Exception as err:
        brief = local_morning_brief(day, player_name, headline)
        brief["aiError"] = friendly_error(err)
        return brief


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def guess_type(self, path):
        ctype = super().guess_type(path)
        if ctype == "text/html":
            return "text/html; charset=utf-8"
        if ctype == "text/css":
            return "text/css; charset=utf-8"
        if ctype in ("text/javascript", "application/javascript"):
            return "application/javascript; charset=utf-8"
        return ctype

    def do_OPTIONS(self):
        if self.path.startswith("/api/"):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self):
        path = self.path.rstrip("/")
        if path not in ("/api/match-dog", "/api/create-character", "/api/morning-brief"):
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "Invalid JSON body"})

        api_key = normalize_api_key(os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY"))

        if path == "/api/morning-brief":
            day = int(payload.get("day") or 1)
            player_name = str(payload.get("playerName") or "Friend")[:24]
            # Morning brief still works offline if the key is missing.
            key_err = api_key_error(os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY"))
            try:
                result = build_morning_brief("" if key_err else api_key, day, player_name)
                return self._json(200, result)
            except Exception as err:
                return self._json(500, {"error": friendly_error(err)})

        key_err = api_key_error(os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY"))
        if key_err:
            return self._json(500, {"error": key_err})

        image = payload.get("image")
        frames = payload.get("frames") or []
        if not image and frames:
            image = frames[0]
        if not image:
            return self._json(400, {"error": "Missing photo. Take a photobooth strip first."})

        try:
            if path == "/api/create-character":
                result = openai_create_character(image, frames, api_key)
            else:
                result = openai_analyze(image, frames, api_key)
            return self._json(200, result)
        except Exception as err:
            return self._json(500, {"error": friendly_error(err)})

    def _json(self, status: int, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    key_err = api_key_error(os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY"))
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Paws & Pause match server on http://{HOST}:{PORT}/game_demo.html")
    if key_err:
        print("Warning:", key_err)
    else:
        print("OpenAI key loaded. Trying models:", ", ".join(model_candidates()[:5]), "...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
