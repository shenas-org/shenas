"""Tests for task management."""

from fl_server.tasks import Task, add_task, get_task, list_tasks, remove_task


class TestTasks:
    def test_default_tasks_exist(self) -> None:
        tasks = list_tasks()
        assert len(tasks) >= 1
        names = [t.name for t in tasks]
        assert "sleep-forecast" in names

    def test_get_existing_task(self) -> None:
        task = get_task("sleep-forecast")
        assert task is not None
        assert task.model == "linear"
        assert len(task.features) > 0
        assert task.target == "target"

    def test_get_nonexistent_task(self) -> None:
        assert get_task("nonexistent") is None

    def test_add_and_remove_task(self) -> None:
        task = Task(
            name="test-task",
            description="Test",
            model="linear",
            query="SELECT 1",
            features=["a", "b"],
            target="y",
        )
        add_task(task)
        assert get_task("test-task") is not None

        assert remove_task("test-task") is True
        assert get_task("test-task") is None

    def test_remove_nonexistent(self) -> None:
        assert remove_task("nonexistent") is False
