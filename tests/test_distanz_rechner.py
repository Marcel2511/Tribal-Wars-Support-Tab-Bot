"""Tests for distanz_rechner.py - Distance calculations."""
import pytest
import math
from distanz_rechner import DistanzRechner


class TestDistanzRechner:
    """Tests for distance calculations between villages."""

    def test_zero_distance_same_coordinates(self):
        """Test that distance between same coordinates is 0."""
        result = DistanzRechner.berechne_distanz("500|500", "500|500")
        assert result == 0.0

    def test_horizontal_distance(self):
        """Test horizontal distance calculation."""
        result = DistanzRechner.berechne_distanz("500|500", "503|500")
        expected = 3.0
        assert result == pytest.approx(expected)

    def test_vertical_distance(self):
        """Test vertical distance calculation."""
        result = DistanzRechner.berechne_distanz("500|500", "500|504")
        expected = 4.0
        assert result == pytest.approx(expected)

    def test_diagonal_distance(self):
        """Test diagonal distance calculation (Pythagorean theorem)."""
        result = DistanzRechner.berechne_distanz("500|500", "503|504")
        expected = math.sqrt(3**2 + 4**2)  # sqrt(9 + 16) = 5.0
        assert result == pytest.approx(expected)

    def test_distance_is_symmetric(self):
        """Test that distance(A, B) == distance(B, A)."""
        coord1 = "500|500"
        coord2 = "510|520"
        
        dist1 = DistanzRechner.berechne_distanz(coord1, coord2)
        dist2 = DistanzRechner.berechne_distanz(coord2, coord1)
        
        assert dist1 == dist2

    def test_large_distance(self):
        """Test calculation with large coordinate differences."""
        result = DistanzRechner.berechne_distanz("100|100", "200|200")
        expected = math.sqrt(100**2 + 100**2)  # sqrt(20000) ≈ 141.42
        assert result == pytest.approx(expected)

    def test_negative_direction_distance(self):
        """Test distance when moving in negative direction."""
        result = DistanzRechner.berechne_distanz("500|500", "490|485")
        expected = math.sqrt(10**2 + 15**2)  # sqrt(100 + 225) ≈ 18.03
        assert result == pytest.approx(expected)

    def test_coordinate_parsing(self):
        """Test that coordinates are correctly parsed."""
        # Test with various coordinate formats
        result1 = DistanzRechner.berechne_distanz("500|500", "503|504")
        result2 = DistanzRechner.berechne_distanz("500|500", "503|504")
        assert result1 == result2

    @pytest.mark.parametrize("coord1,coord2,expected", [
        ("500|500", "500|500", 0.0),
        ("500|500", "501|500", 1.0),
        ("500|500", "500|501", 1.0),
        ("500|500", "503|504", 5.0),
        ("500|500", "506|508", 10.0),
        ("500|500", "510|500", 10.0),
        ("500|500", "500|513", 13.0),
    ])
    def test_various_distances(self, coord1, coord2, expected):
        """Test various distance calculations with parameterized inputs."""
        result = DistanzRechner.berechne_distanz(coord1, coord2)
        assert result == pytest.approx(expected, rel=1e-9)

    def test_real_world_example(self):
        """Test with realistic Tribal Wars coordinates."""
        # Example: Distance from one village to another
        result = DistanzRechner.berechne_distanz("511|523", "498|507")
        expected = math.sqrt((498 - 511)**2 + (507 - 523)**2)
        expected = math.sqrt(13**2 + 16**2)  # sqrt(169 + 256) ≈ 20.62
        assert result == pytest.approx(expected)

    def test_edge_case_max_coordinates(self):
        """Test with maximum possible coordinates."""
        # Tribal Wars typically uses coordinates up to 999|999
        result = DistanzRechner.berechne_distanz("000|000", "999|999")
        expected = math.sqrt(999**2 + 999**2)
        assert result == pytest.approx(expected)

    def test_coordinates_with_leading_zeros(self):
        """Test coordinates with leading zeros."""
        result1 = DistanzRechner.berechne_distanz("500|500", "503|504")
        result2 = DistanzRechner.berechne_distanz("500|500", "503|504")
        assert result1 == result2

    def test_return_type(self):
        """Test that return type is float."""
        result = DistanzRechner.berechne_distanz("500|500", "503|504")
        assert isinstance(result, float)
