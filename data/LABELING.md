# Labeling policy

The current 50 examples are synthetic development/smoke-test data, not real contract excerpts. They are insufficient to claim real-world legal performance. Before final submission, replace or augment them with independently sourced real clauses, document provenance, and have two people verify every final label.

We select 25 clause-level categories with clear categorical names from category_descriptions.csv. Definitions remain in that CSV; src/prompt.py holds the explicit selection. Metadata/extraction fields (Document Name, Parties, dates, Governing Law, Warranty Duration, renewal durations and notice periods) are excluded. Other broad or overlapping categories are omitted to keep this first experiment focused.

Each item has exactly one intended category and each tested category has at least two examples. Clauses should express a single operative provision. For a specialized license provision, choose its specific category over License Grant; use License Grant for a plain permission without specialized attributes. Use Change of Control for ownership changes and Anti-Assignment for transfer of the agreement. Minimum Commitment is a purchase floor; Volume Restriction is an excess-usage threshold. Do not combine these obligations in one item.

Reviewers should reject or rewrite genuinely ambiguous items instead of assigning multiple labels. Independently record labels before resolving disagreements, and retain final provenance and review records. The synthetic labels have not undergone that two-person final review.
