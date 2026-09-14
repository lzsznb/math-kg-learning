"""
Copyright (c) 2026 lzsznb
SPDX‑License‑Identifier: MIT
"""


import json
import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI
import networkx as nx

from .graph_data import load_graph, build_knowledge_context, find_related_nodes, G, node_dict, nodes_data, edges_data, load_user_weights, update_edge_weight, get_edge_weights, apply_progress_to_weights, init_user_weights, delete_user_weights, get_triples
from .agent import agent_executor
from .graph_algo import pagerank_top10, community_detection, community_compare, explain_community, dijkstra, analyze_user_model, scale_free_analysis, small_world_analysis, robustness_analysis, influence_maximization, hybrid_recommendation, counterfactual_simulation, transitive_closure_reasoning, rule_based_reasoning, semantic_query, basic_graph_stats
from .entity_extraction import run_extraction_pipeline, parse_source_text, validate_entities, classify_entities, coverage_analysis, export_to_json


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_graph()
    yield


app = FastAPI(title="高中数学智能学习助手 API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DATA_PATH = Path(__file__).parent.parent / "math_knowledge_network.json"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


# ─── 基础数据接口 ───

@app.get("/")
def root():
    return {"message": "高中数学智能学习助手 API 已启动"}

@app.get("/api/knowledge")
def get_knowledge_network():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/nodes")
def get_nodes():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return {"nodes": json.load(f)["nodes"]}

@app.get("/api/edges")
def get_edges():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return {"edges": json.load(f)["edges"]}

@app.get("/api/modules")
def get_modules():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return {"modules": json.load(f)["modules"]}


# ─── 图谱分析接口 ───

@app.get("/api/node/{node_id}")
def get_node(node_id: int):
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    node = next((n for n in data["nodes"] if n["id"] == node_id), None)
    if not node:
        return {"error": "节点不存在"}
    result = dict(node)
    result["prerequisites"] = [e["from"] for e in data["edges"] if e["to"] == node_id]
    result["dependents"] = [e["to"] for e in data["edges"] if e["from"] == node_id]
    return result

@app.get("/api/centrality/degree")
def get_degree_centrality():
    if G is None:
        return {"error": "图未初始化"}
    cent = nx.degree_centrality(G)
    return {"centrality": [_build_node(nid, cent[nid]) for nid in sorted(cent, key=cent.get, reverse=True)[:10] if nid in node_dict]}

@app.get("/api/centrality/betweenness")
def get_betweenness_centrality():
    if G is None:
        return {"error": "图未初始化"}
    cent = nx.betweenness_centrality(G)
    return {"centrality": [_build_node(nid, cent[nid]) for nid in sorted(cent, key=cent.get, reverse=True)[:10] if nid in node_dict]}

@app.get("/api/centrality/pagerank")
def get_pagerank():
    if G is None:
        return {"error": "图未初始化"}
    result = pagerank_top10(G, node_dict)
    top_name = result[0]['name']
    top_module = result[0]['module']
    summary = (
        "PageRank 衡量知识点在知识网络中的「影响力」——"
        "一个知识点被越多重要的前置知识点指向，其 PageRank 越高。"
        f"排名第一的「{top_name}」（{top_module}）"
        "是知识网络中的核心枢纽，连接了多个模块的关键概念，"
        "是学习路径中反复出现的交汇点。"
    )
    return {"centrality": result, "summary": summary}

@app.get("/api/community")
def get_community():
    if G is None:
        return {"error": "图未初始化"}
    communities = community_detection(G)
    return {"communities": [
        {"community_id": i, "nodes": [node_dict[nid] for nid in comm if nid in node_dict], "size": len(comm)}
        for i, comm in enumerate(communities, 1)
    ]}

@app.get("/api/community/compare")
def get_community_compare():
    if G is None:
        return {"error": "图未初始化"}
    return community_compare(G)

@app.get("/api/community/explain/{node_id}")
def get_community_explain(node_id: int):
    if G is None:
        return {"error": "图未初始化"}
    return explain_community(G, node_dict, node_id)


# ─── 网络科学综合分析 ───

@app.get("/api/network-analysis")
def get_network_analysis():
    if G is None:
        return {"error": "图未初始化"}
    return {
        "basic_stats": basic_graph_stats(G, node_dict),
        "scale_free": scale_free_analysis(G, node_dict),
        "small_world": small_world_analysis(G, node_dict),
        "robustness": robustness_analysis(G, node_dict),
        "influence": influence_maximization(G, node_dict, k=5, mc_sims=50)
    }


# ─── 动态加权边接口 ───

@app.post("/api/edge/weight")
def api_update_edge_weight(body: dict):
    user_id = body.get("user_id", "default")
    from_node = body.get("from")
    to_node = body.get("to")
    delta = body.get("delta", 0)
    if from_node is None or to_node is None:
        return {"error": "缺少 from 或 to 参数"}
    return update_edge_weight(user_id, from_node, to_node, delta)

@app.get("/api/edge/weights/{user_id}")
def api_get_edge_weights(user_id: str):
    return {"edges": get_edge_weights(user_id)}

@app.post("/api/edge/weights/init")
def api_init_weights(body: dict):
    user_id = body.get("user_id", "default")
    init_user_weights(user_id)
    return {"message": f"用户 {user_id} 权重已初始化"}

@app.delete("/api/user/{user_id}")
def api_delete_user(user_id: str):
    delete_user_weights(user_id)
    return {"message": f"用户 {user_id} 数据已删除"}

@app.post("/api/adaptive-path/{user_id}/{target_id}")
def api_adaptive_path(user_id: str, target_id: int, body: dict):
    if G is None or target_id not in G:
        return {"error": "目标知识点不存在"}
    weights = load_user_weights(user_id)
    progress = body.get("progress", {}) if body else {}
    mastered = [int(k) for k, v in progress.items() if v == "mastered"] or [n for n in G.nodes() if G.in_degree(n) == 0]
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
    details = [{"id": nid, "name": node_dict[nid]["name"], "module": node_dict[nid]["module"],
                "difficulty": node_dict[nid].get("difficulty", 1)} for nid in best if nid in node_dict]
    return {"target": {"id": target_id, "name": node_dict[target_id]["name"], "module": node_dict[target_id]["module"]},
            "path": details, "total_weight": round(best_weight, 4), "length": len(best) - 1}

@app.post("/api/edge/weights/apply-progress")
def api_apply_progress(body: dict):
    user_id = body.get("user_id", "default")
    progress = body.get("progress", {})
    changed = apply_progress_to_weights(user_id, progress)
    return {"changed": changed, "count": len(changed)}

@app.post("/api/user-model/{user_id}")
def get_user_model(user_id: str, body: dict):
    if G is None:
        return {"error": "图未初始化"}
    progress = body.get("progress", {}) if body else {}
    modules = sorted(set(n.get("module", "未知") for n in nodes_data))
    return analyze_user_model(G, node_dict, progress, modules)

@app.get("/api/shortest-path/{start_id}/{end_id}")
def get_shortest_path(start_id: int, end_id: int):
    if G is None or start_id not in G or end_id not in G:
        return {"error": "节点不存在"}
    try:
        path = nx.shortest_path(G, source=start_id, target=end_id)
        return {"start": start_id, "end": end_id, "path": [{"id": nid, "name": node_dict[nid]["name"], "module": node_dict[nid]["module"]} for nid in path if nid in node_dict], "length": len(path) - 1}
    except nx.NetworkXNoPath:
        return {"error": "两知识点之间无可达路径"}


# ─── 诊断与推荐接口 ───

@app.post("/api/diagnosis/weak-points")
def diagnose_weak_points(progress: dict):
    if G is None:
        return {"error": "图未初始化"}
    weak_points = []
    missing_prerequisites = {}
    for nid_str, status in progress.items():
        if status == "weak":
            node_id = int(nid_str)
            if node_id in node_dict:
                weak_points.append({"id": node_id, "name": node_dict[node_id]["name"], "module": node_dict[node_id]["module"]})
    for wp in weak_points:
        nid = wp["id"]
        missing = [{"id": pre_id, "name": node_dict[pre_id]["name"], "status": progress.get(str(pre_id), "unlearned")}
                   for pre_id in G.predecessors(nid) if pre_id in node_dict and progress.get(str(pre_id), "unlearned") != "mastered"]
        if missing:
            missing_prerequisites[str(nid)] = {"name": wp["name"], "missing": missing}
    return {"weak_points": weak_points, "missing_prerequisites": missing_prerequisites,
            "summary": {"total_weak_points": len(weak_points), "total_missing_prerequisites": sum(len(v["missing"]) for v in missing_prerequisites.values()),
                        "nodes_with_missing_prerequisites": len(missing_prerequisites)}}

@app.post("/api/recommendation/learning-path")
def recommend_learning_path(progress: dict, target_id: int):
    if G is None or target_id not in G:
        return {"error": "目标知识点不存在"}
    mastered_ids = [int(k) for k, v in progress.items() if v == "mastered"]
    mastered = [m for m in (mastered_ids or [n for n in G.nodes() if G.in_degree(n) == 0]) if m in G]
    best = None
    best_len = float("inf")
    for start in mastered:
        if start == target_id:
            best, best_len = [start], 0; break
        try:
            p = nx.shortest_path(G, source=start, target=target_id)
            if len(p) < best_len:
                best, best_len = p, len(p)
        except nx.NetworkXNoPath:
            continue
    if best is None:
        return {"error": "无法找到学习路径"}
    details = [{"id": nid, "name": node_dict[nid]["name"], "module": node_dict[nid]["module"],
                "difficulty": node_dict[nid].get("difficulty", 1), "status": progress.get(str(nid), "unlearned"),
                "is_mastered": progress.get(str(nid), "") == "mastered", "is_weak": progress.get(str(nid), "") == "weak",
                "is_unlearned": progress.get(str(nid), "") not in ("mastered", "weak")} for nid in best if nid in node_dict]
    mastered_c = sum(1 for d in details if d["is_mastered"])
    weak_c = sum(1 for d in details if d["is_weak"])
    return {"target": {"id": target_id, "name": node_dict[target_id]["name"], "module": node_dict[target_id]["module"]},
            "path": details, "start_node": details[0] if details else None,
            "statistics": {"total_steps": len(details), "mastered": mastered_c, "weak": weak_c,
                           "unlearned": len(details) - mastered_c - weak_c, "needs_learning": len(details) - mastered_c}}


# ─── 混合推荐 ───

@app.post("/api/recommend/hybrid")
def api_hybrid_recommend(body: dict):
    if G is None:
        return {"error": "图未初始化"}
    user_id = body.get("user_id", "")
    progress = body.get("progress", {})
    all_users_progress = body.get("all_users_progress", {})
    return hybrid_recommendation(G, node_dict, progress, all_users_progress, top_n=10)


# ─── 反事实推理 ───

@app.post("/api/counterfactual")
def api_counterfactual(body: dict):
    if G is None:
        return {"error": "图未初始化"}
    progress = body.get("progress", {})
    target_node_id = body.get("node_id")
    new_status = body.get("new_status", "mastered")
    if target_node_id is None:
        return {"error": "请指定知识点ID"}
    try:
        target_node_id = int(target_node_id)
    except (ValueError, TypeError):
        return {"error": "知识点ID格式错误"}
    return counterfactual_simulation(G, node_dict, progress, target_node_id, new_status)


# ─── 知识图谱三元组接口 ───

@app.get("/api/kg/triples")
def api_kg_triples(relation: str = None):
    if G is None:
        return {"error": "图未初始化"}
    triples = get_triples(relation)
    return {"total": len(triples), "relation_type": relation or "全部", "triples": triples}


# ─── 语义推理接口 ───

@app.post("/api/kg/reasoning/transitive-closure")
def api_transitive_closure(body: dict):
    if G is None:
        return {"error": "图未初始化"}
    node_id = body.get("node_id")
    if node_id is None:
        return {"error": "请指定知识点ID"}
    try:
        node_id = int(node_id)
    except (ValueError, TypeError):
        return {"error": "知识点ID格式错误"}
    return transitive_closure_reasoning(G, node_dict, node_id)


@app.post("/api/kg/reasoning/rules")
def api_rule_reasoning(body: dict):
    if G is None:
        return {"error": "图未初始化"}
    rule = body.get("rule", "")
    params = body.get("params", {})
    return rule_based_reasoning(G, node_dict, rule, params)


# ─── 语义检索接口 ───

@app.post("/api/kg/query")
def api_kg_query(body: dict):
    if G is None:
        return {"error": "图未初始化"}
    name = body.get("name")
    module = body.get("module")
    difficulty_min = body.get("difficulty_min")
    difficulty_max = body.get("difficulty_max")
    relation = body.get("relation")
    return semantic_query(G, node_dict, name, module, difficulty_min, difficulty_max, relation)


# ─── 实体抽取接口 ───

SOURCE_TEXT_PATH = Path(__file__).resolve().parent.parent / "entity_source.txt"

@app.post("/api/kg/extract-entities")
def api_extract_entities(body: dict = {}):
    """运行实体抽取管道，返回抽取结果与统计分析"""
    source_file = body.get("source_file")
    if source_file:
        path = Path(source_file)
        if not path.exists():
            return {"error": f"源文件不存在: {source_file}"}
    else:
        # 使用默认源文件
        if not SOURCE_TEXT_PATH.exists():
            return {"error": f"默认源文件不存在: {SOURCE_TEXT_PATH}"}
        path = str(SOURCE_TEXT_PATH)
    return run_extraction_pipeline(source_file=path)


@app.post("/api/kg/validate-entities")
def api_validate_entities(body: dict):
    """校验已有实体数据的质量"""
    nodes = body.get("nodes", [])
    edges = body.get("edges", [])
    return validate_entities({"nodes": nodes, "edges": edges})


@app.get("/api/kg/entity-statistics")
def api_entity_statistics():
    """返回当前图谱实体的统计信息"""
    if G is None:
        return {"error": "图未初始化"}
    data = {"nodes": [n for n in nodes_data], "edges": [e for e in edges_data]}
    return {
        "validation": validate_entities(data),
        "statistics": classify_entities(data),
        "coverage": coverage_analysis(data)
    }


# ─── AI 问答接口 ───

@app.post("/api/chat")
def chat(message: dict):
    """AI知识问答（非流式，兼容前端现有调用）"""
    if not DEEPSEEK_API_KEY:
        return {"error": "未配置DeepSeek API密钥"}
    user_msg = message.get("message", "")
    history = message.get("history", [])
    progress = message.get("progress", {})
    if not user_msg.strip():
        return {"error": "请输入问题"}
    system_prompt = (
        "你是一个高中数学智能学习助手。你熟悉高中数学知识网络的整体结构。\n"
        "请根据知识图谱中的知识点关系回答用户的问题。\n"
        "如果用户问到一个具体知识点，请解释其概念、前置知识（需要先掌握什么）、"
        "以及它可以用来解决什么问题。\n"
        "尽量在回答中引用知识图谱中的具体知识点名称（用双引号括起来），"
        "方便系统定位对应的知识点节点。\n"
        "回答要简洁易懂，适合高中生的理解水平。\n\n"
        "注意：请使用中文回答。\n"
    ) + "\n\n当前知识网络：\n" + build_knowledge_context()
    if progress:
        mastered = [node_dict.get(int(k), {}).get("name", k) for k, v in progress.items() if v == "mastered"]
        weak = [node_dict.get(int(k), {}).get("name", k) for k, v in progress.items() if v == "weak"]
        if mastered: system_prompt += "\n\n用户已掌握：\n" + "、".join(mastered)
        if weak: system_prompt += "\n\n用户薄弱：\n" + "、".join(weak)
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-10:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": user_msg})
    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(model="deepseek-v4-pro", messages=messages, stream=False,
                                               reasoning_effort="high", extra_body={"thinking": {"type": "enabled"}})
        reply = resp.choices[0].message.content
        return {"reply": reply, "related_nodes": find_related_nodes(reply)}
    except Exception as e:
        return {"error": f"AI服务调用失败: {str(e)}"}


@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    """AI知识问答（流式 SSE），一边生成一边推送给前端"""
    if not DEEPSEEK_API_KEY:
        return {"error": "未配置DeepSeek API密钥"}
    body = await request.json()
    user_msg = body.get("message", "")
    history = body.get("history", [])
    progress = body.get("progress", {})
    if not user_msg.strip():
        return {"error": "请输入问题"}

    system_prompt = (
        "你是一个高中数学智能学习助手。你熟悉高中数学知识网络的整体结构。\n"
        "请根据知识图谱中的知识点关系回答用户的问题。\n"
        "回答要简洁易懂，适合高中生的理解水平。\n\n"
        "注意：请使用中文回答。\n"
    ) + "\n\n当前知识网络：\n" + build_knowledge_context()
    if progress:
        mastered = [node_dict.get(int(k), {}).get("name", k) for k, v in progress.items() if v == "mastered"]
        weak = [node_dict.get(int(k), {}).get("name", k) for k, v in progress.items() if v == "weak"]
        if mastered: system_prompt += "\n\n用户已掌握：\n" + "、".join(mastered)
        if weak: system_prompt += "\n\n用户薄弱：\n" + "、".join(weak)

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-10:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": user_msg})

    async def generate():
        full_reply = ""
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        try:
            stream = client.chat.completions.create(
                model="deepseek-v4-pro", messages=messages, stream=True,
                reasoning_effort="high", extra_body={"thinking": {"type": "enabled"}}
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_reply += token
                    yield f"data: {json.dumps({'type': 'chunk', 'content': token}, ensure_ascii=False)}\n\n"
            related = find_related_nodes(full_reply)
            yield f"data: {json.dumps({'type': 'done', 'related_nodes': related}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─── Agent 智能体接口 ───

@app.post("/api/agent/chat")
def agent_chat(message: dict):
    if not os.environ.get("DEEPSEEK_API_KEY", ""):
        return {"error": "未配置DeepSeek API密钥"}
    user_msg = message.get("message", "")
    session_id = message.get("session_id", "") or "agent_" + str(uuid.uuid4())
    progress = message.get("progress", {})
    if not user_msg.strip():
        return {"error": "请输入问题"}
    try:
        msgs = []
        if progress:
            mastered = [node_dict.get(int(k), {}).get("name", k) for k, v in progress.items() if v == "mastered"]
            weak = [node_dict.get(int(k), {}).get("name", k) for k, v in progress.items() if v == "weak"]
            note = "【用户当前学习进度】"
            if mastered: note += "\n已掌握：" + "、".join(mastered)
            if weak: note += "\n薄弱：" + "、".join(weak)
            msgs.append(("system", note))
        msgs.append(("user", user_msg))
        result = agent_executor.invoke({"messages": msgs}, {"configurable": {"thread_id": session_id}, "recursion_limit": 30})
        final = result["messages"][-1]
        reply = final.content if hasattr(final, "content") else str(final)
        tool_calls_info = []
        for m in result["messages"]:
            if hasattr(m, "tool_calls") and m.tool_calls:
                for tc in m.tool_calls:
                    tool_calls_info.append({"tool": tc.get("name", ""), "args": json.dumps(tc.get("args", {}), ensure_ascii=False)})
            elif hasattr(m, "additional_kwargs") and "tool_calls" in m.additional_kwargs:
                for tc in m.additional_kwargs["tool_calls"]:
                    tool_calls_info.append({"tool": tc["function"]["name"], "args": tc["function"]["arguments"]})
        return {"reply": reply, "related_nodes": find_related_nodes(reply), "session_id": session_id, "tool_calls": tool_calls_info}
    except Exception as e:
        return {"error": f"AI Agent 调用失败: {str(e)}"}


# ─── 辅助函数 ───

def _build_node(nid, score):
    info = node_dict.get(nid)
    return {"id": nid, "name": info["name"], "module": info["module"], "score": round(score, 4)} if info else None
