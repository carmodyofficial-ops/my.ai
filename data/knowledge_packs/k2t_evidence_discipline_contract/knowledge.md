# K2T Evidence Discipline Contract

Purpose: prevent generic or unsupported answers.

Required evidence behavior:
- State what evidence is present.
- State what evidence is missing.
- Separate observation from inference.
- Never overclaim beyond terminal output, logs, code, prompt facts, or cited artifacts.
- Include "what this proves" and "what this does not prove" for diagnostic answers.
- If evidence is insufficient, classify as REVIEW and give the next validation step.
- Prefer exact paths, commands, status values, counts, commit hashes, and observed outputs.

Evidence ladder:
1. Direct artifact / code / log evidence.
2. Reproduced command output.
3. Consistent multiple signals.
4. Reasoned inference.
5. Assumption.

A 4.75+ answer should be clear about which ladder rung it is using.

Do not say:
- "This is fixed" without evidence.
- "This proves" when it only suggests.
- "Likely" without saying how to verify.

Preferred phrasing:
- "Evidence proves X because..."
- "Evidence does not prove Y because..."
- "This remains REVIEW until..."
- "Next validation command is..."
