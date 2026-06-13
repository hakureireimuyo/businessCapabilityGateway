"""本地测试脚本 —— 直接 python sandbox/demo.py 即可运行。

不依赖服务，直接本地执行，用于探索插件能力和调试 Graph。
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gateway import Graph, init

# ═══════════════════════════════════════════════════════════════════════
# 1. 加载所有插件（只需要调一次）
# ═══════════════════════════════════════════════════════════════════════
loaded = init()
print(f"已加载插件: {loaded}\n")


# ═══════════════════════════════════════════════════════════════════════
# 2. 简单链式：关键词搜索 → 过滤 → 市场分析
# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("示例 1: 简单链式")
print("=" * 60)

g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland", limit=10)
filtered = g.filter(products=products, price_gte=5.0, price_lte=50.0)
analysis = g.market_analysis(products=filtered)
g.output(analysis)
result = g.execute()

print(f"市场分析结果: {result}\n")


# ═══════════════════════════════════════════════════════════════════════
# 3. 并行分支：sales + reviews → market_score
# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("示例 2: 并行分支")
print("=" * 60)

g = Graph(plugin="amazon")
products = g.keyword_search(keyword="bluetooth headphone", limit=10)
sales = g.sales_analysis(products=products)
reviews = g.review_analysis(products=products)
score = g.market_score(sales=sales, reviews=reviews)
g.output(score)
result = g.execute()

print(f"市场综合评分: {result}\n")


# ═══════════════════════════════════════════════════════════════════════
# 4. amazon_db 插件（真实数据库）
# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("示例 3: amazon_db 关键词市场分析")
print("=" * 60)

g = Graph(plugin="amazon_db")
products = g.keyword_search(keyword="wireless charger", limit=20)
analysis = g.market_analysis(products=products)
g.output(analysis)
result = g.execute()

print(f"amazon_db 市场分析: {result}\n")


print("=" * 60)
print("完成！修改上面的代码来探索更多节点组合。")
print("打开 sandbox/demo.py 编辑，直接 python sandbox/demo.py 运行。")
print("=" * 60)
