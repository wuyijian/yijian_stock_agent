

import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import random

# 设置中文显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 获取一级行业列表
def get_industry_list():
    try:
        # 使用akshare获取申万一级行业列表
        industry_df = ak.stock_board_industry_name_ths()
        
        # 打印数据结构，帮助调试
        print("获取到的行业数据结构:")
        print(industry_df.head())
        print("数据列名:", industry_df.columns.tolist())
        
        # 检查返回的数据是否有效并包含行业名称信息
        if industry_df is not None and not industry_df.empty:
            # 根据akshare可能返回的不同列名进行处理
            if 'industry_name' in industry_df.columns:
                return industry_df
            elif '行业名称' in industry_df.columns:
                # 如果列名是中文的"行业名称"，重命名为英文
                return industry_df.rename(columns={'行业名称': 'industry_name'})
            elif '板块名称' in industry_df.columns:
                # 可能有些API返回的是"板块名称"
                return industry_df.rename(columns={'板块名称': 'industry_name'})
            elif len(industry_df.columns) > 0:
                # 如果有其他列名，使用第一列作为行业名称
                first_col = industry_df.columns[0]
                print(f"使用第一列 '{first_col}' 作为行业名称列")
                return industry_df.rename(columns={first_col: 'industry_name'})
        
        # 如果获取的数据不符合预期，使用备用列表
        print("返回的数据不符合预期，使用备用行业列表")
    except Exception as e:
        print(f"获取行业列表失败: {e}")
    
    # 手动创建申万一级行业列表作为备用
    industry_list = [
        "银行", "非银金融", "食品饮料", "医药生物", "电子", "计算机", 
        "传媒", "通信", "农林牧渔", "化工", "钢铁", "有色金属",
        "采掘", "公用事业", "交通运输", "房地产", "建筑材料",
        "建筑装饰", "电气设备", "机械设备", "国防军工", "汽车",
        "家用电器", "纺织服装", "轻工制造", "商业贸易", "休闲服务"
    ]
    return pd.DataFrame({"industry_name": industry_list})

if __name__ == "__main__":
    industry_df = get_industry_list()
    print(industry_df)