# W3 Lab: Preparation (before the lab)

Do this **at home, at least 48 hours before the lab**. Setup that fails in the
room costs everyone time, and there is no time to debug it during the lab.

You may work **alone or in a pair**. In a pair, **one** of you creates the
repository and the other joins it as a collaborator.

You need what you installed for W1: `git`, `uv` and VSCode.

---

## 1. Create your private repository from the template

*In a pair: only one partner does this step.*

1. Open <https://github.com/melhadad/llm-se-2027-w3-lab>.
2. Click **Use this template** → **Create a new repository**.
3. Owner: your GitHub user. Name: e.g. `llm-se-2027-w3-lab-<your-github-user>`.
4. Choose **Private**.
5. Click **Create repository**.

## 2. Add collaborators

In your new repository: **Settings** → **Collaborators** → **Add people**. Add:

- the course Teaching Assistant: **`tpinhas`**
- your partner's GitHub user, if you work in a pair

*Partner:* GitHub sends you an invitation by email (also shown at
<https://github.com/notifications>). **Accept it**; it expires after 7 days.

## 3. Clone the repository and open it in VSCode

*In a pair: each partner does this, on their own machine.*

In a terminal, in the folder where you keep course work:

```
git clone https://github.com/<owner>/<repo-name>.git
```

Then in VSCode: **File** → **Open Folder…** → choose the cloned folder.

**Note:** If any of the **VSCode extensions** this repository recommends
(Python, Pylance and Jupyter) are missing, VSCode asks whether to install
them. Click **Install**. If you see no prompt, they are already installed.
If you closed the prompt by mistake: open the Extensions view, type `@recommended`, and
install the ones listed under *Workspace Recommendations*.

## 4. Add your model key

*Each partner, with their own key.*

1. Copy `.env.example` to a new file named `.env` (in the repo's top folder).
2. In `.env`, fill in **one** provider key and set `LLM_MODEL` to a model of
   that provider. The comments in the file show examples.
3. Save. `.env` is ignored by git: it must **never** be committed. **Never** paste
   your key anywhere else (not in the notebook, not in Moodle, not in chat).

## 5. Run the environment check

Open a terminal in VSCode (**Terminal** → **New Terminal**) and run:

```
uv run python tools/verify_env.py
```

The first run takes a minute or two: `uv` installs Python 3.13 and the lab's
packages into `.venv/`. The check also installs a git hook that blocks
commits containing a key.

## 6. Check the result

Open `outputs/setup-check-<your git user.name>.txt`. It is the same report the
command printed. Every line should be `[  ok  ]` and it should end with
**All checks passed.**

If something fails, the line says what to fix. Fix it and run step 5 again.

If you cannot fix it, **continue anyway** with steps 7 and 8 before the
deadline, and post the report in the course forum: a failed report on time
tells us what broke and we can help. A missing one does not.

## 7. Commit the setup-check file and push

*Each partner commits their own file.*

```
git pull
git add outputs/setup-check-<your git user.name>.txt
git commit -m "setup check"
git push
```

Open your repository on GitHub and make sure you see the file in `outputs/`.
In a pair, both files should be there.

## 8. Submit in Moodle

Submit a file containing the **URL of your GitHub repository**
(e.g. `https://github.com/<owner>/<repo-name>`).

**In a pair, both partners submit**, with the same URL.

---

## Optional: try the notebook

Open `notebooks/w3_lab.ipynb`. Click **Select Kernel** (top right) and pick
the `.venv` interpreter of this folder. Run the first two code cells: the
first should print `ready`. Do not go further; the rest is for the lab.
