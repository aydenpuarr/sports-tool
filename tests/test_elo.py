from src.models.elo import EloRatings, expected_score, goal_diff_multiplier


def test_default_rating_is_1500():
    elo = EloRatings()
    assert elo.get("Nowhere") == 1500.0


def test_expected_score_symmetric():
    assert abs(expected_score(1500, 1500) - 0.5) < 1e-9
    assert expected_score(1600, 1500) > 0.5
    assert expected_score(1400, 1500) < 0.5


def test_goal_diff_multiplier_scaling():
    assert goal_diff_multiplier(0) == 1.0
    assert goal_diff_multiplier(1) == 1.0
    assert goal_diff_multiplier(2) == 1.5
    assert goal_diff_multiplier(4) > goal_diff_multiplier(2)


def test_winner_gains_rating_loser_loses_equal_amount():
    elo = EloRatings()
    elo.update_match("A", "B", 2, 0, competition="qualifier")
    assert elo.get("A") > 1500.0
    assert elo.get("B") < 1500.0
    assert abs((elo.get("A") - 1500.0) + (elo.get("B") - 1500.0)) < 1e-9


def test_world_cup_final_k_factor_moves_rating_more_than_friendly():
    elo_wc = EloRatings()
    elo_wc.update_match("A", "B", 2, 0, competition="world_cup_final")
    elo_friendly = EloRatings()
    elo_friendly.update_match("A", "B", 2, 0, competition="friendly")
    assert (elo_wc.get("A") - 1500.0) > (elo_friendly.get("A") - 1500.0)


def test_win_draw_loss_probabilities_sum_to_one():
    elo = EloRatings()
    elo.update_match("A", "B", 3, 0, competition="qualifier")
    home, draw, away = elo.win_draw_loss_probabilities("A", "B")
    assert abs(home + draw + away - 1.0) < 1e-9
    assert home > away  # A is rated higher after the win
