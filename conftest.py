import contextlib
import uuid
from pathlib import Path
from typing import Generator

import pytest
from triplestore.classes import TripleStore

index_dir = Path(__file__).parent / "tests/tmp"
index_dir.mkdir(exist_ok=True)
index_path = index_dir / "bplustree-testfile.index"


@pytest.fixture
def clean_file(tmp_path) -> Generator[Path, None, None]:
    unique_index_path = tmp_path / f"bplustree-testfile-{uuid.uuid4()}.index"
    wal_path = unique_index_path.with_name(f"{unique_index_path.name}-wal")

    yield unique_index_path

    # Ensure the file is closed before attempting to delete it
    with contextlib.suppress(PermissionError):
        if unique_index_path.is_file():
            unique_index_path.unlink()
        if wal_path.is_file():
            wal_path.unlink()
    for file in tmp_path.glob("bplustree-testfile-*.index*"):
        with contextlib.suppress(PermissionError):
            file.unlink()


@pytest.fixture
def store():
    return TripleStore(kv_store={}, relations={})
