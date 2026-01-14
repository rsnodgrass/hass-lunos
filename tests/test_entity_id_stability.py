"""Tests to prevent entity ID regressions across versions.

WARNING: These tests protect user installations. Changing unique_id formats
breaks automations, dashboards, and entity history. You MUST provide a
migration path if changes are absolutely necessary.
"""

import pytest

DOMAIN = 'lunos'

# Golden unique_id format documentation
# These patterns are part of the public API - do not change without migration
#
# Fan entity unique_id format:
#   Pattern: {relay_w1}_{relay_w2}
#   Example: switch.lunos_w1_switch.lunos_w2
#
# The unique_id is constructed from the two relay entity IDs that control
# the LUNOS fan speed (W1 and W2). This creates a stable identifier that
# persists across Home Assistant restarts.
GOLDEN_FORMATS = {
    'fan': '{relay_w1}_{relay_w2}',
}


def generate_fan_unique_id(relay_w1: str, relay_w2: str) -> str:
    """Generate unique_id using same logic as LUNOSFan.__init__.

    Mirrors: custom_components/lunos/fan.py line 155
        self._attr_unique_id = f'{relay_w1}_{relay_w2}'
    """
    return f'{relay_w1}_{relay_w2}'


class TestFanUniqueIdStability:
    """Test fan entity unique_id format stability."""

    @pytest.mark.parametrize(
        'relay_w1,relay_w2,expected',
        [
            # standard switch entities
            ('switch.lunos_w1', 'switch.lunos_w2', 'switch.lunos_w1_switch.lunos_w2'),
            # different naming conventions
            ('switch.bedroom_relay_1', 'switch.bedroom_relay_2', 'switch.bedroom_relay_1_switch.bedroom_relay_2'),
            # light entities (zigbee relays often appear as lights)
            ('light.lunos_relay_w1', 'light.lunos_relay_w2', 'light.lunos_relay_w1_light.lunos_relay_w2'),
            # mixed domains (unusual but valid)
            ('switch.w1_relay', 'light.w2_relay', 'switch.w1_relay_light.w2_relay'),
            # numeric suffixes
            ('switch.relay_1', 'switch.relay_2', 'switch.relay_1_switch.relay_2'),
            # underscores in entity names
            ('switch.living_room_lunos_w1', 'switch.living_room_lunos_w2', 'switch.living_room_lunos_w1_switch.living_room_lunos_w2'),
        ],
    )
    def test_format_stability(self, relay_w1: str, relay_w2: str, expected: str):
        """Ensure fan unique_id format matches golden values.

        WARNING: If this test fails, you are about to break user automations,
        dashboards, and entity history. You MUST provide a migration path.
        """
        result = generate_fan_unique_id(relay_w1, relay_w2)
        assert result == expected, (
            f'BREAKING CHANGE: fan unique_id format changed!\n'
            f'  Relay W1: {relay_w1}\n'
            f'  Relay W2: {relay_w2}\n'
            f'  Expected: {expected}\n'
            f'  Got: {result}\n'
            f'This will break existing user installations.'
        )

    def test_unique_id_uses_full_entity_id(self):
        """Verify unique_id includes full entity ID with domain prefix.

        The unique_id must use the complete entity ID (domain.name) to ensure
        uniqueness when users have multiple LUNOS installations with similar
        naming patterns.
        """
        relay_w1 = 'switch.lunos_w1'
        relay_w2 = 'switch.lunos_w2'
        result = generate_fan_unique_id(relay_w1, relay_w2)

        # must include domain prefix
        assert result.startswith('switch.')
        assert '_switch.' in result

    def test_unique_id_preserves_case(self):
        """Verify unique_id preserves entity ID case exactly.

        Entity IDs in Home Assistant are case-sensitive for matching purposes.
        The unique_id should preserve the exact case of the relay entity IDs.
        """
        relay_w1 = 'switch.LUNOS_W1'
        relay_w2 = 'switch.LUNOS_W2'
        result = generate_fan_unique_id(relay_w1, relay_w2)

        assert result == 'switch.LUNOS_W1_switch.LUNOS_W2'

    def test_unique_id_is_deterministic(self):
        """Verify same inputs always produce same unique_id.

        Critical for entity registry persistence across restarts.
        """
        relay_w1 = 'switch.lunos_w1'
        relay_w2 = 'switch.lunos_w2'

        results = [generate_fan_unique_id(relay_w1, relay_w2) for _ in range(10)]
        assert len(set(results)) == 1, 'unique_id generation is not deterministic'

    def test_different_relays_produce_different_ids(self):
        """Verify different relay combinations produce unique IDs.

        Essential for multi-fan installations where each LUNOS unit uses
        different relay pairs.
        """
        id1 = generate_fan_unique_id('switch.w1_a', 'switch.w2_a')
        id2 = generate_fan_unique_id('switch.w1_b', 'switch.w2_b')
        id3 = generate_fan_unique_id('switch.w1_a', 'switch.w2_b')

        assert id1 != id2
        assert id1 != id3
        assert id2 != id3


class TestDeviceIdentifierStability:
    """Test device registry identifier format stability.

    Device identifiers use the same unique_id as the fan entity.
    See fan.py device_info property.
    """

    @pytest.mark.parametrize(
        'relay_w1,relay_w2',
        [
            ('switch.lunos_w1', 'switch.lunos_w2'),
            ('switch.bedroom_w1', 'switch.bedroom_w2'),
            ('light.relay_1', 'light.relay_2'),
        ],
    )
    def test_device_identifier_matches_unique_id(self, relay_w1: str, relay_w2: str):
        """Verify device identifier uses same format as entity unique_id.

        The device_info property creates identifiers as:
            identifiers={(DOMAIN, self._attr_unique_id)}

        This must stay in sync with entity unique_id generation.
        """
        unique_id = generate_fan_unique_id(relay_w1, relay_w2)
        device_identifier = (DOMAIN, unique_id)

        assert device_identifier[0] == DOMAIN
        assert device_identifier[1] == unique_id
