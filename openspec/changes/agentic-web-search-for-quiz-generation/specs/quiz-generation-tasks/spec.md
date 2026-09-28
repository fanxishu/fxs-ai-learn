# Spec Delta

## Purpose

让 AI 出题流程从同步长耗时请求升级为异步任务模式，使前端可以先拿到任务状态并通过轮询获取结果，降低超时风险并改善生成体验。

## ADDED Requirements

### Requirement: Quiz generation request creates an asynchronous task
The system SHALL create a quiz-generation task when the client submits a quiz generation request, persist the task state, and immediately return task metadata instead of waiting for final quiz output in the same request.

#### Scenario: Successful task creation
- **WHEN** an authenticated user submits a valid quiz generation request
- **THEN** the system creates a new task with an initial status and returns a task identifier and current task status

#### Scenario: Invalid request is rejected before task creation
- **WHEN** the request payload is invalid or contains prohibited content
- **THEN** the system rejects the request and does not create a task

### Requirement: Client can poll quiz-generation task status
The system SHALL provide a way for the client to poll the current state of a quiz-generation task owned by the requesting user.

#### Scenario: Task is still running
- **WHEN** the client polls a task that is not finished yet
- **THEN** the system returns the current task status without quiz questions

#### Scenario: Task completed successfully
- **WHEN** the client polls a task that has completed successfully
- **THEN** the system returns the completed status together with the generated quiz payload

#### Scenario: Task failed
- **WHEN** the client polls a task that has failed
- **THEN** the system returns a failed status and an error message suitable for the client to display or retry

### Requirement: Task processing preserves quiz-generation safeguards
The asynchronous task flow SHALL preserve the existing safeguards of quiz generation, including authentication, input validation, sensitive-content checks, structured-output validation, and existing fallback behavior.

#### Scenario: Retrieval or LLM issues occur during processing
- **WHEN** the task encounters retrieval failure, model failure, or structured-output instability during processing
- **THEN** the system applies the configured degradation and fallback strategy before deciding whether the task succeeds or fails

#### Scenario: Successful task still persists quiz data
- **WHEN** a task completes successfully for a logged-in user
- **THEN** the system persists the generated quiz session and makes the result available through the task status response

### Requirement: Task visibility is limited to the owner
The system SHALL ensure that a quiz-generation task can only be queried by the authenticated user who created it.

#### Scenario: User polls own task
- **WHEN** the task owner polls the task identifier
- **THEN** the system returns the task state and any available result

#### Scenario: User polls another user's task
- **WHEN** a user polls a task identifier created by a different user
- **THEN** the system rejects the request without exposing whether the task exists
