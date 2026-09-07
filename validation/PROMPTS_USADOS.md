# Prompts Used in the Judge Panel — Real Examples

Gerado a partir de `scripts/panel_prompts.py`. Os quatro prompts abaixo correspondem ao texto exato enviado à API para um item real do corpus. A ideia é mostrar, lado a lado, como cada estratégia é construída.

## Item Used in All Four Examples

- **Repository:** `Autodesk/synthesis`
- **Artifact type:** `code_comment`
- **Expression that triggered collection:** `dirty hack`
- **Lexical category:** `A`
- **Human ground truth:** **true-UBW**
- **Unanimous among the 3 annotators:** yes

Excerpt:

```text
assert(pthread_create(&t, NULL, func, NULL) == 0); /* A dirty hack, but we cannot rely on pthread_join in this primitive test. */ Sleep(2000);
```

---

## 1. Zero-Shot WITHOUT Definition

Aqui, o modelo não recebe nenhuma explicação sobre o que significa UBW. O system prompt apenas define a tarefa, enquanto o user prompt apresenta as três categorias possíveis. O objetivo é avaliar até que ponto o modelo consegue identificar o conceito sem uma definição explícita.

Tamanho: system 149 caracteres, user 669 caracteres.

### System Prompt

```text
You are a research assistant in empirical software engineering. Your task is to classify text excerpts extracted from software repositories.
```

### User Prompt

```text
Classify the candidate below into EXACTLY one of the three categories: "true-UBW", "non-UBW", or "uncertain".

Candidate context:

- Repository: Autodesk/synthesis
- Artifact type: code_comment
- Automatically assigned lexical category: A
- Expression that triggered collection: "dirty hack"
- Excerpt (with context, when applicable):

"""
  assert(pthread_create(&t, NULL, func, NULL) == 0);  /* A dirty hack, but we cannot rely on pthread_join in this     primitive test. */  Sleep(2000);
"""

Respond STRICTLY in JSON, with no text outside the JSON, using the following format:

{"label": "true-UBW" | "non-UBW" | "uncertain", "rationale": "<justification in up to 2 sentences>"}
```

---

## 2. Zero-Shot WITH Definition

Esta é a versão baseline do projeto. O system prompt apresenta uma definição de UBW, enquanto o user prompt descreve o que deve ser considerado em cada categoria. A comparação com a versão anterior permite avaliar o efeito de fornecer uma definição explícita.

Tamanho: system 635 caracteres, user 1374 caracteres.

### System Prompt

```text
You are a research assistant in empirical software engineering, assisting with the pre-screening of "Ugly But It Works" (UBW) candidates: excerpts from issues, pull requests, commit messages, or code comments where a developer explicitly acknowledges accepting a technically suboptimal solution (ugly, a workaround, or a hack) because it works.

You do NOT replace human annotation. Your task is to reduce the number of obvious candidates that require manual review, while flagging ambiguous cases for mandatory review. When in doubt, err on the side of labeling a case as "uncertain".
```

### User Prompt

```text
Classify the candidate below into EXACTLY one of the three categories:

- "true-UBW": the excerpt clearly expresses functional resignation — the author knows or acknowledges that the solution is ugly, a hack, or a workaround, and kept it because it works. The context confirms that the trigger expression is being used in this sense, rather than in a literal string, test data, third-party quotation, or non-technical context.

- "non-UBW": the trigger expression appears, but the context does NOT indicate functional resignation. Examples include a test string, a variable name, a quotation, a negation such as "this is NOT a dirty hack", or a generic use unrelated to technical debt.

- "uncertain": the available context is not sufficient to make a confident decision. The case should be forwarded for human annotation.

Candidate context:

- Repository: Autodesk/synthesis
- Artifact type: code_comment
- Automatically assigned lexical category: A
- Expression that triggered collection: "dirty hack"
- Excerpt (with context, when applicable):

"""
  assert(pthread_create(&t, NULL, func, NULL) == 0);  /* A dirty hack, but we cannot rely on pthread_join in this     primitive test. */  Sleep(2000);
"""

Respond STRICTLY in JSON, with no text outside the JSON, using the following format:

{"label": "true-UBW" | "non-UBW" | "uncertain", "rationale": "<justification in up to 2 sentences>"}
```

---

## 3. Few-Shot with FIXED Examples (k=6)

Nesta estratégia, a definição é acompanhada por seis exemplos previamente rotulados por anotadores humanos: três positivos e três negativos. Os mesmos exemplos são reutilizados para os 200 itens avaliados.

Foi a estratégia que apresentou o melhor resultado.

Tamanho: system 635 caracteres, user 4929 caracteres.

### System Prompt

```text
You are a research assistant in empirical software engineering, assisting with the pre-screening of "Ugly But It Works" (UBW) candidates: excerpts from issues, pull requests, commit messages, or code comments where a developer explicitly acknowledges accepting a technically suboptimal solution (ugly, a workaround, or a hack) because it works.

You do NOT replace human annotation. Your task is to reduce the number of obvious candidates that require manual review, while flagging ambiguous cases for mandatory review. When in doubt, err on the side of labeling a case as "uncertain".
```

### User Prompt

```text
Classify the candidate below into EXACTLY one of the three categories:

- "true-UBW": the excerpt clearly expresses functional resignation — the author knows or acknowledges that the solution is ugly, a hack, or a workaround, and kept it because it works. The context confirms that the trigger expression is being used in this sense, rather than in a literal string, test data, third-party quotation, or non-technical context.

- "non-UBW": the trigger expression appears, but the context does NOT indicate functional resignation. Examples include a test string, a variable name, a quotation, a negation such as "this is NOT a dirty hack", or a generic use unrelated to technical debt.

- "uncertain": the available context is not sufficient to make a confident decision. The case should be forwarded for human annotation.

Human-annotated examples using the same criteria you should apply:

[EXAMPLE 1 — human label: non-UBW]

artifact type: commit_message | expression: "quick and dirty"

"""
develop into master for the 0.6.359 release (#353)* Add WorldPosition & rename ParentTransform -> Transform* doc fix* WorldRotation, WorldScale* Fix scale & doc* Update SceneNode to use Transform2D* Update SceneGraph demo* forgot to add drawable position, rotation, scale* Transform2D strongly typed parent* Revert "SceneNode & Transform2D"* fixed a failing unit test* Fix* Transform updates.* Matrix2D updates.* negated the roation when calculating the local matrix so that it's consistent with sprite batch rotation* updated Entity to inherit from Transform2D* working on the ecs* Graphics branch;
"""

annotator's justification: the previously implemented AI is described as "quick and dirty", not the current implementation

[EXAMPLE 2 — human label: true-UBW]

artifact type: pr_body | expression: "temporary fix"

"""
This will be a temporary fix until #1556 is merged.![Screenshot_2021-02-11 Chatwoot](https://user-images.githubusercontent.com/2246121/107565307-8e218900-6c09-11eb-9a60-7271215caead.png)
"""

annotator's justification: the case refers to a temporary fix, but not because the code is "ugly"; another implementation is simply required for the final version

[EXAMPLE 3 — human label: non-UBW]

artifact type: pr_body | expression: "workaround for now"

"""
Resolves #39201## SummaryWhen an export specifier name (`as`) shadows an import-default name (`name`), then the resulting `name` would be replaced with a namespace member access. However, member accesses of `.default` are never valid, since they can CommonJS-based. Replacement isn't necessary since the name is already preserved.We can't prevent `exportNamed.has` since this is used elsewhere, but this doubling of state to faciliate the re-export seems a bit problematic, since there's no actual "linking up" that's happening.The re-export logic is basically running into tracking issues with the c
"""

annotator's justification: resolved during calibration (converged with Wendell)

[EXAMPLE 4 — human label: non-UBW]

artifact type: commit_message | expression: "dirty hack"

"""
package fix (tmp, dirty hack)
"""

annotator's justification: resolved during calibration (converged with Wendell)

[EXAMPLE 5 — human label: true-UBW]

artifact type: code_comment | expression: "quick and dirty"

"""
return self._input.sourceName # During a parse is sometimes useful to listen in on the rule entry and exit # events as well as token matches. self is for quick and dirty debugging. # def setTrace(self, trace): if not trace:
"""

annotator's justification: resolved during calibration (converged with Wendell)

[EXAMPLE 6 — human label: true-UBW]

artifact type: pr_body | expression: "quick and dirty"

"""
## What type of PR is this? (check all applicable)- [ X] Refactor- [ ] Feature- [ ] Bug Fix- [ ] Optimization- [ ] Documentation Update- [ X] Community Node Submission## Have you discussed this change with the InvokeAI team?- [ ] Yes- [ X] No, because: invisible change ## Have you updated all relevant documentation?- [ ] Yes- [ ] No## DescriptionThere was a problem in 3.0.1 with root resolution. If INVOKEAI_ROOT were set to "." (or any relative path), then the location of root would change if the code did an os.chdir() after config initialization. I fixed this in a quick and dirty way for 3.0.
"""

annotator's justification: resolved during calibration (converged with Wendell)

Candidate context:

- Repository: Autodesk/synthesis
- Artifact type: code_comment
- Automatically assigned lexical category: A
- Expression that triggered collection: "dirty hack"
- Excerpt (with context, when applicable):

"""
  assert(pthread_create(&t, NULL, func, NULL) == 0);  /* A dirty hack, but we cannot rely on pthread_join in this     primitive test. */  Sleep(2000);
"""

Respond STRICTLY in JSON, with no text outside the JSON, using the following format:

{"label": "true-UBW" | "non-UBW" | "uncertain", "rationale": "<justification in up to 2 sentences>"}
```

---

## 4. Few-Shot with RETRIEVED Examples (k=3)

Aqui, a definição é acompanhada pelos três exemplos mais semelhantes ao item que está sendo classificado, usando similaridade TF-IDF. Portanto, os exemplos podem mudar de um item para outro. Também é aplicada uma restrição para garantir a presença de pelo menos um exemplo negativo.

Tamanho: system 635 caracteres, user 2813 caracteres.

### System Prompt

```text
You are a research assistant in empirical software engineering, assisting with the pre-screening of "Ugly But It Works" (UBW) candidates: excerpts from issues, pull requests, commit messages, or code comments where a developer explicitly acknowledges accepting a technically suboptimal solution (ugly, a workaround, or a hack) because it works.

You do NOT replace human annotation. Your task is to reduce the number of obvious candidates that require manual review, while flagging ambiguous cases for mandatory review. When in doubt, err on the side of labeling a case as "uncertain".
```

### User Prompt

```text
Classify the candidate below into EXACTLY one of the three categories:

- "true-UBW": the excerpt clearly expresses functional resignation — the author knows or acknowledges that the solution is ugly, a hack, or a workaround, and kept it because it works. The context confirms that the trigger expression is being used in this sense, rather than in a literal string, test data, third-party quotation, or non-technical context.

- "non-UBW": the trigger expression appears, but the context does NOT indicate functional resignation. Examples include a test string, a variable name, a quotation, a negation such as "this is NOT a dirty hack", or a generic use unrelated to technical debt.

- "uncertain": the available context is not sufficient to make a confident decision. The case should be forwarded for human annotation.

Human-annotated examples using the same criteria you should apply:

[EXAMPLE 1 — human label: true-UBW]

artifact type: code_comment | expression: "dirty hack"

"""
project: Project, leaderboard_type: str | None = None, live: bool = True): previous_entries = list(project.leaderboard_entries.all()) # Bit of a dirty hack but tl;dr "If this was generated recently don't bother !" if not live: for entry in previous_entries: if entry.edited_at > timezone.now() - timedelta(days=1):
"""

[EXAMPLE 2 — human label: true-UBW]

artifact type: commit_message | expression: "dirty hack"

"""
feat: run tests in parallel in `nargo test` (#4484)# Description## Problem\*Resolves \<!-- Link to GitHub Issue -->## Summary\*This is a dirty hack to get tests running in parallel. To do this, we'vegiven up printing the test results in a stream as they're run but weinstead wait for all the tests in a package to be run before we print themout in one go.This takes the noir-protocol-circuits test suite from taking 1:46s to27s.## Additional Context## Documentation\*Check one:- [x] No documentation needed.- [ ] Documentation included in this PR.- [ ] **[Exceptional Case]** Documentation to be submitted
"""

[EXAMPLE 3 — human label: non-UBW]

artifact type: commit_message | expression: "dirty hack"

"""
package fix (tmp, dirty hack)
"""

annotator's justification: resolved during calibration (converged with Wendell)

Candidate context:

- Repository: Autodesk/synthesis
- Artifact type: code_comment
- Automatically assigned lexical category: A
- Expression that triggered collection: "dirty hack"
- Excerpt (with context, when applicable):

"""
  assert(pthread_create(&t, NULL, func, NULL) == 0);  /* A dirty hack, but we cannot rely on pthread_join in this     primitive test. */  Sleep(2000);
"""

Respond STRICTLY in JSON, with no text outside the JSON, using the following format:

{"label": "true-UBW" | "non-UBW" | "uncertain", "rationale": "<justification in up to 2 sentences>"}
```