import json
from typing import Any, Dict, List

from app.core.models.generation import GenerationRequest, GenerationResult, GeneratedSection
from app.llm.client_factory import get_openai_client


class ContentGenerator:
    """Step3 generation layer.

    Produces structured content and a LaTeX-ready body from a validated requirement.
    """

    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        self.model_name = model_name
        self.client = get_openai_client()

    def generate(self, request: GenerationRequest) -> GenerationResult:
        prompt = self._build_prompt(request)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=prompt,
                temperature=0.4,
            )
            raw_text = response.choices[0].message.content or ""
            usage = self._extract_usage(response)
            structured = self._parse_response(raw_text)
            return GenerationResult(
                ok=True,
                model=self.model_name,
                outline=structured.get("outline", []),
                sections=[GeneratedSection(**item) for item in structured.get("sections", [])],
                latex_body=structured.get("latex_body", ""),
                raw_text=raw_text,
                usage=usage,
            )
        except Exception as exc:  # noqa: BLE001 - want surface API/runtime failure to caller
            return GenerationResult(ok=False, model=self.model_name, error_message=str(exc))

    def _build_prompt(self, request: GenerationRequest) -> List[Dict[str, str]]:
        requirement_json = json.dumps(request.requirement, ensure_ascii=False, indent=2)
        system_message = (
            "你是一个内容生成器，只负责生成内容结构，不要输出LaTeX排版命令。"
            "输出必须是严格JSON，包含outline、sections、latex_body三个键。"
            "outline是章节标题列表，sections是[{title, content}]，latex_body是可直接嵌入模板的正文文本。"
        )
        user_message = (
            "请基于以下需求生成一份结构化内容：\n"
            f"项目名称：{request.project_name}\n"
            f"模板ID：{request.template_id}\n"
            f"需求JSON：\n{requirement_json}\n\n"
            "约束：\n"
            "1. 不要输出任何解释性文字。\n"
            "2. 只输出JSON。\n"
            "3. 内容要适合LaTeX模板渲染。\n"
        )
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    @staticmethod
    def _parse_response(raw_text: str) -> Dict[str, Any]:
        raw_text = raw_text.strip()
        if not raw_text:
            raise ValueError("model returned empty response")

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError("model response is not valid JSON: {0}".format(exc)) from exc

    @staticmethod
    def _extract_usage(response: Any) -> Dict[str, Any]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
