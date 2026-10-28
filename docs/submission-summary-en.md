# Argus — Warehouse Stock-Count Copilot

Argus photographs a warehouse bin with a terminal.
SAM 3.1 counts the items in the bin.
The count is reconciled against the ledger.
A discrepancy report with action priorities is produced.

Theme: Build for Your World — tentative, pending final confirmation.

## Problem

Manual bin counting is slow.
Missed counts and double counts happen.
Delayed recording drifts the ledger away from physical stock.
After finding a discrepancy, the worker still needs to know
which bin to check first.

## Workflow

1. Capture. Photograph a bin with the terminal.
2. SAM counting. Count items at the adapter boundary.
3. Ledger reconciliation. Compare ledger and counted quantities per bin.
4. Discrepancy report. Separate matches from mismatches and attach actions.

Verdicts are match, short, and over.
Match means ledger and counted quantities are equal.
Short means the counted quantity is lower.
Over means the counted quantity is higher.

## What we built vs. what already existed

Already existed:

- Meta SAM 3.1
- Meta Model API
- Python standard library
- Hardware platform

Built for this hackathon:

- All code and documents in this repository.
- Newly written during the hackathon period starting 2026-10-27.

## Meta AI tools

The integration point is the Meta Model API.
Counting sits behind an adapter boundary.
Reconciliation, report, and console only consume its result.
Switching is via environment variables `SAM_API_BASE_URL` and `SAM_API_KEY`.
Unset means the mock adapter runs.

A live SAM 3.1 call has NOT been made yet.
The live adapter code path is prepared but has NOT been verified against the real API; it is exercised only with a fake transport in tests.
Argus is currently running on the mock adapter.
Live calling starts only after the Model API credit deposit is confirmed.
Mock results are labelled as mock in the UI and reports.
Mock results are never claimed as live results.

Pi device camera integration is not yet verified.
Argus is designed for Raspberry Pi 5 + camera.
It is developed with a simulator before the device arrives.

## Technical depth

The reconciliation engine produces per-bin ledger, counted, delta, and verdict.
Summary metrics include counted bins, matches, and mismatches.
Summary metrics also include match rate, total absolute delta, and net delta.
The report module produces a human-readable text report.
The same module produces a structured payload.
Argus uses the Python standard library only.
The QA harness runs 17 baseline checks with literals fixed in the harness file.
Unit tests currently number 105.

## Demo data

All examples are fictional demo data.
There are 6 demo bins.
4 bins matched.
2 bins mismatched.
Short: A-01-02, ledger 8, counted 5, delta -3.
Over: B-01-02, ledger 6, counted 9, delta +3.
Total absolute delta is 6.
Net delta is 0.
Match rate is 66.7%.

## Impact

Demo basis: 2 mismatches out of 6 bins, total absolute delta 6, and a 66.7% match rate are organised in one reconciliation pass, with action priorities attached; action priority sorts mismatches by absolute delta descending, ties by bin_id ascending; short -> re-photograph and check receiving/shipping records; over -> check for misplaced stock and check transfer/return records.
