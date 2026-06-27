import os

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools.agent_tool import AgentTool
from google.genai import types as genai_types

from travel_helper.assistant_response_guard import travel_helper_after_model_callback
from travel_helper.agents.google_search import root_agent as google_search_agent
from travel_helper.tools.currency import convert_currency
from travel_helper.tools.weather import weather_for_city


def _rag_tool():
    if os.environ.get("TRAVEL_HELPER_USE_RAG", "").strip().lower() not in ("1", "true", "yes", "on"):
        return None
    try:
        from travel_helper.rag.tools import rag_search_documents
        return rag_search_documents
    except ImportError:
        return None


instruction_prompt = """
    You are a travel helper agent that provides essential pre-departure information.

    ## Extracting trip details:
    You need: nationality/passport country, origin city, destination city.
    - Infer nationality from origin country when obvious (e.g. "I'm from Mexico" → Mexican passport).
    - Only ask for what you genuinely cannot infer. If origin city and destination city are clear,
      assume nationality matches the origin country and proceed.
    - If truly ambiguous (e.g. expat, dual citizen), ask in one short friendly sentence.

    ## Once you have all three details:
    Call ALL of the following tools AT THE SAME TIME in a single batch:
      • weather_for_city(city=<destination>)
      • convert_currency(from_currency=<origin currency>, to_currency=<destination currency>)
      • google_search_agent(request="destination: <destination>, nationality: <nationality>")

    Wait for all results, then reply in a warm, conversational tone — like a well-traveled friend
    giving advice over coffee. Use short paragraphs, not walls of text. Lead with the most
    important thing (visa), weave in the rest naturally. Use emojis sparingly to break sections.

    Cover in this order, but write it as flowing conversation:
    1. Visa / entry — the critical bit first
    2. Money — quick exchange rate callout
    3. Weather — what to pack, not a data dump
    4. Getting into the city from the airport
    5. 5–7 must-see spots (not a numbered list, just a sentence or two per highlight)

    Keep the whole reply under 250 words. End with one encouraging send-off line.
"""


def _build_tools():
    tools = [weather_for_city, convert_currency]
    rag = _rag_tool()
    if rag:
        tools.append(rag)
    tools.append(AgentTool(agent=google_search_agent))
    return tools


root_agent = Agent(
    name="travel_helper_agent",
    model="gemini-2.5-flash",
    description="Travel helper agent providing essential pre-departure information",
    instruction=instruction_prompt,
    tools=_build_tools(),
    after_model_callback=travel_helper_after_model_callback,
    planner=BuiltInPlanner(thinking_config=genai_types.ThinkingConfig(thinking_budget=0)),
)
