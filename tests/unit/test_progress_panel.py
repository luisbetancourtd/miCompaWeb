"""Tests for ProgressPanel TUI component."""

import pytest

from micompaweb.presentation.tui.progress_panel import ProgressPanel


class TestProgressPanel:
    """Tests for the Pipeline M1 progress panel."""

    def test_stages_list_complete(self):
        """Progress panel should cover all pipeline stages."""
        panel = ProgressPanel()
        expected = [
            "validation", "discovery", "filter_chains",
            "audit", "vigency", "competitors",
            "scoring", "sentiment",
            "revenue", "export",
        ]
        assert panel.STAGES == expected

    def test_stage_names_readable(self):
        """Stage names should be human-readable with emojis."""
        panel = ProgressPanel()
        assert "Validaci" in panel.STAGE_NAMES["validation"]
        assert "Descubrimiento" in panel.STAGE_NAMES["discovery"]
        assert "Scoring 3D" in panel.STAGE_NAMES["scoring"]

    def test_initial_state(self):
        """Initial state should have no active task."""
        panel = ProgressPanel()
        assert panel.task_id is None
        assert panel.current_stage_idx == 0

    def test_start_stage_advances_index(self):
        """Starting a stage should advance current index."""
        panel = ProgressPanel()
        panel.start_stage("audit", total_steps=50)
        assert panel.current_stage_idx == 3  # audit is index 3
        assert panel.task_id is not None

    def test_advance_increments_progress(self):
        """Advancing should move the progress bar."""
        panel = ProgressPanel()
        panel.start_stage("scoring", total_steps=100)
        initial = panel.progress.tasks[panel.task_id].completed
        panel.advance(10)
        after = panel.progress.tasks[panel.task_id].completed
        assert after == initial + 10

    def test_complete_stage_sets_done(self):
        """Completing stage should mark as done and advance to next."""
        panel = ProgressPanel()
        panel.start_stage("discovery", total_steps=10)
        panel.complete_stage()
        assert panel.current_stage_idx == 2  # discovery (idx 1) done → next
        assert panel.task_id is None  # task cleared after completion

    def test_render_exists(self):
        """_render should produce a Panel object."""
        from rich.panel import Panel
        panel = ProgressPanel()
        rendered = panel._render()
        assert isinstance(rendered, Panel)

    def test_stage_not_found_raises(self):
        """Unknown stage should raise ValueError."""
        panel = ProgressPanel()
        with pytest.raises(ValueError):
            panel.start_stage("nonexistent_stage", total_steps=10)
