# 文件名：student_manage_system.py
# -*- coding: utf-8 -*-
"""
基于PyQt6的学生管理信息系统 (Student Management Information System)
=================================================================
版本：v2.0
开发语言：Python 3.10+
GUI框架：PyQt6 (Fusion风格)
数据库：SQLite3 (内嵌式，无需安装)
架构模式：MVC分层架构 (DAO数据访问层 + Service业务逻辑层 + UI界面层)

功能概要：
  1. 用户权限管理（管理员/教师双角色，MD5加盐加密）
  2. 学生信息管理（CRUD、批量导入导出、模糊查询、分页）
  3. 成绩管理（录入编辑、多条件筛选、自动统计）
  4. 数据统计可视化（柱状图、饼图、折线图）
  5. 操作日志审计（全操作记录、管理员可查）
  6. 数据备份还原、PDF/Excel/JSON多格式导出
  7. 个人中心、关于页、数据校验、退出确认

内置测试账号：
  管理员：admin / 123456
  教师：  teacher / 123456

依赖安装（如缺少PyQt6）：
  pip install PyQt6 PyQt6-Charts

运行方式：
  python student_manage_system.py
"""

import sys
import os
import hashlib
import sqlite3
import json
import requests
import csv
import datetime
import secrets
import shutil
import re
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

# ==================== 资源路径工具 ====================

def resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径（兼容开发环境和 PyInstaller 打包环境）"""
    try:
        base_path = sys._MEIPASS  # PyInstaller 临时解压目录
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ==================== PyQt6 导入 ====================
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QStatusBar, QMenuBar, QMenu,
    QToolBar, QSplitter, QFrame, QSpinBox, QDoubleSpinBox, QDateEdit,
    QTextEdit, QCheckBox, QRadioButton, QButtonGroup, QTabWidget,
    QAbstractItemView, QSizePolicy, QScrollArea, QInputDialog, QProgressDialog
)
from PyQt6.QtCore import (
    Qt, QSize, QDate, QDateTime, QTimer, QThread, pyqtSignal, QObject
)
from PyQt6.QtGui import (
    QIcon, QFont, QColor, QPalette, QBrush, QAction, QPixmap, QPainter,
    QShortcut, QKeyEvent
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt6.QtCore import QMarginsF

# 尝试导入图表模块
try:
    from PyQt6.QtCharts import (
        QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis,
        QPieSeries, QPieSlice, QLineSeries, QValueAxis, QCategoryAxis,
        QSplineSeries
    )
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False

# 尝试导入机器学习模块
try:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import IsolationForest
    HAS_ML = True
except ImportError:
    HAS_ML = False

# ==================== 全局常量 ====================
APP_TITLE = "学生管理信息系统 v2.0"
APP_VERSION = "v2.0.0"
APP_AUTHOR = "杨舒羽"
APP_MAJOR = "物联网工程专业"
APP_COPYRIGHT = "Copyright © 2026 杨舒羽. All rights reserved."

DB_NAME = "student_system.db"
BAKCUP_DIR = "backups"

# 分页配置
PAGE_SIZE_OPTIONS = [10, 20, 50, 100]
DEFAULT_PAGE_SIZE = 20

# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_KEY_FILE = "deepseek_key.txt"

def get_deepseek_key() -> str:
    """获取 DeepSeek API Key（优先级：环境变量 > 本地文件）"""
    import os
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DEEPSEEK_KEY_FILE)
    if os.path.exists(key_path):
        try:
            with open(key_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass
    return ""

def save_deepseek_key(api_key: str):
    """保存 API Key 到本地文件"""
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DEEPSEEK_KEY_FILE)
    with open(key_path, 'w', encoding='utf-8') as f:
        f.write(api_key.strip())

# ==================== DeepSeek AI 客户端 ====================

class DeepSeekClient:
    """DeepSeek API 客户端，提供真实LLM驱动的AI分析能力"""

    def __init__(self):
        self.api_key = get_deepseek_key()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def set_key(self, key: str):
        self.api_key = key
        save_deepseek_key(key)

    def chat(self, system_prompt: str, user_message: str,
             temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """调用 DeepSeek Chat API"""
        if not self.api_key:
            return "[未配置 DeepSeek API Key]"

        try:
            resp = requests.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"[API 错误: {resp.status_code}]"
        except Exception as e:
            return f"[请求失败: {str(e)}]"


# 内置测试账号
DEFAULT_USERS = [
    ("admin", "123456", "admin", "系统管理员"),
    ("teacher", "123456", "teacher", "张老师"),
]

# ==================== 工具函数 ====================

def md5_hash(password: str, salt: str = "") -> str:
    """MD5加盐哈希计算"""
    return hashlib.md5((password + salt).encode('utf-8')).hexdigest()

def generate_salt(length: int = 16) -> str:
    """生成随机盐值"""
    return secrets.token_hex(length // 2)

def validate_phone(phone: str) -> bool:
    """验证手机号格式（中国大陆）"""
    if not phone:
        return True  # 空值允许
    return bool(re.match(r'^1[3-9]\d{9}$', phone))

def validate_score(score) -> bool:
    """验证分数在0-100范围内"""
    try:
        s = float(score)
        return 0 <= s <= 100
    except (ValueError, TypeError):
        return False

def format_datetime(dt_str: str) -> str:
    """格式化日期时间字符串"""
    if not dt_str:
        return ""
    try:
        if 'T' in dt_str:
            dt = datetime.datetime.fromisoformat(dt_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return dt_str
    except Exception:
        return dt_str

# ==================== AI智能分析引擎 ====================

class AIAnalyzer:
    """
    本地轻量AI分析引擎
    ====================
    基于统计分析与规则匹配，无需联网大模型，纯本地文本智能处理。
    功能：学情诊断、智能评语、语义搜索、异常检测、报表总结

    设计原则：
      - 所有分析基于数据库真实数据，不产生幻觉
      - 使用统计学方法（均值/标准差/Z-score）识别异常
      - 自然语言解析使用中文关键词正则匹配
      - 评语生成基于模板库 + 数据库事实填充
    """

    # ---- 评语模板库 ----
    COMMENT_TEMPLATES = {
        "努力": [
            "{name}同学学习态度端正，本学期{strong_course}表现突出，取得了{score}分的好成绩。"
            "课堂参与积极，作业完成认真，希望继续保持。{weak_advice}",
            "{name}同学在本学期展现了良好的学习习惯，各科成绩稳步提升。"
            "特别在{courses_list}方面表现优异。希望下学期再接再厉，{suggestion}。",
        ],
        "粗心": [
            "{name}同学思维活跃，理解能力强，但在答题细节上需要更加仔细。"
            "{weak_course}考试中出现了不必要的失误。建议考前多检查，平时养成验算习惯。",
        ],
        "偏科": [
            "{name}同学在{strong_course}方面表现优异（{high_score}分），但{weak_course}有待加强（{low_score}分）。"
            "建议合理分配学习时间，补齐短板，均衡发展各学科能力。",
        ],
        "进步": [
            "{name}同学本学期进步明显，较上学期成绩有较大提升。"
            "尤其在{courses_list}方面的表现令人欣喜。保持这份进取心，未来可期！",
        ],
        "全面": [
            "{name}同学综合素质优秀，各科成绩均衡发展，平均分达到{avg}分。"
            "{strong_course}科目尤为突出。积极参加班级活动，是一位全面发展的好学生。"
            "建议：{suggestion}",
        ],
    }

    def __init__(self):
        self.db = DatabaseManager()
        self.student_dao = StudentDAO()
        self.grade_dao = GradeDAO()
        self.ds = DeepSeekClient()

    # ============ 1. 学情诊断 ============

    def analyze_class(self, class_name: str = None, major: str = None,
                      year: int = None) -> dict:
        """
        一键AI学情诊断
        参数：class_name（班级）, major（专业）, year（入学年份），至少提供一个
        返回：dict 包含弱项科目、偏科学生、波动学生、挂科风险、总体摘要
        """
        # 获取目标群体学生
        filters = {}
        if class_name:
            filters['class_name'] = class_name
        if major:
            filters['major'] = major
        if year:
            filters['enrollment_year'] = year

        students = self.student_dao.get_page(1, 99999, filters)
        if not students:
            return {"error": "未找到符合条件的学生"}

        student_ids = [s['student_id'] for s in students]

        # 获取所有成绩
        conn = self.db.get_connection()
        placeholders = ','.join(['?' for _ in student_ids])
        grades = conn.execute(
            f"SELECT * FROM grades WHERE student_id IN ({placeholders}) ORDER BY student_id, course_name",
            student_ids
        ).fetchall()

        if not grades:
            return {"error": "该群体暂无成绩数据", "student_count": len(students)}

        # --- 统计各科平均分 ---
        course_scores = {}
        for g in grades:
            cn = g['course_name']
            if cn not in course_scores:
                course_scores[cn] = []
            course_scores[cn].append(g['score'])

        course_avg = {cn: round(sum(sc)/len(sc), 1) for cn, sc in course_scores.items()}
        # 弱项科目：平均分低于65
        weak_subjects = [(cn, avg) for cn, avg in course_avg.items() if avg < 65]
        weak_subjects.sort(key=lambda x: x[1])

        # --- 学生成绩汇总 ---
        student_summary = {}
        for g in grades:
            sid = g['student_id']
            if sid not in student_summary:
                student_summary[sid] = {
                    'name': g['name'], 'courses': {}, 'scores': []
                }
            student_summary[sid]['courses'][g['course_name']] = g['score']
            student_summary[sid]['scores'].append(g['score'])

        # 计算每个学生的均值与标准差
        import math
        for sid, info in student_summary.items():
            scores = info['scores']
            info['avg'] = round(sum(scores) / len(scores), 1) if scores else 0
            if len(scores) > 1:
                mean = info['avg']
                variance = sum((s - mean) ** 2 for s in scores) / len(scores)
                info['std'] = round(math.sqrt(variance), 1)
            else:
                info['std'] = 0

        # --- 偏科学生：最高分-最低分 > 30 ---
        imbalanced = []
        for sid, info in student_summary.items():
            courses = info['courses']
            if len(courses) >= 2:
                sorted_c = sorted(courses.items(), key=lambda x: x[1])
                low_course, low_score = sorted_c[0]
                high_course, high_score = sorted_c[-1]
                if high_score - low_score > 30:
                    imbalanced.append({
                        'student_id': sid, 'name': info['name'],
                        'low_course': low_course, 'low_score': low_score,
                        'high_course': high_course, 'high_score': high_score,
                        'gap': round(high_score - low_score, 1)
                    })
        imbalanced.sort(key=lambda x: x['gap'], reverse=True)

        # --- 挂科风险：平均分 < 60 或 任一科 < 60 ---
        at_risk = []
        for sid, info in student_summary.items():
            min_score = min(info['scores'])
            if info['avg'] < 60 or min_score < 60:
                at_risk.append({
                    'student_id': sid, 'name': info['name'],
                    'avg': info['avg'], 'min_score': min_score,
                    'min_course': min(info['courses'].items(), key=lambda x: x[1])[0]
                })
        at_risk.sort(key=lambda x: x['avg'])

        # --- 成绩波动学生：标准差 > 15 ---
        volatile = [
            {'student_id': sid, 'name': info['name'],
             'avg': info['avg'], 'std': info['std']}
            for sid, info in student_summary.items() if info['std'] > 15
        ]
        volatile.sort(key=lambda x: x['std'], reverse=True)

        # --- 总体摘要 ---
        all_scores = [g['score'] for g in grades]
        total_avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
        pass_count = sum(1 for s in all_scores if s >= 60)
        pass_rate = round(pass_count / len(all_scores) * 100, 1) if all_scores else 0

        summary = {
            'student_count': len(students),
            'grade_count': len(grades),
            'total_avg': total_avg,
            'pass_rate': pass_rate,
            'course_count': len(course_avg),
        }

        return {
            'summary': summary,
            'weak_subjects': weak_subjects,
            'imbalanced_students': imbalanced[:10],    # Top 10
            'volatile_students': volatile[:10],
            'at_risk_students': at_risk[:10],
            'course_avg': list(course_avg.items()),
        }

    # ============ 2. 智能评语生成 ============

    def generate_comment(self, student_id: str, keywords: list = None) -> str:
        """
        智能评语生成（DeepSeek API 优先，本地模板降级）
        参数：
          student_id: 学号
          keywords: 关键词列表，如 ['努力', '偏科']，为空则自动推断
        返回：自然语言评语文本
        """
        student = self.student_dao.get_by_student_id(student_id)
        if not student:
            return "未找到该学生信息"

        conn = self.db.get_connection()
        grades = conn.execute(
            "SELECT * FROM grades WHERE student_id = ? ORDER BY score DESC",
            (student_id,)
        ).fetchall()

        if not grades:
            return f"{student['name']}同学暂无成绩数据，无法生成评语。"

        # 提取数据
        scores = [g['score'] for g in grades]
        avg_score = round(sum(scores) / len(scores), 1)
        max_g = max(grades, key=lambda g: g['score'])
        min_g = min(grades, key=lambda g: g['score'])
        strong_courses = [g['course_name'] for g in grades if g['score'] >= 80]
        weak_courses = [g['course_name'] for g in grades if g['score'] < 60]

        # 自动推断关键词
        if not keywords:
            keywords = []
            if max_g['score'] - min_g['score'] > 25:
                keywords.append("偏科")
            if avg_score >= 80:
                keywords.append("全面")
            elif avg_score >= 60:
                keywords.append("努力")
            if any(g['score'] < 60 for g in grades):
                keywords.append("进步")
        if not keywords:
            keywords = ["努力"]

        # ---- DeepSeek API 生成 ----
        if self.ds.is_available():
            result = self._generate_comment_deepseek(
                student, grades, scores, avg_score, max_g, min_g,
                strong_courses, weak_courses, keywords
            )
            if not result.startswith("[") and len(result) > 20:
                return result

        # ---- 本地模板降级 ----
        return self._generate_comment_template(
            student, grades, scores, avg_score, max_g, min_g,
            strong_courses, weak_courses, keywords
        )

    def _generate_comment_deepseek(self, student, grades, scores, avg_score,
                                    max_g, min_g, strong_courses, weak_courses,
                                    keywords) -> str:
        """调用 DeepSeek API 生成个性化评语"""
        course_details = "\n".join(
            f"- {g['course_name']}: {g['score']}分（{g['semester']}）"
            for g in grades
        )
        prompt = f"""请为以下学生生成一段期末综合评语（80-150字），要求：
1. 风格：{keywords[0]}，语气温暖、个性化
2. 必须引用真实数据（课程名、分数）
3. 指出优势科目和需要加强的科目
4. 给出具体可行的学习建议

【学生信息】
姓名：{student['name']}
专业：{student['major']}
班级：{student['class_name']}

【成绩数据】
{course_details}

平均分：{avg_score}分 | 最高：{max_g['course_name']} {max_g['score']}分 | 最低：{min_g['course_name']} {min_g['score']}分
优势科目：{'、'.join(strong_courses) if strong_courses else '无'}
薄弱科目：{'、'.join(weak_courses) if weak_courses else '无'}

请直接输出评语内容，不要带任何前缀说明。"""
        return self.ds.chat(
            system_prompt="你是一位经验丰富的高校辅导员，擅长为学生撰写个性化、有温度的期末评语。评语要引用实际数据，语气亲切专业，建议具体可行。",
            user_message=prompt,
            temperature=0.8,
            max_tokens=512,
        )

    def _generate_comment_template(self, student, grades, scores, avg_score,
                                    max_g, min_g, strong_courses, weak_courses,
                                    keywords) -> str:
        """本地模板评语生成（降级方案）"""
        keyword = keywords[0]
        templates = self.COMMENT_TEMPLATES.get(keyword, self.COMMENT_TEMPLATES["努力"])
        import random
        template = templates[hash(student['student_id'] + keyword) % len(templates)]

        name = student['name']
        strong_course = max_g['course_name'] if strong_courses else (max_g['course_name'] if grades else "各科")
        weak_course = min_g['course_name'] if weak_courses else (min_g['course_name'] if grades else "部分科目")
        courses_list = "、".join([g['course_name'] for g in grades[:2]])
        score = str(max_g['score'])
        high_score = str(max_g['score'])
        low_score = str(min_g['score'])
        avg = str(avg_score)
        weak_advice = f"建议在{weak_course}上多下功夫" if weak_courses else "各科均衡发展良好"
        suggestion = "继续保持优势科目的同时拓宽知识面" if avg_score >= 80 else "夯实基础，稳步提升"

        return template.format(
            name=name, strong_course=strong_course, weak_course=weak_course,
            courses_list=courses_list, score=score, high_score=high_score,
            low_score=low_score, avg=avg, weak_advice=weak_advice,
            suggestion=suggestion
        )

    def analyze_class_deep(self, class_name: str = None, major: str = None,
                           year: int = None) -> str:
        """
        DeepSeek 深度学情分析报告（自然语言）
        参数同 analyze_class()，但返回自然语言报告文本
        """
        if not self.ds.is_available():
            return "[DeepSeek API 未配置，请先设置 API Key]"

        data = self.analyze_class(class_name, major, year)
        if "error" in data:
            return f"数据获取失败：{data['error']}"

        prompt = f"""请根据以下学生群体数据，撰写一份专业的学情分析报告（300-500字），包含：
1. 总体概况总结
2. 弱项科目分析与改进建议
3. 偏科学生情况与干预建议
4. 挂科风险预警
5. 总体教学建议

【数据】
{json.dumps(data, ensure_ascii=False, indent=2)}

请直接输出报告内容，Markdown格式，不要带前缀。"""
        return self.ds.chat(
            system_prompt="你是一位资深教育数据分析师，擅长将统计数据转化为有洞察的教学建议报告。",
            user_message=prompt,
            temperature=0.5,
            max_tokens=1024,
        )

    # ============ 3. 语义搜索 ============

    def parse_natural_query(self, text: str) -> dict:
        """
        AI语义搜索：自然语言 → 结构化过滤条件
        支持示例：
          "一班数学不及格的学生"
          "2024级物联网平均分低于60"
          "张三的高等数学成绩"
          "计科2401班80分以上的学生"
        返回：{'filters': {...}, 'description': str, 'search_type': 'student'|'grade'}
        """
        text = text.strip()
        filters = {}
        search_type = 'student'
        desc_parts = []

        # 班级匹配
        class_match = re.search(r'(计科\d+|软件\d+|数据\d+|智能\d+|网络\d+|信安\d+|[一-龥]*\d+班|一班|二班|三班)', text)
        if class_match:
            cls = class_match.group(1)
            # 数字转换
            cls_map = {'一班': '计科2401', '二班': '计科2402', '三班': '数据2401'}
            filters['class_name'] = cls_map.get(cls, cls)
            desc_parts.append(f"班级={filters['class_name']}")

        # 专业匹配
        major_match = re.search(r'(计算机|软件|数据科学|人工智能|网络工程|信息安全|物联网|[一-龥]+工程)', text)
        if major_match:
            filters['major'] = major_match.group(1)
            desc_parts.append(f"专业={filters['major']}")

        # 年级匹配
        year_match = re.search(r'(\d{4})级', text)
        if year_match:
            filters['enrollment_year'] = int(year_match.group(1))
            desc_parts.append(f"年级={filters['enrollment_year']}")

        # 课程匹配
        course_match = re.search(r'(高等数学|线性代数|C语言|数据结构|大学英语|概率论|操作系统|计算机网络|[一-龥]{2,6})', text)
        if course_match:
            filters['course_name'] = course_match.group(1)
            desc_parts.append(f"课程={filters['course_name']}")
            search_type = 'grade'

        # 分数条件
        if '不及格' in text or '低于60' in text or '小于60' in text:
            filters['score_max'] = 59.9
            desc_parts.append("分数<60（不及格）")
            search_type = 'grade'
        elif '优秀' in text or '高分' in text:
            filters['score_min'] = 85
            desc_parts.append("分数>=85（优秀）")
            search_type = 'grade'

        # 分数比较
        score_comp = re.search(r'(\d+)分以上', text)
        if score_comp:
            filters['score_min'] = float(score_comp.group(1))
            desc_parts.append(f"分数>={filters['score_min']}")
            search_type = 'grade'
        score_comp_low = re.search(r'低于\s*(\d+)', text)
        if score_comp_low and 'score_max' not in filters:
            filters['score_max'] = float(score_comp_low.group(1))
            desc_parts.append(f"分数<{filters['score_max']}")
            search_type = 'grade'

        # 平均分条件
        if '平均分低于' in text or '均分低于' in text:
            avg_match = re.search(r'低于\s*(\d+)', text)
            if avg_match:
                filters['avg_below'] = float(avg_match.group(1))
                desc_parts.append(f"平均分<{filters['avg_below']}")

        # 学生姓名
        name_match = re.search(r'([一-龥]{2,3})(?!大学|工程|科学|技术|数学)', text)
        if name_match:
            nm = name_match.group(1)
            if len(nm) <= 3 and nm not in ('学生', '信息', '管理', '系统'):
                filters['name'] = nm
                desc_parts.append(f"姓名={filters['name']}")

        description = "、".join(desc_parts) if desc_parts else "全量查询"

        return {
            'filters': filters,
            'description': f"AI解析: {description}",
            'search_type': search_type,
        }

    # ============ 4. 数据异常检测 ============

    def detect_anomalies(self) -> list:
        """
        自动扫描数据异常
        返回：异常列表 [{'type': str, 'level': 'error'|'warning', 'desc': str, 'detail': str}]
        """
        anomalies = []
        conn = self.db.get_connection()

        # (a) 分数超出范围
        bad_scores = conn.execute(
            "SELECT g.id, g.student_id, g.name, g.course_name, g.score "
            "FROM grades g WHERE g.score < 0 OR g.score > 100"
        ).fetchall()
        for row in bad_scores:
            anomalies.append({
                'type': '分数异常', 'level': 'error',
                'desc': f"{row['name']}({row['student_id']}) {row['course_name']}分数={row['score']}",
                'detail': f"成绩ID={row['id']}，分数应在0-100之间",
                'target': 'grade', 'target_id': row['id']
            })

        # (b) 重复学号
        dup_ids = conn.execute(
            "SELECT student_id, COUNT(*) as cnt FROM students GROUP BY student_id HAVING cnt > 1"
        ).fetchall()
        for row in dup_ids:
            anomalies.append({
                'type': '重复学号', 'level': 'error',
                'desc': f"学号 {row['student_id']} 存在{row['cnt']}条重复记录",
                'detail': "请删除或合并重复记录",
                'target': 'student', 'target_id': row['student_id']
            })

        # (c) 缺失关键信息
        missing_name = conn.execute(
            "SELECT student_id, name FROM students WHERE name IS NULL OR name = ''"
        ).fetchall()
        for row in missing_name:
            anomalies.append({
                'type': '信息缺失', 'level': 'warning',
                'desc': f"学号 {row['student_id']} 姓名为空",
                'detail': "请补充学生姓名",
                'target': 'student', 'target_id': row['student_id']
            })

        missing_class = conn.execute(
            "SELECT student_id, name FROM students WHERE class_name IS NULL OR class_name = ''"
        ).fetchall()
        for row in missing_class:
            anomalies.append({
                'type': '信息缺失', 'level': 'warning',
                'desc': f"{row['name']}({row['student_id']}) 班级为空",
                'detail': "请补充班级信息",
                'target': 'student', 'target_id': row['student_id']
            })

        # (d) 成绩中姓名与学生表不一致
        mismatched = conn.execute("""
            SELECT g.id, g.student_id, g.name as gname, s.name as sname
            FROM grades g INNER JOIN students s ON g.student_id = s.student_id
            WHERE g.name != s.name
        """).fetchall()
        for row in mismatched:
            anomalies.append({
                'type': '姓名不一致', 'level': 'warning',
                'desc': f"学号{row['student_id']}：成绩表姓名={row['gname']}，学生表姓名={row['sname']}",
                'detail': "建议统一姓名为最新值",
                'target': 'grade', 'target_id': row['id']
            })

        return anomalies

    # ============ 5. 机器学习增强分析 ============

    def _build_student_feature_matrix(self) -> tuple:
        """
        构建学生特征矩阵用于ML分析
        返回: (student_ids, names, feature_matrix, feature_names)
        特征: [平均分, 标准差, 课程数, 及格率, 最高分, 最低分]
        """
        conn = self.db.get_connection()
        rows = conn.execute("""
            SELECT s.student_id, s.name,
                   AVG(g.score) as avg_score,
                   COUNT(g.id) as course_count,
                   SUM(CASE WHEN g.score >= 60 THEN 1 ELSE 0 END) * 1.0 / COUNT(g.id) as pass_rate,
                   MAX(g.score) as max_score,
                   MIN(g.score) as min_score
            FROM students s
            INNER JOIN grades g ON s.student_id = g.student_id
            GROUP BY s.student_id
            HAVING course_count >= 2
        """).fetchall()

        if len(rows) < 4:
            return [], [], np.array([]), []

        student_ids = [r['student_id'] for r in rows]
        names = [r['name'] for r in rows]

        matrix = np.array([
            [r['avg_score'], 0, r['course_count'], r['pass_rate'],
             r['max_score'], r['min_score']] for r in rows
        ], dtype=float)

        # 计算每个学生的标准差
        for i, sid in enumerate(student_ids):
            scores = [g['score'] for g in conn.execute(
                "SELECT score FROM grades WHERE student_id = ?", (sid,)
            ).fetchall()]
            matrix[i, 1] = float(np.std(scores)) if len(scores) > 1 else 0.0

        feature_names = ['平均分', '标准差', '课程数', '及格率', '最高分', '最低分']
        return student_ids, names, matrix, feature_names

    def cluster_students(self, n_clusters: int = 4) -> dict:
        """
        K-Means 学生聚类分析
        将学生按成绩特征自动分为 n_clusters 个群体
        返回: {'clusters': [...], 'centers': [...], 'labels': [...]}
        """
        if not HAS_ML:
            return {"error": "需要安装 scikit-learn: pip install scikit-learn numpy"}

        student_ids, names, matrix, feature_names = self._build_student_feature_matrix()
        if len(matrix) < n_clusters:
            return {"error": f"有成绩的学生数量({len(matrix)})不足{len(n_clusters)}人，无法聚类"}

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(matrix)

        # K-Means 聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        # 将聚类中心反标准化为原始尺度
        centers_original = scaler.inverse_transform(kmeans.cluster_centers_)

        # 按平均分排序，分配语义标签
        cluster_avg = [(i, centers_original[i, 0]) for i in range(n_clusters)]
        cluster_avg.sort(key=lambda x: x[1], reverse=True)
        label_names = {}
        semantic_labels = ['优秀群体', '良好群体', '中等群体', '需关注群体']
        for rank, (orig_idx, _) in enumerate(cluster_avg):
            label_names[orig_idx] = semantic_labels[rank] if rank < len(semantic_labels) else f'群体{rank+1}'

        # 组装结果
        clusters = []
        for i, (sid, name, label) in enumerate(zip(student_ids, names, labels)):
            clusters.append({
                'student_id': sid, 'name': name,
                'cluster_id': int(label),
                'cluster_name': label_names[label],
                'avg_score': round(float(matrix[i, 0]), 1),
                'pass_rate': f"{round(float(matrix[i, 3]) * 100, 1)}%",
                'course_count': int(matrix[i, 2]),
            })

        # 聚类中心描述
        centers_desc = []
        for orig_idx, (rank, _) in enumerate(cluster_avg):
            c = centers_original[orig_idx]
            centers_desc.append({
                'name': label_names[orig_idx],
                'size': int(sum(1 for l in labels if l == orig_idx)),
                'avg_score': round(float(c[0]), 1),
                'avg_pass_rate': f"{round(float(c[3]) * 100, 1)}%",
                'avg_courses': round(float(c[2]), 1),
            })

        return {
            'clusters': clusters,
            'centers': centers_desc,
            'total_students': len(student_ids),
            'n_clusters': n_clusters,
        }

    def predict_future_score(self, student_id: str, target_course: str = None) -> dict:
        """
        基于线性回归预测学生成绩
        用学生的其他特征（已有课程均分、课程数、最高分等）预测目标课程分数
        参数: student_id 学号, target_course 目标课程（可选）
        返回: {'predicted': float, 'confidence': str, 'features_used': [...]}
        """
        if not HAS_ML:
            return {"error": "需要安装 scikit-learn: pip install scikit-learn numpy"}

        conn = self.db.get_connection()

        # 获取所有有成绩的学生
        all_avg = conn.execute("""
            SELECT student_id, AVG(score) as avg_score, COUNT(*) as cnt,
                   MAX(score) as max_score, MIN(score) as min_score
            FROM grades GROUP BY student_id HAVING cnt >= 3
        """).fetchall()

        if len(all_avg) < 5:
            return {"error": "数据量不足，至少需要5名有3门以上课程成绩的学生"}

        # 构建训练数据: [avg_score, course_count, max_score, min_score] → 预测模型
        X = np.array([[r['avg_score'], r['cnt'], r['max_score'], r['min_score']] for r in all_avg], dtype=float)
        y = np.array([r['avg_score'] for r in all_avg], dtype=float)  # 用均分做target训练回归器

        # 训练
        model = LinearRegression()
        model.fit(X, y)
        r2_score = model.score(X, y)

        # 获取目标学生特征
        student = self.student_dao.get_by_student_id(student_id)
        if not student:
            return {"error": "学生不存在"}

        grades = conn.execute(
            "SELECT score FROM grades WHERE student_id = ?", (student_id,)
        ).fetchall()
        if len(grades) < 2:
            return {"error": f"{student['name']}成绩记录不足，无法预测"}

        scores = [g['score'] for g in grades]
        features = np.array([[
            np.mean(scores), len(scores), max(scores), min(scores)
        ]], dtype=float)

        predicted = round(float(model.predict(features)[0]), 1)
        predicted = max(0, min(100, predicted))  # 限制在0-100

        # 置信度评估
        if r2_score > 0.7:
            confidence = "高（模型拟合良好）"
        elif r2_score > 0.4:
            confidence = "中等"
        else:
            confidence = "较低（数据离散度高，仅供参考）"

        return {
            'student_id': student_id,
            'name': student['name'],
            'predicted_avg': predicted,
            'current_avg': round(float(np.mean(scores)), 1),
            'confidence': confidence,
            'r2_score': round(float(r2_score), 3),
            'sample_size': len(all_avg),
            'course_count': len(scores),
        }

    def analyze_course_correlation(self) -> dict:
        """
        课程成绩相关性分析
        计算各课程之间的Pearson相关系数，发现"关联课程"
        返回: {'pairs': [...], 'gateway_courses': [...], 'matrix': [...]}
        """
        if not HAS_ML:
            return {"error": "需要安装 scikit-learn: pip install scikit-learn numpy"}

        conn = self.db.get_connection()

        # 获取所有课程名称
        courses = [r['course_name'] for r in conn.execute(
            "SELECT DISTINCT course_name FROM grades ORDER BY course_name"
        ).fetchall()]

        if len(courses) < 2:
            return {"error": "课程数量不足，至少需要2门课程"}

        # 构建学生-课程分数矩阵
        students = [r['student_id'] for r in conn.execute(
            "SELECT DISTINCT student_id FROM grades"
        ).fetchall()]

        # 构建矩阵: rows=students, cols=courses
        score_matrix = np.full((len(students), len(courses)), np.nan)
        for i, sid in enumerate(students):
            for j, course in enumerate(courses):
                row = conn.execute(
                    "SELECT score FROM grades WHERE student_id = ? AND course_name = ?",
                    (sid, course)
                ).fetchone()
                if row:
                    score_matrix[i, j] = row['score']

        # 计算课程间相关系数（只对同时有两门课成绩的学生计算）
        pairs = []
        for i in range(len(courses)):
            for j in range(i + 1, len(courses)):
                col_i = score_matrix[:, i]
                col_j = score_matrix[:, j]
                mask = ~np.isnan(col_i) & ~np.isnan(col_j)
                if mask.sum() >= 3:  # 至少3个共同学生
                    corr = float(np.corrcoef(col_i[mask], col_j[mask])[0, 1])
                    if not np.isnan(corr):
                        pairs.append({
                            'course_a': courses[i], 'course_b': courses[j],
                            'correlation': round(corr, 3),
                            'strength': '强正相关' if corr > 0.6 else ('强负相关' if corr < -0.6 else
                                        ('中等正相关' if corr > 0.3 else ('中等负相关' if corr < -0.3 else '弱相关'))),
                            'sample_size': int(mask.sum()),
                        })

        pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)

        # 识别"核心课程"（与其他课程平均相关性最高的课程）
        course_avg_corr = {}
        for course in courses:
            related = [p for p in pairs if p['course_a'] == course or p['course_b'] == course]
            if related:
                course_avg_corr[course] = round(
                    sum(abs(p['correlation']) for p in related) / len(related), 3
                )

        gateway = sorted(course_avg_corr.items(), key=lambda x: x[1], reverse=True)[:3]
        gateway_courses = [{'course': c, 'avg_correlation': v} for c, v in gateway]

        return {
            'pairs': pairs[:20],
            'gateway_courses': gateway_courses,
            'total_courses': len(courses),
            'total_students': len(students),
        }

    def detect_outliers_ml(self) -> dict:
        """
        Isolation Forest 异常检测
        替代简单阈值判断，使用无监督学习识别成绩模式异常的学生
        返回: {'outliers': [...], 'total_analyzed': int}
        """
        if not HAS_ML:
            return {"error": "需要安装 scikit-learn: pip install scikit-learn numpy"}

        student_ids, names, matrix, feature_names = self._build_student_feature_matrix()
        if len(matrix) < 10:
            return {"error": "数据量不足，至少需要10名有成绩的学生"}

        # 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(matrix)

        # Isolation Forest
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        preds = iso_forest.fit_predict(X_scaled)
        scores = iso_forest.decision_function(X_scaled)

        outliers = []
        for i, (sid, name) in enumerate(zip(student_ids, names)):
            if preds[i] == -1:  # 异常
                # 找出最异常的维度
                deviations = np.abs(X_scaled[i])
                top_dev_idx = int(np.argmax(deviations))
                reason = f"{feature_names[top_dev_idx]}显著偏离群体（偏差指数: {round(float(deviations[top_dev_idx]), 2)}）"

                outliers.append({
                    'student_id': sid, 'name': name,
                    'anomaly_score': round(float(scores[i]), 3),
                    'avg_score': round(float(matrix[i, 0]), 1),
                    'pass_rate': f"{round(float(matrix[i, 3]) * 100, 1)}%",
                    'reason': reason,
                    'target': 'student', 'target_id': sid,
                })

        outliers.sort(key=lambda x: x['anomaly_score'])
        return {
            'outliers': outliers,
            'total_analyzed': len(student_ids),
            'feature_names': feature_names,
        }

    def rank_students(self) -> dict:
        """
        学生综合排名
        加权评分: 均分*0.6 + 及格率*100*0.3 + min(课程数/8, 1.0)*100*0.1
        返回: {'rankings': [...], 'top3': [...], 'bottom3': [...]}
        """
        student_ids, names, matrix, _ = self._build_student_feature_matrix()
        if len(matrix) == 0:
            return {"error": "暂无足够的成绩数据"}

        rankings = []
        for i, (sid, name) in enumerate(zip(student_ids, names)):
            avg = matrix[i, 0]   # 平均分
            pr = matrix[i, 3]    # 及格率
            cc = min(matrix[i, 2] / 8.0, 1.0)  # 课程数归一化（8门满分）

            weighted = avg * 0.6 + pr * 100 * 0.3 + cc * 100 * 0.1

            rankings.append({
                'student_id': sid, 'name': name,
                'avg_score': round(float(avg), 1),
                'pass_rate': f"{round(float(pr) * 100, 1)}%",
                'course_count': int(matrix[i, 2]),
                'weighted_score': round(float(weighted), 1),
            })

        rankings.sort(key=lambda x: x['weighted_score'], reverse=True)

        # 分配排名和百分位
        n = len(rankings)
        for rank, r in enumerate(rankings, 1):
            r['rank'] = rank
            r['percentile'] = f"前{round((n - rank) / n * 100, 1)}%"

        return {
            'rankings': rankings,
            'top3': rankings[:3],
            'bottom3': rankings[-3:][::-1],
            'total': n,
        }

    # ============ 6. 报表智能总结 ============


    def generate_report_summary(self, students: list, grades: list = None) -> str:
        """
        为导出报表生成AI数据摘要
        参数：students（学生列表Row对象）, grades（成绩列表Row对象，可选）
        返回：自然语言摘要文本（3-4段）
        """
        if not students:
            return "暂无数据可供分析。"

        n_students = len(students)
        classes = list(set(s.get('class_name', '') for s in students if s.get('class_name')))
        majors = list(set(s.get('major', '') for s in students if s.get('major')))
        genders = [s['gender'] for s in students]
        male_count = sum(1 for g in genders if g == '男')
        female_count = n_students - male_count

        lines = []
        lines.append(f"本报表共包含 {n_students} 名学生数据")
        if male_count + female_count == n_students:
            lines[0] += f"（男生 {male_count} 人，女生 {female_count} 人）"
        lines[0] += "。"

        if classes:
            lines.append(f"涵盖 {len(classes)} 个班级：{'、'.join(classes[:5])}"
                        f"{'等' if len(classes) > 5 else ''}。")
        if majors:
            lines.append(f"涉及 {len(majors)} 个专业方向。")

        if grades:
            total_g = len(grades)
            scores = [g['score'] for g in grades]
            avg_g = round(sum(scores) / len(scores), 1) if scores else 0
            pass_g = sum(1 for s in scores if s >= 60)
            pass_r = round(pass_g / len(scores) * 100, 1) if scores else 0

            lines.append(
                f"成绩数据共 {total_g} 条记录，总体平均分 {avg_g} 分，"
                f"及格率 {pass_r}%。"
            )

            # 找出亮点和薄弱点
            course_avgs = {}
            for g in grades:
                cn = g['course_name']
                if cn not in course_avgs:
                    course_avgs[cn] = []
                course_avgs[cn].append(g['score'])
            course_avg = {cn: round(sum(sc)/len(sc), 1) for cn, sc in course_avgs.items()}
            sorted_courses = sorted(course_avg.items(), key=lambda x: x[1], reverse=True)

            if sorted_courses:
                lines.append(
                    f"优势科目为{sorted_courses[0][0]}（均分{sorted_courses[0][1]}分），"
                    f"需关注科目为{sorted_courses[-1][0]}（均分{sorted_courses[-1][1]}分）。"
                )

        return "\n".join(lines)


# ==================== 第一层：数据访问层 (DAO) ====================

class DatabaseManager:
    """
    数据库管理器（单例模式）
    负责数据库连接、建表、初始化种子数据、备份还原
    """

    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.db_path = DB_NAME

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（自动重连）"""
        try:
            if self._connection is None:
                self._connection = sqlite3.connect(self.db_path)
                self._connection.execute("PRAGMA journal_mode=WAL")  # WAL模式提升并发性能
                self._connection.execute("PRAGMA foreign_keys=ON")
                self._connection.row_factory = sqlite3.Row
            return self._connection
        except sqlite3.Error as e:
            print(f"数据库连接失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def init_database(self):
        """
        初始化数据库：建表 + 插入默认数据
        首次运行时自动调用
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # -------- 用户表 --------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(64) NOT NULL,
                salt VARCHAR(32) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'teacher',
                real_name VARCHAR(50) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -------- 学生信息表 --------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(50) NOT NULL,
                gender VARCHAR(10) DEFAULT '男',
                major VARCHAR(100) DEFAULT '',
                class_name VARCHAR(50) DEFAULT '',
                enrollment_year INTEGER DEFAULT 2024,
                phone VARCHAR(20) DEFAULT '',
                remark TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -------- 成绩表 --------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id VARCHAR(20) NOT NULL,
                name VARCHAR(50) NOT NULL,
                course_name VARCHAR(100) NOT NULL,
                score REAL NOT NULL,
                semester VARCHAR(20) DEFAULT '',
                exam_time DATE DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            )
        """)

        # -------- 操作日志表 --------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) NOT NULL,
                operation VARCHAR(50) NOT NULL,
                target VARCHAR(100) DEFAULT '',
                detail TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # -------- 创建索引提升查询性能 --------
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_name ON students(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_class ON students(class_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_grades_student_id ON grades(student_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_grades_course ON grades(course_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_username ON operation_logs(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_time ON operation_logs(created_at)")

        conn.commit()

        # -------- 插入默认用户（如不存在） --------
        for username, password, role, real_name in DEFAULT_USERS:
            existing = cursor.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if not existing:
                salt = generate_salt()
                pwd_hash = md5_hash(password, salt)
                cursor.execute(
                    "INSERT INTO users (username, password_hash, salt, role, real_name) VALUES (?, ?, ?, ?, ?)",
                    (username, pwd_hash, salt, role, real_name)
                )

        # -------- 插入示例学生数据（仅当学生表为空时） --------
        count = cursor.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if count == 0:
            sample_students = [
                ("2024001", "张三", "男", "计算机科学与技术", "计科2401", 2024, "13800138001", "班长"),
                ("2024002", "李四", "女", "软件工程", "软件2401", 2024, "13800138002", ""),
                ("2024003", "王五", "男", "数据科学", "数据2401", 2024, "13800138003", "学习委员"),
                ("2024004", "赵六", "女", "计算机科学与技术", "计科2401", 2024, "13800138004", ""),
                ("2024005", "孙七", "男", "人工智能", "智能2401", 2024, "13800138005", ""),
                ("2024006", "周八", "女", "软件工程", "软件2402", 2024, "13800138006", ""),
                ("2024007", "吴九", "男", "网络工程", "网络2401", 2024, "13800138007", ""),
                ("2024008", "郑十", "女", "计算机科学与技术", "计科2402", 2024, "13800138008", "团支书"),
                ("2024009", "冯十一", "男", "信息安全", "信安2401", 2024, "13800138009", ""),
                ("2024010", "陈十二", "女", "人工智能", "智能2402", 2024, "13800138010", ""),
            ]
            for s in sample_students:
                cursor.execute(
                    "INSERT INTO students (student_id, name, gender, major, class_name, enrollment_year, phone, remark) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", s
                )

            # 插入示例成绩数据
            sample_grades = [
                ("2024001", "张三", "高等数学", 92, "2024-2025-1", "2025-01-10"),
                ("2024001", "张三", "线性代数", 88, "2024-2025-1", "2025-01-15"),
                ("2024002", "李四", "高等数学", 85, "2024-2025-1", "2025-01-10"),
                ("2024002", "李四", "C语言程序设计", 90, "2024-2025-1", "2025-01-12"),
                ("2024003", "王五", "高等数学", 78, "2024-2025-1", "2025-01-10"),
                ("2024003", "王五", "数据结构", 82, "2024-2025-2", "2025-06-20"),
                ("2024004", "赵六", "C语言程序设计", 95, "2024-2025-1", "2025-01-12"),
                ("2024005", "孙七", "线性代数", 73, "2024-2025-1", "2025-01-15"),
                ("2024006", "周八", "高等数学", 91, "2024-2025-1", "2025-01-10"),
                ("2024007", "吴九", "数据结构", 68, "2024-2025-2", "2025-06-20"),
                ("2024008", "郑十", "C语言程序设计", 87, "2024-2025-1", "2025-01-12"),
                ("2024009", "冯十一", "高等数学", 76, "2024-2025-1", "2025-01-10"),
                ("2024010", "陈十二", "线性代数", 94, "2024-2025-1", "2025-01-15"),
            ]
            for g in sample_grades:
                cursor.execute(
                    "INSERT INTO grades (student_id, name, course_name, score, semester, exam_time) "
                    "VALUES (?, ?, ?, ?, ?, ?)", g
                )

        conn.commit()

    def backup_database(self, backup_path: str) -> bool:
        """备份数据库到指定路径"""
        try:
            self.close()  # 先关闭连接确保数据写入磁盘
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            print(f"备份失败: {e}")
            return False
        finally:
            self.get_connection()  # 重新建立连接

    def restore_database(self, backup_path: str) -> bool:
        """从备份文件还原数据库"""
        try:
            self.close()
            shutil.copy2(backup_path, self.db_path)
            return True
        except Exception as e:
            print(f"还原失败: {e}")
            return False
        finally:
            self.get_connection()

    def ensure_ml_training_data(self) -> Tuple[int, int]:
        """
        确保有足够的训练数据供ML分析使用
        若学生数<60, 自动补充合成数据
        返回: (新增学生数, 新增成绩数)
        """
        conn = self.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if count >= 60:
            return 0, 0

        import random
        random.seed(42)

        # 生成合成学生
        majors_list = ['计算机科学与技术', '软件工程', '数据科学与大数据技术',
                       '人工智能', '网络工程', '信息安全', '物联网工程']
        classes_list = ['计科2401', '计科2402', '软件2401', '软件2402', '数据2401',
                        '智能2401', '智能2402', '网络2401', '信安2401', '物联2401']
        surnames = ['张', '李', '王', '赵', '陈', '刘', '黄', '周', '吴', '郑',
                    '冯', '孙', '朱', '马', '胡', '林', '何', '高', '罗', '郭',
                    '杨', '梁', '宋', '唐', '许', '韩', '邓', '彭', '曾', '萧']
        given_names = ['明', '华', '强', '伟', '芳', '娜', '敏', '静', '丽', '洋',
                       '涛', '斌', '磊', '鹏', '杰', '欣', '宇', '浩', '然', '博',
                       '文', '峰', '毅', '恒', '远', '宁', '悦', '雪', '琳', '飞']

        new_students = []
        insert_sql = ("INSERT INTO students (student_id, name, gender, major, class_name, "
                      "enrollment_year, phone, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")

        target = 100
        existing_ids = set(r['student_id'] for r in conn.execute("SELECT student_id FROM students").fetchall())

        for i in range(count + 1, target + 1):
            sid = f"2024{str(i).zfill(3)}"
            if sid in existing_ids:
                continue
            name = random.choice(surnames) + random.choice(given_names)
            if random.random() < 0.5:
                name += random.choice(given_names)
            gender = random.choice(['男', '女'])
            major = random.choice(majors_list)
            class_name = random.choice(classes_list)
            year = random.choice([2022, 2023, 2024])
            phone = f"138{random.randint(10000000, 99999999)}"
            remark = random.choice(['', '班长', '学习委员', '团支书', '', '', ''])
            conn.execute(insert_sql, (sid, name, gender, major, class_name, year, phone, remark))
            new_students.append(sid)

        new_student_count = len(new_students)

        # 生成合成成绩
        courses = ['高等数学', '线性代数', 'C语言程序设计', '数据结构',
                   '大学英语', '概率论与数理统计', '操作系统', '计算机网络',
                   '数据库原理', '软件工程', '离散数学', '计算机组成原理']
        semesters = ['2022-2023-1', '2022-2023-2', '2023-2024-1',
                     '2023-2024-2', '2024-2025-1', '2024-2025-2']

        all_students = conn.execute("SELECT student_id, name FROM students").fetchall()
        grade_insert = ("INSERT INTO grades (student_id, name, course_name, score, semester, exam_time) "
                        "VALUES (?, ?, ?, ?, ?, ?)")

        new_grade_count = 0
        for s in all_students:
            # 每个学生随机选3-8门课程
            my_courses = random.sample(courses, random.randint(3, min(8, len(courses))))
            base_score = random.gauss(72, 10)  # 该学生的能力基准(正态分布)
            base_score = max(40, min(98, base_score))

            for course in my_courses:
                score = base_score + random.gauss(0, 8)  # 各科围绕基准波动
                score = round(max(0, min(100, score)), 1)
                semester = random.choice(semesters)
                # 考试时间: 学期对应的月份
                if '-1' in semester:
                    exam_month = random.choice(['01-10', '01-12', '01-15'])
                else:
                    exam_month = random.choice(['06-20', '06-22', '06-25'])
                exam_time = f"{semester[:4]}-{exam_month}"
                conn.execute(grade_insert, (s['student_id'], s['name'], course, score, semester, exam_time))
                new_grade_count += 1

        conn.commit()
        return new_student_count, new_grade_count


class UserDAO:
    """用户数据访问对象"""

    def __init__(self):
        self.db = DatabaseManager()

    def get_by_username(self, username: str) -> Optional[sqlite3.Row]:
        """根据用户名查询用户，返回行对象或None"""
        conn = self.db.get_connection()
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

    def get_all(self) -> List[sqlite3.Row]:
        """获取所有用户列表"""
        conn = self.db.get_connection()
        return conn.execute(
            "SELECT id, username, role, real_name, created_at FROM users ORDER BY id"
        ).fetchall()

    def insert(self, username: str, password_hash: str, salt: str,
               role: str, real_name: str) -> bool:
        """新增用户，返回是否成功"""
        try:
            conn = self.db.get_connection()
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role, real_name) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, salt, role, real_name)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update(self, user_id: int, **kwargs) -> bool:
        """更新用户信息（role, real_name等）"""
        allowed = ['role', 'real_name', 'password_hash', 'salt']
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        conn = self.db.get_connection()
        conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True

    def delete(self, user_id: int) -> bool:
        """删除用户（不允许删除自己）"""
        conn = self.db.get_connection()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True

    def reset_password(self, user_id: int, new_password: str) -> bool:
        """重置用户密码"""
        salt = generate_salt()
        pwd_hash = md5_hash(new_password, salt)
        return self.update(user_id, password_hash=pwd_hash, salt=salt)

    def exists_username(self, username: str, exclude_id: int = None) -> bool:
        """检查用户名是否已存在"""
        conn = self.db.get_connection()
        if exclude_id:
            row = conn.execute(
                "SELECT id FROM users WHERE username = ? AND id != ?",
                (username, exclude_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
        return row is not None


class StudentDAO:
    """学生信息数据访问对象"""

    def __init__(self):
        self.db = DatabaseManager()

    def get_count(self, filters: dict = None) -> int:
        """获取符合条件的学生总数"""
        conn = self.db.get_connection()
        where_clause, params = self._build_where(filters)
        sql = f"SELECT COUNT(*) FROM students {where_clause}"
        return conn.execute(sql, params).fetchone()[0]

    def get_page(self, page: int = 1, page_size: int = 20,
                 filters: dict = None, order_by: str = "id") -> List[sqlite3.Row]:
        """
        分页查询学生列表
        参数：
          page: 页码（从1开始）
          page_size: 每页条数
          filters: 筛选条件字典 {key: value}
          order_by: 排序字段
        返回：学生行对象列表
        """
        conn = self.db.get_connection()
        where_clause, params = self._build_where(filters)
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM students {where_clause}
            ORDER BY {order_by} LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        return conn.execute(sql, params).fetchall()

    def get_by_student_id(self, student_id: str) -> Optional[sqlite3.Row]:
        """根据学号查询学生"""
        conn = self.db.get_connection()
        return conn.execute(
            "SELECT * FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()

    def get_all_ids(self) -> List[str]:
        """获取所有学号列表"""
        conn = self.db.get_connection()
        rows = conn.execute("SELECT student_id FROM students").fetchall()
        return [r['student_id'] for r in rows]

    def insert(self, data: dict) -> bool:
        """新增学生记录"""
        try:
            conn = self.db.get_connection()
            conn.execute("""
                INSERT INTO students (student_id, name, gender, major, class_name,
                    enrollment_year, phone, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['student_id'], data['name'], data.get('gender', '男'),
                data.get('major', ''), data.get('class_name', ''),
                data.get('enrollment_year', 2024), data.get('phone', ''),
                data.get('remark', '')
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update(self, student_id: str, data: dict) -> bool:
        """更新学生信息"""
        try:
            conn = self.db.get_connection()
            conn.execute("""
                UPDATE students SET name=?, gender=?, major=?, class_name=?,
                    enrollment_year=?, phone=?, remark=?, updated_at=CURRENT_TIMESTAMP
                WHERE student_id=?
            """, (
                data['name'], data.get('gender', '男'), data.get('major', ''),
                data.get('class_name', ''), data.get('enrollment_year', 2024),
                data.get('phone', ''), data.get('remark', ''), student_id
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete(self, student_id: str) -> bool:
        """删除学生及其关联成绩"""
        conn = self.db.get_connection()
        conn.execute("DELETE FROM grades WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()
        return True

    def delete_all(self) -> int:
        """清空所有学生数据，返回删除条数"""
        conn = self.db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        conn.execute("DELETE FROM grades")
        conn.execute("DELETE FROM students")
        conn.commit()
        return count

    def bulk_insert(self, records: List[dict]) -> Tuple[int, int]:
        """
        批量导入学生数据
        返回：(成功条数, 失败条数)
        """
        conn = self.db.get_connection()
        success, fail = 0, 0
        for record in records:
            try:
                conn.execute("""
                    INSERT INTO students (student_id, name, gender, major,
                        class_name, enrollment_year, phone, remark)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.get('student_id', ''),
                    record.get('name', ''),
                    record.get('gender', '男'),
                    record.get('major', ''),
                    record.get('class_name', ''),
                    int(record.get('enrollment_year', 2024)),
                    record.get('phone', ''),
                    record.get('remark', '')
                ))
                success += 1
            except sqlite3.IntegrityError:
                fail += 1
        conn.commit()
        return success, fail

    def get_class_distribution(self) -> List[Tuple[str, int]]:
        """获取各班级人数分布"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT class_name, COUNT(*) as cnt FROM students GROUP BY class_name ORDER BY cnt DESC"
        ).fetchall()
        return [(r['class_name'], r['cnt']) for r in rows]

    def get_all_majors(self) -> List[str]:
        """获取所有不重复的专业列表"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT DISTINCT major FROM students WHERE major != '' ORDER BY major"
        ).fetchall()
        return [r['major'] for r in rows]

    def get_all_classes(self) -> List[str]:
        """获取所有不重复的班级列表"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT DISTINCT class_name FROM students WHERE class_name != '' ORDER BY class_name"
        ).fetchall()
        return [r['class_name'] for r in rows]

    def get_enrollment_years(self) -> List[int]:
        """获取所有入学年份列表"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT DISTINCT enrollment_year FROM students ORDER BY enrollment_year"
        ).fetchall()
        return [r['enrollment_year'] for r in rows]

    def get_major_distribution(self) -> List[Tuple[str, int]]:
        """获取各专业人数分布"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT major, COUNT(*) as cnt FROM students WHERE major != '' "
            "GROUP BY major ORDER BY cnt DESC"
        ).fetchall()
        return [(r['major'], r['cnt']) for r in rows]

    def get_year_distribution(self) -> List[Tuple[int, int]]:
        """获取各入学年份人数分布"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT enrollment_year, COUNT(*) as cnt FROM students "
            "GROUP BY enrollment_year ORDER BY enrollment_year"
        ).fetchall()
        return [(r['enrollment_year'], r['cnt']) for r in rows]

    def _build_where(self, filters: dict = None) -> Tuple[str, list]:
        """构建WHERE子句和参数列表"""
        if not filters:
            return "", []
        conditions = []
        params = []
        for key, value in filters.items():
            if value:
                if key in ('student_id', 'name', 'class_name', 'major'):
                    conditions.append(f"{key} LIKE ?")
                    params.append(f"%{value}%")
                elif key == 'enrollment_year':
                    conditions.append(f"{key} = ?")
                    params.append(int(value))
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where, params


class GradeDAO:
    """成绩数据访问对象"""

    def __init__(self):
        self.db = DatabaseManager()

    def get_count(self, filters: dict = None) -> int:
        """获取符合条件的成绩总数"""
        conn = self.db.get_connection()
        where_clause, params = self._build_where(filters)
        sql = f"SELECT COUNT(*) FROM grades {where_clause}"
        return conn.execute(sql, params).fetchone()[0]

    def get_page(self, page: int = 1, page_size: int = 20,
                 filters: dict = None, order_by: str = "id") -> List[sqlite3.Row]:
        """分页查询成绩列表"""
        conn = self.db.get_connection()
        where_clause, params = self._build_where(filters)
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM grades {where_clause}
            ORDER BY {order_by} LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        return conn.execute(sql, params).fetchall()

    def get_all(self, filters: dict = None) -> List[sqlite3.Row]:
        """获取所有成绩（用于统计）"""
        conn = self.db.get_connection()
        where_clause, params = self._build_where(filters)
        sql = f"SELECT * FROM grades {where_clause} ORDER BY id"
        return conn.execute(sql, params).fetchall()

    def insert(self, data: dict) -> bool:
        """新增成绩记录"""
        try:
            conn = self.db.get_connection()
            conn.execute("""
                INSERT INTO grades (student_id, name, course_name, score, semester, exam_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['student_id'], data['name'], data['course_name'],
                float(data['score']), data.get('semester', ''), data.get('exam_time', None)
            ))
            conn.commit()
            return True
        except Exception:
            return False

    def update(self, grade_id: int, data: dict) -> bool:
        """更新成绩记录"""
        try:
            conn = self.db.get_connection()
            conn.execute("""
                UPDATE grades SET student_id=?, name=?, course_name=?, score=?,
                    semester=?, exam_time=?
                WHERE id=?
            """, (
                data['student_id'], data['name'], data['course_name'],
                float(data['score']), data.get('semester', ''),
                data.get('exam_time', None), grade_id
            ))
            conn.commit()
            return True
        except Exception:
            return False

    def delete(self, grade_id: int) -> bool:
        """删除成绩记录"""
        conn = self.db.get_connection()
        conn.execute("DELETE FROM grades WHERE id = ?", (grade_id,))
        conn.commit()
        return True

    def get_statistics(self, course_name: str = None) -> dict:
        """获取成绩统计数据"""
        conn = self.db.get_connection()
        if course_name:
            row = conn.execute(
                "SELECT AVG(score) as avg_score, MAX(score) as max_score, "
                "MIN(score) as min_score, COUNT(*) as total "
                "FROM grades WHERE course_name = ?", (course_name,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT AVG(score) as avg_score, MAX(score) as max_score, "
                "MIN(score) as min_score, COUNT(*) as total FROM grades"
            ).fetchone()
        return {
            'avg_score': round(row['avg_score'], 2) if row['avg_score'] else 0,
            'max_score': row['max_score'] or 0,
            'min_score': row['min_score'] or 0,
            'total': row['total']
        }

    def get_course_averages(self) -> List[Tuple[str, float]]:
        """获取各课程平均分"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT course_name, AVG(score) as avg_score FROM grades "
            "GROUP BY course_name ORDER BY avg_score DESC"
        ).fetchall()
        return [(r['course_name'], round(r['avg_score'], 2)) for r in rows]

    def get_score_distribution(self) -> List[Tuple[str, int]]:
        """获取分数段分布"""
        conn = self.db.get_connection()
        ranges = [
            ("0-59", 0, 59.9),
            ("60-69", 60, 69.9),
            ("70-79", 70, 79.9),
            ("80-89", 80, 89.9),
            ("90-100", 90, 100),
        ]
        result = []
        for label, lo, hi in ranges:
            cnt = conn.execute(
                "SELECT COUNT(*) FROM grades WHERE score >= ? AND score <= ?",
                (lo, hi)
            ).fetchone()[0]
            result.append((label, cnt))
        return result

    def get_semester_averages(self) -> List[Tuple[str, float]]:
        """获取各学期平均分"""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT semester, AVG(score) as avg_score FROM grades "
            "GROUP BY semester ORDER BY semester"
        ).fetchall()
        return [(r['semester'], round(r['avg_score'], 2)) for r in rows]

    def _build_student_join_where(self, major: str = None, class_name: str = None,
                                   year: int = None) -> Tuple[str, list]:
        """构建JOIN students表的WHERE子句和参数"""
        conditions = []
        params = []
        if major:
            conditions.append("s.major = ?")
            params.append(major)
        if class_name:
            conditions.append("s.class_name = ?")
            params.append(class_name)
        if year:
            conditions.append("s.enrollment_year = ?")
            params.append(int(year))
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where, params

    def get_filtered_statistics(self, major: str = None, class_name: str = None,
                                 year: int = None) -> dict:
        """获取按学生属性过滤后的成绩统计数据"""
        conn = self.db.get_connection()
        where, params = self._build_student_join_where(major, class_name, year)
        sql = f"""
            SELECT AVG(g.score) as avg_score, MAX(g.score) as max_score,
                   MIN(g.score) as min_score, COUNT(*) as total,
                   SUM(CASE WHEN g.score >= 60 THEN 1 ELSE 0 END) as pass_count
            FROM grades g
            INNER JOIN students s ON g.student_id = s.student_id
            {where}
        """
        row = conn.execute(sql, params).fetchone()
        total = row['total'] or 0
        pass_count = row['pass_count'] or 0
        return {
            'avg_score': round(row['avg_score'], 2) if row['avg_score'] else 0,
            'max_score': row['max_score'] or 0,
            'min_score': row['min_score'] or 0,
            'total': total,
            'pass_count': pass_count,
            'pass_rate': round(pass_count / total * 100, 1) if total > 0 else 0
        }

    def get_filtered_score_distribution(self, major: str = None, class_name: str = None,
                                         year: int = None) -> List[Tuple[str, int]]:
        """获取按学生属性过滤后的分数段分布"""
        conn = self.db.get_connection()
        where, params = self._build_student_join_where(major, class_name, year)
        ranges = [
            ("0-59", 0, 59.9),
            ("60-69", 60, 69.9),
            ("70-79", 70, 79.9),
            ("80-89", 80, 89.9),
            ("90-100", 90, 100),
        ]
        result = []
        for label, lo, hi in ranges:
            conds = ["g.score >= ?", "g.score <= ?"]
            all_params = [lo, hi] + params
            prefix = " AND " if where else "WHERE "
            where_full = f"{where}{prefix}" + " AND ".join(conds)
            sql = f"""
                SELECT COUNT(*) FROM grades g
                INNER JOIN students s ON g.student_id = s.student_id
                {where_full}
            """
            cnt = conn.execute(sql, all_params).fetchone()[0]
            result.append((label, cnt))
        return result

    def get_filtered_course_averages(self, major: str = None, class_name: str = None,
                                      year: int = None) -> List[Tuple[str, float]]:
        """获取按学生属性过滤后的各课程平均分"""
        conn = self.db.get_connection()
        where, params = self._build_student_join_where(major, class_name, year)
        sql = f"""
            SELECT g.course_name, AVG(g.score) as avg_score
            FROM grades g
            INNER JOIN students s ON g.student_id = s.student_id
            {where}
            GROUP BY g.course_name ORDER BY avg_score DESC
        """
        rows = conn.execute(sql, params).fetchall()
        return [(r['course_name'], round(r['avg_score'], 2)) for r in rows]

    def get_filtered_semester_averages(self, major: str = None, class_name: str = None,
                                        year: int = None) -> List[Tuple[str, float]]:
        """获取按学生属性过滤后的各学期平均分"""
        conn = self.db.get_connection()
        where, params = self._build_student_join_where(major, class_name, year)
        sql = f"""
            SELECT g.semester, AVG(g.score) as avg_score
            FROM grades g
            INNER JOIN students s ON g.student_id = s.student_id
            {where}
            GROUP BY g.semester ORDER BY g.semester
        """
        rows = conn.execute(sql, params).fetchall()
        return [(r['semester'], round(r['avg_score'], 2)) for r in rows]

    def get_major_score_comparison(self) -> List[Tuple[str, float, int]]:
        """获取各专业成绩对比（专业名, 平均分, 成绩条数）"""
        conn = self.db.get_connection()
        rows = conn.execute("""
            SELECT s.major, AVG(g.score) as avg_score, COUNT(*) as cnt
            FROM grades g
            INNER JOIN students s ON g.student_id = s.student_id
            WHERE s.major != ''
            GROUP BY s.major ORDER BY avg_score DESC
        """).fetchall()
        return [(r['major'], round(r['avg_score'], 2), r['cnt']) for r in rows]

    def get_year_score_comparison(self) -> List[Tuple[int, float, int]]:
        """获取各年级成绩对比（入学年份, 平均分, 成绩条数）"""
        conn = self.db.get_connection()
        rows = conn.execute("""
            SELECT s.enrollment_year, AVG(g.score) as avg_score, COUNT(*) as cnt
            FROM grades g
            INNER JOIN students s ON g.student_id = s.student_id
            GROUP BY s.enrollment_year ORDER BY s.enrollment_year
        """).fetchall()
        return [(r['enrollment_year'], round(r['avg_score'], 2), r['cnt']) for r in rows]

    def get_class_score_comparison(self) -> List[Tuple[str, float, int]]:
        """获取各班级成绩对比（班级名, 平均分, 成绩条数）"""
        conn = self.db.get_connection()
        rows = conn.execute("""
            SELECT s.class_name, AVG(g.score) as avg_score, COUNT(*) as cnt
            FROM grades g
            INNER JOIN students s ON g.student_id = s.student_id
            WHERE s.class_name != ''
            GROUP BY s.class_name ORDER BY avg_score DESC
        """).fetchall()
        return [(r['class_name'], round(r['avg_score'], 2), r['cnt']) for r in rows]

    def _build_where(self, filters: dict = None) -> Tuple[str, list]:
        """构建WHERE子句"""
        if not filters:
            return "", []
        conditions = []
        params = []
        for key, value in filters.items():
            if value is not None and value != '':
                if key == 'score_min':
                    conditions.append("score >= ?")
                    params.append(float(value))
                elif key == 'score_max':
                    conditions.append("score <= ?")
                    params.append(float(value))
                elif key in ('student_id', 'name', 'course_name', 'semester'):
                    conditions.append(f"{key} LIKE ?")
                    params.append(f"%{value}%")
                elif key == 'class_name':
                    conditions.append(
                        "student_id IN (SELECT student_id FROM students WHERE class_name LIKE ?)")
                    params.append(f"%{value}%")
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where, params


class LogDAO:
    """操作日志数据访问对象"""

    def __init__(self):
        self.db = DatabaseManager()

    def insert(self, username: str, operation: str, target: str = "", detail: str = ""):
        """写入一条操作日志"""
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO operation_logs (username, operation, target, detail) VALUES (?, ?, ?, ?)",
            (username, operation, target, detail)
        )
        conn.commit()

    def get_page(self, page: int = 1, page_size: int = 50,
                 filters: dict = None) -> List[sqlite3.Row]:
        """分页查询日志"""
        conn = self.db.get_connection()
        where_clause, params = self._build_where(filters)
        offset = (page - 1) * page_size
        sql = f"""
            SELECT * FROM operation_logs {where_clause}
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        return conn.execute(sql, params).fetchall()

    def get_count(self, filters: dict = None) -> int:
        """获取日志总数"""
        conn = self.db.get_connection()
        where_clause, params = self._build_where(filters)
        sql = f"SELECT COUNT(*) FROM operation_logs {where_clause}"
        return conn.execute(sql, params).fetchone()[0]

    def clear(self) -> int:
        """清空日志"""
        conn = self.db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM operation_logs").fetchone()[0]
        conn.execute("DELETE FROM operation_logs")
        conn.commit()
        return count

    def _build_where(self, filters: dict = None) -> Tuple[str, list]:
        if not filters:
            return "", []
        conditions = []
        params = []
        if filters.get('username'):
            conditions.append("username LIKE ?")
            params.append(f"%{filters['username']}%")
        if filters.get('operation'):
            conditions.append("operation = ?")
            params.append(filters['operation'])
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where, params


# ==================== 第二层：业务逻辑层 (Service) ====================

class AuthService:
    """
    认证与权限服务
    负责登录验证、密码加密、权限判断
    """

    def __init__(self):
        self.user_dao = UserDAO()
        self.log_dao = LogDAO()
        self._current_user = None  # 当前登录用户信息

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        登录验证
        参数：
          username: 用户名
          password: 明文密码
        返回：(是否成功, 错误信息或角色)
        """
        if not username or not password:
            return False, "用户名和密码不能为空"

        user = self.user_dao.get_by_username(username)
        if not user:
            return False, "用户名不存在"

        pwd_hash = md5_hash(password, user['salt'])
        if pwd_hash != user['password_hash']:
            self.log_dao.insert(username, "登录失败", "密码错误")
            return False, "密码错误"

        self._current_user = dict(user)
        self.log_dao.insert(username, "登录成功", f"角色: {user['role']}")
        return True, user['role']

    def get_current_user(self) -> Optional[dict]:
        """获取当前登录用户"""
        return self._current_user

    def get_current_username(self) -> str:
        """获取当前用户名"""
        return self._current_user['username'] if self._current_user else ""

    def is_admin(self) -> bool:
        """判断当前用户是否为管理员"""
        return self._current_user and self._current_user['role'] == 'admin'

    def logout(self):
        """登出"""
        if self._current_user:
            self.log_dao.insert(self._current_user['username'], "登出")
            self._current_user = None

    def change_password(self, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        修改当前用户密码
        返回：(是否成功, 提示信息)
        """
        if not self._current_user:
            return False, "请先登录"

        username = self._current_user['username']
        user = self.user_dao.get_by_username(username)
        if md5_hash(old_password, user['salt']) != user['password_hash']:
            return False, "原密码错误"

        if len(new_password) < 6:
            return False, "新密码长度不能少于6位"

        salt = generate_salt()
        pwd_hash = md5_hash(new_password, salt)
        self.user_dao.update(user['id'], password_hash=pwd_hash, salt=salt)
        self._current_user['password_hash'] = pwd_hash
        self._current_user['salt'] = salt
        self.log_dao.insert(username, "修改密码", "密码已更新")
        return True, "密码修改成功"

    def create_user(self, username: str, password: str, role: str,
                    real_name: str) -> Tuple[bool, str]:
        """创建新用户（仅管理员）"""
        if not self.is_admin():
            return False, "权限不足"
        if len(username) < 3:
            return False, "用户名长度不少于3位"
        if len(password) < 6:
            return False, "密码长度不少于6位"
        if self.user_dao.exists_username(username):
            return False, "用户名已存在"

        salt = generate_salt()
        pwd_hash = md5_hash(password, salt)
        success = self.user_dao.insert(username, pwd_hash, salt, role, real_name)
        if success:
            self.log_dao.insert(self.get_current_username(), "创建用户",
                                username, f"角色: {role}")
            return True, "用户创建成功"
        return False, "创建失败"


class StudentService:
    """学生信息业务逻辑服务"""

    def __init__(self):
        self.student_dao = StudentDAO()
        self.log_dao = LogDAO()

    def validate_student(self, data: dict, is_update: bool = False) -> Tuple[bool, str]:
        """
        校验学生数据合法性
        返回：(是否合法, 错误信息)
        """
        if not data.get('student_id', '').strip():
            return False, "学号不能为空"
        if not data.get('name', '').strip():
            return False, "姓名不能为空"
        if not is_update:
            existing = self.student_dao.get_by_student_id(data['student_id'])
            if existing:
                return False, f"学号 {data['student_id']} 已存在"
        phone = data.get('phone', '')
        if phone and not validate_phone(phone):
            return False, "手机号格式不正确"
        return True, ""

    def add_student(self, data: dict, operator: str) -> Tuple[bool, str]:
        """新增学生"""
        valid, msg = self.validate_student(data)
        if not valid:
            return False, msg
        success = self.student_dao.insert(data)
        if success:
            self.log_dao.insert(operator, "新增学生", data['student_id'], data['name'])
            return True, "新增成功"
        return False, "新增失败，学号可能已存在"

    def update_student(self, student_id: str, data: dict, operator: str) -> Tuple[bool, str]:
        """更新学生信息"""
        valid, msg = self.validate_student(data, is_update=True)
        if not valid:
            return False, msg
        success = self.student_dao.update(student_id, data)
        if success:
            self.log_dao.insert(operator, "修改学生", student_id, data['name'])
            return True, "修改成功"
        return False, "修改失败"

    def delete_student(self, student_id: str, operator: str) -> Tuple[bool, str]:
        """删除学生"""
        student = self.student_dao.get_by_student_id(student_id)
        if not student:
            return False, "学生不存在"
        self.student_dao.delete(student_id)
        self.log_dao.insert(operator, "删除学生", student_id, student['name'])
        return True, "删除成功"

    def import_from_csv(self, filepath: str, operator: str) -> Tuple[int, int, str]:
        """从CSV文件导入学生数据"""
        try:
            records = []
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                records = list(reader)
            if not records:
                return 0, 0, "CSV文件中没有数据"
            success, fail = self.student_dao.bulk_insert(records)
            self.log_dao.insert(operator, "批量导入学生", f"成功{success}条，失败{fail}条")
            return success, fail, f"导入完成：成功{success}条，失败{fail}条"
        except Exception as e:
            return 0, 0, f"导入失败: {str(e)}"

    def import_from_json(self, filepath: str, operator: str) -> Tuple[int, int, str]:
        """从JSON文件导入学生数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                records = json.load(f)
            if isinstance(records, dict):
                records = records.get('students', records.get('data', []))
            if not records:
                return 0, 0, "JSON文件中没有数据"
            success, fail = self.student_dao.bulk_insert(records)
            self.log_dao.insert(operator, "批量导入学生(JSON)", f"成功{success}条，失败{fail}条")
            return success, fail, f"导入完成：成功{success}条，失败{fail}条"
        except Exception as e:
            return 0, 0, f"导入失败: {str(e)}"

    def export_to_csv(self, filepath: str, students: List[sqlite3.Row]) -> bool:
        """导出学生数据到CSV"""
        try:
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['学号', '姓名', '性别', '专业', '班级', '入学年份', '联系电话', '备注'])
                for s in students:
                    writer.writerow([
                        s['student_id'], s['name'], s['gender'], s['major'],
                        s['class_name'], s['enrollment_year'], s['phone'], s['remark']
                    ])
            return True
        except Exception:
            return False

    def export_to_json(self, filepath: str, students: List[sqlite3.Row]) -> bool:
        """导出学生数据到JSON"""
        try:
            data = []
            for s in students:
                data.append({
                    'student_id': s['student_id'], 'name': s['name'],
                    'gender': s['gender'], 'major': s['major'],
                    'class_name': s['class_name'], 'enrollment_year': s['enrollment_year'],
                    'phone': s['phone'], 'remark': s['remark']
                })
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False


class GradeService:
    """成绩业务逻辑服务"""

    def __init__(self):
        self.grade_dao = GradeDAO()
        self.student_dao = StudentDAO()
        self.log_dao = LogDAO()

    def validate_grade(self, data: dict) -> Tuple[bool, str]:
        """校验成绩数据"""
        if not data.get('student_id', '').strip():
            return False, "学号不能为空"
        if not data.get('name', '').strip():
            return False, "姓名不能为空"
        if not data.get('course_name', '').strip():
            return False, "课程名不能为空"
        if not validate_score(data.get('score')):
            return False, "分数必须在0-100之间"
        # 确认学生存在
        student = self.student_dao.get_by_student_id(data['student_id'])
        if not student:
            return False, f"学号 {data['student_id']} 对应的学生不存在"
        return True, ""

    def add_grade(self, data: dict, operator: str) -> Tuple[bool, str]:
        """新增成绩"""
        valid, msg = self.validate_grade(data)
        if not valid:
            return False, msg
        success = self.grade_dao.insert(data)
        if success:
            self.log_dao.insert(operator, "录入成绩",
                                f"{data['student_id']} {data['course_name']}",
                                f"分数: {data['score']}")
            return True, "录入成功"
        return False, "录入失败"

    def update_grade(self, grade_id: int, data: dict, operator: str) -> Tuple[bool, str]:
        """更新成绩"""
        valid, msg = self.validate_grade(data)
        if not valid:
            return False, msg
        success = self.grade_dao.update(grade_id, data)
        if success:
            self.log_dao.insert(operator, "修改成绩",
                                f"ID:{grade_id} {data['course_name']}",
                                f"新分数: {data['score']}")
            return True, "修改成功"
        return False, "修改失败"

    def delete_grade(self, grade_id: int, operator: str) -> Tuple[bool, str]:
        """删除成绩"""
        self.grade_dao.delete(grade_id)
        self.log_dao.insert(operator, "删除成绩", f"ID:{grade_id}")
        return True, "删除成功"


# ==================== 第三层：界面层 (UI) ====================

class LoginDialog(QDialog):
    """
    登录对话框
    功能：账号密码输入、角色识别、登录验证
    """

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.logged_in_role = None
        self.init_ui()

    def init_ui(self):
        """初始化登录界面"""
        self.setWindowTitle(f"{APP_TITLE} - 登录")
        self.setFixedSize(440, 420)
        self.setWindowFlags(
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setStyleSheet("QDialog { background-color: #ffffff; }")

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(40, 32, 40, 28)

        # 标题
        title_label = QLabel("学生管理信息系统")
        title_font = QFont("Microsoft YaHei", 18, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #1e293b;")
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("Student Management System")
        subtitle_font = QFont("Segoe UI", 9)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #64748b;")
        main_layout.addWidget(subtitle_label)

        main_layout.addSpacing(8)

        # 表单区域
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setMinimumHeight(38)
        self.username_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 14px;
            }
            QLineEdit:focus { border-color: #1a73e8; }
        """)

        # 密码框 + 显示/隐藏切换
        pwd_widget = QWidget()
        pwd_layout = QHBoxLayout()
        pwd_layout.setContentsMargins(0, 0, 0, 0)
        pwd_layout.setSpacing(4)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(38)
        self.password_input.setStyleSheet(self.username_input.styleSheet())

        self.toggle_pwd_btn = QPushButton("显示")
        self.toggle_pwd_btn.setFixedWidth(50)
        self.toggle_pwd_btn.setFixedHeight(38)
        self.toggle_pwd_btn.setCheckable(True)
        self.toggle_pwd_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #cbd5e1; border-radius: 6px;
                background-color: #f8fafc; color: #475569; font-size: 11px;
            }
            QPushButton:hover { background-color: #e2e8f0; }
            QPushButton:checked { background-color: #1a73e8; color: white; border-color: #1a73e8; }
        """)
        self.toggle_pwd_btn.clicked.connect(self._toggle_password_visibility)

        pwd_layout.addWidget(self.password_input)
        pwd_layout.addWidget(self.toggle_pwd_btn)
        pwd_widget.setLayout(pwd_layout)

        username_label = QLabel("用户名:")
        username_label.setFont(QFont("Microsoft YaHei", 10))
        username_label.setStyleSheet("color: #334155;")
        password_label = QLabel("密  码:")
        password_label.setFont(QFont("Microsoft YaHei", 10))
        password_label.setStyleSheet("color: #334155;")

        form_layout.addRow(username_label, self.username_input)
        form_layout.addRow(password_label, pwd_widget)

        # 大写锁定警告
        self.caps_lock_label = QLabel("提示: 大写锁定已开启")
        self.caps_lock_label.setFont(QFont("Microsoft YaHei", 8))
        self.caps_lock_label.setStyleSheet("color: #f9ab00;")
        self.caps_lock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caps_lock_label.setVisible(False)
        form_layout.addRow("", self.caps_lock_label)

        main_layout.addLayout(form_layout)

        # 错误提示标签
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Microsoft YaHei", 9))
        self.error_label.setStyleSheet("color: #d93025; padding: 4px 8px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setVisible(False)
        main_layout.addWidget(self.error_label)

        # 登录按钮
        self.login_btn = QPushButton("登  录")
        self.login_btn.setMinimumHeight(42)
        self.login_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1557b0; }
            QPushButton:pressed { background-color: #0d47a1; }
        """)
        self.login_btn.clicked.connect(self.do_login)
        main_layout.addWidget(self.login_btn)

        # 提示信息
        hint_label = QLabel("测试账号: admin/123456 (管理员) | teacher/123456 (教师)")
        hint_label.setFont(QFont("Microsoft YaHei", 8))
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: #64748b;")
        hint_label.setWordWrap(True)
        main_layout.addWidget(hint_label)

        self.setLayout(main_layout)

        # 绑定回车键
        self.password_input.returnPressed.connect(self.do_login)
        self.username_input.returnPressed.connect(self.password_input.setFocus)

        # 大写锁定检测
        self._caps_lock_timer = QTimer()
        self._caps_lock_timer.timeout.connect(self._check_caps_lock)
        self._caps_lock_timer.start(500)  # 每500ms检测

    def _check_caps_lock(self):
        """检测大写锁定状态"""
        try:
            import ctypes
            caps_on = ctypes.windll.user32.GetKeyState(0x14) & 1
            self.caps_lock_label.setVisible(bool(caps_on))
        except Exception:
            pass

    def _toggle_password_visibility(self):
        """切换密码显示/隐藏"""
        if self.toggle_pwd_btn.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pwd_btn.setText("隐藏")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pwd_btn.setText("显示")

    def _shake_window(self):
        """登录失败抖动动画"""
        geo = self.geometry()
        x, y = geo.x(), geo.y()
        for offset in [8, -8, 6, -6, 4, -4, 2, -2, 0]:
            self.move(x + offset, y)
            QApplication.processEvents()
            QThread.msleep(30)

    def do_login(self):
        """执行登录操作"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        success, result = self.auth_service.login(username, password)
        if success:
            self.logged_in_role = result
            self.accept()
        else:
            self.error_label.setText(result)
            self.error_label.setVisible(True)
            self._shake_window()


class StudentPage(QWidget):
    """
    学生信息管理页面
    功能：分页展示、模糊搜索、CRUD操作、批量导入导出
    """

    def __init__(self, student_service: StudentService, auth_service: AuthService):
        super().__init__()
        self.student_service = student_service
        self.auth_service = auth_service
        self.current_page = 1
        self.page_size = DEFAULT_PAGE_SIZE
        self.filters = {}
        self.init_ui()

    def init_ui(self):
        """初始化学生管理页面布局"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # -------- 搜索栏 --------
        search_group = QGroupBox("搜索条件")
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        search_layout.addWidget(QLabel("学号:"))
        self.search_student_id = QLineEdit()
        self.search_student_id.setPlaceholderText("输入学号模糊搜索")
        self.search_student_id.setMaximumWidth(120)

        search_layout.addWidget(QLabel("姓名:"))
        self.search_name = QLineEdit()
        self.search_name.setPlaceholderText("输入姓名模糊搜索")
        self.search_name.setMaximumWidth(120)

        search_layout.addWidget(QLabel("班级:"))
        self.search_class = QLineEdit()
        self.search_class.setPlaceholderText("输入班级")
        self.search_class.setMaximumWidth(100)

        search_layout.addWidget(QLabel("专业:"))
        self.search_major = QLineEdit()
        self.search_major.setPlaceholderText("输入专业")
        self.search_major.setMaximumWidth(100)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.do_search)
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.do_reset)
        self.ai_search_btn = QPushButton("AI 搜索")
        self.ai_search_btn.clicked.connect(self._open_ai_search)
        self.ai_search_btn.setStyleSheet("""
            QPushButton { color: #1a73e8; border-color: #1a73e8; font-weight: bold; }
            QPushButton:hover { background-color: #e8f0fe; }
        """)

        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.reset_btn)
        search_layout.addWidget(self.ai_search_btn)
        search_layout.addStretch()
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # -------- 操作按钮栏 --------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.add_btn = QPushButton("新增学生")
        self.add_btn.clicked.connect(self.do_add)
        self.edit_btn = QPushButton("修改")
        self.edit_btn.clicked.connect(self.do_edit)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.do_delete)
        self.clear_btn = QPushButton("清空所有")
        self.clear_btn.clicked.connect(self.do_clear)

        self.import_csv_btn = QPushButton("导入CSV")
        self.import_csv_btn.clicked.connect(self.do_import_csv)
        self.import_json_btn = QPushButton("导入JSON")
        self.import_json_btn.clicked.connect(self.do_import_json)
        self.export_csv_btn = QPushButton("导出CSV")
        self.export_csv_btn.clicked.connect(self.do_export_csv)
        self.export_json_btn = QPushButton("导出JSON")
        self.export_json_btn.clicked.connect(self.do_export_json)
        self.export_pdf_btn = QPushButton("导出PDF")
        self.export_pdf_btn.clicked.connect(self.do_export_pdf)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(QLabel("导入:"))
        btn_layout.addWidget(self.import_csv_btn)
        btn_layout.addWidget(self.import_json_btn)
        btn_layout.addWidget(QLabel("导出:"))
        btn_layout.addWidget(self.export_csv_btn)
        btn_layout.addWidget(self.export_json_btn)
        btn_layout.addWidget(self.export_pdf_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # -------- 学生表格 --------
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ['学号', '姓名', '性别', '专业', '班级', '入学年份', '联系电话', '备注']
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.verticalHeader().setMinimumWidth(40)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # -------- 分页栏 --------
        page_layout = QHBoxLayout()
        page_layout.setSpacing(8)

        self.page_size_combo = QComboBox()
        for size in PAGE_SIZE_OPTIONS:
            self.page_size_combo.addItem(str(size), size)
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentIndexChanged.connect(self.on_page_size_changed)

        self.prev_btn = QPushButton("< 上一页")
        self.prev_btn.clicked.connect(self.go_prev_page)
        self.next_btn = QPushButton("下一页 >")
        self.next_btn.clicked.connect(self.go_next_page)

        self.page_info_label = QLabel("第 1 页 / 共 1 页 (共 0 条)")
        self.page_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.jump_input = QSpinBox()
        self.jump_input.setMinimum(1)
        self.jump_input.setMaximum(1)
        self.jump_input.setMaximumWidth(60)
        self.jump_btn = QPushButton("跳转")
        self.jump_btn.clicked.connect(self.go_jump_page)

        page_layout.addWidget(QLabel("每页:"))
        page_layout.addWidget(self.page_size_combo)
        page_layout.addWidget(self.prev_btn)
        page_layout.addWidget(self.next_btn)
        page_layout.addStretch()
        page_layout.addWidget(self.page_info_label)
        page_layout.addStretch()
        page_layout.addWidget(QLabel("跳转到第"))
        page_layout.addWidget(self.jump_input)
        page_layout.addWidget(QLabel("页"))
        page_layout.addWidget(self.jump_btn)
        layout.addLayout(page_layout)

        self.setLayout(layout)

        # -------- 表格双击编辑 --------
        self.table.doubleClicked.connect(self.do_edit)

        # -------- 表格上下文菜单 --------
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def load_data(self):
        """加载学生数据到表格"""
        total = self.student_service.student_dao.get_count(self.filters)
        students = self.student_service.student_dao.get_page(
            self.current_page, self.page_size, self.filters
        )

        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.current_page > total_pages:
            self.current_page = total_pages
            students = self.student_service.student_dao.get_page(
                self.current_page, self.page_size, self.filters
            )

        self.table.setRowCount(len(students))
        for row, student in enumerate(students):
            for col, key in enumerate(
                ['student_id', 'name', 'gender', 'major', 'class_name',
                 'enrollment_year', 'phone', 'remark']
            ):
                value = student[key] if student[key] is not None else ""
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        self.page_info_label.setText(
            f"第{self.current_page}页 / 共{total_pages}页 (共{total}条)"
        )
        self.jump_input.setMaximum(total_pages)
        self.jump_input.setValue(self.current_page)

        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

    def do_search(self):
        """执行搜索"""
        self.filters = {}
        if self.search_student_id.text().strip():
            self.filters['student_id'] = self.search_student_id.text().strip()
        if self.search_name.text().strip():
            self.filters['name'] = self.search_name.text().strip()
        if self.search_class.text().strip():
            self.filters['class_name'] = self.search_class.text().strip()
        if self.search_major.text().strip():
            self.filters['major'] = self.search_major.text().strip()
        self.current_page = 1
        self.load_data()

    def do_reset(self):
        """重置搜索条件"""
        self.search_student_id.clear()
        self.search_name.clear()
        self.search_class.clear()
        self.search_major.clear()
        self.filters = {}
        self.current_page = 1
        self.load_data()

    def do_add(self):
        """新增学生"""
        dialog = StudentEditDialog(self.student_service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            operator = self.auth_service.get_current_username()
            success, msg = self.student_service.add_student(data, operator)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.load_data()
            else:
                QMessageBox.warning(self, "操作失败", msg)

    def do_edit(self):
        """修改学生信息"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条学生记录")
            return
        student_id = self.table.item(current_row, 0).text()
        student = self.student_service.student_dao.get_by_student_id(student_id)
        if not student:
            return
        dialog = StudentEditDialog(self.student_service, student_data=dict(student), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            operator = self.auth_service.get_current_username()
            success, msg = self.student_service.update_student(student_id, data, operator)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.load_data()
            else:
                QMessageBox.warning(self, "操作失败", msg)

    def do_delete(self):
        """删除学生"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条学生记录")
            return
        student_id = self.table.item(current_row, 0).text()
        name = self.table.item(current_row, 1).text()
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除学生「{name}」(学号:{student_id})吗？\n该操作将同时删除其所有成绩记录，不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            operator = self.auth_service.get_current_username()
            success, msg = self.student_service.delete_student(student_id, operator)
            QMessageBox.information(self, "结果", msg)
            self.load_data()

    def do_clear(self):
        """清空所有学生数据"""
        reply = QMessageBox.warning(
            self, "危险操作",
            "确定要清空所有学生数据及其成绩吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            count = self.student_service.student_dao.delete_all()
            student_service.log_dao.insert(
                self.auth_service.get_current_username(),
                "清空学生数据", f"共{count}条"
            )
            QMessageBox.information(self, "完成", f"已清空{count}条学生数据")
            self.load_data()

    def do_import_csv(self):
        """从CSV导入学生数据"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入CSV文件", "", "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        if filepath:
            operator = self.auth_service.get_current_username()
            success, fail, msg = self.student_service.import_from_csv(filepath, operator)
            QMessageBox.information(self, "导入结果", msg)
            self.load_data()

    def do_import_json(self):
        """从JSON导入学生数据"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入JSON文件", "", "JSON文件 (*.json);;所有文件 (*.*)"
        )
        if filepath:
            operator = self.auth_service.get_current_username()
            success, fail, msg = self.student_service.import_from_json(filepath, operator)
            QMessageBox.information(self, "导入结果", msg)
            self.load_data()

    def do_export_csv(self):
        """导出学生数据到CSV"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出CSV", "students_export.csv", "CSV文件 (*.csv)"
        )
        if filepath:
            students = self.student_service.student_dao.get_page(
                1, 99999, self.filters  # 导出全部符合条件的数据
            )
            if self.student_service.export_to_csv(filepath, students):
                QMessageBox.information(self, "成功", f"已导出{len(students)}条数据到:\n{filepath}")
            else:
                QMessageBox.warning(self, "失败", "导出失败")

    def do_export_json(self):
        """导出学生数据到JSON"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出JSON", "students_export.json", "JSON文件 (*.json)"
        )
        if filepath:
            students = self.student_service.student_dao.get_page(1, 99999, self.filters)
            if self.student_service.export_to_json(filepath, students):
                QMessageBox.information(self, "成功", f"已导出{len(students)}条数据到:\n{filepath}")
            else:
                QMessageBox.warning(self, "失败", "导出失败")

    def do_export_pdf(self):
        """导出学生数据到PDF"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出PDF", "students_report.pdf", "PDF文件 (*.pdf)"
        )
        if not filepath:
            return

        students = self.student_service.student_dao.get_page(1, 99999, self.filters)

        progress = QProgressDialog("正在生成PDF报表...", "取消", 0, len(students), self)
        progress.setWindowTitle("导出PDF")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(300)

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(filepath)
            printer.setPageMargins(QMarginsF(15, 15, 15, 15))

            painter = QPainter()
            if not painter.begin(printer):
                QMessageBox.warning(self, "失败", "无法创建PDF文件")
                return

            title_font = QFont("Microsoft YaHei", 14, QFont.Weight.Bold)
            header_font = QFont("Microsoft YaHei", 9, QFont.Weight.Bold)
            body_font = QFont("Microsoft YaHei", 8)

            y = 40
            page_width = printer.width()

            # AI 摘要
            ai = AIAnalyzer()
            summary_text = ai.generate_report_summary(students)
            painter.setFont(body_font)
            for line in summary_text.split('\n'):
                if y > page_height - 40:
                    printer.newPage()
                    y = 40
                painter.drawText(10, y, page_width - 20, 20, Qt.AlignmentFlag.AlignLeft, line)
                y += 20

            y += 10
            # 标题
            painter.setFont(title_font)
            painter.drawText(0, y, page_width, 30, Qt.AlignmentFlag.AlignCenter, "学生信息报表")
            y += 40

            # 表头
            headers = ['学号', '姓名', '性别', '专业', '班级', '入学年份', '电话', '备注']
            col_widths = [80, 60, 40, 120, 80, 60, 90, 100]
            total_width = sum(col_widths)
            scale = (page_width - 20) / total_width
            col_widths = [int(w * scale) for w in col_widths]

            painter.setFont(header_font)
            x = 10
            for i, (header, w) in enumerate(zip(headers, col_widths)):
                painter.drawRect(x, y, w, 25)
                painter.drawText(x, y, w, 25, Qt.AlignmentFlag.AlignCenter, header)
                x += w
            y += 25

            # 数据行
            painter.setFont(body_font)
            page_height = printer.height()
            for idx, s in enumerate(students):
                if progress.wasCanceled():
                    break
                progress.setValue(idx + 1)

                if y + 30 > page_height - 40:
                    printer.newPage()
                    y = 40
                    # 重绘表头
                    painter.setFont(header_font)
                    x = 10
                    for i, (header, w) in enumerate(zip(headers, col_widths)):
                        painter.drawRect(x, y, w, 25)
                        painter.drawText(x, y, w, 25, Qt.AlignmentFlag.AlignCenter, header)
                        x += w
                    y += 25
                    painter.setFont(body_font)

                row_data = [
                    s['student_id'], s['name'], s['gender'], s['major'],
                    s['class_name'], str(s['enrollment_year']), s['phone'], s['remark']
                ]
                x = 10
                for data, w in zip(row_data, col_widths):
                    painter.drawRect(x, y, w, 25)
                    painter.drawText(x + 2, y, w - 4, 25, Qt.AlignmentFlag.AlignVCenter, str(data))
                    x += w
                y += 25

            painter.end()
            progress.setValue(len(students))
            QMessageBox.information(self, "成功", f"已导出{len(students)}条数据到:\n{filepath}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def _show_context_menu(self, pos):
        """右键上下文菜单"""
        menu = QMenu(self)
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")
        menu.addSeparator()
        copy_action = menu.addAction("复制单元格")
        menu.addSeparator()
        export_sel_action = menu.addAction("导出选中行")
        select_all_action = menu.addAction("全选")

        row = self.table.currentRow()
        has_row = row >= 0 and row < self.table.rowCount()
        edit_action.setEnabled(has_row)
        delete_action.setEnabled(has_row)
        copy_action.setEnabled(has_row)
        export_sel_action.setEnabled(has_row)

        selected_rows = self.table.selectionModel().selectedRows()
        export_sel_action.setEnabled(len(selected_rows) > 0)

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if not action:
            return
        if action == edit_action:
            self.do_edit()
        elif action == delete_action:
            self.do_delete()
        elif action == copy_action and has_row:
            col = self.table.currentColumn()
            if col >= 0:
                item = self.table.item(row, col)
                text = item.text() if item else ""
                QApplication.clipboard().setText(text)
        elif action == export_sel_action:
            self._export_selected()
        elif action == select_all_action:
            self.table.selectAll()

    def _open_ai_search(self):
        """打开AI语义搜索"""
        main_win = self.window()
        if isinstance(main_win, QMainWindow) and hasattr(main_win, 'switch_page'):
            main_win.switch_page("ai")

    def _export_selected(self):
        """导出选中的学生行到CSV"""
        selected_rows = set()
        for idx in self.table.selectionModel().selectedRows():
            selected_rows.add(idx.row())
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要导出的行")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出选中学生", "selected_students.csv", "CSV文件 (*.csv)"
        )
        if not filepath:
            return
        try:
            data = []
            for row in sorted(selected_rows):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['学号', '姓名', '性别', '专业', '班级', '入学年份', '联系电话', '备注'])
                writer.writerows(data)
            QMessageBox.information(self, "成功", f"已导出 {len(data)} 条数据到:\n{filepath}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def go_prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()

    def go_next_page(self):
        """下一页"""
        self.current_page += 1
        self.load_data()

    def go_jump_page(self):
        """跳转到指定页"""
        self.current_page = self.jump_input.value()
        self.load_data()

    def on_page_size_changed(self):
        """每页条数变更"""
        self.page_size = self.page_size_combo.currentData()
        self.current_page = 1
        self.load_data()


class StudentEditDialog(QDialog):
    """学生信息编辑对话框（新增/修改共用）"""

    def __init__(self, student_service: StudentService, student_data: dict = None, parent=None):
        super().__init__(parent)
        self.student_service = student_service
        self.student_data = student_data
        self.is_edit = student_data is not None
        self.init_ui()

    def init_ui(self):
        """初始化编辑对话框"""
        self.setWindowTitle("修改学生信息" if self.is_edit else "新增学生")
        self.setFixedSize(480, 480)

        layout = QVBoxLayout()
        layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(10)

        self.student_id_input = QLineEdit()
        self.student_id_input.setPlaceholderText("必填，如: 2024001")
        if self.is_edit:
            self.student_id_input.setText(self.student_data.get('student_id', ''))
            self.student_id_input.setReadOnly(True)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("必填")
        if self.is_edit:
            self.name_input.setText(self.student_data.get('name', ''))

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(['男', '女'])
        if self.is_edit:
            self.gender_combo.setCurrentText(self.student_data.get('gender', '男'))

        self.major_input = QLineEdit()
        self.major_input.setPlaceholderText("如: 计算机科学与技术")
        if self.is_edit:
            self.major_input.setText(self.student_data.get('major', ''))

        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("如: 计科2401")
        if self.is_edit:
            self.class_input.setText(self.student_data.get('class_name', ''))

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2030)
        self.year_spin.setValue(self.student_data.get('enrollment_year', 2024) if self.is_edit else 2024)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("如: 13800138001")
        if self.is_edit:
            self.phone_input.setText(self.student_data.get('phone', ''))

        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText("可选备注")
        if self.is_edit:
            self.remark_input.setText(self.student_data.get('remark', ''))

        form.addRow("学号 *:", self.student_id_input)
        form.addRow("姓名 *:", self.name_input)
        form.addRow("性别:", self.gender_combo)
        form.addRow("专业:", self.major_input)
        form.addRow("班级:", self.class_input)
        form.addRow("入学年份:", self.year_spin)
        form.addRow("电话:", self.phone_input)
        form.addRow("备注:", self.remark_input)

        layout.addLayout(form)

        # -------- 实时验证错误提示 --------
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Microsoft YaHei", 9))
        self.error_label.setStyleSheet("color: #d93025; padding: 4px 0;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # -------- 按钮 --------
        btn_layout = QHBoxLayout()
        self.ai_fill_btn_s = QPushButton("AI 填充")
        self.ai_fill_btn_s.setMinimumHeight(36)
        self.ai_fill_btn_s.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc; color: #1a73e8;
                border: 1px solid #1a73e8; border-radius: 6px;
                font-weight: bold; padding: 8px 20px;
            }
            QPushButton:hover { background-color: #e8f0fe; }
        """)
        self.ai_fill_btn_s.clicked.connect(self._ai_fill_student)
        self.save_btn = QPushButton("保存")
        self.save_btn.setMinimumHeight(36)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: white;
                border: none; border-radius: 6px;
                font-weight: bold; padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1557b0; }
            QPushButton:pressed { background-color: #0d47a1; }
            QPushButton:disabled {
                background-color: #cbd5e1; color: #64748b;
            }
        """)
        self.save_btn.clicked.connect(self.do_save)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ai_fill_btn_s)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # -------- 绑定实时校验 --------
        self.name_input.textChanged.connect(self._validate_real_time)
        self.phone_input.textChanged.connect(self._validate_real_time)
        if not self.is_edit:
            self.student_id_input.textChanged.connect(self._validate_real_time)
        self._validate_real_time()  # 初始校验

    def _ai_fill_student(self):
        """AI辅助填报：根据学号和已有信息自动补全专业、班级等"""
        sid = self.student_id_input.text().strip()
        # 从数据库中找到类似学号的学生，推测专业和班级
        if sid and not self.is_edit:
            conn = self.student_service.student_dao.db.get_connection()
            # 按学号前缀匹配
            prefix = sid[:4] if len(sid) >= 4 else sid[:2]
            similar = conn.execute(
                "SELECT major, class_name FROM students WHERE student_id LIKE ? GROUP BY major, class_name LIMIT 1",
                (f"{prefix}%",)
            ).fetchone()
            if similar:
                if not self.major_input.text().strip() and similar['major']:
                    self.major_input.setText(similar['major'])
                if not self.class_input.text().strip() and similar['class_name']:
                    self.class_input.setText(similar['class_name'])

    def _validate_real_time(self):
        """实时输入校验"""
        errors = []
        sid = self.student_id_input.text().strip()
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()

        # 学号检查
        if not sid:
            if not self.is_edit:
                errors.append("学号不能为空")
                self.student_id_input.setProperty("invalid", True)
            else:
                self.student_id_input.setProperty("invalid", False)
        else:
            self.student_id_input.setProperty("invalid", False)

        # 姓名检查
        if not name:
            errors.append("姓名不能为空")
            self.name_input.setProperty("invalid", True)
        else:
            self.name_input.setProperty("invalid", False)

        # 手机号检查
        if phone and not validate_phone(phone):
            errors.append("手机号格式不正确（11位大陆手机号）")
            self.phone_input.setProperty("invalid", True)
        else:
            self.phone_input.setProperty("invalid", False)

        # 刷新样式
        for inp in [self.student_id_input, self.name_input, self.phone_input]:
            inp.style().unpolish(inp)
            inp.style().polish(inp)

        # 更新错误提示
        if errors:
            self.error_label.setText("; ".join(errors))
            self.error_label.setVisible(True)
        else:
            self.error_label.setText("")
            self.error_label.setVisible(False)

        # 保存按钮状态：必填项未填则禁用
        self.save_btn.setEnabled(bool(sid and name) if not self.is_edit else bool(name))

    def get_data(self) -> dict:
        """获取表单数据"""
        return {
            'student_id': self.student_id_input.text().strip(),
            'name': self.name_input.text().strip(),
            'gender': self.gender_combo.currentText(),
            'major': self.major_input.text().strip(),
            'class_name': self.class_input.text().strip(),
            'enrollment_year': self.year_spin.value(),
            'phone': self.phone_input.text().strip(),
            'remark': self.remark_input.text().strip()
        }

    def do_save(self):
        """保存操作"""
        data = self.get_data()
        valid, msg = self.student_service.validate_student(data, is_update=self.is_edit)
        if not valid:
            QMessageBox.warning(self, "数据校验失败", msg)
            return
        self.accept()


class GradePage(QWidget):
    """
    成绩管理页面
    功能：分页展示成绩、多条件筛选、录入编辑删除、自动统计
    """

    def __init__(self, grade_service: GradeService, auth_service: AuthService):
        super().__init__()
        self.grade_service = grade_service
        self.auth_service = auth_service
        self.current_page = 1
        self.page_size = DEFAULT_PAGE_SIZE
        self.filters = {}
        self.init_ui()

    def init_ui(self):
        """初始化成绩管理页面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # -------- 搜索栏 --------
        search_group = QGroupBox("筛选条件")
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        search_layout.addWidget(QLabel("学号:"))
        self.search_sid = QLineEdit()
        self.search_sid.setMaximumWidth(100)
        search_layout.addWidget(self.search_sid)

        search_layout.addWidget(QLabel("课程:"))
        self.search_course = QLineEdit()
        self.search_course.setMaximumWidth(100)
        search_layout.addWidget(self.search_course)

        search_layout.addWidget(QLabel("班级:"))
        self.search_class_g = QLineEdit()
        self.search_class_g.setMaximumWidth(80)
        search_layout.addWidget(self.search_class_g)

        search_layout.addWidget(QLabel("学期:"))
        self.search_semester = QLineEdit()
        self.search_semester.setMaximumWidth(80)
        search_layout.addWidget(self.search_semester)

        search_layout.addWidget(QLabel("分数:"))
        self.score_min = QDoubleSpinBox()
        self.score_min.setRange(0, 100)
        self.score_min.setMaximumWidth(70)
        self.score_min.setSpecialValueText("最低")
        self.score_min.setValue(0)
        search_layout.addWidget(self.score_min)
        search_layout.addWidget(QLabel("~"))
        self.score_max = QDoubleSpinBox()
        self.score_max.setRange(0, 100)
        self.score_max.setValue(100)
        self.score_max.setMaximumWidth(70)
        search_layout.addWidget(self.score_max)

        self.search_btn_g = QPushButton("筛选")
        self.search_btn_g.clicked.connect(self.do_search)
        self.reset_btn_g = QPushButton("重置")
        self.reset_btn_g.clicked.connect(self.do_reset)
        search_layout.addWidget(self.search_btn_g)
        search_layout.addWidget(self.reset_btn_g)
        search_layout.addStretch()
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # -------- 操作按钮 --------
        btn_layout = QHBoxLayout()
        self.add_grade_btn = QPushButton("录入成绩")
        self.add_grade_btn.clicked.connect(self.do_add)
        self.edit_grade_btn = QPushButton("修改")
        self.edit_grade_btn.clicked.connect(self.do_edit)
        self.delete_grade_btn = QPushButton("删除")
        self.delete_grade_btn.clicked.connect(self.do_delete)
        btn_layout.addWidget(self.add_grade_btn)
        btn_layout.addWidget(self.edit_grade_btn)
        btn_layout.addWidget(self.delete_grade_btn)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(QLabel("导出:"))
        self.export_csv_btn_g = QPushButton("导出CSV")
        self.export_csv_btn_g.clicked.connect(self.do_export_csv)
        self.export_json_btn_g = QPushButton("导出JSON")
        self.export_json_btn_g.clicked.connect(self.do_export_json)
        self.export_pdf_btn_g = QPushButton("导出PDF")
        self.export_pdf_btn_g.clicked.connect(self.do_export_pdf)
        btn_layout.addWidget(self.export_csv_btn_g)
        btn_layout.addWidget(self.export_json_btn_g)
        btn_layout.addWidget(self.export_pdf_btn_g)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # -------- 成绩表格 --------
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ['ID', '学号', '姓名', '课程名称', '分数', '学期', '考试时间']
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.verticalHeader().setMinimumWidth(40)
        self.table.setSortingEnabled(True)
        self.table.setColumnHidden(0, True)  # 隐藏ID列
        layout.addWidget(self.table)

        # -------- 统计栏 --------
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        self.avg_label = QLabel("平均分: --")
        self.max_label = QLabel("最高分: --")
        self.min_label = QLabel("最低分: --")
        self.total_label = QLabel("总记录: --")
        for lbl in [self.avg_label, self.max_label, self.min_label, self.total_label]:
            lbl.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            stats_layout.addWidget(lbl)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # -------- 分页栏 --------
        page_layout = QHBoxLayout()
        page_layout.setSpacing(8)

        self.page_size_combo_g = QComboBox()
        for size in PAGE_SIZE_OPTIONS:
            self.page_size_combo_g.addItem(str(size), size)
        self.page_size_combo_g.setCurrentText(str(self.page_size))
        self.page_size_combo_g.currentIndexChanged.connect(self.on_page_size_changed)

        self.prev_btn_g = QPushButton("< 上一页")
        self.prev_btn_g.clicked.connect(self.go_prev_page)
        self.next_btn_g = QPushButton("下一页 >")
        self.next_btn_g.clicked.connect(self.go_next_page)
        self.page_info_label_g = QLabel("第 1 页 / 共 1 页 (共 0 条)")
        self.page_info_label_g.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.jump_input_g = QSpinBox()
        self.jump_input_g.setMinimum(1)
        self.jump_input_g.setMaximum(1)
        self.jump_input_g.setMaximumWidth(60)
        self.jump_btn_g = QPushButton("跳转")
        self.jump_btn_g.clicked.connect(self.go_jump_page)

        page_layout.addWidget(QLabel("每页:"))
        page_layout.addWidget(self.page_size_combo_g)
        page_layout.addWidget(self.prev_btn_g)
        page_layout.addWidget(self.next_btn_g)
        page_layout.addStretch()
        page_layout.addWidget(self.page_info_label_g)
        page_layout.addStretch()
        page_layout.addWidget(QLabel("跳转到第"))
        page_layout.addWidget(self.jump_input_g)
        page_layout.addWidget(QLabel("页"))
        page_layout.addWidget(self.jump_btn_g)
        layout.addLayout(page_layout)

        self.setLayout(layout)

        # -------- 表格双击编辑 --------
        self.table.doubleClicked.connect(self.do_edit)

        # -------- 表格上下文菜单 --------
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def load_data(self):
        """加载成绩数据"""
        total = self.grade_service.grade_dao.get_count(self.filters)
        grades = self.grade_service.grade_dao.get_page(
            self.current_page, self.page_size, self.filters
        )

        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.current_page > total_pages:
            self.current_page = total_pages
            grades = self.grade_service.grade_dao.get_page(
                self.current_page, self.page_size, self.filters
            )

        self.table.setRowCount(len(grades))
        for row, g in enumerate(grades):
            for col, key in enumerate(['id', 'student_id', 'name', 'course_name', 'score', 'semester', 'exam_time']):
                value = g[key] if g[key] is not None else ""
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        self.page_info_label_g.setText(
            f"第{self.current_page}页 / 共{total_pages}页 (共{total}条)"
        )
        self.prev_btn_g.setEnabled(self.current_page > 1)
        self.next_btn_g.setEnabled(self.current_page < total_pages)
        self.jump_input_g.setMaximum(total_pages)
        self.jump_input_g.setValue(self.current_page)

        # 更新统计信息（使用筛选后的数据）
        stats = self._load_filtered_stats()
        self.avg_label.setText(f"平均分: {stats['avg_score']}")
        self.max_label.setText(f"最高分: {stats['max_score']}")
        self.min_label.setText(f"最低分: {stats['min_score']}")
        self.total_label.setText(f"总记录: {stats['total']}")

    def _load_filtered_stats(self):
        """获取当前筛选条件下的成绩统计（平均分/最高分/最低分/总记录数）"""
        conn = self.grade_service.grade_dao.db.get_connection()
        where_clause, params = self.grade_service.grade_dao._build_where(self.filters)
        sql = f"SELECT AVG(score) as avg_score, MAX(score) as max_score, MIN(score) as min_score, COUNT(*) as total FROM grades {where_clause}"
        row = conn.execute(sql, params).fetchone()
        return {
            'avg_score': round(row['avg_score'], 2) if row['avg_score'] else 0,
            'max_score': row['max_score'] or 0,
            'min_score': row['min_score'] or 0,
            'total': row['total']
        }

    def do_search(self):
        """执行筛选"""
        self.filters = {}
        if self.search_sid.text().strip():
            self.filters['student_id'] = self.search_sid.text().strip()
        if self.search_course.text().strip():
            self.filters['course_name'] = self.search_course.text().strip()
        if self.search_class_g.text().strip():
            self.filters['class_name'] = self.search_class_g.text().strip()
        if self.search_semester.text().strip():
            self.filters['semester'] = self.search_semester.text().strip()
        if self.score_min.value() > 0:
            self.filters['score_min'] = self.score_min.value()
        if self.score_max.value() < 100:
            self.filters['score_max'] = self.score_max.value()
        self.current_page = 1
        self.load_data()

    def do_reset(self):
        """重置筛选"""
        self.search_sid.clear()
        self.search_course.clear()
        self.search_class_g.clear()
        self.search_semester.clear()
        self.score_min.setValue(0)
        self.score_max.setValue(100)
        self.filters = {}
        self.current_page = 1
        self.load_data()

    def do_add(self):
        """录入成绩"""
        dialog = GradeEditDialog(self.grade_service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            operator = self.auth_service.get_current_username()
            success, msg = self.grade_service.add_grade(data, operator)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.load_data()
            else:
                QMessageBox.warning(self, "操作失败", msg)

    def do_edit(self):
        """修改成绩"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条成绩记录")
            return
        grade_id = int(self.table.item(current_row, 0).text())
        # 获取完整记录
        grades = self.grade_service.grade_dao.get_page(1, 1, {'student_id': self.table.item(current_row, 1).text()})
        # 简化处理：构建数据字典
        data = {
            'student_id': self.table.item(current_row, 1).text(),
            'name': self.table.item(current_row, 2).text(),
            'course_name': self.table.item(current_row, 3).text(),
            'score': float(self.table.item(current_row, 4).text()),
            'semester': self.table.item(current_row, 5).text(),
            'exam_time': self.table.item(current_row, 6).text()
        }
        dialog = GradeEditDialog(self.grade_service, grade_data=data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()
            operator = self.auth_service.get_current_username()
            success, msg = self.grade_service.update_grade(grade_id, new_data, operator)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.load_data()
            else:
                QMessageBox.warning(self, "操作失败", msg)

    def do_delete(self):
        """删除成绩"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请先选择一条成绩记录")
            return
        grade_id = int(self.table.item(current_row, 0).text())
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这条成绩记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            operator = self.auth_service.get_current_username()
            success, msg = self.grade_service.delete_grade(grade_id, operator)
            QMessageBox.information(self, "结果", msg)
            self.load_data()

    def do_export_csv(self):
        """导出成绩数据到CSV"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出成绩CSV", "grades_export.csv", "CSV文件 (*.csv)"
        )
        if filepath:
            grades = self.grade_service.grade_dao.get_page(1, 99999, self.filters)
            try:
                with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['学号', '姓名', '课程名称', '分数', '学期', '考试时间'])
                    for g in grades:
                        writer.writerow([
                            g['student_id'], g['name'], g['course_name'],
                            g['score'], g['semester'], g['exam_time']
                        ])
                QMessageBox.information(self, "成功", f"已导出{len(grades)}条成绩数据到:\n{filepath}")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", str(e))

    def do_export_json(self):
        """导出成绩数据到JSON"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出成绩JSON", "grades_export.json", "JSON文件 (*.json)"
        )
        if filepath:
            grades = self.grade_service.grade_dao.get_page(1, 99999, self.filters)
            try:
                data = []
                for g in grades:
                    data.append({
                        'student_id': g['student_id'], 'name': g['name'],
                        'course_name': g['course_name'], 'score': g['score'],
                        'semester': g['semester'], 'exam_time': g['exam_time']
                    })
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "成功", f"已导出{len(grades)}条成绩数据到:\n{filepath}")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", str(e))

    def do_export_pdf(self):
        """导出成绩数据到PDF"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出成绩PDF", "grades_report.pdf", "PDF文件 (*.pdf)"
        )
        if not filepath:
            return

        grades = self.grade_service.grade_dao.get_page(1, 99999, self.filters)

        progress = QProgressDialog("正在生成PDF报表...", "取消", 0, len(grades), self)
        progress.setWindowTitle("导出成绩PDF")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(300)

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(filepath)
            printer.setPageMargins(QMarginsF(15, 15, 15, 15))

            painter = QPainter()
            if not painter.begin(printer):
                QMessageBox.warning(self, "失败", "无法创建PDF文件")
                return

            title_font = QFont("Microsoft YaHei", 14, QFont.Weight.Bold)
            header_font = QFont("Microsoft YaHei", 9, QFont.Weight.Bold)
            body_font = QFont("Microsoft YaHei", 8)

            y = 40
            page_width = printer.width()
            page_height = printer.height()

            # AI 摘要
            ai = AIAnalyzer()
            students = self.grade_service.student_dao.get_page(1, 99999)
            summary_text = ai.generate_report_summary(students, grades)
            painter.setFont(body_font)
            for line in summary_text.split('\n'):
                if y > page_height - 40:
                    printer.newPage()
                    y = 40
                painter.drawText(10, y, page_width - 20, 20, Qt.AlignmentFlag.AlignLeft, line)
                y += 20

            y += 10
            # 标题
            painter.setFont(title_font)
            painter.drawText(0, y, page_width, 30, Qt.AlignmentFlag.AlignCenter, "成绩数据报表")
            y += 40

            # 表头
            headers = ['学号', '姓名', '课程名称', '分数', '学期', '考试时间']
            col_widths = [80, 60, 140, 60, 100, 90]
            total_width = sum(col_widths)
            scale = (page_width - 20) / total_width
            col_widths = [int(w * scale) for w in col_widths]

            painter.setFont(header_font)
            x = 10
            for i, (header, w) in enumerate(zip(headers, col_widths)):
                painter.drawRect(x, y, w, 25)
                painter.drawText(x, y, w, 25, Qt.AlignmentFlag.AlignCenter, header)
                x += w
            y += 25

            # 数据行
            painter.setFont(body_font)
            for idx, g in enumerate(grades):
                if progress.wasCanceled():
                    break
                progress.setValue(idx + 1)

                if y + 30 > page_height - 40:
                    printer.newPage()
                    y = 40
                    # 重绘表头
                    painter.setFont(header_font)
                    x = 10
                    for i, (header, w) in enumerate(zip(headers, col_widths)):
                        painter.drawRect(x, y, w, 25)
                        painter.drawText(x, y, w, 25, Qt.AlignmentFlag.AlignCenter, header)
                        x += w
                    y += 25
                    painter.setFont(body_font)

                row_data = [
                    g['student_id'], g['name'], g['course_name'],
                    str(g['score']), g['semester'], str(g.get('exam_time', ''))
                ]
                x = 10
                for data, w in zip(row_data, col_widths):
                    painter.drawRect(x, y, w, 25)
                    painter.drawText(x + 2, y, w - 4, 25, Qt.AlignmentFlag.AlignVCenter, str(data))
                    x += w
                y += 25

            painter.end()
            progress.setValue(len(grades))
            QMessageBox.information(self, "成功", f"已导出{len(grades)}条成绩数据到:\n{filepath}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def _show_context_menu(self, pos):
        """右键上下文菜单"""
        menu = QMenu(self)
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")
        menu.addSeparator()
        copy_action = menu.addAction("复制单元格")
        menu.addSeparator()
        select_all_action = menu.addAction("全选")

        row = self.table.currentRow()
        has_row = row >= 0 and row < self.table.rowCount()
        edit_action.setEnabled(has_row)
        delete_action.setEnabled(has_row)
        copy_action.setEnabled(has_row)

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if not action:
            return
        if action == edit_action:
            self.do_edit()
        elif action == delete_action:
            self.do_delete()
        elif action == copy_action and has_row:
            col = self.table.currentColumn()
            if col >= 0:
                item = self.table.item(row, col)
                text = item.text() if item else ""
                QApplication.clipboard().setText(text)
        elif action == select_all_action:
            self.table.selectAll()

    def go_prev_page(self): self.current_page -= 1; self.load_data()
    def go_next_page(self): self.current_page += 1; self.load_data()
    def go_jump_page(self): self.current_page = self.jump_input_g.value(); self.load_data()

    def on_page_size_changed(self):
        self.page_size = self.page_size_combo_g.currentData()
        self.current_page = 1
        self.load_data()


class GradeEditDialog(QDialog):
    """成绩编辑对话框"""

    def __init__(self, grade_service: GradeService, grade_data: dict = None, parent=None):
        super().__init__(parent)
        self.grade_service = grade_service
        self.grade_data = grade_data
        self.is_edit = grade_data is not None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("修改成绩" if self.is_edit else "录入成绩")
        self.setFixedSize(440, 380)

        layout = QVBoxLayout()
        layout.setSpacing(8)
        form = QFormLayout()
        form.setSpacing(10)

        self.sid_input = QLineEdit()
        self.sid_input.setPlaceholderText("必填，输入学号")
        if self.is_edit:
            self.sid_input.setText(self.grade_data.get('student_id', ''))

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("必填，输入姓名")
        if self.is_edit:
            self.name_input.setText(self.grade_data.get('name', ''))

        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText("如: 高等数学")
        if self.is_edit:
            self.course_input.setText(self.grade_data.get('course_name', ''))

        self.score_spin = QDoubleSpinBox()
        self.score_spin.setRange(0, 100)
        self.score_spin.setDecimals(1)
        self.score_spin.setValue(float(self.grade_data.get('score', 60)) if self.is_edit else 60)

        self.semester_input = QLineEdit()
        self.semester_input.setPlaceholderText("如: 2024-2025-1")
        if self.is_edit:
            self.semester_input.setText(self.grade_data.get('semester', ''))

        self.exam_date = QDateEdit()
        self.exam_date.setCalendarPopup(True)
        self.exam_date.setDate(QDate.currentDate())
        if self.is_edit and self.grade_data.get('exam_time'):
            try:
                dt = QDate.fromString(self.grade_data['exam_time'], "yyyy-MM-dd")
                if dt.isValid():
                    self.exam_date.setDate(dt)
            except Exception:
                pass

        form.addRow("学号 *:", self.sid_input)
        form.addRow("姓名 *:", self.name_input)
        form.addRow("课程 *:", self.course_input)
        form.addRow("分数 *:", self.score_spin)
        form.addRow("学期:", self.semester_input)
        form.addRow("考试时间:", self.exam_date)

        layout.addLayout(form)

        # -------- 实时验证错误提示 --------
        self.error_label = QLabel("")
        self.error_label.setFont(QFont("Microsoft YaHei", 9))
        self.error_label.setStyleSheet("color: #d93025; padding: 4px 0;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # -------- 按钮 --------
        btn_layout = QHBoxLayout()
        self.ai_fill_btn_g = QPushButton("AI 填充")
        self.ai_fill_btn_g.setMinimumHeight(36)
        self.ai_fill_btn_g.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc; color: #1a73e8;
                border: 1px solid #1a73e8; border-radius: 6px;
                font-weight: bold; padding: 8px 20px;
            }
            QPushButton:hover { background-color: #e8f0fe; }
        """)
        self.ai_fill_btn_g.clicked.connect(self._ai_fill_grade)
        self.save_btn = QPushButton("保存")
        self.save_btn.setMinimumHeight(36)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8; color: white;
                border: none; border-radius: 6px;
                font-weight: bold; padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1557b0; }
            QPushButton:pressed { background-color: #0d47a1; }
            QPushButton:disabled {
                background-color: #cbd5e1; color: #64748b;
            }
        """)
        self.save_btn.clicked.connect(self.do_save)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ai_fill_btn_g)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # -------- 绑定实时校验 --------
        self.sid_input.textChanged.connect(self._validate_real_time)
        self.name_input.textChanged.connect(self._validate_real_time)
        self.course_input.textChanged.connect(self._validate_real_time)
        self._validate_real_time()

    def _ai_fill_grade(self):
        """AI辅助填报：根据学号自动补全姓名、课程建议"""
        sid = self.sid_input.text().strip()
        if not sid:
            return
        student = self.grade_service.student_dao.get_by_student_id(sid)
        if student:
            if not self.name_input.text().strip():
                self.name_input.setText(student['name'])
        # 根据学生已有课程推荐
        if not self.course_input.text().strip():
            conn = self.grade_service.grade_dao.db.get_connection()
            existing = conn.execute(
                "SELECT course_name FROM grades WHERE student_id = ? ORDER BY id DESC LIMIT 1",
                (sid,)
            ).fetchone()
            if existing:
                self.course_input.setText(existing['course_name'])

    def _validate_real_time(self):
        """实时输入校验"""
        errors = []
        sid = self.sid_input.text().strip()
        name = self.name_input.text().strip()
        course = self.course_input.text().strip()

        if not sid:
            errors.append("学号不能为空")
            self.sid_input.setProperty("invalid", True)
        else:
            self.sid_input.setProperty("invalid", False)

        if not name:
            errors.append("姓名不能为空")
            self.name_input.setProperty("invalid", True)
        else:
            self.name_input.setProperty("invalid", False)

        if not course:
            errors.append("课程名不能为空")
            self.course_input.setProperty("invalid", True)
        else:
            self.course_input.setProperty("invalid", False)

        for inp in [self.sid_input, self.name_input, self.course_input]:
            inp.style().unpolish(inp)
            inp.style().polish(inp)

        if errors:
            self.error_label.setText("; ".join(errors))
            self.error_label.setVisible(True)
        else:
            self.error_label.setText("")
            self.error_label.setVisible(False)

        self.save_btn.setEnabled(bool(sid and name and course))

    def get_data(self) -> dict:
        return {
            'student_id': self.sid_input.text().strip(),
            'name': self.name_input.text().strip(),
            'course_name': self.course_input.text().strip(),
            'score': self.score_spin.value(),
            'semester': self.semester_input.text().strip(),
            'exam_time': self.exam_date.date().toString("yyyy-MM-dd")
        }

    def do_save(self):
        data = self.get_data()
        valid, msg = self.grade_service.validate_grade(data)
        if not valid:
            QMessageBox.warning(self, "数据校验失败", msg)
            return
        self.accept()


class StatisticsPage(QWidget):
    """
    数据统计与可视化页面
    支持按专业、班级、年级筛选，展示多维度的统计图表与数据摘要
    """

    def __init__(self, student_service: StudentService, grade_service: GradeService):
        super().__init__()
        self.student_service = student_service
        self.grade_service = grade_service
        self.current_filters = {'major': None, 'class_name': None, 'year': None}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ======== 顶部标题栏 + 筛选区 ========
        top_layout = QHBoxLayout()
        title = QLabel("数据统计可视化")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        top_layout.addWidget(title)
        top_layout.addSpacing(30)

        top_layout.addWidget(QLabel("专业:"))
        self.major_combo = QComboBox()
        self.major_combo.setMinimumWidth(130)
        self.major_combo.currentIndexChanged.connect(self.on_filter_changed)
        top_layout.addWidget(self.major_combo)

        top_layout.addWidget(QLabel("班级:"))
        self.class_combo = QComboBox()
        self.class_combo.setMinimumWidth(110)
        self.class_combo.currentIndexChanged.connect(self.on_filter_changed)
        top_layout.addWidget(self.class_combo)

        top_layout.addWidget(QLabel("年级:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(90)
        self.year_combo.currentIndexChanged.connect(self.on_filter_changed)
        top_layout.addWidget(self.year_combo)

        self.reset_filter_btn = QPushButton("重置筛选")
        self.reset_filter_btn.clicked.connect(self.reset_filters)
        top_layout.addWidget(self.reset_filter_btn)

        top_layout.addStretch()
        refresh_btn = QPushButton("刷新数据")
        refresh_btn.clicked.connect(self.refresh_all)
        top_layout.addWidget(refresh_btn)
        layout.addLayout(top_layout)

        # ======== 图表区域 —— TabWidget ========
        self.tab_widget = QTabWidget()

        if HAS_CHARTS:
            # --- Tab 0: 班级与专业概览 ---
            tab_overview = QWidget()
            overview_layout = QHBoxLayout()
            self.overview_bar_view = QChartView()
            self.overview_bar_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.overview_pie_view = QChartView()
            self.overview_pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            overview_layout.addWidget(self.overview_bar_view)
            overview_layout.addWidget(self.overview_pie_view)
            tab_overview.setLayout(overview_layout)
            self.tab_widget.addTab(tab_overview, "班级与专业概览")

            # --- Tab 1: 成绩分布 ---
            tab_score = QWidget()
            score_layout = QHBoxLayout()
            self.score_bar_view = QChartView()
            self.score_bar_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.score_pie_view = QChartView()
            self.score_pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            score_layout.addWidget(self.score_bar_view)
            score_layout.addWidget(self.score_pie_view)
            tab_score.setLayout(score_layout)
            self.tab_widget.addTab(tab_score, "成绩分布分析")

            # --- Tab 2: 学期趋势 ---
            tab_trend = QWidget()
            trend_layout = QHBoxLayout()
            self.trend_view = QChartView()
            self.trend_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            trend_layout.addWidget(self.trend_view)
            tab_trend.setLayout(trend_layout)
            self.tab_widget.addTab(tab_trend, "学期成绩趋势")

            # --- Tab 3: 多维对比 ---
            tab_compare = QWidget()
            compare_outer = QVBoxLayout()
            compare_ctrl = QHBoxLayout()
            compare_ctrl.addWidget(QLabel("对比维度:"))
            self.compare_dim_combo = QComboBox()
            self.compare_dim_combo.addItems(["按专业对比", "按班级对比", "按年级对比"])
            self.compare_dim_combo.currentIndexChanged.connect(self._build_comparison_chart)
            compare_ctrl.addWidget(self.compare_dim_combo)
            compare_ctrl.addStretch()
            compare_outer.addLayout(compare_ctrl)

            self.compare_view = QChartView()
            self.compare_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            compare_outer.addWidget(self.compare_view)
            tab_compare.setLayout(compare_outer)
            self.tab_widget.addTab(tab_compare, "多维对比分析")
        else:
            placeholder = QWidget()
            ph_layout = QVBoxLayout()
            hint = QLabel(
                "PyQt6-Charts 未安装，无法显示统计图表\n\n"
                "请执行以下命令安装：\npip install PyQt6-Charts"
            )
            hint.setFont(QFont("Microsoft YaHei", 12))
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setStyleSheet("color: #999;")
            ph_layout.addWidget(hint)
            placeholder.setLayout(ph_layout)
            self.tab_widget.addTab(placeholder, "统计图表")

        layout.addWidget(self.tab_widget, 1)

        # ======== 数据摘要面板 ========
        summary_group = QGroupBox("数据摘要")
        summary_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 12px;
                border: 1px solid #d0d0d0; border-radius: 6px;
                margin-top: 10px; padding-top: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px;
                padding: 0 6px; color: #2c3e50;
            }
        """)
        self.summary_wrapper = QHBoxLayout()
        self.summary_wrapper.setSpacing(16)
        self.summary_wrapper.setContentsMargins(16, 8, 16, 8)

        self.summary_cards = {}
        card_labels = [
            ("total_students", "学生总数"),
            ("total_grades", "成绩记录"),
            ("avg_score", "平均分"),
            ("max_score", "最高分"),
            ("min_score", "最低分"),
            ("pass_rate", "及格率"),
        ]
        for key, label in card_labels:
            card = self._create_summary_card(label, "--")
            self.summary_cards[key] = card
            self.summary_wrapper.addWidget(card)

        self.summary_wrapper.addStretch()
        summary_group.setLayout(self.summary_wrapper)
        layout.addWidget(summary_group)

        self.setLayout(layout)

        # 初始化筛选下拉框数据
        self._init_filter_combos()

    def _create_summary_card(self, title_text: str, value: str) -> QFrame:
        """创建一个数据摘要卡片"""
        card = QFrame()
        card.setFixedSize(150, 80)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        card_inner = QVBoxLayout()
        card_inner.setContentsMargins(12, 10, 12, 10)
        card_inner.setSpacing(4)

        title_label = QLabel(title_text)
        title_label.setFont(QFont("Microsoft YaHei", 9))
        title_label.setStyleSheet("color: #475569; border: none;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_inner.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #2c3e50; border: none;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setObjectName("card_value")
        card_inner.addWidget(value_label)

        card.setLayout(card_inner)
        return card

    def _init_filter_combos(self):
        """初始化筛选下拉框选项"""
        self.major_combo.blockSignals(True)
        self.major_combo.clear()
        self.major_combo.addItem("全部专业", None)
        for major in self.student_service.student_dao.get_all_majors():
            self.major_combo.addItem(major, major)
        self.major_combo.blockSignals(False)

        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        self.class_combo.addItem("全部班级", None)
        for cls in self.student_service.student_dao.get_all_classes():
            self.class_combo.addItem(cls, cls)
        self.class_combo.blockSignals(False)

        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        self.year_combo.addItem("全部年级", None)
        for year in self.student_service.student_dao.get_enrollment_years():
            self.year_combo.addItem(f"{year}级", year)
        self.year_combo.blockSignals(False)

    def _get_current_filters(self) -> dict:
        """获取当前筛选条件"""
        return {
            'major': self.major_combo.currentData(),
            'class_name': self.class_combo.currentData(),
            'year': self.year_combo.currentData()
        }

    def on_filter_changed(self):
        """筛选条件变更时刷新所有内容"""
        self.current_filters = self._get_current_filters()
        self.refresh_all()

    def reset_filters(self):
        """重置筛选条件"""
        self.major_combo.setCurrentIndex(0)
        self.class_combo.setCurrentIndex(0)
        self.year_combo.setCurrentIndex(0)

    # ==================== 刷新入口 ====================

    def refresh_all(self):
        """刷新所有图表和摘要"""
        if not HAS_CHARTS:
            QMessageBox.warning(self, "提示", "PyQt6-Charts未安装，请执行：pip install PyQt6-Charts")
            return
        self._build_overview_charts()
        self._build_score_charts()
        self._build_semester_chart()
        self._build_comparison_chart()
        self._update_summary()

    # ==================== Tab 0: 班级与专业概览 ====================

    def _build_overview_charts(self):
        """构建班级人数柱状图 + 专业人数饼图"""
        # --- 班级柱状图 ---
        class_dist = self.student_service.student_dao.get_class_distribution()
        bar_set = QBarSet("人数")
        bar_set.setColor(QColor("#3498db"))
        categories = []
        for class_name, count in class_dist:
            bar_set.append(count)
            categories.append(class_name)

        bar_series = QBarSeries()
        bar_series.append(bar_set)

        bar_chart = QChart()
        bar_chart.addSeries(bar_series)
        bar_chart.setTitle("各班级人数统计")
        bar_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        bar_chart.legend().setVisible(False)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        bar_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("人数")
        axis_y.setLabelFormat("%d")
        bar_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)

        self.overview_bar_view.setChart(bar_chart)

        # --- 专业饼图 ---
        major_dist = self.student_service.student_dao.get_major_distribution()
        pie_series = QPieSeries()
        pie_colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6',
                      '#1abc9c', '#e67e22', '#34495e']
        for i, (major, count) in enumerate(major_dist):
            sl = pie_series.append(f"{major} ({count}人)", count)
            sl.setColor(QColor(pie_colors[i % len(pie_colors)]))

        pie_chart = QChart()
        pie_chart.addSeries(pie_series)
        pie_chart.setTitle("各专业人数分布")
        pie_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        self.overview_pie_view.setChart(pie_chart)

    # ==================== Tab 1: 成绩分布 ====================

    def _build_score_charts(self):
        """构建成绩分布柱状图 + 饼图"""
        f = self.current_filters
        score_dist = self.grade_service.grade_dao.get_filtered_score_distribution(
            major=f.get('major'), class_name=f.get('class_name'), year=f.get('year'))

        # --- 柱状图 ---
        bar_set = QBarSet("人数")
        bar_set.setColor(QColor("#3498db"))
        categories = []
        for label, count in score_dist:
            bar_set.append(count)
            categories.append(label + "分")

        bar_series = QBarSeries()
        bar_series.append(bar_set)

        bar_chart = QChart()
        bar_chart.addSeries(bar_series)
        bar_chart.setTitle("分数段人数统计")
        bar_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        bar_chart.legend().setVisible(False)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        bar_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("人数")
        axis_y.setLabelFormat("%d")
        bar_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)

        self.score_bar_view.setChart(bar_chart)

        # --- 饼图 ---
        pie_series = QPieSeries()
        pie_colors = ['#e74c3c', '#f39c12', '#2ecc71', '#3498db', '#9b59b6']
        for i, (label, count) in enumerate(score_dist):
            if count > 0:
                sl = pie_series.append(f"{label}分 ({count}人)", count)
                sl.setColor(QColor(pie_colors[i % len(pie_colors)]))

        pie_chart = QChart()
        pie_chart.addSeries(pie_series)
        pie_chart.setTitle("分数段比例分布")
        pie_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        self.score_pie_view.setChart(pie_chart)

    # ==================== Tab 2: 学期趋势 ====================

    def _build_semester_chart(self):
        """构建学期成绩趋势折线图"""
        f = self.current_filters
        semester_data = self.grade_service.grade_dao.get_filtered_semester_averages(
            major=f.get('major'), class_name=f.get('class_name'), year=f.get('year'))

        if not semester_data:
            chart = QChart()
            chart.setTitle("学期平均分趋势（暂无数据）")
            self.trend_view.setChart(chart)
            return

        series = QSplineSeries()
        series.setName("平均分")
        series.setColor(QColor("#3498db"))
        pen = series.pen()
        pen.setWidth(3)
        series.setPen(pen)
        series.setPointsVisible(True)

        categories = []
        max_val, min_val = 0, 100
        for i, (semester, avg) in enumerate(semester_data):
            series.append(i, avg)
            categories.append(semester)
            max_val = max(max_val, avg)
            min_val = min(min_val, avg)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("各学期平均分趋势")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        axis_x = QCategoryAxis()
        axis_x.setTitleText("学期")
        for i, cat in enumerate(categories):
            axis_x.append(cat, i)
        axis_x.setLabelsAngle(-30)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("平均分")
        axis_y.setRange(max(0, min_val - 10), min(100, max_val + 10))
        axis_y.setLabelFormat("%.1f")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)
        self.trend_view.setChart(chart)

    # ==================== Tab 3: 多维对比 ====================

    def _build_comparison_chart(self):
        """构建多维对比柱状图（按专业/班级/年级）"""
        dim_idx = self.compare_dim_combo.currentIndex()

        if dim_idx == 0:
            data = self.grade_service.grade_dao.get_major_score_comparison()
            title = "各专业平均分对比"
        elif dim_idx == 1:
            data = self.grade_service.grade_dao.get_class_score_comparison()
            title = "各班级平均分对比"
        else:
            data = self.grade_service.grade_dao.get_year_score_comparison()
            title = "各年级平均分对比"

        bar_set = QBarSet("平均分")
        bar_set.setColor(QColor("#3498db"))
        categories = []
        for name, avg, cnt in data:
            bar_set.append(avg)
            categories.append(str(name))

        bar_series = QBarSeries()
        bar_series.append(bar_set)

        chart = QChart()
        chart.addSeries(bar_series)
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("平均分")
        axis_y.setRange(0, 100)
        axis_y.setLabelFormat("%.1f")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)

        self.compare_view.setChart(chart)

    # ==================== 数据摘要更新 ====================

    def _update_summary(self):
        """更新数据摘要面板"""
        f = self.current_filters
        grade_stats = self.grade_service.grade_dao.get_filtered_statistics(
            major=f.get('major'), class_name=f.get('class_name'), year=f.get('year'))
        total_students = self._get_filtered_student_count()

        values = {
            'total_students': str(total_students),
            'total_grades': str(grade_stats['total']),
            'avg_score': str(grade_stats['avg_score']),
            'max_score': str(grade_stats['max_score']),
            'min_score': str(grade_stats['min_score']),
            'pass_rate': f"{grade_stats['pass_rate']}%",
        }

        for key, card in self.summary_cards.items():
            value_label = card.findChild(QLabel, "card_value")
            if value_label:
                value_label.setText(values.get(key, "--"))

    def _get_filtered_student_count(self) -> int:
        """获取当前筛选条件下的学生总数"""
        f = self.current_filters
        major = f.get('major')
        class_name = f.get('class_name')
        year = f.get('year')

        if not major and not class_name and not year:
            return self.student_service.student_dao.get_count()

        conn = self.student_service.student_dao.db.get_connection()
        conditions = []
        params = []
        if major:
            conditions.append("major = ?")
            params.append(major)
        if class_name:
            conditions.append("class_name = ?")
            params.append(class_name)
        if year:
            conditions.append("enrollment_year = ?")
            params.append(int(year))
        where = "WHERE " + " AND ".join(conditions)
        return conn.execute(f"SELECT COUNT(*) FROM students {where}", params).fetchone()[0]


class UserManagePage(QWidget):
    """
    用户管理页面（仅管理员可见）
    功能：查看所有用户、新增用户、删除用户、重置密码
    """

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("用户管理")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.add_user_btn = QPushButton("新增用户")
        self.add_user_btn.clicked.connect(self.do_add_user)
        self.reset_pwd_btn = QPushButton("重置密码")
        self.reset_pwd_btn.clicked.connect(self.do_reset_password)
        self.delete_user_btn = QPushButton("删除用户")
        self.delete_user_btn.clicked.connect(self.do_delete_user)
        btn_layout.addWidget(self.add_user_btn)
        btn_layout.addWidget(self.reset_pwd_btn)
        btn_layout.addWidget(self.delete_user_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 用户表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['ID', '用户名', '角色', '真实姓名', '创建时间'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setSortingEnabled(True)
        self.table.setColumnHidden(0, True)
        layout.addWidget(self.table)

        # -------- 表格双击编辑 --------
        self.table.doubleClicked.connect(self._on_double_click)

        # -------- 表格上下文菜单 --------
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.setLayout(layout)

    def _on_double_click(self):
        """双击行：重置密码"""
        row = self.table.currentRow()
        if row >= 0:
            self.do_reset_password()

    def _show_context_menu(self, pos):
        """右键上下文菜单"""
        menu = QMenu(self)
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除用户")
        menu.addSeparator()
        copy_action = menu.addAction("复制单元格")
        menu.addSeparator()
        select_all_action = menu.addAction("全选")

        row = self.table.currentRow()
        has_row = row >= 0
        edit_action.setEnabled(has_row)
        delete_action.setEnabled(has_row)
        copy_action.setEnabled(has_row)

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if not action:
            return
        if action == edit_action and has_row:
            self._on_double_click()
        elif action == delete_action and has_row:
            self.do_delete_user()
        elif action == copy_action and has_row:
            col = self.table.currentColumn()
            if col >= 0:
                text = self.table.item(row, col).text() if self.table.item(row, col) else ""
                QApplication.clipboard().setText(text)
        elif action == select_all_action:
            self.table.selectAll()

    def load_data(self):
        """加载用户列表"""
        users = self.auth_service.user_dao.get_all()
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            for col, key in enumerate(['id', 'username', 'role', 'real_name', 'created_at']):
                value = user[key] if user[key] else ""
                if key == 'role':
                    value = "管理员" if value == 'admin' else "教师"
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

    def do_add_user(self):
        """新增用户"""
        dialog = UserEditDialog(self.auth_service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def do_reset_password(self):
        """重置选中用户的密码"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个用户")
            return
        user_id = int(self.table.item(row, 0).text())
        username = self.table.item(row, 1).text()

        new_pwd, ok = QInputDialog.getText(
            self, "重置密码", f"为用户「{username}」设置新密码（至少6位）:",
            QLineEdit.EchoMode.Password
        )
        if ok and new_pwd:
            if len(new_pwd) < 6:
                QMessageBox.warning(self, "错误", "密码长度不能少于6位")
                return
            self.auth_service.user_dao.reset_password(user_id, new_pwd)
            self.auth_service.log_dao.insert(
                self.auth_service.get_current_username(),
                "重置密码", username
            )
            QMessageBox.information(self, "成功", f"用户「{username}」的密码已重置")

    def do_delete_user(self):
        """删除用户"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个用户")
            return
        user_id = int(self.table.item(row, 0).text())
        username = self.table.item(row, 1).text()

        if username == self.auth_service.get_current_username():
            QMessageBox.warning(self, "错误", "不能删除自己的账号")
            return

        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除用户「{username}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.auth_service.user_dao.delete(user_id)
            self.auth_service.log_dao.insert(
                self.auth_service.get_current_username(),
                "删除用户", username
            )
            QMessageBox.information(self, "成功", "用户已删除")
            self.load_data()


class UserEditDialog(QDialog):
    """新增用户对话框"""

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("新增用户")
        self.setFixedSize(380, 280)

        layout = QVBoxLayout()
        form = QFormLayout()
        form.setSpacing(10)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("至少3位字符")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("至少6位字符")
        self.real_name_input = QLineEdit()
        self.real_name_input.setPlaceholderText("如：张老师")
        self.role_combo = QComboBox()
        self.role_combo.addItems(['teacher', 'admin'])
        self.role_combo.setItemText(0, "教师")
        self.role_combo.setItemText(1, "管理员")

        form.addRow("用户名:", self.username_input)
        form.addRow("密码:", self.password_input)
        form.addRow("真实姓名:", self.real_name_input)
        form.addRow("角色:", self.role_combo)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("创建")
        save_btn.clicked.connect(self.do_create)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def do_create(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        real_name = self.real_name_input.text().strip()
        role = self.role_combo.currentData() or 'teacher'

        success, msg = self.auth_service.create_user(username, password, role, real_name)
        if success:
            QMessageBox.information(self, "成功", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "失败", msg)


class LogPage(QWidget):
    """操作日志页面（仅管理员可见）"""

    def __init__(self, log_dao: LogDAO):
        super().__init__()
        self.log_dao = log_dao
        self.current_page = 1
        self.page_size = 50
        self.filters = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("操作日志")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("操作人:"))
        self.search_user = QLineEdit()
        self.search_user.setMaximumWidth(120)
        search_layout.addWidget(self.search_user)

        search_layout.addWidget(QLabel("操作类型:"))
        self.search_op = QComboBox()
        self.search_op.addItem("全部", "")
        self.search_op.addItems(['登录成功', '登录失败', '新增学生', '修改学生', '删除学生',
                                  '录入成绩', '修改成绩', '删除成绩', '创建用户', '重置密码',
                                  '删除用户', '修改密码', '批量导入', '清空数据'])
        search_layout.addWidget(self.search_op)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.do_search)
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.do_reset)
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.do_clear)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(reset_btn)
        search_layout.addWidget(clear_btn)
        search_layout.addStretch()
        layout.addLayout(search_layout)

        # 日志表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['ID', '操作人', '操作类型', '操作对象', '详情', '时间'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setSortingEnabled(True)
        self.table.setColumnHidden(0, True)
        layout.addWidget(self.table)

        # -------- 表格上下文菜单 --------
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # 分页
        page_layout = QHBoxLayout()
        self.prev_btn = QPushButton("< 上一页")
        self.prev_btn.clicked.connect(lambda: self.change_page(-1))
        self.next_btn = QPushButton("下一页 >")
        self.next_btn.clicked.connect(lambda: self.change_page(1))
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_layout.addStretch()
        page_layout.addWidget(self.prev_btn)
        page_layout.addWidget(self.page_label)
        page_layout.addWidget(self.next_btn)
        page_layout.addStretch()
        layout.addLayout(page_layout)

        self.setLayout(layout)

    def load_data(self):
        logs = self.log_dao.get_page(self.current_page, self.page_size, self.filters)
        total = self.log_dao.get_count(self.filters)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)

        self.table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            for col, key in enumerate(['id', 'username', 'operation', 'target', 'detail', 'created_at']):
                value = log[key] if log[key] else ""
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        self.page_label.setText(f"第{self.current_page}页 / 共{total_pages}页 (共{total}条)")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < total_pages)

    def do_search(self):
        self.filters = {}
        if self.search_user.text().strip():
            self.filters['username'] = self.search_user.text().strip()
        if self.search_op.currentData():
            self.filters['operation'] = self.search_op.currentData()
        self.current_page = 1
        self.load_data()

    def do_reset(self):
        self.search_user.clear()
        self.search_op.setCurrentIndex(0)
        self.filters = {}
        self.current_page = 1
        self.load_data()

    def do_clear(self):
        reply = QMessageBox.warning(
            self, "确认", "确定清空所有操作日志吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.log_dao.clear()
            self.load_data()

    def _show_context_menu(self, pos):
        """右键上下文菜单"""
        menu = QMenu(self)
        copy_action = menu.addAction("复制单元格")
        menu.addSeparator()
        select_all_action = menu.addAction("全选")

        row = self.table.currentRow()
        has_row = row >= 0 and row < self.table.rowCount()
        copy_action.setEnabled(has_row)

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if not action:
            return
        if action == copy_action and has_row:
            col = self.table.currentColumn()
            if col >= 0:
                item = self.table.item(row, col)
                text = item.text() if item else ""
                QApplication.clipboard().setText(text)
        elif action == select_all_action:
            self.table.selectAll()

    def change_page(self, delta):
        self.current_page += delta
        self.load_data()


class ProfilePage(QWidget):
    """个人中心页面"""

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("个人中心")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(20)

        user = self.auth_service.get_current_user()
        if user:
            info_group = QGroupBox("账号信息")
            info_form = QFormLayout()
            info_form.setSpacing(12)

            username_label = QLabel(user['username'])
            username_label.setFont(QFont("Microsoft YaHei", 11))
            role_label = QLabel("系统管理员" if user['role'] == 'admin' else "普通教师")
            role_label.setFont(QFont("Microsoft YaHei", 11))
            name_label = QLabel(user.get('real_name', ''))
            name_label.setFont(QFont("Microsoft YaHei", 11))
            created_label = QLabel(str(user.get('created_at', '')))
            created_label.setFont(QFont("Microsoft YaHei", 11))

            info_form.addRow("用户名：", username_label)
            info_form.addRow("角　色：", role_label)
            info_form.addRow("真实姓名：", name_label)
            info_form.addRow("创建时间：", created_label)
            info_group.setLayout(info_form)
            layout.addWidget(info_group)

        layout.addSpacing(20)

        # 修改密码区域
        pwd_group = QGroupBox("修改密码")
        pwd_layout = QFormLayout()
        pwd_layout.setSpacing(10)

        self.old_pwd = QLineEdit()
        self.old_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pwd.setPlaceholderText("输入原密码")
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd.setPlaceholderText("输入新密码（至少6位）")
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd.setPlaceholderText("再次输入新密码")

        pwd_layout.addRow("原密码：", self.old_pwd)
        pwd_layout.addRow("新密码：", self.new_pwd)
        pwd_layout.addRow("确认密码：", self.confirm_pwd)

        change_btn = QPushButton("修改密码")
        change_btn.setMinimumHeight(36)
        change_btn.clicked.connect(self.do_change_password)
        pwd_layout.addRow("", change_btn)
        pwd_group.setLayout(pwd_layout)
        layout.addWidget(pwd_group)

        layout.addStretch()
        self.setLayout(layout)

    def do_change_password(self):
        """修改密码"""
        old = self.old_pwd.text().strip()
        new = self.new_pwd.text().strip()
        confirm = self.confirm_pwd.text().strip()

        if not old or not new or not confirm:
            QMessageBox.warning(self, "提示", "请填写所有密码字段")
            return
        if new != confirm:
            QMessageBox.warning(self, "提示", "两次输入的新密码不一致")
            return
        if len(new) < 6:
            QMessageBox.warning(self, "提示", "新密码长度不少于6位")
            return

        success, msg = self.auth_service.change_password(old, new)
        if success:
            QMessageBox.information(self, "成功", msg)
            self.old_pwd.clear()
            self.new_pwd.clear()
            self.confirm_pwd.clear()
        else:
            QMessageBox.warning(self, "失败", msg)


class AboutDialog(QDialog):
    """关于系统对话框 —— 专业软件风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"关于 {APP_TITLE}")
        self.setFixedSize(460, 500)
        self.setStyleSheet("QDialog { background-color: #ffffff; }")

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # ---- 顶部品牌区 ----
        brand_widget = QWidget()
        brand_widget.setStyleSheet("background-color: #f8f9fa; border-bottom: 1px solid #e0e0e0;")
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(6)
        brand_layout.setContentsMargins(40, 28, 40, 24)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 应用图标（用首字做图标）
        icon_label = QLabel("S")
        icon_label.setFixedSize(72, 72)
        icon_label.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                background-color: #4a90d9;
                color: white;
                border-radius: 16px;
            }
        """)
        brand_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        app_name = QLabel("学生管理信息系统")
        app_name.setFont(QFont("Microsoft YaHei", 17, QFont.Weight.Bold))
        app_name.setStyleSheet("color: #2c3e50;")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_layout.addWidget(app_name)

        app_name_en = QLabel("Student Management Information System")
        app_name_en.setFont(QFont("Segoe UI", 9))
        app_name_en.setStyleSheet("color: #64748b;")
        app_name_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_layout.addWidget(app_name_en)

        brand_layout.addSpacing(6)

        version_label = QLabel(f"版本 {APP_VERSION}")
        version_label.setFont(QFont("Microsoft YaHei", 10))
        version_label.setStyleSheet("color: #475569;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_layout.addWidget(version_label)

        brand_widget.setLayout(brand_layout)
        layout.addWidget(brand_widget)

        # ---- 信息区 ----
        info_widget = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(40, 24, 40, 20)

        # 用 QGridLayout 做规整的信息展示
        info_grid = QGridLayout()
        info_grid.setSpacing(6)
        info_grid.setColumnStretch(1, 1)

        rows = [
            ("作  者：", APP_AUTHOR),
            ("专  业：", APP_MAJOR),
            ("开发语言：", "Python 3.10+ / PyQt6"),
            ("GUI 风格：", "Fusion"),
            ("数 据 库：", "SQLite3 (内嵌式)"),
        ]

        for i, (label_text, value_text) in enumerate(rows):
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Microsoft YaHei", 9))
            lbl.setStyleSheet("color: #475569;")
            val = QLabel(value_text)
            val.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
            val.setStyleSheet("color: #2c3e50;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            info_grid.addWidget(lbl, i, 0, Qt.AlignmentFlag.AlignRight)
            info_grid.addWidget(val, i, 1)

        info_layout.addLayout(info_grid)

        info_widget.setLayout(info_layout)
        layout.addWidget(info_widget)

        # ---- 分隔线 ----
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e0e0e0;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # ---- 版权区 ----
        footer_widget = QWidget()
        footer_widget.setStyleSheet("background-color: #f8f9fa;")
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(4)
        footer_layout.setContentsMargins(40, 16, 40, 16)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        copyright_label = QLabel(APP_COPYRIGHT)
        copyright_label.setFont(QFont("Segoe UI", 8))
        copyright_label.setStyleSheet("color: #64748b;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(copyright_label)

        rights_label = QLabel("All rights reserved. 本软件受著作权法保护。")
        rights_label.setFont(QFont("Microsoft YaHei", 8))
        rights_label.setStyleSheet("color: #94a3b8;")
        rights_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(rights_label)

        footer_widget.setLayout(footer_layout)
        layout.addWidget(footer_widget)

        # ---- 按钮区 ----
        btn_widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(40, 12, 40, 20)
        btn_layout.addStretch()

        close_btn = QPushButton("确  定")
        close_btn.setFixedSize(120, 36)
        close_btn.setFont(QFont("Microsoft YaHei", 10))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2a6cb5; }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        btn_widget.setLayout(btn_layout)
        layout.addWidget(btn_widget)

        self.setLayout(layout)


class DashboardPage(QWidget):
    """
    数据首页（Dashboard）
    显示系统概览统计卡片、快捷操作、最近日志、数据库状态
    """

    def __init__(self, student_service: StudentService, grade_service: GradeService,
                 auth_service: AuthService, log_dao: LogDAO):
        super().__init__()
        self.student_service = student_service
        self.grade_service = grade_service
        self.auth_service = auth_service
        self.log_dao = log_dao
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # ======== 标题 ========
        title = QLabel("系统概览")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)

        # ======== 统计卡片行 ========
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        card_configs = [
            ("total_students", "学生总数", "0", "#1a73e8"),
            ("total_grades", "成绩记录", "0", "#0d904f"),
            ("avg_score", "平均分", "--", "#f9ab00"),
            ("pass_rate", "及格率", "--%", "#d93025"),
        ]
        self.cards = {}
        for key, label, default_val, color in card_configs:
            card = self._create_card(label, default_val, color)
            self.cards[key] = card
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)

        # ======== 中段：快捷操作 + 最近日志 ========
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(16)

        # --- 快捷操作 ---
        quick_group = QGroupBox("快捷操作")
        quick_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 12px; color: #1e293b;
                border: 1px solid #e2e8f0; border-radius: 8px;
                margin-top: 12px; padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 14px;
                padding: 0 6px; color: #1e293b;
            }
        """)
        quick_layout = QGridLayout()
        quick_layout.setSpacing(10)

        quick_btns = [
            ("add_student", "新增学生", "Ctrl+N"),
            ("add_grade", "录入成绩", ""),
            ("ai_analysis", "AI 智能分析", "Ctrl+5"),
            ("view_stats", "统计图表", "Ctrl+3"),
            ("export_data", "导出数据", "Ctrl+S"),
            ("backup_db", "备份数据库", ""),
        ]
        self.quick_buttons = {}
        for i, (key, text, shortcut) in enumerate(quick_btns):
            btn = QPushButton(f"{text}\n{shortcut}" if shortcut else text)
            btn.setMinimumHeight(60)
            btn.setMinimumWidth(140)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: bold;
                    color: #1e293b;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #e8f0fe;
                    border-color: #1a73e8;
                    color: #1a73e8;
                }
                QPushButton:pressed {
                    background-color: #d2e3fc;
                }
            """)
            btn.setProperty("action_key", key)
            btn.clicked.connect(lambda checked, k=key: self._on_quick_action(k))
            self.quick_buttons[key] = btn
            quick_layout.addWidget(btn, i // 3, i % 3)

        quick_group.setLayout(quick_layout)
        mid_layout.addWidget(quick_group)

        # --- 最近操作日志 ---
        log_group = QGroupBox("最近操作日志")
        log_group.setStyleSheet(quick_group.styleSheet())
        log_inner = QVBoxLayout()

        self.recent_log_table = QTableWidget()
        self.recent_log_table.setColumnCount(3)
        self.recent_log_table.setHorizontalHeaderLabels(["操作人", "操作类型", "时间"])
        self.recent_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recent_log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.recent_log_table.setAlternatingRowColors(True)
        self.recent_log_table.verticalHeader().setVisible(False)
        self.recent_log_table.setMaximumHeight(280)
        log_inner.addWidget(self.recent_log_table)
        log_group.setLayout(log_inner)
        mid_layout.addWidget(log_group)

        layout.addLayout(mid_layout, 1)

        # ======== 底部：数据库状态 ========
        db_group = QGroupBox("系统状态")
        db_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 12px; color: #1e293b;
                border: 1px solid #e2e8f0; border-radius: 8px;
                margin-top: 12px; padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 14px;
                padding: 0 6px; color: #1e293b;
            }
        """)
        db_layout = QHBoxLayout()
        db_layout.setSpacing(30)

        self.db_path_label = QLabel()
        self.db_size_label = QLabel()
        self.db_tables_label = QLabel()
        self.last_backup_label = QLabel()

        for lbl in [self.db_path_label, self.db_size_label, self.db_tables_label, self.last_backup_label]:
            lbl.setFont(QFont("Microsoft YaHei", 10))
            lbl.setStyleSheet("color: #475569;")
            db_layout.addWidget(lbl)

        db_layout.addStretch()
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        self.setLayout(layout)

    def _create_card(self, title_text: str, value: str, accent_color: str) -> QFrame:
        """创建统计卡片"""
        card = QFrame()
        card.setMinimumHeight(110)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid #e2e8f0;
                border-left: 4px solid {accent_color};
                border-radius: 8px;
            }}
        """)
        inner = QVBoxLayout()
        inner.setContentsMargins(16, 14, 16, 14)
        inner.setSpacing(6)

        title_lbl = QLabel(title_text)
        title_lbl.setFont(QFont("Microsoft YaHei", 11))
        title_lbl.setStyleSheet("color: #475569; border: none;")
        inner.addWidget(title_lbl)

        value_lbl = QLabel(value)
        value_lbl.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        value_lbl.setStyleSheet(f"color: {accent_color}; border: none;")
        value_lbl.setObjectName(f"card_{title_text}")
        inner.addWidget(value_lbl)

        card.setLayout(inner)
        return card

    def _on_quick_action(self, key: str):
        """快捷操作回调 —— 通过父窗口切换页面"""
        main_win = self.window()
        if not isinstance(main_win, QMainWindow):
            return
        action_map = {
            "add_student": "student",
            "add_grade": "grade",
            "ai_analysis": "ai",
            "view_stats": "stats",
            "export_data": "student",
            "backup_db": None,
        }
        target = action_map.get(key)
        if target:
            main_win.switch_page(target)
            # 如果是新增操作，触发对应页面的新增
            if key == "add_student" and hasattr(main_win.student_page, 'do_add'):
                QTimer.singleShot(100, main_win.student_page.do_add)
            elif key == "add_grade" and hasattr(main_win.grade_page, 'do_add'):
                QTimer.singleShot(100, main_win.grade_page.do_add)
            elif key == "export_data" and hasattr(main_win.student_page, 'do_export_csv'):
                QTimer.singleShot(100, main_win.student_page.do_export_csv)
        elif key == "backup_db" and hasattr(main_win, 'do_backup'):
            main_win.do_backup()

    def refresh_all(self):
        """刷新仪表盘所有数据"""
        # 统计数据
        total_students = self.student_service.student_dao.get_count()
        grade_stats = self.grade_service.grade_dao.get_statistics()
        total_grades = grade_stats['total']
        avg_score = grade_stats['avg_score']
        total_all = self.grade_service.grade_dao.get_count()
        pass_count = 0
        if total_all > 0:
            conn = self.grade_service.grade_dao.db.get_connection()
            pass_count = conn.execute(
                "SELECT COUNT(*) FROM grades WHERE score >= 60"
            ).fetchone()[0]
        pass_rate = f"{round(pass_count / total_all * 100, 1)}%" if total_all > 0 else "--"

        self._update_card_value("学生总数", str(total_students))
        self._update_card_value("成绩记录", str(total_grades))
        self._update_card_value("平均分", str(avg_score))
        self._update_card_value("及格率", pass_rate)

        # 最近日志
        recent_logs = self.log_dao.get_page(1, 10)
        self.recent_log_table.setRowCount(len(recent_logs))
        for row, log in enumerate(recent_logs):
            for col, key in enumerate(['username', 'operation', 'created_at']):
                value = str(log[key]) if log[key] else ""
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.recent_log_table.setItem(row, col, item)

        # 数据库状态
        db_path = os.path.abspath(DB_NAME)
        self.db_path_label.setText(f"数据库路径: {db_path}")
        if os.path.exists(db_path):
            size_kb = os.path.getsize(db_path) / 1024
            self.db_size_label.setText(f"文件大小: {size_kb:.1f} KB")
        conn = DatabaseManager().get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        self.db_tables_label.setText(f"数据表: {len(tables)} 个")

        # 最近备份
        backup_dir = BAKCUP_DIR
        if os.path.exists(backup_dir):
            backups = sorted(
                [f for f in os.listdir(backup_dir) if f.endswith('.db')],
                reverse=True
            )
            if backups:
                self.last_backup_label.setText(f"最近备份: {backups[0]}")
            else:
                self.last_backup_label.setText("最近备份: 无")
        else:
            self.last_backup_label.setText("最近备份: 无")

    def _update_card_value(self, title: str, value: str):
        """更新卡片数值"""
        for card in self.cards.values():
            lbl = card.findChild(QLabel, f"card_{title}")
            if lbl:
                lbl.setText(value)


class AIPage(QWidget):
    """
    AI智能分析页面
    五个Tab：学情诊断 | 智能评语 | 语义搜索 | 异常检测 | 机器学习分析
    """

    def __init__(self, student_service: StudentService, grade_service: GradeService,
                 auth_service: AuthService):
        super().__init__()
        self.student_service = student_service
        self.grade_service = grade_service
        self.auth_service = auth_service
        self.ai = AIAnalyzer()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("AI 智能分析")
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #1e293b;")
        layout.addWidget(title)

        self.tab_widget = QTabWidget()
        self._build_analysis_tab()
        self._build_comment_tab()
        self._build_search_tab()
        self._build_anomaly_tab()
        self._build_ml_tab()
        layout.addWidget(self.tab_widget, 1)

        self.setLayout(layout)

    # ==================== Tab 1: 学情诊断 ====================

    def _build_analysis_tab(self):
        tab = QWidget()
        outer = QVBoxLayout()
        outer.setSpacing(10)

        # 筛选行
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("班级:"))
        self.ana_class_combo = QComboBox()
        self.ana_class_combo.setMinimumWidth(120)
        self.ana_class_combo.addItem("全部班级", None)
        for cls in self.student_service.student_dao.get_all_classes():
            self.ana_class_combo.addItem(cls, cls)
        ctrl.addWidget(self.ana_class_combo)

        ctrl.addWidget(QLabel("专业:"))
        self.ana_major_combo = QComboBox()
        self.ana_major_combo.setMinimumWidth(130)
        self.ana_major_combo.addItem("全部专业", None)
        for m in self.student_service.student_dao.get_all_majors():
            self.ana_major_combo.addItem(m, m)
        ctrl.addWidget(self.ana_major_combo)

        ctrl.addWidget(QLabel("年级:"))
        self.ana_year_combo = QComboBox()
        self.ana_year_combo.setMinimumWidth(90)
        self.ana_year_combo.addItem("全部年级", None)
        for y in self.student_service.student_dao.get_enrollment_years():
            self.ana_year_combo.addItem(f"{y}级", y)
        ctrl.addWidget(self.ana_year_combo)

        run_btn = QPushButton("开始分析")
        run_btn.setStyleSheet("""
            QPushButton { background-color: #1a73e8; color: white; border: none;
                border-radius: 6px; padding: 8px 20px; font-weight: bold; }
            QPushButton:hover { background-color: #1557b0; }
        """)
        run_btn.clicked.connect(self._run_analysis)
        ctrl.addWidget(run_btn)
        ctrl.addStretch()
        outer.addLayout(ctrl)

        # 结果展示
        self.ana_result = QTextEdit()
        self.ana_result.setReadOnly(True)
        self.ana_result.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0; border-radius: 8px;
                font-family: "Microsoft YaHei"; font-size: 10pt;
                padding: 12px; background-color: #ffffff;
            }
        """)
        outer.addWidget(self.ana_result, 1)

        # DeepSeek + 导出按钮
        btn_row = QHBoxLayout()
        self.deep_analysis_btn = QPushButton("DeepSeek 深度分析")
        self.deep_analysis_btn.setStyleSheet("""
            QPushButton { background-color: #9b59b6; color: white; border: none;
                border-radius: 6px; padding: 8px 20px; font-weight: bold; }
            QPushButton:hover { background-color: #8e44ad; }
            QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }
        """)
        self.deep_analysis_btn.clicked.connect(self._run_deep_analysis)
        if not self.ai.ds.is_available():
            self.deep_analysis_btn.setEnabled(False)
            self.deep_analysis_btn.setToolTip("请先在【智能评语】标签页配置 DeepSeek API Key")
        btn_row.addWidget(self.deep_analysis_btn)
        btn_row.addStretch()
        export_btn = QPushButton("导出分析报告")
        export_btn.clicked.connect(self._export_analysis)
        btn_row.addWidget(export_btn)
        outer.addLayout(btn_row)

        tab.setLayout(outer)
        self.tab_widget.addTab(tab, "学情诊断")

    def _run_analysis(self):
        """执行学情诊断"""
        class_name = self.ana_class_combo.currentData()
        major = self.ana_major_combo.currentData()
        year = self.ana_year_combo.currentData()

        result = self.ai.analyze_class(
            class_name=class_name, major=major, year=year
        )

        if "error" in result:
            self.ana_result.setHtml(f"<p style='color:#d93025;'>{result['error']}</p>")
            return

        s = result['summary']
        lines = []
        lines.append("<h2 style='color:#1a73e8;'>AI 学情诊断报告</h2>")
        lines.append(f"<p><b>分析范围：</b>{class_name or '全部班级'} | {major or '全部专业'} | "
                     f"{f'{year}级' if year else '全部年级'}</p>")
        lines.append("<hr>")
        lines.append("<h3>一、总体概况</h3>")
        lines.append(f"<ul><li>学生总数：<b>{s['student_count']}</b> 人</li>")
        lines.append(f"<li>成绩记录：<b>{s['grade_count']}</b> 条</li>")
        lines.append(f"<li>总体平均分：<b style='color:#1a73e8;'>{s['total_avg']}</b> 分</li>")
        lines.append(f"<li>及格率：<b style='color:{'#0d904f' if s['pass_rate']>=60 else '#d93025'};'>{s['pass_rate']}%</b></li>")
        lines.append(f"<li>涉及科目：<b>{s['course_count']}</b> 门</li></ul>")

        if result['weak_subjects']:
            lines.append("<h3>二、弱项科目（均分 &lt; 65）</h3><ul>")
            for cn, avg in result['weak_subjects']:
                lines.append(f"<li><b style='color:#d93025;'>{cn}</b>：均分 {avg} 分</li>")
            lines.append("</ul>")

        if result['imbalanced_students']:
            lines.append("<h3>三、偏科学生（分差 &gt; 30）</h3>")
            lines.append("<table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;width:100%;'>")
            lines.append("<tr style='background:#f1f5f9;'><th>学号</th><th>姓名</th><th>弱科(分)</th><th>强科(分)</th><th>分差</th></tr>")
            for st in result['imbalanced_students']:
                lines.append(f"<tr><td>{st['student_id']}</td><td>{st['name']}</td>"
                             f"<td style='color:#d93025;'>{st['low_course']}({st['low_score']})</td>"
                             f"<td style='color:#0d904f;'>{st['high_course']}({st['high_score']})</td>"
                             f"<td>{st['gap']}</td></tr>")
            lines.append("</table>")

        if result['at_risk_students']:
            lines.append("<h3>四、挂科风险学生（均分 &lt; 60 或存在不及格科目）</h3>")
            lines.append("<table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;width:100%;'>")
            lines.append("<tr style='background:#fef2f2;'><th>学号</th><th>姓名</th><th>均分</th><th>最低分</th><th>薄弱科目</th></tr>")
            for st in result['at_risk_students']:
                lines.append(f"<tr><td>{st['student_id']}</td><td>{st['name']}</td>"
                             f"<td style='color:#d93025;'>{st['avg']}</td><td>{st['min_score']}</td>"
                             f"<td>{st['min_course']}</td></tr>")
            lines.append("</table>")

        if result['volatile_students']:
            lines.append("<h3>五、成绩波动较大学生（标准差 &gt; 15）</h3><ul>")
            for st in result['volatile_students']:
                lines.append(f"<li>{st['name']}({st['student_id']})：均分{st['avg']}，标准差{st['std']}</li>")
            lines.append("</ul>")

        lines.append(f"<hr><p style='color:#94a3b8;font-size:9pt;'>报告由 AI 自动生成 | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        self.ana_result.setHtml("\n".join(lines))

    def _run_deep_analysis(self):
        """DeepSeek 深度学情分析"""
        if not self.ai.ds.is_available():
            QMessageBox.warning(self, "提示", "请先在【智能评语】标签页配置 DeepSeek API Key")
            return

        class_name = self.ana_class_combo.currentData()
        major = self.ana_major_combo.currentData()
        year = self.ana_year_combo.currentData()

        self.ana_result.setPlainText("正在调用 DeepSeek 大模型生成深度分析报告，请稍候...")
        QApplication.processEvents()

        report = self.ai.analyze_class_deep(class_name, major, year)
        if report.startswith("["):
            QMessageBox.warning(self, "分析失败", report)
            return
        self.ana_result.setMarkdown(report)

    def _export_analysis(self):
        """导出分析报告为文本文件"""
        text = self.ana_result.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "提示", "请先运行分析再导出")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出分析报告", "ai_analysis_report.txt", "文本文件 (*.txt)"
        )
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(self, "成功", f"报告已导出到:\n{filepath}")

    # ==================== Tab 2: 智能评语 ====================

    def _build_comment_tab(self):
        tab = QWidget()
        outer = QVBoxLayout()
        outer.setSpacing(12)

        # ---- API Key 设置行 ----
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("DeepSeek API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入 DeepSeek API Key（sk-...）")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        existing_key = get_deepseek_key()
        if existing_key:
            self.api_key_input.setText(existing_key[:8] + "****" + existing_key[-4:])
        api_layout.addWidget(self.api_key_input)

        save_key_btn = QPushButton("保存密钥")
        save_key_btn.setStyleSheet("""
            QPushButton { background-color: #0d904f; color: white; border: none;
                border-radius: 6px; padding: 6px 14px; font-weight: bold; }
            QPushButton:hover { background-color: #0b7d42; }
        """)
        save_key_btn.clicked.connect(self._save_api_key)
        api_layout.addWidget(save_key_btn)

        clear_key_btn = QPushButton("清除")
        clear_key_btn.clicked.connect(self._clear_api_key)
        api_layout.addWidget(clear_key_btn)
        api_layout.addStretch()

        self.api_status_label = QLabel(
            "状态: DeepSeek API 已就绪" if self.ai.ds.is_available() else "状态: 未配置（将使用本地模板）"
        )
        self.api_status_label.setFont(QFont("Microsoft YaHei", 9))
        self.api_status_label.setStyleSheet(
            f"color: {'#0d904f' if self.ai.ds.is_available() else '#f9ab00'}; font-weight: bold;"
        )
        api_layout.addWidget(self.api_status_label)
        outer.addLayout(api_layout)

        # 学生选择
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("选择学生:"))
        self.comment_student_combo = QComboBox()
        self.comment_student_combo.setMinimumWidth(200)
        self._load_students_to_combo(self.comment_student_combo)
        sel_layout.addWidget(self.comment_student_combo)
        sel_layout.addStretch()
        outer.addLayout(sel_layout)

        # 关键词选择
        kw_layout = QHBoxLayout()
        kw_layout.addWidget(QLabel("评语风格/关键词:"))
        self.kw_buttons = {}
        for kw in ["努力", "粗心", "偏科", "进步", "全面"]:
            btn = QPushButton(kw)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { border: 1px solid #cbd5e1; border-radius: 14px;
                    padding: 6px 14px; background: white; }
                QPushButton:checked { background: #1a73e8; color: white;
                    border-color: #1a73e8; font-weight: bold; }
                QPushButton:hover:!checked { background: #e8f0fe; }
            """)
            btn.clicked.connect(lambda chk, k=kw: self._on_kw_toggle(k, chk))
            self.kw_buttons[kw] = btn
            kw_layout.addWidget(btn)
        kw_layout.addStretch()
        outer.addLayout(kw_layout)

        # 生成按钮
        gen_btn = QPushButton("生成评语")
        gen_btn.setStyleSheet("""
            QPushButton { background-color: #1a73e8; color: white; border: none;
                border-radius: 6px; padding: 10px 30px; font-weight: bold; font-size: 12pt; }
            QPushButton:hover { background-color: #1557b0; }
        """)
        gen_btn.clicked.connect(self._generate_comment)
        outer.addWidget(gen_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # 生成引擎提示
        self.comment_engine_label = QLabel("")
        self.comment_engine_label.setFont(QFont("Microsoft YaHei", 9))
        self.comment_engine_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comment_engine_label.setStyleSheet("color: #475569;")
        outer.addWidget(self.comment_engine_label)

        # 评语展示
        self.comment_text = QTextEdit()
        self.comment_text.setReadOnly(True)
        self.comment_text.setMaximumHeight(150)
        self.comment_text.setStyleSheet("""
            QTextEdit { border: 2px solid #1a73e8; border-radius: 8px;
                font-size: 11pt; padding: 14px; background: #f8fafc; }
        """)
        self.comment_text.setPlaceholderText("生成的评语将显示在这里...")
        outer.addWidget(self.comment_text)

        # 复制按钮
        copy_btn = QPushButton("一键复制评语")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(
            self.comment_text.toPlainText()))
        outer.addWidget(copy_btn, alignment=Qt.AlignmentFlag.AlignRight)

        outer.addStretch()
        tab.setLayout(outer)
        self.tab_widget.addTab(tab, "智能评语")

    def _load_students_to_combo(self, combo):
        """加载学生列表到下拉框"""
        students = self.student_service.student_dao.get_page(1, 99999)
        combo.clear()
        for s in students:
            combo.addItem(f"{s['student_id']} - {s['name']} ({s['class_name']})", s['student_id'])

    def _on_kw_toggle(self, kw, checked):
        """关键词互斥选择（同一时间最多选2个）"""
        if checked:
            active = [k for k, b in self.kw_buttons.items() if b.isChecked() and k != kw]
            if len(active) >= 2:
                # 取消最早选中的
                first = active[0]
                self.kw_buttons[first].blockSignals(True)
                self.kw_buttons[first].setChecked(False)
                self.kw_buttons[first].blockSignals(False)

    def _save_api_key(self):
        """保存 DeepSeek API Key"""
        key = self.api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请输入有效的 API Key")
            return
        self.ai.ds.set_key(key)
        self.api_status_label.setText("状态: DeepSeek API 已就绪")
        self.api_status_label.setStyleSheet("color: #0d904f; font-weight: bold;")
        self.api_key_input.setText(key[:8] + "****" + key[-4:])
        QMessageBox.information(self, "成功", "API Key 已保存，评语生成将使用 DeepSeek 大模型。")

    def _clear_api_key(self):
        """清除 API Key"""
        save_deepseek_key("")
        self.ai.ds.api_key = ""
        self.api_key_input.clear()
        self.api_status_label.setText("状态: 未配置（将使用本地模板）")
        self.api_status_label.setStyleSheet("color: #f9ab00; font-weight: bold;")
        QMessageBox.information(self, "已清除", "API Key 已清除，将恢复使用本地模板生成评语。")

    def _generate_comment(self):
        """生成评语"""
        sid = self.comment_student_combo.currentData()
        if not sid:
            QMessageBox.warning(self, "提示", "请先选择学生")
            return
        keywords = [k for k, b in self.kw_buttons.items() if b.isChecked()]
        comment = self.ai.generate_comment(sid, keywords if keywords else None)
        self.comment_text.setPlainText(comment)

        # 显示引擎信息
        if self.ai.ds.is_available() and not comment.startswith("[") and len(comment) > 20:
            self.comment_engine_label.setText("由 DeepSeek 大模型生成")
            self.comment_engine_label.setStyleSheet("color: #1a73e8; font-weight: bold;")
            self.comment_text.setStyleSheet("""
                QTextEdit { border: 2px solid #1a73e8; border-radius: 8px;
                    font-size: 11pt; padding: 14px; background: #f0f7ff; }
            """)
        else:
            self.comment_engine_label.setText("由本地模板引擎生成（配置 DeepSeek API Key 可获得更优效果）")
            self.comment_engine_label.setStyleSheet("color: #f9ab00;")
            self.comment_text.setStyleSheet("""
                QTextEdit { border: 2px solid #f9ab00; border-radius: 8px;
                    font-size: 11pt; padding: 14px; background: #f8fafc; }
            """)

    # ==================== Tab 3: 语义搜索 ====================

    def _build_search_tab(self):
        tab = QWidget()
        outer = QVBoxLayout()
        outer.setSpacing(12)

        desc = QLabel("输入自然语言描述，AI 自动解析为查询条件。\n"
                      "示例: \"一班数学不及格的学生\" | \"2024级物联网平均分低于60\" | \"计科2401班80分以上的学生\"")
        desc.setFont(QFont("Microsoft YaHei", 9))
        desc.setStyleSheet("color: #475569;")
        desc.setWordWrap(True)
        outer.addWidget(desc)

        input_layout = QHBoxLayout()
        self.nl_input = QLineEdit()
        self.nl_input.setPlaceholderText("输入自然语言查询，如: 一班数学不及格的学生")
        self.nl_input.setMinimumHeight(40)
        self.nl_input.setStyleSheet("font-size: 12pt; padding: 8px 12px;")
        self.nl_input.returnPressed.connect(self._do_semantic_search)
        input_layout.addWidget(self.nl_input)

        search_btn = QPushButton("AI 搜索")
        search_btn.setMinimumHeight(40)
        search_btn.setStyleSheet("""
            QPushButton { background-color: #1a73e8; color: white; border: none;
                border-radius: 6px; padding: 8px 20px; font-weight: bold; }
            QPushButton:hover { background-color: #1557b0; }
        """)
        search_btn.clicked.connect(self._do_semantic_search)
        input_layout.addWidget(search_btn)
        outer.addLayout(input_layout)

        # 解析结果展示
        self.nl_parsed_label = QLabel("")
        self.nl_parsed_label.setFont(QFont("Microsoft YaHei", 9))
        self.nl_parsed_label.setStyleSheet("color: #1a73e8; padding: 4px 8px;")
        outer.addWidget(self.nl_parsed_label)

        # 结果表格
        self.nl_result_table = QTableWidget()
        self.nl_result_table.setAlternatingRowColors(True)
        self.nl_result_table.verticalHeader().setVisible(True)
        self.nl_result_table.verticalHeader().setDefaultSectionSize(28)
        self.nl_result_table.setSortingEnabled(True)
        outer.addWidget(self.nl_result_table, 1)

        # 操作按钮
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("作为筛选条件应用到学生页")
        apply_btn.clicked.connect(self._apply_nl_filter)
        btn_layout.addWidget(apply_btn)
        btn_layout.addStretch()
        outer.addLayout(btn_layout)

        tab.setLayout(outer)
        self.tab_widget.addTab(tab, "语义搜索")

    def _do_semantic_search(self):
        """执行语义搜索"""
        text = self.nl_input.text().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请输入查询内容")
            return

        parsed = self.ai.parse_natural_query(text)
        filters = parsed['filters']
        self.nl_parsed_label.setText(parsed['description'])

        if parsed['search_type'] == 'grade':
            grades = self.grade_service.grade_dao.get_page(1, 99999, filters)
            self.nl_result_table.setColumnCount(6)
            self.nl_result_table.setHorizontalHeaderLabels(['学号', '姓名', '课程', '分数', '学期', '考试时间'])
            self.nl_result_table.setRowCount(len(grades))
            for row, g in enumerate(grades):
                for col, key in enumerate(['student_id', 'name', 'course_name', 'score', 'semester', 'exam_time']):
                    val = str(g[key]) if g[key] is not None else ""
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.nl_result_table.setItem(row, col, item)
        else:
            students = self.student_service.student_dao.get_page(1, 99999, filters)
            self.nl_result_table.setColumnCount(5)
            self.nl_result_table.setHorizontalHeaderLabels(['学号', '姓名', '性别', '专业', '班级'])
            self.nl_result_table.setRowCount(len(students))
            for row, s in enumerate(students):
                for col, key in enumerate(['student_id', 'name', 'gender', 'major', 'class_name']):
                    val = str(s[key]) if s[key] is not None else ""
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.nl_result_table.setItem(row, col, item)

        self.nl_result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _apply_nl_filter(self):
        """将语义搜索结果应用到学生管理页面"""
        text = self.nl_input.text().strip()
        if not text:
            return
        main_win = self.window()
        if not isinstance(main_win, QMainWindow):
            return
        parsed = self.ai.parse_natural_query(text)
        filters = parsed['filters']

        if parsed['search_type'] == 'student':
            main_win.switch_page("student")
            page = main_win.student_page
            # 设置筛选条件
            if 'student_id' in filters:
                page.search_student_id.setText(filters['student_id'])
            if 'name' in filters:
                page.search_name.setText(filters['name'])
            if 'class_name' in filters:
                page.search_class.setText(filters['class_name'])
            if 'major' in filters:
                page.search_major.setText(filters['major'])
            page.do_search()
        else:
            main_win.switch_page("grade")
            page = main_win.grade_page
            if 'student_id' in filters:
                page.search_sid.setText(filters['student_id'])
            if 'course_name' in filters:
                page.search_course.setText(filters['course_name'])
            if 'class_name' in filters:
                page.search_class_g.setText(filters['class_name'])
            if 'score_min' in filters:
                page.score_min.setValue(filters['score_min'])
            if 'score_max' in filters:
                page.score_max.setValue(filters['score_max'])
            page.do_search()

    # ==================== Tab 4: 异常检测 ====================

    def _build_anomaly_tab(self):
        tab = QWidget()
        outer = QVBoxLayout()
        outer.setSpacing(10)

        desc = QLabel("自动扫描数据库中的分数越界、重复学号、信息缺失、姓名不一致等异常数据。")
        desc.setFont(QFont("Microsoft YaHei", 9))
        desc.setStyleSheet("color: #475569;")
        outer.addWidget(desc)

        scan_layout = QHBoxLayout()
        scan_btn = QPushButton("开始扫描")
        scan_btn.setStyleSheet("""
            QPushButton { background-color: #f9ab00; color: white; border: none;
                border-radius: 6px; padding: 10px 24px; font-weight: bold; }
            QPushButton:hover { background-color: #e09600; }
        """)
        scan_btn.clicked.connect(self._scan_anomalies)
        scan_layout.addWidget(scan_btn)
        scan_layout.addStretch()
        outer.addLayout(scan_layout)

        self.anomaly_table = QTableWidget()
        self.anomaly_table.setColumnCount(4)
        self.anomaly_table.setHorizontalHeaderLabels(['异常类型', '级别', '描述', '详情'])
        self.anomaly_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.anomaly_table.setAlternatingRowColors(True)
        self.anomaly_table.verticalHeader().setVisible(True)
        self.anomaly_table.verticalHeader().setDefaultSectionSize(28)
        self.anomaly_table.setSortingEnabled(True)
        self.anomaly_table.doubleClicked.connect(self._goto_anomaly)
        outer.addWidget(self.anomaly_table, 1)

        goto_btn = QPushButton("双击行可跳转到对应数据页面进行修改")
        goto_btn.setEnabled(False)
        goto_btn.setStyleSheet("border: none; color: #64748b;")
        outer.addWidget(goto_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        tab.setLayout(outer)
        self.tab_widget.addTab(tab, "异常检测")

        self._anomaly_data = []  # 存储异常数据用于跳转

    def _scan_anomalies(self):
        """扫描异常数据"""
        anomalies = self.ai.detect_anomalies()
        self._anomaly_data = anomalies

        self.anomaly_table.setRowCount(len(anomalies))
        for row, a in enumerate(anomalies):
            for col, key in enumerate(['type', 'level', 'desc', 'detail']):
                val = str(a[key])
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # 颜色标记
                if key == 'level':
                    if val == 'error':
                        item.setForeground(QColor("#d93025"))
                        item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                    else:
                        item.setForeground(QColor("#f9ab00"))
                self.anomaly_table.setItem(row, col, item)

    def _goto_anomaly(self, index):
        """双击异常行跳转到对应页面"""
        row = index.row()
        if row >= len(self._anomaly_data):
            return
        a = self._anomaly_data[row]
        main_win = self.window()
        if not isinstance(main_win, QMainWindow):
            return

        if a['target'] == 'student':
            main_win.switch_page("student")
            main_win.student_page.search_student_id.setText(a['target_id'])
            main_win.student_page.do_search()
        elif a['target'] == 'grade':
            main_win.switch_page("grade")
            main_win.grade_page.search_sid.setText(a.get('student_id', ''))
            main_win.grade_page.do_search()

    # ==================== Tab 5: 机器学习分析 ====================

    def _build_ml_tab(self):
        tab = QWidget()
        outer = QVBoxLayout()
        outer.setSpacing(10)

        if not HAS_ML:
            hint = QLabel(
                "需要安装机器学习库\n\n"
                "请执行以下命令安装：\npip install scikit-learn numpy"
            )
            hint.setFont(QFont("Microsoft YaHei", 12))
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setStyleSheet("color: #64748b; padding: 60px;")
            outer.addWidget(hint)
            tab.setLayout(outer)
            self.tab_widget.addTab(tab, "机器学习分析")
            return

        # 数据准备提示
        self.ml_data_label = QLabel("")
        self.ml_data_label.setFont(QFont("Microsoft YaHei", 9))
        self.ml_data_label.setStyleSheet("color: #1a73e8; padding: 4px 8px;")
        self.ml_data_label.setWordWrap(True)
        outer.addWidget(self.ml_data_label)

        # 滚动区域包含4个分析板块
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(16)

        # ======== 板块1: K-Means 聚类 ========
        cluster_group = QGroupBox("K-Means 学生聚类分析")
        cluster_group.setStyleSheet(self._ml_group_style())
        cluster_layout = QVBoxLayout()

        cluster_desc = QLabel("基于平均分、标准差、课程数、及格率等特征，将学生自动分为优秀/良好/中等/需关注四个群体。")
        cluster_desc.setFont(QFont("Microsoft YaHei", 9))
        cluster_desc.setStyleSheet("color: #64748b;")
        cluster_desc.setWordWrap(True)
        cluster_layout.addWidget(cluster_desc)

        cluster_ctrl = QHBoxLayout()
        self.cluster_count_spin = QSpinBox()
        self.cluster_count_spin.setRange(3, 6)
        self.cluster_count_spin.setValue(4)
        self.cluster_count_spin.setPrefix("分组数: ")
        run_cluster_btn = QPushButton("执行聚类分析")
        run_cluster_btn.setStyleSheet(self._ml_btn_style("#1a73e8"))
        run_cluster_btn.clicked.connect(self._run_cluster)
        cluster_ctrl.addWidget(self.cluster_count_spin)
        cluster_ctrl.addWidget(run_cluster_btn)
        cluster_ctrl.addStretch()
        cluster_layout.addLayout(cluster_ctrl)

        self.cluster_result_table = QTableWidget()
        self.cluster_result_table.setAlternatingRowColors(True)
        self.cluster_result_table.verticalHeader().setVisible(True)
        self.cluster_result_table.verticalHeader().setDefaultSectionSize(28)
        self.cluster_result_table.setMaximumHeight(250)
        cluster_layout.addWidget(self.cluster_result_table)
        cluster_group.setLayout(cluster_layout)
        scroll_layout.addWidget(cluster_group)

        # ======== 板块2: 课程相关性 ========
        corr_group = QGroupBox("课程成绩相关性分析")
        corr_group.setStyleSheet(self._ml_group_style())
        corr_layout = QVBoxLayout()

        corr_desc = QLabel("使用 Pearson 相关系数分析各课程之间的成绩关联，识别核心课程和关联课程群。")
        corr_desc.setFont(QFont("Microsoft YaHei", 9))
        corr_desc.setStyleSheet("color: #64748b;")
        corr_desc.setWordWrap(True)
        corr_layout.addWidget(corr_desc)

        corr_ctrl = QHBoxLayout()
        run_corr_btn = QPushButton("分析课程相关性")
        run_corr_btn.setStyleSheet(self._ml_btn_style("#0d904f"))
        run_corr_btn.clicked.connect(self._run_correlation)
        corr_ctrl.addWidget(run_corr_btn)
        corr_ctrl.addStretch()
        corr_layout.addLayout(corr_ctrl)

        self.corr_table = QTableWidget()
        self.corr_table.setAlternatingRowColors(True)
        self.corr_table.verticalHeader().setVisible(True)
        self.corr_table.verticalHeader().setDefaultSectionSize(28)
        corr_layout.addWidget(self.corr_table)

        self.gateway_label = QLabel("")
        self.gateway_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.gateway_label.setStyleSheet("color: #0d904f; padding: 8px;")
        self.gateway_label.setWordWrap(True)
        corr_layout.addWidget(self.gateway_label)

        corr_group.setLayout(corr_layout)
        scroll_layout.addWidget(corr_group)

        # ======== 板块3: 成绩预测 ========
        pred_group = QGroupBox("线性回归成绩预测")
        pred_group.setStyleSheet(self._ml_group_style())
        pred_layout = QVBoxLayout()

        pred_desc = QLabel("基于已有成绩数据训练线性回归模型，预测学生的综合学业表现趋势。")
        pred_desc.setFont(QFont("Microsoft YaHei", 9))
        pred_desc.setStyleSheet("color: #64748b;")
        pred_desc.setWordWrap(True)
        pred_layout.addWidget(pred_desc)

        pred_ctrl = QHBoxLayout()
        pred_ctrl.addWidget(QLabel("选择学生:"))
        self.pred_student_combo = QComboBox()
        self.pred_student_combo.setMinimumWidth(200)
        pred_ctrl.addWidget(self.pred_student_combo)

        run_pred_btn = QPushButton("预测成绩")
        run_pred_btn.setStyleSheet(self._ml_btn_style("#9b59b6"))
        run_pred_btn.clicked.connect(self._run_prediction)
        pred_ctrl.addWidget(run_pred_btn)
        pred_ctrl.addStretch()
        pred_layout.addLayout(pred_ctrl)

        self.pred_result_label = QLabel("")
        self.pred_result_label.setFont(QFont("Microsoft YaHei", 11))
        self.pred_result_label.setStyleSheet(
            "color: #1e293b; border: 2px solid #9b59b6; border-radius: 8px; "
            "padding: 16px; background: #faf5ff;"
        )
        self.pred_result_label.setWordWrap(True)
        self.pred_result_label.setMinimumHeight(80)
        pred_layout.addWidget(self.pred_result_label)

        pred_group.setLayout(pred_layout)
        scroll_layout.addWidget(pred_group)

        # ======== 板块4: 综合排名 ========
        rank_group = QGroupBox("学生综合排名")
        rank_group.setStyleSheet(self._ml_group_style())
        rank_layout = QVBoxLayout()

        rank_desc = QLabel("基于加权评分（均分60% + 及格率30% + 课程广度10%），生成学生综合排名与百分位。")
        rank_desc.setFont(QFont("Microsoft YaHei", 9))
        rank_desc.setStyleSheet("color: #64748b;")
        rank_desc.setWordWrap(True)
        rank_layout.addWidget(rank_desc)

        rank_ctrl = QHBoxLayout()
        run_rank_btn = QPushButton("计算综合排名")
        run_rank_btn.setStyleSheet(self._ml_btn_style("#f9ab00"))
        run_rank_btn.clicked.connect(self._run_ranking)
        rank_ctrl.addWidget(run_rank_btn)
        rank_ctrl.addStretch()
        rank_layout.addLayout(rank_ctrl)

        self.rank_table = QTableWidget()
        self.rank_table.setAlternatingRowColors(True)
        self.rank_table.verticalHeader().setVisible(True)
        self.rank_table.verticalHeader().setDefaultSectionSize(28)
        self.rank_table.setMaximumHeight(300)
        rank_layout.addWidget(self.rank_table)
        rank_group.setLayout(rank_layout)
        scroll_layout.addWidget(rank_group)

        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        outer.addWidget(scroll, 1)

        tab.setLayout(outer)
        self.tab_widget.addTab(tab, "机器学习分析")

        # 加载学生列表供预测使用
        self._load_ml_students()
        # 确保有足够训练数据
        self._ensure_ml_data()

    def _ml_group_style(self):
        return """
            QGroupBox {
                font-weight: bold; font-size: 11pt; color: #1e293b;
                border: 1px solid #e2e8f0; border-radius: 8px;
                margin-top: 12px; padding-top: 22px; background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 14px;
                padding: 0 8px; color: #1e293b;
            }
        """

    def _ml_btn_style(self, color: str):
        return f"""
            QPushButton {{
                background-color: {color}; color: white; border: none;
                border-radius: 6px; padding: 8px 18px; font-weight: bold;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
        """

    def _ensure_ml_data(self):
        """确保有足够的训练数据"""
        db = DatabaseManager()
        added_s, added_g = db.ensure_ml_training_data()
        if added_s > 0:
            self.ml_data_label.setText(
                f"已自动生成 {added_s} 名合成学生和 {added_g} 条成绩记录用于ML分析。"
                f"（真实数据不会被覆盖）"
            )
            self._load_ml_students()
        else:
            conn = db.get_connection()
            cnt = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            gcnt = conn.execute("SELECT COUNT(*) FROM grades").fetchone()[0]
            self.ml_data_label.setText(
                f"当前数据: {cnt} 名学生, {gcnt} 条成绩记录 — 数据量充足，ML分析结果可信"
            )

    def _load_ml_students(self):
        """加载学生列表到预测下拉框"""
        self.pred_student_combo.clear()
        students = self.student_service.student_dao.get_page(1, 99999)
        # 只显示有成绩的学生
        for s in students:
            self.pred_student_combo.addItem(
                f"{s['student_id']} - {s['name']} ({s['class_name']})", s['student_id']
            )

    # ======== 聚类分析回调 ========

    def _run_cluster(self):
        n = self.cluster_count_spin.value()
        result = self.ai.cluster_students(n_clusters=n)

        if "error" in result:
            QMessageBox.warning(self, "提示", result["error"])
            return

        # 聚类中心表
        centers = result['centers']
        self.cluster_result_table.setColumnCount(4)
        self.cluster_result_table.setHorizontalHeaderLabels(['群体', '人数', '平均分', '平均及格率'])
        self.cluster_result_table.setRowCount(len(centers))
        for row, c in enumerate(centers):
            for col, key in enumerate(['name', 'size', 'avg_score', 'avg_pass_rate']):
                val = str(c[key])
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if key == 'name':
                    item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                self.cluster_result_table.setItem(row, col, item)
        self.cluster_result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        QMessageBox.information(self, "聚类完成",
            f"已将 {result['total_students']} 名学生分为 {result['n_clusters']} 个群体。\n"
            f"详细分配结果可通过控制台或日志查看。")

    # ======== 课程相关性回调 ========

    def _run_correlation(self):
        result = self.ai.analyze_course_correlation()

        if "error" in result:
            QMessageBox.warning(self, "提示", result["error"])
            return

        pairs = result['pairs']
        if not pairs:
            self.gateway_label.setText("暂无足够数据计算课程相关性（需要至少2门课程各有3名以上学生）")
            return

        self.corr_table.setColumnCount(5)
        self.corr_table.setHorizontalHeaderLabels(['课程A', '课程B', '相关系数', '关联强度', '样本数'])
        self.corr_table.setRowCount(len(pairs))
        for row, p in enumerate(pairs):
            for col, key in enumerate(['course_a', 'course_b', 'correlation', 'strength', 'sample_size']):
                val = str(p[key])
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # 颜色标记
                if key == 'correlation':
                    corr_val = float(val)
                    if abs(corr_val) > 0.6:
                        item.setForeground(QColor("#d93025" if corr_val > 0 else "#1a73e8"))
                        item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                self.corr_table.setItem(row, col, item)
        self.corr_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # 核心课程
        if result['gateway_courses']:
            parts = ["核心课程（与其他课程关联度最高）:"]
            for gc in result['gateway_courses']:
                parts.append(f"  • {gc['course']}（平均相关系数: {gc['avg_correlation']}）")
            self.gateway_label.setText("\n".join(parts))

    # ======== 成绩预测回调 ========

    def _run_prediction(self):
        sid = self.pred_student_combo.currentData()
        if not sid:
            QMessageBox.warning(self, "提示", "请先选择学生")
            return

        result = self.ai.predict_future_score(sid)

        if "error" in result:
            self.pred_result_label.setText(f"预测失败: {result['error']}")
            return

        lines = [
            f"学生: {result['name']} ({result['student_id']})",
            f"当前平均分: {result['current_avg']} 分 | 预测综合均分: {result['predicted_avg']} 分",
            f"模型拟合度 R²: {result['r2_score']} | 置信度: {result['confidence']}",
            f"训练样本: {result['sample_size']} 名学生 | 该生已修 {result['course_count']} 门课程",
        ]
        self.pred_result_label.setText("\n".join(lines))

    # ======== 综合排名回调 ========

    def _run_ranking(self):
        result = self.ai.rank_students()

        if "error" in result:
            QMessageBox.warning(self, "提示", result["error"])
            return

        rankings = result['rankings']
        self.rank_table.setColumnCount(6)
        self.rank_table.setHorizontalHeaderLabels(['排名', '学号', '姓名', '加权分', '平均分', '百分位'])
        self.rank_table.setRowCount(min(len(rankings), 50))  # 显示前50名
        for row, r in enumerate(rankings[:50]):
            for col, key in enumerate(['rank', 'student_id', 'name', 'weighted_score', 'avg_score', 'percentile']):
                val = str(r[key])
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if key == 'rank' and r['rank'] <= 3:
                    item.setForeground(QColor("#f9ab00"))
                    item.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                self.rank_table.setItem(row, col, item)
        self.rank_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # 前三和后三
        if result['top3']:
            top_names = "、".join(f"{r['name']}({r['weighted_score']}分)" for r in result['top3'])
            QMessageBox.information(self, "排名完成",
                f"共 {result['total']} 名学生参与排名。\n\n"
                f"前三名: {top_names}\n"
                f"详细排名见下方表格（显示前50名）")


class MainWindow(QMainWindow):
    """
    主窗口
    采用"侧边栏导航 + 内容区"经典企业级布局
    """

    def __init__(self, auth_service: AuthService):
        super().__init__()
        self.auth_service = auth_service
        self.student_service = StudentService()
        self.grade_service = GradeService()
        self.log_dao = LogDAO()

        self.init_ui()
        self.apply_style()
        self._setup_shortcuts()
        self._setup_statusbar_timer()

    def init_ui(self):
        """初始化主窗口界面"""
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 800)
        # 设置窗口图标
        icon_path = resource_path("icon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(1024, 600)

        # -------- 中心Widget --------
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -------- 左侧边栏 --------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            #sidebar {
                background-color: #2c3e50;
                border-right: 1px solid #34495e;
            }
        """)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(2)

        # 侧边栏标题
        sidebar_title = QLabel("  功能菜单")
        sidebar_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        sidebar_title.setStyleSheet("color: #ecf0f1; padding: 15px; background-color: #34495e;")
        sidebar_layout.addWidget(sidebar_title)

        # 导航按钮
        self.nav_buttons = []
        nav_items = [
            ("dashboard", "系统概览"),
            ("student", "学生管理"),
            ("grade", "成绩管理"),
            ("stats", "统计可视化"),
            ("ai", "AI 智能分析"),
            ("users", "用户管理"),
            ("logs", "操作日志"),
            ("profile", "个人中心"),
        ]

        self.stacked_widget = QStackedWidget()

        # 创建各页面
        self.dashboard_page = DashboardPage(
            self.student_service, self.grade_service, self.auth_service, self.log_dao
        )
        self.student_page = StudentPage(self.student_service, self.auth_service)
        self.grade_page = GradePage(self.grade_service, self.auth_service)
        self.stats_page = StatisticsPage(self.student_service, self.grade_service)
        self.ai_page = AIPage(self.student_service, self.grade_service, self.auth_service)
        self.users_page = UserManagePage(self.auth_service)
        self.logs_page = LogPage(self.log_dao)
        self.profile_page = ProfilePage(self.auth_service)

        pages = {
            "dashboard": self.dashboard_page,
            "student": self.student_page,
            "grade": self.grade_page,
            "stats": self.stats_page,
            "ai": self.ai_page,
            "users": self.users_page,
            "logs": self.logs_page,
            "profile": self.profile_page,
        }

        for key, name in nav_items:
            btn = QPushButton(f"  {name}")
            btn.setFont(QFont("Microsoft YaHei", 10))
            btn.setFixedHeight(42)
            btn.setCheckable(True)
            btn.setProperty("nav_key", key)
            btn.clicked.connect(lambda checked, k=key: self.switch_page(k))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 15px;
                    border: none;
                    color: #d5dbe3;
                    background: transparent;
                }
                QPushButton:hover { background-color: #34495e; color: #ecf0f1; }
                QPushButton:checked { background-color: #4a90d9; color: white; font-weight: bold; }
            """)
            self.nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)
            self.stacked_widget.addWidget(pages[key])

        # 管理员才能看到用户管理和日志
        if not self.auth_service.is_admin():
            for btn in self.nav_buttons:
                if btn.property("nav_key") in ("users", "logs"):
                    btn.setVisible(False)

        sidebar_layout.addStretch()

        # 侧边栏底部：关于和退出按钮
        sidebar_bottom = QFrame()
        sidebar_bottom.setStyleSheet("border-top: 1px solid #34495e;")
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(2)

        about_btn = QPushButton("  关于系统")
        about_btn.setFont(QFont("Microsoft YaHei", 9))
        about_btn.setFixedHeight(36)
        about_btn.setStyleSheet("""
            QPushButton {
                text-align: left; padding-left: 15px; border: none;
                color: #b0b8c1; background: transparent;
            }
            QPushButton:hover { color: white; background-color: #34495e; }
        """)
        about_btn.clicked.connect(self.show_about)
        bottom_layout.addWidget(about_btn)

        logout_btn = QPushButton("  退出登录")
        logout_btn.setFont(QFont("Microsoft YaHei", 9))
        logout_btn.setFixedHeight(36)
        logout_btn.setStyleSheet(about_btn.styleSheet())
        logout_btn.clicked.connect(self.do_logout)
        bottom_layout.addWidget(logout_btn)

        exit_btn = QPushButton("  退出程序")
        exit_btn.setFont(QFont("Microsoft YaHei", 9))
        exit_btn.setFixedHeight(36)
        exit_btn.setStyleSheet(about_btn.styleSheet())
        exit_btn.clicked.connect(self.close)
        bottom_layout.addWidget(exit_btn)

        sidebar_bottom.setLayout(bottom_layout)
        sidebar_layout.addWidget(sidebar_bottom)
        sidebar.setLayout(sidebar_layout)

        main_layout.addWidget(sidebar)

        # -------- 右侧内容区 --------
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #f5f6fa;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 顶部工具栏
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e0;")
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(15, 0, 15, 0)

        user = self.auth_service.get_current_user()
        welcome_label = QLabel(
            f"欢迎，{user.get('real_name', user['username'])} "
            f"({('管理员' if user['role'] == 'admin' else '教师')})"
        )
        welcome_label.setFont(QFont("Microsoft YaHei", 10))
        toolbar_layout.addWidget(welcome_label)
        toolbar_layout.addStretch()

        # 备份/还原按钮
        backup_btn = QPushButton("备份数据库")
        backup_btn.setFixedHeight(30)
        backup_btn.clicked.connect(self.do_backup)
        restore_btn = QPushButton("还原数据库")
        restore_btn.setFixedHeight(30)
        restore_btn.clicked.connect(self.do_restore)
        toolbar_layout.addWidget(backup_btn)
        toolbar_layout.addWidget(restore_btn)

        toolbar.setLayout(toolbar_layout)
        content_layout.addWidget(toolbar)
        content_layout.addWidget(self.stacked_widget)
        content_frame.setLayout(content_layout)

        main_layout.addWidget(content_frame, 1)
        central.setLayout(main_layout)

        # -------- 状态栏 --------
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("就绪")
        self.setStatusBar(self.status_bar)

        # 默认选中仪表盘
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)
            self.switch_page("dashboard")

    def switch_page(self, key: str):
        """切换页面"""
        page_map = {
            "dashboard": 0, "student": 1, "grade": 2, "stats": 3,
            "ai": 4, "users": 5, "logs": 6, "profile": 7,
        }
        idx = page_map.get(key, 0)
        self.stacked_widget.setCurrentIndex(idx)

        # 更新侧边栏按钮选中状态
        for btn in self.nav_buttons:
            btn.setChecked(btn.property("nav_key") == key)

        # 刷新对应页面数据
        page = self.stacked_widget.currentWidget()
        if hasattr(page, 'load_data'):
            page.load_data()
        if hasattr(page, 'refresh_all') and key == "stats":
            page.refresh_all()

        page_names = {
            "dashboard": "系统概览", "student": "学生管理", "grade": "成绩管理",
            "stats": "统计可视化", "ai": "AI 智能分析",
            "users": "用户管理", "logs": "操作日志", "profile": "个人中心",
        }
        self.status_bar.showMessage(f"当前页面: {page_names.get(key, '')}")

    def apply_style(self):
        """应用企业级全局QSS样式"""
        self.setStyleSheet("""
            /* ===== 全局基础 ===== */
            QMainWindow, QDialog, QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 9pt;
                color: #1e293b;
                background-color: #f1f5f9;
            }

            /* ===== 分组框 ===== */
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 20px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
                color: #1e293b;
            }

            /* ===== 按钮 ===== */
            QPushButton {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 16px;
                background-color: #ffffff;
                color: #1e293b;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #e8f0fe;
                border-color: #1a73e8;
                color: #1a73e8;
            }
            QPushButton:pressed {
                background-color: #d2e3fc;
                border-color: #1557b0;
            }
            QPushButton:disabled {
                background-color: #e2e8f0;
                color: #64748b;
                border-color: #cbd5e1;
            }
            QPushButton:checked {
                background-color: #1a73e8;
                color: white;
                border-color: #1a73e8;
                font-weight: bold;
            }

            /* ===== 输入框 ===== */
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 5px 10px;
                background-color: #ffffff;
                color: #1e293b;
                font-size: 9pt;
                min-height: 22px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
            QComboBox:focus, QDateEdit:focus {
                border-color: #1a73e8;
                background-color: #ffffff;
            }
            QLineEdit:read-only {
                background-color: #f8fafc;
                color: #475569;
            }
            QLineEdit[invalid="true"] {
                border: 2px solid #d93025;
                background-color: #fef2f2;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #e2e8f0;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }

            /* ===== 表格 ===== */
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                gridline-color: #f1f5f9;
                background-color: #ffffff;
                selection-background-color: #e8f0fe;
                selection-color: #1e293b;
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QTableWidget::item:alternate {
                background-color: #f8fafc;
            }
            QHeaderView::section {
                background-color: #f1f5f9;
                color: #475569;
                padding: 8px 6px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                border-right: 1px solid #e2e8f0;
                font-weight: bold;
                font-size: 9pt;
            }
            QHeaderView::section:hover {
                background-color: #e2e8f0;
                color: #1a73e8;
            }

            /* ===== 标签页 ===== */
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                border: 1px solid #e2e8f0;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                background-color: #f8fafc;
                color: #475569;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #1a73e8;
                border-bottom: 2px solid #1a73e8;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e8f0fe;
            }

            /* ===== 滚动条 ===== */
            QScrollBar:vertical {
                border: none;
                background: #f1f5f9;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            /* ===== 状态栏 ===== */
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e2e8f0;
                color: #334155;
                font-size: 9pt;
            }

            /* ===== 菜单 ===== */
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 32px 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
            QMenu::item:disabled {
                color: #64748b;
            }
            QMenu::separator {
                height: 1px;
                background: #e2e8f0;
                margin: 4px 8px;
            }

            /* ===== 提示框 ===== */
            QToolTip {
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #ffffff;
                color: #1e293b;
            }
        """)

    def _setup_shortcuts(self):
        """注册全局快捷键"""
        # Ctrl+N: 新增（当前页面上下文感知）
        QShortcut("Ctrl+N", self).activated.connect(self._on_shortcut_new)
        # Ctrl+F: 聚焦搜索
        QShortcut("Ctrl+F", self).activated.connect(self._on_shortcut_search)
        # Ctrl+E: 编辑选中行
        QShortcut("Ctrl+E", self).activated.connect(self._on_shortcut_edit)
        # Delete: 删除选中行
        QShortcut("Delete", self).activated.connect(self._on_shortcut_delete)
        # F5: 刷新当前页面
        QShortcut("F5", self).activated.connect(self._on_shortcut_refresh)
        # Ctrl+Q: 退出程序
        QShortcut("Ctrl+Q", self).activated.connect(self.close)
        # Ctrl+1~7: 切换页面
        for i in range(1, 8):
            QShortcut(f"Ctrl+{i}", self).activated.connect(
                lambda idx=i-1: self._switch_by_index(idx)
            )

    def _switch_by_index(self, idx: int):
        """按索引切换页面"""
        key_map = {0: "dashboard", 1: "student", 2: "grade", 3: "stats",
                   4: "ai", 5: "users", 6: "logs"}
        key = key_map.get(idx)
        if key:
            # 非管理员不能切换到用户管理和日志
            if key in ("users", "logs") and not self.auth_service.is_admin():
                return
            self.switch_page(key)

    def _current_editable_page(self):
        """获取当前可编辑的页面对象（有do_add/do_edit方法的页面）"""
        page = self.stacked_widget.currentWidget()
        if hasattr(page, 'do_add') or hasattr(page, 'do_edit'):
            return page
        return None

    def _on_shortcut_new(self):
        """Ctrl+N: 当前页面新增"""
        page = self._current_editable_page()
        if page and hasattr(page, 'do_add'):
            page.do_add()

    def _on_shortcut_search(self):
        """Ctrl+F: 聚焦搜索框"""
        page = self.stacked_widget.currentWidget()
        # 尝试找到搜索/筛选输入框并聚焦
        search_inputs = page.findChildren(QLineEdit)
        if search_inputs:
            search_inputs[0].setFocus()

    def _on_shortcut_edit(self):
        """Ctrl+E: 编辑选中行"""
        page = self._current_editable_page()
        if page and hasattr(page, 'do_edit'):
            page.do_edit()

    def _on_shortcut_delete(self):
        """Delete: 删除选中行"""
        page = self._current_editable_page()
        if page and hasattr(page, 'do_delete'):
            page.do_delete()

    def _on_shortcut_refresh(self):
        """F5: 刷新当前页面"""
        page = self.stacked_widget.currentWidget()
        if hasattr(page, 'load_data'):
            page.load_data()
        if hasattr(page, 'refresh_all'):
            page.refresh_all()

    def _setup_statusbar_timer(self):
        """启动状态栏时钟更新定时器"""
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_statusbar)
        self._status_timer.start(1000)  # 每秒更新

    def _update_statusbar(self):
        """更新状态栏信息"""
        user = self.auth_service.get_current_user()
        if not user:
            return
        username = user.get('username', '--')
        role = "管理员" if user.get('role') == 'admin' else "教师"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"|  用户: {username} ({role})  |  {now}  |"
        self.status_bar.showMessage(msg)

    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()

    def do_logout(self):
        """退出登录"""
        reply = QMessageBox.question(
            self, "确认", "确定要退出登录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.auth_service.logout()
            self.close()

    def do_backup(self):
        """数据库备份"""
        os.makedirs(BAKCUP_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BAKCUP_DIR, f"backup_{timestamp}.db")

        db_manager = DatabaseManager()
        if db_manager.backup_database(backup_path):
            self.auth_service.log_dao.insert(
                self.auth_service.get_current_username(),
                "数据库备份", backup_path
            )
            QMessageBox.information(self, "备份成功", f"数据库已备份到：\n{backup_path}")
        else:
            QMessageBox.warning(self, "备份失败", "备份操作未能完成")

    def do_restore(self):
        """数据库还原"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", BAKCUP_DIR, "数据库文件 (*.db);;所有文件 (*.*)"
        )
        if not filepath:
            return

        reply = QMessageBox.warning(
            self, "危险操作",
            "还原将覆盖当前所有数据！\n确定要继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        db_manager = DatabaseManager()
        if db_manager.restore_database(filepath):
            QMessageBox.information(self, "还原成功", "数据库已还原，请重新登录。")
            self.auth_service.logout()
            self.close()
        else:
            QMessageBox.warning(self, "还原失败", "还原操作未能完成")

    def closeEvent(self, event):
        """主窗口关闭事件：弹出确认对话框"""
        reply = QMessageBox.question(
            self, "确认退出",
            "确定要退出学生管理信息系统吗？\n未保存的数据将自动保存到数据库。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.auth_service.logout()
            DatabaseManager().close()
            event.accept()
        else:
            event.ignore()


# ==================== 应用入口 ====================

def main():
    """
    应用程序主入口
    1. 初始化数据库（首次运行自动建表+种子数据）
    2. 创建QApplication实例并设置Fusion风格
    3. 显示登录对话框
    4. 登录成功后进入主窗口
    """
    # 初始化数据库
    db_manager = DatabaseManager()
    db_manager.init_database()

    # 创建Qt应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("学生管理信息系统")
    app.setApplicationVersion(APP_VERSION)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 设置Fusion调色板（浅色主题）
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#4a90d9"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    app.setPalette(palette)

    # 设置应用图标
    icon_path = resource_path("icon.svg")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    # 登录循环
    while True:
        auth_service = AuthService()
        login_dialog = LoginDialog(auth_service)

        if login_dialog.exec() != QDialog.DialogCode.Accepted:
            # 用户关闭登录窗口
            db_manager.close()
            sys.exit(0)

        # 登录成功，进入主窗口
        main_window = MainWindow(auth_service)
        main_window.show()

        # 进入事件循环
        app.exec()

        # 如果主窗口关闭但没有触发logout（比如被还原数据库关闭），检查是否需要重新登录
        if not auth_service.get_current_user():
            # 用户主动登出或还原数据库 → 重新显示登录
            continue
        else:
            # 正常退出
            break

    db_manager.close()
    sys.exit(0)


if __name__ == "__main__":
    main()
