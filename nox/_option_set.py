# Copyright 2019 Alethea Katherine Flowers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Machinery for statically-defined option models.

Options are declared once as fields on attrs classes (see ``nox._options``),
carrying CLI metadata in an :class:`Opt` record. Everything else is derived
from the model: the argparse parser, environment-variable handling, the
noxfile/CLI merge, and serialization back to an argument list (:func:`to_argv`)
for spawning child ``nox`` processes.
"""

from __future__ import annotations

__lazy_modules__ = {"argcomplete", "argparse", "types"}

import argparse
import enum
import os
import types
import typing
from argparse import ArgumentError, ArgumentParser, Namespace
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar

import argcomplete
import attrs

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

__all__ = [
    "ArgumentError",
    "Forward",
    "NoxOptions",  # noqa: F822 (provided lazily by __getattr__)
    "Opt",
    "Options",
    "OptionsBase",
    "Source",
    "opt",
    "to_argv",
]


def __dir__() -> list[str]:
    return __all__


def __getattr__(name: str) -> Any:
    # Compatibility alias; NoxOptions was defined here before the model moved.
    if name == "NoxOptions":
        from nox._options import NoxfileOptions  # noqa: PLC0415

        return NoxfileOptions
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


METADATA_KEY = "nox_opt"

ConfigT = TypeVar("ConfigT", bound="OptionsBase")


class Source(enum.IntEnum):
    """Where a value came from; higher-ranked sources win during merging."""

    DEFAULT = 0
    NOXFILE = 1
    ENVIRONMENT = 2
    COMMAND_LINE = 3


class Forward(enum.Enum):
    """How :func:`to_argv` treats an option when rebuilding an argument list.

    NEVER: not forwarded (presentation-only options, or aliases whose state
    lives in another field). IF_CHANGED: emitted when the value differs from
    the field default. ALWAYS: emitted unconditionally (flag pairs and options
    whose defaults are environment-dependent, so children stay deterministic).
    """

    NEVER = enum.auto()
    IF_CHANGED = enum.auto()
    ALWAYS = enum.auto()


@attrs.frozen(kw_only=True)
class Opt:
    """CLI metadata attached to a model field via ``attrs.field(metadata=...)``.

    Args:
        flags: The argparse flags (e.g. ``-s``, ``--sessions``). The last flag
            is the canonical one used when serializing back to argv.
        group: Key into the option set's group table. Required unless hidden.
        help: The argparse help string.
        negative_flags: If non-empty, this is a flag pair; these flags
            ``store_false`` into the same field.
        env_var: Environment variable providing the value when the flag is not
            passed (comma-split for list-typed fields).
        hidden: Present on the config object but not exposed on the CLI.
        positional: A positional argument (only ``posargs``).
        completer: argcomplete completer.
        forward: See :class:`Forward`.
        serialize: Custom argv emitter; receives the value, returns the argv
            chunk or None to skip. Overrides the generic emission; runs after
            the ``forward`` policy has been applied.
        argparse_kwargs: Extra/overriding kwargs for ``add_argument``.
    """

    flags: tuple[str, ...] = ()
    group: str | None = None
    help: str | None = None
    negative_flags: tuple[str, ...] = ()
    env_var: str | None = None
    hidden: bool = False
    positional: bool = False
    completer: Callable[..., Iterable[str]] | None = None
    forward: Forward = Forward.IF_CHANGED
    serialize: Callable[[Any], list[str] | None] | None = None
    argparse_kwargs: dict[str, Any] = attrs.field(factory=dict)


def opt(*flags: str, **kwargs: Any) -> dict[str, Opt]:
    """Build the metadata dict for an option field."""
    return {METADATA_KEY: Opt(flags=flags, **kwargs)}


def _get_opt(field: attrs.Attribute[Any]) -> Opt | None:
    return field.metadata.get(METADATA_KEY)


@attrs.define(kw_only=True)
class OptionsBase:
    """Base for option models; tracks the provenance of each field's value.

    ``attrs.evolve`` builds the copy through ``__init__``, so the copy's
    provenance resets to ``Source.DEFAULT`` for every field.
    """

    _provenance: dict[str, Source] = attrs.field(
        init=False, factory=dict, repr=False, eq=False
    )

    def provenance(self, name: str) -> Source:
        if name not in attrs.fields_dict(type(self)):
            msg = f"{name} is not an option."
            raise KeyError(msg)
        return self._provenance.get(name, Source.DEFAULT)

    def set_value(self, name: str, value: Any, source: Source) -> None:
        """Set a field and record where the value came from."""
        setattr(self, name, value)
        self._provenance[name] = source


def record_noxfile_set(
    instance: OptionsBase, field: attrs.Attribute[Any], value: Any
) -> Any:
    """on_setattr hook: record plain assignments (``nox.options.x = ...``)."""
    if not field.name.startswith("_"):
        instance._provenance[field.name] = Source.NOXFILE
    return value


def _analyze_type(tp: Any) -> tuple[str, tuple[Any, ...] | None]:
    """Classify a field type for argparse.

    Returns a kind (``"flag"``, ``"list"``, or ``"value"``) and Literal
    choices, if any.
    """
    origin = typing.get_origin(tp)
    if origin in {typing.Union, types.UnionType}:
        non_none = [a for a in typing.get_args(tp) if a is not type(None)]
        if len(non_none) == 1:
            return _analyze_type(non_none[0])
        return ("value", None)
    if origin is Literal:
        return ("value", typing.get_args(tp))
    if tp is bool:
        return ("flag", None)
    if origin in {list, tuple} or tp in {list, tuple}:
        return ("list", None)
    return ("value", None)


def to_argv(config: OptionsBase) -> list[str]:
    """Serialize a config back into the CLI arguments that reproduce it.

    The output, parsed and finalized again, restores every forwardable value.
    Options marked ``Forward.NEVER`` are skipped; new options are forwarded by
    default. Positional arguments (posargs) are emitted last, after ``--``.
    """
    argv: list[str] = []
    tail: list[str] = []
    defaults = type(config)()
    for field in attrs.fields(type(config)):
        option = _get_opt(field)
        if option is None or option.forward is Forward.NEVER:
            continue
        value = getattr(config, field.name)
        if option.positional:
            if value:
                tail = ["--", *(str(v) for v in value)]
            continue
        if option.forward is Forward.IF_CHANGED and value == getattr(
            defaults, field.name
        ):
            continue
        choices = option.argparse_kwargs.get("choices")
        if choices is not None and value not in choices:
            # Values the CLI grammar can't express (e.g. the noxfile-only
            # "uv|virtualenv" fallback syntax); the child re-derives them.
            continue
        if option.serialize is not None:
            argv += option.serialize(value) or []
            continue
        if option.negative_flags:
            argv.append(option.flags[-1] if value else option.negative_flags[-1])
            continue
        flag = option.flags[-1]
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        elif isinstance(value, (list, tuple)):
            if value:
                argv += [flag, *(str(v) for v in value)]
        elif value is not None:
            argv += [flag, str(value)]
    return argv + tail


def apply_noxfile_values(
    config: OptionsBase, noxfile_config: OptionsBase, *, skip: Iterable[str] = ()
) -> None:
    """Copy fields set in the noxfile into the config where nothing outranks them."""
    skip = set(skip)
    for field in attrs.fields(type(noxfile_config)):
        name = field.name
        if _get_opt(field) is None or name in skip:
            continue
        if noxfile_config.provenance(name) is Source.DEFAULT:
            continue
        if config.provenance(name) is Source.DEFAULT:
            config.set_value(name, getattr(noxfile_config, name), Source.NOXFILE)


class Options(Generic[ConfigT]):
    """The full option set: builds the parser and config objects from the model.

    Args:
        config_class: The attrs class holding every option (the CLI surface).
        groups: Mapping of group key to (title, description) for ``--help``.
        description: The parser description.
        finalize: Called with the fresh config after parsing, before returning;
            resolves aliases and cross-field options. ``ArgumentError`` raised
            here is reported via ``parser.error``.
    """

    def __init__(
        self,
        config_class: type[ConfigT],
        *,
        groups: dict[str, tuple[str, str]],
        description: str,
        finalize: Callable[[Any], None] | None = None,
    ) -> None:
        self.config_class = config_class
        self.groups = groups
        self.description = description
        self.finalize = finalize
        attrs.resolve_types(config_class)

    def _argparse_kwargs(
        self, field: attrs.Attribute[Any], option: Opt
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        kind, choices = _analyze_type(field.type)
        if kind == "flag":
            kwargs["action"] = "store_true"
        elif kind == "list":
            kwargs["nargs"] = "*"
        if choices:
            kwargs["choices"] = list(choices)
        kwargs.update(option.argparse_kwargs)
        return kwargs

    def parser(self) -> ArgumentParser:
        """Build the ``ArgumentParser`` for the model.

        Parsing is sparse: only flags actually passed appear in the resulting
        namespace (via ``argparse.SUPPRESS``), so provenance is exact.
        """
        parser = argparse.ArgumentParser(
            description=self.description, add_help=False, allow_abbrev=False
        )
        groups = {
            name: parser.add_argument_group(title, description)
            for name, (title, description) in self.groups.items()
        }
        for field in attrs.fields(self.config_class):
            option = _get_opt(field)
            if option is None or option.hidden:
                continue
            if option.group is None:
                msg = f"Option {field.name} must either have a group or be hidden."
                raise ValueError(msg)
            group = groups[option.group]
            if option.positional:
                group.add_argument(
                    field.name,
                    help=option.help,
                    default=[],
                    **option.argparse_kwargs,
                )
                continue
            argument = group.add_argument(
                *option.flags,
                dest=field.name,
                help=option.help,
                default=argparse.SUPPRESS,
                **self._argparse_kwargs(field, option),
            )
            if option.completer:
                argument.completer = option.completer  # type: ignore[attr-defined]
            if option.negative_flags:
                group.add_argument(
                    *option.negative_flags,
                    dest=field.name,
                    action="store_false",
                    default=argparse.SUPPRESS,
                    help=f"Disables {option.flags[-1]} if it is enabled in the Noxfile.",
                )
        return parser

    def print_help(self) -> None:
        self.parser().print_help()

    def expand(self, namespace: Namespace | ConfigT) -> ConfigT:
        """Build a full config from a sparse argparse namespace.

        Values present in the namespace were passed on the command line;
        everything else falls back to the environment variable (if declared)
        and then the field default. A config passed in (e.g. from
        :meth:`namespace` in tests) is returned unchanged.
        """
        if isinstance(namespace, self.config_class):
            return namespace
        sparse = vars(namespace)
        config = self.config_class()
        for field in attrs.fields(self.config_class):
            option = _get_opt(field)
            if option is None:
                continue
            if field.name in sparse:
                value = sparse[field.name]
                # argparse always fills positionals in; empty means not given.
                if option.positional and not value:
                    continue
                config.set_value(field.name, value, Source.COMMAND_LINE)
            elif option.env_var and (env_value := os.environ.get(option.env_var)):
                kind, _ = _analyze_type(field.type)
                value = env_value.split(",") if kind == "list" else env_value
                config.set_value(field.name, value, Source.ENVIRONMENT)
        return config

    def parse_args(self, args: list[str] | None = None) -> ConfigT:
        parser = self.parser()
        argcomplete.autocomplete(parser)
        namespace = parser.parse_args(args)
        try:
            config = self.expand(namespace)
        except ValueError as err:
            # Bad environment-variable values fail their field validator.
            parser.error(str(err.args[0]) if err.args else str(err))
        try:
            if self.finalize is not None:
                self.finalize(config)
        except ArgumentError as err:
            parser.error(str(err))
        return config

    def namespace(self, **kwargs: Any) -> ConfigT:
        """Return a config with every option at its default.

        kwargs set values in a checked way - you can not set an option that
        does not exist. This is useful for testing.
        """
        fields = attrs.fields_dict(self.config_class)
        config = self.config_class()
        for key, value in kwargs.items():
            if key not in fields or _get_opt(fields[key]) is None:
                msg = f"{key} is not an option."
                raise KeyError(msg)
            config.set_value(key, value, Source.COMMAND_LINE)
        return config
