from crewai import Crew, Process
from .tasks_invest import Intake, Theme, Screen, Risk, Synthesize, Review

# Prosessi: Intake → (Theme | Screen | Risk) → Synthesize → Review
# Huom: CrewAI suorittaa tehtävät järjestyksessä; fan‑out on looginen vaihe –
# anna Theme/Screen/Risk tuottaa syötteet, jotka Synthesize kokoaa.

invest_crew = Crew(
    agents=[
        Intake.agent, Theme.agent, Screen.agent, Risk.agent, Synthesize.agent, Review.agent
    ],
    tasks=[Intake, Theme, Screen, Risk, Synthesize, Review],
    process=Process.sequential,
    verbose=True,
)