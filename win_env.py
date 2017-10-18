import os


def main():
    for key in sorted(os.environ):
        value = os.environ[key]
        print('{} = {}'.format(key, value))


if __name__ == '__main__':
    main()
