from pathlib import Path
import subprocess
import sys


def test_quiz_service_import_does_not_evaluate_shadowed_list_annotation() -> None:
    backend_dir = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; import app.models; import app.schemas.quiz; "
                "source = Path('app/services/quiz.py').read_text(); "
                "namespace = {'__name__': 'quiz_service_import_test', "
                "'list': lambda *_: None}; "
                "exec(compile(source, 'app/services/quiz.py', 'exec'), namespace)"
            ),
        ],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
