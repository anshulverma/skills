# Line-level slop classifier

The slop score counts patterns, and a word list cannot read: "Failed rows get no made-up reward." has no flagged word in it and is still slop. So every pass also runs a classifier that reads each line the way the doc's readers would and judges it, trained on the author's own labels.

## The data

`data/slop_labels.jsonl` holds the author's labels, one per line: the sentence, `slop` or `human`, why, and the author's rewrite when there is one. Every sentence the author flags during a run goes in as `slop` with their rewrite, and their rewrite goes in as `human`; so does any sentence they wrote themselves. Add them with `scripts/slop_lines.py add "<sentence>" slop --why "..." --rewrite "..." --source "<doc>"`, the moment the author gives them, in every session: a flag that is fixed and not recorded is training data lost. These labels are the ground truth: the classifier learns from them as examples, and it is scored against them.

Each label's split comes from a hash of its text: one in three goes to the eval split, the rest are examples. A label never moves between splits, so the eval split only grows and never leaks into the examples. `slop_lines.py freeze vN` pins the eval split as it stands into `data/eval_sets/vN.txt`; a frozen set never changes, so it is the fixed dataset every later classifier version is compared on. Freeze a new one when the eval split has grown by about half.

## Measuring it

`data/classifier_metrics.jsonl` is the classifier's scoreboard: one row per measurement, with the date, the eval set, precision, recall, F1, accuracy, AUC (from `p_slop`), the number of examples it learned from, and a hash of this file, so each change to the prompt or the labels shows up as a row. `slop_lines.py metrics` prints it. Measure on every frozen set:

1. `python3 scripts/slop_lines.py heldout <dir> --set vN` writes the examples (train split only) and the eval lines.
2. A fresh agent runs the prompt below with `<dir>/examples.jsonl` in place of the labels file, judging each line on its own, and writes `<dir>/pred.json`.
3. `python3 scripts/slop_lines.py eval <dir>/pred.json --set vN --log "<what changed>"` scores it and appends the row.

The classifier is an LLM, so the same prompt scores differently from run to run: on `v1`, two runs of one prompt differed by more than the change being tested. Run step 2 three times and log each run with the same note; `metrics` prints the mean and range per prompt version. Measure after every change to the prompt, after every 20 or so new labels, and before switching to a trained model. Report the new mean next to the previous one. A change whose mean AUC falls below the previous version's range is reverted.

## Open-source options

AI-text detectors (Binoculars, Fast-DetectGPT, RoBERTa and DeBERTa detectors on Hugging Face) measure who wrote a text, not whether the author would call it slop, and they are weak on single sentences: on HC3 sentences, fine-tuned RoBERTa scores about 59 F1 and DetectGPT 63, against 87 to 97 on whole documents ([MPU paper](https://arxiv.org/abs/2305.18149)). At most, log one as a feature and keep it only if its AUC on a frozen set beats chance. More useful:

- word and n-gram lists of what LLMs overuse ([slop-forensics](https://github.com/sam-paech/slop-forensics), [EQ-Bench slop score](https://eqbench.com/slop-score.html)) and [Vale](https://vale.sh) rules: cheap line-level features for idioms and stock phrases, though they miss hops and undefined labels;
- the slop taxonomy in [Measuring AI Slop in Text](https://arxiv.org/abs/2509.19163) as a rubric for the prompt;
- one yes/no LLM check per shape, combined by logistic regression trained on the labels, which gives calibrated scores per shape;
- at a few hundred labels, a fine-tuned ModernBERT or DeBERTa-v3 that sees the sentence before and after, since a hop spans sentences.

## A run

1. `python3 scripts/slop_lines.py split vN.md > lines-vN.json` numbers the body's sentences and list items.
2. A fresh agent classifies them with the prompt below and returns `pred-vN.json`.
3. `python3 scripts/slop_lines.py eval pred-vN.json` scores it on any labelled lines that appear in the doc. That is a spot check, not the classifier's score: the scoreboard above is.
4. Lines it calls slop go to step 8 as findings, with its rewrites. The share of lines called slop is logged as a failing read-back check (`sentence read`) until it reaches zero.
5. `python3 scripts/slop_lines.py uncertain pred-vN.json -n 20` lists the lines it is least sure of. Show them to the author as a numbered list and ask which are slop; add each answer with `add`. This is how the classifier gets better: the author labels the lines where it is weakest.

When the labels pass a few hundred, train a small model on them (a fine-tuned classifier through the `fine_tune_api` skill, or a logistic regression on sentence embeddings) and compare it with the prompted classifier on the held-out half before switching.

## The prompt

> You are classifying each line of a document as written by a person (`human`) or reading as AI-generated (`slop`), the way the doc's readers would see it. The readers and purpose are in this humanize context: <context block>. First read every labelled example in `data/slop_labels.jsonl`: the author marked these, and their rewrites show how they write. Slop is not a word list. It is a shape: a sentence that hops from part to part of a mechanism; a bare state sentence with no one doing anything and no purpose ("Failed rows get no made-up reward."); a count of parts instead of the thing proposed; a label or code the reader was never given; an idiom or compressing verb standing in for what happens; a clever recast or aphorism; a tail restating the opposite; an appositive or aside welded into a sentence; a conclusion nothing set up; internal jargon from a system the readers do not own; a detail that does not serve its paragraph; a coined name for a value or event defined only so later rules can use it ("A trip is the first cut ..."); a pronoun whose referent is not the previous subject; a connective that means something else ("while" for "unless"). Not slop: a plain sentence stating one decision, fact or step with a clear subject, even a terse one ("Rows whose scoring failed are left out of training."; "Only transient connection errors get one jittered retry."). Call a line slop only when you can name its shape; terseness alone is not one. A human line says one thing plainly, in the order things happen, with a subject that does something and a reason when one is needed. Then read <lines file> and judge each line in the context of its neighbours. Return only JSON: `{"lines": [{"i": 1, "text": "...", "p_slop": 0.0, "label": "slop|human", "why": "<= 12 words", "rewrite": "plain rewrite, only when slop"}]}`. `p_slop` is your probability that the author would call the line slop; label `slop` at 0.5 or above. Keep every number, link and identifier in a rewrite.
