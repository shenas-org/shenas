"""Entity type definitions for the GitHub source.

Declares a ``repository`` entity type as a child of ``virtual_entity``
with properties sourced from both Wikidata (P277, P275, P571) and
GitHub-specific fields (stars, forks, open issues).

A repository may be *part of* a software project, but it is not a
subclass of one -- a repo is a storage/hosting concept, not a project.
"""

from __future__ import annotations

ENTITY_TYPES = [
    {
        "name": "repository",
        "display_name": "Repository",
        "parent": "virtual_entity",
        "icon": "git-branch",
        "is_abstract": False,
        "wikidata_qid": "Q1334294",  # source code repository
        "wikidata_properties": [
            {"pid": "P277", "label": "programming language"},
            {"pid": "P275", "label": "license"},
            {"pid": "P1324", "label": "source code repository URL"},
            {"pid": "P571", "label": "inception"},
            {"pid": "P178", "label": "developer"},
        ],
        "description": "A source code repository on GitHub.",
    },
]
