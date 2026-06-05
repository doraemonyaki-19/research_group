"""Language Model Abstraction Layer for ResearchGroup.

Provides a unified interface for Anthropic and Gemini models, allowing the
agents to remain provider-agnostic.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any

import anthropic
try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

try:
    import openai
except ImportError:
    openai = None


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]
    # Gemini 3.x requires the model's `thought_signature` to be echoed back
    # with each function_call when feeding it into a follow-up turn. The
    # SDK ignores this field on Gemini 2.x and Anthropic; keeping it None for
    # those providers is harmless.
    thought_signature: bytes | None = None


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    input_tokens: int
    output_tokens: int


class LanguageModel(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def model(self) -> str:
        """The name of the model being used."""
        pass
    
    @abstractmethod
    def generate(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
        max_tokens: int,
    ) -> LLMResponse:
        """Generate a response from the model.

        Args:
            messages: List of messages in standard Anthropic format.
                      Content is a list of parts (text, tool_use, tool_result).
                      Note: tool_result must include both 'tool_use_id' and 'name'.
            system: System prompt string.
            tools: List of tool definitions in standard Anthropic format.
            max_tokens: Maximum tokens to generate.

        Returns:
            LLMResponse containing text, tool calls, and usage stats.
        """
        pass

    @abstractmethod
    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the estimated cost for a given token usage."""
        pass


class AnthropicModel(LanguageModel):
    """Wrapper for Anthropic's Claude models."""

    def __init__(self, client: anthropic.Anthropic, model: str, api_timeout: int = 300):
        self.client = client
        self._model = model
        self.api_timeout = api_timeout

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
        max_tokens: int,
    ) -> LLMResponse:
        
        # Anthropic doesn't expect 'name' in tool_result, but we added it to our
        # generic standard. We must strip it out to avoid validation errors.
        # Also strip 'thought_signature' from tool_use (Gemini 3.x-only field
        # that the Anthropic SDK does not recognize).
        cleaned_messages = []
        for msg in messages:
            if isinstance(msg.get("content"), list):
                new_content = []
                for part in msg["content"]:
                    if part.get("type") == "tool_result":
                        part_copy = dict(part)
                        part_copy.pop("name", None)
                        new_content.append(part_copy)
                    elif part.get("type") == "tool_use":
                        part_copy = dict(part)
                        part_copy.pop("thought_signature", None)
                        new_content.append(part_copy)
                    else:
                        new_content.append(part)
                cleaned_messages.append({"role": msg["role"], "content": new_content})
            else:
                cleaned_messages.append(msg)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=cleaned_messages,
            timeout=self.api_timeout,
        )

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))

        in_tok = response.usage.input_tokens if hasattr(response, "usage") else 0
        out_tok = response.usage.output_tokens if hasattr(response, "usage") else 0

        return LLMResponse(
            text="\n".join(text_parts).strip(),
            tool_calls=tool_calls,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Claude 3.5 Sonnet: $3.00 / 1M in, $15.00 / 1M out
        return (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)


class GeminiModel(LanguageModel):
    """Wrapper for Google Gemini models."""

    def __init__(self, client: genai.Client, model: str, api_timeout: int = 600):
        if not genai:
            raise ImportError("google-genai is not installed.")
        self.client = client
        self._model = model
        self.api_timeout = api_timeout

    @property
    def model(self) -> str:
        return self._model

    def _convert_schema(self, schema: dict) -> dict:
        """Convert standard JSON schema to Gemini schema."""
        if not schema:
            return {}
        result = {}
        for k, v in schema.items():
            if k == "type":
                result[k] = str(v).upper()  # Gemini uses upper case types like "OBJECT"
            elif isinstance(v, dict):
                result[k] = self._convert_schema(v)
            elif isinstance(v, list):
                result[k] = [self._convert_schema(i) if isinstance(i, dict) else i for i in v]
            else:
                result[k] = v
        return result

    def generate(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
        max_tokens: int,
    ) -> LLMResponse:
        
        # 1. Convert tools
        gemini_tools = []
        if tools:
            decls = []
            for t in tools:
                schema = self._convert_schema(t.get("input_schema", {}))
                decls.append({
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": schema
                })
            gemini_tools = [{"function_declarations": decls}]

        # 2. Convert messages to Gemini Content types
        gemini_contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            parts = []
            
            content = msg.get("content", [])
            if isinstance(content, str):
                parts.append(genai_types.Part.from_text(text=content))
            else:
                for part in content:
                    if part["type"] == "text":
                        parts.append(genai_types.Part.from_text(text=part["text"]))
                    elif part["type"] == "tool_use":
                        # Gemini 3.x rejects function_call parts that don't
                        # carry the original thought_signature. Build the Part
                        # directly so we can attach the signature; for 2.x or
                        # missing signatures we fall back to from_function_call.
                        sig = part.get("thought_signature")
                        if sig:
                            parts.append(genai_types.Part(
                                function_call=genai_types.FunctionCall(
                                    name=part["name"],
                                    args=part["input"],
                                ),
                                thought_signature=sig,
                            ))
                        else:
                            parts.append(genai_types.Part.from_function_call(
                                name=part["name"],
                                args=part["input"],
                            ))
                    elif part["type"] == "tool_result":
                        # Gemini requires name and a dict response
                        # We try to parse the string result as JSON, fallback to dict
                        result_str = part["content"]
                        try:
                            result_data = json.loads(result_str)
                            if not isinstance(result_data, dict):
                                result_data = {"result": result_data}
                        except Exception:
                            result_data = {"result": result_str}
                            
                        parts.append(genai_types.Part.from_function_response(
                            name=part.get("name", "unknown"),
                            response=result_data
                        ))
            
            if parts:
                gemini_contents.append(genai_types.Content(role=role, parts=parts))

        # 3. Call API
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            tools=gemini_tools if gemini_tools else None,
        )

        # Enforce a wall-clock timeout on the Gemini call, since the SDK does
        # not expose a native timeout parameter. We avoid `with ThreadPoolExecutor(...)`
        # here: its __exit__ calls shutdown(wait=True), which blocks until the
        # orphaned API thread eventually returns. On a network connection drop
        # (Windows WinError 10053), that wait can be 30+ minutes — exactly
        # what was observed in pilot run b60pkzo6g (turn 2: 9300s wall vs the
        # nominal 300s timeout). Manual shutdown(wait=False) lets us return
        # promptly; the orphan thread becomes a daemon-style leak, which is
        # acceptable because the process is short-lived per ablation cell.
        pool = ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(
                self.client.models.generate_content,
                model=self.model,
                contents=gemini_contents,
                config=config,
            )
            try:
                response = future.result(timeout=self.api_timeout)
            except FuturesTimeoutError:
                future.cancel()
                raise TimeoutError(
                    f"Gemini API call timed out after {self.api_timeout}s"
                )
        finally:
            pool.shutdown(wait=False)

        # 4. Parse response
        text_parts = []
        tool_calls = []
        
        # In Gemini, response.candidates[0].content.parts
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    text_parts.append(part.text)
                elif part.function_call:
                    # Provide a generic ID for the tool call since Gemini doesn't use IDs natively
                    tool_calls.append(ToolCall(
                        id=f"call_{part.function_call.name}",
                        name=part.function_call.name,
                        input=dict(part.function_call.args) if part.function_call.args else {},
                        # Capture thought_signature — required by Gemini 3.x.
                        # Older 2.x responses leave this as None, which is fine.
                        thought_signature=getattr(part, "thought_signature", None),
                    ))

        in_tok = (response.usage_metadata.prompt_token_count or 0) if response.usage_metadata else 0
        out_tok = (response.usage_metadata.candidates_token_count or 0) if response.usage_metadata else 0

        return LLMResponse(
            text="\n".join(text_parts).strip(),
            tool_calls=tool_calls,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        if "pro" in self.model.lower():
            # Gemini 2.5 Pro: $1.25 / 1M in, $5.00 / 1M out
            return (input_tokens / 1_000_000 * 1.25) + (output_tokens / 1_000_000 * 5.0)
        elif "flash" in self.model.lower():
            # Gemini 2.5 Flash: $0.10 / 1M in, $0.40 / 1M out
            return (input_tokens / 1_000_000 * 0.1) + (output_tokens / 1_000_000 * 0.4)
        else:
            return (input_tokens / 1_000_000 * 1.25) + (output_tokens / 1_000_000 * 5.0)


class OpenAIModel(LanguageModel):
    """Wrapper for OpenAI-compatible APIs (OpenAI, NVIDIA NIM, etc.)."""

    def __init__(
        self,
        client: openai.OpenAI,
        model: str,
        api_timeout: int = 600,
        extra_body: dict | None = None,
    ):
        if not openai:
            raise ImportError("openai is not installed.")
        self.client = client
        self._model = model
        self.api_timeout = api_timeout
        self.extra_body = extra_body

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
        max_tokens: int,
    ) -> LLMResponse:
        
        # 1. Convert messages
        # Standard format: [{"role": "user", "content": [{"type": "text", "text": "..."}]}]
        # OpenAI format: [{"role": "user", "content": "..."}] or [{"role": "user", "content": [{"type": "text", "text": "..."}]}]
        # We'll use the simpler string format where possible.
        
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                openai_messages.append({"role": role, "content": content})
            else:
                # Collect text parts, tool_use parts, and tool_result parts separately.
                text_parts = []
                tool_use_parts = []
                tool_result_parts = []
                for part in content:
                    if part["type"] == "text":
                        text_parts.append(part["text"])
                    elif part["type"] == "tool_use":
                        tool_use_parts.append(part)
                    elif part["type"] == "tool_result":
                        tool_result_parts.append(part)

                if role == "assistant":
                    # Build an OpenAI assistant message: content = joined text,
                    # tool_calls = list of function call objects.
                    text_content = "\n".join(text_parts) or None
                    if tool_use_parts:
                        openai_messages.append({
                            "role": "assistant",
                            "content": text_content,
                            "tool_calls": [
                                {
                                    "id": p["id"],
                                    "type": "function",
                                    "function": {
                                        "name": p["name"],
                                        "arguments": json.dumps(p["input"]),
                                    },
                                }
                                for p in tool_use_parts
                            ],
                        })
                    elif text_content:
                        openai_messages.append({"role": "assistant", "content": text_content})
                elif role == "user":
                    if tool_result_parts:
                        # Tool results become role="tool" messages (one per result).
                        for p in tool_result_parts:
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": p["tool_use_id"],
                                "content": p["content"],
                            })
                        # Also emit any accompanying text as a follow-up user message.
                        if text_parts:
                            openai_messages.append({"role": "user", "content": "\n".join(text_parts)})
                    else:
                        text_content = "\n".join(text_parts)
                        if text_content:
                            openai_messages.append({"role": "user", "content": text_content})

        # 2. Convert tools
        openai_tools = []
        if tools:
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t.get("input_schema", {}),
                    }
                })

        # 3. Call API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools if openai_tools else None,
            max_tokens=max_tokens,
            timeout=self.api_timeout,
            extra_body=self.extra_body,
        )

        # 4. Parse response
        msg = response.choices[0].message
        text = msg.content or ""
        
        # Capture DeepSeek reasoning if available (NVIDIA NIM format)
        reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
        if reasoning:
            text = f"<reasoning>\n{reasoning}\n</reasoning>\n\n{text}"

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments),
                ))

        in_tok = response.usage.prompt_tokens if response.usage else 0
        out_tok = response.usage.completion_tokens if response.usage else 0

        return LLMResponse(
            text=text.strip(),
            tool_calls=tool_calls,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        if "deepseek" in self.model.lower() and "flash" in self.model.lower():
            # DeepSeek V4 Flash: placeholder ($0.10 / 1M in, $0.10 / 1M out)
            return (input_tokens / 1_000_000 * 0.1) + (output_tokens / 1_000_000 * 0.1)
        return (input_tokens / 1_000_000 * 0.5) + (output_tokens / 1_000_000 * 1.5)


class InteractiveModel(LanguageModel):
    """Model that prompts the user (or the AI assistant) for responses via stdin."""

    def __init__(self, model: str = "interactive"):
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
        max_tokens: int,
    ) -> LLMResponse:
        import sys
        
        print("\n\n" + "="*80)
        print("INTERACTIVE MODEL PROMPT")
        print("="*80)
        print(f"System: {system[:200]}...\n")
        print(f"Latest Message: {messages[-1]['role'].upper()}")
        print(messages[-1]['content'])
        print("="*80)
        print("Provide your response as a valid JSON object. End with a line containing only 'EOF'.")
        print("Format: {\"text\": \"response text\", \"tool_calls\": [{\"name\": \"tool_name\", \"input\": {\"arg\": \"val\"}}]}")
        print("="*80)
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == "EOF":
                    break
                lines.append(line)
            except EOFError:
                break
                
        resp_str = "\n".join(lines).strip()
        if not resp_str:
            return LLMResponse("No response provided.", [], 0, 0)
            
        try:
            data = json.loads(resp_str)
            text = data.get("text", "")
            tcs = []
            for idx, tc in enumerate(data.get("tool_calls", [])):
                tcs.append(ToolCall(id=f"call_{idx}", name=tc["name"], input=tc.get("input", {})))
            return LLMResponse(text=text, tool_calls=tcs, input_tokens=10, output_tokens=10)
        except Exception as e:
            return LLMResponse(f"Error parsing interactive input: {e}\nRaw input: {resp_str}", [], 0, 0)

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0

