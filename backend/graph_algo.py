import networkx as nx


def pagerank(graph, damping: float = 0.85, max_iter: int = 100, tol: float = 1e-6) -> dict:
    """
    自实现 PageRank 算法。
    
    PR(p_i) = (1-d)/N + d * Σ_{p_j ∈ M(p_i)} PR(p_j) / L(p_j)
    
    参数:
        graph: 有向图 (networkx.DiGraph)
        damping: 阻尼系数（默认 0.85）
        max_iter: 最大迭代次数
        tol: 收敛阈值
    
    返回:
        dict: {node_id: pagerank_score}
    """
    N = graph.number_of_nodes()
    if N == 0:
        return {}

    nodes = sorted(graph.nodes())
    node_index = {n: i for i, n in enumerate(nodes)}
    index_node = {i: n for i, n in enumerate(nodes)}

    # 构建入边列表和出度
    in_links = [[] for _ in range(N)]
    out_degree = [0] * N
    for u, v in graph.edges():
        in_links[node_index[v]].append(node_index[u])
        out_degree[node_index[u]] += 1

    # 悬垂节点（出度为 0）
    dangling = [i for i in range(N) if out_degree[i] == 0]

    pr = [1.0 / N] * N
    for _ in range(max_iter):
        dangling_sum = sum(pr[i] for i in dangling)
        new_pr = [0.0] * N
        for i in range(N):
            s = sum(pr[j] / out_degree[j] for j in in_links[i] if out_degree[j] > 0)
            new_pr[i] = (1.0 - damping) / N + damping * s + damping * dangling_sum / N
        diff = sum(abs(new_pr[i] - pr[i]) for i in range(N))
        pr = new_pr
        if diff < tol * N:
            break

    return {index_node[i]: pr[i] for i in range(N)}


def pagerank_top10(graph, node_dict: dict) -> list:
    """计算 PageRank 并返回 Top 10 知识点及排名变化。"""
    scores = pagerank(graph)
    sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    result = []
    for rank, (nid, score) in enumerate(sorted_nodes[:10], 1):
        info = node_dict.get(nid)
        if info:
            result.append({
                "rank": rank,
                "id": nid,
                "name": info["name"],
                "module": info["module"],
                "score": round(score, 6)
            })
    return result


def community_detection(graph) -> list:
    """
    自实现 Newman 贪婪模块度优化社区发现算法。

    原理：
    - 每个节点初始化为一个独立社区
    - 每次迭代选择使模块度增量 ΔQ 最大的社区对合并
    - 直到所有合并均不能提高模块度
    - 返回模块度最高时的社区划分

    模块度公式：Q = Σ_c [(L_c/m) - (k_c/(2m))²]
    ΔQ(a,b) = 2 * (e_ab/m - k_a·k_b / 4m²)

    参数:
        graph: networkx.Graph / DiGraph

    返回:
        list[set]: 每个 set 为一个社区内的节点 ID 集合
    """
    G = graph.to_undirected() if graph.is_directed() else graph.copy()

    nodes = list(G.nodes())
    n = len(nodes)
    if n <= 1:
        return [{node} for node in nodes]

    m = G.number_of_edges()
    if m == 0:
        return [{node} for node in nodes]

    node_idx = {node: i for i, node in enumerate(nodes)}

    # 每个节点的初始社区 ID = 其索引
    comm_of = list(range(n))

    # 社区数据
    comm_degree = {i: G.degree(node) for i, node in enumerate(nodes)}
    comm_internal = {i: 0 for i in range(n)}
    comm_members = {i: {node} for i, node in enumerate(nodes)}

    # 社区间边数: (a,b) -> count, a < b
    between = {}
    for u, v in G.edges():
        i, j = node_idx[u], node_idx[v]
        if i == j:
            comm_internal[i] += 1
        else:
            key = (i, j) if i < j else (j, i)
            between[key] = between.get(key, 0) + 1

    def _modularity():
        Q = 0.0
        for cid in comm_members:
            L = comm_internal.get(cid, 0)
            K = comm_degree.get(cid, 0)
            Q += L / m - (K / (2 * m)) ** 2
        return Q

    best_Q = _modularity()
    best_comms = [set(comm_members[cid]) for cid in comm_members]

    while len(comm_members) > 1:
        best_pair = None
        best_delta = -float('inf')

        for (a, b), w in between.items():
            da = comm_degree.get(a, 0)
            db = comm_degree.get(b, 0)
            delta = 2 * (w / m - da * db / (4 * m * m))
            if delta > best_delta:
                best_delta = delta
                best_pair = (a, b)

        if best_delta <= 1e-10 or best_pair is None:
            break

        a, b = best_pair

        # 合并 b 到 a
        for node in comm_members[b]:
            comm_of[node_idx[node]] = a

        comm_members[a] |= comm_members[b]
        del comm_members[b]

        comm_degree[a] = comm_degree.get(a, 0) + comm_degree.get(b, 0)
        del comm_degree[b]

        comm_internal[a] = comm_internal.get(a, 0) + comm_internal.get(b, 0) + between.pop(
            (a, b) if a < b else (b, a), 0
        )
        del comm_internal[b]

        # 更新 between：将 b 替换为 a
        new_btw = {}
        for (x, y), w in between.items():
            nx = a if x == b else x
            ny = a if y == b else y
            if nx != ny:
                key = (nx, ny) if nx < ny else (ny, nx)
                new_btw[key] = new_btw.get(key, 0) + w
        between = new_btw

        Q = _modularity()
        if Q > best_Q:
            best_Q = Q
            best_comms = [set(comm_members[cid]) for cid in comm_members]

    return best_comms


def community_compare(graph) -> dict:
    """
    对比自实现社区发现 vs NetworkX 内置算法 (girvan_newman) 的结果。

    返回:
        dict 包含两种算法的社区划分、模块度、以及差异总结
    """
    custom = community_detection(graph)
    custom_Q = _compute_modularity_for_partition(graph, custom)

    nx_result = _nx_community_detection(graph)
    nx_Q = _compute_modularity_for_partition(graph, nx_result)

    return {
        "custom": {
            "communities": _format_communities(custom, graph),
            "modularity": round(custom_Q, 6),
            "count": len(custom)
        },
        "networkx": {
            "communities": _format_communities(nx_result, graph),
            "modularity": round(nx_Q, 6),
            "count": len(nx_result)
        },
        "comparison": {
            "custom_better": custom_Q > nx_Q + 1e-10,
            "nx_better": nx_Q > custom_Q + 1e-10,
            "equal": abs(custom_Q - nx_Q) < 1e-10
        }
    }


def explain_community(graph, node_dict: dict, node_id: int) -> dict:
    """
    解释某个知识点为什么属于其所在的社区。

    返回社区内共同特征、内部连接密度、模块贡献等信息。
    """
    comms = community_detection(graph)
    G = graph.to_undirected() if graph.is_directed() else graph

    target_comm = None
    for comm in comms:
        if node_id in comm:
            target_comm = comm
            break

    if target_comm is None:
        return {"error": "节点不在任何社区中"}

    members = [node_dict.get(nid, {}) for nid in target_comm if nid in node_dict]
    modules = {}
    for m in members:
        mod = m.get("module", "未知")
        modules[mod] = modules.get(mod, 0) + 1

    # 内部边数
    internal_edges = sum(1 for u, v in G.edges() if u in target_comm and v in target_comm)
    total_possible = len(target_comm) * (len(target_comm) - 1) / 2
    density = internal_edges / total_possible if total_possible > 0 else 0

    # 到其他社区的边
    external_edges = sum(1 for u, v in G.edges()
                         if (u in target_comm) != (v in target_comm))

    m_total = G.number_of_edges()
    k_sum = sum(G.degree(n) for n in target_comm)
    comm_Q = internal_edges / m_total - (k_sum / (2 * m_total)) ** 2

    return {
        "node_id": node_id,
        "node_name": node_dict.get(node_id, {}).get("name", str(node_id)),
        "community_id": None,
        "community_size": len(target_comm),
        "community_members": [{"id": nid, "name": node_dict.get(nid, {}).get("name", str(nid)),
                               "module": node_dict.get(nid, {}).get("module", "")}
                              for nid in target_comm if nid in node_dict],
        "module_distribution": modules,
        "main_module": max(modules, key=modules.get) if modules else "",
        "internal_edges": internal_edges,
        "external_edges": external_edges,
        "internal_density": round(density, 4),
        "modularity_contribution": round(comm_Q, 6),
        "explanation": _explain_text(target_comm, node_id, modules, internal_edges, external_edges, density, node_dict)
    }


def _compute_modularity_for_partition(graph, communities: list) -> float:
    G = graph.to_undirected() if graph.is_directed() else graph
    m = G.number_of_edges()
    if m == 0:
        return 0.0
    Q = 0.0
    for comm in communities:
        L = sum(1 for u, v in G.edges() if u in comm and v in comm)
        K = sum(G.degree(n) for n in comm)
        Q += L / m - (K / (2 * m)) ** 2
    return Q


def _format_communities(communities: list, graph) -> list:
    """将社区转为可序列化格式"""
    result = []
    for i, comm in enumerate(communities, 1):
        nodes = [{"id": nid} for nid in comm]
        result.append({"community_id": i, "nodes": nodes, "size": len(comm)})
    return result


def _nx_community_detection(graph) -> list:
    """使用 NetworkX 内置 girvan_newman 进行社区发现"""
    G = graph.to_undirected() if graph.is_directed() else graph
    try:
        communities = next(nx.community.girvan_newman(G))
        return [set(c) for c in communities]
    except Exception:
        return [{node} for node in G.nodes()]


def _explain_text(community, node_id, modules, internal_edges, external_edges, density, node_dict) -> str:
    """生成社区归属的自然语言解释"""
    node_name = node_dict.get(node_id, {}).get("name", str(node_id))
    main_mod = max(modules, key=modules.get) if modules else ""
    mod_detail = "、".join(f"{m}({c}个)" for m, c in sorted(modules.items(), key=lambda x: -x[1]))

    parts = [
        f"「{node_name}」所在的社区共有 {len(community)} 个知识点，",
        f"主要来自「{main_mod}」模块（{mod_detail}）。",
        f"社区内部连接密度为 {density:.1%}（内部边 {internal_edges} 条 vs 外部边 {external_edges} 条），"
    ]
    if density > 0.3:
        parts.append("说明这些知识点联系紧密，共享相似的前置依赖关系，经常一起学习。")
    else:
        parts.append("说明这些知识点之间有一定关联，但并非强耦合。")

    return "".join(parts)


def dijkstra(graph, source, target, weight_map: dict) -> dict:
    """
    自实现 Dijkstra 最短加权路径算法。

    参数:
        graph: networkx.DiGraph — 有向图
        source: 起始节点 ID
        target: 目标节点 ID
        weight_map: dict, key="from-to", value=权重

    返回:
        dict: {"path": [...], "total_weight": float, "length": int}
              或 {"error": "..."}
    """
    if source not in graph or target not in graph:
        return {"error": "节点不存在于图中"}

    INF = float('inf')
    dist = {n: INF for n in graph.nodes()}
    prev = {n: None for n in graph.nodes()}
    dist[source] = 0

    unvisited = set(graph.nodes())

    while unvisited:
        # 选择距离最小的未访问节点
        u = min(unvisited, key=lambda n: dist[n])
        if dist[u] == INF:
            break
        if u == target:
            break
        unvisited.remove(u)

        for v in graph.successors(u):
            if v not in unvisited:
                continue
            key = f"{u}-{v}"
            w = weight_map.get(key, 1.0)
            alt = dist[u] + w
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u

    if dist[target] == INF:
        return {"error": f"从节点 {source} 到 {target} 无可达路径"}

    # 回溯路径
    path = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()

    return {
        "path": path,
        "total_weight": round(dist[target], 4),
        "length": len(path) - 1
    }


def analyze_user_model(graph, node_dict: dict, progress: dict, node_modules: list = None) -> dict:
    """
    综合分析用户知识模型。
    
    参数:
        graph: networkx.DiGraph
        node_dict: {node_id: info}
        progress: {"node_id": "mastered/weak/unlearned"}
        node_modules: 所有模块名列表（用于排序）
    
    返回:
        包含模块掌握度、薄弱分析、学习建议的综合报告
    """
    G_dir = graph if graph.is_directed() else graph.to_directed()
    G_undir = graph.to_undirected() if graph.is_directed() else graph

    # --- 模块级掌握度 ---
    module_stats = {}
    for nid, info in node_dict.items():
        mod = info.get("module", "未知")
        if mod not in module_stats:
            module_stats[mod] = {"total": 0, "mastered": 0, "weak": 0, "unlearned": 0}
        module_stats[mod]["total"] += 1
        status = progress.get(str(nid), "unlearned")
        module_stats[mod][status] += 1

    module_mastery = []
    for mod, st in module_stats.items():
        pct = round(st["mastered"] / st["total"] * 100, 1) if st["total"] > 0 else 0
        module_mastery.append({
            "module": mod,
            "total": st["total"],
            "mastered": st["mastered"],
            "weak": st["weak"],
            "unlearned": st["unlearned"],
            "mastery_pct": pct,
            "status": "strong" if pct >= 80 else ("moderate" if pct >= 40 else "weak")
        })

    if node_modules:
        mod_order = {m: i for i, m in enumerate(node_modules)}
        module_mastery.sort(key=lambda x: mod_order.get(x["module"], 999))

    overall_stats = {"total": sum(m["total"] for m in module_mastery),
                     "mastered": sum(m["mastered"] for m in module_mastery),
                     "weak": sum(m["weak"] for m in module_mastery),
                     "unlearned": sum(m["unlearned"] for m in module_mastery)}

    # --- 薄弱点诊断（含缺失前置分析） ---
    weak_points = []
    missing_prereqs = {}

    weak_ids = [int(k) for k, v in progress.items() if v == "weak"]
    for nid in weak_ids:
        if nid not in node_dict:
            continue
        missing = []
        for pre in G_dir.predecessors(nid):
            pre_status = progress.get(str(pre), "unlearned")
            if pre_status != "mastered":
                info = node_dict.get(pre)
                if info:
                    missing.append({"id": pre, "name": info["name"],
                                    "module": info.get("module", ""),
                                    "status": pre_status})
        info = node_dict[nid]
        weak_points.append({
            "id": nid, "name": info["name"], "module": info.get("module", ""),
            "difficulty": info.get("difficulty", 1),
            "missing_prerequisites": missing,
            "can_study_now": len(missing) == 0
        })
        if missing:
            missing_prereqs[str(nid)] = {"name": info["name"], "missing": missing}

    # 按难度排序（先易后难）
    weak_points.sort(key=lambda x: x["difficulty"])

    # --- 推荐学习顺序 ---
    G_temp = G_dir.copy()
    recommendations = []
    ranked = set()

    while len(ranked) < G_temp.number_of_nodes():
        # 找到所有前置已掌握的未学节点
        candidates = []
        for n in G_temp.nodes():
            if n in ranked:
                continue
            pre_statuses = [progress.get(str(p), "unlearned") for p in G_temp.predecessors(n)]
            prereqs_done = all(s == "mastered" for s in pre_statuses) or G_temp.in_degree(n) == 0
            if prereqs_done and progress.get(str(n), "unlearned") != "mastered":
                cand = {
                    "id": n,
                    "name": node_dict.get(n, {}).get("name", str(n)),
                    "module": node_dict.get(n, {}).get("module", ""),
                    "difficulty": node_dict.get(n, {}).get("difficulty", 1),
                    "status": progress.get(str(n), "unlearned"),
                    "in_degree": G_temp.in_degree(n)
                }
                # 计算中心性权重 (介数中心性高的优先学)
                # 用入度近似中心性
                candidates.append(cand)

        if not candidates:
            break

        # 优先推荐：薄弱 > 未学，入度高的优先（中心节点）
        candidates.sort(key=lambda x: (
            0 if x["status"] == "weak" else 1,
            -x["in_degree"],
            x["difficulty"]
        ))
        pick = candidates[0]
        ranked.add(pick["id"])
        recommendations.append(pick)

    # --- 学习路径建议（针对薄弱点） ---
    learning_paths = []
    for wp in weak_points[:5]:
        if wp["can_study_now"]:
            try:
                path = nx.shortest_path(G_dir, source=wp["id"], target=wp["id"])
                learning_paths.append({
                    "target": {"id": wp["id"], "name": wp["name"]},
                    "type": "复习",
                    "steps": [{"id": wp["id"], "name": wp["name"]}]
                })
            except Exception:
                pass
        else:
            # 从缺失前置开始构建路径
            missing_first = wp["missing_prerequisites"][0]
            try:
                path_nodes = [missing_first["id"]] + [wp["id"]]
                learning_paths.append({
                    "target": {"id": wp["id"], "name": wp["name"]},
                    "type": "补前置+攻克",
                    "steps": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))}
                              for n in path_nodes if n in node_dict]
                })
            except Exception:
                pass

    return {
        "user_stats": {
            "total_nodes": overall_stats["total"],
            "mastered": overall_stats["mastered"],
            "weak": overall_stats["weak"],
            "unlearned": overall_stats["unlearned"],
            "mastery_pct": round(overall_stats["mastered"] / max(overall_stats["total"], 1) * 100, 1)
        },
        "module_mastery": module_mastery,
        "strong_modules": [m["module"] for m in module_mastery if m["status"] == "strong"],
        "weak_modules": [m["module"] for m in module_mastery if m["status"] == "weak"],
        "weak_points": weak_points,
        "missing_prerequisites": missing_prereqs,
        "recommendations": recommendations[:20],
        "learning_paths": learning_paths[:5]
    }


# ========== 网络科学综合分析（新增） ==========

import random as _random
import math as _math
from collections import deque as _deque


def scale_free_analysis(graph, node_dict):
    """
    无标度网络分析：度分布 + 幂律拟合。
    
    返回：
        in_degree_dist: [{degree, count}] 入度分布
        out_degree_dist: [{degree, count}] 出度分布
        power_law: {alpha, xmin, ks_stat} 幂律拟合参数
        summary: 文字分析
    """
    in_degrees = [d for _, d in graph.in_degree()]
    out_degrees = [d for _, d in graph.out_degree()]

    def _dist(degrees):
        dist = {}
        for d in degrees:
            dist[d] = dist.get(d, 0) + 1
        return [{"degree": k, "count": v} for k, v in sorted(dist.items())]

    def _fit_power_law(degrees):
        """简单幂律拟合：最大似然估计 alpha (连续近似)"""
        xs = [d for d in degrees if d > 0]
        if len(xs) < 10:
            return {"alpha": None, "xmin": 1, "ks_stat": None}
        xmin = min(xs)
        n = len(xs)
        sum_log = sum(_math.log(x / xmin) for x in xs)
        alpha = 1 + n / sum_log if sum_log > 0 else None
        # KS 统计量
        if alpha:
            empirical = sorted(xs)
            ks = max(abs(1 - (xmin / x) ** (alpha - 1) - i / n)
                     for i, x in enumerate(empirical))
        else:
            ks = None
        return {"alpha": round(alpha, 4) if alpha else None,
                "xmin": xmin,
                "ks_stat": round(ks, 4) if ks else None}

    in_fit = _fit_power_law(in_degrees)
    out_fit = _fit_power_law(out_degrees)

    total = graph.number_of_nodes()
    max_in = max(in_degrees) if in_degrees else 0
    max_out = max(out_degrees) if out_degrees else 0
    hub_nodes_in = sorted(
        [(n, d) for n, d in graph.in_degree() if d == max_in],
        key=lambda x: -x[1]
    )[:3]
    hub_nodes_out = sorted(
        [(n, d) for n, d in graph.out_degree() if d == max_out],
        key=lambda x: -x[1]
    )[:3]

    hub_names_in = [{"id": n, "name": node_dict.get(n, {}).get("name", str(n)), "degree": d}
                    for n, d in hub_nodes_in]
    hub_names_out = [{"id": n, "name": node_dict.get(n, {}).get("name", str(n)), "degree": d}
                     for n, d in hub_nodes_out]

    return {
        "in_degree_dist": _dist(in_degrees),
        "out_degree_dist": _dist(out_degrees),
        "in_power_law": in_fit,
        "out_power_law": out_fit,
        "hub_nodes_in": hub_names_in,
        "hub_nodes_out": hub_names_out,
        "summary": (
            f"入度分布幂律指数 α={in_fit['alpha']}，"
            f"出度分布幂律指数 α={out_fit['alpha']}。"
            f"入度最大的知识点是「{hub_names_in[0]['name'] if hub_names_in else '无'}」(入度={max_in})，"
            f"出度最大的知识点是「{hub_names_out[0]['name'] if hub_names_out else '无'}」(出度={max_out})。"
        )
    }


def small_world_analysis(graph, node_dict):
    """
    小世界网络分析。
    
    比较真实网络与同等规模随机图的：
    - 平均路径长度
    - 聚类系数
    - 小世界系数 σ = (C/C_rand) / (L/L_rand)
    """
    G = graph.to_undirected() if graph.is_directed() else graph
    n = G.number_of_nodes()

    # 真实网络
    try:
        # 只对最大连通子图计算路径长度
        components = list(nx.connected_components(G))
        largest = G.subgraph(max(components, key=len))
        avg_path = nx.average_shortest_path_length(largest)
    except Exception:
        avg_path = None
    clustering = nx.average_clustering(G)

    # 随机图（ER模型，相同节点数和边数）
    m = G.number_of_edges()
    p = 2 * m / (n * (n - 1)) if n > 1 else 0
    rand_G = nx.erdos_renyi_graph(n, p, seed=42)
    try:
        rand_components = list(nx.connected_components(rand_G))
        rand_largest = rand_G.subgraph(max(rand_components, key=len))
        rand_avg_path = nx.average_shortest_path_length(rand_largest)
    except Exception:
        rand_avg_path = None
    rand_clustering = nx.average_clustering(rand_G)

    # 小世界系数 σ
    if rand_avg_path and avg_path and rand_clustering > 0 and clustering > 0:
        sigma = (clustering / rand_clustering) / (avg_path / rand_avg_path)
    else:
        sigma = None

    return {
        "real_network": {
            "avg_path_length": round(avg_path, 4) if avg_path else None,
            "clustering_coefficient": round(clustering, 4),
            "nodes": n,
            "edges": m
        },
        "random_network": {
            "avg_path_length": round(rand_avg_path, 4) if rand_avg_path else None,
            "clustering_coefficient": round(rand_clustering, 4),
            "nodes": rand_G.number_of_nodes(),
            "edges": rand_G.number_of_edges()
        },
        "sigma": round(sigma, 4) if sigma else None,
        "is_small_world": sigma > 1 if sigma else None,
        "summary": (
            f"真实网络：平均路径长度={avg_path}，聚类系数={clustering}；"
            f"等价随机图：平均路径长度={rand_avg_path}，聚类系数={rand_clustering}；"
            f"小世界系数 σ={sigma}。"
            f"{'该知识网络具有小世界特性。' if sigma and sigma > 1 else '该知识网络不具有明显的小世界特性。'}"
        )
    }


def robustness_analysis(graph, node_dict):
    """
    网络鲁棒性分析。
    
    模拟随机攻击和蓄意攻击（按度排序），
    观察最大连通子图大小随移除节点比例的变化。
    """
    G = graph.to_undirected() if graph.is_directed() else graph
    nodes = list(G.nodes())
    n_total = len(nodes)

    def _largest_component_size(g):
        if g.number_of_nodes() == 0:
            return 0
        components = list(nx.connected_components(g))
        return max(len(c) for c in components)

    steps = 20
    random_curve = []
    targeted_curve = []

    # 随机攻击
    G_rand = G.copy()
    shuffled = nodes.copy()
    _random.shuffle(shuffled)
    for i in range(steps):
        remove_count = int((i + 1) / steps * n_total)
        current = shuffled[:remove_count]
        g = G_rand.copy()
        g.remove_nodes_from(current)
        largest = _largest_component_size(g)
        random_curve.append({
            "removed_pct": round((i + 1) / steps * 100, 1),
            "largest_component_pct": round(largest / n_total * 100, 1),
            "largest_component_size": largest
        })

    # 蓄意攻击（按度从大到小）
    G_tar = G.copy()
    sorted_by_deg = sorted(nodes, key=lambda n: G_tar.degree(n), reverse=True)
    for i in range(steps):
        remove_count = int((i + 1) / steps * n_total)
        current = sorted_by_deg[:remove_count]
        g = G_tar.copy()
        g.remove_nodes_from(current)
        largest = _largest_component_size(g)
        targeted_curve.append({
            "removed_pct": round((i + 1) / steps * 100, 1),
            "largest_component_pct": round(largest / n_total * 100, 1),
            "largest_component_size": largest
        })

    return {
        "random_attack": random_curve,
        "targeted_attack": targeted_curve,
        "summary": (
            f"随机攻击：移除 50% 节点后，最大连通子图占比 {random_curve[9]['largest_component_pct']}%；"
            f"蓄意攻击：移除 50% 节点后，最大连通子图占比 {targeted_curve[9]['largest_component_pct']}%。"
            f"该网络{'对随机攻击具有鲁棒性，但对蓄意攻击脆弱' if targeted_curve[9]['largest_component_pct'] < random_curve[9]['largest_component_pct'] else '对两种攻击表现相似'}。"
        )
    }


def influence_maximization(graph, node_dict, k=5, mc_sims=100):
    """
    影响力最大化——贪心算法（独立级联模型）。
    
    使用贪心方法选择 top-k 种子节点，最大化预期影响力传播。
    对比策略：贪心 vs 高度数 vs PageRank。
    
    参数：
        graph: 有向图（信息从先修节点流向依赖节点）
        node_dict: 节点信息
        k: 种子集大小
        mc_sims: 蒙特卡洛模拟次数
    
    返回：
        seeds: 贪心选出的 top-k
        comparison: 各策略的影响力对比
    """
    G = graph if graph.is_directed() else graph.to_directed()
    nodes = list(G.nodes())
    activation_prob = 0.3  # IC 模型传播概率

    def _ic_spread(seeds):
        """独立级联模型模拟"""
        total = 0
        for _ in range(mc_sims):
            activated = set(seeds)
            frontier = _deque(seeds)
            while frontier:
                u = frontier.popleft()
                for v in G.successors(u):
                    if v not in activated and _random.random() < activation_prob:
                        activated.add(v)
                        frontier.append(v)
            total += len(activated)
        return total / mc_sims

    # 贪心算法
    greedy_seeds = []
    greedy_spreads = []
    remaining = set(nodes)
    for _ in range(min(k, len(nodes))):
        best_node = None
        best_spread = -1
        for n in remaining:
            spread = _ic_spread(greedy_seeds + [n])
            if spread > best_spread:
                best_spread = spread
                best_node = n
        if best_node is not None:
            greedy_seeds.append(best_node)
            greedy_spreads.append(round(best_spread, 2))
            remaining.remove(best_node)

    # 高度数策略
    deg_sorted = sorted(nodes, key=lambda n: G.out_degree(n), reverse=True)[:k]
    deg_spread = round(_ic_spread(deg_sorted), 2)

    # PageRank 策略
    pr = pagerank(graph)
    pr_sorted = sorted(pr.keys(), key=lambda n: pr[n], reverse=True)[:k]
    pr_spread = round(_ic_spread(pr_sorted), 2)

    seed_info = []
    for i, nid in enumerate(greedy_seeds):
        info = node_dict.get(nid, {})
        seed_info.append({
            "rank": i + 1,
            "id": nid,
            "name": info.get("name", str(nid)),
            "module": info.get("module", ""),
            "influence_spread": greedy_spreads[i]
        })

    return {
        "seeds": seed_info,
        "greedy_spread": greedy_spreads[-1] if greedy_spreads else 0,
        "degree_spread": deg_spread,
        "pagerank_spread": pr_spread,
        "greedy_seeds": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in greedy_seeds],
        "degree_seeds": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in deg_sorted],
        "pagerank_seeds": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in pr_sorted],
        "activation_prob": activation_prob,
        "summary": (
            f"贪心算法选出 top-{k} 种子，预期影响力={greedy_spreads[-1] if greedy_spreads else 0}；"
            f"高度数策略影响力={deg_spread}；PageRank 策略影响力={pr_spread}。"
        )
    }


def hybrid_recommendation(graph, node_dict, progress, all_users_progress, top_n=10):
    """
    混合推荐：Graph + CF + LLM 分数加权融合。
    
    Graph 分数: PageRank 归一化 + 入度归一化
    CF 分数:  基于用户相似度的协同过滤
    LLM 分数: 基于知识点与用户薄弱点的语义关联
    
    返回推荐列表 + 各来源贡献占比。
    """
    import math as _math
    
    nodes = list(graph.nodes())
    # 候选节点：当前用户未掌握的
    candidates = [n for n in nodes
                  if progress.get(str(n), "unlearned") != "mastered" and n in node_dict]
    
    if not candidates:
        return {"recommendations": [], "contribution": {}, "explanation": "所有知识点已掌握"}
    
    # ─── 1. Graph 分数 ───
    pr_scores = pagerank(graph)
    max_pr = max(pr_scores.values()) if pr_scores else 1
    max_deg = max(graph.in_degree(n) for n in candidates) or 1
    
    graph_scores = {}
    for n in candidates:
        pr_norm = pr_scores.get(n, 0) / max_pr
        deg_norm = graph.in_degree(n) / max_deg
        graph_scores[n] = 0.6 * pr_norm + 0.4 * deg_norm
    
    # ─── 2. CF 分数 ───
    cf_scores = {}
    if all_users_progress and len(all_users_progress) > 1:
        # 构建用户-知识点矩阵 (只考虑 mastered)
        target_vec = {n: 1 if progress.get(str(n)) == "mastered" else 0 for n in nodes}
        
        similarities = []  # [(other_user, similarity)]
        for uid, uprogress in all_users_progress.items():
            other_vec = {n: 1 if uprogress.get(str(n)) == "mastered" else 0 for n in nodes}
            # 余弦相似度
            dot = sum(target_vec[n] * other_vec[n] for n in nodes)
            norm_t = _math.sqrt(sum(target_vec[n] ** 2 for n in nodes))
            norm_o = _math.sqrt(sum(other_vec[n] ** 2 for n in nodes))
            sim = dot / (norm_t * norm_o) if norm_t * norm_o > 0 else 0
            if sim > 0:
                similarities.append((uid, sim))
        
        similarities.sort(key=lambda x: -x[1])
        
        for n in candidates:
            weighted_sum = 0
            total_weight = 0
            for uid, sim in similarities:
                other_progress = all_users_progress.get(uid, {})
                if other_progress.get(str(n)) == "mastered":
                    weighted_sum += sim
                total_weight += sim
            cf_scores[n] = weighted_sum / total_weight if total_weight > 0 else 0
    else:
        # 没有其他用户数据，CF 分数置 0
        for n in candidates:
            cf_scores[n] = 0
    
    # ─── 3. LLM 分数 ───
    llm_scores = {}
    for n in candidates:
        info = node_dict.get(n, {})
        module = info.get("module", "")
        difficulty = info.get("difficulty", 1)
        name = info.get("name", str(n))
        
        # 检查该节点与用户薄弱点的关联
        weak_ids = [int(k) for k, v in progress.items() if v == "weak"]
        prereq_of_weak = sum(1 for w in weak_ids if w in graph.successors(n))
        dependent_of_weak = sum(1 for w in weak_ids if w in graph.predecessors(n))
        
        # 难度适中、与薄弱点关联强的优先
        llm_scores[n] = 0.3 * (1 / difficulty) + 0.4 * min(prereq_of_weak, 5) / 5 + 0.3 * min(dependent_of_weak, 5) / 5
    
    # ─── 4. 融合 ───
    # 归一化各分数到 [0, 1]
    def _normalize(scores_dict):
        vals = list(scores_dict.values())
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return {k: 0.5 for k in scores_dict}
        return {k: (v - mn) / (mx - mn) for k, v in scores_dict.items()}
    
    gs = _normalize(graph_scores)
    cs = _normalize(cf_scores)
    ls = _normalize(llm_scores)
    
    # 默认权重 (可调)
    w_graph, w_cf, w_llm = 0.4, 0.35, 0.25
    
    fused = {}
    for n in candidates:
        fused[n] = w_graph * gs[n] + w_cf * cs[n] + w_llm * ls[n]
    
    ranked = sorted(fused.keys(), key=lambda n: -fused[n])[:top_n]
    
    # 总分数用于计算贡献占比
    total_graph = sum(gs[n] for n in ranked) or 1
    total_cf = sum(cs[n] for n in ranked) or 1
    total_llm = sum(ls[n] for n in ranked) or 1
    grand = total_graph + total_cf + total_llm
    
    recommendations = []
    for n in ranked:
        info = node_dict.get(n, {})
        recommendations.append({
            "id": n,
            "name": info.get("name", str(n)),
            "module": info.get("module", ""),
            "difficulty": info.get("difficulty", 1),
            "graph_score": round(gs[n], 4),
            "cf_score": round(cs[n], 4),
            "llm_score": round(ls[n], 4),
            "fused_score": round(fused[n], 4),
            "status": progress.get(str(n), "unlearned")
        })
    
    return {
        "recommendations": recommendations,
        "contribution": {
            "graph_pct": round(total_graph / grand * 100, 1),
            "cf_pct": round(total_cf / grand * 100, 1),
            "llm_pct": round(total_llm / grand * 100, 1)
        },
        "weights": {"graph": w_graph, "cf": w_cf, "llm": w_llm},
        "explanation": (
            f"推荐综合了图算法重要性（{w_graph*100:.0f}%）、"
            f"相似用户学习经验（{w_cf*100:.0f}%）、"
            f"知识点关联分析（{w_llm*100:.0f}%）三个维度。"
        )
    }


def counterfactual_simulation(graph, node_dict, progress, target_node_id, new_status="mastered"):
    """
    反事实推理：假设将某个知识点标记为 new_status，
    计算对整体学习状况的影响。
    
    返回前后对比：模块掌握度、可达节点数、PageRank 变化、学习路径变化。
    """
    if target_node_id not in graph or target_node_id not in node_dict:
        return {"error": "知识点不存在"}
    
    # ─── 当前状态 ───
    def _compute_stats(prog):
        total = len(node_dict)
        mastered = sum(1 for k, v in prog.items() if v == "mastered")
        weak = sum(1 for k, v in prog.items() if v == "weak")
        unlocked = 0
        for nid in node_dict:
            if prog.get(str(nid), "unlearned") == "mastered":
                continue
            pres = list(graph.predecessors(nid))
            if pres and all(prog.get(str(p), "unlearned") == "mastered" for p in pres):
                unlocked += 1
        return {"mastered": mastered, "weak": weak, "unlearned": total - mastered - weak,
                "mastery_pct": round(mastered / total * 100, 1) if total else 0,
                "unlocked": unlocked}
    
    before = _compute_stats(progress)
    
    # 模拟假设
    after_progress = dict(progress)
    after_progress[str(target_node_id)] = new_status
    after = _compute_stats(after_progress)
    
    # 模块级变化
    modules_before = {}
    modules_after = {}
    for nid, info in node_dict.items():
        mod = info.get("module", "未知")
        if mod not in modules_before:
            modules_before[mod] = {"total": 0, "mastered": 0}
            modules_after[mod] = {"total": 0, "mastered": 0}
        modules_before[mod]["total"] += 1
        modules_before[mod]["mastered"] += 1 if progress.get(str(nid)) == "mastered" else 0
        modules_after[mod]["total"] += 1
        modules_after[mod]["mastered"] += 1 if after_progress.get(str(nid)) == "mastered" else 0
    
    module_delta = []
    for mod in modules_before:
        b = modules_before[mod]
        a = modules_after[mod]
        module_delta.append({
            "module": mod,
            "before_pct": round(b["mastered"] / b["total"] * 100, 1),
            "after_pct": round(a["mastered"] / a["total"] * 100, 1),
            "delta": round((a["mastered"] - b["mastered"]) / b["total"] * 100, 1)
        })
    
    # 路径变化：以该节点为目标的最短路径
    path_before = None
    path_after = None
    mastered_before = [int(k) for k, v in progress.items() if v == "mastered" and int(k) in graph]
    mastered_after = [int(k) for k, v in after_progress.items() if v == "mastered" and int(k) in graph]
    
    if not mastered_before:
        mastered_before = [n for n in graph.nodes() if graph.in_degree(n) == 0]
    if not mastered_after:
        mastered_after = [n for n in graph.nodes() if graph.in_degree(n) == 0]
    
    best_before = None
    best_before_len = float("inf")
    for start in mastered_before:
        if start == target_node_id:
            best_before, best_before_len = [start], 0; break
        try:
            p = nx.shortest_path(graph, source=start, target=target_node_id)
            if len(p) < best_before_len:
                best_before, best_before_len = p, len(p)
        except nx.NetworkXNoPath:
            continue
    
    best_after = None
    best_after_len = float("inf")
    for start in mastered_after:
        if start == target_node_id:
            best_after, best_after_len = [start], 0; break
        try:
            p = nx.shortest_path(graph, source=start, target=target_node_id)
            if len(p) < best_after_len:
                best_after, best_after_len = p, len(p)
        except nx.NetworkXNoPath:
            continue
    
    target_name = node_dict.get(target_node_id, {}).get("name", str(target_node_id))
    
    delta = {
        "mastered_delta": after["mastered"] - before["mastered"],
        "mastery_pct_delta": round(after["mastery_pct"] - before["mastery_pct"], 1),
        "unlocked_delta": after["unlocked"] - before["unlocked"],
        "path_length_delta": (best_after_len - best_before_len) if best_before_len != float("inf") and best_after_len != float("inf") else None
    }
    
    return {
        "node": {"id": target_node_id, "name": target_name},
        "simulated_status": new_status,
        "before": before,
        "after": after,
        "delta": delta,
        "module_delta": module_delta,
        "path_before": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in (best_before or [])],
        "path_after": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in (best_after or [])],
        "summary": (
            f"如果将「{target_name}」标记为「{new_status}」，"
            f"整体掌握度将从 {before['mastery_pct']}% 提升至 {after['mastery_pct']}%（+{delta['mastery_pct_delta']}%），"
            f"新增 {delta['unlocked_delta']} 个知识点满足前置条件。"
        )
    }


# ─── 语义推理 ───

def transitive_closure_reasoning(graph, node_dict, node_id):
    """传递闭包推理：返回指定节点的全部间接前置（ancestors）和间接后置（descendants）"""
    if node_id not in graph:
        return {"error": "知识点不存在"}
    
    ancestors = list(nx.ancestors(graph, node_id))
    descendants = list(nx.descendants(graph, node_id))
    
    # 按拓扑序排列
    try:
        topo = list(nx.topological_sort(graph))
        ancestors.sort(key=lambda n: topo.index(n) if n in topo else 9999)
        descendants.sort(key=lambda n: topo.index(n) if n in topo else 9999)
    except nx.NetworkXUnfeasible:
        pass
    
    # 构建推理链样例：从最远的祖先到目标的最长路径
    reasoning_paths = []
    if ancestors:
        # 找一个叶子祖先（图中无前驱）
        leaf_ancestors = [n for n in ancestors if graph.in_degree(n) == 0]
        start = leaf_ancestors[0] if leaf_ancestors else ancestors[0]
        try:
            path = nx.shortest_path(graph, source=start, target=node_id)
            reasoning_paths.append({
                "type": "前置传递链",
                "path": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in path],
                "explanation": (
                    f"「{node_dict.get(start, {}).get('name', str(start))}」→……→「{node_dict.get(node_id, {}).get('name', str(node_id))}」"
                    f"构成一条长度为 {len(path)-1} 的前置依赖链，链上每个节点都必须依次掌握。"
                )
            })
        except nx.NetworkXNoPath:
            pass
    
    if descendants:
        leaf_descendants = [n for n in descendants if graph.out_degree(n) == 0]
        end = leaf_descendants[0] if leaf_descendants else descendants[0]
        try:
            path = nx.shortest_path(graph, source=node_id, target=end)
            reasoning_paths.append({
                "type": "后置传播链",
                "path": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in path],
                "explanation": (
                    f"「{node_dict.get(node_id, {}).get('name', str(node_id))}」→……→「{node_dict.get(end, {}).get('name', str(end))}」"
                    f"构成一条长度为 {len(path)-1} 的后置影响链，掌握当前知识点可为后续学习铺路。"
                )
            })
        except nx.NetworkXNoPath:
            pass
    
    node_name = node_dict.get(node_id, {}).get("name", str(node_id))
    return {
        "node": {"id": node_id, "name": node_name, "module": node_dict.get(node_id, {}).get("module", "")},
        "ancestors": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in ancestors],
        "descendants": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in descendants],
        "ancestor_count": len(ancestors),
        "descendant_count": len(descendants),
        "reasoning_paths": reasoning_paths,
        "summary": (
            f"「{node_name}」共有 {len(ancestors)} 个间接前置知识点、{len(descendants)} 个间接后置知识点。"
            f"掌握它需要 {'→'.join([node_dict.get(a,{}).get('name',str(a)) for a in ancestors[:3]])}……等基础知识；"
            f"学完后可继续学习 {'→'.join([node_dict.get(d,{}).get('name',str(d)) for d in descendants[:3]])}……等进阶内容。"
        )
    }


def rule_based_reasoning(graph, node_dict, rule, params):
    """规则引擎推理：支持多条 KG 语义规则"""
    if rule == "transitive_prerequisite":
        node_id = params.get("node_id")
        if node_id not in graph:
            return {"error": "知识点不存在"}
        ancestors = list(nx.ancestors(graph, node_id))
        # 分组：直接前置 vs 间接前置
        direct = list(graph.predecessors(node_id))
        indirect = [n for n in ancestors if n not in direct]
        node_name = node_dict.get(node_id, {}).get("name", str(node_id))
        return {
            "rule": "前置传递推理",
            "rule_description": "若 A 是 B 的前置、B 是 C 的前置，则 A 是 C 的间接前置（传递闭包）",
            "node": {"id": node_id, "name": node_name},
            "direct_prerequisites": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in direct],
            "indirect_prerequisites": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in indirect],
            "direct_count": len(direct),
            "indirect_count": len(indirect),
            "explanation": (
                f"「{node_name}」有 {len(direct)} 个直接前置、{len(indirect)} 个间接前置。"
                f"间接前置由传递闭包推理得出：若 A→B 且 B→C，则 A→C。"
                f"例如「{node_dict.get(direct[0],{}).get('name','?')}」是直接前置，"
                f"其前置通过传递规则也成为「{node_name}」的间接前置。"
            ) if direct else f"「{node_name}」无前置依赖，为根知识点。"
        }
    
    elif rule == "mastery_impact":
        node_id = params.get("node_id")
        progress = params.get("progress", {})
        if node_id not in graph:
            return {"error": "知识点不存在"}
        # 模拟：若掌握该节点，其后继中哪些的剩余前置数减少
        successors = list(graph.successors(node_id))
        impact = []
        for succ in successors:
            prereqs = list(graph.predecessors(succ))
            mastered_prereqs = sum(1 for p in prereqs if progress.get(str(p)) == "mastered" or p == node_id)
            remaining = len(prereqs) - mastered_prereqs
            impact.append({
                "node_id": succ,
                "node_name": node_dict.get(succ, {}).get("name", str(succ)),
                "total_prerequisites": len(prereqs),
                "remaining_after_mastery": max(0, remaining)
            })
        impact.sort(key=lambda x: x["remaining_after_mastery"])
        node_name = node_dict.get(node_id, {}).get("name", str(node_id))
        return {
            "rule": "掌握递推推理",
            "rule_description": "若掌握知识点 A，则 A 的直接后置 B 的「剩余前置数」减 1",
            "node": {"id": node_id, "name": node_name},
            "impact": impact,
            "total_impacted": len(impact),
            "explanation": (
                f"掌握「{node_name}」后，其 {len(impact)} 个直接后置知识点的剩余前置数将减少。"
                f"其中 {sum(1 for x in impact if x['remaining_after_mastery'] == 0)} 个后置的所有前置条件已满足，可直接学习。"
            )
        }
    
    elif rule == "all_paths":
        source_id = params.get("source_id")
        target_id = params.get("target_id")
        if source_id not in graph or target_id not in graph:
            return {"error": "知识点不存在"}
        try:
            paths = list(nx.all_simple_paths(graph, source=source_id, target=target_id, cutoff=10))
        except nx.NetworkXNoPath:
            paths = []
        result_paths = []
        for i, p in enumerate(paths[:20]):
            result_paths.append({
                "rank": i + 1,
                "length": len(p) - 1,
                "path": [{"id": n, "name": node_dict.get(n, {}).get("name", str(n))} for n in p]
            })
        src_name = node_dict.get(source_id, {}).get("name", str(source_id))
        tgt_name = node_dict.get(target_id, {}).get("name", str(target_id))
        return {
            "rule": "全路径推理",
            "rule_description": "找出两个实体之间的所有语义路径（最多返回 20 条，路径长度上限 10）",
            "source": {"id": source_id, "name": src_name},
            "target": {"id": target_id, "name": tgt_name},
            "paths": result_paths,
            "total_paths": len(paths),
            "summary": (
                f"从「{src_name}」到「{tgt_name}」共有 {len(paths)} 条语义路径。"
                f"最短路径长度为 {result_paths[0]['length'] if result_paths else '无'}。"
            ) if result_paths else f"从「{src_name}」到「{tgt_name}」不存在可达路径。"
        }
    
    return {"error": "未知推理规则，支持: transitive_prerequisite, mastery_impact, all_paths"}


# ─── 语义检索 ───

def semantic_query(graph, node_dict, name=None, module=None, difficulty_min=None, difficulty_max=None, relation=None):
    """语义检索：按实体名、模块、难度、关系类型组合筛选知识图谱"""
    matched = []
    for nid, info in node_dict.items():
        score = 0
        match_info = {}
        
        # 名称模糊匹配
        if name:
            if name in info.get("name", ""):
                score += 10
                match_info["name_match"] = True
            elif any(c in info.get("name", "") for c in name if len(c) > 1):
                score += 5
                match_info["name_match"] = "partial"
            else:
                continue  # 名称不匹配则跳过
        
        # 模块筛选
        if module:
            if info.get("module") == module:
                score += 10
                match_info["module_match"] = True
            else:
                continue
        
        # 难度筛选
        diff = info.get("difficulty", 1)
        if difficulty_min is not None and diff < difficulty_min:
            continue
        if difficulty_max is not None and diff > difficulty_max:
            continue
        
        # 无筛选条件时返回全部
        if not name and not module and difficulty_min is None and difficulty_max is None:
            score = 1
        
        if score > 0 or (not name and not module and difficulty_min is None and difficulty_max is None):
            matched.append({
                "id": nid,
                "name": info.get("name", str(nid)),
                "module": info.get("module", ""),
                "difficulty": diff,
                "match_score": score
            })
    
    # 按匹配度排序
    matched.sort(key=lambda x: -x["match_score"])
    
    # 若指定了关系类型，构造诱导子图
    induced_edges = []
    if relation and matched:
        matched_ids = set(m["id"] for m in matched)
        for u, v in graph.edges():
            rel = graph.edges[u, v].get("relation", "前置依赖")
            if rel == relation and u in matched_ids and v in matched_ids:
                induced_edges.append({
                    "from": u, "to": v, "relation": rel,
                    "from_name": node_dict.get(u, {}).get("name", str(u)),
                    "to_name": node_dict.get(v, {}).get("name", str(v))
                })
    
    return {
        "total": len(matched),
        "results": matched[:50],
        "induced_edges": induced_edges if induced_edges else None
    }


import json
from collections import Counter as _Counter

def basic_graph_stats(graph, node_dict):
    """Compute basic graph statistics for frontend display."""
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    in_degrees = [d for _, d in graph.in_degree()]
    out_degrees = [d for _, d in graph.out_degree()]
    
    avg_in = round(sum(in_degrees) / n, 2) if n else 0
    avg_out = round(sum(out_degrees) / n, 2) if n else 0
    max_in = max(in_degrees) if in_degrees else 0
    max_out = max(out_degrees) if out_degrees else 0
    
    # Network diameter (only for weakly connected graphs)
    diameter = None
    try:
        if nx.is_weakly_connected(graph):
            diameter = nx.diameter(graph.to_undirected())
        else:
            # Largest weakly connected component
            wcc = max(nx.weakly_connected_components(graph), key=len)
            sub = graph.subgraph(wcc)
            diameter = nx.diameter(sub.to_undirected())
    except:
        diameter = None
    
    # Density
    density = round(nx.density(graph), 4)
    
    # Average shortest path length
    avg_path = None
    try:
        if nx.is_weakly_connected(graph):
            avg_path = round(nx.average_shortest_path_length(graph.to_undirected()), 2)
        else:
            wcc = max(nx.weakly_connected_components(graph), key=len)
            sub = graph.subgraph(wcc)
            avg_path = round(nx.average_shortest_path_length(sub.to_undirected()), 2)
    except:
        avg_path = None
    
    # Module node counts
    modules = _Counter(n["module"] for n in node_dict.values() if "module" in n)
    max_mod = max(modules.values()) if modules else 0
    min_mod = min(modules.values()) if modules else 0
    max_mod_name = [k for k, v in modules.items() if v == max_mod][0] if modules else ""
    min_mod_name = [k for k, v in modules.items() if v == min_mod][0] if modules else ""
    
    # Modularity Q
    try:
        custom = community_detection(graph)
        custom_q = round(_compute_modularity_for_partition(graph, custom), 4)
    except:
        custom_q = None
    try:
        nx_comm = _nx_community_detection(graph)
        nx_q = round(_compute_modularity_for_partition(graph, nx_comm), 4)
    except:
        nx_q = None
    
    return {
        "node_count": n,
        "edge_count": m,
        "avg_in_degree": avg_in,
        "avg_out_degree": avg_out,
        "max_in_degree": max_in,
        "max_out_degree": max_out,
        "diameter": diameter,
        "density": density,
        "avg_path_length": avg_path,
        "module_count": len(modules),
        "max_module_nodes": max_mod,
        "max_module_name": max_mod_name,
        "min_module_nodes": min_mod,
        "min_module_name": min_mod_name,
        "modularity_custom": custom_q,
        "modularity_girvan_newman": nx_q
    }
