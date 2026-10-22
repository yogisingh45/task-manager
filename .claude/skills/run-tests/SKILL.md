---
name: run-tests
description: Run the test suite and report results
disable-model-invocation: true
---

Run the test suite for the Task Manager:
1. Install dependencies: pip install -r requirements.txt
2. Run tests: pytest tests/ -v
3. Report pass/fail count
4. If any tests fail, analyze the failure and suggest a fix
