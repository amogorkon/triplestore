from hypothesis import given  # noqa: F401
from hypothesis import strategies as st  # noqa: F401
from triplestore.classes import E  # noqa: F401


if __name__ == "__main__":
    for test in globals().copy():
        if test.startswith("test_"):
            globals()[test]()
