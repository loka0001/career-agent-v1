"""One-use AST codemod for splitting legacy aggregate modules."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

ROOT = Path(__file__).resolve().parents[1]
Definition: TypeAlias = ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


def _imports(module: ast.Module, used: set[str]) -> list[str]:
    output: list[str] = []
    for node in module.body:
        if isinstance(node, ast.Import):
            aliases = [
                alias for alias in node.names if (alias.asname or alias.name.split(".")[0]) in used
            ]
            if aliases:
                output.append(ast.unparse(ast.Import(names=aliases)))
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            aliases = [alias for alias in node.names if (alias.asname or alias.name) in used]
            if aliases:
                output.append(
                    ast.unparse(ast.ImportFrom(module=node.module, names=aliases, level=node.level))
                )
    return output


def _split(
    source_path: Path,
    package_path: Path,
    group_for: Callable[[Definition], str | None],
) -> None:
    source = source_path.read_text(encoding="utf-8")
    lines = source.splitlines()
    module = ast.parse(source)
    nodes: list[Definition] = [
        node
        for node in module.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and group_for(node) is not None
    ]
    groups: dict[str, list[Definition]] = {}
    symbol_group: dict[str, str] = {}
    for node in nodes:
        group = group_for(node)
        assert group is not None
        groups.setdefault(group, []).append(node)
        symbol_group[node.name] = group

    package_path.mkdir(parents=True, exist_ok=True)
    (package_path / "__init__.py").write_text(
        '"""Generated bounded model modules."""\n', encoding="utf-8"
    )
    for group, members in groups.items():
        blocks = []
        for node in members:
            decorator_lines = [decorator.lineno for decorator in node.decorator_list]
            start_line = min([node.lineno, *decorator_lines])
            blocks.append("\n".join(lines[start_line - 1 : node.end_lineno]))
        group_source = "\n\n\n".join(blocks)
        parsed_group = ast.parse(group_source)
        used = {node.id for node in ast.walk(parsed_group) if isinstance(node, ast.Name)}
        dependency_imports: list[str] = []
        for symbol in sorted(used):
            dependency_group = symbol_group.get(symbol)
            if dependency_group is not None and dependency_group != group:
                relative = package_path.relative_to(ROOT).as_posix().replace("/", ".")
                dependency_imports.append(f"from {relative}.{dependency_group} import {symbol}")
        header = [
            f'"""Generated {group} slice of {source_path.name}."""',
            "",
            "from __future__ import annotations",
            "",
            *_imports(module, used),
            *dependency_imports,
            "",
            "",
        ]
        (package_path / f"{group}.py").write_text(
            "\n".join(header) + group_source + "\n",
            encoding="utf-8",
        )

    relative = package_path.relative_to(ROOT).as_posix().replace("/", ".")
    facade = [
        f'"""Compatibility exports for the split {source_path.stem} modules."""',
        "",
        "from __future__ import annotations",
        "",
    ]
    for group, members in groups.items():
        names = ", ".join(node.name for node in members)
        facade.append(f"from {relative}.{group} import {names}")
    facade.extend(
        [
            "",
            "__all__ = [",
            *(f'    "{node.name}",' for node in nodes),
            "]",
            "",
        ]
    )
    source_path.write_text("\n".join(facade), encoding="utf-8")


def split_domain() -> None:
    def group_for(node: Definition) -> str:
        line = node.lineno
        boundaries = [
            (42, "shared"),
            (157, "catalog"),
            (199, "marketing"),
            (275, "sales"),
            (410, "messaging"),
            (529, "integrations"),
            (609, "public"),
            (683, "orders"),
            (759, "intelligence"),
            (812, "automations"),
            (935, "content"),
            (1118, "operations"),
            (10_000, "auth"),
        ]
        return next(group for end, group in boundaries if line <= end)

    _split(ROOT / "app/domain/models.py", ROOT / "app/domain/model_groups", group_for)


def split_database() -> None:
    def group_for(node: Definition) -> str:
        line = node.lineno
        boundaries = [
            (26, "shared"),
            (147, "identity"),
            (273, "catalog"),
            (352, "content"),
            (465, "integrations"),
            (593, "customers"),
            (680, "orders"),
            (833, "automation"),
            (947, "billing"),
            (10_000, "platform"),
        ]
        return next(group for end, group in boundaries if line <= end)

    _split(ROOT / "app/db/models.py", ROOT / "app/db/model_groups", group_for)


def split_commerce() -> None:
    groups = {
        "ShopifyConnector": "shopify",
        "WooCommerceConnector": "woocommerce",
        "GenericCommerceConnector": "generic",
        "connector_for": "factory",
        "verify_commerce_signature": "factory",
    }

    def group_for(node: Definition) -> str:
        return groups.get(node.name, "common")

    _split(
        ROOT / "app/integrations/commerce.py",
        ROOT / "app/integrations/commerce_modules",
        group_for,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("domain", "database", "commerce"))
    target = parser.parse_args().target
    {"domain": split_domain, "database": split_database, "commerce": split_commerce}[target]()


if __name__ == "__main__":
    main()
