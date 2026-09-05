# ZenUI

> An enterprise AI interface that transforms natural-language requests into dynamic, context-aware user interfaces.

ZenUI is an AI-powered enterprise UI system that allows users to interact with business data and services using natural language.

Instead of building a separate screen for every request, ZenUI interprets the user's intent, gathers the required information, plans the appropriate interface, and dynamically renders the result in the frontend.

---

## Overview

Traditional enterprise applications usually require users to navigate through multiple screens, forms, tables, filters, and reports.

ZenUI explores a different interaction model:

```text
User
  |
  | Natural Language
  v
Intent Analysis
  |
  v
Conversation Context
  |
  v
Resource / Tool Planning
  |
  v
External or Internal Data
  |
  v
Result Normalization
  |
  v
UI Planning
  |
  v
UI Modification
  |
  v
OpenUI Generation
  |
  v
React Renderer
  |
  v
Dynamic Enterprise UI
```

The goal is to make enterprise applications more conversational while keeping the generated interface structured, predictable, and reusable.

## Key Features

### Natural Language Interaction

Users can describe what they need using normal language instead of navigating through predefined screens.

Examples:

- Show purchase orders
- Show purchase orders with high value
- Show sales as a chart
- Remove the chart
- Filter the table by customer

### Semantic Intent Analysis

ZenUI analyzes the user's request and determines what the user is trying to accomplish.

The system can distinguish between requests such as:

- retrieving business data
- filtering data
- creating visualizations
- modifying an existing interface
- removing UI elements
- referring to previous conversational results
- requesting external information

### Conversational Context

ZenUI maintains conversation context so that follow-up requests can refer to previously generated results.

For example:

```
User:
Show purchase orders

A:
[Purchase Order Table]

User:
Show only high-value orders

A:
[Filtered Purchase Order Table]
```

The second request can be interpreted using the context of the first request.

### Context Isolation

Conversation context is handled carefully so that unrelated conversations do not accidentally influence one another.

This is important for enterprise applications where information from one session should not leak into another session.

### Resource and Tool Planning

ZenUI can determine whether a request should use:

- internal business resources
- database-backed resources
- APIs
- external information/search tools

The system separates the user's intent from the actual mechanism used to retrieve the information.

### Result Normalization

Results from different resources and tools are converted into a normalized representation before being passed to the UI planning layer.

This allows the UI layer to remain generic instead of depending directly on individual tools or APIs.

### Dynamic UI Planning

ZenUI converts normalized information into a UI representation.

Depending on the request, the generated interface can contain:

- headings
- text
- tables
- charts
- filters
- other structured UI elements

### UI Modification

Users can modify previously generated interfaces using natural language.

Examples:

- Remove the chart
- Add a column for customer
- Filter by status
- Show this as a chart

The system interprets these requests as modifications to the existing UI rather than generating an unrelated screen.

### OpenUI Generation

ZenUI uses a structured OpenUI representation for dynamic interface generation.

The backend produces a UI specification and the frontend renderer interprets that specification.

This keeps the frontend generic and avoids hard-coding individual enterprise screens.

### React Renderer

The frontend contains a reusable React renderer responsible for rendering the generated UI.

The renderer can interpret the OpenUI structure and display the appropriate components dynamically.

## Architecture

ZenUI is organized around a separation between intelligence, data access, UI planning, and rendering.

```text
                    +----------------+
                    |     User       |
                    +-------+--------+
                            |
                            v
                    +---------------+
                    |   API Layer   |
                    +-------+-------+
                            |
                            v
                    +---------------+
                    | Intent Engine |
                    +-------+-------+
                            |
                            v
                    +---------------+
                    |   Context     |
                    +-------+-------+
                            |
                            v
                 +----------+----------+
                 | Resource / Tool     |
                 | Planning            |
                 +----------+----------+
                            |
              +-------------+-------------+
              |                           |
              v                           v
      +---------------+          +---------------+
      | Internal Data |          | External Tool |
      +-------+-------+          +-------+-------+
              |                          |
              +------------+-------------+
                           |
                           v
                 +-------------------+
                 | Result Normalizer |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 |    UI Planner     |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 |  UI Modification  |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 |  OpenUI Generator |
                 +---------+---------+
                           |
                           v
                 +-------------------+
                 |   React Renderer  |
                 +---------+---------+
                           |
                           v
                    +-------------+
                    | Dynamic UI  |
                    +-------------+
```

## Project Structure

```
ZenUI/
|
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── conversation/
│   │   ├── core/
│   │   ├── intelligence/
│   │   ├── llm/
│   │   ├── openui/
│   │   ├── resources/
│   │   ├── tools/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── generated/
│   │   ├── App.tsx
│   │   ├── Renderer.tsx
│   │   ├── main.tsx
│   │   ├── App.css
│   │   └── index.css
│   │
│   ├── package.json
│   └── vite.config.*
│
├── COMPLETION_SUMMARY.md
├── DEMO_COMMANDS.md
├── DEMO_WALKTHROUGH.md
├── README.md
└── .gitignore
```

### Backend

The backend contains the intelligence and orchestration layers of ZenUI.

Major areas include:

```
backend/app/
|
├── api/
├── conversation/
├── core/
├── intelligence/
├── llm/
├── openui/
├── resources/
└── tools/
```

The backend is responsible for:

- receiving user requests
- understanding intent
- maintaining conversational context
- selecting resources or tools
- retrieving information
- normalizing results
- planning the UI
- applying UI modifications
- generating the OpenUI representation

### Frontend

The frontend is implemented using React and TypeScript.

The main rendering flow is:

```text
Backend UI Specification
          |
          v
      App.tsx
          |
          v
     Renderer.tsx
          |
          v
    Dynamic Components
```

The frontend is intentionally kept generic.

Business-specific screens are not hard-coded into the renderer. Instead, the renderer consumes the UI representation generated by the backend.

## Example Interactions

### Purchase Orders

User:

```
Show purchase orders
```

ZenUI can generate a purchase-order table dynamically.

### Chart Generation

User:

```
Show sales as a chart
```

ZenUI can generate a visualization based on the available data.

### Chart Modification

User:

```
Remove the chart
```

ZenUI interprets the request as a modification to the existing interface.

### Column Modification

User:

```
Add customer column
```

The generated table can be modified according to the conversational request.

### Filtering

User:

```
Show only high-value orders
```

The system can interpret the request as a filtering operation over the existing data/UI context.

### Conversational References

User:

```
Show purchase orders
```

Then:

```
Show only the expensive ones
```

The second request can use the previous conversational state to understand what "the expensive ones" refers to.

### Enterprise Data

The demo includes business-oriented resources such as:

- Purchase Orders
- Customers
- Employees
- Sales

These resources provide structured data that can be used by the intelligence and UI-generation layers.

### External Information

ZenUI also demonstrates interaction with external information sources.

The external information flow is:

```text
User Request
     |
     v
Intent Analysis
     |
     v
External Tool
     |
     v
Result Normalization
     |
     v
UI Planning
     |
     v
Generated UI
```

This allows the same UI generation pipeline to work with information that does not originate from the internal enterprise data resources.

## Technology Stack

### Backend

- Python
- FastAPI
- Pydantic
- LLM-based intelligence
- REST APIs
- Structured UI generation

### Frontend

- React
- TypeScript
- Vite
- OpenUI rendering

### Data and Tools

- Structured enterprise resources
- REST APIs
- External information/search tools

## Local Development

### Prerequisites

Install:

- Python
- Node.js
- npm
- Git

### Backend Setup

From the project root:

```
cd backend
```

Create and activate the Python virtual environment if required:

```
python -m venv .venv
```

Windows PowerShell:

```
.venv\Scripts\Activate.ps1
```

Install dependencies:

```
pip install -r requirements.txt
```

Create a local environment file:

```
.env
```

Add the required environment variables for the project.

Do not commit `.env` to GitHub.

### Run the Backend

From the backend directory:

```
uvicorn app.main:app --reload
```

The backend will run locally using the FastAPI application.

### Frontend Setup

Open another terminal and move to the frontend directory:

```
cd frontend
```

Install dependencies:

```
npm install
```

Start the development server:

```
npm run dev
```

The Vite development server will provide the local frontend URL.

### Environment Variables

Secrets and environment-specific configuration should be stored in `.env` files.

Example:

```
VARIABLE_NAME=your_value
```

Never commit real API keys, credentials, tokens, or other secrets to the repository.

The repository `.gitignore` is configured to exclude environment files and generated dependency directories.

## Testing

The project contains backend tests covering important parts of the ZenUI pipeline.

The completed verification scope includes scenarios such as:

- greetings and capabilities
- purchase orders
- charts
- chart replacement
- chart removal
- column modifications
- filtering
- conversational references
- context isolation
- external information/search
- API rendering

The goal of these tests is to verify the complete path from user request to generated UI.

## Demo Flow

A typical ZenUI demonstration can follow this sequence:

### 1. Basic Conversation

```
Hello
```

Verify that ZenUI responds correctly.

### 2. Retrieve Enterprise Data

```
Show purchase orders
```

Verify that a dynamic table is generated.

### 3. Modify the UI

```
Add customer column
```

Verify that the table changes.

### 4. Filter the Data

```
Show only high-value orders
```

Verify that the generated result reflects the requested filter.

### 5. Generate a Chart

```
Show this as a chart
```

Verify that the UI changes from the table representation to a visualization.

### 6. Remove the Chart

```
Remove the chart
```

Verify that the UI modification is applied.

### 7. External Information

Ask for information that requires an external tool/search.

Verify that the external result passes through normalization and UI planning before being rendered.

## Design Philosophy

ZenUI follows several core design principles.

### Natural Language First

Users should be able to express their requirements naturally.

### Generic UI Rendering

The frontend should render structured UI specifications rather than contain large amounts of domain-specific UI logic.

### Separation of Concerns

Intent understanding, context management, resource access, normalization, UI planning, and rendering are separate responsibilities.

### Conversational UI Modification

Users should be able to refine an interface through follow-up requests instead of starting over.

### Context Safety

Conversation context should remain isolated and should only influence the appropriate session/request.

### Extensibility

New resources, tools, UI components, and enterprise domains should be possible without redesigning the complete architecture.

## Deployment

The intended demo deployment architecture is:

```text
             Internet
                |
        +-------+-------+
        |               |
        v               v
   Vercel            Render
   Frontend          Backend
        |               |
        +-------+-------+
                |
                v
        ZenUI Application
```

### Frontend

The React/Vite frontend can be deployed using a frontend hosting platform such as Vercel.

### Backend

The FastAPI backend can be deployed using a backend hosting platform such as Render.

The deployed frontend must be configured to communicate with the deployed backend API.

Environment variables should be configured separately in the deployment platforms.

## Security

The following files and directories should never be committed:

```
.env
.venv/
node_modules/
dist/
__pycache__/
```

The root `.gitignore` contains rules for these development and environment-specific files.

Before pushing changes, verify:

```
git status
```

and make sure secrets are not staged.

## Documentation

Additional project documentation is available in:

- COMPLETION_SUMMARY.md
- DEMO_COMMANDS.md
- DEMO_WALKTHROUGH.md

These documents provide additional information about the implementation, testing, and demonstration flow.

## Project Status

ZenUI has reached the completed core demo milestone.

The core implementation includes:

- backend intent analysis
- conversation context
- context isolation
- resource and tool planning
- result normalization
- dynamic UI planning
- UI modification
- OpenUI generation
- React OpenUI rendering
- API communication
- regression verification of the major demo scenarios

The project is currently focused on demonstrating the complete conversational-to-dynamic-UI pipeline.

## Future Extensions

Potential future extensions include:

- additional enterprise resources
- more UI components
- richer data visualizations
- additional external tools
- authentication and authorization
- production-grade observability
- more advanced multi-turn workflows
- additional enterprise integrations

## Author

Muthuraja

## License

This project is currently intended as a demonstration and learning project.

License details can be added when the project is prepared for broader distribution.
