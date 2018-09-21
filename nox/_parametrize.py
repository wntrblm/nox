# Copyright 2017 Alethea Katherine Flowers
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

import functools


class param:
    def __init__(self, *values, run_by_default=None):
        self.values = values
        self.run_by_default = run_by_default


def parametrize_decorator(arg_names, arg_values_list):
    """Parametrize a session.

    Add new invocations to the underlying session function using the list of
    ``arg_values_list`` for the given ``arg_names``. Parametrization is
    performed during session discovery and each invocation appears as a
    separate session to nox.

    Args:
        arg_names (Sequence[str]): A list of argument names.
        arg_values_list (Sequence[Union[Any, Tuple]]): The list of argument
            values determines how often a session is invoked with different
            argument values. If only one argument names was specified then
            this is a simple list of values, for example ``[1, 2, 3]``. If N
            argument names were specified, this must be a list of N-tuples,
            where each tuple-element specifies a value for its respective
            argument name, for example ``[(1, 'a'), (2, 'b')]``.
    """

    # Allow args to be specified as any of 'arg', 'arg,arg2' or ('arg', 'arg2')
    if not isinstance(arg_names, (list, tuple)):
        arg_names = list(filter(None, [arg.strip() for arg in arg_names.split(",")]))

    # If there's only one arg_name, arg_values_list should be a single item
    # or list. Transform it so it'll work with the combine step.
    if len(arg_names) == 1:
        # In this case, the arg_values_list can also just be a single item.
        if not isinstance(arg_values_list, (list, tuple, param)):
            arg_values_list = [arg_values_list]
        arg_values_list = [
            [value] if not isinstance(value, param) else value
            for value in arg_values_list
        ]

    # Combine arg names and values into a list of dictionaries. These are
    # 'call specs' that will be used to generate calls.
    # [{arg: value1}, {arg: value2}, ...]
    call_specs = []
    for arg_values in arg_values_list:
        call_specs.append(CallSpec.make_call_spec(arg_names, arg_values))

    def inner(f):
        previous_call_specs = getattr(f, "parametrize", None)
        new_call_specs = update_call_specs(previous_call_specs, call_specs)
        setattr(f, "parametrize", new_call_specs)
        return f

    return inner


def update_call_specs(call_specs, new_specs):
    if not call_specs:
        call_specs = [CallSpec({})]

    combined_specs = []
    for new_spec in new_specs:
        for spec in call_specs:
            combined_specs.append(spec.combine(new_spec))
    return combined_specs


def generate_session_signature(func, call_spec):
    args = [
        "{}={}".format(k, repr(call_spec.kwargs[k]))
        for k in sorted(call_spec.kwargs.keys())
    ]
    return "({})".format(", ".join(args))


def generate_calls(func, call_specs):
    calls = []
    for call_spec in call_specs:

        def make_call_wrapper(call_spec):
            @functools.wraps(func)
            def call_wrapper(*args, **kwargs):
                kwargs.update(call_spec.kwargs)
                return func(*args, **kwargs)

            return call_wrapper

        call = make_call_wrapper(call_spec)
        call.session_signature = generate_session_signature(func, call_spec)
        call.call_spec = call_spec
        call.run_by_default = call_spec.run_by_default
        calls.append(call)

    return calls


class CallSpec:
    def __init__(self, kwargs, run_by_default=None):
        self.kwargs = kwargs
        self.run_by_default = run_by_default

    def combine(self, call_spec):
        """Combines two CallSpec objects into one.
        Returns a new CallSpec object.

        Args:
            call_spec (CallSpec):
                The call spec to combine arguments
                and other parameters with the current
                CallSpec instance.

        Returns:
            CallSpec: A newly-combined CallSpec instance.
        """
        kwargs = self.kwargs.copy()
        kwargs.update(call_spec.kwargs)

        if call_spec.run_by_default is not None:
            run_by_default = call_spec.run_by_default
        elif self.run_by_default is not None:
            run_by_default = self.run_by_default
        else:
            run_by_default = None

        return CallSpec(kwargs, run_by_default=run_by_default)

    @classmethod
    def make_call_spec(cls, arg_names, arg_values):
        """Creates a CallSpec instance"""
        if isinstance(arg_values, param):
            return cls(
                dict(zip(arg_names, arg_values.values)),
                run_by_default=arg_values.run_by_default,
            )
        return cls(dict(zip(arg_names, arg_values)))
