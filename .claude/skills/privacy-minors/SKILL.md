---
name: privacy-minors
description: Use when a spec, plan or change touches personal data, especially data about people under 18.
---
# Handling personal data (and minors' data)

When designing or changing anything that stores, shows or logs personal data:

1. Minimise: store only fields the spec needs (e.g. birth year, not full date of birth).
2. Pseudonymise: use internal IDs; show real names only to roles that need them.
3. Consent: for under-18s, record guardian consent before storing their data.
4. Retention: every personal-data field has a retention period and a delete path.
5. Logging: never log names, contact details or identifiers that map to a person.
6. Flag conflicts: if a requirement needs more data than this allows, flag it in
   the spec's "Conflicts flagged for the human" section instead of deciding.
7. Record every new personal-data field in docs/threat-model.md.

This is an engineering checklist, not legal advice; check the law that applies
(e.g. India's DPDP Act, GDPR) for the actual product.
