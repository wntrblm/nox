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

"""High-level options interface. This allows defining options just once that
can be specified from the command line and the noxfile, easily used in tests,
and surfaced in documentation."""


import argparse
import collections
import functools


Namespace = argparse.Namespace
ArgumentError = argparse.ArgumentError


class Option:
    """A single option that can be specified via command-line or configuration
    file.

    Args:
        name (str): The name used to refer to the option in the final namespace
            object.
        flags (Sequence[str]): The list of flags used by argparse. Effectively
            the ``*args`` for ``ArgumentParser.add_argument``.
        help (str): The help string pass to argparse.
        group (str): The argument group this option belongs to, if any.
        noxfile (str): Whether or not this option can be set in the
            configuration file.
        merge_func (Callable[[Namespace, Namespace], Any]): A function that
            can define custom behavior when merging the command-line options
            with the configuration file options. The first argument is the
            command-line options, the second is the configuration file options.
            It should return the new value for the option.
        finalizer_func (Callable[Any, Namespace], Any): A function that can
            define custom finalization behavior. This is called after all
            arguments are parsed. It's called with the options parsed value
            and the set of command-line options and should return the new
            value.
        default (Union[Any, Callable[[], Any]]): The default value. It may
            also be a function in which case it will be invoked after argument
            parsing if nothing was specified.
        hidden (bool): Means this option will be present in the namespace, but
            will not show up on the argument list.
        kwargs: Passed through to``ArgumentParser.add_argument``.
    """

    def __init__(
        self,
        name,
        *flags,
        help=None,
        group=None,
        noxfile=False,
        merge_func=None,
        finalizer_func=None,
        default=None,
        hidden=False,
        **kwargs
    ):
        self.name = name
        self.flags = flags
        self.help = help
        self.group = group
        self.noxfile = noxfile
        self.merge_func = merge_func
        self.finalizer_func = finalizer_func
        self.hidden = hidden
        self.kwargs = kwargs
        self._default = default

    @property
    def default(self):
        if callable(self._default):
            return self._default()
        return self._default


def flag_pair_merge_func(enable_name, disable_name, command_args, noxfile_args):
    """Merge function for flag pairs. If the flag is set in the noxfile or
    the command line params, return ``True`` *unless* the disable flag has been
    specified on the command-line.

    For example, assuming you have a flag pair created using::

        make_flag_pair(
            "thing_a",
            "--thing-a",
            "--no-thing-a"
        )

    Then if the Noxfile says::

        nox.options.thing_a = True

    But the command line says::

        nox --no-thing-a

    Then the result will be ``False``.

    However, without the "--no-thing-a" flag set then this returns ``True`` if
    *either*::

        nox.options.thing_a = True

    or::

        nox --thing-a

    are specified.
    """
    noxfile_value = getattr(noxfile_args, enable_name)
    command_value = getattr(command_args, enable_name)
    disable_value = getattr(command_args, disable_name)

    return (command_value or noxfile_value) and not disable_value


def make_flag_pair(name, enable_flags, disable_flags, **kwargs):
    """Returns two options - one to enable a behavior and another to disable it.

    The positive option is considered to be available to the noxfile, as
    there isn't much point in doing flag pairs without it.
    """
    disable_name = "no_{}".format(name)

    kwargs["action"] = "store_true"
    enable_option = Option(
        name,
        *enable_flags,
        noxfile=True,
        merge_func=functools.partial(flag_pair_merge_func, name, disable_name),
        **kwargs
    )

    kwargs["help"] = "Disables {} if it is enabled in the Noxfile.".format(
        enable_flags[-1]
    )
    disable_option = Option(disable_name, *disable_flags, **kwargs)

    return enable_option, disable_option


class OptionSet:
    """A set of options.

    A high-level wrapper over ``argparse.ArgumentParser``. It allows for
    introspection of options as well as quality-of-life features such as
    finalization, callable defaults, and strongly typed namespaces for tests.
    """

    def __init__(self, *args, **kwargs):
        self.parser_args = args
        self.parser_kwargs = kwargs
        self.options = collections.OrderedDict()
        self.groups = collections.OrderedDict()

    def add_options(self, *args):
        """Adds a sequence of Options to the OptionSet.

        Args:
            args (Sequence[Options])
        """
        for option in args:
            self.options[option.name] = option

    def add_group(self, name, *args, **kwargs):
        """Adds a new argument group.

        When :fun:`parser` is invoked, the OptionSet will turn all distinct
        argument groups into separate sections in the ``--help`` output using
        ``ArgumentParser.add_argument_group``.
        """
        self.groups[name] = (args, kwargs)

    def _add_to_parser(self, parser, option):
        parser.add_argument(
            *option.flags, help=option.help, default=option.default, **option.kwargs
        )

    def parser(self):
        """Returns an ``ArgumentParser`` for this option set.

        Generally, you won't use this directly. Instead, use
        :func:`parse_args`.
        """
        parser = argparse.ArgumentParser(*self.parser_args, **self.parser_kwargs)

        groups = {
            name: parser.add_argument_group(*args, **kwargs)
            for name, (args, kwargs) in self.groups.items()
        }

        for option in self.options.values():
            if option.hidden:
                continue

            if option.group is not None:
                self._add_to_parser(groups[option.group], option)
            else:
                self._add_to_parser(parser, option)

        return parser

    def print_help(self):
        return self.parser().print_help()

    def _finalize_args(self, args):
        """Does any necessary post-processing on arguments."""
        for option in self.options.values():
            # Handle hidden items.
            if option.hidden and not hasattr(args, option.name):
                setattr(args, option.name, option.default)

            value = getattr(args, option.name)

            # Handle options that have finalizer functions.
            if option.finalizer_func:
                setattr(args, option.name, option.finalizer_func(value, args))

    def parse_args(self):
        parser = self.parser()
        args = parser.parse_args()

        try:
            self._finalize_args(args)
        except ArgumentError as err:
            parser.error(str(err))
        return args

    def namespace(self, **kwargs):
        """Return a namespace that contains all of the options in this set.

        kwargs can be used to set values and does so in a checked way - you
        can not set an option that does not exist in the set. This is useful
        for testing.
        """
        args = {option.name: option.default for option in self.options.values()}

        # Don't use update - validate that the keys actually exist so that
        # we don't accidentally set non-existent options.
        # don't bother with coverage here, this is effectively only ever
        # used in tests.
        for key, value in kwargs.items():
            if key not in args:
                raise KeyError("{} is not an option.".format(key))
            args[key] = value

        return argparse.Namespace(**args)

    def noxfile_namespace(self):
        """Returns a namespace of options that can be set in the configuration
        file."""
        return argparse.Namespace(
            **{
                option.name: option.default
                for option in self.options.values()
                if option.noxfile
            }
        )

    def merge_namespaces(self, command_args, noxfile_args):
        """Merges the command-line options with the noxfile options."""
        for name, option in self.options.items():
            if option.merge_func:
                setattr(
                    command_args, name, option.merge_func(command_args, noxfile_args)
                )
            elif option.noxfile:
                value = getattr(command_args, name, None) or getattr(
                    noxfile_args, name, None
                )
                setattr(command_args, name, value)
