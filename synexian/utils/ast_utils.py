"""AST utility functions for python code analysis """

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set

from synexian.exceptions import ParserError


def parse_python_file(file_path: Path) -> Optional[ast.AST]:
    """Parse a Python file into an AST.

    Args:
        file_path: Path to Python file

    Returns:
        AST tree or None if parsing fails

    Raises:
        ParserError: If file cannot be parsed
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        raise ParserError("ast_parser", str(file_path), f"Syntax error: {e}")
    except Exception as e:
        raise ParserError("ast_parser", str(file_path), str(e))


def get_functions(tree: ast.AST) -> List[ast.FunctionDef]:
    """Get all function definitions from AST.

    Args:
        tree: AST tree

    Returns:
        List of function definition nodes
    """
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node)
    return functions


def get_classes(tree: ast.AST) -> List[ast.ClassDef]:
    """Get all class definitions from AST.

    Args:
        tree: AST tree

    Returns:
        List of class definition nodes
    """
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node)
    return classes


def get_imports(tree: ast.AST) -> Set[str]:
    """Get all imported modules from AST.

    Args:
        tree: AST tree

    Returns:
        Set of module names
    """
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    return imports


def count_nodes_by_type(tree: ast.AST) -> Dict[str, int]:
    """Count nodes by type in AST.

    Args:
        tree: AST tree

    Returns:
        Dictionary mapping node type to count
    """
    counts = {}

    for node in ast.walk(tree):
        node_type = type(node).__name__
        counts[node_type] = counts.get(node_type, 0) + 1

    return counts


def get_function_complexity(func: ast.FunctionDef) -> int:
    """Calculate simple complexity metric for a function.

    Args:
        func: Function definition node

    Returns:
        Complexity score (number of branches)
    """
    complexity = 1

    for node in ast.walk(func):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1

    return complexity


def get_function_args(func: ast.FunctionDef) -> List[str]:
    """Get function argument names.

    Args:
        func: Function definition node

    Returns:
        List of argument names
    """
    args = []

    # Regular arguments
    for arg in func.args.args:
        args.append(arg.arg)

    # Keyword-only arguments
    for arg in func.args.kwonlyargs:
        args.append(arg.arg)

    # *args
    if func.args.vararg:
        args.append(f"*{func.args.vararg.arg}")

    # **kwargs
    if func.args.kwarg:
        args.append(f"**{func.args.kwarg.arg}")

    return args


def has_docstring(node: ast.AST) -> bool:
    """Check if a node has a docstring.

    Args:
        node: AST node (function, class, or module)

    Returns:
        True if node has docstring
    """
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
        return ast.get_docstring(node) is not None
    return False


def get_max_nesting_depth(tree: ast.AST) -> int:
    """Calculate maximum nesting depth in AST.

    Args:
        tree: AST tree

    Returns:
        Maximum nesting depth
    """
    def _depth(node, current_depth=0):
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                child_depth = _depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = _depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    return _depth(tree)
