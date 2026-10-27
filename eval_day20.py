from app.evaluator import evaluate_player_analysis
from services import count_players, get_high_level_players


DAY18_BAD = """
服务器3共有3名模拟玩家，最低等级为50，高等级玩家为2名。
高等级玩家占总玩家数约66.7%。
未提供高等级玩家的等级判定标准。
"""


DAY19_BAD = """
服务器ID：3。
模拟玩家总数：3人。
最低等级：50级。
高等级玩家：2人，占总人数约66.7%。
当前统计中，所有玩家等级均不低于50级。
具体等级门槛未提供。
"""


GOOD_ANSWER = """
服务器3共有3名模拟玩家。
等级不低于50的玩家有2人。
高等级玩家占比为2÷3×100%，约66.7%。
50是高等级筛选门槛，不代表全体玩家的最低等级。
缺少新增玩家及后续活跃记录，无法计算留存率。
"""


def main() -> None:
    server_id = 3
    min_level = 50

    total = count_players(server_id)
    high_level = len(
        get_high_level_players(server_id, min_level)
    )

    cases = [
        ("Day18历史错误", DAY18_BAD),
        ("Day19历史错误", DAY19_BAD),
        ("正确示例", GOOD_ANSWER),
    ]

    for name, answer in cases:
        result = evaluate_player_analysis(
            answer,
            total_players=total,
            high_level_players=high_level,
            min_level=min_level,
        )

        print(f"\n=== {name} ===")
        print("是否通过：", result.passed)
        print("评分：", result.score)

        if result.issues:
            print("发现的问题：")

            for issue in result.issues:
                print("-", issue)
        else:
            print("没有发现当前规则覆盖的错误")


if __name__ == "__main__":
    main()