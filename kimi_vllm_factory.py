"""
CVDP Custom Model Factory for OpenAI-Compatible APIs (vLLM, Ollama, TGI, etc.)
"""

import os
import sys
import logging
import re
import time
import math
from urllib.parse import urlparse
from typing import Optional, Any

# 把项目根目录加入路径，确保能 import cvdp 的内部模块
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.append(_current_dir)

from src.llm_lib.model_factory import ModelFactory
from src.model_helpers import ModelHelpers
from src.config_manager import config

# ------------------------------------------------------------
# 核心：你的 vLLM / OpenAI-Compatible 模型类
# ------------------------------------------------------------
class VLLM_Instance:
    """
    支持任何 OpenAI Compatible API 的模型封装。
    适用：vLLM, Ollama(openai compat mode), TGI, xinference, DeepSeek API 等
    """

    def __init__(self, context: str = "You are a helpful assistant.",
                 key: Optional[str] = None,
                 model: Optional[str] = None,
                 base_url: Optional[str] = None):
        """
        Args:
            context: 系统提示词上下文
            key: API Key（vLLM 本地部署时通常无所谓，填 dummy 即可）
            model: 模型名称（必须与你 vLLM 服务里的 model name 一致）
            base_url: vLLM 服务地址，如 http://localhost:8000/v1
        """
        if model is None:
            model = config.get("DEFAULT_MODEL", "vllm-glm")

        self.model = model
        self.context = context
        self.debug = self._get_bool_env("VLLM_DEBUG", False)
        self.enable_thinking = self._get_bool_env("VLLM_ENABLE_THINKING", True)
        self.strip_thinking_tags = self._get_bool_env("VLLM_STRIP_THINKING_TAGS", True)
        self.trust_env = self._get_bool_env("VLLM_TRUST_ENV", True)
        self.thinking_policy = os.environ.get("VLLM_THINKING_POLICY", "env").strip().lower()
        self.codegen_enable_thinking = self._get_bool_env("VLLM_CODEGEN_ENABLE_THINKING", False)
        self.comprehension_enable_thinking = self._get_bool_env("VLLM_COMPREHENSION_ENABLE_THINKING", True)
        self.prompt_profile = os.environ.get("VLLM_PROMPT_PROFILE", "auto").strip().lower()
        self.sanitize_output = self._get_bool_env("VLLM_SANITIZE_OUTPUT", True)
        self.check_module_name = self._get_bool_env("VLLM_CHECK_MODULE_NAME", False)
        self.auto_timeout = self._get_bool_env("VLLM_AUTO_TIMEOUT", False)
        self.throughput_tokens_per_sec = self._get_float_env("VLLM_THROUGHPUT_TOKENS_PER_SEC", 30.0)
        self.timeout_margin = self._get_float_env("VLLM_TIMEOUT_MARGIN", 1.5)
        self.min_timeout = self._get_int_env("VLLM_MIN_TIMEOUT", 120)
        self.max_timeout = self._get_int_env("VLLM_MAX_TIMEOUT", 2000)
        self.default_max_tokens = self._get_int_env("VLLM_MAX_TOKENS", 32384)
        self.max_tokens_codegen_nonthinking = self._get_int_env("VLLM_MAX_TOKENS_CODEGEN_NONTHINKING", 8192)
        self.max_tokens_codegen_thinking = self._get_int_env("VLLM_MAX_TOKENS_CODEGEN_THINKING", 12000)
        self.max_tokens_comprehension_thinking = self._get_int_env("VLLM_MAX_TOKENS_COMPREHENSION_THINKING", 8192)
        self.max_tokens_comprehension_nonthinking = self._get_int_env("VLLM_MAX_TOKENS_COMPREHENSION_NONTHINKING", 4096)
        self.retry_empty_with_nonthinking = self._get_bool_env("VLLM_RETRY_EMPTY_WITH_NONTHINKING", True)
        self.log_generation_stats = self._get_bool_env("VLLM_DEBUG_GENERATION_STATS", True)
        self.api_model = os.environ.get("VLLM_MODEL_NAME", "/data/HF_models/GLM-5.1-FP8")
        self.last_reasoning = ""
        self.last_generation_stats = {}

        # 读取 base_url：优先从环境变量，其次从参数，最后默认本地
        self.base_url = base_url or os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:30009/v1")

        # 读取 api_key：vLLM 本地部署时很多服务不验 key，但需要非空字符串
        api_key = key or os.environ.get("VLLM_API_KEY") or os.environ.get("OPENAI_USER_KEY") or "dummy-key"
        if api_key == "dummy-key":
            logging.warning("VLLM_API_KEY not set, using dummy key. If your server requires auth, set the env var.")

        # 初始化 OpenAI 客户端（只改 base_url，其余兼容）
        try:
            import openai
            client_kwargs = {
                "base_url": self.base_url,
                "api_key": api_key,
            }

            # Local OpenAI-compatible servers should bypass corporate proxy settings.
            if self._is_local_base_url(self.base_url):
                import httpx
                client_kwargs["http_client"] = httpx.Client(trust_env=False)
            elif not self.trust_env:
                import httpx
                client_kwargs["http_client"] = httpx.Client(trust_env=False)

            self.chat = openai.OpenAI(**client_kwargs)
            logging.info(f"[VLLM_Instance] Created client: base_url={self.base_url}, model={self.model}")
        except Exception as e:
            raise ValueError(f"Failed to create OpenAI client for vLLM: {e}")

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
            logging.warning("Invalid integer for %s=%r; using default %s", name, raw, default)
            return default

    @staticmethod
    def _get_float_env(name: str, default: float) -> float:
        raw = os.environ.get(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            return float(raw)
        except ValueError:
            logging.warning("Invalid float for %s=%r; using default %s", name, raw, default)
            return default

    @staticmethod
    def _coerce_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = [VLLM_Instance._coerce_text(item) for item in value]
            return "".join(part for part in parts if part)
        if isinstance(value, dict):
            for key in ("text", "content", "value"):
                if key in value:
                    return VLLM_Instance._coerce_text(value[key])
            return str(value)

        text = getattr(value, "text", None)
        if text is not None:
            return VLLM_Instance._coerce_text(text)

        content = getattr(value, "content", None)
        if content is not None:
            return VLLM_Instance._coerce_text(content)

        value_attr = getattr(value, "value", None)
        if value_attr is not None:
            return VLLM_Instance._coerce_text(value_attr)

        return str(value)

    @staticmethod
    def _is_local_base_url(base_url: str) -> bool:
        hostname = urlparse(base_url).hostname
        return hostname in {"127.0.0.1", "localhost", "::1"}

    def _sanitize_final_content(self, content: str) -> str:
        if not self.strip_thinking_tags:
            return content.strip()

        # Some thinking-capable models may inline reasoning inside <think>...</think> blocks.
        cleaned = re.sub(r"^\s*<think>.*?</think>\s*", "", content, flags=re.DOTALL)
        return cleaned.strip()

    @staticmethod
    def _is_codegen_category(category: Optional[int]) -> bool:
        return category in {2, 3, 4, 5, 7, 12, 13, 14, 16}

    @staticmethod
    def _is_comprehension_category(category: Optional[int]) -> bool:
        return category in {6, 8, 9, 10}

    def _resolve_thinking_enabled(self, category: Optional[int]) -> bool:
        policy = self.thinking_policy
        if policy in {"always", "on", "true"}:
            return True
        if policy in {"never", "off", "false"}:
            return False
        if policy in {"auto", "codegen_off_comprehension_on", "two_stage"}:
            if self._is_codegen_category(category):
                return self.codegen_enable_thinking
            if self._is_comprehension_category(category):
                return self.comprehension_enable_thinking
        return self.enable_thinking

    def _resolve_max_tokens(self, category: Optional[int], thinking_enabled: bool) -> int:
        if self._is_codegen_category(category):
            return self.max_tokens_codegen_thinking if thinking_enabled else self.max_tokens_codegen_nonthinking
        if self._is_comprehension_category(category):
            return self.max_tokens_comprehension_thinking if thinking_enabled else self.max_tokens_comprehension_nonthinking
        return self.default_max_tokens

    def _estimate_timeout(self, max_tokens: int, requested_timeout: int) -> int:
        if not self.auto_timeout:
            return requested_timeout
        if self.throughput_tokens_per_sec <= 0:
            return requested_timeout
        estimated = math.ceil(max_tokens / self.throughput_tokens_per_sec * self.timeout_margin)
        estimated = max(self.min_timeout, min(self.max_timeout, estimated))
        return max(requested_timeout or 0, estimated)

    def _category_prompt_guidance(self, category: Optional[int], thinking_enabled: bool) -> str:
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
                    "For modification/debug tasks, preserve unrelated behavior and make the smallest targeted change that satisfies the request.",
                    "Keep reset behavior, valid/done timing, and pipeline latency unchanged unless explicitly requested.",
                ])
            if category == 7:
                lines.extend([
                    "For lint/QoR tasks, preserve functional behavior while improving implementation quality.",
                    "Avoid new latches, unused signals, width truncation, unsynthesizable constructs, and unnecessary interface changes.",
                ])
            if thinking_enabled:
                lines.append("Think internally if needed, but the final answer must contain only compilable RTL code.")
        elif self._is_comprehension_category(category):
            lines.extend([
                "Answer only what the question asks; keep the final answer concise and directly comparable to the reference answer.",
                "Do not include hidden reasoning, scratch work, or unrelated explanation in the final answer.",
            ])

        if not lines:
            return ""
        return "\nAdditional output constraints:\n" + "\n".join(f"- {line}" for line in lines) + "\n"

    def _extract_expected_module_names(self, prompt: str) -> list[str]:
        names = []
        patterns = [
            r"Module Name:\s*`?([A-Za-z_][A-Za-z0-9_$]*)`?",
            r"module\s+`?([A-Za-z_][A-Za-z0-9_$]*)`?",
            r"module named\s+\*\*([A-Za-z_][A-Za-z0-9_$]*)\*\*",
            r"module named\s+`?([A-Za-z_][A-Za-z0-9_$]*)`?",
            r"module\s+`([A-Za-z_][A-Za-z0-9_$]*)`",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, prompt, flags=re.IGNORECASE):
                name = match.group(1)
                if name.lower() in {"named", "that", "which", "with", "for", "to", "called"}:
                    continue
                if name not in names:
                    names.append(name)
        return names

    def _sanitize_model_output(self, content: str, files: Optional[list], expected_single_file: bool,
                               category: Optional[int]) -> str:
        if not self.sanitize_output or not content:
            return content.strip()

        cleaned = content.replace("\ufeff", "")
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

        # Remove common prose wrappers before preserving JSON or RTL.
        cleaned = re.sub(r"^\s*(Here is|Here's|Below is).*?:\s*", "", cleaned, flags=re.IGNORECASE | re.DOTALL)

        if not expected_single_file:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return cleaned[start:end + 1].strip()
            return cleaned.strip()

        # Direct single-file RTL mode: extract code block first if present.
        block_match = re.search(r"```(?:systemverilog|verilog|sv|v)?\s*\n(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if block_match:
            cleaned = block_match.group(1).strip()
        else:
            cleaned = re.sub(r"^```(?:systemverilog|verilog|sv|v)?\s*", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        if self._is_codegen_category(category):
            module_start = re.search(r"\bmodule\b", cleaned)
            endmodule_matches = list(re.finditer(r"\bendmodule\b", cleaned))
            if module_start and endmodule_matches:
                cleaned = cleaned[module_start.start():endmodule_matches[-1].end()]

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

    def _record_generation_stats(self, **stats) -> None:
        self.last_generation_stats = stats
        if self.log_generation_stats or self.debug:
            logging.info("[VLLM_Instance] generation_stats=%s", stats)

    def _extract_message_output(self, message: Any) -> tuple[str, str]:
        reasoning = self._coerce_text(getattr(message, "reasoning_content", None)).strip()
        content = self._coerce_text(getattr(message, "content", None))
        content = self._sanitize_final_content(content)
        return content, reasoning

    @property
    def requires_evaluation(self) -> bool:
        """标准模型需要跑 harness 评估"""
        return True

    def prompt(self, prompt: str,
               schema: Optional[str] = None,
               prompt_log: str = "./prompt.log",
               files: Optional[list] = None,
               timeout: int = 1200,
               category: Optional[int] = None) -> str:
        """
        CVDP 核心调用接口：接收 prompt，返回模型生成的文本。
        """

        if self.chat is None:
            raise ValueError("Chat client not initialized")

        helper = ModelHelpers()
        system_prompt = helper.create_system_prompt(self.context, schema, category)

        thinking_enabled = self._resolve_thinking_enabled(category)
        max_tokens = self._resolve_max_tokens(category, thinking_enabled)

        # 如果 timeout 是默认值，尝试从配置读取
        if timeout == 1200:
            timeout = config.get("MODEL_TIMEOUT", 1200)
        timeout = self._estimate_timeout(max_tokens, timeout)

        system_prompt += self._category_prompt_guidance(category, thinking_enabled)

        # 写 prompt 日志（CVDP 框架用于调试）
        if prompt_log:
            try:
                os.makedirs(os.path.dirname(prompt_log), exist_ok=True)
                with open(prompt_log, "w+") as f:
                    f.write(system_prompt + "\n\n----------------------------------------\n" + prompt)
            except Exception as e:
                logging.error(f"Failed to write prompt log: {e}")
                raise
        expected_single_file = files and len(files) == 1 and schema is None
        expected_module_names = self._extract_expected_module_names(prompt) if self._is_codegen_category(category) else []

        def _create_completion(use_thinking: bool, retry_label: str = "none"):
            start_time = time.time()
            try:
                response_obj = self.chat.chat.completions.create(
                    model=self.api_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": prompt}
                    ],
                    timeout=timeout,
                    temperature=0.2,
                    max_tokens=max_tokens,
                    extra_body={"chat_template_kwargs": {"enable_thinking": use_thinking}},
                )
            except Exception as api_error:
                duration = time.time() - start_time
                self._record_generation_stats(
                    thinking_enabled=use_thinking,
                    category=category,
                    max_tokens=max_tokens,
                    timeout_s=timeout,
                    duration_s=round(duration, 3),
                    finish_reason=None,
                    content_len=0,
                    reasoning_len=0,
                    error_type="api_error",
                    retry_mode=retry_label,
                    error=str(api_error),
                )
                raise

            duration = time.time() - start_time
            choice = response_obj.choices[0]
            message_obj = choice.message
            content_obj, reasoning_obj = self._extract_message_output(message_obj)
            finish_reason = getattr(choice, "finish_reason", None)
            self._record_generation_stats(
                thinking_enabled=use_thinking,
                category=category,
                max_tokens=max_tokens,
                timeout_s=timeout,
                duration_s=round(duration, 3),
                finish_reason=finish_reason,
                content_len=len(content_obj),
                reasoning_len=len(reasoning_obj),
                error_type=None if content_obj else "empty_content",
                retry_mode=retry_label,
            )
            return content_obj, reasoning_obj

        try:
            content, reasoning = _create_completion(thinking_enabled)
            self.last_reasoning = reasoning

            if self.debug:
                logging.info(
                    "[VLLM_Instance] thinking=%s content_len=%s reasoning_len=%s",
                    thinking_enabled,
                    len(content),
                    len(reasoning),
                )

                logging.info("vllm resoning is %s", reasoning)
                logging.info("vllm raw content is %s", content)

            if not content and thinking_enabled and self.retry_empty_with_nonthinking and self._is_codegen_category(category):
                logging.warning(
                    "Model returned empty final content in thinking mode; retrying codegen once with thinking disabled."
                )
                content, reasoning = _create_completion(False, retry_label="empty_content_nonthinking_fallback")
                self.last_reasoning = reasoning

            if not content:
                raise ValueError(
                    "Model returned empty final content. Refusing to use reasoning_content as benchmark output."
                )

            # 自动解析：单文件直接返回 / 多文件从代码块提取 / JSON schema 处理
            content = self._sanitize_model_output(content, files, expected_single_file, category)
            mismatch = self._module_name_mismatch(content, expected_module_names)
            if mismatch:
                raise ValueError(f"Generated RTL module-name check failed: {mismatch}")

            if not expected_single_file and schema is not None:
                if content.startswith('{') and content.endswith('}'):
                    content = helper.fix_json_formatting(content)

            result = helper.parse_model_response(content, files, expected_single_file)
            if self.debug:
                logging.info("vllm content is %s", result)
            return result

        except Exception as e:
            raise ValueError(f"Unable to get response from vLLM model '{self.model}' at {self.base_url}: {str(e)}")


# ------------------------------------------------------------
# 工厂类：注册模型名称
# ------------------------------------------------------------
class CustomModelFactory(ModelFactory):
    """
    自定义工厂，把 CVDP 的模型请求路由到 VLLM_Instance。
    """

    def __init__(self):
        super().__init__()
        # 注册你的模型名 → 工厂方法映射
        # 你可以注册多个，对应 vLLM 里不同模型
        self.model_types["vllm-glm"] = self._create_vllm_instance

        logging.info("[CustomModelFactory] Registered vLLM / OpenAI-compatible models")

    def _create_vllm_instance(self, model_name: str, context: Any, key: Optional[str], **kwargs) -> Any:
        """创建 vLLM 模型实例"""
        return VLLM_Instance(context=context, key=key, model=model_name)


# 本地测试（直接运行 python vllm_model_factory.py 时执行）
if __name__ == "__main__":
    factory = CustomModelFactory()

    # 测试连通性
    test_model = factory.create_model(model_name="vllm-glm", context="You are a Verilog expert.")
    print(f"Model created: {test_model.model}, base_url={test_model.base_url}")

    try:
        resp = test_model.prompt("Write a Verilog module for a 2-input AND gate.", files=["and_gate.v"], category=3)
        print(f"Response:\n{resp[:500]}...")
    except Exception as e:
        print(f"Test failed: {e}")
