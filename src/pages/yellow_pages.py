"""
电话黄页页面模块
提供郑州航院各部门、学院、服务机构的联系方式查询
"""

import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

import streamlit as st

from src.utils.exceptions import DataLoadError, safe_execute

logger = logging.getLogger(__name__)


class YellowPages:
    """电话黄页数据管理类"""

    def __init__(self, data_path: Optional[str] = None):
        """
        初始化电话黄页
        
        Args:
            data_path: 黄页数据文件路径，默认为 data/yellow_pages.json
        """
        if data_path is None:
            # 默认路径：项目根目录下的 data/yellow_pages.json
            base_dir = Path(__file__).parent.parent.parent
            data_path = base_dir / "data" / "yellow_pages.json"
        
        self.data_path = Path(data_path)
        self._data: List[Dict] = []
        self._categories: List[str] = []
        self._load_data()

    @safe_execute(default_return=None, reraise=True)
    def _load_data(self) -> None:
        """加载黄页数据"""
        if not self.data_path.exists():
            raise DataLoadError(
                "黄页数据文件不存在",
                file_path=str(self.data_path)
            )
        
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            
            # 提取所有分类
            categories = set()
            for item in self._data:
                cat = item.get("category", "其他")
                categories.add(cat)
            self._categories = sorted(list(categories))
            
            logger.info(f"已加载 {len(self._data)} 条黄页记录，共 {len(self._categories)} 个分类")
        except json.JSONDecodeError as e:
            raise DataLoadError(
                f"黄页数据文件格式错误: {e}",
                file_path=str(self.data_path)
            )

    def get_all(self) -> List[Dict]:
        """获取所有黄页数据"""
        return self._data.copy()

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return self._categories.copy()

    def search(self, keyword: str = "", category: Optional[str] = None) -> List[Dict]:
        """
        搜索黄页数据
        
        Args:
            keyword: 搜索关键词
            category: 分类筛选
        
        Returns:
            匹配的黄页记录列表
        """
        results = self._data
        
        # 分类筛选
        if category and category != "全部":
            results = [
                item for item in results
                if item.get("category", "") == category
            ]
        
        # 关键词搜索
        if keyword:
            keyword_lower = keyword.lower()
            results = [
                item for item in results
                if self._match_keyword(item, keyword_lower)
            ]
        
        return results

    def _match_keyword(self, item: Dict, keyword: str) -> bool:
        """
        检查黄页记录是否匹配关键词
        
        Args:
            item: 黄页记录
            keyword: 搜索关键词（已转小写）
        
        Returns:
            是否匹配
        """
        search_fields = ["name", "phone", "address", "department", "email", "description"]
        
        for field in search_fields:
            value = item.get(field, "")
            if isinstance(value, str) and keyword in value.lower():
                return True
            elif isinstance(value, list):
                for v in value:
                    if keyword in str(v).lower():
                        return True
        
        return False


def render_yellow_pages_page(data_path: Optional[str] = None) -> None:
    """
    渲染电话黄页页面
    
    Args:
        data_path: 黄页数据文件路径
    """
    # 页面标题
    st.title("📞 校园电话黄页")
    st.markdown("---")
    
    # 说明文字
    st.info(
        "💡 提示：在这里可以查询郑州航院各部门、学院、服务机构的联系方式。"
        "支持按分类筛选和关键词搜索。"
    )
    
    try:
        # 加载黄页数据
        yellow_pages = YellowPages(data_path)
        
        # 搜索区域
        col1, col2 = st.columns([2, 1])
        
        with col1:
            keyword = st.text_input(
                "🔍 关键词搜索",
                placeholder="输入部门名称、电话、地址等关键词..."
            )
        
        with col2:
            categories = ["全部"] + yellow_pages.get_categories()
            category = st.selectbox("📂 分类筛选", categories)
        
        # 搜索结果
        results = yellow_pages.search(keyword, category)
        
        st.markdown("---")
        st.subheader(f"📋 查询结果 (共 {len(results)} 条)")
        
        if not results:
            st.warning("🔍 没有找到匹配的记录，请尝试其他关键词或分类。")
        else:
            # 按分类分组显示
            if category == "全部":
                grouped = {}
                for item in results:
                    cat = item.get("category", "其他")
                    if cat not in grouped:
                        grouped[cat] = []
                    grouped[cat].append(item)
                
                for cat, items in sorted(grouped.items()):
                    with st.expander(f"📁 {cat} ({len(items)} 条)", expanded=False):
                        _display_contact_items(items)
            else:
                _display_contact_items(results)
        
        # 底部信息
        st.markdown("---")
        st.caption(
            "📌 以上信息仅供参考，如有变动请以学校官方公布为准。\n"
            "发现信息有误？请联系学校信息化管理中心更新。"
        )
        
    except DataLoadError as e:
        st.error(f"❌ 数据加载失败：{e.message}")
        if e.file_path:
            st.caption(f"数据文件路径：`{e.file_path}`")
    except Exception as e:
        st.error(f"❌ 页面加载时发生错误：{str(e)}")
        logger.exception("电话黄页页面加载失败")


def _display_contact_items(items: List[Dict]) -> None:
    """
    显示联系信息列表
    
    Args:
        items: 联系信息记录列表
    """
    for idx, item in enumerate(items, 1):
        with st.container():
            # 名称和部门
            name = item.get("name", "未知")
            department = item.get("department", "")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**🏢 {name}**")
                if department:
                    st.caption(f"所属：{department}")
            
            with col2:
                # 电话按钮
                phones = item.get("phone", [])
                if isinstance(phones, str):
                    phones = [phones]
                
                for phone in phones:
                    if phone:
                        st.markdown(f"📞 [{phone}](tel:{phone})")
            
            # 地址和邮箱
            address = item.get("address", "")
            email = item.get("email", "")
            
            info_cols = st.columns(2)
            with info_cols[0]:
                if address:
                    st.markdown(f"📍 {address}")
            with info_cols[1]:
                if email:
                    st.markdown(f"📧 [{email}](mailto:{email})")
            
            # 描述
            description = item.get("description", "")
            if description:
                st.caption(f"ℹ️ {description}")
            
            # 分隔线（最后一条不显示）
            if idx < len(items):
                st.markdown("---")
