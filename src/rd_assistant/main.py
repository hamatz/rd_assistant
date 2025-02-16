import asyncio
from dotenv import load_dotenv
from .config import Config
from .llm.service import LLMServiceFactory
from .core.analyzer import RequirementAnalyzer
from .cli.interface import InteractiveDialogue

async def main():
    load_dotenv()
    try:
        config = Config()
        llm_config = config.get_llm_config()
        llm_service = LLMServiceFactory.create(llm_config)
        analyzer = RequirementAnalyzer(llm_service)
        dialogue = InteractiveDialogue(analyzer, config)
        await dialogue.start_dialogue()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
