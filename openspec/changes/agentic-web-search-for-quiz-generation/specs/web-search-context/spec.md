# Spec Delta

## Purpose

让系统在生成题目前能够为用户输入的主题自动获取更准确、更新的外部知识上下文，既支持关键词搜索，也支持网页内容提取，并在外部检索不可用时平滑降级。

## ADDED Requirements

### Requirement: System can obtain external knowledge from keywords or URLs
The system SHALL support two knowledge acquisition modes before quiz generation: keyword-based search for topical queries, and full-page content extraction when the user input is or contains a URL.

#### Scenario: Keyword input uses search mode
- **WHEN** the user submits a topic, phrase, or paragraph without a URL
- **THEN** the system acquires external knowledge through web search and produces a knowledge summary for quiz generation

#### Scenario: URL input uses extraction mode
- **WHEN** the user submits a URL or text that contains a URL
- **THEN** the system extracts content from the referenced page and produces a knowledge summary for quiz generation

### Requirement: System chooses acquisition strategy adaptively
The system SHALL choose knowledge acquisition strategy adaptively based on the user input, including whether to use a lightweight search summary, deeper content retrieval, URL extraction, or a combination of these approaches.

#### Scenario: Simple topic uses lightweight retrieval
- **WHEN** the submitted topic is simple or common and lightweight search results are sufficient
- **THEN** the system uses concise external results to build the knowledge summary without unnecessarily retrieving long raw content

#### Scenario: Complex or emerging topic uses deeper retrieval
- **WHEN** the submitted topic is complex, niche, or likely to be affected by recent developments
- **THEN** the system uses deeper retrieval and richer content to improve factual accuracy before quiz generation

#### Scenario: Regional intent is inferred without unsupported location parameters
- **WHEN** the submitted topic implies a regional context such as domestic or overseas usage
- **THEN** the system adapts retrieval through instantiation-time country boosting (when supported), query rewriting, and source-domain preference, rather than relying on unsupported city or country runtime invocation parameters

### Requirement: Knowledge summary is bounded and injected into quiz generation
The system SHALL transform retrieved external materials into a bounded knowledge summary and provide that summary to the quiz generation stage as reference context.

#### Scenario: Retrieved context is long
- **WHEN** the acquired external materials exceed the allowed prompt budget
- **THEN** the system truncates or compresses them into a bounded knowledge summary before quiz generation

#### Scenario: Retrieved context is available
- **WHEN** knowledge acquisition succeeds
- **THEN** the quiz generation stage receives both the original user input and the generated knowledge summary

### Requirement: Retrieval failures degrade gracefully
The system SHALL treat web retrieval as an enhancement rather than a prerequisite, and SHALL continue quiz generation without external knowledge when retrieval fails, times out, or returns no useful results.

#### Scenario: Search or extraction times out
- **WHEN** external knowledge acquisition times out
- **THEN** the system logs a warning and continues quiz generation without external context

#### Scenario: Search or extraction returns no useful result
- **WHEN** external knowledge acquisition completes but yields no useful result
- **THEN** the system continues quiz generation using only the original user input
