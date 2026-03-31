# Review System

The review system is deterministic-first.

## Pipeline

1. build context
2. classify PR
3. run deterministic analyzers
4. optionally run semantic review
5. aggregate final verdict

## Verdicts

- `APPROVE`: no blocking or escalation findings
- `WARN`: advisory issues only
- `BLOCK`: deterministic blocking policy violated
- `ESCALATE`: change requires non-autonomous review
