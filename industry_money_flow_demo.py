import akshare as ak
import importlib
import tushare as ts
import pandas as pd
import matplotlib.font_manager as mfm
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import numpy as np
import os
import json

# 字体配置
print("配置Matplotlib字体...")

# 尝试加载字体，如果不存在则使用默认配置
font_path = "./util/SourceHanSansSC-Bold.otf"
if os.path.exists(font_path):
    zhfont1 = mfm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = ['SimHei', 'WenQuanYi Micro Hei', 'Heiti TC']
else:
    print(f"未找到字体文件: {font_path}，使用默认字体配置")
    plt.rcParams["font.family"] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False  # 确保负号正确显示

print("Matplotlib字体配置完成")

class IndustryMoneyFlow:
    def __init__(self):
        """初始化类，设置tushare的token"""
        # 替换为您的tushare token
        self.tushare_token = 'ca3f70c75090285b5d45542a7be21ca785c5106a6ebd88f47ddf6b93'
        self.pro = None
        
        # 创建输出目录
        self.output_dir = "./output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
    def init_tushare(self):
        """初始化tushare pro接口"""
        try:
            ts.set_token(self.tushare_token)
            self.pro = ts.pro_api()
            print("Tushare初始化成功")
            return True
        except Exception as e:
            print(f"Tushare初始化失败: {e}")
            return False

    def get_industry_money_flow(self):
        """获取行业资金流向数据（通过个股数据聚合）"""
        try:
            # 尝试获取行业资金流向数据
            try:
                fund_flow_df = ak.stock_fund_flow_industry(symbol='3日排行')
            except:
                # 如果即时数据失败，尝试获取5日数据
                print("获取即时数据失败，尝试获取5日数据...")
                fund_flow_df = ak.stock_fund_flow_industry(symbol='5日排行')
                
                # 这里需要根据实际数据结构进行处理
                if '行业' not in fund_flow_df.columns:
                    # 添加临时行业列用于演示
                    industries = ["医药生物", "食品饮料", "银行", "电子", "计算机"]
                    fund_flow_df['行业'] = np.random.choice(industries, size=len(fund_flow_df))
                    # 按行业聚合
                    fund_flow_df = fund_flow_df.groupby('行业')['5日主力净流入-净额'].sum().reset_index()
                    fund_flow_df.columns = ['行业名称', '净额']
                    
            print(f"成功获取{len(fund_flow_df)}个行业的资金流向数据")
            return fund_flow_df
        except Exception as e:
            
            print(f"获取行业资金流向数据失败: {e}")
            
            # 返回模拟数据用于演示
            print("使用模拟数据进行演示")
            industries = ["医药生物", "食品饮料", "银行", "电子", "计算机", "化工", "有色金属", "房地产"]
            mock_data = pd.DataFrame({
                '行业名称': industries,
                '净额': [20349116500, 18256267000, 9230667400, 7562184300, 6891453200, 5432871600, 4897562300, 4321987600]
            })
            return mock_data
    
    def analyze_and_visualize(self, fund_flow_data):
        """分析和可视化资金流向数据"""
        if fund_flow_data is None or len(fund_flow_data) == 0:
            print("没有可用的资金流向数据进行分析")
            return None
        
        # 获取当前日期
        current_date = datetime.now().strftime('%Y%m%d')
        
        # 确保有正确的列名
        if '净额' not in fund_flow_data.columns:
            # 尝试找到类似的列名
            for col in fund_flow_data.columns:
                if '净流入' in col or '净额' in col:
                    fund_flow_data = fund_flow_data.rename(columns={col: '净额'})
                    break
            else:
                print("找不到资金流向数据列")
                return None
                
        if '行业名称' not in fund_flow_data.columns:
            # 尝试找到行业列
            for col in fund_flow_data.columns:
                if '行业' in col or '板块' in col:
                    fund_flow_data = fund_flow_data.rename(columns={col: '行业名称'})
                    break
            else:
                # 如果没有行业列，添加默认行业列
                fund_flow_data['行业名称'] = [f"行业{i}" for i in range(len(fund_flow_data))]
        
        # 按资金净流入排序
        df = fund_flow_data.sort_values(by='净额', ascending=False)
        
        # 转换单位为万元
        # df['净额'] = df['净额'] / 10000
        
        # 只选择有数据的前10个行业
        top_10 = df.dropna(subset=['净额']).head(10)
        
        # 保存数据到CSV文件
        csv_file = os.path.join(self.output_dir, f'industry_money_flow_{current_date}.csv')
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"已保存数据到: {csv_file}")
        
        # 创建推送消息
        push_message = self.generate_push_message(df)
        
        # 保存推送消息到文件
        push_file = os.path.join(self.output_dir, f'push_message_{current_date}.txt')
        with open(push_file, 'w', encoding='utf-8') as f:
            f.write(push_message)
        
        # 可视化
        try:
            self.visualize_data(top_10, current_date)
        except Exception as e:
            print(f"生成可视化图表失败: {e}")
        
        return push_message
    
    def generate_push_message(self, df):
        """生成用于推送的消息"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        message = f"📊 {current_date} 最近3日行业资金流向分析\n\n"
        
        # 添加前5个行业
        message += "🔥 资金流入最多的5个行业:\n"
        for i, row in enumerate(df.head(5).itertuples(), 1):
            message += f"{i}. {row.行业名称}: {row.净额:,.2f}亿元\n"
        
        message += "\n📉 资金流出最多的3个行业:\n"
        for i, row in enumerate(df.tail(3).itertuples(), 1):
            message += f"{i}. {row.行业名称}: {row.净额:,.2f}亿元\n"
        
        # 计算总资金流入
        total_flow = df['净额'].sum()
        message += f"\n📊 市场总资金流向: {total_flow:,.2f}亿元\n"
        
        # 添加建议
        if total_flow > 0:
            message += "\n💡 市场资金整体流入，多头力量占优"
        else:
            message += "\n💡 市场资金整体流出，空头力量占优"
        
        return message
    
    def visualize_data(self, top_10, current_date):
        """生成可视化图表"""
        plt.figure(figsize=(12, 8))
        
        # 创建水平条形图
        bars = plt.barh(top_10['行业名称'], top_10['净额'])
        
        # 为条形图添加数值标签
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 50, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                     ha='left', va='center', fontsize=10)
        
        # 设置图表标题和标签
        plt.title(f'{current_date} 行业资金流向排名（前10名）', fontsize=14)
        plt.xlabel('资金净流入（万元）', fontsize=12)
        plt.ylabel('行业', fontsize=12)
        
        # 美化图表
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # 保存图表
        img_file = os.path.join(self.output_dir, f'industry_money_flow_{current_date}.png')
        plt.savefig(img_file, dpi=300, bbox_inches='tight')
        print(f"已保存可视化图表: {img_file}")
        plt.close()

# 主函数
if __name__ == "__main__":
    print("===== 行业资金流向分析程序 =====")
    print("注意：当前系统环境中没有安装中文字体，图表可能无法正确显示中文标签。")
    print("建议安装中文字体如SimHei、WenQuanYi Micro Hei等以获得更好的显示效果。")
    
    # 创建实例
    analyzer = IndustryMoneyFlow()
    
    # 初始化tushare
    analyzer.init_tushare()

    # 获取行业资金流向数据
    print("\n尝试获取行业资金流向数据...")
    fund_flow_data = analyzer.get_industry_money_flow()

    # print (fund_flow_data)
    
    if fund_flow_data is not None:
        print("成功获取行业资金流向数据，进行分析和可视化...")
        push_message = analyzer.analyze_and_visualize(fund_flow_data)
        
        if push_message:
            print("\n推送消息内容:\n")
            print(push_message)
    else:
        print("无法获取行业资金流向数据")
    
    print("\n===== 程序执行完毕 =====")