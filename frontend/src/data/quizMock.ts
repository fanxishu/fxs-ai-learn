import type {
  QuizGenerateRequest,
  QuizGenerateResult,
  ReportGenerateRequest,
  ReportGenerateResult,
  Question,
  AnswerRecord,
} from '@/types/quiz'

type KnowledgeBank = {
  topic: RegExp
  bank: Omit<Question, 'id'>[]
  mastery_pool: { mastered: string[]; weak: string[] }
}

const PYTHON_BANK: Omit<Question, 'id'>[] = [
  {
    question_type: 'single',
    stem: '在 Python 中，以下哪个关键字用于定义函数？',
    options: [
      { key: 'A', text: 'function' },
      { key: 'B', text: 'def' },
      { key: 'C', text: 'func' },
      { key: 'D', text: 'define' },
    ],
    answer: 'B',
    knowledge_point: 'Python 函数定义',
    explanation: '在 Python 中使用 def 关键字来定义函数，例如：def add(a, b): return a + b。',
    difficulty: 1,
  },
  {
    question_type: 'single',
    stem: 'Python 中，下列哪个方法可以向列表末尾添加一个元素？',
    options: [
      { key: 'A', text: 'append()' },
      { key: 'B', text: 'add()' },
      { key: 'C', text: 'insert()' },
      { key: 'D', text: 'push()' },
    ],
    answer: 'A',
    knowledge_point: 'Python 列表方法',
    explanation: 'list.append(x) 用于在列表末尾添加元素；insert 是指定位置插入；set 使用 add。',
    difficulty: 1,
  },
  {
    question_type: 'single',
    stem: '表达式 3 ** 2 的值是多少？',
    options: [
      { key: 'A', text: '6' },
      { key: 'B', text: '9' },
      { key: 'C', text: '5' },
      { key: 'D', text: '8' },
    ],
    answer: 'B',
    knowledge_point: 'Python 运算符',
    explanation: '** 是 Python 的幂运算运算符，3**2 = 3^2 = 9。',
    difficulty: 1,
  },
  {
    question_type: 'multiple',
    stem: '以下哪些类型属于 Python 中的不可变（immutable）类型？（多选）',
    options: [
      { key: 'A', text: 'int' },
      { key: 'B', text: 'str' },
      { key: 'C', text: 'list' },
      { key: 'D', text: 'tuple' },
    ],
    answer: ['A', 'B', 'D'],
    knowledge_point: 'Python 可变/不可变类型',
    explanation: 'int/str/tuple 都是不可变的，一旦创建内容不能修改；list 和 dict 是可变类型。',
    difficulty: 2,
  },
  {
    question_type: 'judge',
    stem: 'Python 中以 # 开头的行是单行注释。',
    options: [
      { key: 'T', text: '正确' },
      { key: 'F', text: '错误' },
    ],
    answer: 'T',
    knowledge_point: 'Python 注释',
    explanation: 'Python 使用 # 作为单行注释；多行注释可用三引号字符串。',
    difficulty: 1,
  },
]

const JAVA_BANK: Omit<Question, 'id'>[] = [
  {
    question_type: 'single',
    stem: '在 Java 中，下列哪个关键字用于定义一个类？',
    options: [
      { key: 'A', text: 'class' },
      { key: 'B', text: 'def' },
      { key: 'C', text: 'struct' },
      { key: 'D', text: 'interface' },
    ],
    answer: 'A',
    knowledge_point: 'Java 类定义',
    explanation: 'Java 使用 class 关键字定义类，例如：public class User { ... }。',
    difficulty: 1,
  },
  {
    question_type: 'single',
    stem: '下列哪个是 Java 中创建线程的推荐方式？',
    options: [
      { key: 'A', text: '继承 Thread 类并重写 run()' },
      { key: 'B', text: '实现 Runnable 接口并传给 Thread' },
      { key: 'C', text: '直接调用 start() 静态方法' },
      { key: 'D', text: '使用 run() 启动线程' },
    ],
    answer: 'B',
    knowledge_point: 'Java 多线程',
    explanation: '实现 Runnable（或 Callable）+ 线程池是推荐做法，避免单继承限制并利于组合。',
    difficulty: 2,
  },
  {
    question_type: 'multiple',
    stem: '下列哪些属于 Java 23 种设计模式中的「创建型模式」？（多选）',
    options: [
      { key: 'A', text: '单例 Singleton' },
      { key: 'B', text: '工厂方法 Factory Method' },
      { key: 'C', text: '策略 Strategy' },
      { key: 'D', text: '建造者 Builder' },
    ],
    answer: ['A', 'B', 'D'],
    knowledge_point: 'Java 设计模式-创建型',
    explanation: 'Strategy 属于行为型模式；单例/工厂方法/建造者/抽象工厂/原型是 5 种创建型。',
    difficulty: 2,
  },
  {
    question_type: 'single',
    stem: '观察者模式（Observer）最适合以下哪个场景？',
    options: [
      { key: 'A', text: '对象创建过程复杂，希望分步构造' },
      { key: 'B', text: '一个对象状态变化，多个依赖对象自动收到通知并更新' },
      { key: 'C', text: '把请求封装成对象，支持排队和撤销' },
      { key: 'D', text: '动态给对象添加职责' },
    ],
    answer: 'B',
    knowledge_point: 'Java 设计模式-观察者',
    explanation: 'Observer = 发布-订阅，典型：事件总线、Spring ApplicationEvent、监听器。',
    difficulty: 2,
  },
  {
    question_type: 'judge',
    stem: 'Java 中 String 是不可变对象（immutable）。',
    options: [
      { key: 'T', text: '正确' },
      { key: 'F', text: '错误' },
    ],
    answer: 'T',
    knowledge_point: 'Java String',
    explanation: 'String 对象一旦创建，其 char[] 内容不能再修改，substring/concat 等都会返回新对象。',
    difficulty: 1,
  },
]

const JS_BANK: Omit<Question, 'id'>[] = [
  {
    question_type: 'single',
    stem: 'JavaScript 中，typeof null 的结果是？',
    options: [
      { key: 'A', text: '"null"' },
      { key: 'B', text: '"undefined"' },
      { key: 'C', text: '"object"' },
      { key: 'D', text: '"number"' },
    ],
    answer: 'C',
    knowledge_point: 'JS 类型与 typeof',
    explanation: '这是 JS 历史遗留 bug：typeof null === "object"，实际要判断 null 应用 value === null。',
    difficulty: 2,
  },
  {
    question_type: 'single',
    stem: '下列哪段代码会触发 JavaScript 的「事件循环」先执行微任务？',
    options: [
      { key: 'A', text: 'setTimeout(fn, 0)' },
      { key: 'B', text: 'Promise.resolve().then(fn)' },
      { key: 'C', text: 'setInterval(fn, 100)' },
      { key: 'D', text: 'XMLHttpRequest onload 回调' },
    ],
    answer: 'B',
    knowledge_point: 'JS 事件循环：宏微任务',
    explanation: 'Promise.then / queueMicrotask / MutationObserver 属于微任务，在当前宏任务末尾同步执行，优先于 setTimeout 等宏任务。',
    difficulty: 3,
  },
  {
    question_type: 'multiple',
    stem: '以下哪些是 JavaScript 的「原始类型」（primitive）？（多选）',
    options: [
      { key: 'A', text: 'string' },
      { key: 'B', text: 'number' },
      { key: 'C', text: 'Array' },
      { key: 'D', text: 'Symbol' },
    ],
    answer: ['A', 'B', 'D'],
    knowledge_point: 'JS 原始类型 vs 引用类型',
    explanation: '7 种原始类型：null / undefined / boolean / number / bigint / string / symbol；Array 是引用类型（object）。',
    difficulty: 2,
  },
  {
    question_type: 'single',
    stem: 'const arr = [1,2,3]; arr.push(4); 之后 arr.length 是？',
    options: [
      { key: 'A', text: '报错，因为 const 不能修改' },
      { key: 'B', text: '3' },
      { key: 'C', text: '4' },
      { key: 'D', text: 'undefined' },
    ],
    answer: 'C',
    knowledge_point: 'JS const 引用',
    explanation: 'const 只保证「变量绑定不被重新赋值」，数组本身内容可变；push 会修改原数组，长度变为 4。',
    difficulty: 2,
  },
  {
    question_type: 'judge',
    stem: '=== 和 == 的区别是：=== 比较类型和值，== 只比较值（会做隐式类型转换）。',
    options: [
      { key: 'T', text: '正确' },
      { key: 'F', text: '错误' },
    ],
    answer: 'T',
    knowledge_point: 'JS 相等比较',
    explanation: '日常开发推荐始终用 === 以避免 [1] == true、"0" == false 等反直觉结果。',
    difficulty: 1,
  },
]

const REACT_BANK: Omit<Question, 'id'>[] = [
  {
    question_type: 'single',
    stem: '在 React 18 函数组件中，哪个 Hook 用于管理本地状态？',
    options: [
      { key: 'A', text: 'useEffect' },
      { key: 'B', text: 'useState' },
      { key: 'C', text: 'useContext' },
      { key: 'D', text: 'useRef' },
    ],
    answer: 'B',
    knowledge_point: 'React Hooks：useState',
    explanation: 'useState 返回 [state, setState]，setState 触发组件重新渲染。',
    difficulty: 1,
  },
  {
    question_type: 'multiple',
    stem: '以下哪些场景适合使用 useEffect？（多选）',
    options: [
      { key: 'A', text: '组件挂载时请求接口拉数据' },
      { key: 'B', text: '渲染时直接计算派生值' },
      { key: 'C', text: '订阅全局事件，卸载时解绑' },
      { key: 'D', text: '依赖变化后同步写入 localStorage' },
    ],
    answer: ['A', 'C', 'D'],
    knowledge_point: 'React Hooks：useEffect 场景',
    explanation: '渲染时派生值直接在函数体内计算即可，不需要 effect（反而会多一次 render）。',
    difficulty: 2,
  },
  {
    question_type: 'single',
    stem: '关于 React 18 自动批处理（Automatic Batching），下列说法正确的是？',
    options: [
      { key: 'A', text: '只有合成事件里的多次 setState 才会合并成一次渲染' },
      { key: 'B', text: 'Promise / setTimeout / 原生事件回调里的多次 setState 也会合并成一次渲染' },
      { key: 'C', text: '每次 setState 必定触发一次渲染' },
      { key: 'D', text: 'useState 不会被批处理，只有 useReducer 会' },
    ],
    answer: 'B',
    knowledge_point: 'React 18 Automatic Batching',
    explanation: 'React 18 之后，所有上下文（Promise/setTimeout/原生事件/微任务）都会自动批处理，性能更好。',
    difficulty: 3,
  },
  {
    question_type: 'single',
    stem: 'useCallback 和 useMemo 的主要区别是？',
    options: [
      { key: 'A', text: '两者完全一样，可以互换' },
      { key: 'B', text: 'useCallback 缓存「函数引用」；useMemo 缓存「计算的返回值」' },
      { key: 'C', text: 'useMemo 只能缓存数字/字符串，不能缓存对象' },
      { key: 'D', text: 'useCallback 可以直接改变状态' },
    ],
    answer: 'B',
    knowledge_point: 'React Hooks：useCallback vs useMemo',
    explanation: '可以把 useCallback(fn, deps) 理解成 useMemo(() => fn, deps) 的语法糖。',
    difficulty: 2,
  },
  {
    question_type: 'judge',
    stem: '子组件 React.memo 默认只做 props 的浅比较（shallow equal）。',
    options: [
      { key: 'T', text: '正确' },
      { key: 'F', text: '错误' },
    ],
    answer: 'T',
    knowledge_point: 'React memo 浅比较',
    explanation: '所以父组件每次渲染若 inline 传对象/数组/函数作为 props，memo 会失效，要用 useMemo/useCallback 配合。',
    difficulty: 2,
  },
]

const HTTP_BANK: Omit<Question, 'id'>[] = [
  {
    question_type: 'single',
    stem: 'HTTP 默认端口和 HTTPS 默认端口分别是？',
    options: [
      { key: 'A', text: '80 和 443' },
      { key: 'B', text: '8080 和 8443' },
      { key: 'C', text: '21 和 22' },
      { key: 'D', text: '3306 和 5432' },
    ],
    answer: 'A',
    knowledge_point: 'HTTP 端口',
    explanation: '8080/8443 是常用的「非特权端口」替代，不是默认；21=FTP, 22=SSH, 3306=MySQL, 5432=PostgreSQL。',
    difficulty: 1,
  },
  {
    question_type: 'multiple',
    stem: 'HTTPS 相比 HTTP 的主要改进有哪些？（多选）',
    options: [
      { key: 'A', text: '加密传输，中间人抓不到明文' },
      { key: 'B', text: '身份认证（通过数字证书确认服务器是真的）' },
      { key: 'C', text: '完整性校验，防篡改' },
      { key: 'D', text: '速度一定比 HTTP 快很多' },
    ],
    answer: ['A', 'B', 'C'],
    knowledge_point: 'HTTP vs HTTPS',
    explanation: 'HTTPS 多了 TLS 握手和加解密，首次建连比 HTTP 慢；但 HTTP/2 / HTTP/3 通常基于 TLS 部署，配合现代优化整体体验更好。',
    difficulty: 2,
  },
  {
    question_type: 'single',
    stem: 'HTTP 状态码 304 Not Modified 表示什么？',
    options: [
      { key: 'A', text: '请求参数错误' },
      { key: 'B', text: '服务器内部错误' },
      { key: 'C', text: '资源未变，可以继续使用浏览器缓存' },
      { key: 'D', text: '请求方法不允许' },
    ],
    answer: 'C',
    knowledge_point: 'HTTP 缓存：304',
    explanation: '304 配合 If-Modified-Since / ETag 做协商缓存，节省带宽；400=参数错, 500=服务器错, 405=方法不允许。',
    difficulty: 2,
  },
  {
    question_type: 'single',
    stem: '下列关于 GET 和 POST 的区别，正确的是？',
    options: [
      { key: 'A', text: 'GET 绝对没有请求体，只有 POST 有' },
      { key: 'B', text: 'GET 请求长度受浏览器/代理限制，POST 通常可以更大' },
      { key: 'C', text: 'POST 比 GET 更安全，因为参数在 body 里看不到' },
      { key: 'D', text: 'HTTP 规范规定 GET 不能产生副作用' },
    ],
    answer: 'B',
    knowledge_point: 'HTTP GET vs POST',
    explanation: 'A：HTTP 没禁止 GET 带 body，只是多数服务器/客户端不推荐；C：HTTPS 下两者都加密，安全不应靠位置；D 是 RESTful 的语义约定，不是 HTTP 强制。',
    difficulty: 3,
  },
  {
    question_type: 'judge',
    stem: '跨域请求时，浏览器会先对非简单请求发送 OPTIONS 预检（preflight）。',
    options: [
      { key: 'T', text: '正确' },
      { key: 'F', text: '错误' },
    ],
    answer: 'T',
    knowledge_point: 'CORS 预检',
    explanation: '简单请求（GET/HEAD/POST + 几个 MIME + 少数 header）直接发；否则先发 OPTIONS 问服务器是否允许，再发真正请求。',
    difficulty: 2,
  },
]

const GENERIC_BANK: Omit<Question, 'id'>[] = [
  {
    question_type: 'single',
    stem: '在软件工程中，「单一职责原则」（SRP）的核心是？',
    options: [
      { key: 'A', text: '一个类/模块只做一件事，只有一个引起变化的原因' },
      { key: 'B', text: '尽量少写注释' },
      { key: 'C', text: '所有代码写在一个函数里，减少文件数' },
      { key: 'D', text: '优先用继承而不是组合' },
    ],
    answer: 'A',
    knowledge_point: 'SOLID-SRP',
    explanation: 'SRP 是 SOLID 首字母：单一职责带来可读性/可测性/可维护性；其他三个都是反模式。',
    difficulty: 2,
  },
  {
    question_type: 'single',
    stem: '时间复杂度 O(n log n) 对应的常见排序算法是？',
    options: [
      { key: 'A', text: '冒泡排序' },
      { key: 'B', text: '归并排序 MergeSort' },
      { key: 'C', text: '插入排序' },
      { key: 'D', text: '选择排序' },
    ],
    answer: 'B',
    knowledge_point: '算法：排序复杂度',
    explanation: '冒泡/插入/选择都是 O(n^2)；归并/快速排序（平均）/堆排序是 O(n log n)。',
    difficulty: 2,
  },
  {
    question_type: 'multiple',
    stem: '以下哪些是常见的关系型数据库？（多选）',
    options: [
      { key: 'A', text: 'PostgreSQL' },
      { key: 'B', text: 'MySQL' },
      { key: 'C', text: 'MongoDB' },
      { key: 'D', text: 'SQLite' },
    ],
    answer: ['A', 'B', 'D'],
    knowledge_point: '数据库分类',
    explanation: 'MongoDB 是文档型 NoSQL；PostgreSQL / MySQL / SQLite 都基于 SQL 和关系模型。',
    difficulty: 1,
  },
  {
    question_type: 'single',
    stem: 'Git 中下列哪个命令用来「暂存当前未提交的修改，切分支做别的，之后再恢复」？',
    options: [
      { key: 'A', text: 'git stash' },
      { key: 'B', text: 'git reset --hard' },
      { key: 'C', text: 'git cherry-pick' },
      { key: 'D', text: 'git rebase' },
    ],
    answer: 'A',
    knowledge_point: 'Git stash',
    explanation: 'git stash push 入栈，git stash pop 恢复；其他三个都会直接动 commit 或工作区。',
    difficulty: 2,
  },
  {
    question_type: 'judge',
    stem: '测试驱动开发（TDD）的典型流程是：先写测试（红）→ 写实现让测试过（绿）→ 重构。',
    options: [
      { key: 'T', text: '正确' },
      { key: 'F', text: '错误' },
    ],
    answer: 'T',
    knowledge_point: '工程方法：TDD',
    explanation: 'Red → Green → Refactor，保证每个行为都有测试兜底，且代码不会过度设计。',
    difficulty: 1,
  },
]

const KNOWLEDGE_BANKS: KnowledgeBank[] = [
  {
    topic: /python|爬虫|django|flask|pandas|numpy|py\b/i,
    bank: PYTHON_BANK,
    mastery_pool: {
      mastered: ['函数定义与调用掌握', '列表/字典等核心数据结构熟练', '运算符与基础语法牢固'],
      weak: ['可变/不可变类型边界模糊', '列表与集合方法混淆', '编码规范（PEP8）需注意'],
    },
  },
  {
    topic: /java|jvm|spring|springboot|servlet|maven|gradle|mybatis|设计模式|多线程|并发|juc/i,
    bank: JAVA_BANK,
    mastery_pool: {
      mastered: ['面向对象（类/接口）掌握扎实', 'JDK 核心类库（String/集合）熟练', '多线程基础模型理解'],
      weak: ['创建型/结构型/行为型模式易混', '线程安全与锁机制需加深', 'JVM 内存结构可再巩固'],
    },
  },
  {
    topic: /javascript|js\b|typescript|ts\b|es6|esnext|原型|闭包|this|异步|promise|事件循环|node|nodejs|webpack|vite/i,
    bank: JS_BANK,
    mastery_pool: {
      mastered: ['7 种原始类型与引用类型区分清楚', '相等比较/类型转换模型建立', '事件循环宏微任务掌握'],
      weak: ['原型链与继承机制易混', '作用域与 this 绑定需再巩固', '常见内存泄漏场景可总结'],
    },
  },
  {
    topic: /react|hooks|redux|mobx|next|nextjs|jsx|tsx|fiber|虚拟dom|vdom/i,
    bank: REACT_BANK,
    mastery_pool: {
      mastered: ['常用 Hooks（useState/useEffect/useMemo）熟练', '父子组件数据流与 Props 掌握', '渲染优化（memo/依赖）基本意识到位'],
      weak: ['Hooks 依赖数组细节易漏', 'useEffect 滥用（effect 里做本可同步派生的值）', 'Concurrent/RSC 模式需再了解'],
    },
  },
  {
    topic: /http|https|网络|tcp|websocket|rest|cors|dns|三次握手|四次挥手|ssl|tls/i,
    bank: HTTP_BANK,
    mastery_pool: {
      mastered: ['HTTP 方法与状态码掌握', 'HTTPS 三大价值（加密/认证/完整）理解', '缓存（强缓存/协商缓存）模型清楚'],
      weak: ['HTTP/2 / HTTP/3 差异需再记', 'CORS 预检与携带凭证细节易混', 'HTTPS 握手阶段可再拆解'],
    },
  },
]

function pickBank (raw: string): { bank: Omit<Question, 'id'>[]; mastery_pool: { mastered: string[]; weak: string[] } } {
  const text = (raw || '').trim()
  for (const k of KNOWLEDGE_BANKS) {
    if (k.topic.test(text)) return { bank: k.bank, mastery_pool: k.mastery_pool }
  }
  return {
    bank: GENERIC_BANK,
    mastery_pool: {
      mastered: ['核心概念掌握扎实', '基础能力到位', '答题节奏稳定'],
      weak: ['细节边界需再打磨', '易混点可单独整理对比表', '建议做错题卡片间隔复习'],
    },
  }
}

function cloneWithIds (qs: Omit<Question, 'id'>[]): Question[] {
  return qs.map((q, i) => ({ ...q, id: `q-mock-${i + 1}` }))
}

export function mockQuiz (req: QuizGenerateRequest): QuizGenerateResult {
  const { bank } = pickBank(req.user_input || '')
  const count = Math.min(Math.max(req.question_count ?? 5, 3), 5)
  const qs = cloneWithIds(bank.slice(0, count))
  const titleBase = (req.user_input || '通用知识').slice(0, 12)
  return {
    quiz_id: `quiz_mock_${Date.now()}`,
    title: `${titleBase} · 闯关题`,
    questions: qs,
  }
}

export function mockReport (req: ReportGenerateRequest): ReportGenerateResult {
  const records = req.answer_records || []
  const total = records.length || 1
  const correct = records.filter(r => !!r.is_correct).length
  const acc = Math.round((correct / total) * 100)
  const { mastery_pool } = pickBank(req.topic || '')
  const mastered = acc >= 60 ? mastery_pool.mastered.slice(0, 2) : ['基础仍需巩固，暂无稳定掌握项']
  const weak = acc < 80 ? mastery_pool.weak.slice(0, 2) : ['暂无明显薄弱，保持练习即可']
  const topicName = (req.topic || '本次闯关').slice(0, 12)

  return {
    accuracy: acc,
    mastered_points: mastered,
    weak_points: weak,
    three_line_summary: [
      `你在「${topicName}」闯关中答对了 ${correct} / ${total} 题，正确率 ${acc}%。`,
      acc >= 80
        ? '整体掌握很扎实，已经具备进阶学习的基础。'
        : acc >= 60
          ? '基础过关，建议把薄弱点用「对比表格」整理一次，易错概念立刻清晰。'
          : '核心概念需要再巩固一轮，建议逐题重看解析并在 1 小时内重闯一次。',
      '利用间隔重复：24h 后再重闯一次，次日正确率明显提升；一周后再刷一次，转长时记忆。',
    ],
    advice:
      '错题是进步的种子：每道错题做 3 件事 → ① 看解析后自己能讲出来；② 把易混点做一张对比表；③ 24h 后重闯这道题。坚持下来，正确率会肉眼可见地上升。',
    share_quote: `智能 AI 闯关：「${topicName}」我正确率 ${acc}%，学习像闯关一样认真！🐟`,
  }
}

export const mockQuestions = [...PYTHON_BANK, ...JAVA_BANK, ...JS_BANK, ...REACT_BANK, ...HTTP_BANK, ...GENERIC_BANK]

