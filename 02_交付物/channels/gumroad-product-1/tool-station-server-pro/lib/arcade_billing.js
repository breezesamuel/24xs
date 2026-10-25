'use strict';
/**
 * arcade_billing.js — AI Arcade 服务器权威计费核心（纯函数，可单测）
 *
 * 修复的漏洞（原 alipay.js /api/arcade tick 分支）：
 *   原逻辑每次心跳都把「邀请奖励全额」加回余额：
 *     balanceSeconds = max(0, balanceSeconds + effBonus - br)
 *   即奖励被每个 tick 反复计入 → 余额只涨不跌 → 可无限刷时长。
 *
 * 正确语义：
 *   1) 免费额度（arc_free_，新用户一次性 600s）优先扣；
 *   2) 邀请奖励（friends×600，上限 INVITE_CAP）只把「增量」一次性并入余额，
 *      用水位账本 arc_bapp_ 记录已并入额度，杜绝重复加回；
 *   3) 付费/奖励余额只做扣减，永不加回。
 */

const MAX_ELAPSED = 90; // 单次心跳最多计 90s（防刷新/跳时间戳刷秒）

/**
 * @param {{freeLeft:number, bal:number, bonusTarget:number, bonusApplied:number}} state
 * @param {number} elapsedSeconds 相邻心跳间隔（秒，由服务器时钟算）
 * @returns {{freeLeft:number, bal:number, bonusTarget:number, bonusApplied:number,
 *            elapsed:number, usedFree:number, usedPaid:number}}
 */
function applyTick(state, elapsedSeconds) {
  const freeLeft0 = Math.max(0, parseInt(state.freeLeft || 0, 10) || 0);
  let bal = Math.max(0, parseInt(state.bal || 0, 10) || 0);
  const bonusTarget = Math.max(0, parseInt(state.bonusTarget || 0, 10) || 0);
  let bonusApplied = Math.max(0, parseInt(state.bonusApplied || 0, 10) || 0);

  const elapsed = Math.max(0, Math.min(MAX_ELAPSED, Math.floor(elapsedSeconds || 0)));

  // 1) 免费额度优先
  const usedFree = Math.min(freeLeft0, elapsed);
  const freeLeft = freeLeft0 - usedFree;
  let remaining = elapsed - usedFree;

  // 2) 邀请奖励增量一次性并入（修复点：只有 target > applied 才补差额）
  if (bonusTarget > bonusApplied) {
    bal += bonusTarget - bonusApplied;
    bonusApplied = bonusTarget;
  }

  // 3) 扣付费/奖励余额
  const usedPaid = Math.min(bal, remaining);
  bal -= usedPaid;
  remaining -= usedPaid;

  return { freeLeft, bal, bonusTarget, bonusApplied, elapsed, usedFree, usedPaid };
}

module.exports = { applyTick, MAX_ELAPSED };
