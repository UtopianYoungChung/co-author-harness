#!/usr/bin/env python3
"""Enforce deterministic decoding for subprocess and explicit byte decoding.

Windows inherits an arbitrary ANSI code page unless callers select one.  A
``text=True`` subprocess without both ``encoding`` and ``errors`` can therefore
crash while merely rendering a UTF-8 child diagnostic.  Explicit UTF-8 byte
decodes must likewise state their malformed-input policy.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SUBPROCESS_APIS = {"call", "check_call", "check_output", "Popen", "run"}
ALLOWED_ERRORS = {"replace", "strict"}


def _constant_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _true(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _keyword_map(call: ast.Call) -> dict[str, ast.AST]:
    return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg is not None}


def _subprocess_api(call: ast.Call) -> str | None:
    function = call.func
    if (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "subprocess"
        and function.attr in SUBPROCESS_APIS
    ):
        return function.attr
    return None


def _is_cmd_mklink(call: ast.Call) -> bool:
    if not call.args or not isinstance(call.args[0], (ast.List, ast.Tuple)):
        return False
    command = call.args[0].elts
    values = [_constant_string(item) for item in command[:3]]
    return values == ["cmd", "/c", "mklink"]


def _preferred_locale_call(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "locale"
        and node.func.attr == "getpreferredencoding"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value is False
    )


def _explicit_utf8_decode(call: ast.Call) -> bool:
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "decode" or not call.args:
        return False
    encoding = _constant_string(call.args[0])
    return encoding is not None and encoding.lower().replace("_", "-") in {"utf-8", "utf8"}


PYTHON_TOKEN = "<sys.executable>"
MAX_COMMAND_VARIANTS = 64
Variants = list[tuple[str, ...]]
Environment = dict[str, Variants]
Bundles = dict[str, Variants]
FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef
FunctionBinding = tuple[
    FunctionNode,
    Environment,
    Bundles,
    dict[str, Variants],
    dict[str, set[str]],
]
FunctionRegistry = dict[str, list[FunctionBinding]]


def _copy_registry(functions: FunctionRegistry) -> FunctionRegistry:
    return {name: list(bindings) for name, bindings in functions.items()}


def _merge_registries(*registries: FunctionRegistry) -> FunctionRegistry:
    merged: FunctionRegistry = {}
    for registry in registries:
        for name, bindings in registry.items():
            target = merged.setdefault(name, [])
            for binding in bindings:
                if all(id(existing[0]) != id(binding[0]) for existing in target):
                    target.append(binding)
    return merged


def _function_binding(
    node: FunctionNode, environment: Environment, bundles: Bundles
) -> FunctionBinding:
    parameters = node.args.posonlyargs + node.args.args
    captured: dict[str, Variants] = {}
    aliases: dict[str, set[str]] = {}
    default_offset = len(parameters) - len(node.args.defaults)
    for index, default in enumerate(node.args.defaults, start=default_offset):
        captured[parameters[index].arg] = _sequence_variants(default, environment)
        if isinstance(default, ast.Name):
            source = environment.get(default.id)
            aliases[parameters[index].arg] = {
                name for name, value in environment.items() if value is source
            } or {default.id}
    for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        if default is not None:
            captured[argument.arg] = _sequence_variants(default, environment)
            if isinstance(default, ast.Name):
                source = environment.get(default.id)
                aliases[argument.arg] = {
                    name for name, value in environment.items() if value is source
                } or {default.id}
    return node, dict(environment), dict(bundles), captured, aliases


def _refresh_captured_defaults(
    functions: FunctionRegistry, source_name: str, variants: Variants
) -> None:
    for bindings in functions.values():
        for _, _, _, captured, aliases in bindings:
            for parameter, alias_names in aliases.items():
                if source_name in alias_names:
                    captured[parameter] = list(variants)


def _rebind_captured_aliases(
    functions: FunctionRegistry, target_name: str, source_name: str | None
) -> None:
    for bindings in functions.values():
        for _, _, _, _, aliases in bindings:
            source_parameters = {
                parameter
                for parameter, names in aliases.items()
                if source_name is not None and source_name in names
            }
            for names in aliases.values():
                names.discard(target_name)
            for parameter in source_parameters:
                aliases[parameter].add(target_name)


def _scope_nodes(scope: ast.AST):
    """Yield one lexical scope without borrowing bindings from nested scopes."""
    pending = list(ast.iter_child_nodes(scope))
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield node
        pending.extend(ast.iter_child_nodes(node))


def _combine_variants(
    left: Variants, right: Variants
) -> Variants:
    combined: Variants = []
    for prefix in left:
        for suffix in right:
            combined.append(prefix + suffix)
            if len(combined) >= MAX_COMMAND_VARIANTS:
                return combined
    return combined


def _union_variants(*groups: Variants) -> Variants:
    combined: Variants = []
    for group in groups:
        for variant in group:
            if variant not in combined:
                combined.append(variant)
                if len(combined) >= MAX_COMMAND_VARIANTS:
                    return combined
    return combined


def _sequence_variants(node: ast.AST, environment: Environment) -> Variants:
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
        and node.attr == "executable"
    ):
        return [(PYTHON_TOKEN,)]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [(node.value,)]
    if isinstance(node, ast.Name):
        return environment.get(node.id, [(f"<unresolved:{node.id}>",)])
    if isinstance(node, ast.Starred):
        return _sequence_variants(node.value, environment)
    if isinstance(node, (ast.List, ast.Tuple)):
        variants: list[tuple[str, ...]] = [()]
        for element in node.elts:
            variants = _combine_variants(
                variants,
                _sequence_variants(element, environment),
            )
        return variants
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _combine_variants(
            _sequence_variants(node.left, environment),
            _sequence_variants(node.right, environment),
        )
    if isinstance(node, ast.IfExp):
        return (
            _sequence_variants(node.body, environment)
            + _sequence_variants(node.orelse, environment)
        )[:MAX_COMMAND_VARIANTS]
    return [("<dynamic>",)]


def _unsafe_isolated_python(variants: Variants) -> bool:
    return any(
        PYTHON_TOKEN in variant
        and bool(set(variant) & {"-I", "-S"})
        and "-B" not in variant
        for variant in variants
    )


def _executor_callback(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id.endswith(("runner", "executor"))


def _command_bundle(node: ast.AST, environment: Environment) -> Variants | None:
    if not isinstance(node, (ast.List, ast.Tuple)) or not node.elts:
        return None
    commands = [_sequence_variants(element, environment) for element in node.elts]
    if not all(any(PYTHON_TOKEN in variant for variant in variants) for variants in commands):
        return None
    return _union_variants(*commands)


def _merge_maps(*maps: dict[str, Variants]) -> dict[str, Variants]:
    merged: dict[str, Variants] = {}
    for name in {key for mapping in maps for key in mapping}:
        merged[name] = _union_variants(*(mapping[name] for mapping in maps if name in mapping))
    return merged


def _scan_expression(
    node: ast.AST,
    environment: Environment,
    bundles: Bundles,
    lines: set[int],
    functions: FunctionRegistry,
    call_stack: frozenset[int],
    visited: set[int],
) -> None:
    pending = [node]
    while pending:
        child = pending.pop()
        if child is not node and isinstance(
            child, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        if isinstance(child, ast.Call) and child.args and (
            _subprocess_api(child) is not None or _executor_callback(child)
        ):
            variants = _sequence_variants(child.args[0], environment)
            if _unsafe_isolated_python(variants):
                lines.add(child.args[0].lineno)
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id in functions
        ):
            for binding in functions[child.func.id]:
                _scan_function(
                    binding, environment, bundles, lines,
                    functions, call_stack, visited, child,
                )
        pending.extend(ast.iter_child_nodes(child))


def _local_binding_names(scope: ast.AST) -> set[str]:
    inherited = {
        name
        for node in _scope_nodes(scope)
        if isinstance(node, (ast.Global, ast.Nonlocal))
        for name in node.names
    }
    local: set[str] = set()
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
        local.update(argument.arg for argument in scope.args.posonlyargs)
        local.update(argument.arg for argument in scope.args.args)
        local.update(argument.arg for argument in scope.args.kwonlyargs)
        if scope.args.vararg is not None:
            local.add(scope.args.vararg.arg)
        if scope.args.kwarg is not None:
            local.add(scope.args.kwarg.arg)
    for node in _scope_nodes(scope):
        if isinstance(node, ast.Assign):
            local.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            local.add(node.target.id)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            local.add(node.target.id)
    return local - inherited


def _direct_nested_functions(scope: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    found: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    pending = list(scope.body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append(node)
            continue
        if isinstance(node, (ast.ClassDef, ast.Lambda)):
            continue
        pending.extend(ast.iter_child_nodes(node))
    return found


def _process_statements(
    statements: list[ast.stmt],
    environment: Environment,
    bundles: Bundles,
    lines: set[int],
    functions: FunctionRegistry,
    call_stack: frozenset[int],
    visited: set[int],
) -> tuple[Environment, Bundles]:
    environment = dict(environment)
    bundles = dict(bundles)
    for node in statements:
        if isinstance(node, ast.Assign):
            _scan_expression(node.value, environment, bundles, lines, functions, call_stack, visited)
            value = _sequence_variants(node.value, environment)
            bundle = _command_bundle(node.value, environment)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    _rebind_captured_aliases(
                        functions,
                        target.id,
                        node.value.id if isinstance(node.value, ast.Name) else None,
                    )
                    environment[target.id] = value
                    if bundle is None:
                        bundles.pop(target.id, None)
                    else:
                        bundles[target.id] = bundle
                    if isinstance(node.value, ast.Name) and node.value.id in functions:
                        functions[target.id] = list(functions[node.value.id])
                    else:
                        functions.pop(target.id, None)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            _scan_expression(node.value, environment, bundles, lines, functions, call_stack, visited)
            _rebind_captured_aliases(
                functions,
                node.target.id,
                node.value.id if isinstance(node.value, ast.Name) else None,
            )
            environment[node.target.id] = _sequence_variants(node.value, environment)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and isinstance(node.op, ast.Add):
            _scan_expression(node.value, environment, bundles, lines, functions, call_stack, visited)
            previous = environment.get(node.target.id, [(f"<unresolved:{node.target.id}>",)])
            updated = _combine_variants(
                previous,
                _sequence_variants(node.value, environment),
            )
            affected = [name for name, value in environment.items() if value is previous]
            for name in affected or [node.target.id]:
                environment[name] = updated
                _refresh_captured_defaults(functions, name, updated)
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.attr in {"append", "extend"}
            and len(node.value.args) == 1
        ):
            name = node.value.func.value.id
            previous = environment.get(name, [(f"<unresolved:{name}>",)])
            addition = _sequence_variants(node.value.args[0], environment)
            if node.value.func.attr == "append":
                addition = [(variant[0] if len(variant) == 1 else "<dynamic-append>",) for variant in addition]
            updated = _combine_variants(previous, addition)
            affected = [alias for alias, value in environment.items() if value is previous]
            for alias in affected or [name]:
                environment[alias] = updated
                _refresh_captured_defaults(functions, alias, updated)
        elif isinstance(node, ast.If):
            _scan_expression(node.test, environment, bundles, lines, functions, call_stack, visited)
            body_functions = _copy_registry(functions)
            else_functions = _copy_registry(functions)
            body_env, body_bundles = _process_statements(
                node.body, environment, bundles, lines, body_functions, call_stack, visited
            )
            else_env, else_bundles = _process_statements(
                node.orelse, environment, bundles, lines, else_functions, call_stack, visited
            )
            environment = _merge_maps(body_env, else_env)
            bundles = _merge_maps(body_bundles, else_bundles)
            functions.clear()
            functions.update(_merge_registries(body_functions, else_functions))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            _scan_expression(node.iter, environment, bundles, lines, functions, call_stack, visited)
            body_env = dict(environment)
            body_bundles = dict(bundles)
            if isinstance(node.target, ast.Name):
                if isinstance(node.iter, ast.Name) and node.iter.id in bundles:
                    body_env[node.target.id] = bundles[node.iter.id]
                else:
                    body_env[node.target.id] = [("<iteration-value>",)]
            body_env, body_bundles = _process_statements(
                node.body, body_env, body_bundles, lines, functions, call_stack, visited
            )
            else_env, else_bundles = _process_statements(
                node.orelse, environment, bundles, lines, functions, call_stack, visited
            )
            environment = _merge_maps(environment, body_env, else_env)
            bundles = _merge_maps(bundles, body_bundles, else_bundles)
        elif isinstance(node, ast.While):
            _scan_expression(node.test, environment, bundles, lines, functions, call_stack, visited)
            body_env, body_bundles = _process_statements(
                node.body, environment, bundles, lines, functions, call_stack, visited
            )
            else_env, else_bundles = _process_statements(
                node.orelse, environment, bundles, lines, functions, call_stack, visited
            )
            environment = _merge_maps(environment, body_env, else_env)
            bundles = _merge_maps(bundles, body_bundles, else_bundles)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                _scan_expression(
                    item.context_expr, environment, bundles, lines, functions, call_stack, visited
                )
            environment, bundles = _process_statements(
                node.body, environment, bundles, lines, functions, call_stack, visited
            )
        elif isinstance(node, ast.Try):
            paths = [_process_statements(
                node.body + node.orelse, environment, bundles, lines,
                functions, call_stack, visited,
            )]
            paths.extend(
                _process_statements(
                    handler.body, environment, bundles, lines,
                    functions, call_stack, visited,
                )
                for handler in node.handlers
            )
            environment = _merge_maps(*(path[0] for path in paths))
            bundles = _merge_maps(*(path[1] for path in paths))
            environment, bundles = _process_statements(
                node.finalbody, environment, bundles, lines, functions, call_stack, visited
            )
        elif isinstance(node, ast.Match):
            _scan_expression(node.subject, environment, bundles, lines, functions, call_stack, visited)
            paths = [
                _process_statements(
                    case.body, environment, bundles, lines, functions, call_stack, visited
                )
                for case in node.cases
            ]
            paths.append((environment, bundles))
            environment = _merge_maps(*(path[0] for path in paths))
            bundles = _merge_maps(*(path[1] for path in paths))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[node.name] = [_function_binding(node, environment, bundles)]
        elif isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _scan_function(
                        _function_binding(method, environment, bundles),
                        environment, bundles, lines, functions, call_stack, visited,
                    )
            continue
        else:
            _scan_expression(node, environment, bundles, lines, functions, call_stack, visited)
    return environment, bundles


def _scan_function(
    binding: FunctionBinding,
    inherited_environment: Environment,
    inherited_bundles: Bundles,
    lines: set[int],
    functions: FunctionRegistry,
    call_stack: frozenset[int],
    visited: set[int],
    call: ast.Call | None = None,
) -> None:
    scope, definition_environment, definition_bundles, captured_defaults, default_aliases = binding
    identity = id(scope)
    if identity in call_stack:
        return
    visited.add(identity)
    environment = dict(inherited_environment)
    bundles = dict(inherited_bundles)
    for name in _local_binding_names(scope):
        environment.pop(name, None)
        bundles.pop(name, None)
    entry_inherited_values = {
        name: list(variants) for name, variants in environment.items()
    }
    local_functions = _copy_registry(functions)
    initial_function_ids = {
        id(function[0])
        for bindings in local_functions.values()
        for function in bindings
    }
    parameters = scope.args.posonlyargs + scope.args.args
    for parameter, variants in captured_defaults.items():
        environment[parameter] = list(variants)
    argument_aliases: dict[str, set[str]] = {
        parameter: set(names) for parameter, names in default_aliases.items()
    }
    if call is not None:
        for parameter, argument in zip(parameters, call.args):
            environment[parameter.arg] = _sequence_variants(argument, inherited_environment)
            bundle = _command_bundle(argument, inherited_environment)
            if bundle is not None:
                bundles[parameter.arg] = bundle
            if isinstance(argument, ast.Name):
                argument_aliases[parameter.arg] = {argument.id}
            else:
                argument_aliases.pop(parameter.arg, None)
        parameter_names = {parameter.arg for parameter in parameters + scope.args.kwonlyargs}
        for keyword in call.keywords:
            if keyword.arg in parameter_names:
                environment[keyword.arg] = _sequence_variants(keyword.value, inherited_environment)
                bundle = _command_bundle(keyword.value, inherited_environment)
                if bundle is not None:
                    bundles[keyword.arg] = bundle
                if isinstance(keyword.value, ast.Name):
                    argument_aliases[keyword.arg] = {keyword.value.id}
                else:
                    argument_aliases.pop(keyword.arg, None)
    entry_parameter_values = {
        parameter: list(environment[parameter])
        for parameter in argument_aliases
        if parameter in environment
    }
    final_environment, final_bundles = _process_statements(
        scope.body, environment, bundles, lines,
        local_functions, call_stack | {identity}, visited,
    )
    local_names = _local_binding_names(scope)
    propagated = {
        name
        for node in _scope_nodes(scope)
        if isinstance(node, ast.Global)
        for name in node.names
    }
    propagated.update(
        node.value.func.value.id
        for node in _scope_nodes(scope)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.attr in {"append", "extend"}
        and node.value.func.value.id not in local_names
    )
    propagated.update(
        name
        for name, entry_value in entry_inherited_values.items()
        if name in final_environment and final_environment[name] != entry_value
    )
    for name in propagated:
        if name in final_environment:
            inherited_environment[name] = final_environment[name]
        if name in final_bundles:
            inherited_bundles[name] = final_bundles[name]
    parameter_names = set(argument_aliases)
    mutated_parameters = {
        node.target.id
        for node in _scope_nodes(scope)
        if isinstance(node, ast.AugAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id in parameter_names
    }
    mutated_parameters.update(
        node.value.func.value.id
        for node in _scope_nodes(scope)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.attr in {"append", "extend"}
        and node.value.func.value.id in parameter_names
    )
    assigned_parameters = {
        target.id
        for node in _scope_nodes(scope)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id in parameter_names
    }
    assigned_parameters.update(
        node.target.id
        for node in _scope_nodes(scope)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id in parameter_names
    )
    pre_assignment_effects: dict[str, Variants] = {}
    lexical_nodes = sorted(
        _scope_nodes(scope), key=lambda node: (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))
    )
    for parameter in parameter_names:
        assignment_positions = [
            (node.lineno, node.col_offset)
            for node in lexical_nodes
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == parameter for target in node.targets)
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == parameter
            )
        ]
        if not assignment_positions or parameter not in entry_parameter_values:
            continue
        first_assignment = min(assignment_positions)
        effect = list(entry_parameter_values[parameter])
        observed_mutation = False
        for node in lexical_nodes:
            if (getattr(node, "lineno", 0), getattr(node, "col_offset", 0)) >= first_assignment:
                break
            addition: Variants | None = None
            append_mode = False
            if (
                isinstance(node, ast.AugAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == parameter
                and isinstance(node.op, ast.Add)
            ):
                addition = _sequence_variants(node.value, environment)
            elif (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and isinstance(node.value.func.value, ast.Name)
                and node.value.func.value.id == parameter
                and node.value.func.attr in {"append", "extend"}
                and len(node.value.args) == 1
            ):
                addition = _sequence_variants(node.value.args[0], environment)
                append_mode = node.value.func.attr == "append"
            if addition is not None:
                if append_mode:
                    addition = [
                        (variant[0] if len(variant) == 1 else "<dynamic-append>",)
                        for variant in addition
                    ]
                effect = _combine_variants(effect, addition)
                observed_mutation = True
        if observed_mutation:
            pre_assignment_effects[parameter] = effect
    mutated_parameters.update(
        parameter
        for parameter, entry_value in entry_parameter_values.items()
        if parameter in final_environment and final_environment[parameter] != entry_value
    )
    for parameter, caller_names in argument_aliases.items():
        if parameter not in mutated_parameters:
            continue
        propagated_value = pre_assignment_effects.get(parameter)
        if parameter in assigned_parameters and propagated_value is None:
            continue
        if propagated_value is None:
            propagated_value = final_environment.get(parameter)
        for caller_name in caller_names:
            if propagated_value is not None:
                inherited_environment[caller_name] = propagated_value
            if parameter in final_bundles:
                inherited_bundles[caller_name] = final_bundles[parameter]
    for bindings in local_functions.values():
        for nested in bindings:
            if id(nested[0]) not in initial_function_ids and id(nested[0]) not in visited:
                _scan_function(
                    nested, final_environment, final_bundles, lines,
                    local_functions, call_stack | {identity}, visited,
                )


def _isolated_python_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    functions: FunctionRegistry = {}
    visited: set[int] = set()
    module_environment, module_bundles = _process_statements(
        tree.body, {}, {}, lines, functions, frozenset(), visited
    )
    for bindings in functions.values():
        for binding in bindings:
            if id(binding[0]) not in visited:
                _scan_function(
                    binding, module_environment, module_bundles, lines,
                    functions, frozenset(), visited,
                )
    return lines


def _detector_smoketest() -> None:
    cases = [
        ("import subprocess, sys\nsubprocess.run([sys.executable, '-I', 'x.py'])\n", 1),
        ("import subprocess, sys\ncmd=[sys.executable]\ncmd += ['-I']\nsubprocess.run(cmd)\n", 1),
        ("import subprocess, sys\ncmd=[sys.executable]; cmd += ['-I']; subprocess.run(cmd)\n", 1),
        ("import subprocess, sys\nflags=['-I']\ncmd=[sys.executable,*flags]\nsubprocess.run(cmd)\n", 1),
        ("import subprocess, sys\nflags=['-I']; cmd=[sys.executable,*flags]; subprocess.run(cmd)\n", 1),
        ("import subprocess, sys\nsubprocess.run([sys.executable] + (['-I'] if True else []) + ['x.py'])\n", 1),
        ("import sys\ntemplate=[sys.executable, '-I']\n", 0),
        ("import subprocess, sys\nsubprocess.run([sys.executable, '-I'] + ['-B', 'x.py'])\n", 0),
        ("import subprocess, sys\ncmd=[sys.executable, '-I']; cmd.append('-B'); subprocess.run(cmd)\n", 0),
        ("import subprocess, sys\ncmd=[sys.executable]; cmd.extend(['-I']); subprocess.run(cmd)\n", 1),
        (
            "import os, subprocess, sys\ncmd=[sys.executable, '-I']\nif os.name == 'nt':\n cmd=[sys.executable, '-I', '-B']\nsubprocess.run(cmd)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I']\ndef main():\n subprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef main():\n CMD.extend(['-I'])\n subprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I']\ndef main():\n CMD.append('-B')\n subprocess.run(CMD)\n",
            0,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef main():\n global CMD\n CMD += ['-I']\n subprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\ndef main():\n subprocess.run(CMD)\nCMD=[sys.executable, '-I']\nmain()\n",
            1,
        ),
        (
            "import subprocess, sys\ndef main():\n subprocess.run(CMD)\nCMD=[sys.executable]\nCMD.append('-I')\nmain()\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I']\ndef main():\n subprocess.run(CMD)\nmain()\nCMD=[sys.executable, '-I', '-B']\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I', '-B']\ndef main():\n subprocess.run(CMD)\nmain()\nCMD=[sys.executable, '-I']\n",
            0,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I']\ndef main():\n subprocess.run(CMD)\nmain()\nCMD.append('-B')\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I', '-B']\ndef main():\n subprocess.run(CMD)\nmain()\nCMD.append('-I')\n",
            0,
        ),
        (
            "import subprocess, sys\ndef outer():\n cmd=[sys.executable, '-I']\n def inner():\n  subprocess.run(cmd)\n inner()\nouter()\n",
            1,
        ),
        (
            "import subprocess, sys\ndef launch(cmd):\n subprocess.run(cmd)\nlaunch([sys.executable, '-I'])\n",
            1,
        ),
        (
            "import subprocess, sys\ndef launch(cmd):\n subprocess.run(cmd)\nlaunch([sys.executable, '-I', '-B'])\n",
            0,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef configure():\n global CMD\n CMD += ['-I']\nconfigure()\nsubprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\ndef outer():\n cmd=[sys.executable, '-I']\n def dormant():\n  subprocess.run(cmd)\nouter()\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I']\ndef main():\n subprocess.run(CMD)\nrun=main\nrun()\nCMD=[sys.executable, '-I', '-B']\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I', '-B']\ndef main():\n subprocess.run(CMD)\nrun=main\nrun()\nCMD=[sys.executable, '-I']\n",
            0,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I']\ndef launch(cmd=CMD):\n subprocess.run(cmd)\nCMD=[sys.executable, '-I', '-B']\nlaunch()\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I', '-B']\ndef launch(cmd=CMD):\n subprocess.run(cmd)\nCMD=[sys.executable, '-I']\nlaunch()\n",
            0,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef launch(cmd=CMD):\n subprocess.run(cmd)\nCMD.append('-I')\nlaunch()\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef configure(cmd=CMD):\n cmd.append('-I')\nconfigure()\nsubprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\nALIAS=CMD\ndef launch(cmd=CMD):\n subprocess.run(cmd)\nCMD=[sys.executable, '-I', '-B']\nALIAS.append('-I')\nlaunch()\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I', '-B']\ndef launch(cmd=CMD):\n subprocess.run(cmd)\nCMD=[sys.executable]\nCMD.append('-I')\nlaunch()\n",
            0,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef configure(*, cmd=CMD):\n cmd.extend(['-I'])\nconfigure()\nsubprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\ncmd=[sys.executable, '-I']\ndef configure(value):\n value=[sys.executable, '-I', '-B']\nconfigure(cmd)\nsubprocess.run(cmd)\n",
            1,
        ),
        (
            "import subprocess, sys\ncmd=[sys.executable, '-I', '-B']\ndef configure(value):\n value=[sys.executable, '-I']\nconfigure(cmd)\nsubprocess.run(cmd)\n",
            0,
        ),
        (
            "import subprocess, sys\ncmd=[sys.executable]\ndef configure(value):\n value.append('-I')\n value=[sys.executable, '-I', '-B']\nconfigure(cmd)\nsubprocess.run(cmd)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef configure():\n CMD.append('-I')\nconfigure()\nsubprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef configure(target):\n target.extend(['-I'])\nconfigure(CMD)\nsubprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef mutate(target):\n target.append('-I')\ndef configure(target):\n mutate(target)\nconfigure(CMD)\nsubprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable]\ndef mutate():\n CMD.append('-I')\ndef configure():\n mutate()\nconfigure()\nsubprocess.run(CMD)\n",
            1,
        ),
        (
            "import subprocess, sys\nCMD=[sys.executable, '-I']\ndef unsafe():\n subprocess.run(CMD)\ndef safe():\n subprocess.run([sys.executable, '-I', '-B'])\nif condition:\n run=unsafe\nelse:\n run=safe\nrun()\nCMD=[sys.executable, '-I', '-B']\n",
            1,
        ),
        (
            "import subprocess, sys\nclass Runner:\n def launch(self):\n  subprocess.run([sys.executable, '-I'])\nRunner().launch()\n",
            1,
        ),
        (
            "import subprocess, sys\ncmd=[sys.executable, '-I']\nif condition:\n cmd=[sys.executable, '-I', '-B']\nelse:\n cmd=[sys.executable, '-S', '-B']\nsubprocess.run(cmd)\n",
            0,
        ),
        (
            "import subprocess, sys\ncmd=[sys.executable]\nif condition:\n cmd.append('-I')\n cmd.append('-B')\nsubprocess.run(cmd)\n",
            0,
        ),
        (
            "import sys\ndef check(runner):\n commands=([sys.executable, '-I', 'x.py'],)\n for command in commands:\n  runner(command)\n",
            1,
        ),
        (
            "import sys\ndef check(runner):\n commands=([sys.executable, '-I', '-B', 'x.py'],)\n for command in commands:\n  runner(command)\n",
            0,
        ),
    ]
    observed = [len(_isolated_python_lines(ast.parse(source))) for source, _ in cases]
    expected = [count for _, count in cases]
    mismatches = [
        (index, observed[index], expected[index], cases[index][0])
        for index in range(len(cases))
        if observed[index] != expected[index]
    ]
    assert not mismatches, mismatches


def violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for line in sorted(_isolated_python_lines(tree)):
        found.append(
            f"{path.relative_to(ROOT)}:{line}: isolated Python command lacks -B bytecode suppression"
        )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        api = _subprocess_api(node)
        if api is not None:
            keywords = _keyword_map(node)
            text_mode = _true(keywords.get("text")) or _true(keywords.get("universal_newlines"))
            if text_mode:
                encoding = _constant_string(keywords.get("encoding"))
                errors = _constant_string(keywords.get("errors"))
                utf8 = encoding is not None and encoding.lower().replace("_", "-") in {"utf-8", "utf8"}
                locale_mklink = _is_cmd_mklink(node) and _preferred_locale_call(keywords.get("encoding"))
                if not (utf8 or locale_mklink):
                    found.append(f"{path.relative_to(ROOT)}:{node.lineno}: subprocess.{api} text mode lacks encoding='utf-8'")
                if errors not in ALLOWED_ERRORS:
                    found.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: subprocess.{api} text mode lacks errors='replace' or 'strict'"
                    )

        if _explicit_utf8_decode(node):
            keywords = _keyword_map(node)
            positional_errors = _constant_string(node.args[1]) if len(node.args) > 1 else None
            errors = positional_errors or _constant_string(keywords.get("errors"))
            if errors not in ALLOWED_ERRORS:
                found.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}: decode('utf-8') lacks explicit errors='replace' or 'strict'"
                )
    return found


def main() -> int:
    _detector_smoketest()
    failures: list[str] = []
    files = sorted(SCRIPTS.rglob("*.py"))
    for path in files:
        failures.extend(violations(path))
    if failures:
        print(f"FAIL: {len(failures)} deterministic text-decoding policy violation(s)")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"PASS: deterministic text-decoding policy ({len(files)} Python files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
