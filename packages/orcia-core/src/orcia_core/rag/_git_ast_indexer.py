"""Regime 2: Syntactic AST symbol chunking & Code Property Graph helper (`AD-8`)."""

from __future__ import annotations

import ast
import hashlib

from orcia_core.rag.models import CodeGraphEdgeEntity, KbChunkEntity, KbDocumentEntity
from orcia_core.rag.vector_and_ast import build_contextual_header
from orcia_core.rag.vector_and_ast import chunk_ast_symbol as _chunk_ast_symbol
from orcia_kernel.ids import new_uuid7_str


def index_git_ast_and_code_graph_impl(
    *,
    workspace_id: str,
    datasource_id: str,
    datasource_alias: str,
    repo_uri: str,
    file_path: str,
    python_source: str,
    commit_sha: str,
    implements_concepts: dict[str, str] | None = None,
) -> tuple[KbDocumentEntity, tuple[KbChunkEntity, ...], tuple[CodeGraphEdgeEntity, ...]]:
    """Regime 2: Syntactic AST symbol chunking (`150-800` tokens) + Code Property Graph."""
    doc_id = new_uuid7_str()
    sha256_hex = hashlib.sha256(f"{commit_sha}:{python_source}".encode()).hexdigest()
    doc = KbDocumentEntity(
        id=doc_id,
        doc_key=f"doc-git-{datasource_alias}-{file_path.replace('/', '-')}",
        workspace_id=workspace_id,
        datasource_id=datasource_id,
        datasource_alias=datasource_alias,
        source_uri=f"{repo_uri}/blob/{commit_sha}/{file_path}",
        source_scheme="git",
        indexing_regime="CODE_AST_GRAPH",
        title=file_path,
        revision_tag=commit_sha,
        content_sha256=sha256_hex,
    )
    concept_map = implements_concepts or {}
    try:
        tree = ast.parse(python_source)
    except SyntaxError:
        header = build_contextual_header(
            datasource_alias=datasource_alias, hierarchy_path=file_path, title=file_path
        )
        fallback = KbChunkEntity(
            id=new_uuid7_str(),
            chunk_key=f"{doc.doc_key}-ast-module",
            document_id=doc_id,
            workspace_id=workspace_id,
            datasource_alias=datasource_alias,
            parent_chunk_id=None,
            chunk_role="AST_SYMBOL",
            contextual_header=header,
            content_text=python_source,
            token_count=max(150, min(800, len(python_source.split()) + 150)),
            embedding=None,
            embedding_model_id=None,
            embedding_generated_at=None,
        )
        return doc, (fallback,), ()

    lines = python_source.splitlines()
    chunks: list[KbChunkEntity] = []
    edges: list[CodeGraphEdgeEntity] = []
    prefix = f"edge-{datasource_alias}-{file_path}"

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(
                    CodeGraphEdgeEntity(
                        id=new_uuid7_str(),
                        edge_key=f"{prefix}-import-{alias.name}",
                        workspace_id=workspace_id,
                        source_repo_uri=repo_uri,
                        source_symbol=file_path,
                        target_repo_uri=repo_uri,
                        target_symbol=alias.name,
                        edge_type="IMPORTS",
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            base_mod = node.module or ""
            targets = [f"{base_mod}.{a.name}".strip(".") for a in node.names] or [base_mod]
            for mod_name in targets:
                edges.append(
                    CodeGraphEdgeEntity(
                        id=new_uuid7_str(),
                        edge_key=f"{prefix}-import-{mod_name}",
                        workspace_id=workspace_id,
                        source_repo_uri=repo_uri,
                        source_symbol=file_path,
                        target_repo_uri=repo_uri,
                        target_symbol=mod_name,
                        edge_type="IMPORTS",
                    )
                )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            c_chunk, c_edges = _chunk_ast_symbol(
                node=node,
                qualname=node.name,
                doc_id=doc_id,
                doc_key=doc.doc_key,
                workspace_id=workspace_id,
                datasource_alias=datasource_alias,
                repo_uri=repo_uri,
                file_path=file_path,
                lines=lines,
                concept_map=concept_map,
            )
            chunks.append(c_chunk)
            edges.extend(c_edges)
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m_chunk, m_edges = _chunk_ast_symbol(
                            node=sub,
                            qualname=f"{node.name}.{sub.name}",
                            doc_id=doc_id,
                            doc_key=doc.doc_key,
                            workspace_id=workspace_id,
                            datasource_alias=datasource_alias,
                            repo_uri=repo_uri,
                            file_path=file_path,
                            lines=lines,
                            concept_map=concept_map,
                        )
                        chunks.append(m_chunk)
                        edges.extend(m_edges)
    return doc, tuple(chunks), tuple(edges)
