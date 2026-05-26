"""
CVDP Custom Model Factory for native GitHub Copilot API access.
Self-contained: implements GitHub Device Flow OAuth + direct Copilot API calls.
No external proxy needed.

Usage:
    CUSTOM_MODEL_FACTORY=/path/to/copilot_direct_factory.py
    COPILOT_CLIENT_ID=Iv1.b507a97f6c5c6c5d       # GitHub OAuth App ID for Copilot
    python run_benchmark.py -f dataset.jsonl -l -m copilot
"""

import os
import sys
import json
import time
import logging
import re
import webbrowser
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional, Any

import httpx

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.append(_current_dir)

from src.llm_lib.model_factory import ModelFactory
from src.model_helpers import ModelHelpers
from src.config_manager import config

# ---------------------------------------------------------------------------
# GitHub OAuth constants
# ---------------------------------------------------------------------------
GITHUB_DEVICE_API = "https://github.com/login/device/code"
GITHUB_TOKEN_API = "https://github.com/login/oauth/access_token"
GITHUB_COPILOT_TOKEN_API = "https://api.github.com/copilot_internal/v2/token"
COPILOT_CHAT_API = "https://api.githubcopilot.com/chat/completions"
COPILOT_MODELS_API = "https://api.githubcopilot.com/models"

# Default public OAuth App client_id used by GitHub Copilot extensions
DEFAULT_CLIENT_ID = os.environ.get("COPILOT_CLIENT_ID", "Iv1.b507a97f6c5c6c5d")
TOKEN_CACHE_DIR = os.path.expanduser(os.environ.get("COPILOT_TOKEN_DIR", "~/.config/copilot_direct"))
TOKEN_CACHE_FILE = os.path.join(TOKEN_CACHE_DIR, "tokens.json")


# ---------------------------------------------------------------------------
# Auth: GitHub Device Flow + Copilot Token
# ---------------------------------------------------------------------------
class CopilotAuth:
    """
    GitHub Device Authorization Flow (RFC 8628) for Copilot access.

    1. Request device code from GitHub
    2. User visits github.com/login/device and enters the code
    3. Poll for access_token
    4. Exchange access_token for a Copilot API token
    """

    def __init__(self, client_id: str = DEFAULT_CLIENT_ID):
        self.client_id = client_id
        self._http = httpx.Client(follow_redirects=True)
        self._cached_copilot_token: Optional[str] = None
        self._cached_expires_at: float = 0
        self._load_cache()

    # -- token cache -------------------------------------------------------

    def _cache_path(self) -> str:
        return TOKEN_CACHE_FILE

    def _load_cache(self):
        try:
            with open(self._cache_path()) as f:
                data = json.load(f)
            self._cached_copilot_token = data.get("copilot_token")
            self._cached_expires_at = data.get("expires_at", 0)
            if self._cached_copilot_token and self._cached_expires_at > time.time():
                logging.info("[CopilotAuth] Loaded cached token (expires at %s)",
                             datetime.fromtimestamp(self._cached_expires_at, tz=timezone.utc).isoformat())
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def _save_cache(self, copilot_token: str, expires_in: int):
        os.makedirs(os.path.dirname(self._cache_path()), exist_ok=True)
        data = {
            "copilot_token": copilot_token,
            "expires_at": time.time() + expires_in,
        }
        with open(self._cache_path(), "w") as f:
            json.dump(data, f)
        self._cached_copilot_token = copilot_token
        self._cached_expires_at = data["expires_at"]
        # Restrict permissions
        try:
            os.chmod(self._cache_path(), 0o600)
        except OSError:
            pass

    # -- device flow -------------------------------------------------------

    def _request_device_code(self) -> dict:
        r = self._http.post(
            GITHUB_DEVICE_API,
            data={"client_id": self.client_id, "scope": "read:user"},
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        return r.json()

    def _poll_for_token(self, device_code: str, interval: int = 5) -> str:
        """Poll GitHub until user authorizes, return access_token."""
        while True:
            r = self._http.post(
                GITHUB_TOKEN_API,
                data={
                    "client_id": self.client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )
            data = r.json()
            error = data.get("error")
            if error is None:
                return data["access_token"]
            if error == "authorization_pending":
                time.sleep(interval)
                continue
            if error == "slow_down":
                interval += 5
                time.sleep(interval)
                continue
            raise RuntimeError(f"Device flow failed: {error} — {data.get('error_description', '')}")

    def _exchange_for_copilot_token(self, github_token: str) -> tuple[str, int]:
        """Exchange GitHub access_token for a Copilot API token."""
        r = self._http.get(
            GITHUB_COPILOT_TOKEN_API,
            headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/json",
                "User-Agent": "GitHubCopilotChat/1.0.0",
                "Editor-Version": "vscode/1.96.0",
                "Editor-Plugin-Version": "copilot/1.250.0",
            },
        )
        if r.status_code == 401 or r.status_code == 403:
            # Token expired or insufficient scopes — re-auth needed
            raise PermissionError(
                f"GitHub token rejected ({r.status_code}). "
                "You may need to re-authenticate. "
                "Delete the token cache and re-run."
            )
        r.raise_for_status()
        data = r.json()
        token = data.get("token")
        expires_in = data.get("expires_in", 1800)
        if not token:
            raise RuntimeError(f"Failed to get Copilot token: {data}")
        return token, expires_in

    # -- public API --------------------------------------------------------

    def get_copilot_token(self, force: bool = False) -> str:
        """Get a valid Copilot API token, refreshing or re-authing if needed."""
        now = time.time()
        if not force and self._cached_copilot_token and self._cached_expires_at > now + 60:
            return self._cached_copilot_token

        # Try refreshing first (use existing github token if cached)
        github_token = self._get_github_token()
        if github_token:
            try:
                copilot_token, expires_in = self._exchange_for_copilot_token(github_token)
                self._save_cache(copilot_token, expires_in)
                return copilot_token
            except (PermissionError, RuntimeError) as e:
                logging.warning("[CopilotAuth] Token refresh failed: %s", e)
                # Fall through to full re-auth

        # Full device auth flow
        return self._full_auth()

    def _get_github_token(self) -> Optional[str]:
        """Retrieve cached GitHub access token if available."""
        try:
            with open(self._cache_path()) as f:
                data = json.load(f)
            return data.get("github_token")
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def _save_github_token(self, github_token: str):
        """Save GitHub token alongside copilot token."""
        try:
            with open(self._cache_path()) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data["github_token"] = github_token
        with open(self._cache_path(), "w") as f:
            json.dump(data, f)

    def _full_auth(self) -> str:
        """Full device authorization flow."""
        print("\n" + "=" * 60)
        print("  GitHub Copilot — Device Authorization Required")
        print("=" * 60)

        # Step 1: get device code
        device = self._request_device_code()
        user_code = device["user_code"]
        verification_uri = device.get("verification_uri", "https://github.com/login/device")
        device_code = device["device_code"]
        interval = device.get("interval", 5)

        print(f"\n  Please visit: {verification_uri}")
        print(f"  And enter code: \033[1;32m{user_code}\033[0m")
        print(f"\n  This is a one-time step. Token will be cached.")
        print(f"\n  Waiting for authorization... (Ctrl+C to cancel)")

        # Try to open browser
        try:
            webbrowser.open(f"{verification_uri}?code={user_code}")
        except Exception:
            pass

        # Step 2: poll
        try:
            github_token = self._poll_for_token(device_code, interval)
            self._save_github_token(github_token)
            print("  ✅ GitHub authorization successful!")
        except KeyboardInterrupt:
            print("\n  Authorization cancelled.")
            raise RuntimeError("Device flow cancelled by user")

        # Step 3: exchange for copilot token
        copilot_token, expires_in = self._exchange_for_copilot_token(github_token)
        self._save_cache(copilot_token, expires_in)
        print(f"  ✅ Copilot API token acquired (expires in {expires_in}s)")
        return copilot_token


# ---------------------------------------------------------------------------
# Copilot API Instance
# ---------------------------------------------------------------------------
class CopilotInstance:
    """
    Direct GitHub Copilot API caller — no external proxy needed.
    Implements the same interface as VLLM_Instance for CVDP.
    """

    def __init__(self, context: str = "You are a helpful assistant.",
                 key: Optional[str] = None,
                 model: Optional[str] = None,
                 base_url: Optional[str] = None):
        if model is None:
            model = config.get("DEFAULT_MODEL", "copilot")

        self.model = model
        self.context = context
        self.debug = self._get_bool_env("COPILOT_DEBUG", False)

        # Model selection (mapped by copilot2api proxy)
        self.api_model = os.environ.get("COPILOT_MODEL", "gpt-5-mini")

        # Auth
        self._client_id = os.environ.get("COPILOT_CLIENT_ID", DEFAULT_CLIENT_ID)
        self._auth = CopilotAuth(client_id=self._client_id)

        # Generation params
        self.max_tokens = self._get_int_env("COPILOT_MAX_TOKENS", 16384)
        self.timeout_s = self._get_int_env("COPILOT_TIMEOUT", 300)
        self.temperature = self._get_float_env("COPILOT_TEMPERATURE", 0.2)

        # Sanitization
        self.sanitize_output = self._get_bool_env("COPILOT_SANITIZE_OUTPUT", True)
        self.check_module_name = self._get_bool_env("COPILOT_CHECK_MODULE_NAME", False)
        self.retry_module_name_mismatch = self._get_bool_env("COPILOT_RETRY_MODULE_NAME_MISMATCH", False)
        self.prompt_profile = os.environ.get("COPILOT_PROMPT_PROFILE", "auto").strip().lower()

        logging.info(
            "[CopilotInstance] Initialized: api_model=%s, max_tokens=%d, timeout=%ds",
            self.api_model, self.max_tokens, self.timeout_s,
        )

    @staticmethod
    def _get_bool_env(name: str, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _get_int_env(name: str, default: int) -> int:
        raw = os.environ.get(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    @staticmethod
    def _get_float_env(name: str, default: float) -> float:
        raw = os.environ.get(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    @staticmethod
    def _coerce_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "".join(CopilotInstance._coerce_text(item) for item in value if item)
        if isinstance(value, dict):
            for key in ("text", "content", "value"):
                if key in value:
                    return CopilotInstance._coerce_text(value[key])
            return str(value)
        text = getattr(value, "text", None)
        if text is not None:
            return CopilotInstance._coerce_text(text)
        content = getattr(value, "content", None)
        if content is not None:
            return CopilotInstance._coerce_text(content)
        return str(value)

    @staticmethod
    def _is_codegen_category(category: Optional[int]) -> bool:
        return category in {2, 3, 4, 5, 7, 12, 13, 14, 16}

    @staticmethod
    def _is_comprehension_category(category: Optional[int]) -> bool:
        return category in {6, 8, 9, 10}

    def _category_prompt_guidance(self, category: Optional[int]) -> str:
        profile = self.prompt_profile
        if profile in {"off", "none", "disabled"}:
            return ""
        lines = []
        if self._is_codegen_category(category):
            lines.extend([
                "Output raw RTL code only; do not include markdown fences, explanations, or prose.",
                "Keep the exact required module name, port names, parameter names, and file path from the prompt.",
                "Do not rename existing signals, modules, parameters, or ports unless the prompt explicitly requires it.",
                "Use conservative synthesizable Verilog/SystemVerilog compatible with Icarus Verilog.",
                "Avoid declaring variables in the middle of procedural blocks; declare temporaries before statements or at module scope.",
                "Avoid chained part-selects such as vector[a +: b][c:d]; use direct indexed part-selects instead.",
                "Avoid multiple drivers, implicit latches, out-of-range indexes, and width-ambiguous expressions.",
            ])
            if category in {4, 16}:
                lines.extend([
                    "For modification/debug tasks, preserve unrelated behavior and make the smallest targeted change.",
                    "Keep reset behavior, valid/done timing, and pipeline latency unchanged unless explicitly requested.",
                ])
            if category == 7:
                lines.extend([
                    "For lint/QoR tasks, preserve functional behavior while improving implementation quality.",
                    "Avoid new latches, unused signals, width truncation, unsynthesizable constructs, and unnecessary interface changes.",
                ])
        elif self._is_comprehension_category(category):
            lines.extend([
                "Answer only what the question asks; keep the final answer concise.",
                "Do not include hidden reasoning or unrelated explanation in the final answer.",
            ])
        if not lines:
            return ""
        return "\nAdditional output constraints:\n" + "\n".join(f"- {line}" for line in lines) + "\n"

    def _sanitize_output(self, content: str, files: Optional[list],
                          expected_single_file: bool, category: Optional[int]) -> str:
        if not self.sanitize_output or not content:
            return content.strip()
        cleaned = content.replace("\ufeff", "")
        cleaned = re.sub(r"^\s*(Here is|Here's|Below is).*?:\s*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        if not expected_single_file:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return cleaned[start:end + 1].strip()
            return cleaned.strip()
        block = re.search(r"```(?:systemverilog|verilog|sv|v)?\s*\n(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if block:
            cleaned = block.group(1).strip()
        if self._is_codegen_category(category):
            ms = re.search(r"(?m)^\s*(?:`\s*)?module\s+(?:automatic\s+)?[A-Za-z_][A-Za-z0-9_$]*\s*(?=[#(;])", cleaned)
            em = list(re.finditer(r"\bendmodule\b", cleaned))
            if ms and em:
                cleaned = cleaned[ms.start():em[-1].end()]
        return cleaned.strip()

    def _module_name_mismatch(self, content: str, expected_names: list[str]) -> Optional[str]:
        if not self.check_module_name or not expected_names:
            return None
        declared = set(re.findall(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)", content))
        if not declared:
            return f"expected one of {expected_names}, but no module declaration was found"
        if not any(name in declared for name in expected_names):
            return f"expected one of {expected_names}, but found modules {sorted(declared)}"
        return None

    @property
    def requires_evaluation(self) -> bool:
        return True

    def prompt(self, prompt: str,
               schema: Optional[str] = None,
               prompt_log: str = "./prompt.log",
               files: Optional[list] = None,
               timeout: int = 300,
               category: Optional[int] = None) -> str:

        helper = ModelHelpers()
        system_prompt = helper.create_system_prompt(self.context, schema, category)
        system_prompt += self._category_prompt_guidance(category)
        actual_timeout = timeout or self.timeout_s

        if prompt_log:
            try:
                os.makedirs(os.path.dirname(prompt_log), exist_ok=True)
                with open(prompt_log, "w+") as f:
                    f.write(system_prompt + "\n\n---\n" + prompt)
            except Exception as e:
                logging.error("Failed to write prompt log: %s", e)

        expected_single_file = files and len(files) == 1 and schema is None
        expected_names = self._extract_expected_names(prompt) if self._is_codegen_category(category) else []

        # Get Copilot API token (auto auth if needed)
        token = self._auth.get_copilot_token()

        try:
            start = time.time()
            with httpx.Client(timeout=httpx.Timeout(actual_timeout)) as client:
                resp = client.post(
                    COPILOT_CHAT_API,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Copilot-Integration-Id": "vscode-chat",
                        "Editor-Version": "vscode/1.96.0",
                        "User-Agent": "GitHubCopilotChat/1.0.0",
                    },
                    json={
                        "model": self.api_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            duration = time.time() - start
            content = self._coerce_text(data["choices"][0]["message"]["content"])
            finish_reason = data["choices"][0].get("finish_reason", "")

            if self.debug:
                logging.info("[Copilot] len=%s finish=%s dur=%.1fs", len(content), finish_reason, duration)

            if not content:
                raise ValueError("Model returned empty response")

            content = self._sanitize_output(content, files, expected_single_file, category)
            mismatch = self._module_name_mismatch(content, expected_names)

            if mismatch and self.retry_module_name_mismatch and self._is_codegen_category(category):
                retry_prompt = self._build_retry_prompt(prompt, content, mismatch, expected_names)
                retry_resp = client.post(
                    COPILOT_CHAT_API,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Copilot-Integration-Id": "vscode-chat",
                    },
                    json={
                        "model": self.api_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": retry_prompt},
                        ],
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                    },
                )
                retry_data = retry_resp.json()
                content = self._coerce_text(retry_data["choices"][0]["message"]["content"])
                if content:
                    content = self._sanitize_output(content, files, expected_single_file, category)
                    mismatch = self._module_name_mismatch(content, expected_names)

            if mismatch:
                raise ValueError(f"Generated RTL module-name check failed: {mismatch}")

            if not expected_single_file and schema is not None and content.startswith('{'):
                content = helper.fix_json_formatting(content)

            return helper.parse_model_response(content, files, expected_single_file)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token expired — force re-auth and retry
                logging.warning("[Copilot] Token expired, re-authenticating...")
                token = self._auth.get_copilot_token(force=True)
                return self.prompt(prompt, schema, prompt_log, files, timeout, category)
            raise ValueError(f"Copilot API error ({e.response.status_code}): {e.response.text[:200]}")
        except Exception as e:
            raise ValueError(f"Copilot API call failed: {e}")

    def _extract_expected_names(self, prompt: str) -> list[str]:
        names = []
        patterns = [
            r"Module Name:\s*(?:\n\s*)?`([A-Za-z_][A-Za-z0-9_$]*)`",
            r"Module Name:\s*(?:\n\s*)?\*\*([A-Za-z_][A-Za-z0-9_$]*)\*\*",
            r"module named\s+\*\*([A-Za-z_][A-Za-z0-9_$]*)\*\*",
        ]
        for pat in patterns:
            for m in re.finditer(pat, prompt, re.IGNORECASE):
                name = m.group(1)
                if name.lower() not in {"named", "that", "which", "with", "for", "to"} and name not in names:
                    names.append(name)
        return names

    def _build_retry_prompt(self, prompt: str, content: str, mismatch: str, expected: list[str]) -> str:
        return (
            f"{prompt}\n\n"
            "The previous RTL was rejected because its module name didn't match. "
            f"Expected: {', '.join(expected)}. Checker: {mismatch}.\n\n"
            "Regenerate with the exact module name. Output raw RTL only.\n"
        )


# ---------------------------------------------------------------------------
# CVDP ModelFactory
# ---------------------------------------------------------------------------
class CustomModelFactory(ModelFactory):
    def __init__(self):
        super().__init__()
        self.model_types["copilot"] = lambda *a, **kw: CopilotInstance(*a, **kw)
        logging.info("[CopilotDirectFactory] Registered: copilot (GPT-4o via GitHub Copilot)")


if __name__ == "__main__":
    factory = CustomModelFactory()
    m = factory.create_model("copilot", "You are a Verilog expert.")
    print(f"Model: {m.model}, API: {m.api_model}")
    try:
        r = m.prompt("Write a 2-input AND gate in Verilog.", files=["and.sv"], category=3)
        print(f"Result:\n{r[:500]}")
    except Exception as e:
        print(f"Error: {e}")
