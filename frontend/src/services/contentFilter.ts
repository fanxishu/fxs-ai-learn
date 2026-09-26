import Taro from '@tarojs/taro';
import { ErrorCode, ERROR_TOAST } from '@/types/common';

/**
 * 方案文档 §15.3 敏感词三层过滤链 — 第一层 前端 100 正则快速拦截。
 * 目的：在不发请求的情况下尽早挡住明显违规输入，节省 Token / 带宽。
 * 注意：前端只是"粗筛"，最终以 后端 DFA + LLM 输出二次扫描 为准。
 */

// —————————————— 正则库（覆盖违规政治/黄/赌/毒/诈骗/外链/广告/脏话，约 100 条） ——————————————
const RE_BLOCKLIST: Array<[RegExp, string]> = [
  // === 1. 涉政敏感 ===
  [/习近平|胡锦涛|温家宝|李克强|江泽民|毛泽东|邓小平/i, '涉及政治敏感人物'],
  [/法轮功|全能神|门徒会|血水圣灵|观音法门|华藏宗门|被政府|镇压|六四|天安门事件/i, '涉及敏感政治事件或邪教'],
  [/台独|藏独|疆独|港独|分裂国家|反共|推翻政府|一党专政/i, '涉及分裂国家或敏感政治主张'],
  [/中国威胁|反华|辱华|汉奸|卖国贼/i, '涉及民族矛盾内容'],

  // === 2. 涉黄低俗 ===
  [/色情|黄色|黄片|黄网|裸聊|裸体|裸照|口交|性交|做爱|性爱|嫖|娼|妓|援交|约炮|一夜情|成人影片|av|a片|毛片|三级片/i, '涉及色情低俗内容'],
  [/淫|骚|逼|屌|穴|乳房|乳头|阴茎|阴道|肛交|自慰|手淫|撸管|打飞机|颜射|中出|吞精|潮吹|巨乳|爆乳|萝莉控|幼交/i, '涉及低俗性暗示内容'],
  [/18禁|成人向|里番|本子|工口|えろ|エロ|nude|porn|sex|xxx|fuck|bitch|slut|dick|pussy|asshole/i, '涉及色情或低俗外语词汇'],

  // === 3. 涉赌 ===
  [/赌博|赌球|赌马|赌石|开赌|六合彩|时时彩|快乐十分|北京赛车|pc蛋蛋|龙虎斗|百家乐|德州扑克|炸金花|牛牛|三公|博彩|赌场|老虎机|水果机|打鱼机|网赌|线上赌/i, '涉及赌博或博彩'],
  [/下注|赔率|盘口|庄家|杀庄|赢钱|输钱|回本|返水|流水|套利|菠菜|澳门赌场|威尼斯人|太阳城|皇冠|ag平台|bbin/i, '涉及赌博黑话或境外赌场'],

  // === 4. 涉毒 / 涉枪 / 暴力 ===
  [/毒品|冰毒|海洛因|大麻|摇头丸|k粉|可卡因|白粉|麻古|开心果|浴盐|丧尸药|吸毒|贩毒|制毒|种毒|瘾君子|戒毒|嗑药/i, '涉及毒品违法内容'],
  [/枪支|手枪|步枪|狙击枪|机枪|霰弹枪|子弹|弹药|军火|炸药|雷管|手榴弹|火箭炮|导弹|气枪|仿真枪|买枪|卖枪|走私枪/i, '涉及枪支/弹药违法内容'],
  [/杀人|杀死|砍人|碎尸|分尸|抛尸|奸杀|虐杀|毒杀|灭口|自杀|自残|跳楼|割腕|上吊|烧炭|开煤气|吃安眠药/i, '涉及暴力或自杀自残内容'],
  [/恐怖袭击|人肉炸弹|劫持|劫机|绑架|撕票|敲诈|勒索|抢劫|抢夺|盗窃|偷窃|诈骗|传销|敲诈勒索/i, '涉及犯罪行为描述'],
  [/殴打|群殴|校园暴力|霸凌|施暴|虐待|家暴|体罚|虐待动物|虐猫|虐狗/i, '涉及暴力虐待内容'],

  // === 5. 诈骗 / 传销 / 违规金融 ===
  [/传销|直销|层级分销|拉人头|交会费|代理费|加盟费|躺赚|日赚|月入过万|轻松赚钱|空手套白狼|无本万利|暴富|财务自由捷径/i, '涉及传销/虚假暴富宣传'],
  [/套路贷|高利贷|裸贷|校园贷|佳丽贷|空放|短拆|过桥|零用贷|714高炮|砍头息|借条|借贷宝|今借到|米房|有凭证/i, '涉及违规借贷'],
  [/非法集资|私募|拆分盘|互助盘|分红盘|复利盘|代币|虚拟币|ico|炒币|挖矿|比特币之外的传销币|空气币|资金盘/i, '涉及违规金融活动'],
  [/加微信|加vx|加v信|加weixin|加qq|加扣扣|私聊我|私信我|联系方式|联系我|电话号|手机号|qq群|微信群|公众号关注|加群领取/i, '涉及引流/外链联系方式'],
  [/点击链接|扫描二维码|领取红包|免费领|0元购|一元购|刷单|刷好评|刷信誉|刷钻|刷榜|互刷|信誉提升|店铺装修代运营/i, '涉及刷单诈骗或营销外链'],

  // === 6. 脏话 / 人身攻击 ===
  [/傻逼|煞笔|sb|操你|草你|日你|妈的|尼玛|你妈|你娘|狗日|畜生|杂种|贱人|婊子|骚货|破鞋|窝囊废|废物|垃圾人|白痴|弱智|智障|脑残|神经病|滚蛋|去死/i, '涉及脏话或人身攻击'],
  [/nigger|nigga|faggot|retard|whore|slut|bastard|asshole|motherfucker|son of a bitch/i, '涉及英文脏话或歧视语'],

  // === 7. 邪教 / 迷信 ===
  [/算命|八字合婚|风水大师|作法|降头|养小鬼|古曼童|泰国佛牌|跳大神|看相|手相|面相|驱邪|驱魔|辟邪|灵符|符咒|巫术|蛊术/i, '涉及封建迷信或巫术'],
];

// 长度校验常量（与后端同步：2~500 字）
export const MIN_INPUT_LEN = 2;
export const MAX_INPUT_LEN = 500;

export interface ContentFilterResult {
  ok: boolean;
  reason?: string;
  errorCode?: number;
}

/**
 * 前端输入校验三件套：长度 + 敏感正则 + 空值。
 * ok=true 可放行；ok=false 直接 Toast + 不发请求。
 */
export function validateUserInput(raw: unknown): ContentFilterResult {
  if (raw == null) {
    return { ok: false, reason: '请输入学习内容', errorCode: ErrorCode.PARAM_MISSING };
  }
  const text = typeof raw === 'string' ? raw : String(raw);
  const trimmed = text.trim();

  if (!trimmed) {
    return { ok: false, reason: '请输入学习内容', errorCode: ErrorCode.PARAM_MISSING };
  }
  // 纯标点 / 纯空白也算无效
  if (/^[\p{P}\p{Z}\p{S}]+$/u.test(trimmed)) {
    return { ok: false, reason: '请输入有效内容', errorCode: ErrorCode.INPUT_TOO_SHORT };
  }
  if (trimmed.length < MIN_INPUT_LEN) {
    return { ok: false, reason: `输入过短，至少 ${MIN_INPUT_LEN} 个字`, errorCode: ErrorCode.INPUT_TOO_SHORT };
  }
  if (trimmed.length > MAX_INPUT_LEN) {
    return {
      ok: false,
      reason: `输入过长，请删减到 ${MAX_INPUT_LEN} 字以内（当前 ${trimmed.length} 字）`,
      errorCode: ErrorCode.INPUT_TOO_LONG,
    };
  }

  for (const [re, label] of RE_BLOCKLIST) {
    if (re.test(trimmed)) {
      return {
        ok: false,
        reason: `输入内容不合规：${label}`,
        errorCode: ErrorCode.INPUT_CONTENT_VIOLATION,
      };
    }
  }

  return { ok: true };
}

/** 校验不通过时统一 Toast。返回 true 表示通过可以继续。 */
export function validateAndToast(raw: unknown): boolean {
  const r = validateUserInput(raw);
  if (r.ok) return true;
  const msg = r.reason || ERROR_TOAST[r.errorCode ?? ErrorCode.PARAM_INVALID] || '输入有误';
  Taro.showToast({ title: msg, icon: 'none', duration: 2000 });
  return false;
}

const NICK_MIN_LEN = 1
const NICK_MAX_LEN = 20

export function validateNickname(raw: unknown): boolean {
  if (raw == null) {
    Taro.showToast({ title: '昵称不能为空', icon: 'none' })
    return false
  }
  const text = typeof raw === 'string' ? raw : String(raw)
  const trimmed = text.trim()
  if (!trimmed) {
    Taro.showToast({ title: '昵称不能为空', icon: 'none' })
    return false
  }
  if (trimmed.length < NICK_MIN_LEN) {
    Taro.showToast({ title: '昵称过短', icon: 'none' })
    return false
  }
  if (trimmed.length > NICK_MAX_LEN) {
    Taro.showToast({ title: `昵称最多 ${NICK_MAX_LEN} 字符`, icon: 'none' })
    return false
  }
  for (const [re, label] of RE_BLOCKLIST) {
    if (re.test(trimmed)) {
      Taro.showToast({ title: `昵称不合规：${label}`, icon: 'none', duration: 2000 })
      return false
    }
  }
  return true
}
