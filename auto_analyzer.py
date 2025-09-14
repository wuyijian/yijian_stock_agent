import os
import sys
import time
from datetime import datetime, timedelta
import subprocess
import json
import logging
from notification_utils import NotificationSender

class AutoStockAnalyzer:
    """自动股票分析器，用于定时运行股票分析任务"""
    
    def __init__(self):
        """初始化自动分析器"""
        # 创建日志目录
        self.log_dir = "./logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # 设置日志
        self.logger = self._setup_logger()
        
        # 通知发送器
        self.notification_sender = NotificationSender("notification_config.json")
        
        # 获取当前目录
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 配置文件路径
        self.config_file = os.path.join(self.current_dir, "auto_run_config.json")
        
        # 加载配置
        self.config = self._load_config()
        
        # 分析脚本路径
        self.analysis_script = os.path.join(self.current_dir, "stock_analysis.py")
    
    def _setup_logger(self):
        """设置日志配置"""
        log_file = os.path.join(self.log_dir, f"auto_run_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        return logging.getLogger("auto_stock_analyzer")
    
    def _load_config(self):
        """加载配置文件"""
        default_config = {
            "schedule_time": "09:45",  # 默认每天上午9:45执行
            "analysis_types": ["industry_flow", "abnormal_volume", "us_stock"],  # 默认分析类型
            "notification_methods": None,  # 默认使用notification_config.json中的所有配置
            "timeout": 300  # 默认超时时间（秒）
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # 合并默认配置和用户配置
                default_config.update(user_config)
                self.logger.info(f"从配置文件{self.config_file}加载设置成功")
            except Exception as e:
                self.logger.error(f"加载配置文件失败: {e}")
                self.logger.info("使用默认配置")
        else:
            # 创建默认配置文件
            self.logger.warning(f"配置文件{self.config_file}不存在，创建默认配置")
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=4)
                self.logger.info(f"默认配置文件已创建: {self.config_file}")
            except Exception as e:
                self.logger.error(f"创建默认配置文件失败: {e}")
        
        return default_config
    
    def run_analysis(self, analysis_types=None):
        """运行股票分析程序
        
        Args:
            analysis_types (list): 要运行的分析类型列表，为None时使用配置文件中的设置
        
        Returns:
            str: 分析报告内容，如果运行失败则返回None
        """
        self.logger.info("开始运行股票分析程序")
        
        # 确定分析类型参数
        if analysis_types is None:
            analysis_types = self.config.get("analysis_types", [])
        
        # 构建命令参数
        cmd_args = [sys.executable, self.analysis_script]
        
        # 根据分析类型添加命令行参数
        if analysis_types:
            if "industry_flow" in analysis_types:
                cmd_args.append("--industry")
            if "abnormal_volume" in analysis_types:
                cmd_args.append("--volume")
            if "us_stock" in analysis_types:
                cmd_args.append("--us")
        else:
            # 如果没有指定分析类型，添加--all参数
            cmd_args.append("--all")
        
        self.logger.info(f"运行命令: {' '.join(cmd_args)}")
        
        try:
            # 运行分析程序
            result = subprocess.run(
                cmd_args,
                cwd=self.current_dir,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout", 300)
            )
            
            # 记录程序输出
            self.logger.info(f"程序返回码: {result.returncode}")
            
            # 记录标准输出和错误输出，但避免重复记录大量内容
            if result.stdout:
                self.logger.info(f"程序标准输出长度: {len(result.stdout)}字符")
                # 如果输出较短，记录完整内容
                if len(result.stdout) < 1000:
                    self.logger.info(f"程序标准输出:\n{result.stdout}")
                else:
                    self.logger.info(f"程序标准输出前100字符:\n{result.stdout[:100]}...")
            
            if result.stderr:
                self.logger.warning(f"程序标准错误输出:\n{result.stderr}")
            
            # 检查是否运行成功
            if result.returncode == 0:
                self.logger.info("股票分析程序运行成功")
                
                # 从输出中提取推送消息
                push_message = self._extract_push_message(result.stdout)
                return push_message
            else:
                self.logger.error(f"股票分析程序运行失败，返回码: {result.returncode}")
                return None
        except subprocess.TimeoutExpired:
            self.logger.error(f"股票分析程序运行超时（{self.config.get('timeout', 300)}秒）")
            return None
        except Exception as e:
            self.logger.error(f"运行股票分析程序时发生异常: {e}")
            return None
    
    def _extract_push_message(self, output):
        """从程序输出中提取推送消息"""
        # 尝试从输出中提取分析报告
        # 查找"分析报告:"后面的内容
        report_start = output.find("\n分析报告:\n\n")
        if report_start != -1:
            # 提取报告内容
            report_content = output[report_start + len("\n分析报告:\n\n"):]
            # 去除最后的"程序执行完毕"信息
            report_end = report_content.find("\n\n=====")
            if report_end != -1:
                report_content = report_content[:report_end]
            return report_content.strip()
        
        # 如果没有找到完整的报告，尝试提取有价值的信息
        lines = output.split("\n")
        valuable_lines = []
        
        # 查找包含关键词的行
        keywords = ["资金流入最多", "资金流出最多", "成交量最大", "涨幅最大", "跌幅最大"]
        
        for line in lines:
            for keyword in keywords:
                if keyword in line and line.strip():  # 确保行不为空
                    valuable_lines.append(line.strip())
                    break
        
        if valuable_lines:
            return "\n".join(valuable_lines)
        
        # 如果没有找到有价值的信息，返回完整输出的前一部分
        return output[:1000] if len(output) > 1000 else output
    
    def send_notification(self, message):
        """发送通知"""
        if not message:
            self.logger.error("没有可发送的消息内容")
            return False
        
        try:
            title = f"📊 股票市场分析报告 ({datetime.now().strftime('%Y-%m-%d')})"
            methods = self.config.get("notification_methods")
            
            # 发送通知
            results = self.notification_sender.send_notification(title, message, methods)
            
            # 检查是否有至少一种通知方式发送成功
            success = any(result for result in results.values())
            
            if success:
                self.logger.info("通知发送成功")
            else:
                self.logger.error("所有通知方式均发送失败")
            
            return success
        except Exception as e:
            self.logger.error(f"发送通知时发生异常: {e}")
            return False
    
    def run_once(self):
        """仅运行一次分析"""
        self.logger.info("===== 自动运行股票分析程序 - 单次模式 =====")
        
        # 运行分析程序
        push_message = self.run_analysis()
        
        if push_message:
            self.logger.info("准备发送通知")
            # 发送通知
            self.send_notification(push_message)
        else:
            self.logger.error("无法获取推送消息，通知发送失败")
        
        self.logger.info("===== 自动运行结束 =====")
    
    def run_scheduled(self):
        """启动定时任务模式"""
        self.logger.info("===== 自动运行股票分析程序 - 定时模式 =====")
        self.logger.info(f"每天预定执行时间: {self.config.get('schedule_time', '09:45')}")
        
        while True:
            try:
                # 获取当前时间
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                
                # 获取预定执行时间
                schedule_time = self.config.get("schedule_time", "09:45")
                
                # 检查是否到达执行时间
                if current_time == schedule_time:
                    # 检查今天是否已经执行过
                    last_run_file = os.path.join(self.log_dir, "last_run.txt")
                    today = now.strftime("%Y-%m-%d")
                    
                    if os.path.exists(last_run_file):
                        with open(last_run_file, 'r') as f:
                            last_run_date = f.read().strip()
                    else:
                        last_run_date = ""
                    
                    if last_run_date != today:
                        self.logger.info(f"到达预定执行时间: {schedule_time}，开始执行分析")
                        
                        # 运行分析
                        push_message = self.run_analysis()
                        
                        if push_message:
                            self.logger.info("准备发送通知")
                            # 发送通知
                            self.send_notification(push_message)
                        else:
                            self.logger.error("无法获取推送消息，通知发送失败")
                        
                        # 记录今天已执行
                        with open(last_run_file, 'w') as f:
                            f.write(today)
                        
                        self.logger.info(f"今日分析任务已完成，下次执行时间: 明天{schedule_time}")
                    else:
                        self.logger.info(f"今天({today})已经执行过分析任务，跳过本次执行")
                
                # 每分钟检查一次
                time.sleep(60)
                
            except KeyboardInterrupt:
                self.logger.info("定时任务已被用户中断")
                break
            except Exception as e:
                self.logger.error(f"定时任务执行过程中发生异常: {e}")
                # 发生异常后，等待一段时间再继续，避免频繁出错
                time.sleep(300)  # 等待5分钟
    
    def update_config(self, new_config):
        """更新配置"""
        try:
            # 合并新配置
            self.config.update(new_config)
            
            # 保存配置到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            
            self.logger.info(f"配置已更新并保存到: {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"更新配置时发生异常: {e}")
            return False

# 主函数
def main():
    """主函数"""
    # 创建自动分析器实例
    auto_analyzer = AutoStockAnalyzer()
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='自动运行股票分析程序并推送结果')
    parser.add_argument('--once', action='store_true', help='仅运行一次并退出')
    parser.add_argument('--schedule', action='store_true', help='启动定时任务模式')
    
    # 分析类型参数
    parser.add_argument('--industry', action='store_true', help='仅运行行业资金流向分析')
    parser.add_argument('--volume', action='store_true', help='仅运行个股异常成交量分析')
    parser.add_argument('--us', action='store_true', help='仅运行美股行业分析')
    parser.add_argument('--all', action='store_true', help='运行所有分析')
    
    args = parser.parse_args()
    
    # 根据参数执行不同的逻辑
    if args.once:
        # 仅运行一次
        auto_analyzer.run_once()
    elif args.schedule:
        # 启动定时任务模式
        try:
            auto_analyzer.run_scheduled()
        except KeyboardInterrupt:
            print("\n定时任务已被用户中断")
    else:
        # 显示帮助信息
        print("使用方法:")
        print("  python auto_analyzer.py --once       # 仅运行一次并退出")
        print("  python auto_analyzer.py --schedule   # 启动定时任务模式")
        print("\n分析类型选项（可与--once一起使用）:")
        print("  --industry   # 仅运行行业资金流向分析")
        print("  --volume     # 仅运行个股异常成交量分析")
        print("  --us         # 仅运行美股行业分析")
        print("  --all        # 运行所有分析")
        print("\n示例:")
        print("  python auto_analyzer.py --once --industry --volume  # 运行行业资金和成交量分析")
        
        # 如果没有指定参数，默认仅运行一次
        print("\n未指定参数，默认仅运行一次分析")
        auto_analyzer.run_once()

if __name__ == "__main__":
    main()