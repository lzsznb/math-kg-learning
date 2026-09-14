"""Entity extraction pipeline from syllabus text to KG entities."""
import re, json
from pathlib import Path
from collections import Counter


def parse_source_text(text):
    """Parse entity_source.txt into nodes and edges.
    
    Format:
      模块：module_name
       知识点：name，难度：N
      ---
      name1 → name2
    """
    nodes, edges = [], []
    cur_mod = "unknown"
    nid = 1
    name2id = {}
    in_edge = False
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Edge section delimiter
        if line.startswith('---'):
            in_edge = True
            continue
        
        # Edge section
        if in_edge:
            sep = '→' if '→' in line else ('->' if '->' in line else None)
            if sep:
                parts = line.split(sep)
                if len(parts) == 2:
                    s, t = parts[0].strip(), parts[1].strip()
                    if s in name2id and t in name2id:
                        edges.append({"from": name2id[s], "to": name2id[t]})
            continue
        
        # Module line
        if line.startswith('模块'):
            parts = line.split('：' if '：' in line else ':', 1)
            if len(parts) == 2:
                cur_mod = parts[1].strip()
            continue
        
        # Skip count line: 包含知识点数：NN
        if '知识点数' in line:
            continue
        
        # Knowledge node line:   知识点：name，难度：N
        if '知识点' in line:
            comma = '，' if '，' in line else ','
            parts = line.split(comma)
            name = None
            diff = 2
            for p in parts:
                p = p.strip()
                if '知识点' in p:
                    colon = '：' if '：' in p else ':'
                    name = p.split(colon)[-1].strip()
                if '难度' in p:
                    m = re.search(r'(\d+)', p)
                    if m:
                        diff = int(m.group(1))
            if name and name not in name2id:
                nodes.append({
                    "id": nid,
                    "name": name,
                    "module": cur_mod,
                    "difficulty": min(max(diff, 1), 5)
                })
                name2id[name] = nid
                nid += 1
    
    return {"nodes": nodes, "edges": edges}


def validate_entities(data):
    """Validate parsed entities for completeness and consistency."""
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    node_ids = set(n["id"] for n in nodes)
    node_names = [n["name"] for n in nodes]
    issues = []
    
    for n in nodes:
        if not n.get("name"):
            issues.append("Node ID=%d missing name" % n['id'])
        if not n.get("module"):
            issues.append("Node '%s' missing module" % n.get('name', '?'))
        if n.get("difficulty") is None:
            issues.append("Node '%s' missing difficulty" % n.get('name', '?'))
        elif n["difficulty"] < 1 or n["difficulty"] > 5:
            issues.append("Node '%s' difficulty %d OOB" % (n['name'], n['difficulty']))
    
    for name, cnt in Counter(node_names).items():
        if cnt > 1:
            issues.append("Duplicate: '%s' x%d" % (name, cnt))
    
    for e in edges:
        if e["from"] not in node_ids:
            issues.append("Edge src ID=%d missing" % e['from'])
        if e["to"] not in node_ids:
            issues.append("Edge dst ID=%d missing" % e['to'])
    
    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "issues": issues,
        "issue_count": len(issues),
        "is_clean": len(issues) == 0
    }


def classify_entities(data):
    """Classify entities by module and difficulty distributions."""
    nodes = data.get("nodes", [])
    mod_dist = Counter(n["module"] for n in nodes)
    diff_dist = Counter(n["difficulty"] for n in nodes)
    return {
        "module_distribution": dict(mod_dist.most_common()),
        "difficulty_distribution": dict(diff_dist.most_common())
    }


STANDARD_MODULES = [
    "集合与逻辑", "函数", "三角函数", "平面向量", "数列",
    "不等式", "立体几何", "解析几何", "概率与统计",
    "导数", "复数", "排列组合与二项式定理"
]


def coverage_analysis(data):
    """Analyze module coverage against standard high-school math modules."""
    nodes = data.get("nodes", [])
    modules = set(n["module"] for n in nodes)
    covered = [m for m in STANDARD_MODULES if m in modules]
    missing = [m for m in STANDARD_MODULES if m not in modules]
    extra = list(modules - set(STANDARD_MODULES))
    return {
        "standard_module_count": len(STANDARD_MODULES),
        "covered_module_count": len(covered),
        "covered_modules": covered,
        "missing_modules": missing,
        "extra_modules": extra,
        "module_coverage_pct": round(len(covered) / len(STANDARD_MODULES) * 100, 1) if STANDARD_MODULES else 0,
        "avg_nodes_per_module": round(len(nodes) / len(modules), 1) if modules else 0
    }


def run_extraction_pipeline(source_text=None, source_file=None):
    """Run the full entity extraction pipeline."""
    if source_file:
        with open(source_file, "r", encoding="utf-8") as f:
            source_text = f.read()
    if not source_text:
        return {"error": "No source text provided"}
    
    raw = parse_source_text(source_text)
    validation = validate_entities(raw)
    statistics = classify_entities(raw)
    coverage = coverage_analysis(raw)
    nc = len(raw.get("nodes", []))
    ec = len(raw.get("edges", []))
    status = "通过" if validation['is_clean'] else "未通过"
    
    summary = (
        "实体抽取管道执行完成："
        "从原始文本中提取 %d 个实体、%d 条关系，"
        "覆盖 %d/%d 个标准模块（%s%%），"
        "校验 %s。"
    ) % (nc, ec, coverage['covered_module_count'], coverage['standard_module_count'],
         coverage['module_coverage_pct'], status)
    
    return {
        "entities": raw,
        "validation": validation,
        "statistics": statistics,
        "coverage": coverage,
        "pipeline_summary": summary
    }


def export_to_json(data, output_file):
    """Export parsed entities to JSON file."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"output_file": output_file, "entity_count": len(data.get("nodes", [])), "relation_count": len(data.get("edges", []))}


if __name__ == "__main__":
    src = Path(__file__).parent.parent / "entity_source.txt"
    if src.exists():
        r = run_extraction_pipeline(source_file=str(src))
        print(r["pipeline_summary"])
        print("  Issues: %d" % r['validation']['issue_count'])
        print("  Modules: %d" % len(r['statistics']['module_distribution']))
