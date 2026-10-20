from reviewbot import container_entrypoint


def test_non_root_runtime_does_not_change_identity(monkeypatch):
    monkeypatch.setattr(container_entrypoint.os, "geteuid", lambda: 10001)
    monkeypatch.setattr(
        container_entrypoint.os,
        "setuid",
        lambda _: (_ for _ in ()).throw(AssertionError("setuid should not run")),
    )
    container_entrypoint.prepare_runtime()


def test_root_runtime_ignores_paths_outside_github_mount(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(container_entrypoint.os, "geteuid", lambda: 0)
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setattr(container_entrypoint.os, "chown", lambda *args: calls.append(("chown", args)))
    monkeypatch.setattr(container_entrypoint.os, "setgid", lambda value: calls.append(("gid", value)))
    monkeypatch.setattr(container_entrypoint.os, "setuid", lambda value: calls.append(("uid", value)))
    container_entrypoint.prepare_runtime()
    assert calls == [("gid", 10001), ("uid", 10001)]
