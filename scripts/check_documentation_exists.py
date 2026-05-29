#!/usr/bin/env python3
import pathlib

def is_reusable_workflow(file: pathlib.Path) -> bool:
    return file.is_file() and file.name.endswith('.yml') and file.name.startswith('reusable-')

reusable_workflow_filenames = [f for f in pathlib.Path('.github/workflows').iterdir() if is_reusable_workflow(f)]

missing_documentation = []

for reusable_workflow in reusable_workflow_filenames:
    workflow_name = reusable_workflow.stem
    expected_doc_path = pathlib.Path(f'docs/{workflow_name}.md')
    if not expected_doc_path.exists():
        missing_documentation.append(str(expected_doc_path))

if missing_documentation:
    raise ValueError(f"Missing documentation for reusable workflows: {', '.join(missing_documentation)}")
else:
    print("All reusable workflows have corresponding documentation.")
