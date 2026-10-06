# Validation-only correction: ImageJ's padded Done button

The pinned ImageJ 1.54p `ij.gui.MessageDialog` constructs its AWT button with
`"  OK  "` (two ASCII spaces on each side). The previous harness compared its
label to `"OK"`, so it could not acknowledge that actual button if the success
dialog was reached. This is a harness issue, not a demonstrated registration
algorithm defect.

`MultiplexFullProbe` now accepts only `"OK"` and that exact known padded label.
It examines the button only after the existing exact MessageDialog class,
`Multiplex Registration` title and `Done.\nSaved to: <test Results directory>`
body checks succeed. Existing expected-output-file, modality, activity and
visibility guards remain. The action still clicks the real button and logs its
literal label. No error dialog or unrelated prompt is accepted.

Regression controls exercise both accepted labels and reject null, Cancel,
Not OK, OK! and unrecognized single-space padding. They extend the existing
headless prompt-contract check; they do not create or click a native dialog.

## Evidence

`results/padded-done-26298b7/` contains:

- Successful Java harness compilation against the actual production classes
- Four passing headless controls, including the new two-positive/five-negative
  Done-label regression checks
- Thirteen passing Python reporting/provenance tests
- Bytecode from the checksum-recorded pinned ImageJ jar showing the padded label
- Portable summary, source/class/dependency/input hashes and redaction provenance

The run selected only `controls`; its `full_service_acceptance_passed` remains
false. No full workflow, native dialog action or Mac result is claimed. These
checks do not modify or reclassify any native run already in progress, and prior
published evidence is unchanged. A subsequent native run is needed to establish
that the actual button can be acknowledged and to evaluate saved workflow outputs.

`padded-done-delta-manifest.json` hashes this correction and its new evidence.
The original frozen manifest remains an immutable record of the first published
harness; it is not rewritten to describe this later correction.
