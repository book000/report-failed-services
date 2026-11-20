import json
import multiprocessing
import os

import pytest

import src


def _add_many(directory, start, count, ready):
    os.chdir(directory)
    ready.wait()
    for number in range(start, start + count):
        src.add_notified_id("{}.service".format(number))


def _hold_run_lock(directory, acquired, release):
    os.chdir(directory)
    with src.state_lock("notified_ids.run.lock"):
        acquired.set()
        release.wait(10)


def _acquire_run_lock(directory, acquired):
    os.chdir(directory)
    with src.state_lock("notified_ids.run.lock"):
        acquired.set()


def test_failed_replace_preserves_previous_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src.save_notified_ids(["original.service"])

    def fail_replace(*args):
        raise OSError("disk error")

    monkeypatch.setattr(src.os, "replace", fail_replace)
    with pytest.raises(OSError):
        src.add_notified_id("new.service")
    assert src.load_notified_ids() == ["original.service"]
    assert not list(tmp_path.glob(".notified_ids.*"))


def test_interrupted_write_preserves_previous_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src.save_notified_ids(["original.service"])

    def fail_dump(value, stream):
        stream.write('["partial')
        raise OSError("disk full")

    monkeypatch.setattr(src.json, "dump", fail_dump)
    with pytest.raises(OSError):
        src.add_notified_id("new.service")
    assert src.load_notified_ids() == ["original.service"]
    assert not list(tmp_path.glob(".notified_ids.*"))


@pytest.mark.parametrize("contents", ["", "[", "{}", '[1]', '["ok", null]', '"text"', '\udcff'])
def test_corrupt_state_is_preserved(tmp_path, monkeypatch, contents):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "notified_ids.json"
    path.write_bytes(contents.encode("utf-8", errors="surrogateescape"))
    original = path.read_bytes()
    with pytest.raises(ValueError, match="restore a valid state file"):
        src.add_notified_id("new.service")
    assert path.read_bytes() == original


def test_competing_processes_keep_all_updates(tmp_path):
    ready = multiprocessing.Event()
    processes = [multiprocessing.Process(target=_add_many, args=(str(tmp_path), i * 20, 20, ready)) for i in range(4)]
    for process in processes:
        process.start()
    ready.set()
    for process in processes:
        process.join(20)
        assert process.exitcode == 0
    state = json.loads((tmp_path / "notified_ids.json").read_text())
    assert set(state) == {"{}.service".format(i) for i in range(80)}
    assert len(state) == 80


def test_run_lock_serializes_processes(tmp_path):
    acquired = multiprocessing.Event()
    release = multiprocessing.Event()
    second_acquired = multiprocessing.Event()
    first = multiprocessing.Process(target=_hold_run_lock, args=(str(tmp_path), acquired, release))
    second = multiprocessing.Process(target=_acquire_run_lock, args=(str(tmp_path), second_acquired))
    first.start()
    try:
        assert acquired.wait(5)
        second.start()
        assert not second_acquired.wait(0.3)
        release.set()
        assert second_acquired.wait(5)
        second.join(5)
        assert second.exitcode == 0
    finally:
        release.set()
        first.join(5)
        if second.is_alive():
            second.terminate()
            second.join()
    assert first.exitcode == 0
