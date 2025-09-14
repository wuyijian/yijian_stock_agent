import os
import sys
import time
from datetime import datetime, timedelta
import subprocess
import json
import logging
from notification_utils import NotificationSender, create_config_template

# 配置日志
def setup_logger():
    """设置日志配置"""
    log_dir = "./logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, f"auto_run_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("industry_money_flow")

# 运行行业资金流向分析程序
def run_industry_analysis():
    """运行行业资金流向分析程序"""
    logger = setup_logger()
    logger.info("开始运行行业资金流向分析程序")
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, "industry_money_flow_demo.py")
    
    try:
        # 运行分析程序
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=current_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        # 记录程序输出
        logger.info(f"程序返回码: {result.returncode}")
        logger.info(f"程序标准输出:\n{result.stdout}")
        
        if result.stderr:
            logger.warning(f"程序标准错误输出:\n{result.stderr}")
        
        # 检查是否运行成功
        if result.returncode == 0:
            logger.info("行业资金流向分析程序运行成功")
            
            # 从输出中提取推送消息
            push_message = extract_push_message(result.stdout)
            return push_message
        else:
            logger.error(f"行业资金流向分析程序运行失败，返回码: {result.returncode}")
            return None
    except subprocess.TimeoutExpired:
        logger.error("行业资金流向分析程序运行超时")
        return None
    except Exception as e:
        logger.error(f"运行行业资金流向分析程序时发生异常: {e}")
        return None

# 从程序输出中提取推送消息
def extract_push_message(output):
    """从程序输出中提取推送消息"""
    try:
        # 查找推送消息的开始位置
        start_marker = "\n推送消息内容:\n\n"
        start_index = output.find(start_marker)
        
        if start_index != -1:
            # 提取推送消息内容
            push_message = output[start_index + len(start_marker):]
            # 去除末尾可能的其他内容
            end_marker = "\n\n===== 程序执行完毕 ====="
            end_index = push_message.find(end_marker)
            if end_index != -1:
                push_message = push_message[:end_index].strip()
            
            return push_message
        
        # 如果没有找到推送消息，尝试从文件中读取
        current_date = datetime.now().strftime('%Y%m%d')
        push_file = os.path.join("./output", f"push_message_{current_date}.txt")
        
        if os.path.exists(push_file):
            with open(push_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        
        # 如果都没有找到，返回默认消息
        return "行业资金流向分析已完成，但未找到详细报告内容"
    except Exception as e:
        logging.error(f"提取推送消息时发生异常: {e}")
        return None

# 发送通知
def send_notification(message):
    """发送通知"""
    logger = setup_logger()
    
    if not message:
        logger.warning("没有可发送的消息内容")
        return False
    
    # 确保配置文件存在
    config_file = "./notification_config.json"
    if not os.path.exists(config_file):
        create_config_template(config_file)
        logger.warning(f"配置文件{config_file}不存在，已创建模板，请根据需要修改")
    
    # 创建通知发送器
    sender = NotificationSender(config_file)
    
    # 设置通知标题
    current_date = datetime.now().strftime('%Y-%m-%d')
    title = f"📊 {current_date} 行业资金流向分析报告"
    
    # 发送通知
    logger.info("开始发送通知")
    results = sender.send_notification(title, message)
    
    # 记录发送结果
    success = any(results.values())
    if success:
        logger.info(f"通知发送成功，发送方式: {[k for k, v in results.items() if v]}")
    else:
        logger.error("所有通知方式均发送失败")
    
    return success

# 主函数
def main():
    """主函数"""
    logger = setup_logger()
    logger.info("===== 自动运行行业资金流向分析程序 =====")
    
    # 运行分析程序
    push_message = run_industry_analysis()
    
    if push_message:
        logger.info("准备发送通知")
        # 发送通知
        send_notification(push_message)
    else:
        logger.error("无法获取推送消息，通知发送失败")
    
    logger.info("===== 自动运行结束 =====")

# 定时执行逻辑
def run_scheduled():
    """定时执行逻辑"""
    logger = setup_logger()
    
    # 检查是否有配置文件，如果没有则创建
    config_file = "./auto_run_config.json"
    if not os.path.exists(config_file):
        # 创建默认配置
        default_config = {
            "schedule_time": "09:45",  # 默认在每天早上9:45执行（A股开盘后）
            "run_immediately": True  # 默认立即运行一次
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        
        logger.info(f"已创建默认配置文件: {config_file}")
    
    # 加载配置
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 获取配置的执行时间
    schedule_time_str = config.get("schedule_time", "09:45")
    run_immediately = config.get("run_immediately", True)
    
    # 如果设置了立即运行，则先运行一次
    if run_immediately:
        logger.info("根据配置，立即运行一次分析程序")
        main()
    else:
        logger.info("根据配置，不立即运行分析程序")
    
    # 解析执行时间
    try:
        hour, minute = map(int, schedule_time_str.split(':'))
        logger.info(f"配置的定时执行时间: 每天 {hour:02d}:{minute:02d}")
    except ValueError:
        logger.error(f"无效的定时执行时间格式: {schedule_time_str}，使用默认值 09:45")
        hour, minute = 9, 45
    
    # 进入定时循环
    while True:
        # 获取当前时间
        now = datetime.now()
        
        # 计算下一次执行时间
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 如果今天的执行时间已过，则设置为明天同一时间
        if next_run <= now:
            next_run += timedelta(days=1)
        
        # 计算等待时间
        wait_seconds = (next_run - now).total_seconds()
        
        logger.info(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"将等待 {wait_seconds/3600:.2f} 小时后执行")
        
        # 等待到指定时间
        time.sleep(wait_seconds)
        
        # 执行分析程序
        logger.info("到达执行时间，开始运行分析程序")
        main()

if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='自动运行行业资金流向分析程序并推送结果')
    parser.add_argument('--once', action='store_true', help='仅运行一次并退出')
    parser.add_argument('--schedule', action='store_true', help='启动定时任务模式')
    
    args = parser.parse_args()
    
    # 根据参数执行不同的逻辑
    if args.once:
        # 仅运行一次
        main()
    elif args.schedule:
        # 启动定时任务模式
        try:
            run_scheduled()
        except KeyboardInterrupt:
            print("\n定时任务已被用户中断")
    else:
        # 默认行为：仅运行一次
        print("使用方法:\n  python auto_run.py --once      # 仅运行一次并退出\n  python auto_run.py --schedule  # 启动定时任务模式")
        main()