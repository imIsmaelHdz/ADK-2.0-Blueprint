# Agent Development Kit (ADK) Demos

<img src="https://github.com/google/adk-docs/blob/main/docs/assets/agent-development-kit.png" alt="Agent Development Kit Logo" width="150">

[Agent Development Kit](https://github.com/google/adk-python) (ADK) is an open-source toolkit for building, evaluating,
and deploying AI agents.

This repository is a collection of ADK samples/tutorials to get you up to speed.

> [!CAUTION]
> Before you start, make sure to follow the [setup](setup.md) page.

## About this repository

This project starts from the **official Google ADK sample material** (the same patterns and agents you see in the [ADK Python](https://github.com/google/adk-python) ecosystem and related demos). On top of that baseline, this fork adds a **FastAPI API gateway** under [`travel_helper_api/`](./travel_helper_api) so you can talk to agents over **HTTP with JSON** (including a streaming endpoint), instead of only CLI or the ADK web UI.

The goal is to bring **software engineering foundations** to an AI agent project: a clearer service layout, explicit API contracts, and a path toward production concerns (sessions, errors, deployment) while keeping the original agent logic intact.

## Samples

Follow the following sub-pages for samples/tutorials (in order):

* [Travel Helper Agent](./travel_helper)
* [Travel Helper Agent Runner](./travel_helper_runner) (depends on the above)
* [ADK Callbacks Agent](./adk-callbacks-agent/)

## References

* [Documentation: Agent Development Kit](https://google.github.io/adk-docs/)
* [GitHub: ADK Python repository](https://github.com/google/adk-python)
* [GitHub: ADK samples repository](https://github.com/google/adk-samples)
* [Blog: From Zero to Multi-Agents: A Beginner’s Guide to Google Agent Development Kit (ADK)](https://medium.com/@sokratis.kartakis/from-zero-to-multi-agents-a-beginners-guide-to-google-agent-development-kit-adk-b56e9b5f7861)
* [GitHub: Google ADK Walkthrough: Your Step-by-Step Development Tutorial](https://github.com/sokart/adk-walkthrough/tree/main)
* [Blog: Agent Development Kit: Making it easy to build multi-agent applications](https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/)
* [Awesome Google ADK](https://github.com/tsubasakong/awesome-google-adk)

-------

This is not an official Google product.
