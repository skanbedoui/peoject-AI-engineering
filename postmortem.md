# Postmortem

The first dataset was not a benchmark: `category_descriptions.csv` contains category definitions but no contract text or labels. We avoided silently presenting definitions as evidence and built a synthetic smoke-test set instead. This makes the pipeline reproducible, but it does not measure real-world legal extraction quality.

The current run also has only the self-hosted model because API credentials are not available. That means there is no model choice across three systems yet. Before submission, add independently sourced clauses, have two people verify every label, run the exact same items and prompt on the top and cheap API models, record their exact model names and dates, and replace the placeholder hardware assumptions with measured hardware and electricity costs.
