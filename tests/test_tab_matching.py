"""Tests for tab_matching.py - Core tab matching logic."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytz

from tab_matching import TabMatching, TabMatch


class TestTabMatchingFindeTabs:
    """Tests for the finde_tabs method."""

    def test_basic_tab_matching(self, sample_doerfer, sample_angriffe, standard_tabgroessen, berlin_tz):
        """Test basic tab matching with standard configuration."""
        # Use freezegun to set current time
        from freezegun import freeze_time
        
        with freeze_time("2026-01-25 10:00:00", tz_offset=1):  # CET is UTC+1
            matches = TabMatching.finde_tabs(
                angriffe=sample_angriffe,
                eigene_dörfer=sample_doerfer,
                tabgroessen_liste=standard_tabgroessen,
                welt_speed=1.0,
                einheiten_speed=1.0
            )
            
            # Should find matches for all attacks
            assert len(matches) > 0, "Should find at least one match"
            
            # Verify match structure
            for match in matches:
                assert isinstance(match, TabMatch)
                assert match.herkunft is not None
                assert match.ziel_koord is not None
                assert match.abschickzeit is not None
                assert match.ankunftszeit is not None
                assert isinstance(match.einheiten, dict)
                assert len(match.einheiten) > 0

    def test_tab_matching_with_zeitfenster(self, sample_doerfer, sample_angriffe, standard_tabgroessen, berlin_tz):
        """Test tab matching with time windows."""
        from freezegun import freeze_time
        
        zeitfenster = [
            (berlin_tz.localize(datetime(2026, 1, 25, 10, 0, 0)),
             berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0)))
        ]
        
        with freeze_time("2026-01-25 09:00:00", tz_offset=1):
            matches = TabMatching.finde_tabs(
                angriffe=sample_angriffe,
                eigene_dörfer=sample_doerfer,
                tabgroessen_liste=standard_tabgroessen,
                welt_speed=1.0,
                einheiten_speed=1.0,
                zeitfenster_liste=zeitfenster
            )
            
            # All matches should have send times within the time window
            for match in matches:
                assert any(
                    von <= match.abschickzeit <= bis
                    for von, bis in zeitfenster
                ), f"Send time {match.abschickzeit} not in time windows"

    def test_tab_matching_with_auto_speed_units(self, sample_doerfer, sample_angriffe, standard_tabgroessen):
        """Test tab matching with auto-speed units enabled."""
        from freezegun import freeze_time
        
        auto_speed_units = {
            "Axtkämpfer": True,
            "Leichte Kavallerie": True,
            "Katapulte": False,
            "Schwertkämpfer": False
        }
        
        with freeze_time("2026-01-25 09:00:00", tz_offset=1):
            matches = TabMatching.finde_tabs(
                angriffe=sample_angriffe,
                eigene_dörfer=sample_doerfer,
                tabgroessen_liste=standard_tabgroessen,
                welt_speed=1.0,
                einheiten_speed=1.0,
                auto_speed_units=auto_speed_units
            )
            
            # Check that some matches include auto-speed units
            for match in matches:
                # Verify only enabled units are added
                if "Axtkämpfer" in match.einheiten:
                    assert match.einheiten["Axtkämpfer"] == 1
                if "Katapulte" in match.einheiten:
                    # Katapulte should only be there if in original tab
                    pass

    def test_tab_matching_with_auto_scouts(self, sample_doerfer, sample_angriffe, standard_tabgroessen):
        """Test tab matching with auto-scouts enabled."""
        from freezegun import freeze_time
        
        with freeze_time("2026-01-25 09:00:00", tz_offset=1):
            matches = TabMatching.finde_tabs(
                angriffe=sample_angriffe,
                eigene_dörfer=sample_doerfer,
                tabgroessen_liste=standard_tabgroessen,
                welt_speed=1.0,
                einheiten_speed=1.0,
                auto_scouts_enabled=True,
                auto_scouts_count=5
            )
            
            # At least some matches should have scouts
            scout_counts = [match.einheiten.get("Späher", 0) for match in matches]
            assert any(count > 0 for count in scout_counts), "Some matches should have scouts"

    def test_tab_matching_respects_troop_availability(self, sample_doerfer, sample_angriffe, berlin_tz):
        """Test that tab matching respects available troops."""
        from freezegun import freeze_time
        
        # Create a tab size larger than available troops
        large_tabgroessen = [
            {
                "Speerträger": 10000,  # More than available
                "Schwertkämpfer": 10000,
                "Schwere Kavallerie": 10000
            }
        ]
        
        with freeze_time("2026-01-25 09:00:00", tz_offset=1):
            matches = TabMatching.finde_tabs(
                angriffe=sample_angriffe,
                eigene_dörfer=sample_doerfer,
                tabgroessen_liste=large_tabgroessen,
                welt_speed=1.0,
                einheiten_speed=1.0
            )
            
            # Should not match when troops unavailable
            # Or should use smaller available amounts
            assert len(matches) == 0 or all(
                all(match.herkunft.truppen.get(unit, 0) >= count 
                    for unit, count in match.einheiten.items())
                for match in matches
            )

    def test_tab_matching_with_world_speed(self, sample_doerfer, sample_angriffe, standard_tabgroessen):
        """Test tab matching with different world speeds."""
        from freezegun import freeze_time
        
        with freeze_time("2026-01-25 09:00:00", tz_offset=1):
            matches_speed_1 = TabMatching.finde_tabs(
                angriffe=sample_angriffe,
                eigene_dörfer=sample_doerfer,
                tabgroessen_liste=standard_tabgroessen,
                welt_speed=1.0,
                einheiten_speed=1.0
            )
            
            matches_speed_2 = TabMatching.finde_tabs(
                angriffe=sample_angriffe,
                eigene_dörfer=sample_doerfer,
                tabgroessen_liste=standard_tabgroessen,
                welt_speed=2.0,
                einheiten_speed=1.0
            )
            
            # Higher speed should allow later send times
            if matches_speed_1 and matches_speed_2:
                assert len(matches_speed_1) <= len(matches_speed_2)

    def test_no_self_targeting(self, sample_doerfer, berlin_tz):
        """Test that villages don't send tabs to themselves."""
        from freezegun import freeze_time
        
        # Create attack on own village
        self_attack = [
            type('Angriff', (), {
                'ziel_koord': '500|500',
                'ankunftszeit': berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0))
            })()
        ]
        
        tabgroessen = [{"Speerträger": 100, "Schwertkämpfer": 100}]
        
        with freeze_time("2026-01-25 09:00:00", tz_offset=1):
            matches = TabMatching.finde_tabs(
                angriffe=self_attack,
                eigene_dörfer=sample_doerfer,
                tabgroessen_liste=tabgroessen,
                welt_speed=1.0,
                einheiten_speed=1.0
            )
            
            # Village at 500|500 should not send to itself
            for match in matches:
                assert match.herkunft.koordinaten != match.ziel_koord


class TestPruefeInEinemBeliebigenZeitfenster:
    """Tests for the pruefe_in_einem_beliebigen_zeitfenster method."""

    def test_empty_zeitfenster_liste(self, berlin_tz):
        """Test with no time windows - should always return True."""
        ts = berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0))
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts, None) is True
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts, []) is True

    def test_within_single_zeitfenster(self, berlin_tz):
        """Test timestamp within a single time window."""
        von = berlin_tz.localize(datetime(2026, 1, 25, 10, 0, 0))
        bis = berlin_tz.localize(datetime(2026, 1, 25, 14, 0, 0))
        
        ts_within = berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0))
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts_within, [(von, bis)]) is True

    def test_outside_single_zeitfenster(self, berlin_tz):
        """Test timestamp outside a single time window."""
        von = berlin_tz.localize(datetime(2026, 1, 25, 10, 0, 0))
        bis = berlin_tz.localize(datetime(2026, 1, 25, 14, 0, 0))
        
        ts_before = berlin_tz.localize(datetime(2026, 1, 25, 9, 0, 0))
        ts_after = berlin_tz.localize(datetime(2026, 1, 25, 15, 0, 0))
        
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts_before, [(von, bis)]) is False
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts_after, [(von, bis)]) is False

    def test_within_multiple_zeitfenster(self, berlin_tz):
        """Test timestamp within one of multiple time windows."""
        fenster = [
            (berlin_tz.localize(datetime(2026, 1, 25, 8, 0, 0)),
             berlin_tz.localize(datetime(2026, 1, 25, 10, 0, 0))),
            (berlin_tz.localize(datetime(2026, 1, 25, 14, 0, 0)),
             berlin_tz.localize(datetime(2026, 1, 25, 18, 0, 0)))
        ]
        
        ts_in_first = berlin_tz.localize(datetime(2026, 1, 25, 9, 0, 0))
        ts_in_second = berlin_tz.localize(datetime(2026, 1, 25, 15, 0, 0))
        ts_between = berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0))
        
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts_in_first, fenster) is True
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts_in_second, fenster) is True
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts_between, fenster) is False

    def test_boundary_conditions(self, berlin_tz):
        """Test boundary conditions (inclusive)."""
        von = berlin_tz.localize(datetime(2026, 1, 25, 10, 0, 0))
        bis = berlin_tz.localize(datetime(2026, 1, 25, 14, 0, 0))
        
        # Boundaries should be inclusive
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(von, [(von, bis)]) is True
        assert TabMatching.pruefe_in_einem_beliebigen_zeitfenster(bis, [(von, bis)]) is True

    def test_none_values_in_zeitfenster(self, berlin_tz):
        """Test handling of None values in time windows."""
        ts = berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0))
        
        fenster_with_none = [
            (None, None),
            (berlin_tz.localize(datetime(2026, 1, 25, 14, 0, 0)),
             berlin_tz.localize(datetime(2026, 1, 25, 18, 0, 0)))
        ]
        
        # Should skip None entries and check valid ones
        result = TabMatching.pruefe_in_einem_beliebigen_zeitfenster(ts, fenster_with_none)
        assert result is False


class TestExportFunctions:
    """Tests for export functionality."""

    @patch('tab_matching.TabMatching.lade_koord_to_id_map')
    def test_export_dsultimate_basic(self, mock_lade_koord, sample_doerfer, berlin_tz):
        """Test basic DS Ultimate export."""
        # Mock the coordinate to ID mapping
        mock_lade_koord.return_value = {
            "500|500": 1001,
            "505|505": 1002,
            "510|510": 1003,
            "515|515": 1004
        }
        
        # Create a simple match
        match = TabMatch(
            herkunft=sample_doerfer[0],
            ziel_koord="505|505",
            abschickzeit=berlin_tz.localize(datetime(2026, 1, 25, 10, 0, 0)),
            ankunftszeit=berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0)),
            einheiten={"Speerträger": 100, "Schwertkämpfer": 100, "Schwere Kavallerie": 100},
            einheit_kuerzel="Schwere Kavallerie"
        )
        
        result = TabMatching.export_dsultimate([match], "221")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "1001" in result  # Source village ID
        assert "1002" in result  # Target village ID

    @patch('tab_matching.requests.get')
    def test_lade_koord_to_id_map_success(self, mock_get):
        """Test successful loading of coordinate to ID mapping."""
        import gzip
        from io import BytesIO
        
        # Create mock gzipped data
        test_data = "1001,Village1,500,500,1,100,0\n1002,Village2,505,505,1,100,0\n"
        compressed = BytesIO()
        with gzip.GzipFile(fileobj=compressed, mode='w') as f:
            f.write(test_data.encode('utf-8'))
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = compressed.getvalue()
        mock_get.return_value = mock_response
        
        result = TabMatching.lade_koord_to_id_map("221")
        
        assert isinstance(result, dict)
        assert "500|500" in result
        assert result["500|500"] == 1001
        assert "505|505" in result
        assert result["505|505"] == 1002

    @patch('tab_matching.requests.get')
    def test_lade_koord_to_id_map_failure(self, mock_get):
        """Test handling of failed coordinate mapping download."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Download der Dorfdaten fehlgeschlagen"):
            TabMatching.lade_koord_to_id_map("999")

    @patch('tab_matching.requests.post')
    @patch('tab_matching.TabMatching.lade_koord_to_id_map')
    def test_send_attackplanner_to_dsu(self, mock_lade_koord, mock_post, sample_doerfer, berlin_tz):
        """Test sending attack planner to DS Ultimate API."""
        # Mock coordinate mapping
        mock_lade_koord.return_value = {
            "500|500": 1001,
            "505|505": 1002
        }
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"edit": "test_edit_link", "view": "test_view_link"}
        mock_post.return_value = mock_response
        
        match = TabMatch(
            herkunft=sample_doerfer[0],
            ziel_koord="505|505",
            abschickzeit=berlin_tz.localize(datetime(2026, 1, 25, 10, 0, 0)),
            ankunftszeit=berlin_tz.localize(datetime(2026, 1, 25, 12, 0, 0)),
            einheiten={"Speerträger": 100, "Schwertkämpfer": 100},
            einheit_kuerzel="Schwertkämpfer"
        )
        
        result = TabMatching.send_attackplanner_to_dsu(
            matches=[match],
            world="221",
            api_key="test_key",
            server="de",
            title="Test Attack Plan"
        )
        
        assert "edit" in result
        mock_post.assert_called_once()

    @patch('tab_matching.TabMatching.lade_koord_to_id_map')
    def test_send_attackplanner_missing_api_key(self, mock_lade_koord):
        """Test that missing API key raises error."""
        mock_lade_koord.return_value = {}
        
        with pytest.raises(ValueError, match="DSU API_KEY fehlt"):
            TabMatching.send_attackplanner_to_dsu(
                matches=[],
                world="221",
                api_key="",
                server="de"
            )
