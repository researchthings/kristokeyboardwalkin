# Mutations and audit-time cracking

Real keyboard-walk passwords are rarely bare walks. Users capitalize the
first letter, append a digit or a year, swap in leetspeak, duplicate, or
reverse. `keywalk_audit.hashing.mutations` expresses those mutation
families two ways, and `keywalk_audit.audit.crack` uses them to drive
hashcat against hashes that miss the rainbow table.

## Rule set

`DEFAULT_RULES` is a tuple of hashcat rule strings spanning:

- passthrough `:`; case `l u c t`; structural `r` (reverse), `d`
  (duplicate);
- digit appends `$0`-`$9`; symbol appends `$! $@ $# $$ $%`;
- year appends (`$2$0$2$4`, … and `$1$2$3$4`);
- capitalize-then-append combinations (`c$1`, `c$@`, …);
- leet substitutions (`se3`, `sa@`, `so0`, `si1`, `ss$`).

`write_rule_file(DEFAULT_RULES, path)` writes one rule per line for use
with `hashcat -r`.

## Python-side expansion

`python_mutations(plaintext)` applies a curated subset in pure Python and
returns a de-duplicated, order-preserving list (the original first). This
expands a seed wordlist without invoking hashcat:

```
keywalk-audit mutations --sample 1qaz2wsx     # show the expansions
keywalk-audit mutations --rules-out walk.rule # write the hashcat rule file
keywalk-audit mutations --masks               # walk-shaped hashcat masks
```

`walk_masks()` returns hashcat mask strings for common walk-with-suffix
shapes (lowercase run, capitalized run, runs followed by digits or a
symbol).

## Audit-time cracking

The rainbow answers exact lookups instantly for the fast algorithms it
materializes. Everything else -- a slow algorithm, or a walk derivative the
build did not enumerate -- goes to hashcat. `crack_hashes` assembles the
attack:

1. read the rainbow candidate plaintexts as a seed wordlist
   (`candidate_plaintexts`, ordered by score);
2. optionally expand them with `python_mutations`;
3. write a hashcat rule file from `DEFAULT_RULES`;
4. write the unmatched target hashes and invoke `hashcat -a 0 -r walk.rule`.

```
keywalk-audit crack users.pwdump --db rainbow.duckdb --algorithm ntlm \
    --mutate --min-score 0.6 --work-dir ./crack
```

The hashcat invocation is injected (`run_hashcat`) so the orchestration is
unit-tested without the binary, mirroring the builder. When hashcat is not
installed the `CrackReport` is returned with `hashcat_invoked=False` and an
explanatory error rather than raising, so the command degrades gracefully.
All subprocess calls use explicit argument lists and never a shell.
