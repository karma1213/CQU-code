#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内置汉字→拼音字表（无声调），供 search_widget 在未安装 pypinyin 时兜底使用。

格式：每项 "字:拼音"，多音字用 | 分隔（第一个为默认读音）。
词组表 PHRASES 用于修正常见多音字组合的读音。
安装 pypinyin 后（pip install pypinyin），本表自动被忽略。
"""

_RAW = """
一:yi 丁:ding 七:qi 万:wan 三:san 上:shang 下:xia 不:bu 与:yu 专:zhuan
且:qie 世:shi 业:ye 东:dong 丝:si 丢:diu 两:liang 严:yan 丨:gun 个:ge
中:zhong 丰:feng 临:lin 丹:dan 为:wei 主:zhu 丽:li 举:ju 么:me 义:yi
之:zhi 乌:wu 乐:le|yue 乘:cheng 九:jiu 也:ye 习:xi 乡:xiang 书:shu 买:mai
了:le|liao 予:yu 争:zheng 事:shi 二:er 于:yu 云:yun 五:wu 亚:ya 些:xie
亡:wang 交:jiao 产:chan 享:xiang 京:jing 亲:qin 人:ren 亿:yi 什:shen|shi 仅:jin
今:jin 介:jie 仍:reng 从:cong 仓:cang 他:ta 付:fu 代:dai 令:ling 以:yi
们:men 仲:zhong 件:jian 价:jia 任:ren 份:fen 企:qi 伊:yi 伐:fa 休:xiu
众:zhong 优:you 伙:huo 会:hui|kuai 伟:wei 传:chuan|zhuan 伤:shang 伦:lun 估:gu 但:dan
位:wei 低:di 住:zhu 体:ti 何:he 余:yu 作:zuo 你:ni 佩:pei 佳:jia
使:shi 例:li 供:gong 依:yi 侦:zhen 侧:ce 侵:qin 便:bian|pian 促:cu 俄:e
俗:su 保:bao 信:xin 修:xiu 倍:bei 倒:dao 倡:chang 值:zhi 假:jia 做:zuo
停:ting 偷:tou 偿:chang 像:xiang 儿:er 元:yuan 充:chong 先:xian 光:guang 克:ke
免:mian 兑:dui 党:dang 入:ru 全:quan 八:ba 公:gong 六:liu 兰:lan 共:gong
关:guan 兴:xing 兵:bing 其:qi 具:ju 典:dian 养:yang 兼:jian 内:nei 再:zai
冒:mao 写:xie 军:jun 农:nong 冬:dong 冲:chong 决:jue 况:kuang 冷:leng 准:zhun
凉:liang 凌:ling 减:jian 凝:ning 凡:fan 出:chu 击:ji 分:fen 切:qie 划:hua
列:lie 刘:liu 则:ze 创:chuang 初:chu 判:pan 利:li 别:bie 到:dao 制:zhi
刷:shua 刻:ke 剁:duo 前:qian 剧:ju 剩:sheng 副:fu 力:li 办:ban 功:gong
加:jia 务:wu 动:dong 助:zhu 努:nu 劳:lao 势:shi 勒:le 勤:qin 勿:wu
匀:yun 包:bao 匈:xiong 化:hua 北:bei 区:qu 医:yi 十:shi 千:qian 升:sheng
午:wu 半:ban 华:hua 协:xie 单:dan|shan 南:nan 博:bo 卡:ka 卢:lu 印:yin
危:wei 即:ji 卷:juan 卿:qing 厅:ting 历:li 压:ya 厚:hou 原:yuan 厦:sha|xia
去:qu 县:xian 参:can|shen 又:you 及:ji 友:you 双:shuang 反:fan 发:fa 取:qu
受:shou 变:bian 叠:die 口:kou 古:gu 召:zhao 可:ke 台:tai 史:shi 右:you
叶:ye 号:hao 司:si 各:ge 合:he 同:tong 名:ming 后:hou 向:xiang 吕:lv
吗:ma 吨:dun 启:qi 吴:wu 吸:xi 告:gao 员:yuan 周:zhou 味:wei 呼:hu
命:ming 和:he 咬:yao 品:pin 哈:ha 响:xiang 哪:na 售:shou 唱:chang 商:shang
喀:ka 善:shan 喜:xi 嘉:jia 嘛:ma 器:qi 四:si 回:hui 因:yin 团:tuan
园:yuan 困:kun 围:wei 国:guo 图:tu 圆:yuan 圈:quan 土:tu 在:zai 圭:gui
地:di|de 圳:zhen 场:chang 址:zhi 均:jun 坏:huai 块:kuai 坚:jian 坛:tan 坝:ba
坡:po 坦:tan 坪:ping 垂:chui 垄:long 型:xing 城:cheng 域:yu 培:pei 基:ji
堂:tang 堆:dui 堡:bao 塑:su 塔:ta 塞:sai|se 塬:yuan 境:jing 墙:qiang 增:zeng
墨:mo 士:shi 声:sheng 处:chu 备:bei 复:fu 夏:xia 外:wai 多:duo 夜:ye
大:da 天:tian 太:tai 夫:fu 央:yang 失:shi 头:tou 奇:qi 奉:feng 奋:fen
奔:ben 奖:jiang 套:tao 奚:xi 女:nv 好:hao 如:ru 妈:ma 妻:qi 姆:mu
始:shi 姓:xing 委:wei 姝:shu 威:wei 娟:juan 婉:wan 婵:chan 媒:mei 嫌:xian
嫩:nen 子:zi 孔:kong 字:zi 存:cun 孙:sun 季:ji 学:xue 孩:hai 宁:ning
守:shou 安:an 完:wan 宕:dang 宗:zong 官:guan 定:ding 宝:bao 实:shi 审:shen
客:ke 宣:xuan 室:shi 害:hai 家:jia 容:rong 宾:bin 寄:ji 密:mi 富:fu
寒:han 察:cha 寨:zhai 对:dui 导:dao 封:feng 射:she 将:jiang 尊:zun 小:xiao
少:shao 尔:er 就:jiu 尼:ni 尽:jin 尾:wei 局:ju 层:ceng 居:ju 届:jie
屋:wu 屏:ping 展:zhan 属:shu 山:shan 岗:gang 岸:an 峡:xia 川:chuan 州:zhou
巡:xun 工:gong 左:zuo 巧:qiao 巨:ju 己:ji 已:yi 巴:ba 市:shi 布:bu
帆:fan 师:shi 带:dai 席:xi 常:chang 幅:fu 幕:mu 干:gan 平:ping 年:nian
并:bing 广:guang 庄:zhuang 庆:qing 应:ying 底:di 店:dian 府:fu 废:fei 度:du
庭:ting 康:kang 延:yan 廷:ting 建:jian 开:kai 弃:qi 弊:bi 式:shi 引:yin
张:zhang 弱:ruo 弹:dan|tan 强:qiang 归:gui 当:dang 录:lu 形:xing 彬:bin 彰:zhang
影:ying 彼:bi 往:wang 征:zheng 待:dai 很:hen 律:lv 得:de|dei 微:wei 徵:zhi
德:de 徽:hui 心:xin 忆:yi 志:zhi 忠:zhong 快:kuai 念:nian 忻:xin 态:tai
思:si 怡:yi 急:ji 性:xing 总:zong 恢:hui 恩:en 息:xi 恶:e|wu 悉:xi
患:huan 情:qing 惠:hui 想:xiang 意:yi 感:gan 愿:yuan 慧:hui 懂:dong 戈:ge
戏:xi 成:cheng 我:wo 或:huo 战:zhan 户:hu 房:fang 所:suo 手:shou 才:cai
扎:zha 打:da 托:tuo 执:zhi 扬:yang 批:pi 承:cheng 技:ji 把:ba 抓:zhua
抗:kang 护:hu 报:bao 抵:di 押:ya 担:dan 拉:la 拒:ju 拔:ba 招:zhao
择:ze 括:kuo 拿:na 持:chi 挂:gua 指:zhi 按:an 挑:tiao 挚:zhi 挝:wo
挥:hui 振:zhen 挺:ting 损:sun 换:huan 捣:dao 捧:peng 据:ju 捷:jie 掉:diao
排:pai 探:tan 接:jie 控:kong 推:tui 措:cuo 提:ti 握:wo 揭:jie 援:yuan
搜:sou 搭:da 携:xie 摄:she 撑:cheng 撒:sa 撤:che 播:bo 撼:han 操:cao
支:zhi 收:shou 改:gai 攻:gong 放:fang 政:zheng 效:xiao 教:jiao 敬:jing 数:shu
整:zheng 文:wen 斗:dou 料:liao 斤:jin 斥:chi 断:duan 斯:si 新:xin 方:fang
施:shi 旅:lv 族:zu 无:wu 日:ri 旨:zhi 旭:xu 旱:han 时:shi 旺:wang
昆:kun 明:ming 昔:xi 星:xing 映:ying 春:chun 是:shi 显:xian 晋:jin 晨:chen
普:pu 景:jing 晶:jing 智:zhi 暂:zan 暖:nuan 暨:ji 暴:bao 曲:qu 更:geng
曼:man 曾:zeng|ceng 最:zui 月:yue 有:you 朋:peng 服:fu 朗:lang 望:wang 朝:chao|zhao
期:qi 木:mu 未:wei 末:mo 本:ben 术:shu 朱:zhu 朴:pu 机:ji 杂:za
权:quan 李:li 材:cai 村:cun 束:shu 条:tiao 来:lai 杨:yang 杯:bei 杰:jie
松:song 构:gou 林:lin 果:guo 枝:zhi 架:jia 染:ran 查:cha 标:biao 树:shu
校:xiao|jiao 样:yang 核:he 根:gen 格:ge 桂:gui 案:an 桌:zhuo 桥:qiao 梁:liang
梅:mei 梦:meng 梧:wu 梭:suo 检:jian 森:sen 植:zhi 楼:lou 榴:liu 模:mo|mu
次:ci 欧:ou 款:kuan 歉:qian 止:zhi 正:zheng 此:ci 步:bu 武:wu 死:si
殊:shu 殖:zhi 段:duan 毁:hui 母:mu 每:mei 比:bi 毕:bi 毛:mao 民:min
气:qi 水:shui 永:yong 求:qiu 汇:hui 汉:han 江:jiang 污:wu 汽:qi 沙:sha
沟:gou 没:mei|mo 沪:hu 河:he 油:you 治:zhi 沿:yan 泊:bo|po 法:fa 波:bo
注:zhu 泷:long 洁:jie 洋:yang 洛:luo 洲:zhou 活:huo 派:pai 流:liu 济:ji
浓:nong 浙:zhe 浦:pu 浪:lang 浮:fu 海:hai 浸:jin 消:xiao 涉:she 涌:yong
涎:xian 润:run 涨:zhang 深:shen 混:hun 清:qing 渐:jian 渔:yu 港:gang 游:you
湖:hu 湛:zhan 源:yuan 溢:yi 滑:hua 满:man 演:yan 漠:mo 漫:man 潜:qian
潭:tan 潮:chao 火:huo 灯:deng 灸:jiu 灾:zai 炬:ju 炸:zha 点:dian 热:re
焦:jiao 然:ran 煜:yu 照:zhao 熊:xiong 熔:rong 燃:ran 爆:bao 爱:ai 爸:ba
爽:shuang 片:pian 版:ban 牙:ya 牛:niu 牡:mu 牢:lao 物:wu 特:te 犯:fan
状:zhuang 狄:di 狠:hen 独:du 猛:meng 献:xian 率:lv|shuai 玉:yu 王:wang 玩:wan
环:huan 现:xian 玲:ling 玻:bo 珍:zhen 班:ban 球:qiu 理:li 琪:qi 琳:lin
琴:qin 琵:pi 琶:pa 瑞:rui 瑶:yao 璃:li 璐:lu 生:sheng 用:yong 田:tian
由:you 申:shen 电:dian 画:hua 界:jie 畔:pan 略:lve 疆:jiang 疗:liao 病:bing
登:deng 百:bai 的:de|di 皮:pi 益:yi 盐:yan 监:jian 盖:gai 盗:dao 盘:pan
盛:sheng 盟:meng 目:mu 直:zhi 相:xiang 盾:dun 省:sheng|xing 看:kan 真:zhen 眼:yan
着:zhe|zhao|zhuo 睛:jing 督:du 瞩:zhu 瞬:shun 知:zhi 短:duan 石:shi 矿:kuang 码:ma
研:yan 破:po 砻:long 础:chu 硕:shuo 确:que 碑:bei 碳:tan 示:shi 社:she
神:shen 票:piao 禁:jin 福:fu 离:li 秀:xiu 种:zhong 科:ke 秒:miao 秘:mi
租:zu 积:ji 称:cheng 稀:xi 程:cheng 税:shui 稳:wen 稻:dao 究:jiu 空:kong
穿:chuan 突:tu 窃:qie 窄:zhai 窑:yao 窗:chuang 立:li 站:zhan 竞:jing 竟:jing
童:tong 端:duan 笔:bi 第:di 等:deng 筑:zhu 答:da 策:ce 签:qian 简:jian
管:guan 箱:xiang 篇:pian 籍:ji 米:mi 类:lei 籽:zi 粉:fen 粒:li 粤:yue
精:jing 系:xi|ji 素:su 索:suo 紧:jin 紫:zi 累:lei 繁:fan 纠:jiu 红:hong
约:yue 级:ji 纪:ji 纬:wei 纳:na 纷:fen 纸:zhi 线:xian 组:zu 细:xi
织:zhi 绍:shao 经:jing 绑:bang 结:jie 绕:rao 绘:hui 给:gei|ji 络:luo 绝:jue
统:tong 绩:ji 续:xu 维:wei 综:zong 绿:lv 缀:zhui 缓:huan 编:bian 缘:yuan
缴:jiao 缺:que 网:wang 罕:han 罗:luo 罚:fa 罪:zui 署:shu 美:mei 群:qun
翠:cui 翡:fei 翰:han 老:lao 考:kao 者:zhe 耕:geng 耘:yun 耶:ye 职:zhi
联:lian 聘:pin 聚:ju 肄:yi 股:gu 育:yu 胀:zhang 胜:sheng 能:neng 脆:cui
脚:jiao 脱:tuo 腐:fu 腔:qiang 腹:fu 自:zi 至:zhi 致:zhi 舅:jiu 航:hang
舰:jian 船:chuan 艘:sou 良:liang 色:se 艺:yi 节:jie 芒:mang 芦:lu 芬:fen
芯:xin 花:hua 芳:fang 苏:su 苑:yuan 苗:miao 英:ying 茂:mao 范:fan 茶:cha
茹:ru 荐:jian 荒:huang 荣:rong 药:yao 莫:mo 莱:lai 莲:lian 获:huo 菜:cai
菲:fei 营:ying 落:luo 董:dong 葱:cong 蓄:xu 蓝:lan 蔚:wei 薄:bao|bo 薛:xue
薪:xin 藏:cang|zang 虎:hu 虽:sui 蝶:die 融:rong 血:xue|xie 行:xing|hang 补:bu 表:biao
袖:xiu 被:bei 袭:xi 裁:cai 裂:lie 装:zhuang 西:xi 要:yao 覆:fu 见:jian|xian
观:guan 规:gui 视:shi 览:lan 角:jiao|jue 解:jie 言:yan 詹:zhan 警:jing 计:ji
订:ding 认:ren 讨:tao 让:rang 训:xun 议:yi 讯:xun 记:ji 讲:jiang 许:xu
论:lun 设:she 访:fang 证:zheng 评:ping 识:shi 诈:zha 诉:su 词:ci 试:shi
诗:shi 该:gai 语:yu 说:shuo 诵:song 请:qing 读:du 课:ke 调:diao|tiao 谈:tan
谋:mou 谍:die 谐:xie 谢:xie 谦:qian 谭:tan 谱:pu 谶:chen 谷:gu 豆:dou
贝:bei 负:fu 贡:gong 财:cai 责:ze 败:bai 货:huo 质:zhi 购:gou 贵:gui
贸:mao 费:fei 贾:jia 资:zi 赔:pei 赛:sai 赢:ying 赫:he 走:zou 赴:fu
起:qi 超:chao 越:yue 趋:qu 足:zu 距:ju 跟:gen 跨:kua 路:lu 践:jian
踪:zong 身:shen 车:che 转:zhuan 轮:lun 轻:qing 载:zai 较:jiao 辆:liang 辉:hui
辑:ji 输:shu 辛:xin 辩:bian 边:bian 达:da 迅:xun 过:guo 迎:ying 运:yun
近:jin 返:fan 这:zhe 进:jin 远:yuan 违:wei 连:lian 迪:di 迭:die 述:shu
追:zhui 退:tui 送:song 逃:tao 选:xuan 透:tou 逐:zhu 递:di 途:tu 通:tong
速:su 造:zao 逻:luo 遇:yu 遍:bian 道:dao 遭:zao 遴:lin 避:bi 邀:yao
邑:yi 邓:deng 那:na 邦:bang 邮:you 邹:zou 郁:yu 郊:jiao 郑:zheng 部:bu
郭:guo 都:dou|du 采:cai 里:li 重:zhong|chong 野:ye 量:liang 金:jin 针:zhen 钍:tu
钢:gang 钱:qian 铁:tie 银:yin 铺:pu 锋:feng 错:cuo 锡:xi 键:jian 锻:duan
镇:zhen 镜:jing 镱:yi 长:chang|zhang 门:men 闫:yan 闭:bi 问:wen 间:jian 闻:wen
队:dui 阮:ruan 防:fang 阳:yang 阶:jie 阿:a|e 附:fu 际:ji 陈:chen 降:jiang|xiang
限:xian 院:yuan 除:chu 险:xian 随:sui 隔:ge 障:zhang 难:nan 雄:xiong 雅:ya
集:ji 雨:yu 零:ling 雷:lei 需:xu 震:zhen 霸:ba 青:qing 静:jing 非:fei
靠:kao 面:mian 革:ge 韧:ren 韩:han 项:xiang 顺:shun 须:xu 顾:gu 颁:ban
预:yu 领:ling 频:pin 颗:ke 题:ti 额:e 颠:dian 风:feng 飘:piao 飞:fei
食:shi 餐:can 饱:bao 馆:guan 馈:kui 馒:man 首:shou 香:xiang 马:ma 驳:bo
驻:zhu 验:yan 骗:pian 高:gao 魔:mo 鱼:yu 鲁:lu 鲈:lu 鲜:xian 鲤:li
鳅:qiu 鳞:lin 鸭:ya 鹏:peng 麦:mai 黄:huang 黎:li 黑:hei 黔:qian 齐:qi
龄:ling 龙:long
"""

# 常见多音字词组修正（无声调读音，按词优先于按字）
PHRASES = {
    "重庆": ["chong", "qing"],
    "重大": ["zhong", "da"],
    "重要": ["zhong", "yao"],
    "重点": ["zhong", "dian"],
    "重申": ["zhong", "shen"],
    "重新": ["chong", "xin"],
    "重复": ["chong", "fu"],
    "银行": ["yin", "hang"],
    "行业": ["hang", "ye"],
    "行长": ["hang", "zhang"],
    "发行": ["fa", "xing"],
    "校长": ["xiao", "zhang"],
    "院长": ["yuan", "zhang"],
    "部长": ["bu", "zhang"],
    "增长": ["zeng", "zhang"],
    "成长": ["cheng", "zhang"],
    "长江": ["chang", "jiang"],
    "长期": ["chang", "qi"],
    "长效": ["chang", "xiao"],
    "长沙": ["chang", "sha"],
    "会计": ["kuai", "ji"],
    "音乐": ["yin", "yue"],
    "乐团": ["yue", "tuan"],
    "乐器": ["yue", "qi"],
    "首都": ["shou", "du"],
    "都市": ["du", "shi"],
    "成都": ["cheng", "du"],
    "传统": ["chuan", "tong"],
    "传播": ["chuan", "bo"],
    "传承": ["chuan", "cheng"],
    "宣传": ["xuan", "chuan"],
    "传记": ["zhuan", "ji"],
    "西藏": ["xi", "zang"],
    "藏族": ["zang", "zu"],
    "调查": ["diao", "cha"],
    "调研": ["diao", "yan"],
    "调整": ["tiao", "zheng"],
    "调节": ["tiao", "jie"],
    "空调": ["kong", "tiao"],
    "参加": ["can", "jia"],
    "参与": ["can", "yu"],
    "参考": ["can", "kao"],
    "参赛": ["can", "sai"],
    "参评": ["can", "ping"],
    "人参": ["ren", "shen"],
    "方便": ["fang", "bian"],
    "便宜": ["pian", "yi"],
    "血液": ["xue", "ye"],
    "献血": ["xian", "xue"],
    "得到": ["de", "dao"],
    "获得": ["huo", "de"],
    "取得": ["qu", "de"],
    "目的": ["mu", "di"],
    "的确": ["di", "que"],
    "土地": ["tu", "di"],
    "地区": ["di", "qu"],
    "基地": ["ji", "di"],
    "厦门": ["xia", "men"],
    "大厦": ["da", "sha"],
    "朝鲜": ["chao", "xian"],
    "朝阳": ["chao", "yang"],
    "朝廷": ["chao", "ting"],
    "单位": ["dan", "wei"],
    "名单": ["ming", "dan"],
    "单元": ["dan", "yuan"],
    "什么": ["shen", "me"],
    "降低": ["jiang", "di"],
    "下降": ["xia", "jiang"],
    "降雨": ["jiang", "yu"],
    "投降": ["tou", "xiang"],
    "薄弱": ["bo", "ruo"],
    "淡薄": ["dan", "bo"],
    "系统": ["xi", "tong"],
    "关系": ["guan", "xi"],
    "联系": ["lian", "xi"],
    "系列": ["xi", "lie"],
    "角色": ["jue", "se"],
    "角度": ["jiao", "du"],
    "阿里": ["a", "li"],
    "弹性": ["tan", "xing"],
    "弹药": ["dan", "yao"],
    "导弹": ["dao", "dan"],
    "模型": ["mo", "xing"],
    "模式": ["mo", "shi"],
    "模样": ["mu", "yang"],
    "省份": ["sheng", "fen"],
    "节省": ["jie", "sheng"],
    "湖泊": ["hu", "po"],
    "停泊": ["ting", "bo"],
    "曾经": ["ceng", "jing"],
    "学校": ["xue", "xiao"],
    "校园": ["xiao", "yuan"],
    "校对": ["jiao", "dui"],
    "率先": ["shuai", "xian"],
    "比率": ["bi", "lv"],
    "效率": ["xiao", "lv"],
    "利率": ["li", "lv"],
    "汇率": ["hui", "lv"],
}


def _parse(raw):
    table = {}
    for pair in raw.split():
        char, _, readings = pair.partition(":")
        if char and readings:
            table[char] = readings.split("|")
    return table


TABLE = _parse(_RAW)
