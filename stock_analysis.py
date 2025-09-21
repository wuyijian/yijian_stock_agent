import os
from statistics import median_grouped
import sys
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random
import logging
import tushare as ts
from notification_utils import NotificationSender

# 配置Tushare token
# 注意：在实际使用时，建议从配置文件或环境变量中读取token
# 这里使用默认值，可以在运行时通过环境变量TUSHARE_TOKEN覆盖
ts.set_token(os.environ.get('TUSHARE_TOKEN', 'ca3f70c75090285b5d45542a7be21ca785c5106a6ebd88f47ddf6b93'))
pro = ts.pro_api()

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
                        '资金净流入': [20349116500, 18256267000, 9230667400, 7562184300, 6891453200, 5432871600, 4897562300, 4321987600]
                    })
            
            self.logger.info(f"成功获取{len(fund_flow_df)}个行业的资金流向数据")
            return self._process_industry_flow_data(fund_flow_df)
        except Exception as e:
            self.logger.error(f"行业资金流向分析过程中出错: {e}")
            return None
    
    def _process_industry_flow_data(self, fund_flow_data):
        """处理行业资金流向数据，计算资金净流入排名"""
        self.logger.info(f"处理资金流向数据: {len(fund_flow_data)} 条")
        
        # 确保资金流向数据不为空
        if fund_flow_data.empty:
            self.logger.warning("资金流向数据为空，无法进行处理")
            return pd.DataFrame()
        
        try:
            # 使用传入的资金流向数据作为合并后的数据
            merged_data = fund_flow_data.copy()
            
            # 确保合并后的数据不为空
            if merged_data.empty:
                self.logger.warning("合并后的数据为空，无法进行处理")
                return pd.DataFrame()
            
            # 打印列名以便调试
            self.logger.info(f"原始数据列名: {list(merged_data.columns)}")
            
            # 动态查找行业名称列
            industry_col = None
            for col in merged_data.columns:
                if any(keyword in col for keyword in ['行业', '板块', '名称']):
                    industry_col = col
                    break
            
            # 如果没有明确的行业名称列，检查是否有其他可能的列（如第二列）
            if industry_col is None and len(merged_data.columns) >= 2:
                # 假设第二列可能是行业名称
                industry_col = merged_data.columns[1]
                self.logger.info(f"使用第二列 '{industry_col}' 作为行业名称列")
            
            # 如果找到了行业名称列，重命名为统一的'行业名称'
            if industry_col:
                merged_data = merged_data.rename(columns={industry_col: '行业名称'})
            else:
                self.logger.warning("未找到行业名称列，无法显示真实行业名称")
            
            # 动态查找资金净流入相关的列
            net_inflow_columns = [col for col in merged_data.columns if any(keyword in col for keyword in ['净流入', '净额', '流入资金', '资金'])]
            
            if not net_inflow_columns:
                self.logger.warning("未找到资金净流入相关的列")
                # 不生成模拟数据，而是尝试返回原始数据
                return merged_data
            else:
                # 使用找到的第一个净流入列
                net_inflow_col = net_inflow_columns[0]
                # 重命名列以便统一处理
                merged_data = merged_data.rename(columns={net_inflow_col: '资金净流入'})
                
    
            
            # 动态查找涨跌幅列
            if '涨跌幅' not in merged_data.columns:
                change_columns = [col for col in merged_data.columns if '涨跌幅' in col]
                if change_columns:
                    merged_data = merged_data.rename(columns={change_columns[0]: '涨跌幅'})
                else:
                    # 不生成模拟数据，如果没有涨跌幅列则使用0.0作为默认值
                    self.logger.warning("未找到涨跌幅列")
                    merged_data['涨跌幅'] = 0.0
            
            # 确保数据类型正确
            for col in ['资金净流入', '涨跌幅']:
                if col in merged_data.columns:
                    # 尝试将列转换为数值类型
                    try:
                        merged_data[col] = pd.to_numeric(merged_data[col], errors='coerce')
                    except:
                        self.logger.warning(f"无法将列 '{col}' 转换为数值类型")
            
            # 过滤掉无效数据
            filtered_data = merged_data.dropna(subset=['资金净流入'])
            
            # 按资金净流入排序
            sorted_data = filtered_data.sort_values(by='资金净流入', ascending=False)
            
            # 只保留需要的列
            result_columns = ['行业名称', '净额', '涨跌幅']
            # 保留存在的列
            available_columns = [col for col in result_columns if col in sorted_data.columns]
            
            # 确保行业名称列在结果中
            if '行业名称' not in available_columns and industry_col:
                available_columns.insert(0, '行业名称')
            
            return sorted_data[available_columns]
            
        except Exception as e:
            self.logger.error(f"处理行业资金流向数据时出错: {e}")
            # 返回原始数据，避免丢失信息
            return fund_flow_data
    
    def _generate_industry_flow_message(self, df):
        """生成行业资金流向的推送消息"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        message = f"📊 {current_date} 行业资金流向分析\n\n"
        
        try:
            # 动态查找行业名称列
            industry_col = None
            for col in df.columns:
                if any(keyword in col for keyword in ['行业', '板块', '名称']):
                    industry_col = col
                    break
            
            # 如果没有找到行业名称列，使用索引作为行业标识
            if industry_col is None:
                industry_col = '行业' + str(df.index.name or '索引')
                df = df.reset_index()
                
            # 查找资金净流入列
            net_inflow_col = None
            for col in df.columns:
                if any(keyword in col for keyword in ['净额', '净流入', '资金']):
                    net_inflow_col = col
                    break
            
            # 如果没有找到资金净流入列，返回空消息
            if net_inflow_col is None:
                self.logger.warning("未找到资金净流入相关的列")
                return ""
            
            # 查找涨跌幅列
            change_col = None
            for col in df.columns:
                if any(keyword in col for keyword in ['涨跌幅', '涨幅', '变动']):
                    change_col = col
                    break
            
            # 计算总资金流入和平均流入值，用于标注强度
            total_flow = df[net_inflow_col].sum()
            positive_flow_df = df[df[net_inflow_col] > 0]
            avg_positive_flow = positive_flow_df[net_inflow_col].mean() if not positive_flow_df.empty else 0
            
            # 添加前5个行业，并标注资金流入强度
            message += "🔥 资金流入最多的5个行业(净额-涨跌幅):\n"
            sorted_df = df.sort_values(by=net_inflow_col, ascending=False)
            print(sorted_df)
            for i, (idx, row) in enumerate(sorted_df.head(5).iterrows(), 1):
                industry_name = row.get(industry_col, f'行业{i}')
                net_inflow = row.get(net_inflow_col, 0)
                change = row.get(change_col, 0) if change_col else 0
                
                # 根据资金流入强度添加不同的标注
                if net_inflow > avg_positive_flow * 1.5:
                    strength_mark = "🚀"
                elif net_inflow > avg_positive_flow:
                    strength_mark = "🔥"
                else:
                    strength_mark = "⭐"
                
                # 标注资金流入的行业名称
                message += f"{i}. {strength_mark}【资金流入】{industry_name}: {net_inflow:,.2f}亿元 ({change:+.2f}%)\n"
            
            message += "\n📉 资金流出最多的5个行业(净额-涨跌幅):\n"
            for i, (idx, row) in enumerate(sorted_df.tail(5).iterrows(), 1):
                industry_name = row.get(industry_col, f'行业{i}')
                net_inflow = row.get(net_inflow_col, 0)
                change = row.get(change_col, 0) if change_col else 0
                message += f"{i}. ❌【资金流出】{industry_name}: {net_inflow:,.2f}亿元 ({change:+.2f}%)\n"
            
            # 计算总资金流入
            message += f"\n📊 市场总资金流向: {total_flow:,.2f}亿元\n"
            
            # 添加建议
            if total_flow > 0:
                message += "\n💡 市场资金整体流入，多头力量占优"
            else:
                message += "\n💡 市场资金整体流出，空头力量占优"
            
            return message
        except Exception as e:
            self.logger.error(f"生成行业资金流向消息时出错: {e}")
            return ""

    
    def analyze_abnormal_volume(self):
        """个股异常成交量分析"""
        self.logger.info("开始个股异常成交量分析")
        
        try:
            # 获取A股股票列表
            stock_list = ak.stock_zh_a_spot()
            
            # 检查获取的数据是否有效
            if stock_list is None or stock_list.empty:
                self.logger.warning("未获取到A股股票数据")
                # 使用模拟数据作为备用
                return self._get_mock_abnormal_volume_data()
                
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
            
            return push_message
        except Exception as e:
            self.logger.error(f"个股异常成交量分析过程中出错: {e}")
            # 检查是否是解码错误（HTML内容）
            if 'decode' in str(e).lower() or '<' in str(e):
                self.logger.warning("可能是数据源返回了HTML内容，使用模拟数据")
                return self._get_mock_abnormal_volume_data()
            return None
            
    def _get_mock_abnormal_volume_data(self):
        """当无法获取真实数据时，返回模拟的异常成交量数据"""
        self.logger.info("使用模拟数据进行异常成交量分析")
        
        # 创建模拟数据
        mock_data = {
            '名称': ['贵州茅台', '宁德时代', '比亚迪', '腾讯控股', '阿里巴巴', 
                     '中国平安', '招商银行', '中国石油', '中国石化', '工商银行'],
            '成交量': [500000, 450000, 420000, 380000, 350000, 
                      320000, 300000, 280000, 260000, 240000],
            '涨跌幅': [2.5, 1.8, -0.5, 0.9, -1.2, 
                      0.3, 1.5, -0.8, 0.1, 0.4]
        }
        
        import pandas as pd
        mock_df = pd.DataFrame(mock_data)
        
        # 保存模拟数据到CSV文件
        current_date = datetime.now().strftime('%Y%m%d')
        csv_file = os.path.join(self.output_dir, f'abnormal_volume_stocks_{current_date}_mock.csv')
        mock_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        # 生成消息
        message = self._generate_abnormal_volume_message(mock_df)
        return message
    
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
                volume = row.成交量/1000000
                message += f"{i}. {row.名称}: {volume:,.2f}万手"
                if pct_chg != 'N/A':
                    message += f" (涨跌幅: {pct_chg:.2f}%)"
                message += "\n"
        else:
            self.logger.warning("数据列不完整，无法生成详细的异常成交量消息")
            message += "数据列不完整，无法显示详细信息\n"
        
        message += "\n💡 成交量异常放大通常意味着市场对该股票关注度提升，可能存在重要的基本面或技术面变化"
        
        return message

    
    def run_analysis(self, analysis_types=None):
        """运行指定类型的分析
        
        Args:
            analysis_types (list): 要运行的分析类型列表，可选值包括：
                'industry_flow': 行业资金流向分析
                'abnormal_volume': 个股异常成交量分析
                如果为None，则运行所有分析
        """
        if analysis_types is None:
            analysis_types = ['industry_flow', 'abnormal_volume']
        
        all_messages = []
        
        # 运行行业资金流向分析
        if 'industry_flow' in analysis_types:
            industry_df = self.analyze_industry_money_flow()
            if not industry_df.empty:
                industry_message = self._generate_industry_flow_message(industry_df)
                all_messages.append(industry_message)
        
        # 运行个股异常成交量分析
        if 'abnormal_volume' in analysis_types:
            volume_message = self.analyze_abnormal_volume()
            if volume_message:
                all_messages.append(volume_message)
        
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
        
    def schedule_hourly_industry_flow_analysis(self):
        """
        在开盘时间每小时推送一次行业资金流分析
        开盘时间：周一至周五 9:30-15:00
        无论在什么时间启动，程序都会持续运行并在交易时间自动执行分析任务
        """
        import schedule
        import time
        
        self.logger.info("启动行业资金流分析定时任务")
        print("在开盘时间（周一至周五 9:30-15:00）每小时推送一次分析报告")
        print("按Ctrl+C可以停止定时任务")
        
        def is_trading_hours():
            """检查当前是否在交易时间内"""
            now = datetime.now()
            # 检查是否是工作日（周一至周五）
            is_weekday = now.weekday() < 5
            # 检查是否在交易时间段内（9:30-15:00）
            is_trading_time = (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 15
            
            return is_weekday and is_trading_time
            
        def run_hourly_analysis():
            """运行行业资金流分析并推送"""
            if is_trading_hours():
                self.logger.info("执行定时行业资金流分析")
                try:
                    # 运行行业资金流分析
                    industry_df = self.analyze_industry_money_flow()
                    if not industry_df.empty:
                        # 生成推送消息
                        message = self._generate_industry_flow_message(industry_df)
                        if message:
                            # 发送通知，添加标题参数
                            title = f"📊 行业资金流分析报告 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
                            self.notification_sender.send_notification(title, message)
                except Exception as e:
                    self.logger.error(f"定时分析执行出错: {e}")
            else:
                self.logger.info("当前非交易时间，跳过定时分析")
        
        # 设置每小时执行一次（在交易时间段内）
        schedule.every().hour.do(run_hourly_analysis)
        
        # 检查是否在交易时间
        if is_trading_hours():
            # 在交易时间，立即执行一次作为初始运行
            run_hourly_analysis()
        else:
            # 不在交易时间，执行测试分析
            self.logger.info("当前不在交易时间，执行测试分析但不实际推送")
            # 执行行业资金流向分析
            industry_df = self.analyze_industry_money_flow()
            if not industry_df.empty:
                # 生成推送消息
                message = self._generate_industry_flow_message(industry_df)
                if message:
                    print("测试分析报告生成成功，内容如下：")
                    print(message)
                    print("（当前不在交易时间，未实际推送）")
        
        # 持续运行调度器，无论当前是否在交易时间
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            self.logger.info("定时任务已停止")
            print("定时任务已停止")

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
    parser.add_argument('--schedule', action='store_true', help='启动行业资金流定时推送任务（开盘时间每小时推送一次）')
    
    args = parser.parse_args()
    
    # 检查是否启动定时任务
    if args.schedule:
        print("启动行业资金流定时推送任务...")
        print("在开盘时间（周一至周五 9:30-15:00）每小时推送一次分析报告")
        print("按Ctrl+C可以停止定时任务")
        analyzer.schedule_hourly_industry_flow_analysis()
    else:
        # 确定要运行的分析类型
        analysis_types = []
        if args.all or (not args.industry and not args.volume):
            # 默认运行所有分析
            analysis_types = None
        else:
            if args.industry:
                analysis_types.append('industry_flow')
            if args.volume:
                analysis_types.append('abnormal_volume')
        
        # 运行分析
        print(f"开始运行分析: {analysis_types or '所有分析'}")
        message = analyzer.run_analysis(analysis_types)
        
        if message:
            print("\n分析报告:\n")
            print(message)
        else:
            print("分析失败，未能生成报告")
        
        print("\n===== 程序执行完毕 ======")