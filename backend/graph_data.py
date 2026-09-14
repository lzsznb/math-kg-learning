import json
import networkx as nx
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "math_knowledge_network.json"
WEIGHTS_DIR = Path(__file__).parent.parent / "user" / "weights"

G = nx.DiGraph()
nodes_data = []
edges_data = []
node_dict = {}
_loaded = False

# 默认边权重
DEFAULT_WEIGHT = 1.0
_weight_cache = {}  # user_id -> { "from-to": weight }


def _edge_key(u, v):
    return f"{u}-{v}"


def _user_weights_path(user_id: str) -> Path:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    return WEIGHTS_DIR / f"{user_id}.json"


def load_user_weights(user_id: str) -> dict:
    """加载用户特定的边权重"""
    if user_id in _weight_cache:
        return _weight_cache[user_id]

    path = _user_weights_path(user_id)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            weights = json.load(f)
    else:
        # 初始化为默认权重
        weights = {_edge_key(e["from"], e["to"]): DEFAULT_WEIGHT for e in edges_data}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(weights, f, ensure_ascii=False, indent=2)

    _weight_cache[user_id] = weights
    return weights


def save_user_weights(user_id: str, weights: dict):
    """持久化用户边权重"""
    path = _user_weights_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(weights, f, ensure_ascii=False, indent=2)
    _weight_cache[user_id] = weights


def delete_user_weights(user_id: str):
    """删除用户权重文件及缓存"""
    path = _user_weights_path(user_id)
    if path.exists():
        path.unlink()
    _weight_cache.pop(user_id, None)


def init_user_weights(user_id: str):
    """初始化用户权重文件（若不存在）"""
    path = _user_weights_path(user_id)
    if not path.exists():
        weights = {_edge_key(e["from"], e["to"]): DEFAULT_WEIGHT for e in edges_data}
        save_user_weights(user_id, weights)


def update_edge_weight(user_id: str, from_node: int, to_node: int, delta: float) -> dict:
    """
    更新某条边的权重。
    delta > 0 表示变难/更重要，delta < 0 表示变易。
    权重范围 [0.1, 5.0]。
    """
    key = _edge_key(from_node, to_node)
    weights = load_user_weights(user_id)
    old = weights.get(key, DEFAULT_WEIGHT)
    new = max(0.1, min(5.0, old + delta))
    weights[key] = new
    save_user_weights(user_id, weights)
    return {"from": from_node, "to": to_node, "old_weight": round(old, 4), "new_weight": round(new, 4), "delta": round(delta, 4)}


def get_edge_weights(user_id: str) -> list:
    """返回用户的所有边权重列表，用于前端可视化"""
    weights = load_user_weights(user_id)
    result = []
    for e in edges_data:
        key = _edge_key(e["from"], e["to"])
        w = weights.get(key, DEFAULT_WEIGHT)
        result.append({
            "from": e["from"],
            "to": e["to"],
            "weight": w,
            "relation": e.get("relation", "前置依赖")
        })
    return result


def apply_progress_to_weights(user_id: str, progress: dict):
    """
    将用户学习进度（已会/薄弱）自动映射为权重调整：
    - 薄弱 → 该节点的入边 +0.3
    - 已会 → 该节点的入边 -0.1
    """
    weights = load_user_weights(user_id)
    changed = []
    for nid_str, status in progress.items():
        node_id = int(nid_str)
        if node_id not in node_dict:
            continue
        # 找到所有指向该节点的边
        for pre_id in G.predecessors(node_id):
            key = _edge_key(pre_id, node_id)
            old = weights.get(key, DEFAULT_WEIGHT)
            if status == "weak":
                new = max(0.1, min(5.0, old + 0.3))
            elif status == "mastered":
                new = max(0.1, min(5.0, old - 0.1))
            else:
                continue
            if abs(new - old) > 1e-6:
                weights[key] = new
                changed.append({"from": pre_id, "to": node_id, "old": round(old, 4), "new": round(new, 4)})
    if changed:
        save_user_weights(user_id, weights)
    return changed


def load_graph():
    global _loaded
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes_data.clear()
    nodes_data.extend(data["nodes"])

    edges_data.clear()
    edges_data.extend(data["edges"])

    node_dict.clear()
    for n in nodes_data:
        node_dict[n["id"]] = n

    G.clear()
    for node in nodes_data:
        attrs = {k: v for k, v in node.items() if k != "id"}
        G.add_node(node["id"], **attrs)
    for edge in edges_data:
        G.add_edge(edge["from"], edge["to"], relation=edge.get("relation", "前置依赖"))

    _loaded = True


def build_knowledge_context() -> str:
    mod_nodes = {}
    for n in nodes_data:
        mod = n.get("module", "未知")
        mod_nodes.setdefault(mod, []).append(n["name"])
    context = "高中数学知识网络（按模块分组）：\n"
    for mod, names in mod_nodes.items():
        context += f"\n【{mod}】\n" + "\n".join(f"  - {name}" for name in names)
    context += "\n\n前置依赖关系：\n"
    for e in edges_data:
        fm = node_dict.get(e["from"], {}).get("name", str(e["from"]))
        to = node_dict.get(e["to"], {}).get("name", str(e["to"]))
        context += f"  {fm} → {to}\n"
    return context


def find_related_nodes(text: str) -> list:
    related = []
    for n in nodes_data:
        if n["name"] in text:
            related.append({"id": n["id"], "name": n["name"], "module": n["module"]})
    return related


def get_triples(relation_type=None):
    """
    返回知识图谱的全部三元组列表。
    支持按关系类型筛选：'前置依赖'、'所属模块'、'难度等级'
    """
    triples = []
    # 前置依赖
    if relation_type is None or relation_type == "前置依赖":
        for e in edges_data:
            src = node_dict.get(e["from"], {})
            tgt = node_dict.get(e["to"], {})
            triples.append({
                "subject_id": e["from"],
                "subject_name": src.get("name", str(e["from"])),
                "predicate": "前置依赖",
                "object_id": e["to"],
                "object_name": tgt.get("name", str(e["to"]))
            })
    # 所属模块
    if relation_type is None or relation_type == "所属模块":
        for n in nodes_data:
            triples.append({
                "subject_id": n["id"],
                "subject_name": n["name"],
                "predicate": "所属模块",
                "object_id": n["module"],
                "object_name": n["module"]
            })
    # 难度等级
    if relation_type is None or relation_type == "难度等级":
        levels = {1: "1级（最易）", 2: "2级（较易）", 3: "3级（中等）", 4: "4级（较难）"}
        for n in nodes_data:
            triples.append({
                "subject_id": n["id"],
                "subject_name": n["name"],
                "predicate": "难度等级",
                "object_id": n["difficulty"],
                "object_name": levels.get(n["difficulty"], str(n["difficulty"]))
            })
    return triples
