"""Tests for einheiten.py - Unit definitions and travel time calculations."""
import pytest
from einheiten import get_laufzeit, laufzeiten_pro_feld, einheiten_aliases


class TestLaufzeitenProFeld:
    """Tests for base travel times per field."""

    def test_all_units_have_laufzeit(self):
        """Test that all expected units have travel times defined."""
        expected_units = [
            "Speerträger",
            "Schwertkämpfer",
            "Axtkämpfer",
            "Späher",
            "Leichte Kavallerie",
            "Schwere Kavallerie",
            "Rammböcke",
            "Katapulte"
        ]
        
        for unit in expected_units:
            assert unit in laufzeiten_pro_feld, f"{unit} missing from laufzeiten_pro_feld"
            assert isinstance(laufzeiten_pro_feld[unit], (int, float))
            assert laufzeiten_pro_feld[unit] > 0

    def test_relative_speeds_are_correct(self):
        """Test that unit speeds are in correct relative order."""
        # Scouts should be fastest
        assert laufzeiten_pro_feld["Späher"] == 9
        
        # Light cavalry should be faster than heavy cavalry
        assert laufzeiten_pro_feld["Leichte Kavallerie"] < laufzeiten_pro_feld["Schwere Kavallerie"]
        
        # Rams and catapults should be slowest
        assert laufzeiten_pro_feld["Rammböcke"] == 30
        assert laufzeiten_pro_feld["Katapulte"] == 30


class TestEinheitenAliases:
    """Tests for unit name aliases."""

    def test_alias_mappings(self):
        """Test that common aliases are correctly mapped."""
        assert einheiten_aliases["speertraeger"] == "Speerträger"
        assert einheiten_aliases["speerträger"] == "Speerträger"
        assert einheiten_aliases["leichte kavallerie"] == "Leichte Kavallerie"
        assert einheiten_aliases["schwere kavallerie"] == "Schwere Kavallerie"

    def test_all_aliases_map_to_valid_units(self):
        """Test that all aliases map to units in laufzeiten_pro_feld."""
        for alias, unit_name in einheiten_aliases.items():
            assert unit_name in laufzeiten_pro_feld, f"Alias '{alias}' maps to unknown unit '{unit_name}'"


class TestGetLaufzeit:
    """Tests for get_laufzeit function."""

    def test_basic_laufzeit_calculation(self):
        """Test basic travel time calculation with default parameters."""
        result = get_laufzeit("Speerträger")
        assert result == 18.0
        
        result = get_laufzeit("Späher")
        assert result == 9.0

    def test_laufzeit_with_welt_speed(self):
        """Test travel time with world speed modifier."""
        # Speed 1.0 (normal)
        result1 = get_laufzeit("Speerträger", welt_speed=1.0)
        assert result1 == 18.0
        
        # Speed 2.0 (double speed)
        result2 = get_laufzeit("Speerträger", welt_speed=2.0)
        assert result2 == 9.0
        
        # Speed 0.5 (half speed)
        result3 = get_laufzeit("Speerträger", welt_speed=0.5)
        assert result3 == 36.0

    def test_laufzeit_with_einheiten_speed(self):
        """Test travel time with unit speed modifier."""
        result1 = get_laufzeit("Schwere Kavallerie", einheiten_speed=1.0)
        assert result1 == 11.0
        
        result2 = get_laufzeit("Schwere Kavallerie", einheiten_speed=2.0)
        assert result2 == 5.5

    def test_laufzeit_with_boost_multiplier(self):
        """Test travel time with boost multiplier."""
        result1 = get_laufzeit("Katapulte", boost_multiplier=1.0)
        assert result1 == 30.0
        
        # With 10% boost (multiplier 1.1)
        result2 = get_laufzeit("Katapulte", boost_multiplier=1.1)
        assert result2 == pytest.approx(30.0 / 1.1)

    def test_laufzeit_with_combined_modifiers(self):
        """Test travel time with all modifiers combined."""
        # Base time: 18
        # World speed 2.0, unit speed 1.5, boost 1.2
        # Result: 18 / (2.0 * 1.5 * 1.2) = 18 / 3.6 = 5.0
        result = get_laufzeit("Speerträger", welt_speed=2.0, einheiten_speed=1.5, boost_multiplier=1.2)
        assert result == pytest.approx(5.0)

    def test_laufzeit_with_lowercase_name(self):
        """Test that lowercase unit names work via aliases."""
        result = get_laufzeit("speerträger")
        assert result == 18.0

    def test_laufzeit_with_normalized_name(self):
        """Test that names with umlauts are normalized."""
        result = get_laufzeit("speertraeger")  # ae instead of ä
        assert result == 18.0

    def test_laufzeit_case_insensitive(self):
        """Test case insensitivity."""
        result1 = get_laufzeit("SPEERTRÄGER")
        result2 = get_laufzeit("speerträger")
        result3 = get_laufzeit("Speerträger")
        
        assert result1 == result2 == result3

    def test_laufzeit_with_whitespace(self):
        """Test handling of whitespace."""
        result = get_laufzeit("  Speerträger  ")
        assert result == 18.0

    def test_unknown_unit_raises_error(self):
        """Test that unknown unit name raises ValueError."""
        with pytest.raises(ValueError, match="nicht bekannt"):
            get_laufzeit("Unbekannte Einheit")

    @pytest.mark.parametrize("unit_name,expected_base_time", [
        ("Speerträger", 18),
        ("Schwertkämpfer", 22),
        ("Axtkämpfer", 18),
        ("Späher", 9),
        ("Leichte Kavallerie", 10),
        ("Schwere Kavallerie", 11),
        ("Rammböcke", 30),
        ("Katapulte", 30),
    ])
    def test_all_units_base_times(self, unit_name, expected_base_time):
        """Test base travel times for all units."""
        result = get_laufzeit(unit_name)
        assert result == expected_base_time

    def test_realistic_world_scenario(self):
        """Test with realistic world settings."""
        # Example: World speed 1.5, unit speed 1.0, 10% boost
        result = get_laufzeit("Schwere Kavallerie", welt_speed=1.5, einheiten_speed=1.0, boost_multiplier=1.1)
        expected = 11.0 / (1.5 * 1.0 * 1.1)
        assert result == pytest.approx(expected)

    def test_extreme_speed_values(self):
        """Test with extreme speed values."""
        # Very high speed
        result1 = get_laufzeit("Späher", welt_speed=10.0)
        assert result1 == 0.9
        
        # Very low speed (shouldn't happen in game but test edge case)
        result2 = get_laufzeit("Späher", welt_speed=0.1)
        assert result2 == 90.0

    def test_return_type_is_float(self):
        """Test that return type is always float."""
        result = get_laufzeit("Speerträger")
        assert isinstance(result, float)

    def test_precision(self):
        """Test calculation precision with complex modifiers."""
        result = get_laufzeit("Axtkämpfer", welt_speed=1.3, einheiten_speed=1.7, boost_multiplier=1.15)
        # 18 / (1.3 * 1.7 * 1.15) = 18 / 2.5415 ≈ 7.083
        assert result == pytest.approx(18 / (1.3 * 1.7 * 1.15))


class TestAliasNormalization:
    """Tests for alias normalization logic."""

    def test_umlaut_normalization(self):
        """Test that umlauts are correctly normalized."""
        # ä -> ae, ö -> oe, ü -> ue
        result1 = get_laufzeit("speerträger")
        result2 = get_laufzeit("speertraeger")
        assert result1 == result2

    def test_mixed_case_with_umlauts(self):
        """Test mixed case with umlauts."""
        result1 = get_laufzeit("SchwertkäMPfer")
        result2 = get_laufzeit("Schwertkämpfer")
        assert result1 == result2

    def test_special_characters_in_unit_names(self):
        """Test unit names with special characters."""
        # "Leichte Kavallerie" has a space
        result = get_laufzeit("leichte kavallerie")
        assert result == 10.0
        
        # "Rammböcke" has ö
        result = get_laufzeit("rammbocke")
        assert result == 30.0
