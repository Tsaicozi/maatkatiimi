from dotenv import load_dotenv
from crew.crew_invest import invest_crew
from crew.memory_invest import IdeaRegistry
import sys

# Lataa .env3 tiedosto
load_dotenv('.env3')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_idea.py \"brief: lyhyt kuvaus ideasta\"")
        sys.exit(1)

    brief = sys.argv[1]
    result = invest_crew.kickoff(inputs={"brief": brief})
    print("\n=== INVESTMENT IDEA RESULT ===\n")
    print(result)
    
    # Näytä myös tallennetut ideat
    ideas = IdeaRegistry()
    all_ideas = ideas.list_all()
    if all_ideas:
        print("\n=== TALLENNETUT IDEAT ===\n")
        for idea in all_ideas[:5]:  # Näytä viimeisimmät 5
            print(f"ID: {idea['id']}")
            print(f"Title: {idea['title']}")
            print(f"Status: {idea['status']}")
            print(f"Created: {idea['created']}")
            print("---")