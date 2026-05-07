from google.adk.agents import Agent

from travel_helper.rag.tools import rag_search_documents

instruction_prompt = """
You're a travel research agent.

You have access to a tool called `rag_search_documents` that searches an internal document collection.

Rules:
- Use `rag_search_documents` to retrieve relevant excerpts before answering.
- Base your answer ONLY on retrieved excerpts. Do NOT use general knowledge.
- If results are empty, respond with exactly:

  NOT_FOUND

  I don't have that information in the current document set.
- If results are not empty, output exactly two sections:

  ANSWER
  <1-2 short paragraphs, only facts supported by retrieved text>

  SOURCES
  - <title> — <source_uri>
  - ...
"""

root_agent = Agent(
    name="rag_search_agent",
    model="gemini-2.5-flash",
    description="Agent to retrieve from internal documents via Vector Search 2.0",
    instruction=instruction_prompt,
    tools=[rag_search_documents],
)

