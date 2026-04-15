"""Per-family entity table packages.

Each submodule here hosts the abstract base + concrete tables for one
family of entities (places, people, devices, ...). They compose on top
of the core :class:`app.entity.EntityTable` machinery but live in their
own files so the entity domain doesn't turn into a single megafile.
"""
