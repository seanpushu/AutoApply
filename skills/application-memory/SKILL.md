---
name: application-memory
description: Reuse locally confirmed applicant facts to fill a user-requested internship application, preserve corrections, and verify Oracle-style forms without publishing private information.
---

# Application memory

## Locate private facts
Read `data/application-memory.json` relative to the AutoApply checkout. When installed globally, use `local-config.json` beside this skill to locate that file. If neither exists, ask for the private memory location; do not search unrelated personal folders. The example in this repository contains no applicant facts.

Load only the facts needed for the specified application. User corrections and the latest designated resume supersede older facts; retain a dated local history before updates. Never print the whole memory or put personal values, document contents, screenshots, or absolute personal paths into tracked files. Do not overwrite the application's separate local-profile.json schema.

## Reuse and confirmation
A request to fill a specific application permits reuse of confirmed ordinary application facts within that scope; avoid asking the same factual questions again. Unknown values remain unknown. Age must retain an as-of date; do not invent a birth date. Future CPT eligibility is not proof of current approval or a reusable blanket yes/no answer. Do not infer sponsorship, military history, disability, ethnicity, or prior employer relationships. Clarify only missing answers and changed consent requirements.

Keep final submission per-application and explicitly confirmed. Past submissions, stored facts and exported kits are not submission authorization. Do not resume a paused application unless requested. Stop before signing/accepting declarations until the user has reviewed their actual terms. Credentials and CAPTCHA remain user-operated.

## Form workflow
Use an available connected browser and inspect the current application before modifying it. Preserve existing user-entered values unless an update is authorized. Map the requested resume's education, dates and responsibilities; missing degree selections may survive resume import and need explicit choice.

For Oracle-style dependent address fields, search the postal code and select the matching city/county/state row. Merely entering text can be discarded on blur. Verify the final rendered values of all address fields. Use fresh semantic locators; when a radio click does not stick, use the scoped radio group's check operation and verify checked state. Do not use old accessibility indices after form changes.

For uploads, use the supported file-chooser flow and verify the resulting filename after upload completes. A resume used for profile parsing may still be missing from the required resume attachment section. A completed undergraduate transcript does not establish current graduate enrollment. Preserve that distinction and request current enrollment evidence when required; never invent a new-program GPA.

After saving education/work details, reopen or inspect visible values when needed to check text and dates. Never click Submit merely to test validation. At the review stage, summarize attachments, outstanding answers and declarations, then obtain final approval. Record success only from a visible receipt. A cancelled/paused workflow is not Applied.

## Sharing
Private memory and document files stay under ignored `data/` or outside Git. Before committing, check ignored status and scan staged changes for private values/paths. Push only on explicit user request. An ignore rule does not remove content already in Git history. Stop and report an existing disclosure rather than claiming it is protected or rewriting history without authorization.
