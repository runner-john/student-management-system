<div align="center">

<img src="icon.svg" width="72" height="72" alt="logo">

# 学生管理信息系统 v3.0

**Student Management Information System**

基于 PyQt6 + SQLite + scikit-learn + DeepSeek 的智能教务管理桌面应用

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt-6.7+-green?logo=qt)](https://www.riverbankcomputing.com/software/pyqt/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3+-orange?logo=scikit-learn)](https://scikit-learn.org/)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-purple?logo=openai)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

---

## 📖 项目简介

一套功能完备的学生管理信息系统，采用 **MVC 分层架构**（数据访问层 → 业务逻辑层 → 界面表现层），集成了**本地机器学习**与**云端大模型 AI**，覆盖教务管理的全流程需求。

> 🏫 适用场景：高校教务管理 | 课程实验项目 | PyQt6 学习参考 | 桌面应用开发模板

---

## ✨ 功能矩阵

### 🔐 用户权限
- 管理员 / 教师双角色，MD5 加盐加密
- 前后端双重权限校验，越权防护
- Caps Lock 检测、密码显隐切换、登录失败抖动动画

### 👨‍🎓 学生管理
- CRUD 操作 + 批量 CSV/JSON 导入导出 + PDF 报表
- 学号/姓名/班级/专业四维度模糊组合搜索
- 分页（10/20/50/100 条/页）+ 页码跳转
- 右键上下文菜单：编辑、删除、复制、导出选中行、全选
- 实时输入校验（红色边框高亮 + 错误提示）

### 📊 成绩管理
- 学号/课程/班级/学期/分数区间多条件筛选
- 统计栏实时显示筛选后的平均分、最高分、最低分
- 学号关联校验（学生表中不存在则拒绝录入）
- CSV / JSON / PDF 多格式导出

### 📈 数据可视化
- 4 个 Tab 共 7 种图表组合
- 班级人数柱状图 + 专业人数饼图
- 成绩分数段柱状图 + 饼图（5 段分布）
- 学期平均分趋势样条曲线图
- 专业/班级/年级多维对比柱状图
- 支持按专业/班级/年级筛选联动
- 数据摘要卡片（学生总数、成绩数、平均分、及格率）

### 🤖 机器学习分析（scikit-learn）
| 功能 | 算法 | 说明 |
|------|------|------|
| 学生聚类 | K-Means + StandardScaler | 基于 6 维特征自动分组（优秀/良好/中等/需关注） |
| 成绩预测 | Linear Regression | 训练回归模型，输出 R² 置信度 |
| 课程相关性 | Pearson 相关系数 | 识别核心课程与关联课程群 |
| 异常检测 | Isolation Forest | 无监督学习识别成绩模式异常学生 |
| 综合排名 | 加权评分（0.6/0.3/0.1） | 百分位排名 + Top3 榜单 |

### 🧠 DeepSeek 大模型 AI
- **智能评语**：真实大模型生成，引用具体课程名和分数，语气自然温暖
- **深度学情报告**：五段式 300-500 字专业分析（概况→弱项→偏科→预警→建议）
- **智能降级**：API 不可用时自动切换本地模板引擎
- **API Key 管理**：本地加密存储，一键配置/清除

### 🛡️ 系统辅助
- 操作日志审计（全操作记录、多条件筛选、分页）
- 数据库一键备份 + 历史还原（二次确认防误操作）
- 系统概览仪表盘（统计卡片 + 快捷操作 + 最近日志 + 数据库状态）
- 个人中心密码修改 + 关于系统 + 退出确认
- 全局快捷键（Ctrl+N/F/E/Delete/F5/Q + Ctrl+1~7 切换页面）

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│                  UI 层 (PyQt6)                    │
│  登录 → 仪表盘 → 学生 → 成绩 → 图表 → AI → 用户/日志 │
├─────────────────────────────────────────────────┤
│               Service 层 (业务逻辑)                │
│  AuthService │ StudentService │ GradeService      │
│  校验 · 权限 · 日志 · 导入导出                      │
├─────────────────────────────────────────────────┤
│                DAO 层 (数据访问)                    │
│  UserDAO │ StudentDAO │ GradeDAO │ LogDAO         │
│  参数化 SQL · 分页 · WHERE 构建 · 统计聚合          │
├─────────────────────────────────────────────────┤
│            SQLite3 (WAL 模式 · 外键约束)            │
└─────────────────────────────────────────────────┘

AI 增强层: AIAnalyzer ──┬── scikit-learn (本地 ML)
                        └── DeepSeek API (云端 LLM)
```

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 基础运行环境 |
| PyQt6 | 6.7+ | GUI 框架 |
| PyQt6-Charts | 6.7+ | 图表组件（可选，未安装时显示提示） |
| scikit-learn | 1.3+ | 机器学习（可选，未安装时显示提示） |
| numpy | 1.26+ | 数值计算（scikit-learn 依赖） |
| DeepSeek API Key | — | AI 评语/分析（可选，未配置时降级为本地引擎） |

### 安装与运行

```bash
# 1. 克隆仓库
git clone https://github.com/runner-john/student-management-system.git
cd student-management-system

# 2. 安装依赖
pip install PyQt6 PyQt6-Charts scikit-learn numpy

# 3. 运行
python student_manage_system.py
```

### 内置测试账号

| 账号 | 密码 | 角色 |
|------|------|------|
| `admin` | `123456` | 管理员（全部权限） |
| `teacher` | `123456` | 教师（学生/成绩管理） |

---

## 🎨 设计原则

1. **分层解耦，单向依赖** — UI → Service → DAO → DB，下层对上无感知
2. **优雅降级，渐进增强** — 图表/ML/AI 模块均可选，核心 CRUD 始终可用
3. **单一职责，最小接口** — 每类只做一件事，对外暴露最小 API
4. **防御式编程，安全优先** — 参数化 SQL + 前后端双重权限 + 输入白名单校验
5. **DRY 原则与模式复用** — 分页/导出/右键菜单遵循统一模式
6. **数据驱动，真实为本** — 所有 AI 分析基于数据库真实数据

---

## 📁 项目结构

```
student-management-system/
├── student_manage_system.py        # 主程序（~6500 行）
├── generate_paper.py               # 论文生成辅助脚本
├── icon.svg / icon.ico             # 应用图标
├── .gitignore                      # Git 排除规则
├── README.md                       # 本文件
└── MQTT/                           # MQTT 辅助模块
```

---

## 🔧 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.10+ | 全部代码 |
| GUI | PyQt6 (Fusion 风格) | 桌面应用界面 |
| 数据库 | SQLite3 (WAL 模式) | 数据持久化 |
| 加密 | MD5 + 随机盐值 | 用户密码保护 |
| 图表 | PyQt6-Charts | 数据可视化 |
| ML | scikit-learn (KMeans / LinearRegression / IsolationForest) | 聚类/预测/异常检测 |
| AI | DeepSeek Chat API | 智能评语/深度报告 |
| 导出 | QPrinter / csv / json | PDF/CSV/JSON 导出 |
| 版本控制 | Git + GitHub | 代码管理 |

---

## 📝 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.0 | 2026.05 | 基础 CRUD + 登录 + 分页 |
| v2.0 | 2026.06 | 图表可视化 + 日志审计 + AI 规则引擎 |
| v3.0 | 2026.06 | scikit-learn ML + DeepSeek LLM + 界面优化 |

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)

---

<div align="center">

**Made with ❤️ by [runner-john](https://github.com/runner-john)**

</div>
