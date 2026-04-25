import subprocess


def test_sim():
    result = subprocess.run(["make"], cwd="sim", capture_output=True, text=True)

    assert result.returncode == 0
