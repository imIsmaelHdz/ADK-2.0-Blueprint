from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.genai import types as genai_types

root_agent = Agent(
    name="google_search_agent",
    model="gemini-2.5-flash",
    description=(
        "Searches Google for all three travel topics at once: entry requirements, "
        "airport transport, and tourist attractions. Call once with destination and nationality."
    ),
    instruction="""
    You are a travel research agent. You will be given a destination city and traveler nationality.

    Call google_search ONCE with a combined query covering all three topics:
      "<destination> travel guide <nationality> passport visa entry requirements airport transport top attractions"

    From the search results, extract and return findings in exactly this format:

    ENTRY REQUIREMENTS
    <2-3 sentences: visa needed yes/no, max stay, how to apply>

    AIRPORT TO CITY CENTER
    <2-3 sentences: transport options, approx cost, travel time>

    TOURIST ATTRACTIONS
    1. <attraction> — <one sentence>
    2. ...
    (list 10)
    """,
    tools=[google_search],
    planner=BuiltInPlanner(thinking_config=genai_types.ThinkingConfig(thinking_budget=0)),
)
