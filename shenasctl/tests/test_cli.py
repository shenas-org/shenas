from typer.testing import CliRunner

from shenasctl.main import app as main_app

runner = CliRunner()


class TestMainCLI:
    def test_help(self) -> None:
        result = runner.invoke(main_app, ["--help"])
        assert result.exit_code == 0
        assert "pipe" in result.output
        assert "component" in result.output
        assert "schema" in result.output
        assert "db" in result.output

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(main_app, [])
        assert result.exit_code == 0
        assert "Usage" in result.output
