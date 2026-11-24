# Loan Processing Automation: Retrospective Business Analysis Case Study

| File | Contents |
|---|---|
| [`Loan_Processing_Automation_BA_Case_Study.pdf`](./Loan_Processing_Automation_BA_Case_Study.pdf) | The case study, for reading |
| [`Loan_Processing_Automation_BA_Case_Study.docx`](./Loan_Processing_Automation_BA_Case_Study.docx) | Editable Word version |
| [`Loan_Processing_Backlog.csv`](./Loan_Processing_Backlog.csv) | The 10 user stories as a Jira-importable backlog |

## The case in brief

A financial cooperative's loan processing relied on a manual routine: typing a computed
amount for each transaction, clicking through many steps to print documents, and
recording every transaction on paper. The routine already ran in Excel, so the work was
to analyze how the processor actually worked and automate the repeated steps in VBA
without changing the parts of the workflow people depended on. The platform has been in
daily use since 2022 and its outputs are used across four roles: loan processing,
cashier, bookkeeping and management.

## What the case study contains

- Business objective, scope and out-of-scope items
- Stakeholder table
- As-is and to-be process maps
- Business and functional requirements (BR-1 to BR-5, FR-1 to FR-8)
- 10 user stories with Given/When/Then acceptance criteria
- Edge cases with their current status
- Numbered assumptions with confidence ratings
- Requirement-to-story traceability
- Outcome and what I would do differently
- Appendix: the Jira backlog

## Honest limits

- Reconstructed after the system was built; criteria were not written before development.
- No before-and-after time measurement exists, so no time-saving claim is made.
- The insurer's rate structure and print format already existed; the contribution is the
  automation around them.
- Individual payments, penalties and partial payments stay in the cooperative's legacy
  ledger and are out of scope.

## Backlog CSV

Columns: Summary, Issue Type, Description (user story, acceptance criteria, requirement
links), Priority (suggested), Labels (epic name and `retrospective`), Status. Import with
Jira's CSV importer and map the two Labels columns to Labels.
