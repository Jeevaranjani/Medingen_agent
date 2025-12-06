from crewai import Crew
from task import billing_task
from billing_agent import billing_agent
from billing_tool import engine

crew = Crew(
    agents=[billing_agent],
    tasks=[billing_task],                            
    max_rpm=1 
     
)

print("Medingen Billing Assistant")
print("Type 'exit' to quit.\n")
print("Agent: Hello! Please type any message to begin.\n")

while True:
    user_msg = input("You: ").strip()
    if user_msg.lower() == "exit":
        break

    response = crew.kickoff(inputs={"input": user_msg})
    print("Agent:", response, "\n")

