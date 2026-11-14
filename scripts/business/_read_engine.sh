#!/usr/bin/env bash
# 读 CN bds-engines.js 引擎: 入口函数 + 回测指标 + 是否可被 C3~C6 调用
echo "=== 文件头 + 引擎入口 ==="
head -60 /www/wwwroot/tools-cn.highkingflower.com/bds-engines.js
echo ""
echo "=== 导出/可调用函数 (module.exports / function runXxx) ==="
grep -nE "module\.exports|function |=>|runBacktest|runEngine|computeMetrics|sharpe|drawdown|export" /www/wwwroot/tools-cn.highkingflower.com/bds-engines.js 2>/dev/null | head -30
echo ""
echo "=== 有没有被 HTTP 端点暴露 (serverless/端点) ==="
grep -rniE "bds-engines|require.*bds-engines|/api/engine|engine.*api" /www/wwwroot/tools-cn.highkingflower.com/api 2>/dev/null | grep -v node_modules | head -10
echo done
