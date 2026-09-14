from langchain_core.tools import tool
from .graph_data import G, node_dict
from .graph_algo import community_detection, explain_community, dijkstra, analyze_user_model
from .graph_data import load_user_weights, update_edge_weight as _update_weight
import json
import networkx as nx


@tool
def get_node_info(node_id: int) -> dict:
    """查询知识点的详细信息，包括所属模块、难度、前置知识和后置知识"""
    if G is None:
        return {"error": "图未初始化"}
    node = node_dict.get(node_id)
    if not node:
        return {"error": f"知识点 {node_id} 不存在"}
    return {
        "id": node_id,
        "name": node["name"],
        "module": node["module"],
        "difficulty": node.get("difficulty", 1),
        "prerequisites": [
            {"id": nid, "name": node_dict[nid]["name"]}
            for nid in G.predecessors(node_id) if nid in node_dict
        ],
        "dependents": [
            {"id": nid, "name": node_dict[nid]["name"]}
            for nid in G.successors(node_id) if nid in node_dict
        ]
    }


@tool
def find_shortest_path(start_id: int, end_id: int) -> dict:
    """查找两个知识点之间的最短学习路径（基于前置依赖关系）"""
    if G is None:
        return {"error": "图未初始化"}
    if start_id not in G:
        return {"error": f"起始知识点 {start_id} 不存在"}
    if end_id not in G:
        return {"error": f"目标知识点 {end_id} 不存在"}
    try:
        path = nx.shortest_path(G, source=start_id, target=end_id)
        return {
            "path": [{"id": nid, "name": node_dict[nid]["name"]} for nid in path if nid in node_dict],
            "length": len(path) - 1,
            "start_name": node_dict[start_id].get("name", str(start_id)),
            "end_name": node_dict[end_id].get("name", str(end_id))
        }
    except nx.NetworkXNoPath:
        return {"error": "两知识点之间无可达路径"}


@tool
def analyze_weak_points(progress: str) -> dict:
    """分析用户的学习薄弱点。参数 progress 是 JSON 字符串，格式为 {"节点ID": "状态"}"""
    if G is None:
        return {"error": "图未初始化"}
    try:
        progress_dict = json.loads(progress) if isinstance(progress, str) else progress
    except json.JSONDecodeError:
        return {"error": "progress 格式错误"}
    weak_points = []
    missing_prerequisites = {}
    for nid_str, status in progress_dict.items():
        if status == "weak":
            node_id = int(nid_str)
            if node_id in node_dict:
                weak_points.append({"id": node_id, "name": node_dict[node_id]["name"], "module": node_dict[node_id]["module"]})
    for wp in weak_points:
        nid = wp["id"]
        missing = []
        for pre_id in G.predecessors(nid):
            if progress_dict.get(str(pre_id), "unlearned") != "mastered":
                info = node_dict.get(pre_id)
                if info:
                    missing.append({"id": pre_id, "name": info["name"], "status": progress_dict.get(str(pre_id), "unlearned")})
        if missing:
            missing_prerequisites[str(nid)] = {"name": wp["name"], "missing": missing}
    return {"weak_points": weak_points, "missing_prerequisites": missing_prerequisites, "total_weak": len(weak_points), "total_missing": sum(len(v["missing"]) for v in missing_prerequisites.values())}


@tool
def get_community_analysis() -> dict:
    """获取知识图谱的社区/模块分析结果，返回每个社区包含的知识点、模块度及社区解释"""
    if G is None:
        return {"error": "图未初始化"}
    try:
        communities = community_detection(G)
        m = G.number_of_edges()
        total_internal = 0
        result = []
        for i, community in enumerate(communities, 1):
            L = sum(1 for u, v in G.edges() if u in community and v in community)
            K = sum(G.degree(n) for n in community)
            comm_Q = round(L / m - (K / (2 * m)) ** 2, 6) if m > 0 else 0
            total_internal += L
            modules = {}
            nodes = []
            for nid in community:
                if nid in node_dict:
                    info = node_dict[nid]
                    nodes.append({"id": nid, "name": info["name"], "module": info["module"]})
                    mod = info.get("module", "未知")
                    modules[mod] = modules.get(mod, 0) + 1
            main_mod = max(modules, key=modules.get) if modules else ""
            density = round(L / (len(community) * (len(community) - 1) * 0.5), 4) if len(community) > 1 else 1
            result.append({
                "community_id": i,
                "nodes": nodes,
                "size": len(community),
                "internal_edges": L,
                "modularity_contribution": comm_Q,
                "main_module": main_mod,
                "internal_density": density
            })
        total_Q = round(sum(c["modularity_contribution"] for c in result), 6)
        return {
            "communities": result,
            "total_communities": len(result),
            "modularity": total_Q,
            "algorithm": "Newman贪婪模块度优化（自实现）"
        }
    except Exception as e:
        return {"error": f"社区分析失败: {str(e)}"}


@tool
def explain_node_community(node_id: int) -> dict:
    """解释某个知识点为什么属于其所在的社区，包括社区特征、内部连接密度等"""
    if G is None:
        return {"error": "图未初始化"}
    return explain_community(G, node_dict, node_id)


@tool
def get_centrality_analysis() -> dict:
    """获取知识图谱中重要的知识点排名，包括度中心性和介数中心性 Top 10"""
    if G is None:
        return {"error": "图未初始化"}
    degree = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G)
    def top10(cent):
        return [{"id": nid, "name": node_dict[nid]["name"], "module": node_dict[nid]["module"], "score": round(score, 4)}
                for nid, score in sorted(cent.items(), key=lambda x: x[1], reverse=True)[:10] if nid in node_dict]
    return {"degree_centrality": top10(degree), "betweenness_centrality": top10(betweenness)}


@tool
def update_edge_weight_tool(from_node: int, to_node: int, delta: float, user_id: str = "default") -> dict:
    """根据用户反馈调整知识点之间边的权重。
    delta > 0 表示该前置知识更难/更重要（权重增加），delta < 0 表示变容易。
    权重用于自适应学习路径规划，高权重边会被 Dijkstra 算法避开。"""
    if G is None:
        return {"error": "图未初始化"}
    if from_node not in G or to_node not in G:
        return {"error": "边不存在"}
    return _update_weight(user_id, from_node, to_node, delta)


@tool
def get_adaptive_path_tool(target_id: int, user_id: str = "default", progress: str = "{}") -> dict:
    """基于用户特定边权重的自适应学习路径规划（自实现 Dijkstra）。
    从已掌握知识点出发，找到目标知识点的最小加权路径。
    权重越高的边意味着越难，算法会尽量避开。
    参数 progress 是 JSON 字符串，格式为 {"节点ID": "mastered/weak/unlearned"}"""
    if G is None or target_id not in G:
        return {"error": "目标知识点不存在"}
    try:
        prog = json.loads(progress) if isinstance(progress, str) else progress
    except json.JSONDecodeError:
        return {"error": "progress 格式错误"}
    weights = load_user_weights(user_id)
    mastered = [int(k) for k, v in prog.items() if v == "mastered"] or [n for n in G.nodes() if G.in_degree(n) == 0]
    best = None
    best_weight = float("inf")
    for start in mastered:
        if start == target_id:
            best, best_weight = [start], 0
            break
        result = dijkstra(G, start, target_id, weights)
        if "error" not in result and result["total_weight"] < best_weight:
            best = result["path"]
            best_weight = result["total_weight"]
    if best is None:
        return {"error": "无法找到加权学习路径"}
    details = [{"id": nid, "name": node_dict[nid]["name"], "module": node_dict[nid]["module"]}
               for nid in best if nid in node_dict]
    return {
        "path": details,
        "total_weight": round(best_weight, 4),
        "length": len(best) - 1,
        "algorithm": "自实现 Dijkstra（加权最短路径）"
    }


@tool
def analyze_user_model_tool(progress: str) -> dict:
    """综合分析用户的知识模型：模块级掌握度、薄弱点诊断、缺失前置知识、个性化学习推荐。
    参数 progress 是 JSON 字符串，格式为 {"节点ID": "mastered/weak/unlearned"}"""
    if G is None:
        return {"error": "图未初始化"}
    try:
        prog = json.loads(progress) if isinstance(progress, str) else progress
    except json.JSONDecodeError:
        return {"error": "progress 格式错误"}
    modules = sorted(set(n.get("module", "未知") for n in node_dict.values()))
    return analyze_user_model(G, node_dict, prog, modules)


knowledge_graph_tools = [
    get_node_info, find_shortest_path, analyze_weak_points,
    get_community_analysis, explain_node_community, get_centrality_analysis,
    update_edge_weight_tool, get_adaptive_path_tool,
    analyze_user_model_tool
]
