# Line-level slop classifier

The slop score counts patterns, and a word list cannot read: "Failed rows get no made-up reward." has no flagged word in it and is still slop. So every pass also runs a classifier that reads each line the way the doc's readers would and judges it, trained on the author's own labels.

## The data

`data/slop_labels.jsonl` holds the author's labels, one per line: the sentence, `slop` or `human`, why, and the author's rewrite when there is one. Every sentence the author flags during a run goes in as `slop` with their rewrite, and their rewrite goes in as `human`; so does any sentence they wrote themselves. Add them with `scripts/slop_lines.py add "<sentence>" slop --why "..." --rewrite "..."`. These labels are the ground truth: the classifier learns from them as examples, and it is scored against them.

## A run

1. `python3 scripts/slop_lines.py split vN.md > lines-vN.json` numbers the body's sentences and list items.
2. A fresh agent classifies them with the prompt below and returns `pred-vN.json`.
3. `python3 scripts/slop_lines.py eval pred-vN.json` scores it on any labelled lines that appear in the doc. Measure the classifier itself by running it on a held-out half of the labels, with the other half as its examples, and report precision and recall.
4. Lines it calls slop go to step 8 as findings, with its rewrites. The share of lines called slop is logged as a failing read-back check (`sentence read`) until it reaches zero.
5. `python3 scripts/slop_lines.py uncertain pred-vN.json -n 20` lists the lines it is least sure of. Show them to the author as a numbered list and ask which are slop; add each answer with `add`. This is how the classifier gets better: the author labels the lines where it is weakest.

When the labels pass a few hundred, train a small model on them (a fine-tuned classifier through the `fine_tune_api` skill, or a logistic regression on sentence embeddings) and compare it with the prompted classifier on the held-out half before switching.

## The prompt

> You are classifying each line of a document as written by a person (`human`) or reading as AI-generated (`slop`), the way the doc's readers would see it. The readers and purpose are in this humanize context: <context block>. First read every labelled example in `data/slop_labels.jsonl`: the author marked these, and their rewrites show how they write. Slop is not a word list. It is a shape: a sentence that hops from part to part of a mechanism; a bare state sentence with no one doing anything and no purpose ("Failed rows get no made-up reward."); a count of parts instead of the thing proposed; a label or code the reader was never given; an idiom or compressing verb standing in for what happens; a clever recast or aphorism; a tail restating the opposite; an appositive or aside welded into a sentence; a conclusion nothing set up; internal jargon from a system the readers do not own; a detail that does not serve its paragraph. A human line says one thing plainly, in the order things happen, with a subject that does something and a reason when one is needed. Then read <lines file> and judge each line in the context of its neighbours. Return only JSON: `{"lines": [{"i": 1, "text": "...", "p_slop": 0.0, "label": "slop|human", "why": "<= 12 words", "rewrite": "plain rewrite, only when slop"}]}`. `p_slop` is your probability that the author would call the line slop; label `slop` at 0.5 or above. Keep every number, link and identifier in a rewrite.
