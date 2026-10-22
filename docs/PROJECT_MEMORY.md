# JARVIS AI — Project Memory

## Product vision
Build a voice-first personal AI operating system with a supervisor
and five specialist agents. Agents perform real work through controlled
tools and independent execution environments.

## Operating principles
- Hand-written, reviewed source code; do not rely on AI coding agents
  to generate the application.
- Backend and execution engine before the website.
- Production-minded architecture, verified through tests.
- No fake agent activity or fabricated execution events.
- Explicit permissions, isolated workspaces, protected credentials,
  resource limits and cost controls.
- Design for scale; prove one execution path before scaling.

## Six agents
1. Boss / Supervisor
2. Research
3. Developer
4. Operations
5. Communications
6. QA & Security

## Intended technology
- Python 3.11
- LangGraph orchestration
- FastAPI backend
- PostgreSQL and durable checkpoints when appropriate
- Docker for isolated execution; dedicated cloud VMs when justified
- Modular model-provider adapters
- ElevenLabs voice services
- Omni Voice integration pending confirmation of the exact provider
- n8n and other approved integrations
- React and React Flow for the future website and live execution graph

## Constraints
- Windows development machine
- Initial budget target: under INR 2,000
- Potential later budget: up to INR 10,000
- No powerful local GPU assumed
- Website is a later phase, not the first deliverable

## Current environment
- Python 3.11.7 from C:\anaconda3new
- Git 2.53.0.windows.2
- LangGraph 1.2.14 installed globally
- langchain-google-genai 4.4.1 installed globally
- langchain-core 1.6.9 installed globally
- Docker command was not found during initial inspection
- Project path: C:\Users\alexp\OneDrive\Desktop\AI agent

## Current milestone
Milestone 1: establish an isolated Python environment and a versioned,
documented repository. Dependency imports and tests still need verification.

## Rules for updating this file
Record durable architecture decisions, completed milestones, test evidence,
known issues, costs and the exact next action. Never claim a milestone
passed without evidence.
