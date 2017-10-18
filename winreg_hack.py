# NOTE: This assumes Python 3.6.

import textwrap
import winreg


VALUE_TYPES = {
    winreg.REG_BINARY: 'REG_BINARY',
    winreg.REG_DWORD: 'REG_DWORD',
    winreg.REG_DWORD_LITTLE_ENDIAN: 'REG_DWORD_LITTLE_ENDIAN',
    winreg.REG_DWORD_BIG_ENDIAN: 'REG_DWORD_BIG_ENDIAN',
    winreg.REG_EXPAND_SZ: 'REG_EXPAND_SZ',
    winreg.REG_LINK: 'REG_LINK',
    winreg.REG_MULTI_SZ: 'REG_MULTI_SZ',
    winreg.REG_NONE: 'REG_NONE',
    winreg.REG_QWORD: 'REG_QWORD',
    winreg.REG_QWORD_LITTLE_ENDIAN: 'REG_QWORD_LITTLE_ENDIAN',
    winreg.REG_RESOURCE_LIST: 'REG_RESOURCE_LIST',
    winreg.REG_FULL_RESOURCE_DESCRIPTOR: 'REG_FULL_RESOURCE_DESCRIPTOR',
    winreg.REG_RESOURCE_REQUIREMENTS_LIST: 'REG_RESOURCE_REQUIREMENTS_LIST',
    winreg.REG_SZ: 'REG_SZ',
}
WIN_SEP = '\\'


def get_key(path):
    parts = path.split(WIN_SEP, 1)
    if parts[0] == 'HKEY_CURRENT_USER':
        base = winreg.HKEY_CURRENT_USER
    elif parts[0] == 'HKEY_LOCAL_MACHINE':
        base = winreg.HKEY_LOCAL_MACHINE
    else:
        raise NotImplementedError(path)

    if len(parts) == 1:
        return base
    else:
        return winreg.OpenKey(base, parts[1])


def tree(key, name):
    parts = []
    num_subkeys, num_values, _ = winreg.QueryInfoKey(key)

    for index in range(num_values):
        val_name, data, reg_type = winreg.EnumValue(key, index)
        reg_type = VALUE_TYPES.get(reg_type, reg_type)
        msg = '{} ({}) = {!r}'.format(val_name, reg_type, data)
        parts.append(msg)

    for index in range(num_subkeys):
        key_name = winreg.EnumKey(key, index)
        sub_key = winreg.OpenKey(key, key_name)
        parts.append(key_name + WIN_SEP)
        sub_part = tree(sub_key, key_name)
        parts.append(textwrap.indent(sub_part, '  '))

    return '\n'.join(parts)


def print_tree(path):
    key = get_key(path)
    to_print = tree(key, path)
    print(path + WIN_SEP)
    print(textwrap.indent(to_print, '  '))


def main():
    paths = (
        r'HKEY_CURRENT_USER\Software\Python\PythonCore',
        r'HKEY_LOCAL_MACHINE\Software\Python\PythonCore',
        r'HKEY_LOCAL_MACHINE\Software\Wow6432Node\Python\PythonCore',
    )
    for path in paths:
        print_tree(path)


if __name__ == '__main__':
    main()
