"""Tests for core selectors module."""


from apps.core.selectors import example_filter, example_get, example_list


class TestExampleSelectors:
    """Tests for example selector functions."""

    def test_example_list_no_filters(self):
        """Test example_list with no filters returns empty list."""
        result = example_list()
        assert result == []

    def test_example_list_with_filters(self):
        """Test example_list with filters returns empty list."""
        result = example_list(filters={"name": "test"})
        assert result == []

    def test_example_get_existing(self):
        """Test example_get returns None for any ID."""
        result = example_get(instance_id=1)
        assert result is None

    def test_example_get_nonexistent(self):
        """Test example_get returns None for non-existent ID."""
        result = example_get(instance_id=999)
        assert result is None

    def test_example_filter_no_search(self):
        """Test example_filter with no search term."""
        result = example_filter()
        assert result == []

    def test_example_filter_with_search(self):
        """Test example_filter with search term."""
        result = example_filter(search="test")
        assert result == []
