---
name: New Workflow Submission
about: New Workflow Submission
title: ''
labels: enhancement
assignees: bls20AWS

---

To submit a workflow to the Step Functions Workflows Collection, submit an issue with the following information.

To learn more about submitting a workflow, read the publishing guidelines page.

1. Use the model template located at https://github.com/aws-samples/step-functions-workflows-collection/tree/main/_workflow_model to set up a README, template and any associated code.


2. All the information below must be provided in the "example-workflow.json" file cloned from the [model](https://github.com/aws-samples/step-functions-workflows-collection/tree/main/_workflow_model) **

Note the following information for the model:

- Description (introBox.text) should be a 300-500 word explanation of how the pattern works.
- Simplicity: must be 1 of (`1 - Fundamental`, `2 -  Pattern`, `3 - Application` )
- Diagram: This must link to an Exported PNG of the workflow that shows any service integrations, you can export this from Workflow studio.
- Type: Must be one of (`Standard`, `Express`)
- Resources should link to AWS documentation and AWS blogs related to the post (1-5 maximum).
- Framework: currently, we support SAM or CDK.
- Author bio may include a LinkedIn and/or Twitter reference and a 1-sentence bio.

You must ensure that the sections of the model README.md are completed in full.
