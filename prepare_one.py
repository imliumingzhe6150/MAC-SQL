import json
from pathlib import Path

# 读取完整的 Spider 问题文件
input_path = Path("data/spider/dev.json")

with open(input_path, "r", encoding="utf-8") as f:
    examples = json.load(f)

# 找到我们要练习的那道题
for index, item in enumerate(examples):
    if (
        item["db_id"] == "concert_singer"
        and item["question"].strip() == "List all song names by singers above the average age."
    ):
        one_item = item.copy()

        # 单题文件中，它的位置是 0
        one_item["question_id"] = 0

        # 保存在原文件旁边，不改动原始 dev.json
        output_path = input_path.with_name("dev_nested.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([one_item], f, ensure_ascii=False, indent=2)

        print(f"原始样本位置：{index}")
        print(f"问题：{one_item['question']}")
        print(f"已保存到：{output_path}")
        break
else:
    raise ValueError("没有找到这道题，请检查输入文件")