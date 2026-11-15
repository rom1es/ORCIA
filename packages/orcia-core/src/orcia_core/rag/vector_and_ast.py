"""Contextual Header, Cosine Similarity & AST Symbol Chunker (`AD-8`, `AD-24.11`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import ast

from orcia_core.rag.models import CodeGraphEdgeEntity, KbChunkEntity
from orcia_kernel.ids import new_uuid7_str

EMBEDDING_DIM: int = 1024


def cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Compute dot-product cosine similarity on normalized vectors."""
    return sum(x * y for x, y in zip(a, b, strict=False))


def build_contextual_header(
    *,
    datasource_alias: str,
    hierarchy_path: str,
    title: str,
    ontology_concepts: tuple[str, ...] = (),
) -> str:
    """Format `[Alias Source : Espace/Projet > Parent > Titre | Concepts Ontologie]` (`AD-8`)."""
    concepts_str = ", ".join(ontology_concepts) if ontology_concepts else "Général"
    return f"[{datasource_alias} : {hierarchy_path} > {title} | {concepts_str}]"


def chunk_ast_symbol(
    *,
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    qualname: str,
    doc_id: str,
    doc_key: str,
    workspace_id: str,
    datasource_alias: str,
    repo_uri: str,
    file_path: str,
    lines: list[str],
    concept_map: dict[str, str],
) -> tuple[KbChunkEntity, list[CodeGraphEdgeEntity]]:
    """Extract a syntactic AST symbol chunk and its Code Property Graph edges."""
    start = max(0, node.lineno - 1)
    end = getattr(node, "end_lineno", node.lineno)
    symbol_src = "\n".join(lines[start:end])
    concept = concept_map.get(qualname) or concept_map.get(node.name)
    header = build_contextual_header(
        datasource_alias=datasource_alias,
        hierarchy_path=file_path,
        title=qualname,
        ontology_concepts=(concept,) if concept else (),
    )
    chunk = KbChunkEntity(
        id=new_uuid7_str(),
        chunk_key=f"{doc_key}-ast-{qualname}",
        document_id=doc_id,
        workspace_id=workspace_id,
        datasource_alias=datasource_alias,
        parent_chunk_id=None,
        chunk_role="AST_SYMBOL",
        contextual_header=header,
        content_text=symbol_src,
        token_count=max(150, min(800, len(symbol_src.split()) + 150)),
        embedding=None,
        embedding_model_id=None,
        embedding_generated_at=None,
    )
    prefix = f"edge-{datasource_alias}-{file_path}"
    edges: list[CodeGraphEdgeEntity] = [
        CodeGraphEdgeEntity(
            id=new_uuid7_str(),
            edge_key=f"{prefix}-def-{qualname}",
            workspace_id=workspace_id,
            source_repo_uri=repo_uri,
            source_symbol=file_path,
            target_repo_uri=repo_uri,
            target_symbol=qualname,
            edge_type="DEFINES",
        )
    ]
    if concept:
        edges.append(
            CodeGraphEdgeEntity(
                id=new_uuid7_str(),
                edge_key=f"{prefix}-concept-{qualname}-{concept}",
                workspace_id=workspace_id,
                source_repo_uri=repo_uri,
                source_symbol=qualname,
                target_repo_uri="orcia://ontology",
                target_symbol=concept,
                edge_type="IMPLEMENTS_CONCEPT",
            )
        )
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
            called = sub.func.id
            edges.append(
                CodeGraphEdgeEntity(
                    id=new_uuid7_str(),
                    edge_key=f"{prefix}-call-{qualname}-{called}-{sub.lineno}",
                    workspace_id=workspace_id,
                    source_repo_uri=repo_uri,
                    source_symbol=qualname,
                    target_repo_uri=repo_uri,
                    target_symbol=called,
                    edge_type="TESTED_BY" if node.name.startswith("test_") else "CALLS",
                )
            )
    return chunk, edges
