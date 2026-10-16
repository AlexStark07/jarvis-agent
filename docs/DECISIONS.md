# JARVIS AI — Architecture Decisions

## DEC-001: Backend before website
Status: Accepted
Build and test the execution engine before the web interface.
The backend must expose stable APIs and real execution events.

## DEC-002: LangGraph orchestration
Status: Selected for initial implementation
Keep orchestration separate from tools, model providers and execution workers.

## DEC-003: Independent worker environments
Status: Accepted
Start with isolated environments; evaluate dedicated cloud VMs when justified.
A container is not the same as a separate physical computer or VM.

## DEC-004: No AI-generated application implementation
Status: User constraint
Write and review the source code manually. Use Antigravity as the IDE
and terminal, not as an autonomous code generator.

## DEC-005: Voice provider integration
Status: Pending
ElevenLabs is intended. The exact Omni Voice provider/API must be confirmed
before choosing an implementation.
