# The rule builder generates code in one direction only

The rule builder writes a normal strategy version from its rules. It never
parses code back into rules. ATrade stores the rules as JSON in a nullable
column of `strategy_version`, only on the versions that the rule builder
saved, and the version source gets a third value, "rule builder" (next to
user and AI assistant, ADR 0004). When the user or the AI assistant changes
the code later, the rule builder opens the rules of the latest version that
it saved and warns that the code changed. Saving the rules again replaces
those code changes, and ATrade shows the diff first. Decided in
[#138](https://github.com/Mano-Liaoyan/ATrade/issues/138).

## Considered options

- Two-way editing (code back to rules). Rejected: a parser can read only the
  exact code that the builder writes, so most hand edits break it. None of
  the products in the UI research (#135) does it.
- Rules in a structured comment at the top of the code. Rejected: a code
  edit can change the code and leave the comment, so ATrade would need a
  hash check, and the block is about 20 lines long.
- Builder versions read-only until "convert to code". Rejected: one more
  step for each hand edit.

## Consequences

- A strategy version with a code change made after the builder has no rules.
  The builder cannot open it as it is.
- Indicator parameters and number thresholds are config fields with default
  values, so a parameter sweep can change them without the rule builder.
