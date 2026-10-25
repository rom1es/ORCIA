"""Deterministic 1024-d Halfvec Embeddings, Contextual Header & AST Symbol Chunker (`AD-8`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import ast
import hashlib
import math
import re

from orcia_core.domain.identifiers import new_uuid7_str
from orcia_core.rag.models import CodeGraphEdgeEntity, KbChunkEntity

EMBEDDING_DIM: int = 1024


def compute_deterministic_halfvec_1024(text: str) -> tuple[float, ...]:
    """Generate a deterministic L2-normalized 1024-d vector (`halfvec(1024)`) from tokens."""
    vec = [0.0] * EMBEDDING_DIM
    tokens = re.findall(r"[a-z0-9_]{2,}", text.lower())
    if not tokens:
        vec[0] = 1.0
        return tuple(vec)

    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        for i in range(0, 16, 2):
            idx = ((digest[i] << 8) | digest[i + 1]) % EMBEDDING_DIM
            sign = 1.0 if (digest[(i + 2) % 32] % 2 == 0) else -1.0
            vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return tuple(round(v / norm, 6) for v in vec)


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
        embedding=compute_deterministic_halfvec_1024(f"{header}\n{symbol_src}"),
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
