# Codex task: run Abaqus model audit

## Goal
Inspect the Abaqus/CAE model `doub_part25_2d_seepage_plastic_v1.cae` without modifying the original model, run the supplied audit script, and return the generated text reports to this same GitHub branch.

## Inputs
- `abaqus-audit/doub_part25_2d_seepage_plastic_v1.cae`
- `abaqus-audit/abaqus_model_audit.py`

## Required execution
1. Check whether Abaqus/CAE is installed and available on PATH.
2. First try:

```bash
abaqus cae noGUI=abaqus_model_audit.py -- doub_part25_2d_seepage_plastic_v1.cae
```

Run the command from the `abaqus-audit` directory.

3. If `abaqus` is not found, check common SIMULIA/Abaqus launchers and installation paths, including `abaqus.bat`, `abq*.bat`, SIMULIA Commands, and installed Abaqus Python/CAE launchers. Use the actual installed launcher if available.
4. Do not edit, resave, repair, or overwrite the original `.cae` file.

## Expected outputs
If successful, commit these generated files back to branch `abaqus-audit-task`:
- `abaqus-audit/abaqus_model_audit.txt`
- every `abaqus-audit/*_keywords_no_mesh.txt`

Also create `abaqus-audit/codex_run_status.txt` containing:
- exact command used
- Abaqus version if detectable
- whether the run succeeded
- any warnings/errors printed by Abaqus

If Abaqus cannot be run, still create and commit `codex_run_status.txt` explaining exactly what is missing (executable, license, environment, etc.) and what locations were checked.

## What the report must expose
The supplied script is intended to extract enough information for ChatGPT to diagnose the model, especially:
- material Density values
- Elastic / plastic model parameters
- Permeability values
- pore-fluid Specific Weight
- analysis Steps and increments
- Gravity loads
- pore-pressure / predefined fields
- displacement and pore-pressure boundary conditions
- element types and mesh summary
- keyword blocks without the full mesh

## Important diagnostic context
The main suspected issue is a unit/parameter inconsistency around Density, Gravity, Permeability and pore-fluid Specific Weight. Do not change those values. Only extract and report them so ChatGPT can analyze which parameter is wrong and by what factor.
