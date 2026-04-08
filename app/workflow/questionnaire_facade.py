from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.core.models.questionnaire import Question
from app.workflow.questionnaire_engine import QuestionnaireEngine
from app.workflow.questionnaire_session import QuestionnairePolicy, QuestionnaireSession

AnswerProvider = Callable[[Question], Dict[str, Any]]


class QuestionnaireFacade:
    """Thin facade for UI layers.

    PyQt can use this class to fetch available questions and run a session
    without depending on internal implementation details.
    """

    def __init__(self, schema_path: Path, policy: Optional[QuestionnairePolicy] = None) -> None:
        self.engine = QuestionnaireEngine(schema_path=schema_path)
        self.policy = policy or QuestionnairePolicy()

    def get_question_fields(self) -> List[str]:
        return list(self.engine.required_fields)

    def get_question(self, field: str) -> Optional[Question]:
        return self.engine.questions.get(field)

    def list_questions(self) -> List[Question]:
        return [self.engine.questions[field] for field in self.engine.required_fields if field in self.engine.questions]

    def create_session(self) -> QuestionnaireSession:
        return QuestionnaireSession(engine=self.engine, policy=self.policy)

    def run(self, answer_provider: AnswerProvider):
        return self.create_session().run(answer_provider=answer_provider)
