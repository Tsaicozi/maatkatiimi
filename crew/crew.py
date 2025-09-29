from crewai import Crew, Process
from .agents import Researcher, Builder, Reviewer
from .tasks import ResearchTask, BuildTask, ReviewTask

# Prosessi: tutkija -> rakentaja -> tarkastaja

crew = Crew(
    agents=[Researcher, Builder, Reviewer],
    tasks=[ResearchTask, BuildTask, ReviewTask],
    process=Process.sequential,  # voit vaihtaa parallel + reviewer-gate
    verbose=True,
)