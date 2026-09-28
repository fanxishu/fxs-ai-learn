# Spec Delta

## MODIFIED Requirements

### Requirement: Agentic retrieval chooses between knowledge base and web search
When a valid `doc_id` is provided, the system SHALL use an agent with access to a knowledge-base retrieval tool (scoped to the requesting user and the specified document) and, when web retrieval is enabled and configured, external search and URL-extraction tools. The agent SHALL autonomously decide which tool or combination of tools to invoke to produce a knowledge summary for quiz generation.

#### Scenario: Agent retrieves from knowledge base only
- **WHEN** the knowledge-base retrieval tool returns sufficient relevant content for the topic
- **THEN** the agent produces a knowledge summary based on the retrieved document chunks without necessarily invoking external retrieval tools

#### Scenario: Agent supplements with web search
- **WHEN** the knowledge-base retrieval tool returns insufficient or partial content and external retrieval is enabled
- **THEN** the agent MAY additionally invoke external search or URL extraction to supplement the knowledge summary

#### Scenario: User input contains a URL and doc_id
- **WHEN** a valid `doc_id` is provided and the quiz request also includes a URL in the user input
- **THEN** the agent MAY use both the scoped knowledge-base retrieval tool and URL extraction to build the final knowledge summary

#### Scenario: Web search unavailable, knowledge base still used
- **WHEN** external retrieval is disabled, not configured, or temporarily unavailable but a valid `doc_id` is provided
- **THEN** the agent uses only the knowledge-base retrieval tool to produce the knowledge summary

#### Scenario: Retrieval agent failure degrades gracefully
- **WHEN** the retrieval agent raises an exception or times out
- **THEN** the system logs a warning and proceeds to generate the quiz without a knowledge summary, rather than failing the entire request
