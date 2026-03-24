import queue, threading
from strands import Agent
from strands.models.openai import OpenAIModel

import config
import src.agents.agents as agents_module
from src.agents.handler import OrchestratorCallbackHandler, AnswerCallbackHandler

model = OpenAIModel(
    model_id=config.llm_config['model'],
    client_args={
        "api_key": config.llm_config['api_key'],
        "base_url": config.llm_config['base_url']
    }
)

def build_orchestrator_agent(q: queue.Queue, text_q: queue.Queue, download_q: queue.Queue, done_event: threading.Event):
    agents_module._callback_handler = AnswerCallbackHandler(text_q, done_event)
    agents_module._download_q = download_q

    return Agent(
        model=model,
        tools=[
            agents_module.brand_model_agent,
            agents_module.query_versioning_agent,
            agents_module.query_knowledge_agent,
            agents_module.answer_agent
        ],
        callback_handler=OrchestratorCallbackHandler(q, download_q),
        system_prompt=config.prompts['ORCHESTRATION_PROMPT'].format(
            name=config.agent['agent_name']
        )
    )

# if __name__ == "__main__":
#     user_input = input("Tú: ").strip()
#     orchestrator_agent = build_orchestrator_agent(queue.Queue, queue.Queue, queue.Queue)
#     response = orchestrator_agent(user_input)
#     print(f"\nAgente: {response}\n")