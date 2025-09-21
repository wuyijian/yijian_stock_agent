# 股票市场分析工具

这是一个功能强大的股票市场分析工具，集成了多种分析能力，帮助投资者更好地了解市场动态和资金流向。

## 功能特点

### 1. 行业资金流向分析
- 实时获取A股市场各行业资金流入流出数据
- 分析并可视化资金流向排名
- 生成详细的资金流向报告

### 2. 个股异常成交量分析
- 检测成交量异常放大的股票
- 分析市场关注度高的个股
- 可视化成交量排名前N的股票

### 3. 美股行业资金分析
- 使用Tushare获取美股主要指数和行业ETF数据
- 分析全球市场风险偏好
- 提供投资参考指标

## 安装指南

### 1. 环境要求
- Python 3.6+ 
- 依赖包：akshare, pandas, numpy, matplotlib, requests

### 2. 快速安装

```bash
# 克隆或下载项目到本地
cd /path/to/your/workspace

# 安装依赖包
./start_analyzer.sh --install-deps
```

### 3. 配置API凭证

1. **Tushare Token配置**
   - 需要注册Tushare账号并获取API Token
   - 可以通过环境变量设置：`export TUSHARE_TOKEN=your_token_here`
   - 或者直接在代码中修改`stock_analysis.py`文件中的默认token值

2. **通知功能配置**
   - 首次运行程序会自动生成 `notification_config.json` 配置文件模板
   - 您需要根据需要修改配置文件中的各项参数，以启用邮件、企业微信、钉钉等通知功能

## 使用方法

### 基本用法

```bash
# 运行单次分析（所有分析类型）
./start_analyzer.sh --once

# 启动定时任务模式（每天固定时间执行）
./start_analyzer.sh --schedule
```

### 高级用法

```bash
# 仅运行行业资金流向分析
./start_analyzer.sh --once --industry

# 运行行业资金和个股成交量分析
./start_analyzer.sh --once --industry --volume

# 运行所有分析类型
./start_analyzer.sh --once --all
```

### 直接运行Python脚本

```bash
# 运行主分析脚本
python stock_analysis.py

# 仅运行行业分析
python stock_analysis.py --industry

# 运行自动分析器（单次模式）
python auto_analyzer.py --once

# 运行自动分析器（定时模式）
python auto_analyzer.py --schedule
```

## 输出结果

分析结果将保存在以下位置：

- **数据文件**: `output/` 目录下，包含CSV格式的数据文件
- **图表文件**: `output/` 目录下，包含PNG格式的可视化图表
- **日志文件**: `logs/` 目录下，记录程序运行状态和错误信息
- **推送消息**: `output/` 目录下，包含生成的推送消息文本

## 配置选项

程序使用 `auto_run_config.json` 文件进行配置，主要配置项包括：

- `schedule_time`: 定时任务执行时间，默认为 "09:45"
- `analysis_types`: 要执行的分析类型列表
- `notification_methods`: 通知发送方式
- `timeout`: 程序执行超时时间（秒）

您可以根据需要修改这些配置项。

## 依赖说明

本项目主要依赖以下Python库：

- **tushare**: 提供股票市场数据接口（主要数据源）
- **akshare**: 提供辅助数据接口
- **pandas**: 数据处理和分析
- **numpy**: 数学计算
- **matplotlib**: 数据可视化
- **requests**: 网络请求

## 注意事项

1. 本工具使用的数据源主要来自 Tushare，部分数据可能有访问限制或延迟
2. 美股行业分析功能使用美股主要指数和行业ETF数据作为参考
3. 分析结果仅供参考，不构成任何投资建议
4. 如需更准确的数据，请参考官方金融数据源
5. 在使用前请确保已正确配置Tushare API Token

## 免责声明

本工具仅用于学习和研究目的，不保证数据的准确性和完整性。投资者在做出任何投资决策前，应自行承担风险，并咨询专业的金融顾问。

## 更新日志

- **V1.0**: 初始版本，集成行业资金流向分析功能
- **V2.0**: 优化代码结构，新增个股异常成交量分析和美股行业分析功能

---

© 2025 股票市场分析工具 - 让投资决策更科学