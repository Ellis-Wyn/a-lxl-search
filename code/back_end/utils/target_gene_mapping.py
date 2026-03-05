"""
=====================================================
靶点-基因映射表（Target-Gene Mapping）
=====================================================

用于智能PubMed查询转换：
- 用户输入 → 自动扩展为同义词+全名
- 提升召回率和准确率

使用示例：
    from utils.target_gene_mapping import TARGET_GENE_MAPPING, expand_search_query

    # 输入: EGFR
    # 输出: ("EGFR" OR "ERBB1" OR "HER1" OR "Epidermal Growth Factor Receptor")

    query = expand_search_query("EGFR")
    print(query)
=====================================================
"""

from typing import Dict, List, Set
import re

# =====================================================
# 靶点-基因映射表（核心）
# =====================================================

TARGET_GENE_MAPPING: Dict[str, Dict[str, str]] = {
    # ===================== 生长因子受体 =====================
    "EGFR": {
        "standard_name": "EGFR",
        "gene_name": "ERBB1",
        "aliases": ["HER1", "ERBB1"],
        "full_name": "Epidermal Growth Factor Receptor",
        "protein_name": "Epidermal growth factor receptor"
    },
    "HER2": {
        "standard_name": "HER2",
        "gene_name": "ERBB2",
        "aliases": ["ERBB2", "c-erbB2"],
        "full_name": "Human Epidermal Growth Factor Receptor 2",
        "protein_name": "Receptor tyrosine-protein kinase erbB-2"
    },
    "VEGFR": {
        "standard_name": "VEGFR",
        "gene_name": "KDR",
        "aliases": ["FLK1", "VEGFR1"],
        "full_name": "Vascular Endothelial Growth Factor Receptor",
        "protein_name": "Vascular endothelial growth factor receptor 1"
    },
    "VEGFR2": {
        "standard_name": "VEGFR2",
        "gene_name": "KDR",
        "aliases": ["FLK1", "KDR"],
        "full_name": "Vascular Endothelial Growth Factor Receptor 2",
        "protein_name": "Vascular endothelial growth factor receptor 2"
    },
    "PD-1": {
        "standard_name": "PD-1",
        "gene_name": "PDCD1",
        "aliases": ["CD279"],
        "full_name": "Programmed Cell Death 1",
        "protein_name": "Programmed cell death protein 1"
    },
    "PD-L1": {
        "standard_name": "PD-L1",
        "gene_name": "CD274",
        "aliases": ["B7-H1"],
        "full_name": "Programmed Cell Death Ligand 1",
        "protein_name": "Programmed death-ligand 1"
    },
    "CTLA-4": {
        "standard_name": "CTLA-4",
        "gene_name": "CTLA4",
        "aliases": ["CD152"],
        "full_name": "Cytotoxic T-Lymphocyte Antigen 4",
        "protein_name": "T-cell surface antigen CD152"
    },
    "ALK": {
        "standard_name": "ALK",
        "gene_name": "ALK",
        "aliases": ["CD246"],
        "full_name": "Anaplastic Lymphoma Kinase",
        "protein_name": "Anaplastic lymphoma kinase"
    },
    "ROS1": {
        "standard_name": "ROS1",
        "gene_name": "ROS1",
        "aliases": ["c-ROS"],
        "full_name": "ROS Proto-Oncogene 1",
        "protein_name": "Proto-oncogene tyrosine-protein kinase Ros"
    },
    "BRAF": {
        "standard_name": "BRAF",
        "gene_name": "BRAF",
        "aliases": ["B-RAF"],
        "full_name": "B-Raf Proto-Oncogene",
        "protein_name": "B-Raf proto-oncogene serine/threonine-protein kinase"
    },
    "KRAS": {
        "standard_name": "KRAS",
        "gene_name": "KRAS",
        "aliases": ["c-K-Ras"],
        "full_name": "Kirsten Rat Sarcoma Viral Oncogene",
        "protein_name": "GTPase KRas"
    },
    "NRAS": {
        "standard_name": "NRAS",
        "gene_name": "NRAS",
        "aliases": ["c-N-Ras"],
        "full_name": "Neuroblastoma RAS Viral Oncogene",
        "protein_name": "GTPase NRas"
    },
    "PI3K": {
        "standard_name": "PI3K",
        "gene_name": "PIK3CA",
        "aliases": [],
        "full_name": "Phosphatidylinositol 3-Kinase",
        "protein_name": "Phosphatidylinositol 3-kinase"
    },
    "mTOR": {
        "standard_name": "mTOR",
        "gene_name": "MTOR",
        "aliases": ["FRAP"],
        "full_name": "Mechanistic Target of Rapamycin",
        "protein_name": "Serine/threonine-protein kinase mTOR"
    },
    "CD19": {
        "standard_name": "CD19",
        "gene_name": "CD19",
        "aliases": ["B4"],
        "full_name": "CD19 Molecule",
        "protein_name": "B-lymphocyte antigen CD19"
    },
    "CD20": {
        "standard_name": "CD20",
        "gene_name": "MS4A1",
        "aliases": ["B1"],
        "full_name": "CD20 Molecule",
        "protein_name": "B-lymphocyte antigen CD20"
    },
    "BCMA": {
        "standard_name": "BCMA",
        "gene_name": "TNFRSF17",
        "aliases": ["CD269"],
        "full_name": "B-Cell Maturation Antigen",
        "protein_name": "Tumor necrosis factor receptor superfamily member 17"
    },
    "CLDN18": {
        "standard_name": "CLDN18",
        "gene_name": "CLDN18",
        "aliases": ["Claudin-18"],
        "full_name": "Claudin 18",
        "protein_name": "Claudin-18"
    },
    "CLDN18.2": {
        "standard_name": "CLDN18.2",
        "gene_name": "CLDN18",
        "aliases": ["Claudin 18.2"],
        "full_name": "Claudin 18.2",
        "protein_name": "Claudin-18"
    },
    "FGFR": {
        "standard_name": "FGFR",
        "gene_name": "FGFR1",
        "aliases": [],
        "full_name": "Fibroblast Growth Factor Receptor",
        "protein_name": "Fibroblast growth factor receptor"
    },
    "c-MET": {
        "standard_name": "c-MET",
        "gene_name": "MET",
        "aliases": ["HGFR"],
        "full_name": "Mesenchymal-Epithelial Transition Factor",
        "protein_name": "Hepatocyte growth factor receptor"
    },
    "MET": {
        "standard_name": "MET",
        "gene_name": "MET",
        "aliases": ["c-MET", "HGFR"],
        "full_name": "Hepatocyte Growth Factor Receptor",
        "protein_name": "Hepatocyte growth factor receptor"
    },
    "PARP": {
        "standard_name": "PARP",
        "gene_name": "PARP1",
        "aliases": ["Poly(ADP-ribose) polymerase"],
        "full_name": "Poly(ADP-Ribose) Polymerase",
        "protein_name": "Poly [ADP-ribose] polymerase 1"
    },
    "CDK4": {
        "standard_name": "CDK4",
        "gene_name": "CDK4",
        "aliases": [],
        "full_name": "Cyclin-Dependent Kinase 4",
        "protein_name": "Cell division protein kinase 4"
    },
    "CDK6": {
        "standard_name": "CDK6",
        "gene_name": "CDK6",
        "aliases": [],
        "full_name": "Cyclin-Dependent Kinase 6",
        "protein_name": "Cell division protein kinase 6"
    },
    "JAK": {
        "standard_name": "JAK",
        "gene_name": "JAK1",
        "aliases": ["Janus Kinase"],
        "full_name": "Janus Kinase",
        "protein_name": "Tyrosine-protein kinase JAK"
    },
    "STAT": {
        "standard_name": "STAT",
        "gene_name": "STAT3",
        "aliases": [],
        "full_name": "Signal Transducer and Activator of Transcription",
        "protein_name": "Signal transducer and activator of transcription"
    },
    "TIGIT": {
        "standard_name": "TIGIT",
        "gene_name": "TIGIT",
        "aliases": ["Vstm3"],
        "full_name": "T Cell Immunoreceptor With Ig And ITIM Domains",
        "protein_name": "T-cell immunoreceptor with Ig and ITIM domains"
    },
    "LAG3": {
        "standard_name": "LAG3",
        "gene_name": "LAG3",
        "aliases": ["CD223"],
        "full_name": "Lymphocyte Activation Gene-3",
        "protein_name": "Lymphocyte-activation gene 3 protein"
    },
    "TIM3": {
        "standard_name": "TIM3",
        "gene_name": "HAVCR2",
        "aliases": ["CD366"],
        "full_name": "Hepatitis A Virus Cellular Receptor 2",
        "protein_name": "Hepatitis A virus cellular receptor 2"
    },
    "IDO1": {
        "standard_name": "IDO1",
        "gene_name": "IDO1",
        "aliases": ["INDO"],
        "full_name": "Indoleamine 2,3-Dioxygenase 1",
        "protein_name": "Indoleamine 2,3-dioxygenase 1"
    },
    "SIRPα": {
        "standard_name": "SIRPA",
        "gene_name": "SIRPA",
        "aliases": ["CD47a"],
        "full_name": "Signal Regulatory Protein Alpha",
        "protein_name": "Signal-regulatory protein alpha"
    },
    "CD47": {
        "standard_name": "CD47",
        "gene_name": "CD47",
        "aliases": ["Integrin-Associated Protein"],
        "full_name": "CD47 Molecule",
        "protein_name": "Leukocyte surface antigen CD47"
    },
    "CXCR4": {
        "standard_name": "CXCR4",
        "gene_name": "CXCR4",
        "aliases": [],
        "full_name": "C-X-C Chemokine Receptor Type 4",
        "protein_name": "C-X-C chemokine receptor type 4"
    },
    "CCR5": {
        "standard_name": "CCR5",
        "gene_name": "CCR5",
        "aliases": [],
        "full_name": "C-C Chemokine Receptor Type 5",
        "protein_name": "C-C chemokine receptor type 5"
    },
    "GITR": {
        "standard_name": "GITR",
        "gene_name": "TNFRSF18",
        "aliases": ["CD357"],
        "full_name": "TNF Receptor Superfamily Member 18",
        "protein_name": "Tumor necrosis factor receptor superfamily member 18"
    },
    "OX40": {
        "standard_name": "OX40",
        "gene_name": "TNFRSF4",
        "aliases": ["CD134"],
        "full_name": "Tumor Necrosis Factor Receptor Superfamily Member 4",
        "protein_name": "Tumor necrosis factor receptor superfamily member 4"
    },
    "4-1BB": {
        "standard_name": "4-1BB",
        "gene_name": "TNFRSF9",
        "aliases": ["CD137"],
        "full_name": "Tumor Necrosis Factor Receptor Superfamily Member 9",
        "protein_name": "Tumor necrosis factor receptor superfamily member 9"
    },
}


def get_target_info(target_name: str) -> Dict[str, str] | None:
    """
    获取靶点信息

    Args:
        target_name: 靶点名称（EGFR、HER2等）

    Returns:
        靶点信息字典，包含：
        - standard_name: 标准名称
        - gene_name: 基因名称
        - aliases: 别名列表
        - full_name: 全名
        - protein_name: 蛋白质名称

    Example:
        >>> info = get_target_info("EGFR")
        >>> print(info["full_name"])
        'Epidermal Growth Factor Receptor'
    """
    target_name_upper = target_name.upper().replace("-", "").replace(".", "")

    # 精确匹配
    if target_name_upper in TARGET_GENE_MAPPING:
        return TARGET_GENE_MAPPING[target_name_upper]

    # 模糊匹配
    for key, value in TARGET_GENE_MAPPING.items():
        if target_name_upper == key.replace("-", "").replace(".", ""):
            return value

        # 检查别名
        if target_name_upper in [alias.upper().replace("-", "") for alias in value.get("aliases", [])]:
            return value

    return None


def expand_search_query(
    target_name: str,
    include_full_name: bool = True,
    include_gene_name: bool = True,
    include_aliases: bool = True,
    search_fields: List[str] = None
) -> str:
    """
    扩展PubMed查询字符串（智能查询转换）

    Args:
        target_name: 靶点名称（如 EGFR、Claudin 18.2）
        include_full_name: 是否包含全名
        include_gene_name: 是否包含基因名称
        include_aliases: 是否包含别名
        search_fields: 搜索字段（默认 ["Gene/Protein Name", "Title/Abstract"]）

    Returns:
        PubMed查询字符串

    Example:
        >>> query = expand_search_query("EGFR")
        >>> print(query)
        ("EGFR"[Gene/Protein Name] OR "ERBB1"[Gene/Protein Name] OR \
         "HER1"[Gene/Protein Name] OR "Epidermal Growth Factor Receptor"[Title/Abstract])

        >>> query = expand_search_query("Claudin 18.2")
        >>> print(query)
        ("CLDN18"[Gene/Protein Name] OR "Claudin 18.2"[Title/Abstract] OR \
         "Claudin-18.2"[Title/Abstract]) AND (Clinical Trial[Filter] OR "Phase")
    """
    info = get_target_info(target_name)

    if not info:
        # 如果没有映射，直接返回原始名称
        return f'("{target_name}"[Title/Abstract])'

    # 默认搜索字段
    if search_fields is None:
        search_fields = ["Gene/Protein Name", "Title/Abstract"]

    # 构建搜索词列表
    search_terms = []

    # 标准名称
    search_terms.append(info["standard_name"])

    # 基因名称
    if include_gene_name and info.get("gene_name"):
        search_terms.append(info["gene_name"])

    # 别名
    if include_aliases and info.get("aliases"):
        search_terms.extend(info["aliases"])

    # 去重
    search_terms = list(set(search_terms))

    # 构建查询字符串
    term_queries = []
    for term in search_terms:
        term_queries.append(f'"{term}"')

    # 字段限定查询
    field_queries = []
    for field in search_fields:
        field_queries.append(f' {field} '.join(term_queries))

    # 组合查询
    if len(field_queries) == 1:
        query_str = field_queries[0]
    else:
        # 多字段：用 OR 连接
        query_str = " OR ".join(field_queries)

    # 添加全名
    if include_full_name and info.get("full_name"):
        query_str += f' OR "{info["full_name"]}"[Title/Abstract]'

    return f"({query_str})"


def add_clinical_filter(query: str, include_preclinical: bool = False) -> str:
    """
    添加临床试验过滤器

    Args:
        query: 原始查询
        include_preclinical: 是否包含临床前

    Returns:
        带过滤器的查询字符串

    Example:
        >>> query = "EGFR"
        >>> filtered = add_clinical_filter(query)
        >>> print(filtered)
        (EGFR[Gene/Protein Name]) AND (Clinical Trial[Filter] OR "Phase")
    """
    filters = ['Clinical Trial[Filter]', '"Phase"']

    if include_preclinical:
        filters.append('"Preclinical"')

    filter_str = " OR ".join(filters)

    return f"{query} AND ({filter_str})"


def get_all_target_names() -> List[str]:
    """获取所有已知的靶点名称"""
    return list(TARGET_GENE_MAPPING.keys())


def search_target_by_keyword(keyword: str) -> List[str]:
    """
    根据关键词搜索靶点

    Args:
        keyword: 关键词（如 "EGF"）

    Returns:
        匹配的靶点列表

    Example:
        >>> results = search_target_by_keyword("EGF")
        >>> print(results)
        ['EGFR']
    """
    keyword_upper = keyword.upper()
    results = []

    for target_name, info in TARGET_GENE_MAPPING.items():
        # 检查标准名称
        if keyword_upper in target_name:
            results.append(target_name)
            continue

        # 检查全名
        if keyword_upper in info.get("full_name", "").upper():
            results.append(target_name)
            continue

        # 检查别名
        if any(keyword_upper in alias.upper() for alias in info.get("aliases", [])):
            results.append(target_name)

    return results


# =====================================================
# 导出
# =====================================================

__all__ = [
    "TARGET_GENE_MAPPING",
    "get_target_info",
    "expand_search_query",
    "add_clinical_filter",
    "get_all_target_names",
    "search_target_by_keyword",
]
