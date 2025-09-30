import os
import sys
from dotenv import load_dotenv
from crew.crew import crew
from crew.tasks import ResearchTask, BuildTask, ReviewTask

# Lataa .env3 tiedosto
load_dotenv('.env3')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run.py \"feature: kuvaus\"")
        sys.exit(1)

    feature = sys.argv[1]

    # Syötä dynaamiset muuttujat tehtäville
    inputs = {"feature": feature}

    result = crew.kickoff(inputs=inputs)
    print("\n=== CREW RESULT ===\n")
    print(result)