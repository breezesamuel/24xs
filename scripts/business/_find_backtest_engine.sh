#!/usr/bin/env bash
# 找 CN 工具站/生产系统里现成的回测引擎 (C3~C6 要接的真实引擎)
echo "=== 1. tools-cn 站点里回测/backtest 相关端点/库 ==="
grep -rlniE "backtest|回测|strategy.*run|runBacktest|simulate|回测引擎|backtestEngine|momentum|rolling.*return" /www/wwwroot/tools-cn.highkingflower.com 2>/dev/null | grep -vE "node_modules|\.git" | head -15
echo ""
echo "=== 2. /opt/bingdashan 里回测引擎 ==="
grep -rlniE "backtest|回测|runStrategy|simulateStrategy|backtestEngine|momentum|rolling|sharpe|maxDrawdown" /opt/bingdashan 2>/dev/null | grep -vE "node_modules|\.git|i18n|web/.*i18n" | head -15
echo ""
echo "=== 3. 有没有可跑的 strategy/backtest API 端点 (HTTP) ==="
grep -rniE "api/.*backtest|api/.*strategy|/backtest|strategy/backtest|回测.*端点|端点.*回测" /opt/bingdashan/server.js /www/wwwroot/tools-cn.highkingflower.com/api 2>/dev/null | head -15
echo ""
echo "=== 4. 站点现有的指标计算 (sharpe/drawdown/收益) 引擎 ==="
grep -rniE "sharpe|drawdown|回撤|年化收益|annReturn|winRate|胜率|CAGR" /www/wwwroot/tools-cn.highkingflower.com /opt/bingdashan --include="*.js" 2>/dev/null | grep -vE "node_modules|i18n" | head -15
echo done
