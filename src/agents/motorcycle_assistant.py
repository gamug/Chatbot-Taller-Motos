from strands import Agent
from strands.models.openai import OpenAIModel

import config
from src.agents.agents import brand_model_agent, query_versioning_agent, query_knowledge_agent, answer_agent

model = OpenAIModel(
    model_id=config.llm_config['model'],
    client_args={
        "api_key": config.llm_config['api_key'],
        "base_url": config.llm_config['base_url']
    }
)

orchestrator_agent = Agent(
    model=model,
    tools=[brand_model_agent, query_versioning_agent, query_knowledge_agent, answer_agent],
    system_prompt=config.prompts['ORCHESTRATION_PROMPT'].format(
        name=config.agent['agent_name'],
        language=config.agent['answer_language'],
        output=config.agent['knowledge_output']
    )
)

if __name__ == "__main__":
    user_input = input("Tú: ").strip()
    response = orchestrator_agent(user_input)
    print(f"\nAgente: {response}\n")