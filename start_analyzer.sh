#!/bin/bash

# 股票分析程序启动脚本

# 获取当前脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 切换到脚本所在目录
cd "$SCRIPT_DIR"

# 检查Python环境
check_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        echo "python"
    else
        echo ""  # 未找到Python
    fi
}

PYTHON_CMD=$(check_python)

if [ -z "$PYTHON_CMD" ]; then
    echo "错误: 未找到Python环境"
    echo "请先安装Python 3.x"
    exit 1
fi

# 显示帮助信息
show_help() {
    echo "股票分析程序启动脚本"
    echo "使用方法: ./start_analyzer.sh [选项]"
    echo ""
    echo "选项:"
    echo "  --once                仅运行一次分析并退出"
    echo "  --schedule            启动定时任务模式"
    echo "  --industry            仅运行行业资金流向分析"
    echo "  --volume              仅运行个股异常成交量分析"
    echo "  --us                  仅运行美股行业分析"
    echo "  --all                 运行所有分析类型（默认）"
    echo "  --help                显示帮助信息"
    echo "  --install-deps        安装依赖包"
    echo ""
    echo "示例:"
    echo "  ./start_analyzer.sh --once --industry --volume  # 仅运行一次行业资金和成交量分析"
    echo "  ./start_analyzer.sh --schedule                  # 启动定时任务模式"
    echo "  ./start_analyzer.sh --install-deps              # 安装依赖包"
}

# 安装依赖包
install_dependencies() {
    echo "===== 安装依赖包 =====