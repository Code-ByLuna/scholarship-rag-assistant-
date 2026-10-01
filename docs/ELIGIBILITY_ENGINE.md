# Deterministic eligibility engine

The application uses core/eligibility.py. The supplied root engine is retained as
a legacy reference. Rules are normalized by field/key and a small audited text
grammar, never by scholarship ID. equals, not_equals, comparisons, required,
membership, conditional rules, OR booleans, and verification are supported.

Every unrecognized clause survives as REQUIRES_VERIFICATION with its source path.
Renewal rules are NOT_APPLICABLE for fresh application checks. A known failure
wins over unknowns. No failure plus missing/verification means NEEDS_VERIFICATION.
Only completely resolved hard rules can produce ELIGIBLE. Awards are still subject
to official selection; selection constraints are exposed as verification.

Unknown lateral entry and a partially unknown GATE/CEED disjunction are missing,
not false. Student age cannot prove age at admission. A supplied generic institution
approval does not prove a scheme-specific notified institution. Family limits with
twin exceptions need verification. Income conflicts cannot produce a pass or fail.

Additional optional profile fields are asked for only from candidate rule traces.
Natural language never updates profile facts. Schema rejects extra fields/types.
