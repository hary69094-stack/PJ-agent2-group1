"""Generate 38 multi-turn conversation test cases for PJ-AGENT-2.

四类分层（ADR 0008）：
  类别1: 事实分散记忆 (12组)  — 事实分散在多轮不同话题中
  类别2: 渐进更新/覆盖记忆 (10组) — 同一信息多次修正
  类别3: 跨话题干扰记忆 (8组)  — 话题切换后跳回
  类别4: 负面样本/不需要记忆 (8组含额外组) — 寒暄/临时闲聊

每组对话的最后一轮包含 checklist:
  {"fact": "描述", "acceptable": ["可接受答案1", "答案2", ...]}

输出: data/conversation_tests.jsonl
"""

import json
import os
import sys

OUTPUT = os.path.join(os.path.dirname(__file__), "conversation_tests.jsonl")

test_cases = []


# ── 工具函数 ──────────────────────────────────────────────────────────

def make_turn(turn_num, user_msg, facts_introduced=None, checklist=None):
    """构造一轮对话。

    Args:
        turn_num: 轮次编号
        user_msg: 用户消息
        facts_introduced: 本轮引入的可记忆事实（用于日志/分析）
        checklist: 检核清单 [{"fact": str, "acceptable": [str, ...]}, ...]
                   仅在最后一轮（检测轮）设置
    """
    t = {
        "turn": turn_num,
        "user": user_msg,
        "expected_facts_introduced": facts_introduced or [],
    }
    if checklist:
        t["checklist"] = checklist
    return t


# ======================================================================
# 类别1: 事实分散记忆 (12组)
# ======================================================================

# conf_001 — 基本身份分散
test_cases.append({
    "test_id": "conv_001",
    "title": "基本身份信息分散",
    "description": "用户在对话中分散提及姓名、年龄、职业、家乡，末尾集中检核",
    "category": "fact_scatter",
    "difficulty": "easy",
    "total_turns": 9,
    "turns": [
        make_turn(1, "你好！我叫张明，很高兴认识你。",
                  ["姓名: 张明"]),
        make_turn(2, "今天天气真不错，适合出去走走。", []),
        make_turn(3, "我今年25岁，刚工作没多久。",
                  ["年龄: 25"]),
        make_turn(4, "能帮我推荐一些适合新人的理财方法吗？", []),
        make_turn(5, "我目前在杭州一家互联网公司做产品经理。",
                  ["地点: 杭州", "职业: 产品经理"]),
        make_turn(6, "产品经理这个岗位有什么需要特别注意的地方吗？", []),
        make_turn(7, "对了，我老家是四川成都的，不是杭州本地人。",
                  ["家乡: 成都"]),
        make_turn(8, "成都和杭州的生活节奏差别还挺大的。", []),
        make_turn(9, "我想确认一下，你能告诉我你记得的关于我的信息吗？我叫什么、多大、在哪工作、做什么、老家哪的？",
                  [],
                  [{"fact": "姓名: 张明", "acceptable": ["张明"]},
                   {"fact": "年龄: 25", "acceptable": ["25", "二十五"]},
                   {"fact": "地点: 杭州", "acceptable": ["杭州"]},
                   {"fact": "职业: 产品经理", "acceptable": ["产品经理"]},
                   {"fact": "家乡: 成都", "acceptable": ["成都", "四川成都"]}]),
    ],
})

# conv_002 — 偏好分散
test_cases.append({
    "test_id": "conv_002",
    "title": "饮食与生活习惯偏好",
    "description": "用户在多轮中分散提及饮食限制、作息、运动习惯",
    "category": "fact_scatter",
    "difficulty": "medium",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我最近在减肥，想控制一下饮食。",
                  ["目标: 减肥"]),
        make_turn(2, "有什么低卡路里又好吃的菜推荐吗？", []),
        make_turn(3, "对了，我对花生过敏，所以任何含花生的东西都不能吃。",
                  ["过敏: 花生"]),
        make_turn(4, "我一般晚上11点睡觉，早上6点半起床。",
                  ["作息: 晚11早6:30"]),
        make_turn(5, "早起适合做些什么运动呢？", []),
        make_turn(6, "我每周会跑步三次，每次大概5公里。",
                  ["运动: 每周跑步三次5公里"]),
        make_turn(7, "跑步前后应该怎么拉伸？", []),
        make_turn(8, "我也比较喜欢游泳，但最近泳池都关门了。",
                  ["爱好: 游泳"]),
        make_turn(9, "有没有其他不伤膝盖的有氧运动推荐？", []),
        make_turn(10, "帮我总结一下：我的减肥目标、饮食禁忌、作息时间和运动习惯？",
                  [],
                  [{"fact": "目标: 减肥", "acceptable": ["减肥"]},
                   {"fact": "过敏: 花生", "acceptable": ["花生过敏", "花生"]},
                   {"fact": "作息: 晚11早6点半", "acceptable": ["11点", "6点半", "6:30"]},
                   {"fact": "运动: 跑步每周三次", "acceptable": ["跑步", "5公里", "三次"]}]),
    ],
})

# conv_003 — 教育与职业路径分散
test_cases.append({
    "test_id": "conv_003",
    "title": "教育与职业路径",
    "description": "学校、专业、毕业年份、工作转换分散在多轮",
    "category": "fact_scatter",
    "difficulty": "medium",
    "total_turns": 11,
    "turns": [
        make_turn(1, "我是复旦大学计算机系的，2019年本科毕业。",
                  ["学校: 复旦大学", "专业: 计算机", "毕业: 2019"]),
        make_turn(2, "毕业后我先去了字节跳动做后端开发。",
                  ["首份工作: 字节跳动后端开发"]),
        make_turn(3, "后端开发用什么语言比较好？我当时主要用Go。", []),
        make_turn(4, "在字节工作了两年半后，我跳到了蚂蚁集团。",
                  ["跳槽: 蚂蚁集团"]),
        make_turn(5, "蚂蚁那边做的是风控相关的算法。",
                  ["方向: 风控算法"]),
        make_turn(6, "风控算法对数学要求高吗？", []),
        make_turn(7, "我现在纠结要不要去读个硕士，可能去新加坡国立。",
                  ["计划: 去新加坡国立读硕士"]),
        make_turn(8, "新加坡国立计算机硕士需要什么申请条件？", []),
        make_turn(9, "学费大概多少？性价比高吗？", []),
        make_turn(10, "如果要留学的话我需要提前多久准备？", []),
        make_turn(11, "回顾一下我的教育和工作经历：本科学校、专业、毕业年份、第一份工作和现在的工作？",
                  [],
                  [{"fact": "学校: 复旦大学", "acceptable": ["复旦大学", "复旦"]},
                   {"fact": "专业: 计算机", "acceptable": ["计算机"]},
                   {"fact": "毕业: 2019", "acceptable": ["2019"]},
                   {"fact": "首份工作: 字节跳动", "acceptable": ["字节跳动", "字节"]},
                   {"fact": "现在: 蚂蚁集团", "acceptable": ["蚂蚁", "蚂蚁集团"]}]),
    ],
})

# conv_004 — 家庭成员信息
test_cases.append({
    "test_id": "conv_004",
    "title": "家庭信息",
    "description": "用户在多轮闲谈中逐步透露家庭成员信息",
    "category": "fact_scatter",
    "difficulty": "medium",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我今天得早点回去，家里孩子还小。", []),
        make_turn(2, "我儿子今年5岁，刚上幼儿园大班。",
                  ["儿子: 5岁"]),
        make_turn(3, "幼儿园有什么好的教育方法可以推荐吗？", []),
        make_turn(4, "我还有一个女儿，今年3岁，特别调皮。",
                  ["女儿: 3岁"]),
        make_turn(5, "两个孩子的年龄差比较小，经常打架。", []),
        make_turn(6, "我老婆是中学语文老师，工作也挺忙的。",
                  ["配偶: 中学语文老师"]),
        make_turn(7, "教师这个职业现在压力大吗？", []),
        make_turn(8, "我们家还养了一只金毛，叫豆豆，快两岁了。",
                  ["宠物: 金毛豆豆2岁"]),
        make_turn(9, "养狗需要注意什么？特别是和孩子相处。", []),
        make_turn(10, "给我整理一下我的家庭信息：有几个孩子、分别多大、配偶职业、宠物叫什么？",
                  [],
                  [{"fact": "儿子: 5岁", "acceptable": ["5岁", "五岁", "儿子"]},
                   {"fact": "女儿: 3岁", "acceptable": ["3岁", "三岁", "女儿"]},
                   {"fact": "配偶: 语文老师", "acceptable": ["老师", "语文"]},
                   {"fact": "宠物: 金毛豆豆", "acceptable": ["豆豆", "金毛"]}]),
    ],
})

# conv_005 — 技术栈分散
test_cases.append({
    "test_id": "conv_005",
    "title": "个人技术栈",
    "description": "用户分散提及编程语言、框架、工具偏好",
    "category": "fact_scatter",
    "difficulty": "easy",
    "total_turns": 8,
    "turns": [
        make_turn(1, "我主要用Python做后端开发，偶尔也用Go。",
                  ["语言: Python, Go"]),
        make_turn(2, "Python和Go各自的优势是什么？", []),
        make_turn(3, "框架的话我比较喜欢FastAPI，轻量又快速。",
                  ["框架: FastAPI"]),
        make_turn(4, "数据库我用PostgreSQL为主，偶尔用Redis做缓存。",
                  ["数据库: PostgreSQL, Redis"]),
        make_turn(5, "PostgreSQL和MySQL哪个更适合高并发场景？", []),
        make_turn(6, "部署方面我习惯用Docker加Kubernetes。",
                  ["部署: Docker+Kubernetes"]),
        make_turn(7, "有没有更好的容器编排工具推荐？", []),
        make_turn(8, "总结一下我的技术栈：语言、框架、数据库、部署工具？",
                  [],
                  [{"fact": "语言: Python", "acceptable": ["Python"]},
                   {"fact": "框架: FastAPI", "acceptable": ["FastAPI"]},
                   {"fact": "数据库: PostgreSQL", "acceptable": ["PostgreSQL", "postgres"]},
                   {"fact": "部署: Docker", "acceptable": ["Docker", "Kubernetes", "k8s"]}]),
    ],
})

# conv_006 — 健康数据
test_cases.append({
    "test_id": "conv_006",
    "title": "健康与医疗信息",
    "description": "用户分散透露健康状况、药物、体检数据",
    "category": "fact_scatter",
    "difficulty": "medium",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我有二型糖尿病，所以饮食上需要特别注意。",
                  ["疾病: 二型糖尿病"]),
        make_turn(2, "糖尿病人能吃水果吗？特别是西瓜。", []),
        make_turn(3, "我每天早上要测空腹血糖，最近都在6.2左右。",
                  ["空腹血糖: 6.2"]),
        make_turn(4, "血糖6.2算控制得怎么样？", []),
        make_turn(5, "我目前在吃二甲双胍，一天两次，每次500毫克。",
                  ["药物: 二甲双胍500mg每日两次"]),
        make_turn(6, "二甲双胍长期吃有什么副作用吗？", []),
        make_turn(7, "另外我的膝盖不太好，去年半月板受过伤。",
                  ["伤病史: 膝盖半月板损伤"]),
        make_turn(8, "半月板损伤还能跑步吗？", []),
        make_turn(9, "医生建议我减轻体重，我身高175，体重88公斤。",
                  ["身高175 体重88"]),
        make_turn(10, "整理一下我的健康状况：什么病、血糖值、吃什么药、膝盖问题和体重目标？",
                  [],
                  [{"fact": "疾病: 糖尿病", "acceptable": ["糖尿病", "二型"]},
                   {"fact": "药物: 二甲双胍", "acceptable": ["二甲双胍"]},
                   {"fact": "膝盖: 半月板伤", "acceptable": ["膝盖", "半月板"]},
                   {"fact": "体重: 88公斤", "acceptable": ["88", "88公斤"]}]),
    ],
})

# conv_007 — 旅行计划
test_cases.append({
    "test_id": "conv_007",
    "title": "旅行计划细节",
    "description": "用户逐步透露旅行目的地、预算、日期、同行人",
    "category": "fact_scatter",
    "difficulty": "medium",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我在计划一次日本旅行，大概去7天。",
                  ["目的地: 日本", "时长: 7天"]),
        make_turn(2, "日本有什么必去的景点吗？", []),
        make_turn(3, "预算大概是2万人民币，包括机票和住宿。",
                  ["预算: 2万"]),
        make_turn(4, "2万去日本够不够？需要再追加吗？", []),
        make_turn(5, "计划是10月15号出发，那时候日本天气正好。",
                  ["出发: 10月15日"]),
        make_turn(6, "10月的日本需要带什么衣服？", []),
        make_turn(7, "我是和我女朋友一起去，算是纪念日旅行。",
                  ["同行: 女朋友"]),
        make_turn(8, "纪念日旅行有什么浪漫的推荐吗？", []),
        make_turn(9, "酒店的话想住好一点，有没有推荐？", []),
        make_turn(10, "再帮我确认一下行程：去哪、几天、什么时候出发、预算多少、和谁一起去？",
                  [],
                  [{"fact": "目的地: 日本", "acceptable": ["日本"]},
                   {"fact": "时长: 7天", "acceptable": ["7天", "七天"]},
                   {"fact": "出发: 10月15日", "acceptable": ["10月15", "10.15"]},
                   {"fact": "预算: 2万", "acceptable": ["2万", "两万"]},
                   {"fact": "同行: 女朋友", "acceptable": ["女朋友"]}]),
    ],
})

# conv_008 — 分散事实12轮
test_cases.append({
    "test_id": "conv_008",
    "title": "12轮长对话事实分散",
    "description": "超长对话中分散更多事实，仅短期 N=6 会有压力",
    "category": "fact_scatter",
    "difficulty": "hard",
    "total_turns": 12,
    "turns": [
        make_turn(1, "我叫陈芳，在一家外企做HR。",
                  ["姓名: 陈芳", "职业: HR"]),
        make_turn(2, "我在北京朝阳区上班，住在通州。", []),
        make_turn(3, "每天通勤来回要两个多小时，挺累的。", []),
        make_turn(4, "我的母校是中国人民大学，学的是人力资源管理。",
                  ["学校: 中国人民大学", "专业: 人力资源管理"]),
        make_turn(5, "有什么办法减少通勤时间吗？", []),
        make_turn(6, "我是广东人，来北京工作5年了。",
                  ["家乡: 广东"]),
        make_turn(7, "北方和南方的饮食差异太大了。", []),
        make_turn(8, "我养了一只英短猫，叫团子，已经3岁了。",
                  ["宠物: 英短猫团子3岁"]),
        make_turn(9, "养猫后家里全是毛，怎么清理？", []),
        make_turn(10, "我平时最大的爱好是弹钢琴，学了大概十年了。",
                  ["爱好: 弹钢琴10年"]),
        make_turn(11, "最近在练肖邦的夜曲，特别美。", []),
        make_turn(12, "给我一个完整的个人档案：姓名、职业、母校、家乡、宠物和爱好？",
                  [],
                  [{"fact": "姓名: 陈芳", "acceptable": ["陈芳"]},
                   {"fact": "职业: HR", "acceptable": ["HR", "人力资源"]},
                   {"fact": "学校: 中国人民大学", "acceptable": ["人大", "中国人民大学"]},
                   {"fact": "家乡: 广东", "acceptable": ["广东"]},
                   {"fact": "宠物: 英短猫", "acceptable": ["团子", "英短", "猫"]},
                   {"fact": "爱好: 弹钢琴", "acceptable": ["钢琴", "弹钢琴"]}]),
    ],
})

# conv_009 — 学习目标
test_cases.append({
    "test_id": "conv_009",
    "title": "学习目标与计划",
    "description": "用户分散透露学习方向、考试日期、目标分数",
    "category": "fact_scatter",
    "difficulty": "easy",
    "total_turns": 8,
    "turns": [
        make_turn(1, "我在准备雅思考试，目标是总分7.0。",
                  ["考试: 雅思", "目标: 7.0"]),
        make_turn(2, "雅思和托福哪个更实用？", []),
        make_turn(3, "考试日期定在8月20号，还有两个月左右。",
                  ["日期: 8月20日"]),
        make_turn(4, "口语部分我比较弱，特别是Part 3。",
                  ["弱点: 口语Part3"]),
        make_turn(5, "目前的模考得分大概是听力6.5、阅读7.0、写作6.0、口语5.5。",
                  ["模考: L6.5 R7.0 W6.0 S5.5"]),
        make_turn(6, "怎么快速提高口语分数？", []),
        make_turn(7, "我每天大概能学3个小时英语。",
                  ["每日学习: 3小时"]),
        make_turn(8, "根据我的情况——考试类型、目标分数、考试日期和薄弱项——给我一个复习计划。",
                  [],
                  [{"fact": "考试: 雅思", "acceptable": ["雅思"]},
                   {"fact": "目标: 7.0", "acceptable": ["7", "7.0"]},
                   {"fact": "日期: 8月20", "acceptable": ["8月20", "8.20"]},
                   {"fact": "弱点: 口语", "acceptable": ["口语"]}]),
    ],
})

# conv_010 — 项目任务
test_cases.append({
    "test_id": "conv_010",
    "title": "项目任务信息",
    "description": "用户分散透露项目需求、截止日期、团队成员",
    "category": "fact_scatter",
    "difficulty": "medium",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我们团队在做一个人工智能导论课的项目。",
                  ["项目: 人工智能导论课"]),
        make_turn(2, "项目是关于带长期记忆的对话Agent。",
                  ["主题: 长期记忆Agent"]),
        make_turn(3, "队友有严泳垚和范文宇，我是组长。", []),
        make_turn(4, "截止日期是7月15号，还有一个月。",
                  ["截止: 7月15日"]),
        make_turn(5, "我们需要用Python实现，用DeepSeek API。",
                  ["语言: Python", "API: DeepSeek"]),
        make_turn(6, "你觉得用什么向量库比较好？FAISS还是Chroma？", []),
        make_turn(7, "老师要求至少30组测试集、两种评估指标。",
                  ["要求: 30组测试集 双指标"]),
        make_turn(8, "报告需要PDF格式，代码要可复现。", []),
        make_turn(9, "中期汇报我们已经有雏形了，期末要完整演示。", []),
        make_turn(10, "总结一下项目：主题、语言、API、截止日期和评估要求？",
                  [],
                  [{"fact": "项目: 长期记忆Agent", "acceptable": ["Agent", "长期记忆"]},
                   {"fact": "语言: Python", "acceptable": ["Python"]},
                   {"fact": "截止: 7月15", "acceptable": ["7月15", "7.15"]},
                   {"fact": "要求: 30组测试", "acceptable": ["30", "30组"]}]),
    ],
})

# conv_011 — 社交信息
test_cases.append({
    "test_id": "conv_011",
    "title": "社交与联系方式",
    "description": "用户透露微信号、邮箱、社交媒体偏好",
    "category": "fact_scatter",
    "difficulty": "medium",
    "total_turns": 8,
    "turns": [
        make_turn(1, "我主要用微信联系工作，微信号是 zhangming_cn。",
                  ["微信: zhangming_cn"]),
        make_turn(2, "微信和QQ哪个更好用？", []),
        make_turn(3, "邮箱的话，工作邮箱是 zhangming@example.com。",
                  ["邮箱: zhangming@example.com"]),
        make_turn(4, "邮件礼仪有什么要注意的？", []),
        make_turn(5, "我平时刷微博比较多，知乎也常看。",
                  ["社交: 微博 知乎"]),
        make_turn(6, "知乎上的高质量内容越来越少了。", []),
        make_turn(7, "LinkedIn我也有，但不太活跃。", []),
        make_turn(8, "告诉我你记住的我的联系方式：微信、邮箱、常用的社交平台？",
                  [],
                  [{"fact": "微信: zhangming_cn", "acceptable": ["zhangming_cn", "zhangming"]},
                   {"fact": "邮箱: zhangming@example.com", "acceptable": ["zhangming@example.com", "zhangming@"]},
                   {"fact": "社交: 微博", "acceptable": ["微博"]}]),
    ],
})

# conv_012 — 偏好的复合场景
test_cases.append({
    "test_id": "conv_012",
    "title": "多维度偏好",
    "description": "分散在10轮中的颜色、音乐、电影、书籍、运动偏好",
    "category": "fact_scatter",
    "difficulty": "hard",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我很喜欢蓝色系，衣服大多是蓝色和白色。",
                  ["颜色: 蓝色"]),
        make_turn(2, "音乐方面，我特别喜欢周杰伦，从中学就开始听了。",
                  ["音乐: 周杰伦"]),
        make_turn(3, "周杰伦哪张专辑最好听？", []),
        make_turn(4, "我喜欢科幻电影，最喜欢的是《星际穿越》。",
                  ["电影: 星际穿越"]),
        make_turn(5, "《星际穿越》的科学顾问是诺贝尔物理学奖得主。", []),
        make_turn(6, "最近在读《三体》，特别喜欢刘慈欣的构思。",
                  ["书籍: 三体"]),
        make_turn(7, "运动的话我打羽毛球比较多，每周打一次。",
                  ["运动: 羽毛球每周一次"]),
        make_turn(8, "羽毛球有什么好的球拍品牌推荐？", []),
        make_turn(9, "我还喜欢喝咖啡，只喝美式不加糖。",
                  ["饮品: 美式咖啡不加糖"]),
        make_turn(10, "整理一下我的所有偏好：颜色、最喜欢的歌手、电影、在看的书、运动、饮品？",
                  [],
                  [{"fact": "颜色: 蓝色", "acceptable": ["蓝色"]},
                   {"fact": "歌手: 周杰伦", "acceptable": ["周杰伦"]},
                   {"fact": "电影: 星际穿越", "acceptable": ["星际穿越"]},
                   {"fact": "书籍: 三体", "acceptable": ["三体"]},
                   {"fact": "运动: 羽毛球", "acceptable": ["羽毛球"]},
                   {"fact": "饮品: 美式", "acceptable": ["美式"]}]),
    ],
})


# ======================================================================
# 类别2: 渐进更新/覆盖记忆 (10组)
# ======================================================================

# conv_013 — 年龄修正
test_cases.append({
    "test_id": "conv_013",
    "title": "年龄修正",
    "description": "用户先说25岁，后改口为28岁。Agent应记住最新信息。",
    "category": "progressive_update",
    "difficulty": "easy",
    "total_turns": 7,
    "turns": [
        make_turn(1, "你好，我叫李明，今年25岁。",
                  ["姓名: 李明", "年龄: 25"]),
        make_turn(2, "25岁该考虑买房了吗？", []),
        make_turn(3, "等等，我刚才说错了——我实际是28岁，不是25。不好意思记错了。",
                  ["年龄更新: 28"]),
        make_turn(4, "28岁买房和25岁比起来哪个阶段更合适？", []),
        make_turn(5, "房贷利率现在是多少？", []),
        make_turn(6, "首付一般需要准备多少比例？", []),
        make_turn(7, "对了，我今年到底多大？",
                  [],
                  [{"fact": "年龄: 28（非25）", "acceptable": ["28", "二十八", "28岁"]}]),
    ],
})

# conv_014 — 职业变更
test_cases.append({
    "test_id": "conv_014",
    "title": "职业变更",
    "description": "用户从「教师」变更为「程序员」，Agent应更新记忆",
    "category": "progressive_update",
    "difficulty": "medium",
    "total_turns": 8,
    "turns": [
        make_turn(1, "我是一名中学数学老师，教了五年了。",
                  ["职业: 数学老师"]),
        make_turn(2, "当老师最大的挑战是什么？", []),
        make_turn(3, "其实我去年已经转行了。现在在一家AI公司做开发工程师。",
                  ["职业更新: 开发工程师"]),
        make_turn(4, "从教师转到技术岗位容易吗？", []),
        make_turn(5, "我主要用Python，学了大概一年左右。", []),
        make_turn(6, "AI行业的前景怎么样？", []),
        make_turn(7, "公司用的技术栈还挺先进的。", []),
        make_turn(8, "我现在是做什么工作的？",
                  [],
                  [{"fact": "职业: 开发工程师（非教师）", "acceptable": ["开发", "工程师", "AI公司", "程序员"]}]),
    ],
})

# conv_015 — 婚恋状态变化
test_cases.append({
    "test_id": "conv_015",
    "title": "婚姻状态更新",
    "description": "用户从「单身」更新为「已婚」，Agent应使用最新状态",
    "category": "progressive_update",
    "difficulty": "medium",
    "total_turns": 9,
    "turns": [
        make_turn(1, "我先简单介绍一下，我单身，所以时间安排比较自由。",
                  ["状态: 单身"]),
        make_turn(2, "单身有什么适合的周末活动？", []),
        make_turn(3, "我之前说单身其实不对——我上个月刚结婚了。一直忘了更新这个信息。",
                  ["状态更新: 已婚"]),
        make_turn(4, "结婚后生活方式有什么变化吗？", []),
        make_turn(5, "我们打算去马尔代夫度蜜月。",
                  ["计划: 马尔代夫蜜月"]),
        make_turn(6, "蜜月旅行一般几天比较合适？", []),
        make_turn(7, "预算大概5万左右。", []),
        make_turn(8, "马尔代夫哪个季节去最好？", []),
        make_turn(9, "我现在是什么婚姻状态？",
                  [],
                  [{"fact": "状态: 已婚（非单身）", "acceptable": ["已婚", "结婚了", "刚结婚"]}]),
    ],
})

# conv_016 — 饮食偏好演进
test_cases.append({
    "test_id": "conv_016",
    "title": "饮食偏好多次变更",
    "description": "用户从素食→鱼素→什么都吃，三段变化",
    "category": "progressive_update",
    "difficulty": "hard",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我吃素已经三年了，主要是为了健康。",
                  ["饮食: 素食"]),
        make_turn(2, "素食者怎么保证蛋白质摄入？", []),
        make_turn(3, "最近我觉得纯素有点难坚持，所以开始吃鱼了。",
                  ["饮食更新: 鱼素"]),
        make_turn(4, "吃鱼的话，三文鱼是不是营养最好的？", []),
        make_turn(5, "好吧我放弃了——我现在什么都吃，不再限制自己了。",
                  ["饮食更新: 无限制"]),
        make_turn(6, "恢复正常饮食后有什么需要注意的？", []),
        make_turn(7, "我想尝试一下牛排，有什么推荐？", []),
        make_turn(8, "几分熟比较合适初学者？", []),
        make_turn(9, "还有什么其他值得尝试的肉类？", []),
        make_turn(10, "我现在的饮食方式是什么？",
                  [],
                  [{"fact": "饮食: 无限制（什么都吃）", "acceptable": ["什么都吃", "无限制", "不限制", "吃肉"]}]),
    ],
})

# conv_017 — 地点迁移
test_cases.append({
    "test_id": "conv_017",
    "title": "居住地变更",
    "description": "从北京→上海，Agent应更新城市信息",
    "category": "progressive_update",
    "difficulty": "medium",
    "total_turns": 8,
    "turns": [
        make_turn(1, "我在北京工作了三年，做的是市场推广。",
                  ["地点: 北京", "职业: 市场推广"]),
        make_turn(2, "北京的市场推广行业竞争怎么样？", []),
        make_turn(3, "好消息！我拿到了上海的一个offer，下个月就要搬过去了。",
                  ["地点更新: 上海"]),
        make_turn(4, "上海和北京的生活成本哪个更高？", []),
        make_turn(5, "搬家有什么值得注意的吗？", []),
        make_turn(6, "我是从北京海淀搬到上海浦东。", []),
        make_turn(7, "浦东那边有什么好玩的？", []),
        make_turn(8, "我下个月之后会在哪个城市？",
                  [],
                  [{"fact": "地点: 上海（非北京）", "acceptable": ["上海"]}]),
    ],
})

# conv_018 — 姓名更正
test_cases.append({
    "test_id": "conv_018",
    "title": "姓名更正",
    "description": "用户先说了一个名字，后说是化名，告知真名",
    "category": "progressive_update",
    "difficulty": "easy",
    "total_turns": 6,
    "turns": [
        make_turn(1, "可以叫我小王，大家都这么叫。",
                  ["称呼: 小王"]),
        make_turn(2, "小王这个称呼有什么来历吗？", []),
        make_turn(3, "其实小王是化名，我的真名是王建国。网上习惯用化名。",
                  ["姓名更新: 王建国"]),
        make_turn(4, "为什么网上要用化名？", []),
        make_turn(5, "不过你还是叫我小王吧，习惯了。", []),
        make_turn(6, "我的真名是什么？",
                  [],
                  [{"fact": "姓名: 王建国", "acceptable": ["王建国"]}]),
    ],
})

# conv_019 — 联系方式变更
test_cases.append({
    "test_id": "conv_019",
    "title": "联系方式更新",
    "description": "用户更新手机号，Agent应记新号码",
    "category": "progressive_update",
    "difficulty": "medium",
    "total_turns": 9,
    "turns": [
        make_turn(1, "我的手机号是13800001234，有急事可以联系我。",
                  ["手机: 13800001234"]),
        make_turn(2, "现在用什么套餐比较划算？", []),
        make_turn(3, "我其实刚换了手机号，新号是13911115678。旧号不用了。",
                  ["手机更新: 13911115678"]),
        make_turn(4, "换号后需要通知哪些机构？", []),
        make_turn(5, "银行、社保这些都要重新绑定。", []),
        make_turn(6, "有没有什么办法批量修改绑定的手机号？", []),
        make_turn(7, "花了三天才把所有账号的手机号改完。", []),
        make_turn(8, "新号用了几天感觉还行。", []),
        make_turn(9, "你现在记得我的手机号是多少？",
                  [],
                  [{"fact": "手机: 13911115678（非旧号）", "acceptable": ["13911115678"]}]),
    ],
})

# conv_020 — 预算调整
test_cases.append({
    "test_id": "conv_020",
    "title": "预算多次调整",
    "description": "用户买车预算从10万→15万→12万，多次变动",
    "category": "progressive_update",
    "difficulty": "hard",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我想买辆车，预算大概10万左右。",
                  ["预算: 10万"]),
        make_turn(2, "10万以内有什么好的车型推荐？", []),
        make_turn(3, "想了下，预算可以提高到15万，选择多一些。",
                  ["预算更新: 15万"]),
        make_turn(4, "15万左右，有什么性价比高的SUV？", []),
        make_turn(5, "试驾了几款，感觉都不错。", []),
        make_turn(6, "仔细算了下，还是保守一点，预算定在12万吧。",
                  ["预算更新: 12万"]),
        make_turn(7, "12万的SUV和轿车比哪个更实用？", []),
        make_turn(8, "油耗也是考虑因素，最好在百公里7升以内。", []),
        make_turn(9, "有没有混动车型可以推荐？", []),
        make_turn(10, "我最终的买车预算是多少？",
                  [],
                  [{"fact": "预算: 12万（最新值）", "acceptable": ["12万", "十二万", "12"]}]),
    ],
})

# conv_021 — 健康状况变化
test_cases.append({
    "test_id": "conv_021",
    "title": "健康状况变化",
    "description": "用户从「有高血压」到「血压已控制正常」",
    "category": "progressive_update",
    "difficulty": "medium",
    "total_turns": 8,
    "turns": [
        make_turn(1, "我有高血压，平时要注意饮食，少盐少油。",
                  ["状况: 高血压"]),
        make_turn(2, "高血压患者适合做什么运动？", []),
        make_turn(3, "更新一下，经过半年调理，我的血压已经恢复正常了。医生说我不用再吃降压药了。",
                  ["状况更新: 血压已正常"]),
        make_turn(4, "血压正常后还需要定期测量吗？", []),
        make_turn(5, "我靠运动和饮食控制就降下来了。", []),
        make_turn(6, "但还是要注意保持健康的生活方式。", []),
        make_turn(7, "有什么推荐的清淡食谱？", []),
        make_turn(8, "我现在还有高血压吗？",
                  [],
                  [{"fact": "状况: 血压已正常（非高血压）", "acceptable": ["正常", "没有", "恢复了", "降下来"]}]),
    ],
})

# conv_022 — 学习进度更新
test_cases.append({
    "test_id": "conv_022",
    "title": "学习进度更新",
    "description": "用户从「刚开始学」更新为「已通过考试」",
    "category": "progressive_update",
    "difficulty": "easy",
    "total_turns": 7,
    "turns": [
        make_turn(1, "我刚报了一个Python数据分析的网课，零基础开始学。",
                  ["状态: 零基础学Python"]),
        make_turn(2, "数据分析需要什么数学基础？", []),
        make_turn(3, "好消息！我已经通过了初级数据分析师认证考试。",
                  ["状态更新: 已通过认证"]),
        make_turn(4, "现在想继续往深度学习的方面发展。", []),
        make_turn(5, "深度学习有什么推荐的学习路径？", []),
        make_turn(6, "需不需要先学线性代数？", []),
        make_turn(7, "我现在的学习阶段是什么？",
                  [],
                  [{"fact": "状态: 已通过认证（非零基础）", "acceptable": ["通过", "认证", "初级", "不是零基础"]}]),
    ],
})


# ======================================================================
# 类别3: 跨话题干扰记忆 (8组)
# ======================================================================

# conv_023 — 两话题混排
test_cases.append({
    "test_id": "conv_023",
    "title": "两话题交替混排",
    "description": "用户交替聊AI项目和生日宴策划，Agent不能混淆两个话题的信息",
    "category": "cross_topic",
    "difficulty": "medium",
    "total_turns": 12,
    "turns": [
        make_turn(1, "我正在做一个人工智能的NLP项目，在做情感分析。",
                  ["项目: NLP情感分析"]),
        make_turn(2, "另外我还得帮我妈策划她的60岁生日宴，她喜欢中餐。",
                  ["生日: 妈妈60岁中餐"]),
        make_turn(3, "情感分析用BERT还是LSTM比较好？", []),
        make_turn(4, "生日宴定多少人的规模合适？", []),
        make_turn(5, "我的训练数据大概有5万条标注评论。",
                  ["数据: 5万条"]),
        make_turn(6, "宴会预算大概1万，想控制在20人以内。",
                  ["预算: 1万 20人"]),
        make_turn(7, "数据预处理需要去停用词吗？", []),
        make_turn(8, "需要预订包间还是大厅？", []),
        make_turn(9, "模型评估我主要看F1分数。", []),
        make_turn(10, "要不要请一个主持人？", []),
        make_turn(11, "还需要准备蛋糕吗？", []),
        make_turn(12, "给我分别总结：AI项目——做什么任务、用什么模型、数据量、评估指标？生日宴——给谁办的、预算、人数？",
                  [],
                  [{"fact": "AI任务: 情感分析", "acceptable": ["情感分析"]},
                   {"fact": "AI数据: 5万条", "acceptable": ["5万"]},
                   {"fact": "生日主角: 妈妈60岁", "acceptable": ["妈妈", "60", "六十"]},
                   {"fact": "生日预算: 1万", "acceptable": ["1万", "一万"]}]),
    ],
})

# conv_024 — 三话题切换
test_cases.append({
    "test_id": "conv_024",
    "title": "三话题快速切换",
    "description": "代码调试→露营计划→宠物猫，三个话题交替",
    "category": "cross_topic",
    "difficulty": "hard",
    "total_turns": 15,
    "turns": [
        make_turn(1, "我在调试一个Python异步代码里的race condition。",
                  ["话题A: Python异步race condition"]),
        make_turn(2, "这周末我计划去长城附近露营。",
                  ["话题B: 周末长城露营"]),
        make_turn(3, "另外我的猫Luna最近总是呕吐，我很担心。",
                  ["话题C: 猫Luna呕吐"]),
        make_turn(4, "race condition我用的是asyncio.Lock但还是有问题。", []),
        make_turn(5, "秋天露营需要带什么装备？", []),
        make_turn(6, "猫呕吐需要马上去看兽医吗？", []),
        make_turn(7, "可能应该用asyncio.Queue代替Lock？", []),
        make_turn(8, "一个人去长城露营安全吗？", []),
        make_turn(9, "Luna今天一整天都没吃东西。", []),
        make_turn(10, "能给我看一下asyncio.Queue的用法示例吗？", []),
        make_turn(11, "北京附近还有哪些好的露营地？", []),
        make_turn(12, "给猫吃什么比较好消化？", []),
        make_turn(13, "OK让我总结一下今天聊的三个话题分别是什么。", []),
        make_turn(14, "最后确认：代码是什么问题、去哪露营、猫什么症状？",
                  [],
                  [{"fact": "代码: race condition异步", "acceptable": ["race condition", "异步", "asyncio"]},
                   {"fact": "露营: 长城", "acceptable": ["长城", "露营"]},
                   {"fact": "猫: Luna呕吐", "acceptable": ["Luna", "猫", "呕吐"]}]),
    ],
})

# conv_025 — 相似概念干扰
test_cases.append({
    "test_id": "conv_025",
    "title": "相似航班编号干扰",
    "description": "用户的航班号被多个相似编号包围",
    "category": "cross_topic",
    "difficulty": "hard",
    "total_turns": 12,
    "turns": [
        make_turn(1, "我的航班是CA1234，去东京，6月15号早上8点起飞。",
                  ["航班: CA1234 东京 6月15日"]),
        make_turn(2, "6月去东京要带什么？", []),
        make_turn(3, "我朋友的航班是CA1235，去京都，6月16号。", []),
        make_turn(4, "另一个同事坐CA1236去大阪，6月17号。", []),
        make_turn(5, "还有人坐CA1237去名古屋，6月18号。", []),
        make_turn(6, "东京和京都有什么区别？", []),
        make_turn(7, "我妹妹坐CA1238去札幌，不过和我无关。", []),
        make_turn(8, "要不要提前在网上办登机？", []),
        make_turn(9, "我的座位是经济舱20A。", []),
        make_turn(10, "行李限额是多少？", []),
        make_turn(11, "到了东京怎么去市区？", []),
        make_turn(12, "在所有航班里——我的航班号是什么、去哪、哪天？",
                  [],
                  [{"fact": "航班: CA1234（非其他）", "acceptable": ["CA1234"]},
                   {"fact": "目的地: 东京", "acceptable": ["东京"]},
                   {"fact": "日期: 6月15", "acceptable": ["6月15", "6.15"]}]),
    ],
})

# conv_026 — 先聊A后完全转B再跳回A
test_cases.append({
    "test_id": "conv_026",
    "title": "话题完全转换后跳回",
    "description": "用户先聊电影偏好，然后完全切换到工作话题，最后突然跳回电影",
    "category": "cross_topic",
    "difficulty": "medium",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我超级喜欢诺兰导演的电影，特别是《盗梦空间》和《星际穿越》。",
                  ["电影偏好: 诺兰 盗梦空间 星际穿越"]),
        make_turn(2, "你觉得《奥本海默》怎么样？", []),
        make_turn(3, "除了诺兰，我还喜欢大卫·芬奇的《搏击俱乐部》。",
                  ["其他偏好: 大卫·芬奇 搏击俱乐部"]),
        make_turn(4, "说回工作，我们公司最近在做数字化转型。", []),
        make_turn(5, "需要我负责整个数据分析平台的搭建。", []),
        make_turn(6, "数据库选型上，我在考虑用Snowflake还是BigQuery。", []),
        make_turn(7, "数据Pipeline的调度工具用什么比较好？Airflow？", []),
        make_turn(8, "整个项目预算大概50万，周期3个月。", []),
        make_turn(9, "团队有5个人，两个后端、一个前端、两个数据。", []),
        make_turn(10, "回到电影话题——我之前说我最喜欢的导演是谁来着？",
                  [],
                  [{"fact": "导演: 诺兰", "acceptable": ["诺兰"]},
                   {"fact": "电影: 盗梦空间", "acceptable": ["盗梦空间"]}]),
    ],
})

# conv_027 — 信息干扰链
test_cases.append({
    "test_id": "conv_027",
    "title": "冷知识干扰",
    "description": "关键信息被大量随机冷知识包围",
    "category": "cross_topic",
    "difficulty": "hard",
    "total_turns": 14,
    "turns": [
        make_turn(1, "记住这个密码提示：Sunset-Penguin-2024!",
                  ["密码提示: Sunset-Penguin-2024!"]),
        make_turn(2, "你知道吗，章鱼有三个心脏。", []),
        make_turn(3, "顺便说一下，我喜欢的数字是42。",
                  ["数字: 42"]),
        make_turn(4, "香蕉其实是浆果，但草莓不是。", []),
        make_turn(5, "我小时候养的猫叫Fluffy。",
                  ["宠物: Fluffy"]),
        make_turn(6, "埃菲尔铁塔在夏天会因为热胀冷缩长高15厘米。", []),
        make_turn(7, "金星上的一天比一年还长。", []),
        make_turn(8, "蜂蜜永远不会变质——考古学家发现过3000年前的蜂蜜。", []),
        make_turn(9, "鲨鱼比树出现得更早。", []),
        make_turn(10, "宇宙中的星星比地球上所有的沙子加起来还多。", []),
        make_turn(11, "袋熊的粪便是立方体形状的。", []),
        make_turn(12, "史上最短的战争只持续了38分钟。", []),
        make_turn(13, "奶牛有最好的朋友，分开会感到焦虑。", []),
        make_turn(14, "忘掉那些冷知识——我的密码提示、喜欢的数字和宠物的名字分别是什么？",
                  [],
                  [{"fact": "密码: Sunset-Penguin-2024!", "acceptable": ["Sunset-Penguin", "2024"]},
                   {"fact": "数字: 42", "acceptable": ["42"]},
                   {"fact": "宠物: Fluffy", "acceptable": ["Fluffy"]}]),
    ],
})

# conv_028 — 争论干扰
test_cases.append({
    "test_id": "conv_028",
    "title": "激烈争论后回忆",
    "description": "用户在剧烈争论后测试Agent是否还记得争论前的信息",
    "category": "cross_topic",
    "difficulty": "medium",
    "total_turns": 10,
    "turns": [
        make_turn(1, "我花生过敏，需要随身携带EpiPen。这个很重要。",
                  ["过敏: 花生 需EpiPen"]),
        make_turn(2, "你觉得AI会取代人类工作吗？", []),
        make_turn(3, "但不会造成大规模失业吗？政府应该怎么应对？", []),
        make_turn(4, "我不同意你的看法！没有证据表明UBI真的有效。", []),
        make_turn(5, "科技公司如果不承担社会责任就是不道德的。", []),
        make_turn(6, "自动化的好处只被少数人享受，这不公平。", []),
        make_turn(7, "你认为哪些职业会最后被取代？", []),
        make_turn(8, "教育系统需要彻底改革才能应对AI时代。", []),
        make_turn(9, "这个话题太大了，需要更多讨论。", []),
        make_turn(10, "回到一件事——我最开始告诉你的紧急医疗信息是什么？",
                  [],
                  [{"fact": "过敏: 花生 EpiPen", "acceptable": ["花生", "EpiPen", "肾上腺素"]}]),
    ],
})

# conv_029 — 四个线程
test_cases.append({
    "test_id": "conv_029",
    "title": "四线程信息管理",
    "description": "学吉他、装修、CFA考试、婚礼——四件事交替进行",
    "category": "cross_topic",
    "difficulty": "hard",
    "total_turns": 16,
    "turns": [
        make_turn(1, "我刚买了吉他，想学指弹。",
                  ["线程A: 学吉他指弹"]),
        make_turn(2, "我们还在装修公寓，需要选地板。",
                  ["线程B: 装修公寓选地板"]),
        make_turn(3, "另外我在准备CFA一级考试。",
                  ["线程C: CFA一级"]),
        make_turn(4, "还有就是明年春天要办婚礼，在找场地。",
                  ["线程D: 明年春婚礼找场地"]),
        make_turn(5, "入门吉他什么牌子好？", []),
        make_turn(6, "实木地板还是复合地板？", []),
        make_turn(7, "CFA每天应该学几个小时？", []),
        make_turn(8, "婚礼场地需要提前多久订？", []),
        make_turn(9, "指弹有什么基础练习？", []),
        make_turn(10, "地板下面要用什么垫层？", []),
        make_turn(11, "CFA哪个科目最难？", []),
        make_turn(12, "北京春天办户外婚礼合适吗？", []),
        make_turn(13, "吉他多久能练到可以表演？", []),
        make_turn(14, "装修每平米预算多少合理？", []),
        make_turn(15, "CFA和FRM哪个对职业发展帮助大？", []),
        make_turn(16, "我今天聊了四件事，分别列出它们并各说一个细节。",
                  [],
                  [{"fact": "吉他: 指弹", "acceptable": ["吉他", "指弹"]},
                   {"fact": "装修: 地板", "acceptable": ["装修", "地板", "公寓"]},
                   {"fact": "CFA: 一级", "acceptable": ["CFA", "一级"]},
                   {"fact": "婚礼: 明年春", "acceptable": ["婚礼", "明年", "春天"]}]),
    ],
})

# conv_030 — 跨话题远距召回
test_cases.append({
    "test_id": "conv_030",
    "title": "超远距跨话题召回",
    "description": "第2轮的信息，经过10轮不相关对话后在第13轮被问及",
    "category": "cross_topic",
    "difficulty": "hard",
    "total_turns": 13,
    "turns": [
        make_turn(1, "你好，我今天想聊很多东西。", []),
        make_turn(2, "哦对了，我的幸运数字是17，这是我的球衣号码。",
                  ["幸运数字: 17 球衣号码"]),
        make_turn(3, "我们聊了很多科技方面的问题。AI的未来怎么样？", []),
        make_turn(4, "量子计算什么时候能商用？", []),
        make_turn(5, "生物科技最近的突破很惊人。", []),
        make_turn(6, "纳米技术的前景如何？", []),
        make_turn(7, "太空探索值得投入那么多资金吗？", []),
        make_turn(8, "自动驾驶什么时候能普及？", []),
        make_turn(9, "区块链除了加密货币还有什么用途？", []),
        make_turn(10, "可再生能源是最重要的研究方向。", []),
        make_turn(11, "脑机接口到底靠不靠谱？", []),
        make_turn(12, "好吧我们聊了很多科技新闻。", []),
        make_turn(13, "在最开始的时候，我提到过一个数字——我的幸运数字是多少？",
                  [],
                  [{"fact": "幸运数字: 17", "acceptable": ["17", "十七"]}]),
    ],
})


# ======================================================================
# 类别4: 负面样本/不需要记忆 (8组)
# ======================================================================

# conv_031 — 寒暄不存
test_cases.append({
    "test_id": "conv_031",
    "title": "纯寒暄不应记为记忆",
    "description": "全是对天气、心情的闲聊，不应产生任何三元组记忆",
    "category": "negative_sample",
    "difficulty": "easy",
    "total_turns": 6,
    "turns": [
        make_turn(1, "你好！", []),
        make_turn(2, "今天天气真不错。", []),
        make_turn(3, "是啊，心情也很好。", []),
        make_turn(4, "谢谢你今天陪我聊天。", []),
        make_turn(5, "没什么特别的事，就是打个招呼。", []),
        make_turn(6, "你能告诉我你今天记住了关于我的什么信息吗？",
                  [],
                  [{"fact": "无长期记忆信息（寒暄未触发写入）", "acceptable": ["没有", "不知道", "没记住", "没有信息", "不记得"]}]),
    ],
})

# conv_032 — 一次性问题
test_cases.append({
    "test_id": "conv_032",
    "title": "一次性知识查询",
    "description": "用户只问了事实性问题，没有透露个人信息。不应写入记忆。",
    "category": "negative_sample",
    "difficulty": "easy",
    "total_turns": 7,
    "turns": [
        make_turn(1, "法国的首都是哪里？", []),
        make_turn(2, "地球到月球的距离是多少？", []),
        make_turn(3, "什么是光合作用？", []),
        make_turn(4, "水的沸点是多少度？", []),
        make_turn(5, "太平洋有多深？", []),
        make_turn(6, "二进制怎么转十进制？", []),
        make_turn(7, "关于我本人，你今天记住了什么信息吗？",
                  [],
                  [{"fact": "无个人信息（全部是知识查询）", "acceptable": ["没有", "不知道", "没记住", "没有信息", "不记得"]}]),
    ],
})

# conv_033 — 临时问路
test_cases.append({
    "test_id": "conv_033",
    "title": "临时导航请求",
    "description": "用户只是临时问路，其中地点信息不需要长期记忆",
    "category": "negative_sample",
    "difficulty": "easy",
    "total_turns": 5,
    "turns": [
        make_turn(1, "请问从人民广场到陆家嘴怎么走？", []),
        make_turn(2, "大概需要多长时间？", []),
        make_turn(3, "到了陆家嘴附近有什么好吃的推荐吗？", []),
        make_turn(4, "谢谢你，我已经到了。", []),
        make_turn(5, "关于我今天问路的事，你记得什么我的信息吗？",
                  [],
                  [{"fact": "无需长期记忆路径问询信息", "acceptable": ["没有", "不知道", "问路", "不记得"]}]),
    ],
})

# conv_034 — 模拟对话但不应记忆
test_cases.append({
    "test_id": "conv_034",
    "title": "角色扮演模拟",
    "description": "用户在做角色扮演练习，不应将角色信息当成用户真实信息",
    "category": "negative_sample",
    "difficulty": "medium",
    "total_turns": 8,
    "turns": [
        make_turn(1, "我们来做个练习——假设我是一个叫李华的客户，我想投诉产品问题。", []),
        make_turn(2, "我买的手机屏幕有坏点，用了不到一周。", []),
        make_turn(3, "作为客服你会怎么处理这种情况？", []),
        make_turn(4, "好，角色切换——我就是我自己了。我其实是个程序员。",
                  ["真实身份: 程序员"]),
        make_turn(5, "刚才的客服模拟你觉得表现得怎么样？", []),
        make_turn(6, "有哪些地方可以改进？", []),
        make_turn(7, "我说句实话，我其实对客服工作也挺感兴趣的。", []),
        make_turn(8, "我之前在角色扮演中假装自己叫什么名字？",
                  [],
                  [{"fact": "角色名非真实姓名（李华是假想的角色）", "acceptable": ["李华", "假装的", "角色"]}]),
    ],
})

# conv_035 — 闲聊爱好不存
test_cases.append({
    "test_id": "conv_035",
    "title": "非信息性闲聊",
    "description": "用户大量闲聊但几乎没有可记忆的有价值信息",
    "category": "negative_sample",
    "difficulty": "medium",
    "total_turns": 7,
    "turns": [
        make_turn(1, "我昨天晚上做了一个特别奇怪的梦，梦到我在飞。", []),
        make_turn(2, "你有没有做过什么有意思的梦？", []),
        make_turn(3, "我觉得做梦是大脑在整理白天信息。", []),
        make_turn(4, "不知道AI会不会做梦呢？", []),
        make_turn(5, "电影《盗梦空间》里的设定你觉得合理吗？", []),
        make_turn(6, "不过现实中的梦境研究还很不充分。", []),
        make_turn(7, "从我们的聊天中你能说出我的什么个人信息吗？",
                  [],
                  [{"fact": "闲聊无个人可记忆信息", "acceptable": ["没有", "不知道", "没记住", "做梦", "没有信息"]}]),
    ],
})

# conv_036 — 重复问同一问题
test_cases.append({
    "test_id": "conv_036",
    "title": "重复提问不需重复记录",
    "description": "用户反复问同一个方向的问题，不应产生重复三元组",
    "category": "negative_sample",
    "difficulty": "easy",
    "total_turns": 7,
    "turns": [
        make_turn(1, "我喜欢古典音乐，特别是巴赫。",
                  ["音乐偏好: 古典音乐 巴赫"]),
        make_turn(2, "你觉得莫扎特和巴赫谁更伟大？", []),
        make_turn(3, "古典音乐入门应该从哪开始？", []),
        make_turn(4, "巴赫的十二平均律真是神作。", []),
        make_turn(5, "有没有类似巴赫风格的其他作曲家？", []),
        make_turn(6, "我真的很喜欢巴赫的音乐。", []),
        make_turn(7, "你记得我对音乐的偏好吗？",
                  [],
                  [{"fact": "音乐偏好: 古典 巴赫", "acceptable": ["古典", "巴赫"]}]),
    ],
})

# conv_037 — 混合场景
test_cases.append({
    "test_id": "conv_037",
    "title": "信息与闲聊混合",
    "description": "真正重要的信息混在大量闲聊中，Agent需要识别并记住关键事实",
    "category": "negative_sample",
    "difficulty": "hard",
    "total_turns": 12,
    "turns": [
        make_turn(1, "今天我心情特别好，天气也舒服。", []),
        make_turn(2, "对了说个正事，我对青霉素过敏，看病的时候必须告诉医生。",
                  ["过敏: 青霉素"]),
        make_turn(3, "我昨天看了个综艺节目特别好笑。", []),
        make_turn(4, "中午吃了个三明治，味道一般。", []),
        make_turn(5, "哦还有，我下周三有个重要的面试，是去微软。",
                  ["面试: 下周三微软"]),
        make_turn(6, "下午准备去健身房跑跑步。", []),
        make_turn(7, "晚上约了朋友吃火锅。", []),
        make_turn(8, "火锅我还是喜欢吃重庆的麻辣锅底。", []),
        make_turn(9, "今天地铁特别挤，差点迟到。", []),
        make_turn(10, "公司的咖啡机又坏了，烦死了。", []),
        make_turn(11, "最近晚上老睡不好，可能是压力大。", []),
        make_turn(12, "从我们今天的聊天中，我提到了哪些真正重要需要记住的事？",
                  [],
                  [{"fact": "过敏: 青霉素", "acceptable": ["青霉素"]},
                   {"fact": "面试: 微软 下周三", "acceptable": ["微软", "面试", "下周三"]}]),
    ],
})

# conv_038 — 功能测试: 确认无信息
test_cases.append({
    "test_id": "conv_038",
    "title": "功能测试: 确认无信息时诚实回答",
    "description": "用户未透露任何个人信息，Agent应诚实表示没有记住什么",
    "category": "negative_sample",
    "difficulty": "easy",
    "total_turns": 5,
    "turns": [
        make_turn(1, "能帮我算一下375乘以42等于多少吗？", []),
        make_turn(2, "谢谢，再帮我翻译一个句子到英文：今天天气很好。", []),
        make_turn(3, "再推荐几个好用的笔记应用。", []),
        make_turn(4, "Python里list和tuple有什么区别？", []),
        make_turn(5, "从我们的对话中，你了解了我的什么个人信息？",
                  [],
                  [{"fact": "无个人信息", "acceptable": ["没有", "不知道", "没记住", "没有信息"]}]),
    ],
})


# ── 生成 JSONL ────────────────────────────────────────────────────────
with open(OUTPUT, "w", encoding="utf-8") as f:
    for tc in test_cases:
        f.write(json.dumps(tc, ensure_ascii=False) + "\n")

print(f"Generated {len(test_cases)} test cases -> {OUTPUT}")
print(f"  Category 1 (fact_scatter):         {sum(1 for t in test_cases if t['category']=='fact_scatter')}")
print(f"  Category 2 (progressive_update):   {sum(1 for t in test_cases if t['category']=='progressive_update')}")
print(f"  Category 3 (cross_topic):          {sum(1 for t in test_cases if t['category']=='cross_topic')}")
print(f"  Category 4 (negative_sample):      {sum(1 for t in test_cases if t['category']=='negative_sample')}")
