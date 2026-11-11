import unittest
from unittest.mock import patch

import mastery_service


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class PostGameMasteryTests(unittest.TestCase):
    def setUp(self):
        mastery_service._PROVISIONAL_MASTERY_UPDATES.clear()

    def tearDown(self):
        mastery_service._PROVISIONAL_MASTERY_UPDATES.clear()

    def test_vayne_level_up_uses_post_game_result_until_lcu_catches_up(self):
        game_stats = {
            "gameId": 12345,
            "localPlayer": {"championId": 67},
        }
        post_game_update = {
            "gameId": 12345,
            "championId": 67,
            "championLevel": 15,
            "championPointsBeforeGame": 19384,
            # Synthetic gain crosses 500 remaining, leaving the screenshot's 116 / 11,000 progress.
            "championPointsGained": 615,
            "championPointsUntilNextLevelBeforeGame": 500,
            "championPointsUntilNextLevelAfterGame": 10884,
            "championLevelUp": True,
        }
        stale_mastery = [{
            "championId": 67,
            "championLevel": 14,
            "championPoints": 19384,
            "championPointsUntilNextLevel": 500,
            "markRequiredForNextLevel": 0,
            "tokensEarned": 0,
        }]

        with patch.object(
            mastery_service,
            "_get_lcu_response",
            side_effect=[
                (FakeResponse(200, game_stats), None),
                (FakeResponse(200, post_game_update), None),
                (FakeResponse(200, stale_mastery), None),
            ],
        ):
            update, status = mastery_service.get_post_game_mastery_update()
            data, mastery_status = mastery_service.get_mastery_data(
                {67: "Vayne"},
                {},
                "test",
            )

        self.assertEqual(status, 200)
        self.assertTrue(update["available"])
        self.assertEqual(mastery_status, 200)
        vayne = data["champions"][0]
        self.assertEqual(vayne["championLevel"], 15)
        self.assertEqual(vayne["championPoints"], 19999)
        self.assertEqual(vayne["championPointsGained"], 615)
        self.assertEqual(vayne["pointsIntoLevel"], 116)
        self.assertEqual(vayne["xpRemaining"], 10884)
        self.assertTrue(vayne["isProvisional"])

        synchronized_mastery = [dict(stale_mastery[0], championLevel=15, championPoints=19999)]
        with patch.object(
            mastery_service,
            "_get_lcu_response",
            return_value=(FakeResponse(200, synchronized_mastery), None),
        ):
            synchronized, status = mastery_service.get_mastery_data(
                {67: "Vayne"},
                {},
                "test",
            )

        self.assertEqual(status, 200)
        self.assertEqual(synchronized["champions"][0]["championLevel"], 15)
        self.assertNotIn("isProvisional", synchronized["champions"][0])
        self.assertNotIn(67, mastery_service._PROVISIONAL_MASTERY_UPDATES)

    def test_ignores_post_game_update_for_a_different_game(self):
        game_stats = {
            "gameId": 12345,
            "localPlayer": {"championId": 67},
        }
        stale_update = {
            "gameId": 12344,
            "championId": 67,
            "championLevel": 15,
            "championPointsBeforeGame": 19384,
            "championPointsGained": 615,
            "championLevelUp": True,
        }

        with patch.object(
            mastery_service,
            "_get_lcu_response",
            side_effect=[
                (FakeResponse(200, game_stats), None),
                (FakeResponse(200, stale_update), None),
            ],
        ):
            update, status = mastery_service.get_post_game_mastery_update()

        self.assertEqual(status, 200)
        self.assertFalse(update["available"])
        self.assertEqual(mastery_service._PROVISIONAL_MASTERY_UPDATES, {})


if __name__ == "__main__":
    unittest.main()
