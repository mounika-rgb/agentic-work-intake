# HEDAMO Agentic Work Intake & Execution

An AI-powered work intake and execution prototype that converts unstructured work requests into structured, reviewable, and partially automated workflows.

The system uses Gemini to understand incoming work requests, break them into actionable tasks, route those tasks based on their execution requirements, execute supported tools, involve a human when approval is required, persist workflow state, and maintain a visible activity trace.

## Project Objective

The goal of this project is to demonstrate an agentic workflow that can transform unstructured work instructions into an executable workflow while avoiding assumptions when important information is missing.

### Core Workflow

```text
Unstructured Work Request
          ↓
     AI Interpretation
          ↓
   Structured Work Item
          ↓
    Action Planning
          ↓
   Action Routing
          ↓
 ┌────────┼───────────────┐
 ↓        ↓               ↓
Execute  Human Review   Clarification
Auto     Required       Required
 ↓        ↓               ↓
Tool     Approve/Reject  Wait for Info
Execution
          ↓
      Persistence
          ↓
     Activity Trace
          ↓
       Completion

## Features

- Unstructured work request intake through a web interface
- Gemini-powered AI interpretation
- Structured JSON output using Pydantic schemas
- Task title and summary generation
- Priority detection
- Deadline detection
- Missing-information detection
- Action-item generation
- Agentic action planning and routing
- Automatic execution of supported actions
- Human-in-the-loop approval
- Action edit and reject support
- Persistent workflow state using SQLite
- Tool execution and tool outputs
- Visible activity trace
- Website checking
- Simulated reminders
- Markdown brief generation
- Stored-work search
- Clear failure and clarification handling

### Action Routing

Each action is routed into one of four states:

| Route | Purpose |
|---|---|
| `EXECUTE_AUTOMATICALLY` | Execute a concrete supported action automatically |
| `PREPARE_FOR_HUMAN_REVIEW` | Prepare an output that requires human approval |
| `REQUIRES_CLARIFICATION` | Stop when important information is missing |
| `CANNOT_EXECUTE` | Identify tasks that require unavailable capabilities |

### 5. Architecture

The application follows a layered architecture where each component has a specific responsibility.

```mermaid
flowchart TD
    A[User] --> B[Web Interface]

    B --> C[FastAPI API]

    C --> D[LLM Interpretation]

    D --> E[Structured Work Interpretation]

    E --> F[Agent / Planner]

    F --> G{Action Route}

    G -->|EXECUTE_AUTOMATICALLY| H[Executor]

    G -->|PREPARE_FOR_HUMAN_REVIEW| I[Human Approval]

    G -->|REQUIRES_CLARIFICATION| J[Blocked Action]

    G -->|CANNOT_EXECUTE| K[Unsupported Action]

    I -->|Approve| H
    I -->|Edit| I
    I -->|Reject| L[Rejected]

    H --> M[Tools]

    M --> N[Tool Output]

    N --> O[SQLite Database]

    J --> O
    K --> O
    L --> O

    O --> P[Activity Trace]

    P --> B

## 6. Agent Workflow

The system processes a work request through multiple controlled stages.

### 1. Intake

The user submits unstructured text through the web interface.

Example:

```text
Review https://hedamo.com, run whatever automated checks
your prototype supports, and produce a short technical report.

### 2. AI Interpretation

The unstructured request is sent to Gemini for analysis.

Gemini converts the request into structured information instead of returning free-form text.

The interpretation includes:

- Task title
- Summary
- Priority
- Detected deadline
- Missing information
- Action items
- Automation possibilities
- Human confirmation requirements

The generated response is validated using Pydantic schemas before it is passed to the next stage.

### 3. Agentic Planning

The structured interpretation is passed to the agent and planner.

The planner examines each action item and decides how it should be handled.

Each action is routed to one of four routes:

- `EXECUTE_AUTOMATICALLY`
- `PREPARE_FOR_HUMAN_REVIEW`
- `REQUIRES_CLARIFICATION`
- `CANNOT_EXECUTE`

### 4. Tool Selection

For actions that can be handled by the prototype, the planner selects an appropriate tool.

Available tools include:

- `web_check`
- `draft_communication`
- `generate_markdown_brief`
- `simulate_reminder`
- `search_stored_work`

### 5. Action Execution

The executor receives the planned actions.

If an action is safe and fully concrete, it can be executed automatically.

For example:

```text
Set a simulated reminder for 7 days
        ↓
EXECUTE_AUTOMATICALLY
        ↓
simulate_reminder
        ↓
COMPLETED

### 6. Human-in-the-Loop

Some actions require human approval before they are treated as completed.

For example:

```text
Draft a thank-you email
        ↓
PREPARE_FOR_HUMAN_REVIEW
        ↓
AWAITING_CONFIRMATION
        ↓
Human reviews the action
        ↓
Approve / Edit / Reject

### 7. Clarification

If important information is missing, the system does not invent the missing details.

For example:

```text
Please take care of the documentation and send it
to everyone before the meeting.

The system identifies missing information such as:

- Which documentation?
- Who are the recipients?
- Which meeting?
- What deadline?

The affected action is routed to:

```text
REQUIRES_CLARIFICATION

### 8. Persistence

The application stores workflow state in SQLite.

The stored information includes:

- Original request
- Structured interpretation
- Action items
- Action status
- Tool parameters
- Tool outputs
- Timestamps
- Activity events

### 9. Activity Trace

The application records important events during processing.

For example:

```text
Work Request Ingested
        ↓
Action Planned
        ↓
Action Executed
        ↓
Action Approved
        ↓
Intake Processing Finished

The activity trace provides a visible history of what the system did during the workflow.

### End-to-End Flow

```
User
```

 ↓

Unstructured Request

 ↓

FastAPI Intake

 ↓

Gemini Interpretation

 ↓

Pydantic Validation

 ↓

Agent / Planner

 ↓

Action Routing

 ↓

Tool Execution / Human Review / Clarification

 ↓

SQLite Persistence

 ↓

Activity Trace

 ↓

Final Status
## 7. Tools / Functions

The prototype includes multiple bounded tools that can be selected and executed based on the planned action.

7.1 Web Check

web_check

Used for bounded website checks.

Example:

Review https://hedamo.com

The system extracts the URL and passes it to the website-checking tool.

The tool performs only the checks supported by the prototype and returns information that it can actually verify.

The application does not claim to perform checks that are not implemented.

7.2 Draft Communication

draft_communication

Used to prepare communication drafts such as:

Emails

Messages

Slack-style communication

Communication drafts are routed to human review before being treated as completed.

The prototype does not send real external emails.

7.3 Generate Markdown Brief

generate_markdown_brief

Used to generate short markdown-based briefs or reports from available work information.

Because generated documents may require human review, this action can be routed to:

PREPARE_FOR_HUMAN_REVIEW

7.4 Simulate Reminder

simulate_reminder

Used to create simulated reminders.

Example:

Set a reminder for 7 days

The tool calculates a simulated reminder time and records the result.

It does not create a real external calendar event.

7.5 Search Stored Work

search_stored_work

Used to search previously stored work records.

The tool accepts a search query and returns matching stored work information.

Tool Routing Example

User Request
      ↓
AI Interpretation
      ↓
Planner
      ↓
Select Tool
      ↓
┌──────────────────────────────┐
│ web_check                    │
│ draft_communication          │
│ generate_markdown_brief      │
│ simulate_reminder            │
│ search_stored_work           │
└──────────────────────────────┘
      ↓
Executor
      ↓
Tool Output
      ↓
SQLite Database
      ↓
Activity Trace

8. Human-in-the-Loop Control

The application includes an explicit human-in-the-loop workflow for actions that should not be completed automatically.

When an action is classified as PREPARE_FOR_HUMAN_REVIEW, the system pauses the action and waits for a human decision.

The user can:

Approve the action

Edit the action

Reject the action

Approval Workflow

Action Created
      ↓
PREPARE_FOR_HUMAN_REVIEW
      ↓
AWAITING_CONFIRMATION
      ↓
Human Review
      ↓
┌──────────┬──────────┬──────────┐
↓          ↓          ↓
Approve    Edit       Reject
↓          ↓          ↓
Execute    Review     Rejected
           Again

Example

For a partner discussion request, the system may create:

Draft a thank-you email for the partner discussion.

The action is routed to:

PREPARE_FOR_HUMAN_REVIEW

The user can review the generated draft and choose to:

Approve it

Edit it

Reject it

The action is not treated as completed until the human approval step is performed.

Safety Boundary

The prototype does not send real external emails.

Communication-related actions are prepared as drafts and require human review before completion.

9. Failure Handling

The application handles failures explicitly instead of silently reporting success.

For example, when the Gemini API quota is exhausted, the API returns:

429 Too Many Requests

instead of returning a fake successful result.

Example response:

{
  "detail": "Gemini API quota exceeded. Please wait for the quota to reset or check your Gemini API plan."
}

This demonstrates that external service failures are surfaced clearly to the user.

The application also handles clarification cases by blocking actions when required information is missing instead of inventing information.

10. Test Scenarios

The prototype was tested against the three required assignment scenarios.

Scenario 1 — Routine Business Work

Input:

Analyze the recent partner discussion to summarize it,
identify follow-up actions, draft a thank-you email,
and set a reminder for 7 days.

The system:

Detects the requested work

Identifies missing discussion content

Identifies the missing email recipient

Blocks actions requiring missing information

Routes the communication draft for human review

Executes the simulated 7-day reminder

Records the workflow in the activity trace

Scenario 2 — Product / Website Work

Input:

Review https://hedamo.com, run whatever automated checks
your prototype supports, and produce a short technical report.

The system:

Extracts the website URL

Identifies the website-checking action

Routes supported website checks to web_check

Generates the requested markdown brief where applicable

Records tool execution and outputs

Does not claim checks that the prototype cannot actually perform

Scenario 3 — Ambiguous Request

Input:

Please take care of the documentation and send it
to everyone before the meeting.

The system identifies missing information instead of inventing details.

Examples of missing information:

Which documentation?

Who should receive it?

Which meeting?

What is the meeting date or deadline?

The affected actions are routed to:

REQUIRES_CLARIFICATION

11. Persistence

The application uses SQLite to persist workflow state between runs.

The database stores:

Original work request

Structured interpretation

Action items

Action status

Tool parameters

Tool outputs

Work-item status

Timestamps

Activity events

This allows previously processed work to remain available after the application is restarted.

12. Activity Trace

The application maintains a visible activity trace for each work item.

The trace records important workflow events such as:

Work Request Ingested
        ↓
Action Planned
        ↓
Action Blocked / Paused / Executed
        ↓
Human Approval
        ↓
Tool Output Recorded
        ↓
Intake Processing Finished

The activity trace makes the system's actions understandable without requiring the user to inspect the source code.

13. Setup and Installation

Clone the repository:

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <PROJECT_DIRECTORY>

Create a virtual environment:

python -m venv .venv

Activate the virtual environment on Windows:

.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Create a .env file:

GEMINI_API_KEY=your_gemini_api_key_here

Never commit the .env file or API keys to GitHub.

Start the FastAPI server:

uvicorn app.main:app --reload

Open the application:

http://127.0.0.1:8000

Open Swagger API documentation:

http://127.0.0.1:8000/docs

14. Running Tests

Run the test suite:

pytest

The implemented test suite currently passes:

8 passed

15. Environment Variables

The application uses the following environment variable:

GEMINI_API_KEY=your_gemini_api_key_here

The API key is loaded from the .env file using python-dotenv.

API keys and other secrets must never be committed to the repository.

16. Design Decisions

Structured LLM Output

The LLM response is validated against a Pydantic schema rather than relying on free-form text.

This makes downstream planning and execution more predictable.

Explicit Action Routing

Every action receives an explicit route.

This prevents the system from treating every task as automatically executable.

Human Approval Boundary

Actions that generate communication or other reviewable outputs require human approval.

Bounded Tools

The executor can only call tools explicitly supported by the application.

The LLM cannot arbitrarily execute commands or external operations.

Persistent State

SQLite was selected because it is lightweight and sufficient for this prototype.

17. Limitations

Website checks are limited to the functionality implemented by the prototype.

Reminder functionality is simulated and does not create real calendar events.

Communication tools generate drafts but do not send real external emails.

The prototype uses SQLite rather than a production database.

The application is designed as a prototype rather than a production-scale distributed system.

18. What I Would Build Next

Add authentication and role-based access control.

Add integrations with task-management and communication platforms.

Improve website monitoring with additional bounded checks.

Add richer document and meeting-note ingestion.

Deploy the application with production monitoring and observability.

19. How I Used AI

AI coding tools were used during development to:

Understand and break down the assignment requirements

Generate and refine implementation ideas

Debug Python and FastAPI issues

Improve error handling

Design structured Pydantic schemas

Test API workflows

Improve technical documentation

AI-generated suggestions were reviewed and tested rather than accepted blindly.

For example, during development, an incorrect workflow behavior was identified through API testing and inspection of the resulting action status and activity trace. The implementation was then corrected and retested.

20. Project Status

The prototype currently demonstrates:

AI-powered work interpretation

Structured JSON output

Agentic planning

Explicit action routing

Bounded tool execution

Human-in-the-loop approval

Edit and reject workflow

Missing-information detection

SQLite persistence

Activity tracing

Failure handling

FastAPI APIs

Web interface

Automated tests

The project demonstrates a small but functional agentic work-intake and execution workflow where AI interpretation, planning, execution, human approval, persistence, and failure handling are clearly separated.