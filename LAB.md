# W3 Lab: Issue triage with DSPy

Two hours. Alone or in the same pair as the preparation.

## Before you start

- Your preparation is done: `outputs/setup-check-<your git user.name>.txt`
  says **All checks passed**, and it is pushed.
- In a pair, run `git pull` first, so you both have the latest version.

## The lab

Open `notebooks/w3_lab.ipynb`, select the `.venv` kernel (top right), and
work through it from the top. The notebook explains each part.

| Time | Part |
|---|---|
| 0:00 | 1. Connect to your LLM model |
| 0:05 | 2. Structured output |
| 0:25 | 3. One-shot |
| 0:35 | 4. Tools and context |
| 0:55 | 5. Two step workflow |
| 1:15 | 6. ReAct |
| 1:40 | 7. Prompt optimization |
| 1:52 | 8. Wrap-up |

Keep `improvement-log.md` and `docs/decisions.md` open, as in W1.

## Submit

At the end of the notebook (Part 8), commit and push:

```
git add notebooks/w3_lab.ipynb outputs/results/w3_results.json docs/decisions.md improvement-log.md
git commit -m "W3 lab"
git push
```

Make sure you see your changes on GitHub.
Then submit your repo URL in Moodle. **In a pair, both partners submit.**
