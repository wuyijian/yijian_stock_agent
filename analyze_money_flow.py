import pandas as pd

# 读取CSV文件
df = pd.read_csv('industry_money_flow_data.csv')

# 按行业汇总资金流入
total_flow = df.groupby('industry_name')['net_amount_main'].sum().reset_index()

# 排序找出资金流入最多的三个行业
top_3 = total_flow.sort_values(by='net_amount_main', ascending=False).head(3)

# 打印结果
print("近10天资金流入最多的三个板块：")
for i, row in enumerate(top_3.itertuples(), 1):
    print(f"{i}. {row.industry_name}: {row.net_amount_main:,.2f}万元")

# 打印完整的排序结果
print("\n所有行业资金流入排序：")
for i, row in enumerate(total_flow.sort_values(by='net_amount_main', ascending=False).itertuples(), 1):
    print(f"{i}. {row.industry_name}: {row.net_amount_main:,.2f}万元")