# Ledger design

This module stores immutable forecast records in SQLite, and keeps validated outcomes in a separate table.

- The forecast table is append-only and does not overwrite old records.
- The outcome table stores the realized result for each matured forecast.
- Duplicate forecast IDs are treated as idempotent retries.
- CSV export and backup are provided for portability and operator review.
