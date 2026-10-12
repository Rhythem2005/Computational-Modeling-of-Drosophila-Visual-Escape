"""Run frozen parents in an isolated snapshot without reverting the user's README."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from .config import BASE, OUT
from .evidence import ROOT, protected_hashes, file_hash, write_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--task",choices=["validate","baseline","run"],default="validate")
    parser.add_argument("arguments",nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if args.arguments[:1] == ["--"]: args.arguments=args.arguments[1:]
    before=protected_hashes()
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT / "workspace_preservation_before.json"
    if p.exists() and json.loads(p.read_text()) != before and (OUT / "execution_snapshot.json").exists():
        raise ValueError("Workspace parent files changed since Phase 9 baseline")
    write_json(p,before)
    # Freeze checks intentionally include the archival README. Only that documented
    # user change is substituted in the execution copy, never in the repository.
    archival=BASE / "execution_baseline/README.md"
    expected=json.loads((ROOT / "connectome/phase8/completion/results/preservation_after.json").read_text())
    recovered={}
    for name,value in expected.items():
        if name == "README.md":
            if file_hash(archival) != value:
                raise ValueError("Archival README does not match the saved freeze")
        elif before.get(name) != value:
            # The user is also cleaning archival Phase 1 duplicates. Recover only
            # exact frozen bytes into the copy, without restoring/deleting in cwd.
            if not name.startswith(("connectome/phase1/", "connectome/data/phase1/")):
                raise ValueError(f"Frozen earlier file differs: {name}")
            git_name=name.replace("connectome/data/phase1/", "connectome/phase1/")
            data=subprocess.check_output(["git","show",f"8ef70f3:{git_name}"],cwd=ROOT)
            if hashlib.sha256(data).hexdigest() != value:
                raise ValueError(f"Local history does not match frozen bytes: {name}")
            recovered[name]=data
    snapshot=Path(tempfile.mkdtemp(prefix="fly-phase9-execution-"))
    for name in before:
        target=snapshot/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(archival if name == "README.md" else ROOT/name,target)
    for name,data in recovered.items():
        target=snapshot/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
    for base in (BASE,ROOT / "connectome/scripts/phase9"):
        for source in base.rglob("*"):
            if source.is_file() and "__pycache__" not in source.parts:
                target=snapshot/source.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
    common=[sys.executable,"-m"]
    if args.task == "baseline":
        commands=[common+["connectome.scripts.phase9.evidence"],common+["connectome.scripts.phase9.regression","--stage","before"]]
    elif args.task == "run":
        commands=[common+["connectome.scripts.phase9.run_environment",*args.arguments]]
    else:
        commands=[]
        if not (OUT / "preservation_before.json").exists():
            commands.append(common+["connectome.scripts.phase9.evidence"])
        if not (OUT / "regression/before/summary.json").exists():
            commands.append(common+["connectome.scripts.phase9.regression","--stage","before"])
        commands.append(common+["connectome.scripts.phase9.validate_phase9"])
    return_code=0
    for command in commands:
        print("Execution snapshot:",snapshot,"Command:",command,flush=True)
        result=subprocess.run(command,cwd=snapshot)
        if result.returncode:
            return_code=result.returncode; break
    outputs=snapshot / "connectome/phase9/results"
    if outputs.exists():
        shutil.copytree(outputs,OUT,dirs_exist_ok=True)
    after=protected_hashes(); write_json(OUT / "workspace_preservation_after.json",after)
    if before != after:
        raise ValueError("Original workspace parents changed during isolated execution")
    write_json(OUT / "execution_snapshot.json",dict(snapshot=str(snapshot),status="PASS" if return_code == 0 else "FAIL",
        commands=commands,exit_code=return_code,workspace_parent_files=len(before),workspace_parent_files_unchanged=True,
        current_readme_sha256=before["README.md"],execution_readme_sha256=file_hash(archival),
        archival_phase1_files_recovered_in_snapshot_only=list(recovered),
        rationale="User pushed Phase 6 and changed README while later phases were stashed. Restore missing files only; execute unchanged frozen parents with their original README in a copy. No branch/reset/stash mutation."))
    raise SystemExit(return_code)


if __name__ == "__main__":
    main()
