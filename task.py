from crewai import Task
from billing_agent import billing_agent

billing_task = Task(
    description=(
        "Always output exactly:\n\n"
        "Thought: routing\n"
        "Action: BillingTool\n"
        "Action Input: {\"user_input\": \"{input}\"}\n\n"
        "Do NOT modify {input} in any way."
    ),
    expected_output="BillingTool output only.",
    agent=billing_agent
)
