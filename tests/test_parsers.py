"""Tests for parsers - SOS and troop parsing."""
import pytest
from datetime import datetime
import pytz
from sos_parser import SosParser, Angriff
from eigene_truppen_parser import EigeneTruppenParser, EigenesDorf


class TestSosParser:
    """Tests for SOS attack parser."""

    def test_parse_single_attack(self):
        """Test parsing a single attack."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command] [coord]510|510[/coord] --> Ankunftszeit: 25.01.26 12:00:00"""
        
        result = SosParser.parse(text)
        
        assert len(result) == 1
        assert isinstance(result[0], Angriff)
        assert result[0].ziel_koord == "500|500"
        assert result[0].ankunftszeit.hour == 12
        assert result[0].ankunftszeit.minute == 0

    def test_parse_multiple_attacks_same_village(self):
        """Test parsing multiple attacks on the same village."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command] [coord]510|510[/coord] --> Ankunftszeit: 25.01.26 12:00:00
[command]attack[/command] [coord]515|515[/coord] --> Ankunftszeit: 25.01.26 13:30:00
[command]attack[/command] [coord]520|520[/coord] --> Ankunftszeit: 25.01.26 14:00:00"""
        
        result = SosParser.parse(text)
        
        assert len(result) == 3
        assert all(r.ziel_koord == "500|500" for r in result)
        assert result[0].ankunftszeit.hour == 12
        assert result[1].ankunftszeit.hour == 13
        assert result[2].ankunftszeit.hour == 14

    def test_parse_multiple_villages(self):
        """Test parsing attacks on multiple villages."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command] [coord]510|510[/coord] --> Ankunftszeit: 25.01.26 12:00:00
[b]Dorf:[/b] [coord]505|505[/coord]
[command]attack[/command] [coord]515|515[/coord] --> Ankunftszeit: 25.01.26 13:00:00"""
        
        result = SosParser.parse(text)
        
        assert len(result) == 2
        assert result[0].ziel_koord == "500|500"
        assert result[1].ziel_koord == "505|505"

    def test_parse_with_unit_type(self):
        """Test parsing attacks with unit types specified."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command]Axtkämpfer [coord]510|510[/coord] --> Ankunftszeit: 25.01.26 12:00:00"""
        
        result = SosParser.parse(text)
        
        assert len(result) == 1
        assert result[0].einheit == "Axtkämpfer"

    def test_parse_empty_text(self):
        """Test parsing empty text."""
        result = SosParser.parse("")
        assert len(result) == 0

    def test_parse_text_without_attacks(self):
        """Test parsing text with village but no attacks."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
Some other text without attack pattern"""
        
        result = SosParser.parse(text)
        assert len(result) == 0

    def test_parse_timezone_handling(self):
        """Test that parsed times are in Berlin timezone."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command] [coord]510|510[/coord] --> Ankunftszeit: 25.01.26 12:00:00"""
        
        result = SosParser.parse(text)
        
        assert result[0].ankunftszeit.tzinfo is not None
        assert result[0].ankunftszeit.tzinfo.zone == "Europe/Berlin"

    def test_parse_date_formats(self):
        """Test parsing various date formats."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command] [coord]510|510[/coord] --> Ankunftszeit: 01.12.26 23:59:59"""
        
        result = SosParser.parse(text)
        
        assert len(result) == 1
        assert result[0].ankunftszeit.day == 1
        assert result[0].ankunftszeit.month == 12
        assert result[0].ankunftszeit.hour == 23
        assert result[0].ankunftszeit.minute == 59
        assert result[0].ankunftszeit.second == 59

    def test_parse_ignores_invalid_date(self):
        """Test that invalid dates are skipped."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command] [coord]510|510[/coord] --> Ankunftszeit: 99.99.99 99:99:99
[command]attack[/command] [coord]515|515[/coord] --> Ankunftszeit: 25.01.26 12:00:00"""
        
        result = SosParser.parse(text)
        
        # Should skip the invalid date and only parse the valid one
        assert len(result) == 1
        assert result[0].ankunftszeit.hour == 12

    def test_parse_coordinate_formats(self):
        """Test parsing various coordinate formats."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command] [coord]999|999[/coord] --> Ankunftszeit: 25.01.26 12:00:00
[b]Dorf:[/b] [coord]001|001[/coord]
[command]attack[/command] [coord]010|020[/coord] --> Ankunftszeit: 25.01.26 13:00:00"""
        
        result = SosParser.parse(text)
        
        assert len(result) == 2
        assert result[0].ziel_koord == "500|500"
        assert result[1].ziel_koord == "001|001"

    def test_parse_preserves_attack_order(self):
        """Test that attack order is preserved."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]
[command]attack[/command] [coord]510|510[/coord] --> Ankunftszeit: 25.01.26 14:00:00
[command]attack[/command] [coord]515|515[/coord] --> Ankunftszeit: 25.01.26 12:00:00
[command]attack[/command] [coord]520|520[/coord] --> Ankunftszeit: 25.01.26 13:00:00"""
        
        result = SosParser.parse(text)
        
        # Should preserve order, not sort by time
        assert result[0].ankunftszeit.hour == 14
        assert result[1].ankunftszeit.hour == 12
        assert result[2].ankunftszeit.hour == 13

    def test_parse_multiline_format(self):
        """Test parsing with different line breaks."""
        text = """[b]Dorf:[/b] [coord]500|500[/coord]

[command]attack[/command] [coord]510|510[/coord] --> Ankunftszeit: 25.01.26 12:00:00

[b]Dorf:[/b] [coord]505|505[/coord]

[command]attack[/command] [coord]515|515[/coord] --> Ankunftszeit: 25.01.26 13:00:00"""
        
        result = SosParser.parse(text)
        
        assert len(result) == 2


class TestEigeneTruppenParser:
    """Tests for own troops parser."""

    def test_parse_single_village(self):
        """Test parsing a single village with troops."""
        text = "Dorf 1 (500|500) K45 eigene 1000 800 600 100 200 300 50 75"
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 1
        assert isinstance(result[0], EigenesDorf)
        assert result[0].dorf_name == "Dorf 1"
        assert result[0].koordinaten == "500|500"
        assert result[0].truppen["Speerträger"] == 1000
        assert result[0].truppen["Schwertkämpfer"] == 800
        assert result[0].truppen["Axtkämpfer"] == 600
        assert result[0].truppen["Späher"] == 100
        assert result[0].truppen["Leichte Kavallerie"] == 200
        assert result[0].truppen["Schwere Kavallerie"] == 300
        assert result[0].truppen["Rammböcke"] == 50
        assert result[0].truppen["Katapulte"] == 75

    def test_parse_multiple_villages(self):
        """Test parsing multiple villages."""
        text = """Dorf 1 (500|500) K45 eigene 1000 800 600 100 200 300 50 75
Dorf 2 (510|510) K45 eigene 2000 1500 1000 200 300 400 100 150
Dorf 3 (520|520) K45 eigene 500 400 300 50 100 150 25 40"""
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 3
        assert result[0].dorf_name == "Dorf 1"
        assert result[1].dorf_name == "Dorf 2"
        assert result[2].dorf_name == "Dorf 3"
        assert result[1].truppen["Speerträger"] == 2000

    def test_parse_village_with_special_characters_in_name(self):
        """Test parsing village names with special characters."""
        text = "Dorf-Süd (500|500) K45 eigene 1000 800 600 100 200 300 50 75"
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 1
        assert result[0].dorf_name == "Dorf-Süd"

    def test_parse_village_with_long_name(self):
        """Test parsing village with long name."""
        text = "Mein super langes Dorfname (500|500) K45 eigene 1000 800 600 100 200 300 50 75"
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 1
        assert result[0].dorf_name == "Mein super langes Dorfname"

    def test_parse_empty_text(self):
        """Test parsing empty text."""
        result = EigeneTruppenParser.parse("")
        assert len(result) == 0

    def test_parse_zero_troops(self):
        """Test parsing village with zero troops."""
        text = "Neues Dorf (500|500) K45 eigene 0 0 0 0 0 0 0 0"
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 1
        assert all(count == 0 for count in result[0].truppen.values())

    def test_parse_large_troop_numbers(self):
        """Test parsing large troop numbers."""
        text = "Großes Dorf (500|500) K45 eigene 10000 9000 8000 5000 4000 3000 2000 1000"
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 1
        assert result[0].truppen["Speerträger"] == 10000
        assert result[0].truppen["Katapulte"] == 1000

    def test_parse_invalid_format_skipped(self):
        """Test that invalid format lines are skipped with warning."""
        text = """Dorf 1 (500|500) K45 eigene 1000 800 600
Dorf 2 (510|510) K45 eigene 2000 1500 1000 200 300 400 100 150"""
        
        result = EigeneTruppenParser.parse(text)
        
        # First line should be skipped (not enough values), second should be parsed
        assert len(result) == 1
        assert result[0].dorf_name == "Dorf 2"

    def test_parse_different_kontinents(self):
        """Test parsing villages from different kontinents."""
        text = """Dorf K45 (500|500) K45 eigene 1000 800 600 100 200 300 50 75
Dorf K55 (555|555) K55 eigene 2000 1500 1000 200 300 400 100 150"""
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 2

    def test_parse_coordinate_edge_cases(self):
        """Test parsing edge case coordinates."""
        text = """Dorf Min (000|000) K00 eigene 100 100 100 10 10 10 5 5
Dorf Max (999|999) K99 eigene 200 200 200 20 20 20 10 10"""
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 2
        assert result[0].koordinaten == "000|000"
        assert result[1].koordinaten == "999|999"

    def test_parse_whitespace_handling(self):
        """Test handling of various whitespace."""
        text = "Dorf   1   (500|500)   K45   eigene   1000   800   600   100   200   300   50   75"
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 1
        assert result[0].truppen["Speerträger"] == 1000

    def test_parse_mixed_valid_invalid(self):
        """Test parsing mixed valid and invalid entries."""
        text = """Dorf 1 (500|500) K45 eigene 1000 800 600 100 200 300 50 75
Invalid line without proper format
Dorf 2 (510|510) K45 eigene 2000 1500 1000 200 300 400 100 150
Another invalid line
Dorf 3 (520|520) K45 eigene 500 400 300 50 100 150 25 40"""
        
        result = EigeneTruppenParser.parse(text)
        
        assert len(result) == 3
        assert all(isinstance(d, EigenesDorf) for d in result)

    def test_troop_order_is_correct(self):
        """Test that troop counts are assigned in correct order."""
        text = "Test (500|500) K45 eigene 1 2 3 4 5 6 7 8"
        
        result = EigeneTruppenParser.parse(text)
        
        assert result[0].truppen["Speerträger"] == 1
        assert result[0].truppen["Schwertkämpfer"] == 2
        assert result[0].truppen["Axtkämpfer"] == 3
        assert result[0].truppen["Späher"] == 4
        assert result[0].truppen["Leichte Kavallerie"] == 5
        assert result[0].truppen["Schwere Kavallerie"] == 6
        assert result[0].truppen["Rammböcke"] == 7
        assert result[0].truppen["Katapulte"] == 8


class TestParserIntegration:
    """Integration tests for parsers."""

    def test_realistic_sos_scenario(self):
        """Test with realistic SOS data."""
        sos_text = """[b]Dorf:[/b] [coord]511|523[/coord]
[command]attack[/command]Axtkämpfer [coord]498|507[/coord] --> Ankunftszeit: 25.01.26 10:30:15
[command]attack[/command]Axtkämpfer [coord]502|519[/coord] --> Ankunftszeit: 25.01.26 11:45:30
[b]Dorf:[/b] [coord]525|508[/coord]
[command]attack[/command]Leichte Kavallerie [coord]533|501[/coord] --> Ankunftszeit: 25.01.26 12:15:45"""
        
        attacks = SosParser.parse(sos_text)
        
        assert len(attacks) == 3
        assert attacks[0].ziel_koord == "511|523"
        assert attacks[1].ziel_koord == "511|523"
        assert attacks[2].ziel_koord == "525|508"

    def test_realistic_troops_scenario(self):
        """Test with realistic troop data."""
        troops_text = """Hauptdorf (500|500) K45 eigene 5000 4000 3000 500 1000 800 200 300
Zweitdorf (510|505) K45 eigene 3000 2500 2000 300 600 500 100 150
Norddorf (505|515) K55 eigene 4000 3500 2800 400 800 700 150 200"""
        
        villages = EigeneTruppenParser.parse(troops_text)
        
        assert len(villages) == 3
        assert villages[0].dorf_name == "Hauptdorf"
        assert villages[1].koordinaten == "510|505"
        assert villages[2].truppen["Speerträger"] == 4000
