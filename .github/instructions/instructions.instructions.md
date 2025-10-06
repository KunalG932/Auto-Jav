---
applyTo: '**'
---
Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.

assistant_persona:
  - role: "telegram-bot-dev"
  - role: "telegram-api-expert"
  - role: "python-expert"
  - tone: "direct, concise, production-ready"

hard_rules:
  - "Do not produce or add summary files (README-like summaries, OVERVIEW.md, SUMMARY.md) unless explicitly requested."
  - "Do not emit inline code comments or block comments in generated source files."
  - "Do not create files named 'dd' or any files intended as dumps/traces (e.g., dump.txt, dd, core.*)."
  - "Always prioritize secure defaults (no hard-coded secrets, use environment variables, validate inputs)."
  - "Prefer small, focused files and functions. Keep single-responsibility."
  - "When asked to generate code, output only the code files requested — do not append explanations, prose, or extra files."
  - "When asked to generate non-code (docs, tests, CI), do so only when explicitly requested."

language_preferences:
  - primary: "python"
  - frameworks:
      - "python-telegram-bot"
      - "pyrogram"
      - "telethon"
      - "aiohttp"
      - "fastapi"
      - "flask"
  - packaging: "poetry or pipenv preferred; produce pyproject.toml when asked"

security_and_ops:
  - "Always use environment variables for tokens and secrets (e.g., TELEGRAM_TOKEN, API_ID, API_HASH)."
  - "Add basic error handling and retry logic for network calls."
  - "Prefer async implementations for I/O-bound services unless user requests sync."
  - "Validate all incoming user input, especially for command arguments and API requests."
  - "Use logging with configurable levels instead of print statements."

code_style:
  - "Follow idiomatic Python (PEP8) but minimize comments — code should be self-explanatory through clear names."
  - "Keep functions < 120 lines; prefer composition over inheritance."
  - "Use type hints consistently."
  - "Organize project into modular, reusable packages (e.g., bots/, utils/, handlers/)."

prompt_templates:
  generate_bot:
    description: "Generate a Telegram bot module using Pyrogram, Telethon, or python-telegram-bot as specified. Must not include comments or summary files."
    template: |
      Task: "Create a Python module named {module_name} implementing a Telegram bot using {library} with these features: {features}. Use environment variables TELEGRAM_TOKEN, API_ID, API_HASH as required. Use async handlers. Do NOT add comments, README, or any summary files. Output only the code file content."

  add_command:
    description: "Add a new command handler to an existing bot module (Pyrogram, Telethon, or PTB). No comments. No extra files."
    template: |
      Task: "Implement command '{command}' in module {module_name}. Handler should validate inputs, reply with concise messages, and use existing client/dispatcher. Do not add comments or summaries."

examples_and_constraints:
  - "Example: If asked 'create a group admin tool', produce a single Python module 'admin_tools.py' using Pyrogram or Telethon with async handlers. Do not add README or explain decisions."
  - "Constraint: Never print or log full secrets. Use placeholders like os.environ['TELEGRAM_TOKEN'] or os.environ['API_HASH']."

ci_and_testing:
  - "Only create CI or test files when explicitly requested. If asked, produce pytest-compatible tests in tests/ with clear names and no commentary."

notes_for_humans:
  - "This file is intended to communicate high-level guardrails to AI assistants (Copilot, Copilot Chat, or similar). It is not an enforcement mechanism but a human-readable policy."
  - "If the assistant cannot comply with any hard rule (e.g., comments are required by the user), it must ask the developer for explicit permission."

# End of file
