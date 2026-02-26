# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utility functions for interacting with Gemini and Claude APIs, image processing, and PDF handling.
"""

import json
import asyncio
import base64
import urllib.parse
import time
from io import BytesIO
from functools import partial
from ast import literal_eval
from typing import List, Dict, Any

import aiofiles
import requests
from PIL import Image
from google import genai
from google.genai import types
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

import os
import re

import yaml
from pathlib import Path

# Load config
config_path = Path(__file__).parent.parent / "configs" / "model_config.yaml"
model_config = {}
if config_path.exists():
    with open(config_path, "r") as f:
        model_config = yaml.safe_load(f) or {}

def get_config_val(section, key, env_var, default=""):
    val = os.getenv(env_var)
    if not val and section in model_config:
        val = model_config[section].get(key)
    return val or default

# Initialize clients lazily. Resolve credentials from env first, then yaml.
_gemini_client = None
_gemini_key = None

def get_gemini_client():
    global _gemini_client, _gemini_key
    api_key = get_config_val("api_keys", "google_api_key", "GOOGLE_API_KEY", "")
    if not api_key:
        return None
    if _gemini_client is None or _gemini_key != api_key:
        _gemini_client = genai.Client(api_key=api_key)
        _gemini_key = api_key
    return _gemini_client


_anthropic_client = None
_anthropic_key = None

def get_anthropic_client():
    global _anthropic_client, _anthropic_key
    api_key = get_config_val("api_keys", "anthropic_api_key", "ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    if _anthropic_client is None or _anthropic_key != api_key:
        _anthropic_client = AsyncAnthropic(api_key=api_key)
        _anthropic_key = api_key
    return _anthropic_client


_openai_clients = {}

def _openai_lane_env(lane: str):
    lane = (lane or "text").strip().lower()
    if lane == "image":
        key = (os.getenv("OPENAI_IMAGE_API_KEY") or "").strip()
        base_url = (os.getenv("OPENAI_IMAGE_BASE_URL") or "").strip() or None
    else:
        key = (os.getenv("OPENAI_TEXT_API_KEY") or "").strip()
        base_url = (os.getenv("OPENAI_TEXT_BASE_URL") or "").strip() or None
    return key, base_url

def get_openai_client(lane: str = "text"):
    api_key, base_url = _openai_lane_env(lane)
    if not api_key:
        api_key = get_config_val("api_keys", "openai_api_key", "OPENAI_API_KEY", "")
        base_url = (os.getenv("OPENAI_BASE_URL") or "").strip() or None

    if not api_key:
        return None

    cache_key = (api_key, base_url)
    client = _openai_clients.get(cache_key)
    if client is None:
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        # Avoid very long hangs on unstable upstream endpoints.
        kwargs["timeout"] = 120
        client = AsyncOpenAI(**kwargs)
        _openai_clients[cache_key] = client
    return client

def _convert_to_gemini_parts(contents: List[Dict[str, Any]]) -> List[types.Part]:
    """
    Convert a generic content list to a list of Gemini's genai.types.Part objects.
    """
    gemini_parts = []
    for item in contents:
        if item.get("type") == "text":
            gemini_parts.append(types.Part.from_text(text=item["text"]))
        elif item.get("type") == "image":
            source = item.get("source", {})
            if source.get("type") == "base64":
                gemini_parts.append(
                    types.Part.from_bytes(
                        data=base64.b64decode(source["data"]),
                        mime_type=source["media_type"],
                    )
                )
    return gemini_parts


def _normalize_contents(contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize legacy content items to a unified format used by all providers."""
    normalized = []
    for item in (contents or []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "image" and item.get("image_base64"):
            normalized.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": item.get("image_base64"),
                    },
                }
            )
        else:
            normalized.append(item)
    return normalized


def strip_reasoning_trace(text: str) -> str:
    """Remove visible reasoning traces (e.g. <think>...</think>) from model outputs."""
    if not isinstance(text, str):
        return text

    cleaned = text
    # Remove explicit think blocks.
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE)
    # Remove markdown reasoning blocks if present.
    cleaned = re.sub(r"```(?:think|thinking|reasoning)[\s\S]*?```", "", cleaned, flags=re.IGNORECASE)
    # Trim common leaked prefixes.
    cleaned = re.sub(r"^\s*(?:Thoughts?|Reasoning|Analysis)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


async def call_gemini_with_retry_async(
    model_name, contents, config, max_attempts=5, retry_delay=5, error_context=""
):
    """
    ASYNC: Call Gemini API with asynchronous retry logic.
    """
    result_list = []
    target_candidate_count = config.candidate_count
    # Gemini API max candidate count is 8. We will call multiple times if needed.
    if config.candidate_count > 8:
        config.candidate_count = 8

    current_contents = contents
    for attempt in range(max_attempts):
        try:
            client = get_gemini_client()
            if client is None:
                raise ValueError("Gemini client not initialized (missing GOOGLE_API_KEY)")
            
            # Convert generic content list to Gemini's format right before the API call
            gemini_contents = _convert_to_gemini_parts(current_contents)
            response = await client.aio.models.generate_content(
                model=model_name, contents=gemini_contents, config=config
            )

            # If we are using Image Generation models to generate images
            if (
                "nanoviz" in model_name
                or "image" in model_name
            ):
                raw_response_list = []
                if not response.candidates or not response.candidates[0].content.parts:
                    print(
                        f"[Warning]: Failed to generate image, retrying in {retry_delay} seconds..."
                    )
                    await asyncio.sleep(retry_delay)
                    continue

                # In this mode, we can only have one candidate
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        # Append base64 encoded image data to raw_response_list
                        raw_response_list.append(
                            base64.b64encode(part.inline_data.data).decode("utf-8")
                        )
                        break

            # Otherwise, for text generation models
            else:
                raw_response_list = [
                    part.text
                    for candidate in response.candidates
                    for part in candidate.content.parts
                ]
            result_list.extend([r for r in raw_response_list if r.strip() != ""])
            if len(result_list) >= target_candidate_count:
                result_list = result_list[:target_candidate_count]
                break

        except Exception as e:
            context_msg = f" for {error_context}" if error_context else ""
            
            # Exponential backoff (capped at 30s)
            current_delay = min(retry_delay * (2 ** attempt), 30)
            
            print(
                f"Attempt {attempt + 1} for model {model_name} failed{context_msg}: {e}. Retrying in {current_delay} seconds..."
            )

            if attempt < max_attempts - 1:
                await asyncio.sleep(current_delay)
            else:
                print(f"Error: All {max_attempts} attempts failed{context_msg}")
                result_list = ["Error"] * target_candidate_count

    if len(result_list) < target_candidate_count:
        result_list.extend(["Error"] * (target_candidate_count - len(result_list)))
    return result_list

def _convert_to_claude_format(contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converts the generic content list to Claude's API format.
    Currently, the formats are identical, so this acts as a pass-through
    for architectural consistency and future-proofing.

    Claude API's format:
    [
        {"type": "text", "text": "some text"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}},
        ...
    ]
    """
    return contents


def _convert_to_openai_format(contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converts the generic content list (Claude format) to OpenAI's API format.
    
    Claude format:
    [
        {"type": "text", "text": "some text"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}},
        ...
    ]
    
    OpenAI format:
    [
        {"type": "text", "text": "some text"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
        ...
    ]
    """
    openai_contents = []
    for item in contents:
        if item.get("type") == "text":
            openai_contents.append({"type": "text", "text": item["text"]})
        elif item.get("type") == "image":
            source = item.get("source", {})
            if source.get("type") == "base64":
                media_type = source.get("media_type", "image/jpeg")
                data = source.get("data", "")
                # OpenAI expects data URL format
                data_url = f"data:{media_type};base64,{data}"
                openai_contents.append({
                    "type": "image_url",
                    "image_url": {"url": data_url}
                })
    return openai_contents


async def call_claude_with_retry_async(
    model_name, contents, config, max_attempts=5, retry_delay=30, error_context=""
):
    """
    ASYNC: Call Claude API with asynchronous retry logic.
    This version efficiently handles input size errors by validating and modifying
    the content list once before generating all candidates.
    """
    system_prompt = config["system_prompt"]
    temperature = config["temperature"]
    candidate_num = config["candidate_num"]
    max_output_tokens = config["max_output_tokens"]
    response_text_list = []

    # --- Preparation Phase ---
    # Convert to the Claude-specific format and perform an initial optimistic resize.
    current_contents = contents

    # --- Validation and Remediation Phase ---
    # We loop until we get a single successful response, proving the input is valid.
    # Note that this check is required because Claude only has 128k / 256k context windows.
    # For Gemini series that support 1M, we do not need this step.
    is_input_valid = False
    for attempt in range(max_attempts):
        try:
            claude_contents = _convert_to_claude_format(current_contents)
            # Attempt to generate the very first candidate.
            client = get_anthropic_client()
            if client is None:
                raise ValueError("Anthropic client not initialized (missing ANTHROPIC_API_KEY)")
            first_response = await client.messages.create(
                model=model_name,
                max_tokens=max_output_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": claude_contents}],
                system=system_prompt,
            )
            response_text_list.append(first_response.content[0].text)
            is_input_valid = True
            break

        except Exception as e:
            error_str = str(e).lower()
            context_msg = f" for {error_context}" if error_context else ""
            print(
                f"Validation attempt {attempt + 1} failed{context_msg}: {error_str}. Retrying in {retry_delay} seconds..."
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(retry_delay)

    # --- Sampling Phase ---
    if not is_input_valid:
        print(
            f"Error: All {max_attempts} attempts failed to validate the input{context_msg}. Returning errors."
        )
        return ["Error"] * candidate_num

    # We already have 1 successful candidate, now generate the rest.
    remaining_candidates = candidate_num - 1
    if remaining_candidates > 0:
        print(
            f"Input validated. Now generating remaining {remaining_candidates} candidates..."
        )
        valid_claude_contents = _convert_to_claude_format(current_contents)
        client = get_anthropic_client()
        if client is None:
            raise ValueError("Anthropic client not initialized (missing ANTHROPIC_API_KEY)")
        tasks = [
            client.messages.create(
                model=model_name,
                max_tokens=max_output_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": valid_claude_contents}
                ],
                system=system_prompt,
            )
            for _ in range(remaining_candidates)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                print(f"Error generating a subsequent candidate: {res}")
                response_text_list.append("Error")
            else:
                response_text_list.append(res.content[0].text)

    return response_text_list

async def call_openai_with_retry_async(
    model_name, contents, config, max_attempts=5, retry_delay=30, error_context=""
):
    """
    ASYNC: Call OpenAI API with asynchronous retry logic.
    This follows the same pattern as Claude's implementation.
    """
    system_prompt = config["system_prompt"]
    temperature = config["temperature"]
    candidate_num = config["candidate_num"]
    max_completion_tokens = config["max_completion_tokens"]
    response_text_list = []

    def _looks_like_upstream_error_text(text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return True
        markers = [
            "invalid_argument",
            "invalid argument",
            "model not found",
            "unsupported model",
            "unauthorized",
            "forbidden",
            "rate limit",
            "too many requests",
        ]
        return any(m in t for m in markers)

    # --- Preparation Phase ---
    # Convert to the OpenAI-specific format
    current_contents = contents

    # --- Validation and Remediation Phase ---
    # We loop until we get a single successful response, proving the input is valid.
    is_input_valid = False
    for attempt in range(max_attempts):
        try:
            openai_contents = _convert_to_openai_format(current_contents)
            # Attempt to generate the very first candidate.
            client = get_openai_client(lane="text")
            if client is None:
                raise ValueError("OpenAI client not initialized (missing OPENAI_API_KEY)")
            first_response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": openai_contents}
                ],
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
            )
            first_content = first_response.choices[0].message.content
            if _looks_like_upstream_error_text(first_content):
                raise ValueError(f"OpenAI-compatible upstream returned error text: {first_content}")
            # If we reach here, the input is valid.
            response_text_list.append(first_content)
            is_input_valid = True
            break  # Exit the validation loop

        except Exception as e:
            error_str = str(e).lower()
            context_msg = f" for {error_context}" if error_context else ""
            print(
                f"Validation attempt {attempt + 1} failed{context_msg}: {error_str}. Retrying in {retry_delay} seconds..."
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(retry_delay)

    # --- Sampling Phase ---
    if not is_input_valid:
        print(
            f"Error: All {max_attempts} attempts failed to validate the input{context_msg}. Returning errors."
        )
        return ["Error"] * candidate_num

    # We already have 1 successful candidate, now generate the rest.
    remaining_candidates = candidate_num - 1
    if remaining_candidates > 0:
        print(
            f"Input validated. Now generating remaining {remaining_candidates} candidates..."
        )
        valid_openai_contents = _convert_to_openai_format(current_contents)
        client = get_openai_client(lane="text")
        if client is None:
            raise ValueError("OpenAI client not initialized (missing OPENAI_API_KEY)")
        tasks = [
            client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": valid_openai_contents}
                ],
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
            )
            for _ in range(remaining_candidates)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                print(f"Error generating a subsequent candidate: {res}")
                response_text_list.append("Error")
            else:
                content = res.choices[0].message.content
                if _looks_like_upstream_error_text(content):
                    response_text_list.append("Error")
                else:
                    response_text_list.append(content)

    return response_text_list


async def call_text_model_with_retry_async(
    model_name,
    contents,
    *,
    system_prompt="",
    temperature=0.7,
    candidate_num=1,
    max_output_tokens=50000,
    max_attempts=5,
    retry_delay=5,
    error_context="",
):
    """Route text generation to Gemini / Anthropic / OpenAI-compatible providers by model name."""
    lower_model = (model_name or "").lower()
    normalized_contents = _normalize_contents(contents)
    text_provider = (os.getenv("OPENAI_TEXT_PROVIDER") or "").strip().lower()

    if text_provider == "google":
        return await call_gemini_with_retry_async(
            model_name=model_name,
            contents=normalized_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                candidate_count=candidate_num,
                max_output_tokens=max_output_tokens,
            ),
            max_attempts=max_attempts,
            retry_delay=retry_delay,
            error_context=error_context,
        )

    if text_provider == "anthropic":
        return await call_claude_with_retry_async(
            model_name=model_name,
            contents=normalized_contents,
            config={
                "system_prompt": system_prompt,
                "temperature": temperature,
                "candidate_num": candidate_num,
                "max_output_tokens": max_output_tokens,
            },
            max_attempts=max_attempts,
            retry_delay=retry_delay,
            error_context=error_context,
        )

    # Any explicit non-google/non-anthropic provider is OpenAI-compatible (grsai, deepseek, openai, openrouter...).
    if text_provider:
        return await call_openai_with_retry_async(
            model_name=model_name,
            contents=normalized_contents,
            config={
                "system_prompt": system_prompt,
                "temperature": temperature,
                "candidate_num": candidate_num,
                "max_completion_tokens": max_output_tokens,
            },
            max_attempts=max_attempts,
            retry_delay=retry_delay,
            error_context=error_context,
        )

    if "gemini" in lower_model:
        return await call_gemini_with_retry_async(
            model_name=model_name,
            contents=normalized_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                candidate_count=candidate_num,
                max_output_tokens=max_output_tokens,
            ),
            max_attempts=max_attempts,
            retry_delay=retry_delay,
            error_context=error_context,
        )

    if any(token in lower_model for token in ["claude", "sonnet", "haiku", "opus"]):
        return await call_claude_with_retry_async(
            model_name=model_name,
            contents=normalized_contents,
            config={
                "system_prompt": system_prompt,
                "temperature": temperature,
                "candidate_num": candidate_num,
                "max_output_tokens": max_output_tokens,
            },
            max_attempts=max_attempts,
            retry_delay=retry_delay,
            error_context=error_context,
        )

    return await call_openai_with_retry_async(
        model_name=model_name,
        contents=normalized_contents,
        config={
            "system_prompt": system_prompt,
            "temperature": temperature,
            "candidate_num": candidate_num,
            "max_completion_tokens": max_output_tokens,
        },
        max_attempts=max_attempts,
        retry_delay=retry_delay,
        error_context=error_context,
    )


async def call_openai_image_generation_with_retry_async(
    model_name, prompt, config, max_attempts=5, retry_delay=30, error_context=""
):
    """
    ASYNC: Call OpenAI Image Generation API (GPT-Image) with asynchronous retry logic.
    """
    size = config.get("size", "1536x1024")
    quality = config.get("quality", "high")
    background = config.get("background", "opaque")
    output_format = config.get("output_format", "png")
    aspect_ratio = (config.get("aspect_ratio") or "auto").strip() or "auto"
    image_size = (config.get("image_size") or "1K").strip() or "1K"
    
    # Base parameters for all models
    gen_params = {
        "model": model_name,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    
    # Add GPT-Image specific parameters
    gen_params.update({
        "quality": quality,
        "background": background,
        "output_format": output_format,
    })

    def _ratio_from_size(size_text: str) -> str:
        s = (size_text or "").strip().lower()
        mapping = {
            "1024x1024": "1:1",
            "1536x1024": "3:2",
            "1024x1536": "2:3",
        }
        return mapping.get(s, "auto")

    def _looks_like_grsai_base(base_url: str) -> bool:
        b = (base_url or "").lower()
        return ("grsaiapi.com" in b) or ("dakka.com.cn" in b) or ("api.grsai.com" in b)

    def _v1_endpoint(base_url: str, path: str) -> str:
        base = (base_url or "").strip().rstrip("/")
        if not base:
            return ""
        if base.lower().endswith("/v1"):
            return f"{base}{path}"
        return f"{base}/v1{path}"

    def _grsai_base_candidates(configured_base: str) -> List[str]:
        configured = (configured_base or "").strip().rstrip("/")
        ordered: List[str] = []

        # Prefer documented stable hosts first, then the configured host.
        preferred = [
            "https://grsai.dakka.com.cn",
            "https://grsaiapi.com",
        ]
        for host in preferred:
            if host not in ordered:
                ordered.append(host)
        # Keep configured host only if it is not the legacy api.grsai.com endpoint.
        if configured and ("api.grsai.com" not in configured.lower()) and (configured not in ordered):
            ordered.append(configured)

        # Normalize legacy/unstable host to primary host.
        if configured and "api.grsai.com" in configured.lower():
            legacy_mapped = configured.lower().replace("api.grsai.com", "grsaiapi.com")
            if legacy_mapped not in ordered:
                ordered.append(legacy_mapped)
        return ordered

    def _grsai_model_candidates(requested_model: str) -> List[str]:
        model = (requested_model or "").strip()
        candidates: List[str] = []
        if model:
            candidates.append(model)
        fallback_map = {
            "nano-banana-pro-vt": "nano-banana-pro",
        }
        mapped = fallback_map.get(model)
        if mapped and mapped not in candidates:
            candidates.append(mapped)
        return candidates or ["nano-banana-pro"]

    def _is_nano_banana_model(name: str) -> bool:
        return (name or "").strip().lower().startswith("nano-banana")

    def _http_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 60) -> Dict[str, Any]:
        # Some OpenAI-compatible providers intermittently fail TLS handshake on Windows.
        # Use requests + retry and allow a final verify=False fallback for SSL EOF cases.
        last_exc = None
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
                resp.raise_for_status()
                text = resp.text or ""
                return json.loads(text) if text else {}
            except Exception as e:
                last_exc = e
                msg = str(e).lower()
                if ("eof occurred in violation of protocol" in msg) or ("ssleoferror" in msg):
                    try:
                        resp = requests.post(
                            url,
                            json=payload,
                            headers=headers,
                            timeout=timeout,
                            verify=False,
                        )
                        resp.raise_for_status()
                        text = resp.text or ""
                        return json.loads(text) if text else {}
                    except Exception as e2:
                        last_exc = e2
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
        raise ValueError(f"http post failed url={url}: {last_exc}")

    def _download_url_b64(target_url: str) -> str:
        # Robust download for flaky TLS endpoints (e.g., SSL EOF on some providers).
        last_exc = None
        for attempt in range(3):
            try:
                resp = requests.get(target_url, timeout=60)
                resp.raise_for_status()
                if resp.content:
                    return base64.b64encode(resp.content).decode("utf-8")
            except Exception as e:
                last_exc = e
                # Last-resort retry with verify=False only for SSL EOF class failures.
                msg = str(e).lower()
                if ("eof occurred in violation of protocol" in msg) or ("ssleoferror" in msg):
                    try:
                        resp = requests.get(target_url, timeout=60, verify=False)
                        resp.raise_for_status()
                        if resp.content:
                            return base64.b64encode(resp.content).decode("utf-8")
                    except Exception as e2:
                        last_exc = e2
                if attempt < 2:
                    continue
        raise ValueError(f"download image url failed: {last_exc}")

    async def _try_grsai_draw_fallback() -> List[str] | None:
        image_key, image_base = _openai_lane_env("image")
        image_provider = (os.getenv("OPENAI_IMAGE_PROVIDER") or "").strip().lower()
        if not image_key:
            image_key = get_config_val("api_keys", "openai_api_key", "OPENAI_API_KEY", "")
        if not image_base:
            image_base = (os.getenv("OPENAI_BASE_URL") or "").strip()
        # Enable automatic host probing for grsai even without an explicit base URL.
        if not image_key:
            return None
        if image_base and not _looks_like_grsai_base(image_base) and image_provider != "grsai":
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {image_key}",
        }
        last_err = None
        for base in _grsai_base_candidates(image_base):
            result_url = _v1_endpoint(base, "/draw/result")
            if not result_url:
                continue
            try:
                submit_data = None
                selected_model = None
                for model_try in _grsai_model_candidates(model_name):
                    for transient_try in range(2):
                        if _is_nano_banana_model(model_try):
                            submit_url = _v1_endpoint(base, "/draw/nano-banana")
                            submit_payload = {
                                "model": model_try,
                                "prompt": (prompt or "")[:32000],
                                "aspectRatio": aspect_ratio,
                                "imageSize": image_size,
                                "webHook": "-1",
                                "shutProgress": True,
                            }
                        else:
                            submit_url = _v1_endpoint(base, "/draw/completions")
                            submit_payload = {
                                "model": model_try,
                                "prompt": (prompt or "")[:32000],
                                "size": _ratio_from_size(size),
                                "webHook": "-1",
                                "shutProgress": True,
                            }
                        if not submit_url:
                            continue
                        submit_data = await asyncio.to_thread(_http_post_json, submit_url, submit_payload, headers, 60)
                        if int((submit_data or {}).get("code", -1)) != 0:
                            msg = str((submit_data or {}).get("msg") or "").strip()
                            if ("不存在该模型" in msg) or ("model not found" in msg.lower()):
                                break
                            raise ValueError(f"grsai draw submit failed: {msg or submit_data}")

                        task_id = ((submit_data.get("data") or {}).get("id") or "").strip()
                        if not task_id:
                            raise ValueError(f"grsai draw submit missing task id: {submit_data}")
                        if selected_model is None:
                            selected_model = model_try

                        # Poll up to 20 minutes by default (2s interval).
                        # Can be overridden via PAPERBANANA_GRSAI_POLL_SECONDS.
                        poll_seconds = int(os.getenv("PAPERBANANA_GRSAI_POLL_SECONDS", "1200") or "1200")
                        poll_attempts = max(1, poll_seconds // 2)
                        for _ in range(poll_attempts):
                            await asyncio.sleep(2)
                            poll_data = await asyncio.to_thread(_http_post_json, result_url, {"id": task_id}, headers, 60)
                            if int(poll_data.get("code", -1)) != 0:
                                continue
                            data_obj = poll_data.get("data") or {}
                            status = (data_obj.get("status") or "").lower()
                            if status == "succeeded":
                                results = data_obj.get("results") or []
                                image_url = ""
                                if isinstance(results, list) and results:
                                    first = results[0] or {}
                                    image_url = (first.get("url") or "").strip()
                                if not image_url:
                                    image_url = (data_obj.get("url") or "").strip()
                                if image_url:
                                    b64_data = await asyncio.to_thread(_download_url_b64, image_url)
                                    if b64_data:
                                        if selected_model and selected_model != (model_name or "").strip():
                                            print(f"[Info]: grsai draw model fallback: {model_name} -> {selected_model}")
                                        return [b64_data]
                                raise ValueError("grsai draw succeeded but no downloadable image url")
                            if status == "failed":
                                failure_reason = str(data_obj.get("failure_reason") or "").strip()
                                detail_error = str(data_obj.get("error") or "").strip()
                                if (failure_reason.lower() == "error") and transient_try < 1:
                                    print(f"[Warning]: grsai transient failure, retry submit once. task_id={task_id}")
                                    break
                                raise ValueError(
                                    f"grsai draw failed: failure_reason={failure_reason or 'unknown'}; "
                                    f"error={detail_error or 'N/A'}; task_id={task_id}"
                                )
                        else:
                            raise ValueError(f"grsai draw polling timeout after {poll_seconds}s")
                    else:
                        continue
                    break

                if int((submit_data or {}).get("code", -1)) != 0:
                    raise ValueError(f"grsai draw submit failed: {(submit_data or {}).get('msg') or submit_data}")
            except Exception as e:
                last_err = e
                err_text = str(e).lower()
                # Only switch host on transport-level failures (TLS/connection/timeouts).
                # Business-level errors should be returned directly.
                is_transport_error = (
                    "http post failed url=" in err_text
                    or "ssl" in err_text
                    or "connection" in err_text
                    or "timeout" in err_text
                )
                print(f"[Warning]: grsai host failed {base}: {e}")
                if is_transport_error:
                    continue
                raise
        raise ValueError(f"grsai draw failed on all hosts: {last_err}")

    # If image lane is configured to grsai-compatible host, use draw API directly.
    image_key_now, image_base_now = _openai_lane_env("image")
    image_provider_now = (os.getenv("OPENAI_IMAGE_PROVIDER") or "").strip().lower()
    if not image_key_now:
        image_key_now = get_config_val("api_keys", "openai_api_key", "OPENAI_API_KEY", "")
    if not image_base_now:
        image_base_now = (os.getenv("OPENAI_BASE_URL") or "").strip()
    if image_key_now and (
        (image_base_now and _looks_like_grsai_base(image_base_now))
        or (image_provider_now == "grsai")
    ):
        direct_result = await _try_grsai_draw_fallback()
        if direct_result:
            return direct_result
        raise ValueError("grsai draw direct mode returned no result")

    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            client = get_openai_client(lane="image")
            if client is None:
                raise ValueError("OpenAI client not initialized (missing OPENAI_API_KEY)")
            response = await client.images.generate(**gen_params)
            
            # OpenAI images.generate returns a list of images in response.data
            if response.data:
                first = response.data[0]
                if getattr(first, "b64_json", None):
                    return [first.b64_json]

                # Some OpenAI-compatible providers return URL instead of b64_json.
                url = getattr(first, "url", None)
                if url:
                    try:
                        b64_data = await asyncio.to_thread(_download_url_b64, url)
                        if b64_data:
                            return [b64_data]
                    except Exception as dl_err:
                        print(f"[Warning]: Failed to download generated image URL: {dl_err}")

            print(f"[Warning]: Failed to generate image via OpenAI, no usable image payload returned.")
            try:
                fallback_result = await _try_grsai_draw_fallback()
                if fallback_result:
                    return fallback_result
            except Exception as fb_err:
                last_error = fb_err
                print(f"[Warning]: grsai draw fallback failed: {fb_err}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(retry_delay)
            continue

        except Exception as e:
            last_error = e
            context_msg = f" for {error_context}" if error_context else ""
            print(
                f"Attempt {attempt + 1} for OpenAI image generation model {model_name} failed{context_msg}: {e}. Retrying in {retry_delay} seconds..."
            )
            try:
                fallback_result = await _try_grsai_draw_fallback()
                if fallback_result:
                    return fallback_result
            except Exception as fb_err:
                last_error = fb_err
                print(f"[Warning]: grsai draw fallback failed: {fb_err}")

            if attempt < max_attempts - 1:
                await asyncio.sleep(retry_delay)
            else:
                print(f"Error: All {max_attempts} attempts failed{context_msg}")
                break

    raise ValueError(f"Image generation failed for model={model_name}: {last_error or 'unknown error'}")




