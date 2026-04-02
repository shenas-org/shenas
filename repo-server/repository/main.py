from __future__ import annotations

from pathlib import Path

import typer
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from repository.server import PackageRepository, normalize

app = FastAPI(title="Simple Package Repository", docs_url=None, redoc_url=None)

_repo: PackageRepository | None = None


def get_repo() -> PackageRepository:
    if _repo is None:
        raise RuntimeError("Repository not initialized")
    return _repo


def _index_html(repo: PackageRepository) -> str:
    packages = repo.all_packages()
    links = "\n".join(f'    <a href="/simple/{pkg.normalized}/">{pkg.name}</a>' for pkg in packages)
    return f"""<!DOCTYPE html>
<html>
  <head><title>Simple Index</title></head>
  <body>
{links}
  </body>
</html>"""


def _package_html(repo: PackageRepository, name: str) -> str:
    pkg = repo.get_package(name)
    if pkg is None:
        raise HTTPException(status_code=404, detail=f"No package {name!r} found")
    links = "\n".join(f'    <a href="/packages/{f.path.name}#sha256={f.sha256}">{f.path.name}</a>' for f in pkg.files)
    return f"""<!DOCTYPE html>
<html>
  <head><title>Links for {pkg.name}</title></head>
  <body>
    <h1>Links for {pkg.name}</h1>
{links}
  </body>
</html>"""


@app.get("/simple/", response_class=HTMLResponse)
def simple_index() -> HTMLResponse:
    return HTMLResponse(content=_index_html(get_repo()), media_type="text/html; charset=utf-8")


@app.get("/simple/{name}/", response_class=HTMLResponse)
def simple_package(name: str) -> HTMLResponse:
    return HTMLResponse(content=_package_html(get_repo(), normalize(name)), media_type="text/html; charset=utf-8")


@app.get("/packages/{filename}")
def download_file(filename: str) -> FileResponse:
    repo = get_repo()
    path = repo.packages_dir / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=path, filename=filename)


cli = typer.Typer()


@cli.command()
def serve(
    packages_dir: Path = typer.Argument(Path("packages"), help="Directory containing distribution files"),
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(7290, help="Bind port"),
) -> None:
    global _repo
    packages_dir.mkdir(parents=True, exist_ok=True)
    _repo = PackageRepository(packages_dir)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    cli()
