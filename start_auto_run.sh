#!/bin/bash

# 启动行业资金流向分析程序的定时执行模式

# 获取当前脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 切换到脚本所在目录
cd "$SCRIPT_DIR"

# 检查Python环境
if command -v python3 &> /dev/null
then
    PYTHON_CMD=python3
elif command -v python &> /dev/null
then
    PYTHON_CMD=python
else
    echo "错误: 未找到Python环境"
    exit 1
fi

# 启动定时执行模式
"$PYTHON_CMD" auto_run.py --schedule

# 如果脚本意外退出，添加日志
if [ $? -ne 0 ];
then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 定时执行脚本异常退出" >> logs/cron_error.log
fi