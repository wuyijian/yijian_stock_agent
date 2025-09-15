import os
import sys
import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time
import random
import logging
from notification_utils import NotificationSender

# 设置中文显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "SourceHanSansSC-Bold"]
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class StockAnalyzer:
    """股票数据分析工具类，集成多种分析功能"""
    
    def __init__(self):
        """初始化股票分析器"""
        # 创建输出目录
        self.output_dir = "./output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 创建日志目录
        self.log_dir = "./logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # 设置日志
        self.logger = self._setup_logger()
        
        # 通知发送器
        self.notification_sender = NotificationSender("notification_config.json")
    
    def _setup_logger(self):
        """设置日志配置"""
        log_file = os.path.join(self.log_dir, f"stock_analysis_{datetime.now().strftime('%Y%m%d')}.log")
        
        logger = logging.getLogger("stock_analyzer")
        logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if not logger.handlers:
            # 文件处理器
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def get_industry_list(self):
        """获取一级行业列表"""
        try:
            # 使用akshare获取申万一级行业列表
            industry_df = ak.stock_board_industry_name_ths()
            
            # 检查返回的数据是否有效并包含行业名称信息
            if industry_df is not None and not industry_df.empty:
                # 根据akshare可能返回的不同列名进行处理
                if 'industry_name' in industry_df.columns:
                    return industry_df
                elif '行业名称' in industry_df.columns:
                    return industry_df.rename(columns={'行业名称': 'industry_name'})
                elif '板块名称' in industry_df.columns:
                    return industry_df.rename(columns={'板块名称': 'industry_name'})
                elif len(industry_df.columns) > 0:
                    first_col = industry_df.columns[0]
                    self.logger.info(f"使用第一列 '{first_col}' 作为行业名称列")
                    return industry_df.rename(columns={first_col: 'industry_name'})
            
            self.logger.warning("返回的数据不符合预期，使用备用行业列表")
        except Exception as e:
            self.logger.error(f"获取行业列表失败: {e}")
        
        # 手动创建申万一级行业列表作为备用
        industry_list = [
            "银行", "非银金融", "食品饮料", "医药生物", "电子", "计算机", 
            "传媒", "通信", "农林牧渔", "化工", "钢铁", "有色金属",
            "采掘", "公用事业", "交通运输", "房地产", "建筑材料",
            "建筑装饰", "电气设备", "机械设备", "国防军工", "汽车",
            "家用电器", "纺织服装", "轻工制造", "商业贸易", "休闲服务"
        ]
        return pd.DataFrame({"industry_name": industry_list})
    
    def analyze_industry_money_flow(self):
        """行业资金流向分析"""
        self.logger.info("开始行业资金流向分析")
        
        try:
            # 尝试获取行业资金流向数据
            try:
                fund_flow_df = ak.stock_fund_flow_industry(symbol='即时')
            except Exception as e:
                # 如果即时数据失败，尝试获取5日数据
                self.logger.warning(f"获取即时数据失败: {e}，尝试获取5日数据...")
                try:
                    fund_flow_df = ak.stock_fund_flow_industry(symbol='5日排行')
                except Exception as e:
                    self.logger.error(f"获取5日数据也失败: {e}")
                    # 返回模拟数据用于演示
                    self.logger.info("使用模拟数据进行演示")
                    industries = ["医药生物", "食品饮料", "银行", "电子", "计算机", "化工", "有色金属", "房地产"]
                    fund_flow_df = pd.DataFrame({
                        '行业名称': industries,
                        '净额': [20349116500, 18256267000, 9230667400, 7562184300, 6891453200, 5432871600, 4897562300, 4321987600]
                    })
            
            self.logger.info(f"成功获取{len(fund_flow_df)}个行业的资金流向数据")
            return self._process_industry_flow_data(fund_flow_df)
        except Exception as e:
            self.logger.error(f"行业资金流向分析过程中出错: {e}")
            return None
    
    def _process_industry_flow_data(self, fund_flow_data):
        """处理行业资金流向数据并生成分析结果"""
        if fund_flow_data is None or len(fund_flow_data) == 0:
            self.logger.error("没有可用的资金流向数据进行分析")
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
                self.logger.error("找不到资金流向数据列")
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
        
      
        
        # 只选择有数据的前10个行业
        top_10 = df.dropna(subset=['净额']).head(10)
        
        # 保存数据到CSV文件
        csv_file = os.path.join(self.output_dir, f'industry_money_flow_{current_date}.csv')
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        self.logger.info(f"已保存数据到: {csv_file}")
        
        # 创建推送消息
        push_message = self._generate_industry_flow_message(df)
        
        # 保存推送消息到文件
        push_file = os.path.join(self.output_dir, f'push_message_{current_date}.txt')
        with open(push_file, 'w', encoding='utf-8') as f:
            f.write(push_message)
        
        # 可视化
        try:
            self._visualize_industry_flow(top_10, current_date)
        except Exception as e:
            self.logger.error(f"生成可视化图表失败: {e}")
        
        return push_message
    
    def _generate_industry_flow_message(self, df):
        """生成行业资金流向的推送消息"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        message = f"📊 {current_date} 行业资金流向分析\n\n"
        
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
    
    def _visualize_industry_flow(self, top_10, current_date):
        """可视化行业资金流向数据"""
        # plt.figure(figsize=(12, 8))
        
        # # 创建水平条形图
        # bars = plt.barh(top_10['行业名称'], top_10['净额'])
        
        # # 为条形图添加数值标签
        # for bar in bars:
        #     width = bar.get_width()
        #     plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{width:,.1f}', 
        #              ha='left', va='center', fontsize=10)
        
        # # 设置图表标题和标签
        # plt.title(f'{current_date} 行业资金流向排名（前10名）', fontsize=14)
        # plt.xlabel('资金净流入（亿元）', fontsize=12)
        # plt.ylabel('行业', fontsize=12)
        
        # # 美化图表
        # plt.grid(axis='x', linestyle='--', alpha=0.7)
        # plt.tight_layout()
        
        # 保存图表
        # img_file = os.path.join(self.output_dir, f'industry_money_flow_{current_date}.png')
        # plt.savefig(img_file, dpi=300, bbox_inches='tight')
        # self.logger.info(f"已保存可视化图表: {img_file}")
        # plt.close()
    
    def analyze_abnormal_volume(self):
        """个股异常成交量分析"""
        self.logger.info("开始个股异常成交量分析")
        
        try:
            # 获取A股股票列表
            stock_list = ak.stock_zh_a_spot()
            self.logger.info(f"获取到{len(stock_list)}只A股股票数据")
            
            # 筛选出成交量异常的股票（这里简单以成交量排名前20作为异常）
            abnormal_stocks = stock_list.sort_values(by='成交量', ascending=False).head(20)
            
            # 获取当前日期
            current_date = datetime.now().strftime('%Y%m%d')
            
            # 保存数据到CSV文件
            csv_file = os.path.join(self.output_dir, f'abnormal_volume_stocks_{current_date}.csv')
            abnormal_stocks.to_csv(csv_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"已保存异常成交量股票数据到: {csv_file}")
            
            # 创建推送消息
            push_message = self._generate_abnormal_volume_message(abnormal_stocks)
            
            # 可视化
            try:
                self._visualize_abnormal_volume(abnormal_stocks, current_date)
            except Exception as e:
                self.logger.error(f"生成异常成交量可视化图表失败: {e}")
            
            return push_message
        except Exception as e:
            self.logger.error(f"个股异常成交量分析过程中出错: {e}")
            return None
    
    def _generate_abnormal_volume_message(self, abnormal_stocks):
        """生成个股异常成交量的推送消息"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        message = f"📊 {current_date} 个股异常成交量分析\n\n"
        
        # 添加成交量最大的10只股票
        message += "🔥 成交量最大的10只股票:\n"
        
        # 确保数据有需要的列
        if '名称' in abnormal_stocks.columns and '成交量' in abnormal_stocks.columns:
            for i, row in enumerate(abnormal_stocks.head(10).itertuples(), 1):
                # 检查是否可以获取涨跌幅信息
                pct_chg = getattr(row, '涨跌幅', 'N/A')
                volume = row.成交量
                message += f"{i}. {row.名称}: {volume / 1000000:,.2f}万手"
                if pct_chg != 'N/A':
                    message += f" (涨跌幅: {pct_chg:.2f}%)"
                message += "\n"
        else:
            self.logger.warning("数据列不完整，无法生成详细的异常成交量消息")
            message += "数据列不完整，无法显示详细信息\n"
        
        message += "\n💡 成交量异常放大通常意味着市场对该股票关注度提升，可能存在重要的基本面或技术面变化"
        
        return message
    
    def _visualize_abnormal_volume(self, abnormal_stocks, current_date):
        """可视化个股异常成交量数据"""
        plt.figure(figsize=(12, 8))
        
        # 确保数据有需要的列
        if '名称' in abnormal_stocks.columns and '成交量' in abnormal_stocks.columns:
            # 只取前15只股票进行可视化
            top_stocks = abnormal_stocks.head(15)
            
            # 创建水平条形图
            bars = plt.barh(top_stocks['名称'], top_stocks['成交量'])
            
            # 为条形图添加数值标签
            for bar in bars:
                width = bar.get_width()
                plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                         ha='left', va='center', fontsize=10)
            
            # 设置图表标题和标签
            plt.title(f'{current_date} 个股成交量排名（前15名）', fontsize=14)
            plt.xlabel('成交量（万手）', fontsize=12)
            plt.ylabel('股票名称', fontsize=12)
            
            # 美化图表
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            # 保存图表
            img_file = os.path.join(self.output_dir, f'abnormal_volume_{current_date}.png')
            plt.savefig(img_file, dpi=300, bbox_inches='tight')
            self.logger.info(f"已保存异常成交量可视化图表: {img_file}")
            plt.close()
        else:
            self.logger.error("数据列不完整，无法生成异常成交量可视化图表")
    
    def analyze_us_stock_industry_flow(self):
        """美股行业资金分析"""
        self.logger.info("开始美股行业资金分析")
        
        try:
            # 获取美股行业数据（这里使用可用的AKShare接口）
            # 注意：AKShare可能没有直接的美股行业资金流向接口，这里使用变通方法
            
            # 获取道琼斯行业分类指数
            dow_sectors = ak.stock_us_dji_spot()
            self.logger.info(f"获取到{len(dow_sectors)}个道琼斯行业指数数据")
            
            # 获取当前日期
            current_date = datetime.now().strftime('%Y%m%d')
            
            # 保存数据到CSV文件
            csv_file = os.path.join(self.output_dir, f'us_stock_sectors_{current_date}.csv')
            dow_sectors.to_csv(csv_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"已保存美股行业数据到: {csv_file}")
            
            # 创建推送消息
            push_message = self._generate_us_stock_message(dow_sectors)
            
            # 可视化
            try:
                self._visualize_us_stock_sectors(dow_sectors, current_date)
            except Exception as e:
                self.logger.error(f"生成美股行业可视化图表失败: {e}")
            
            return push_message
        except Exception as e:
            self.logger.error(f"美股行业资金分析过程中出错: {e}")
            # 如果无法获取实际数据，返回模拟数据
            return self._generate_mock_us_stock_message()
    
    def _generate_us_stock_message(self, dow_sectors):
        """生成美股行业分析的推送消息"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        message = f"📊 {current_date} 美股行业表现分析\n\n"
        
        # 尝试获取涨跌幅数据
        if '涨跌幅' in dow_sectors.columns:
            # 按涨跌幅排序
            sorted_sectors = dow_sectors.sort_values(by='涨跌幅', ascending=False)
            
            # 添加涨幅最大的5个行业
            message += "🔥 涨幅最大的5个行业:\n"
            for i, row in enumerate(sorted_sectors.head(5).itertuples(), 1):
                if hasattr(row, '名称'):
                    message += f"{i}. {row.名称}: {row.涨跌幅:.2f}%\n"
                elif hasattr(row, '指数名称'):
                    message += f"{i}. {row.指数名称}: {row.涨跌幅:.2f}%\n"
            
            # 添加跌幅最大的3个行业
            message += "\n📉 跌幅最大的3个行业:\n"
            for i, row in enumerate(sorted_sectors.tail(3).itertuples(), 1):
                if hasattr(row, '名称'):
                    message += f"{i}. {row.名称}: {row.涨跌幅:.2f}%\n"
                elif hasattr(row, '指数名称'):
                    message += f"{i}. {row.指数名称}: {row.涨跌幅:.2f}%\n"
        else:
            message += "无法获取涨跌幅数据，显示行业列表:\n"
            if '名称' in dow_sectors.columns:
                for i, row in enumerate(dow_sectors.head(10).itertuples(), 1):
                    message += f"{i}. {row.名称}\n"
            elif '指数名称' in dow_sectors.columns:
                for i, row in enumerate(dow_sectors.head(10).itertuples(), 1):
                    message += f"{i}. {row.指数名称}\n"
        
        message += "\n💡 美股行业表现可以作为全球市场风险偏好的重要参考指标"
        
        return message
    
    def _generate_mock_us_stock_message(self):
        """生成模拟的美股行业分析消息"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        message = f"📊 {current_date} 美股行业表现分析 (模拟数据)\n\n"
        
        # 模拟美股行业数据
        sectors = [
            {"name": "科技", "change": 2.34},
            {"name": "医疗保健", "change": 1.87},
            {"name": "消费者非必需品", "change": 1.56},
            {"name": "工业", "change": 1.23},
            {"name": "金融", "change": 0.98},
            {"name": "能源", "change": -0.56},
            {"name": "公用事业", "change": -1.23},
            {"name": "材料", "change": -1.89}
        ]
        
        message += "🔥 涨幅最大的5个行业:\n"
        for i, sector in enumerate(sorted(sectors, key=lambda x: x["change"], reverse=True)[:5], 1):
            message += f"{i}. {sector['name']}: {sector['change']:.2f}%\n"
        
        message += "\n📉 跌幅最大的3个行业:\n"
        for i, sector in enumerate(sorted(sectors, key=lambda x: x["change"])[:3], 1):
            message += f"{i}. {sector['name']}: {sector['change']:.2f}%\n"
        
        message += "\n💡 注意：当前为模拟数据，实际使用时需要配置正确的美股数据接口"
        
        return message
    
    def _visualize_us_stock_sectors(self, dow_sectors, current_date):
        """可视化美股行业数据"""
        plt.figure(figsize=(12, 8))
        
        # 尝试获取涨跌幅和行业名称数据
        if '涨跌幅' in dow_sectors.columns:
            # 按涨跌幅排序
            sorted_sectors = dow_sectors.sort_values(by='涨跌幅', ascending=False)
            
            # 获取行业名称
            if '名称' in sorted_sectors.columns:
                names = sorted_sectors['名称']
            elif '指数名称' in sorted_sectors.columns:
                names = sorted_sectors['指数名称']
            else:
                names = [f"行业{i}" for i in range(len(sorted_sectors))]
            
            # 创建条形图
            colors = ['green' if x > 0 else 'red' for x in sorted_sectors['涨跌幅']]
            bars = plt.bar(names, sorted_sectors['涨跌幅'], color=colors)
            
            # 为条形图添加数值标签
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height, f'{height:.2f}%', 
                         ha='center', va='bottom' if height > 0 else 'top', fontsize=9)
            
            # 设置图表标题和标签
            plt.title(f'{current_date} 美股行业涨跌幅表现', fontsize=14)
            plt.xlabel('行业', fontsize=12)
            plt.ylabel('涨跌幅 (%)', fontsize=12)
            
            # 旋转x轴标签以避免重叠
            plt.xticks(rotation=45, ha='right')
            
            # 添加水平线表示0值
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            # 美化图表
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            # 保存图表
            img_file = os.path.join(self.output_dir, f'us_stock_sectors_{current_date}.png')
            plt.savefig(img_file, dpi=300, bbox_inches='tight')
            self.logger.info(f"已保存美股行业可视化图表: {img_file}")
            plt.close()
        else:
            self.logger.error("数据列不完整，无法生成美股行业可视化图表")
    
    def run_analysis(self, analysis_types=None):
        """运行指定类型的分析
        
        Args:
            analysis_types (list): 要运行的分析类型列表，可选值包括：
                'industry_flow': 行业资金流向分析
                'abnormal_volume': 个股异常成交量分析
                'us_stock': 美股行业分析
                如果为None，则运行所有分析
        """
        if analysis_types is None:
            analysis_types = ['industry_flow', 'abnormal_volume', 'us_stock']
        
        all_messages = []
        
        # 运行行业资金流向分析
        if 'industry_flow' in analysis_types:
            industry_message = self.analyze_industry_money_flow()
            if industry_message:
                all_messages.append(industry_message)
        
        # 运行个股异常成交量分析
        if 'abnormal_volume' in analysis_types:
            volume_message = self.analyze_abnormal_volume()
            if volume_message:
                all_messages.append(volume_message)
        
        # 运行美股行业分析
        if 'us_stock' in analysis_types:
            us_stock_message = self.analyze_us_stock_industry_flow()
            if us_stock_message:
                all_messages.append(us_stock_message)
        
        # 合并所有消息并发送通知
        if all_messages:
            # 如果有多个消息，合并它们
            if len(all_messages) > 1:
                combined_message = "\n\n".join(all_messages)
                title = f"📊 股票市场综合分析报告 ({datetime.now().strftime('%Y-%m-%d')})"
            else:
                combined_message = all_messages[0]
                title = f"📊 股票市场分析报告 ({datetime.now().strftime('%Y-%m-%d')})"
            
            # 发送通知
            self.notification_sender.send_notification(title, combined_message)
            return combined_message
        
        return None

# 主函数
if __name__ == "__main__":
    print("===== 股票市场综合分析程序 ======")
    
    # 创建分析器实例
    analyzer = StockAnalyzer()
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='股票市场综合分析工具')
    parser.add_argument('--all', action='store_true', help='运行所有分析')
    parser.add_argument('--industry', action='store_true', help='仅运行行业资金流向分析')
    parser.add_argument('--volume', action='store_true', help='仅运行个股异常成交量分析')
    parser.add_argument('--us', action='store_true', help='仅运行美股行业分析')
    
    args = parser.parse_args()
    
    # 确定要运行的分析类型
    analysis_types = []
    if args.all or (not args.industry and not args.volume and not args.us):
        # 默认运行所有分析
        analysis_types = None
    else:
        if args.industry:
            analysis_types.append('industry_flow')
        if args.volume:
            analysis_types.append('abnormal_volume')
        if args.us:
            analysis_types.append('us_stock')
    
    # 运行分析
    print(f"开始运行分析: {analysis_types or '所有分析'}")
    message = analyzer.run_analysis(analysis_types)
    
    if message:
        print("\n分析报告:\n")
        print(message)
    else:
        print("分析失败，未能生成报告")
    
    print("\n===== 程序执行完毕 =====")