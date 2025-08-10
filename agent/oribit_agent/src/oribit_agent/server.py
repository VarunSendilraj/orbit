from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()


class CreateFiles(BaseModel):
    dir: str = "~/Documents"
    count: int = 5
    prefix: str = "note"
    ext: str = "md"


@app.post("/tools/create_files")
def create_files(a: CreateFiles) -> dict[str, list[str]]:
    target_directory = Path(os.path.expanduser(a.dir))
    target_directory.mkdir(parents=True, exist_ok=True)

    created_paths: list[str] = []
    for index in range(1, a.count + 1):
        file_path = target_directory / f"{a.prefix}_{index}.{a.ext}"
        file_path.write_text("")
        created_paths.append(str(file_path))

    return {"created": created_paths}


@app.post("/tools/open_app")
def open_app(name: str) -> dict[str, str]:
    subprocess.run(["open", "-a", name], check=True)
    return {"status": "ok"}
