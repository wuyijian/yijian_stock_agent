import os
import sys
import time
from datetime import datetime, timedelta
import subprocess
import json
import logging
import os
from notification_utils import NotificationSender
from barron_news import FinancialNewsCrawler
from kimi_financial_news import KimiFinancialNews  # 修改为Kimi财经要闻导入
from local_financial_news import LocalFinancialNews  # 添加本地财经要闻导入
from newsapi_financial_news import NewsAPIFinancialNews  # 添加NewsAPI财经要闻导入
from akshare_financial_news import AKShareFinancialNews  # 添加AKShare财经要闻导入
from macro_data_getter import MacroDataGetter  # 添加宏观经济数据获取器导入

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
        
        # 财经新闻爬虫（保留以便兼容）
        self.financial_crawler = FinancialNewsCrawler()
        
        # Kimi财经要闻获取器（更新为Kimi）
        self.kimi_news = KimiFinancialNews("notification_config.json")
        
        # 本地财经要闻生成器（作为Kimi API的替代方案）
        self.local_news = LocalFinancialNews("notification_config.json")
        
        # NewsAPI财经要闻获取器
        self.newsapi_news = NewsAPIFinancialNews("notification_config.json")
        
        # AKShare财经要闻获取器（专门用于获取新浪财经要闻）
        self.akshare_news = AKShareFinancialNews("notification_config.json")
        
        # 宏观经济数据获取器
        self.macro_data_getter = MacroDataGetter("notification_config.json")
        
        # 获取当前目录
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 配置文件路径（现在使用默认配置）
        self.config_file = None  # auto_run_config.json 已被移除
        
        # 宏观经济数据推送时间（每天上午10:30）
        self.macro_data_time = "10:30"
        
        # 加载默认配置
        self.config = self._load_config()
        
        # 分析脚本路径
        self.analysis_script = os.path.join(self.current_dir, "stock_analysis.py")
        
        # 财经要闻推送时间
        self.financial_news_time = "09:00"
    
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
        """加载配置（现在使用默认配置，不再读取配置文件）"""
        # 使用默认配置，auto_run_config.json已被移除
        default_config = {
            "schedule_time": "09:45",  # 默认每天上午9:45执行
            "analysis_types": ["industry_flow", "abnormal_volume", "us_stock"],  # 默认分析类型
            "notification_methods": None,  # 默认使用notification_config.json中的所有配置
            "timeout": 300  # 默认超时时间（秒）
        }
        
        self.logger.info("使用内置默认配置")
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
            # 移除--us参数，因为stock_analysis.py不支持这个参数
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
            
    def send_macro_data_notification(self):
        """发送宏观经济数据通知"""
        try:
            self.logger.info("开始获取并发送宏观经济数据...")
            
            # 获取中国宏观经济数据
            china_macro_data = self.macro_data_getter.get_china_macro_data()
            # 获取美国宏观经济数据
            us_macro_data = self.macro_data_getter.get_us_macro_data()
            
            # 整理通知内容
            content = "📊 每日宏观经济数据概览\n\n"
            
            # 添加中国宏观数据
            if china_macro_data:
                content += "🇨🇳 中国宏观经济数据\n"
                for data in china_macro_data:
                    content += f"- {data['指标']}: {data['值']}（{data['发布日期']}）\n"
                content += "\n"
            else:
                content += "🇨🇳 中国宏观经济数据暂无更新\n\n"
            
            # 添加美国宏观数据
            if us_macro_data:
                content += "🇺🇸 美国宏观经济数据\n"
                for data in us_macro_data:
                    content += f"- {data['指标']}: {data['值']}（{data['发布日期']}）\n"
            else:
                content += "🇺🇸 美国宏观经济数据暂无更新\n"
            
            # 添加数据更新时间
            content += f"\n🔄 数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 发送通知
            self.send_notification(content)
            
            # 记录成功发送的日期
            with open('last_macro_run.txt', 'w', encoding='utf-8') as f:
                f.write(datetime.now().strftime('%Y-%m-%d'))
                
            self.logger.info("宏观经济数据通知发送成功")
        except Exception as e:
            self.logger.error(f"发送宏观经济数据通知时发生错误: {str(e)}")
    
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
    
    def run_news_only(self):
        """仅运行财经要闻功能，实现Kimi→本地→NewsAPI→爬虫的三级回退机制"""
        self.logger.info("===== 运行财经要闻获取功能 ======")
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.logger.info(f"开始获取最新财经要闻 ({today})")
        
        # 尝试使用Kimi大模型发送财经要闻通知
        try:
            self.logger.info("尝试使用Kimi财经要闻...")
            success = self.kimi_news.send_news_notification()
            if success:
                self.logger.info("Kimi财经要闻推送成功")
                return True
            else:
                self.logger.warning("Kimi财经要闻推送失败，尝试使用本地生成器...")
        except Exception as e:
            self.logger.error(f"Kimi财经要闻执行异常: {str(e)}")
            self.logger.warning("尝试使用本地生成器...")
        
        # 尝试使用本地财经要闻生成器
        try:
            self.logger.info("尝试使用本地生成器...")
            success = self.local_news.send_news_notification()
            if success:
                self.logger.info("本地财经要闻推送成功")
                return True
            else:
                self.logger.warning("本地财经要闻生成器也失败，尝试使用NewsAPI...")
        except Exception as e:
            self.logger.error(f"本地生成器执行异常: {str(e)}")
            self.logger.warning("尝试使用NewsAPI...")
        
        # 尝试使用NewsAPI
        try:
            self.logger.info("尝试使用NewsAPI...")
            # 检查NewsAPI连接状态
            if hasattr(self.newsapi_news, 'check_connection'):
                connection_status = self.newsapi_news.check_connection()
                if not connection_status:
                    self.logger.warning("NewsAPI连接检查失败，准备回退到爬虫...")
                    # 直接尝试爬虫，不进行NewsAPI请求
                    success = self._crawl_and_send_news()
                    if success:
                        return True
                else:
                    self.logger.info("NewsAPI连接检查成功，开始获取新闻...")
                    success = self.newsapi_news.send_news_notification()
                    if success:
                        self.logger.info("NewsAPI财经要闻推送成功")
                        return True
                    else:
                        self.logger.warning("NewsAPI财经要闻获取失败，尝试使用爬虫...")
            else:
                # 如果没有check_connection方法，直接尝试获取新闻
                success = self.newsapi_news.send_news_notification()
                if success:
                    self.logger.info("NewsAPI财经要闻推送成功")
                    return True
                else:
                    self.logger.warning("NewsAPI财经要闻获取失败，尝试使用爬虫...")
        except Exception as e:
            self.logger.error(f"NewsAPI财经要闻执行异常: {str(e)}")
            self.logger.warning("尝试使用爬虫...")
        
        # 尝试使用爬虫方式
        try:
            success = self._crawl_and_send_news()
            if success:
                return True
        except Exception as e:
            self.logger.error(f"爬虫执行异常: {str(e)}")
        
        # 尝试使用原有的爬虫方式作为最后的兜底
        try:
            self.logger.info("尝试使用原有爬虫方式作为最后的兜底...")
            success = self.financial_crawler.send_news_notification()
            if success:
                self.logger.info("原有爬虫方式推送成功")
                return True
            else:
                self.logger.warning("原有爬虫方式也失败")
        except Exception as e:
            self.logger.error(f"原有爬虫方式执行异常: {str(e)}")
        
        self.logger.error("所有财经要闻获取方式均失败")
        return False
        
    def _crawl_and_send_news(self):
        """使用简单爬虫获取财经要闻并发送通知"""
        try:
            self.logger.info("尝试使用备用爬虫获取财经要闻...")
            news_content = self._crawl_financial_news()
            if news_content:
                self.logger.info("爬虫获取财经要闻成功")
                # 使用Kimi的通知方法发送爬虫获取的新闻
                title = f"📰 财经要闻 ({datetime.now().strftime('%Y-%m-%d')})"
                results = self.notification_sender.send_notification(title, news_content)
                success = any(result for result in results.values())
                if success:
                    self.logger.info("爬虫获取的财经要闻推送成功")
                else:
                    self.logger.warning("爬虫获取的财经要闻推送失败")
                return success
            else:
                self.logger.warning("爬虫未获取到任何新闻")
                return False
        except Exception as e:
            self.logger.error(f"爬虫功能执行异常: {str(e)}")
            return False
            
    def _crawl_financial_news(self):
        """简单的财经要闻爬虫实现，作为最后的回退机制"""
        try:
            import requests
            from bs4 import BeautifulSoup
            from datetime import datetime
            
            self.logger.info("使用简单爬虫获取财经要闻")
            
            # 这里选择一些可访问的中文财经网站作为爬虫目标
            # 注意：实际使用时请遵守网站的robots.txt规则
            news_sources = [
                {
                    'name': '新浪财经',
                    'url': 'https://finance.sina.com.cn/',
                    'selector': '.news-item'
                },
                {
                    'name': '东方财富网',
                    'url': 'https://finance.eastmoney.com/',
                    'selector': '.newsflash_body li'
                }
            ]
            
            crawled_news = []
            max_articles = 10
            
            for source in news_sources:
                if len(crawled_news) >= max_articles:
                    break
                
                try:
                    self.logger.info(f"爬取{source['name']}...")
                    response = requests.get(source['url'], timeout=10)
                    response.encoding = 'utf-8'
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    items = soup.select(source['selector'])
                    
                    for i, item in enumerate(items):
                        if len(crawled_news) >= max_articles:
                            break
                        
                        try:
                            # 根据不同网站的结构提取标题和链接
                            if source['name'] == '新浪财经':
                                a_tag = item.select_one('a')
                                if a_tag:
                                    title = a_tag.get_text().strip()
                                    link = a_tag.get('href')
                                    if title and len(title) > 5:
                                        crawled_news.append({
                                            'title': title,
                                            'source': source['name'],
                                            'url': link,
                                            'publishedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        })
                            elif source['name'] == '东方财富网':
                                a_tag = item.select_one('a')
                                if a_tag:
                                    title = a_tag.get_text().strip()
                                    link = a_tag.get('href')
                                    if title and len(title) > 5:
                                        crawled_news.append({
                                            'title': title,
                                            'source': source['name'],
                                            'url': link,
                                            'publishedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        })
                        except Exception as e:
                            self.logger.warning(f"解析{source['name']}新闻项时出错: {str(e)}")
                except Exception as e:
                    self.logger.warning(f"爬取{source['name']}时出错: {str(e)}")
            
            # 格式化爬取的新闻
            if crawled_news:
                formatted_news = "【爬虫获取财经要闻】\n\n"
                formatted_news += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
                for i, news in enumerate(crawled_news, 1):
                    formatted_news += f"{i}. {news['title']}\n"
                    formatted_news += f"   来源: {news['source']}\n"
                    formatted_news += f"   链接: {news['url']}\n\n"
                
                formatted_news += "\n注意：本新闻由爬虫自动抓取，可能存在时效性问题，仅供参考。"
                return formatted_news
            else:
                self.logger.warning("爬虫未获取到任何新闻")
                return None
        except Exception as e:
            self.logger.error(f"爬虫功能执行异常: {str(e)}")
            return None
    
    def run_scheduled(self):
        """启动定时任务模式"""
        self.logger.info("===== 自动运行股票分析程序 - 定时模式 ======")
        self.logger.info(f"每天预定执行时间: {self.config.get('schedule_time', '09:45')}")
        self.logger.info(f"每天财经要闻推送时间: {self.financial_news_time}")
        self.logger.info(f"每天新浪财经要闻推送时间: 17:00")
        self.logger.info(f"每天宏观经济数据推送时间: {self.macro_data_time}")
        
        while True:
            try:
                # 获取当前时间
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                today = now.strftime("%Y-%m-%d")
                
                # 获取预定执行时间
                schedule_time = self.config.get("schedule_time", "09:45")
                
                # 检查是否到达财经要闻推送时间
                if current_time == self.financial_news_time:
                    # 检查今天是否已经推送过财经要闻
                    financial_last_run_file = os.path.join(self.log_dir, "last_financial_run.txt")
                    
                    if os.path.exists(financial_last_run_file):
                        with open(financial_last_run_file, 'r') as f:
                            financial_last_run_date = f.read().strip()
                    else:
                        financial_last_run_date = ""
                    
                    if financial_last_run_date != today:
                        self.logger.info(f"到达财经要闻推送时间: {self.financial_news_time}，开始推送最新财经要闻")
                        
                        # 使用Kimi大模型发送财经要闻通知（替换原来的爬虫方式）
                        success = self.kimi_news.send_news_notification()
                        
                        # 如果Kimi大模型失败，回退到本地财经要闻生成器
                        if not success:
                            self.logger.warning("Kimi财经要闻推送失败，切换到本地财经要闻生成器")
                            success = self.local_news.send_news_notification()
                        
                        # 如果本地生成器也失败，再回退到原有的爬虫方式
                        if not success:
                            self.logger.warning("本地财经要闻生成器也失败，回退到爬虫方式")
                            success = self.financial_crawler.send_news_notification()
                        
                        if success:
                            self.logger.info("财经要闻推送完成")
                            # 记录今天已推送
                            with open(financial_last_run_file, 'w') as f:
                                f.write(today)
                        else:
                            self.logger.error("财经要闻推送失败")
                    else:
                        self.logger.info(f"今天({today})已经推送过财经要闻，跳过本次推送")
                
                # 检查是否到达新浪财经要闻推送时间（每天下午5点）
                if current_time == "17:00":
                    # 检查今天是否已经推送过新浪财经要闻
                    sina_last_run_file = os.path.join(self.log_dir, "last_sina_news_run.txt")
                    
                    if os.path.exists(sina_last_run_file):
                        with open(sina_last_run_file, 'r') as f:
                            sina_last_run_date = f.read().strip()
                    else:
                        sina_last_run_date = ""
                    
                    if sina_last_run_date != today:
                        self.logger.info(f"到达新浪财经要闻推送时间: 17:00，开始推送最新新浪财经要闻")
                        
                        # 使用AKShare获取新浪财经要闻
                        try:
                            success = self.akshare_news.send_news_notification()
                            if success:
                                self.logger.info("新浪财经要闻推送成功")
                                # 记录今天已推送
                                with open(sina_last_run_file, 'w') as f:
                                    f.write(today)
                            else:
                                self.logger.error("新浪财经要闻推送失败")
                        except Exception as e:
                            self.logger.error(f"获取新浪财经要闻时发生异常: {str(e)}")
                    else:
                        self.logger.info(f"今天({today})已经推送过新浪财经要闻，跳过本次推送")
                
                # 检查是否到达宏观经济数据推送时间
                if current_time == self.macro_data_time:
                    # 检查今天是否已经推送过宏观经济数据
                    macro_last_run_file = os.path.join(self.log_dir, "last_macro_run.txt")
                    
                    if os.path.exists(macro_last_run_file):
                        with open(macro_last_run_file, 'r') as f:
                            macro_last_run_date = f.read().strip()
                    else:
                        macro_last_run_date = ""
                    
                    if macro_last_run_date != today:
                        self.logger.info(f"到达宏观经济数据推送时间: {self.macro_data_time}，开始推送最新中美宏观经济数据")
                        
                        # 获取并发送宏观经济数据
                        try:
                            success = self.macro_data_getter.send_macro_data_notification()
                            if success:
                                self.logger.info("宏观经济数据推送成功")
                                # 记录今天已推送
                                with open(macro_last_run_file, 'w') as f:
                                    f.write(today)
                            else:
                                self.logger.error("宏观经济数据推送失败")
                        except Exception as e:
                            self.logger.error(f"获取宏观经济数据时发生异常: {str(e)}")
                    else:
                        self.logger.info(f"今天({today})已经推送过宏观经济数据，跳过本次推送")
                
                # 检查是否到达股票分析执行时间
                if current_time == schedule_time:
                    # 检查今天是否已经执行过股票分析
                    stock_last_run_file = os.path.join(self.log_dir, "last_run.txt")
                    
                    if os.path.exists(stock_last_run_file):
                        with open(stock_last_run_file, 'r') as f:
                            stock_last_run_date = f.read().strip()
                    else:
                        stock_last_run_date = ""
                    
                    if stock_last_run_date != today:
                        self.logger.info(f"到达预定执行时间: {schedule_time}，开始执行股票分析")
                        
                        # 运行分析
                        push_message = self.run_analysis()
                        
                        if push_message:
                            self.logger.info("准备发送股票分析通知")
                            # 发送通知
                            self.send_notification(push_message)
                        else:
                            self.logger.error("无法获取股票分析推送消息，通知发送失败")
                        
                        # 记录今天已执行
                        with open(stock_last_run_file, 'w') as f:
                            f.write(today)
                        
                        self.logger.info(f"今日股票分析任务已完成，下次执行时间: 明天{schedule_time}")
                    else:
                        self.logger.info(f"今天({today})已经执行过股票分析任务，跳过本次执行")
                
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
        """更新配置（仅在内存中更新，不再保存到文件）"""
        try:
            # 合并新配置
            self.config.update(new_config)
            
            self.logger.info("配置已在内存中更新")
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
    # 移除--us参数，因为stock_analysis.py不支持这个参数
    parser.add_argument('--all', action='store_true', help='运行所有分析')
    # 添加财经要闻参数
    parser.add_argument('--news', action='store_true', help='仅运行财经要闻获取和推送功能')
    parser.add_argument('--newsapi', action='store_true', help='仅使用NewsAPI获取和推送财经要闻')
    
    args = parser.parse_args()
    
    # 根据参数执行不同的逻辑
    if args.newsapi:
        # 仅使用NewsAPI运行财经要闻功能，先检查网络连接
        print("\n===== NewsAPI财经要闻功能 ======")
        print("正在检查NewsAPI服务连接状态...")
        
        # 检查网络连接
        try:
            import socket
            socket.setdefaulttimeout(5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('newsapi.org', 80))
            print("✓ NewsAPI服务连接测试通过")
        except Exception as e:
            print("\n❌ NewsAPI服务连接测试失败")
            print("错误信息: 无法连接到newsapi.org服务器")
            print("\n网络连接诊断结果:")
            print("- 您的网络可能无法访问newsapi.org")
            print("- 可能是网络限制或防火墙阻止了连接")
            print("- 请检查您的网络设置")
            print("\n建议解决方案:")
            print("1. 尝试使用 --news 参数代替 --newsapi")
            print("2. 使用 --news 参数可以启用多级回退机制 (Kimi→本地→NewsAPI→爬虫)")
            print("3. 检查您的网络设置和防火墙规则")
            print("\n是否继续尝试使用NewsAPI? (y/n): ")
            
            # 获取用户输入
            try:
                user_input = input().strip().lower()
                if user_input != 'y':
                    print("已取消NewsAPI财经要闻功能")
                    return
            except:
                print("无法获取用户输入，继续执行...")
        
        auto_analyzer.logger.info("===== 使用NewsAPI运行财经要闻获取功能 ======")
        today = datetime.now().strftime("%Y-%m-%d")
        auto_analyzer.logger.info(f"开始使用NewsAPI获取最新财经要闻 ({today})")
        success = auto_analyzer.newsapi_news.send_news_notification()
        if success:
            auto_analyzer.logger.info("NewsAPI财经要闻推送完成")
        else:
            auto_analyzer.logger.error("NewsAPI财经要闻推送失败")
        auto_analyzer.logger.info("===== NewsAPI财经要闻获取功能执行完毕 =====")
    elif args.news:
        # 仅运行财经要闻功能
        auto_analyzer.run_news_only()
    elif args.once:
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
        # 移除--us参数说明，因为stock_analysis.py不支持这个参数
        print("  --all        # 运行所有分析")
        print("  --news       # 仅运行财经要闻获取和推送功能（使用默认的多级回退机制）")
        print("  --newsapi    # 仅使用NewsAPI获取和推送财经要闻")
        print("\n示例:")
        print("  python auto_analyzer.py --once --industry --volume  # 运行行业资金和成交量分析")
        print("  python auto_analyzer.py --news  # 仅运行财经要闻获取和推送功能")
        print("  python auto_analyzer.py --newsapi  # 仅使用NewsAPI获取和推送财经要闻")
        
        # 如果没有指定参数，默认仅运行一次
        print("\n未指定参数，默认仅运行一次分析")
        auto_analyzer.run_once()

if __name__ == "__main__":
    main()