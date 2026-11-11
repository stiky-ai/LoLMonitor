import json
import os
import tempfile
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
        mastery_service._LAST_MASTERY_SNAPSHOT = {}
        mastery_service._MATCH_MASTERY_SNAPSHOT = {}
        mastery_service._LAST_GAMEFLOW_PHASE = None
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.history_patcher = patch.object(
            mastery_service,
            "_MASTERY_GAIN_HISTORY_PATH",
            os.path.join(self.temp_dir.name, "mastery_gain_samples.json"),
        )
        self.history_patcher.start()
        self.addCleanup(self.history_patcher.stop)

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

    def test_no_level_up_adds_mordekaiser_points_when_pre_game_total_is_omitted(self):
        game_stats = {
            "gameId": 67890,
            "localPlayer": {"championId": 82},
        }
        post_game_update = {
            "gameId": 67890,
            "championId": 82,
            "championLevel": 6,
            "championPointsGained": 533,
            "championPointsSinceLastLevelBeforeGame": 30000,
            "championPointsUntilNextLevelBeforeGame": 2300,
            "championPointsUntilNextLevelAfterGame": 1767,
            "championLevelUp": False,
        }
        stale_mastery = [{
            "championId": 82,
            "championLevel": 6,
            "championPoints": 33059,
            "championPointsUntilNextLevel": 2300,
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
                {82: "Mordekaiser"},
                {},
                "test",
            )

        self.assertEqual(status, 200)
        self.assertTrue(update["available"])
        self.assertNotIn("_fallbackBeforeGamePoints", update)
        self.assertEqual(mastery_status, 200)
        mordekaiser = data["champions"][0]
        self.assertEqual(mordekaiser["championLevel"], 6)
        self.assertEqual(mordekaiser["championPoints"], 33592)
        self.assertEqual(mordekaiser["championPointsGained"], 533)
        self.assertEqual(mordekaiser["pointsIntoLevel"], 30533)
        self.assertEqual(mordekaiser["xpRemaining"], 1767)
        self.assertTrue(mordekaiser["isProvisional"])

        with patch.object(
            mastery_service,
            "_get_lcu_response",
            side_effect=[
                (FakeResponse(200, game_stats), None),
                (FakeResponse(200, post_game_update), None),
                (FakeResponse(200, stale_mastery), None),
            ],
        ):
            mastery_service.get_post_game_mastery_update()
            repeated_data, status = mastery_service.get_mastery_data(
                {82: "Mordekaiser"},
                {},
                "test",
            )

        self.assertEqual(status, 200)
        self.assertEqual(repeated_data["champions"][0]["championPoints"], 33592)
        self.assertTrue(repeated_data["champions"][0]["isProvisional"])

        synchronized_mastery = [dict(
            stale_mastery[0],
            championPoints=33592,
            championPointsUntilNextLevel=1767,
        )]
        with patch.object(
            mastery_service,
            "_get_lcu_response",
            return_value=(FakeResponse(200, synchronized_mastery), None),
        ):
            synchronized, status = mastery_service.get_mastery_data(
                {82: "Mordekaiser"},
                {},
                "test",
            )

        self.assertEqual(status, 200)
        self.assertEqual(synchronized["champions"][0]["championPoints"], 33592)
        self.assertNotIn("isProvisional", synchronized["champions"][0])
        self.assertNotIn(82, mastery_service._PROVISIONAL_MASTERY_UPDATES)

    def test_estimate_waits_for_three_real_gain_samples(self):
        baseline = {
            82: {
                "championLevel": 6,
                "championPoints": 33059,
                "championPointsUntilNextLevel": 1000,
            },
        }
        mastery_service._MATCH_MASTERY_SNAPSHOT = baseline
        for game_id, gain in ((1, 400), (2, 533)):
            self.assertIsNone(mastery_service._record_observed_mastery_gain({
                "gameId": game_id,
                "championId": 82,
                "championPointsGained": gain,
            }))

        with patch.object(
            mastery_service,
            "_read_current_champion_mastery",
            return_value=(None, None),
        ):
            pending, status = mastery_service._estimate_post_game_mastery_update(3, 82)

        self.assertEqual(status, 200)
        self.assertFalse(pending["available"])
        self.assertEqual(pending["observedGainSamples"], 2)
        self.assertEqual(pending["requiredGainSamples"], 3)

        self.assertIsNone(mastery_service._record_observed_mastery_gain({
            "gameId": 3,
            "championId": 82,
            "championPointsGained": 700,
        }))
        with patch.object(
            mastery_service,
            "_read_current_champion_mastery",
            return_value=(None, None),
        ):
            estimated, status = mastery_service._estimate_post_game_mastery_update(4, 82)

        self.assertEqual(status, 200)
        self.assertTrue(estimated["available"])
        self.assertTrue(estimated["isEstimated"])
        self.assertEqual(estimated["championPointsGained"], 533)
        self.assertEqual(estimated["championPointsUntilNextLevelAfterGame"], 467)
        self.assertEqual(estimated["estimateSampleCount"], 3)
        with open(mastery_service._MASTERY_GAIN_HISTORY_PATH, "r", encoding="utf-8") as history_file:
            samples = json.load(history_file)
        self.assertEqual(len(samples), 3)

    def test_estimate_requires_a_match_start_snapshot(self):
        for game_id, gain in ((1, 400), (2, 533), (3, 700)):
            mastery_service._record_observed_mastery_gain({
                "gameId": game_id,
                "championId": 82,
                "championPointsGained": gain,
            })

        pending, status = mastery_service._estimate_post_game_mastery_update(4, 82)

        self.assertEqual(status, 200)
        self.assertFalse(pending["available"])
        self.assertEqual(pending["observedGainSamples"], 3)
        self.assertEqual(pending["pendingReason"], "missing-match-snapshot")

    def test_estimated_gain_updates_points_without_inventing_level_or_tokens(self):
        game_stats = {
            "gameId": 45678,
            "localPlayer": {"championId": 236},
        }
        stale_mastery = [{
            "championId": 236,
            "championLevel": 11,
            "championPoints": 116017,
            "championPointsUntilNextLevel": 0,
            "markRequiredForNextLevel": 2,
            "tokensEarned": 1,
        }]
        mastery_service._MATCH_MASTERY_SNAPSHOT = {
            236: {"championLevel": 11, "championPoints": 116017},
        }
        for game_id, gain in ((1, 400), (2, 533), (3, 700)):
            mastery_service._record_observed_mastery_gain({
                "gameId": game_id,
                "championId": 236,
                "championPointsGained": gain,
            })

        with patch.object(
            mastery_service,
            "_get_lcu_response",
            side_effect=[
                (FakeResponse(200, game_stats), None),
                (FakeResponse(404, {}), None),
                (FakeResponse(200, stale_mastery), None),
                (FakeResponse(200, stale_mastery), None),
            ],
        ):
            update, update_status = mastery_service.get_post_game_mastery_update()
            data, mastery_status = mastery_service.get_mastery_data(
                {236: "Lucian"},
                {},
                "test",
            )

        lucian = data["champions"][0]
        self.assertEqual(update_status, 200)
        self.assertTrue(update["isEstimated"])
        self.assertEqual(update["championPointsGained"], 533)
        self.assertEqual(mastery_status, 200)
        self.assertEqual(lucian["championPoints"], 116550)
        self.assertEqual(lucian["championLevel"], 11)
        self.assertEqual(lucian["markRequiredForNextLevel"], 2)
        self.assertEqual(lucian["tokensEarned"], 1)
        self.assertTrue(lucian["isProvisional"])
        self.assertTrue(lucian["isEstimated"])
        self.assertEqual(lucian["estimateSampleCount"], 3)

    def test_missing_update_uses_exact_delta_when_lcu_totals_have_caught_up(self):
        game_stats = {
            "gameId": 99887,
            "localPlayer": {"championId": 82},
        }
        updated_mastery = [{
            "championId": 82,
            "championLevel": 6,
            "championPoints": 33592,
            "championPointsUntilNextLevel": 1767,
            "markRequiredForNextLevel": 0,
            "tokensEarned": 0,
        }]
        mastery_service._MATCH_MASTERY_SNAPSHOT = {
            82: {"championLevel": 6, "championPoints": 33059},
        }

        with patch.object(
            mastery_service,
            "_get_lcu_response",
            side_effect=[
                (FakeResponse(200, game_stats), None),
                (FakeResponse(404, {}), None),
                (FakeResponse(200, updated_mastery), None),
            ],
        ):
            update, status = mastery_service.get_post_game_mastery_update()

        self.assertEqual(status, 200)
        self.assertTrue(update["available"])
        self.assertEqual(update["source"], "observed-delta")
        self.assertEqual(update["championPointsGained"], 533)
        self.assertFalse(update.get("isEstimated", False))
        with open(mastery_service._MASTERY_GAIN_HISTORY_PATH, "r", encoding="utf-8") as history_file:
            samples = json.load(history_file)
        self.assertEqual(samples, [{
            "gameId": 99887,
            "championId": 82,
            "pointsGained": 533,
        }])

    def test_gameflow_start_captures_the_last_known_mastery_totals(self):
        mastery_service._LAST_MASTERY_SNAPSHOT = {
            236: {"championLevel": 11, "championPoints": 116017},
        }
        with patch.object(
            mastery_service,
            "_get_lcu_response",
            return_value=(FakeResponse(200, "InProgress"), None),
        ):
            phase, status = mastery_service.get_gameflow_phase()

        self.assertEqual(status, 200)
        self.assertEqual(phase["phase"], "InProgress")
        self.assertEqual(mastery_service._MATCH_MASTERY_SNAPSHOT[236]["championPoints"], 116017)


if __name__ == "__main__":
    unittest.main()
