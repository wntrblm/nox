

def parametrize_decorator(arg_names, arg_values_list):

    # Allow args to be specified as any of 'arg', 'arg,arg2' or ('arg', 'arg2')
    if not isinstance(arg_names, (list, tuple)):
        arg_names = list(
            filter(None, [arg.strip() for arg in arg_names.split(',')]))

    # If there's only one arg_name, arg_values_list should be a single item
    # or list. Transform it so it'll work with the combine step.
    if len(arg_names) == 1:
        # In this case, the arg_values_list can also just be a single item.
        if not isinstance(arg_values_list, (list, tuple)):
            arg_values_list = [arg_values_list]
        arg_values_list = [[value] for value in arg_values_list]

    # Combine arg names and values into a list of dictionaries. These are
    # 'call specs' that will be used to generate calls.
    # [{arg: value1}, {arg: value2}, ...]
    call_specs = []
    for arg_values in arg_values_list:
        call_spec = dict(zip(arg_names, arg_values))
        call_specs.append(call_spec)

    def inner(f):
        previous_call_specs = getattr(f, 'parametrize', None)
        new_call_specs = update_call_specs(
            previous_call_specs, call_specs)
        setattr(f, 'parametrize', new_call_specs)
        return f

    return inner


def update_call_specs(call_specs, new_specs):
    if not call_specs:
        call_specs = [{}]

    combined_specs = []
    for new_spec in new_specs:
        for spec in call_specs:
            spec = spec.copy()
            spec.update(new_spec)
            combined_specs.append(spec)
    return combined_specs


def generate_session_signature(func, call_spec):
    args = [
        '{}={}'.format(k, repr(call_spec[k]))
        for k in sorted(call_spec.keys())]
    return '({})'.format(', '.join(args))


def generate_calls(func, call_specs):
    calls = []
    for call_spec in call_specs:

        def make_call_wrapper(call_spec):
            def call_wrapper(*args, **kwargs):
                kwargs.update(call_spec)
                return func(*args, **kwargs)
            return call_wrapper

        call = make_call_wrapper(call_spec)
        call.session_signature = generate_session_signature(func, call_spec)
        call.call_spec = call_spec
        calls.append(call)

    return calls
